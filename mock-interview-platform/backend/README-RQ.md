Running Redis + RQ worker (development)

This project supports background jobs using RQ (Redis Queue). To run the backend plus a worker locally using Docker Compose, use the supplementary compose file which brings up a Redis server and a worker that processes queued jobs.

Quickstart (Docker Compose)

1. Ensure you have Docker and Docker Compose installed.
2. Copy your environment variables into a .env file at the repository root (do not commit secrets).
3. Start the full stack with worker support:

   docker compose -f docker-compose.yml -f docker-compose.rq.yml up --build

   This will start:
   - mongodb (from docker-compose.yml)
   - backend (from docker-compose.yml)
   - frontend (from docker-compose.yml)
   - redis (from docker-compose.rq.yml)
   - worker (from docker-compose.rq.yml) — runs `rq worker default`

4. Verify:
   - Backend API: http://localhost:5000
   - Frontend: http://localhost:3000
   - Redis: default port 6379 on localhost

Notes & Troubleshooting

- The worker runs in the same codebase as the backend, so it needs the same environment variables set (MONGO_URI, REDIS_URL, GOOGLE_GEMINI_API_KEY, etc.). Make sure they are present in your environment or in a .env file consumed by Docker Compose.

- If the worker cannot import a callable referenced by an enqueued job, check PYTHONPATH and that the service is started from the project root. The worker must be able to import `app.routes.interview` where job functions are defined.

- Logs: `docker compose logs -f worker` shows real-time worker logs. Inspect these if jobs are failing.

- In production, prefer a managed Redis instance (e.g., ElastiCache, Redis Cloud) and point REDIS_URL to the secure endpoint (rediss:// when supported).

Security

- Do not expose Redis publicly; restrict access via network/VPC.
- Use a passworded Redis URL in production and TLS when supported (rediss://).

Advanced

- Scale workers by increasing `replicas` (or run multiple worker services) and use named queues to separate workloads (e.g., `rq worker ai_jobs default`).
- Monitor RQ using rq-dashboard (pip install rq-dashboard) but keep admin UI behind auth or internal network.

If you want, I can also add a Procfile and a systemd unit example for deploying workers on a VM or Heroku. Let me know.