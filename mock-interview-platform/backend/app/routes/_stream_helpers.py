from flask import Response, stream_with_context
import json
import time
from app.routes.interview import use_redis_queue, rq_queue, redis_conn, jobs, jobs_lock


def sse_event(data: dict, event: str = None):
    payload = ''
    if event:
        payload += f"event: {event}\n"
    payload += f"data: {json.dumps(data)}\n\n"
    return payload


def poll_job_and_stream(job_id, timeout_seconds=60):
    start = time.time()
    interval = 1.0
    while time.time() - start < timeout_seconds:
        # Check Redis RQ job first
        if use_redis_queue and redis_conn is not None:
            try:
                from rq.job import Job
                rq_job = Job.fetch(job_id, connection=redis_conn)
                status = rq_job.get_status()
                if status in ('queued', 'deferred', 'started', 'scheduled'):
                    yield sse_event({'status': 'pending', 'job_id': job_id})
                elif status == 'finished':
                    yield sse_event({'status': 'completed', 'job_id': job_id, 'result': rq_job.result})
                    return
                elif status == 'failed':
                    yield sse_event({'status': 'failed', 'job_id': job_id, 'error': str(rq_job.exc_info)})
                    return
            except Exception:
                pass
        # Fall back to in-process job store
        with jobs_lock:
            job = jobs.get(job_id)
            if job:
                if job.get('status') == 'pending':
                    yield sse_event({'status': 'pending', 'job_id': job_id})
                elif job.get('status') == 'completed':
                    yield sse_event({'status': 'completed', 'job_id': job_id, 'result': job.get('result')})
                    return
                elif job.get('status') == 'failed':
                    yield sse_event({'status': 'failed', 'job_id': job_id, 'error': job.get('error')})
                    return
        time.sleep(interval)
        interval = min(interval * 1.5, 5.0)
    # Timeout
    yield sse_event({'status': 'timeout', 'job_id': job_id})
