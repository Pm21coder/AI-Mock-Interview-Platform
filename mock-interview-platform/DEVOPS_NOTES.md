Production configuration notes

- Rate limiting: Set RATE_LIMIT_STORAGE_URI to a Redis URI (e.g. redis://redis:6379/0) to avoid in-memory limiter and make rate limits persistent across workers.
- Example env:
  RATE_LIMIT_STORAGE_URI=redis://localhost:6379/0

- Secrets: do not commit .env with real secrets. Use a secrets manager or GitHub Actions secrets. Add .env to .gitignore (already present).

- CORS: set CORS_ORIGINS to the production frontend origin(s).
