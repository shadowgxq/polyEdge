# Railway deployment

This project is a monorepo with separate frontend and backend services. Deploy it on Railway as four services:

- `backend`: root directory `/backend`, Dockerfile deploy.
- `frontend`: root directory `/frontend`, Dockerfile deploy.
- `Postgres`: Railway PostgreSQL plugin.
- `Redis`: Railway Redis plugin.

Railway reads each service's `railway.toml` from that service root.

## 1. Create services

In Railway, create a new project from `shadowgxq/polyEdge`.

Add:

- PostgreSQL
- Redis
- backend service from the GitHub repo, root directory `/backend`
- frontend service from the GitHub repo, root directory `/frontend`

Generate a public domain for `backend` and `frontend`.

## 2. Backend variables

Set these on the `backend` service:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<replace-with-a-strong-random-value>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MARKET_PREFETCH_INTERVAL_SECONDS=30
MARKET_PREFETCH_BATCH_LIMIT=100
MARKET_REFRESH_THROTTLE_SECONDS=30
EVENT_LIST_PAGE_SIZE=20
RANKING_TOP_N=10
EVENT_SEARCH_LIMIT=10
REALTIME_RATE_LIMIT_WINDOW=60
REALTIME_RATE_LIMIT_MAX=30
```

Do not set `PORT`; Railway injects it.

## 3. Frontend variables

Set this on the `frontend` service:

```env
BACKEND_UPSTREAM=https://<backend-domain>.railway.app
```

The browser calls same-origin `/api/...`; the frontend Nginx proxies it to `BACKEND_UPSTREAM`.

## 4. Verify

Backend:

```bash
curl https://<backend-domain>.railway.app/health
curl "https://<backend-domain>.railway.app/api/v1/events?category=hot&page=1"
```

Frontend:

```bash
open https://<frontend-domain>.railway.app
```

If events are empty but the API returns `{ "code": 0 }`, check backend logs for upstream access to `gamma-api.polymarket.com`.
