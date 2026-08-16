import json
from datetime import datetime
from pathlib import Path

from app import mongo
from flask import current_app
from app.models.dashboard import DashboardStats
from app.utils.time import utc_now


class DashboardService:
    """Service layer for persisting and retrieving dashboard statistics.

    Statistics are stored in the `dashboard_stats` collection, keyed by
    user_id, and are updated incrementally as interviews are completed.
    This avoids recomputing aggregates from raw interview documents on
    every dashboard request.
    """

    COLLECTION = 'dashboard_stats'
    FALLBACK_STATS_FILE = Path(__file__).resolve().parents[2] / 'data' / 'dashboard_stats.json'
    PROCESSED_SESSIONS = 'dashboard_processed_sessions'
    # Simple per-process TTL cache to reduce repeated DB reads during
    # high-frequency polling from the frontend. Keys are user_id strings.
    _cache = {}
    _cache_ttl_seconds = 5
    # When the optional MongoDB service is offline, authenticated local users
    # still need to see the interviews they just completed. Keep the
    # idempotency guard in-process alongside the fallback stats cache.
    _in_memory_processed_sessions = set()

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def _load_fallback_stats(self):
        try:
            self.FALLBACK_STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            if not self.FALLBACK_STATS_FILE.exists():
                self.FALLBACK_STATS_FILE.write_text('{}', encoding='utf-8')
                return {}
            raw = self.FALLBACK_STATS_FILE.read_text(encoding='utf-8').strip()
            if not raw:
                return {}
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _save_fallback_stats(self, payload):
        try:
            self.FALLBACK_STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.FALLBACK_STATS_FILE.write_text(json.dumps(payload, default=str, indent=2), encoding='utf-8')
        except Exception:
            pass

    def get_stats(self, user_id):
        """Return the persisted dashboard stats for a user from MongoDB or JSON fallback."""
        try:
            # Check short-lived cache first to avoid repeated expensive DB reads
            cache_entry = self._cache.get(user_id)
            if cache_entry:
                cached_value, ts = cache_entry
                # Only use cache if still valid (5-second TTL)
                if (utc_now() - ts).total_seconds() < self._cache_ttl_seconds:
                    return cached_value

            # Try MongoDB first (primary source)
            if current_app.config.get('MONGO_AVAILABLE', True):
                try:
                    doc = mongo.db[self.COLLECTION].find_one({'user_id': user_id})
                    if doc:
                        stats = DashboardStats.from_dict(doc)
                        self._cache[user_id] = (stats, utc_now())
                        return stats
                except Exception as exc:
                    print(f'DashboardService.get_stats MongoDB error: {exc}')
                    # Fall through to JSON fallback below

            # Fall back to JSON file if MongoDB not available or no data found
            try:
                payload = self._load_fallback_stats()
                doc = payload.get(str(user_id))
                if doc:
                    stats = DashboardStats.from_dict(doc)
                    self._cache[user_id] = (stats, utc_now())
                    return stats
            except Exception as exc:
                print(f'DashboardService.get_stats JSON fallback error: {exc}')

        except Exception as exc:
            print(f'DashboardService.get_stats error: {exc}')

        return None

    def get_or_create_stats(self, user_id):
        """Return existing stats or create a fresh zeroed record."""
        stats = self.get_stats(user_id)
        if stats is None:
            stats = DashboardStats(user_id=user_id)
            self.save_stats(stats)
            # Ensure new stats are cached immediately
            self._cache[user_id] = (stats, utc_now())
        return stats

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def save_stats(self, stats):
        """Upsert the given DashboardStats document to both MongoDB and fallback JSON file."""
        stats_dict = stats.to_dict()
        
        # Always save to fallback JSON file for redundancy, even if MongoDB is available
        try:
            payload = self._load_fallback_stats()
            payload[str(stats.user_id)] = stats_dict
            self._save_fallback_stats(payload)
        except Exception as exc:
            print(f'DashboardService.save_stats JSON fallback error: {exc}')
        
        # Also try to save to MongoDB if available
        if not current_app.config.get('MONGO_AVAILABLE', True):
            self._cache[stats.user_id] = (stats, utc_now())
            return True

        try:
            mongo.db[self.COLLECTION].update_one(
                {'user_id': stats.user_id},
                {'$set': stats_dict},
                upsert=True,
            )
            self._cache[stats.user_id] = (stats, utc_now())
            return True
        except Exception as exc:
            print(f'DashboardService.save_stats MongoDB error: {exc}')
            # Fallback was already saved above, so mark as successful
            self._cache[stats.user_id] = (stats, utc_now())
            return True

    def update_after_interview(self, user_id, interview):
        """Incrementally update a user's stats after an interview completes.

        Args:
            user_id: The string user id.
            interview: A dict representing the completed interview document
                (must contain `responses`, `job_role`, and `created_at`).
        """
        session_id = interview.get('_id')
        if session_id:
            session_key = (user_id, str(session_id))
            if session_key in self._in_memory_processed_sessions:
                return self.get_stats(user_id) or self.get_or_create_stats(user_id)

            # Guard against double-counting when get_feedback is called
            # multiple times for the same session (e.g. page refresh). In
            # fallback mode the in-memory set above provides that guard
            # without attempting a database connection.
            if current_app.config.get('MONGO_AVAILABLE', True):
                try:
                    already_processed = mongo.db[self.PROCESSED_SESSIONS].find_one(
                        {'session_id': session_id, 'user_id': user_id}
                    )
                    if already_processed:
                        self._in_memory_processed_sessions.add(session_key)
                        return self.get_stats(user_id) or self.get_or_create_stats(user_id)
                    mongo.db[self.PROCESSED_SESSIONS].insert_one(
                        {'session_id': session_id, 'user_id': user_id, 'processed_at': utc_now()}
                    )
                except Exception as exc:
                    print(f'DashboardService.update_after_interview guard error: {exc}')
            self._in_memory_processed_sessions.add(session_key)

        stats = self.get_or_create_stats(user_id)

        responses = interview.get('responses', [])
        if not responses:
            return stats

        # Extract the latest response for scoring.
        last_response = responses[-1]
        gemini_feedback = last_response.get('feedback', {}).get('gemini_feedback', {})
        cv_analysis = last_response.get('feedback', {}).get('cv_analysis', {})

        score = gemini_feedback.get('overall_score')
        confidence = cv_analysis.get('average_confidence')

        # Update aggregate counters.
        stats.interviews_completed += 1
        stats.total_responses += len(responses)

        # Recompute averages including the new interview.
        all_scores = [stats.average_score] if stats.average_score else []
        all_confidences = [stats.confidence_score] if stats.confidence_score else []
        if score is not None:
            all_scores.append(score)
        if confidence is not None:
            all_confidences.append(int(confidence * 100))

        stats.average_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
        stats.confidence_score = round(sum(all_confidences) / len(all_confidences)) if all_confidences else 0

        # Prepend the new interview to recent list (newest first).
        created_at = interview.get('created_at', utc_now())
        recent_entry = {
            'role': interview.get('job_role', 'N/A'),
            'score': score if score is not None else 'N/A',
            'date': created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at),
            'confidence': int(confidence * 100) if confidence is not None else 'N/A',
        }
        stats.recent_interviews.insert(0, recent_entry)
        stats.recent_interviews = stats.recent_interviews[:10]  # Keep latest 10

        stats.updated_at = utc_now()
        stats.history_synced_at = stats.updated_at
        self.save_stats(stats)
        # Refresh short-lived cache so immediate reads return the updated stats
        try:
            self._cache[user_id] = (stats, utc_now())
        except Exception:
            pass
        return stats

    def rebuild_from_interviews(self, user_id):
        """Recompute a user's dashboard stats from raw interview documents.

        This is useful for backfilling or correcting stats after data
        migrations or manual edits.
        """
        try:
            # Only project the fields we need to compute stats to reduce IO
            interviews = list(
                mongo.db.interviews.find(
                    {'user_id': user_id, 'responses': {'$exists': True, '$ne': []}},
                    {'responses': 1, 'job_role': 1, 'created_at': 1}
                )
            )
        except Exception as exc:
            print(f'DashboardService.rebuild_from_interviews error: {exc}')
            interviews = []
            try:
                current_app.config['MONGO_AVAILABLE'] = False
            except Exception:
                pass

        stats = DashboardStats(user_id=user_id)
        all_scores = []
        all_confidences = []
        recent = []

        for interview in interviews:
            responses = interview.get('responses', [])
            if not responses:
                continue

            stats.interviews_completed += 1
            stats.total_responses += len(responses)

            last_response = responses[-1]
            gemini_feedback = last_response.get('feedback', {}).get('gemini_feedback', {})
            cv_analysis = last_response.get('feedback', {}).get('cv_analysis', {})

            score = gemini_feedback.get('overall_score')
            confidence = cv_analysis.get('average_confidence')

            if score is not None:
                all_scores.append(score)
            if confidence is not None:
                all_confidences.append(int(confidence * 100))

            created_at = interview.get('created_at', utc_now())
            recent.append({
                'role': interview.get('job_role', 'N/A'),
                'score': score if score is not None else 'N/A',
                'date': created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at),
                'confidence': int(confidence * 100) if confidence is not None else 'N/A',
            })

        stats.average_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0
        stats.confidence_score = round(sum(all_confidences) / len(all_confidences)) if all_confidences else 0
        recent.sort(key=lambda x: x['date'], reverse=True)
        stats.recent_interviews = recent[:10]
        stats.updated_at = utc_now()
        # Mark the record as backfilled so a dashboard with no completed
        # interviews does not query the interview collection on every poll.
        stats.history_synced_at = stats.updated_at

        self.save_stats(stats)
        # Cache rebuilt stats
        self._cache[user_id] = (stats, utc_now())
        return stats
