"""Helpers for avoiding repeated blocking MongoDB operations after an outage."""

from flask import current_app


def is_mongo_available():
    """Return the current request's MongoDB availability when Flask is active."""
    try:
        return bool(current_app.config.get('MONGO_AVAILABLE', False))
    except RuntimeError:
        # Service unit tests can run outside an application context. Preserve
        # their existing behavior and let their database mocks handle calls.
        return True


def mark_mongo_unavailable(error):
    """Disable further Mongo calls for this process after a connection failure."""
    try:
        if current_app.config.get('MONGO_AVAILABLE', False):
            current_app.logger.warning(
                'MongoDB became unavailable; using local fallbacks until restart: %s',
                error,
            )
        current_app.config['MONGO_AVAILABLE'] = False
    except RuntimeError:
        # There is no Flask app context to update (for example, a unit test).
        pass
