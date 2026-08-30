# parserapp — LinkedIn Profile Parser API

A FastAPI service that fetches structured LinkedIn profile data and exposes it
through a simple HTTP API. Designed to deploy on Render (free plan supported).

## Endpoints

### `GET /health`
Health check (no API key required). Returns whether the LinkedIn session is valid.

```
curl https://<service>.onrender.com/health
```

### `GET /api/profile?username=<username>`
Fetches a LinkedIn profile by vanity name or full profile URL. **Requires an API key.**

```
curl -H "X-API-Key: <your-api-key>" \
     "https://<service>.onrender.com/api/profile?username=satyanadella"
```

Interactive docs (Swagger UI): `https://<service>.onrender.com/docs`

## Deploying on Render

1. Push this repository to GitHub.
2. On Render, create a **New Web Service** and connect the repo.
3. Render uses `render.yaml` automatically: Python runtime,
   `pip install -r requirements.txt`, and start command
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Set the following environment variables on the service
   (never commit these to the repo — the `.env` file is gitignored):

   | Variable        | Purpose                                                                |
   |-----------------|------------------------------------------------------------------------|
   | `LI_AT`         | LinkedIn session cookie `li_at` (primary working auth)                 |
   | `JSESSIONID`    | LinkedIn session cookie `JSESSIONID` (used with `LI_AT`)               |
   | `API_KEYS`      | Comma-separated keys required to call `/api/profile`                   |
   | `LI_EMAIL`      | (Optional) LinkedIn email for auto-login fallback                      |
   | `LI_PASSWORD`   | (Optional) LinkedIn password for auto-login fallback                   |
   | `CACHE_TTL`     | (Optional) Response cache TTL in seconds (default 1800)                |
   | `RATE_LIMIT`    | (Optional) Requests per minute per client (default 10)                 |

5. Click **Create Web Service**. Render provisions an HTTPS URL automatically
   (`https://<service>.onrender.com`).

> **Note on LinkedIn cookies:** `LI_AT`/`JSESSIONID` are live session cookies.
> If the session is flagged from a new server IP or expires, requests return
> `502 Bad Gateway`. Refresh the cookie from a logged-in browser and update the
> env var to restore service.

## Local development

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your values
uvicorn app.main:app --reload
```
