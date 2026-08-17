"""Simple RQ worker entrypoint for background job processing.

Run this in production (or locally) with:

  REDIS_URL=redis://localhost:6379/0 python backend/worker.py

The worker imports application modules so ensure PYTHONPATH includes the repo root or run from project root.
"""
import os
import logging

try:
    import redis
    from rq import Worker, Queue, Connection
except Exception as e:
    logging.error('Redis/RQ not available: %s', e)
    raise

logging.basicConfig(level=logging.INFO)

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
conn = redis.from_url(redis_url)

listen = ['default']

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
