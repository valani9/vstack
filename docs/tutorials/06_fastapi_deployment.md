# Tutorial 06 — The vstack FastAPI server

The `vstack-api` server exposes the same 34 patterns + the
cross-pattern `/v1/diagnose` runner as a production-hardened HTTP
service. v0.6.0 added auth + rate limiting + size enforcement +
async path + CORS + observability; v0.18.0 added the
`/v1/diagnose` endpoint.

## Install

```bash
pip install valanistack[anthropic]
```

Verify:

```bash
vstack-api --version
# vstack-api 0.18.1
```

## Run

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
vstack-api --host 0.0.0.0 --port 8000
```

The server speaks HTTP/1.1 + JSON. OpenAPI spec at
`http://localhost:8000/openapi.json`, interactive docs at
`/docs`.

## Endpoints

### Health

- `GET /healthz` — liveness probe, always returns 200 if the
  process is alive.
- `GET /readyz` — readiness probe, returns 503 during startup /
  graceful shutdown.
- `GET /livez` — alias for `/healthz`.

### Catalog

- `GET /v1/patterns` — list of 34 patterns (name + summary + URLs).
- `GET /v1/patterns/{name}` — pattern detail.
- `GET /v1/patterns/{name}/citations` — literature anchors.
- `GET /v1/patterns/{name}/playbooks` — failure-mode playbooks.
- `GET /v1/patterns/{name}/composition` — composition manifest.

### Per-pattern analysis

- `POST /v1/analyze/{name}` — run one pattern.

Body:

```json
{
  "trace": {"goal": "...", "steps": [], "outcome": "...", "success": false},
  "mode": "standard",
  "model": "claude-sonnet-4-6"
}
```

Response (success):

```json
{
  "pattern": "lewin",
  "mode": "standard",
  "model": "claude-sonnet-4-6",
  "detection": { ... pattern-specific Pydantic model ... },
  "cached": false
}
```

### Cross-pattern `/v1/diagnose` (v0.18.0+)

- `POST /v1/diagnose` — run the cross-pattern runner.

Body:

```json
{
  "trace": {"goal": "...", "steps": [], "outcome": "...", "success": false},
  "shape": "individual",       // optional
  "recipe": "stuck_in_loop",   // optional; mutex with `patterns`
  "patterns": ["lewin", "aar"], // optional; mutex with `recipe`
  "mode": "standard",
  "model": "claude-sonnet-4-6",
  "cache": true,
  "top": 5
}
```

Response:

```json
{
  "shape": "individual",
  "findings": [
    {
      "pattern": "lewin",
      "severity": "high",
      "title": "environmental locus 0.78",
      "evidence": "stale RAG returned 2003 wiki revision",
      "intervention": "refresh RAG index nightly"
    },
    ...
  ],
  "per_pattern": [
    {"pattern": "lewin", "n_findings": 3, "elapsed_seconds": 4.2, "error": null},
    ...
  ],
  "errors": {},
  "cost": {
    "llm_calls": 12,
    "input_tokens": 4500,
    "output_tokens": 1200,
    "total_tokens": 5700,
    "elapsed_ms": 8200,
    "by_pattern": { ... },
    "by_model": { ... }
  },
  "cache_stats": {
    "hits": 3,
    "misses": 9,
    "inserts": 9,
    "hit_rate": 0.25
  }
}
```

## Authentication

vstack-api uses API-key auth keyed on the `X-API-Key` header. Off
by default (loopback-friendly). To enable:

```bash
export VSTACK_API_KEYS="key1=alice,key2=bob"
vstack-api --require-auth
```

Or read keys from a file:

```bash
export VSTACK_API_KEYS_FILE=/etc/vstack/keys.json
vstack-api --require-auth
```

## Rate limiting

Configured via env vars:

```bash
export VSTACK_API_RATE_LIMIT_PER_KEY="100/minute"
export VSTACK_API_RATE_LIMIT_PER_IP="50/minute"
```

Returns `429 Too Many Requests` with a `Retry-After` header when
exceeded.

## Request size limits

```bash
export VSTACK_API_MAX_BODY_BYTES=262144         # 256 KiB
export VSTACK_API_MAX_TRACE_STEPS=500
export VSTACK_API_REQUEST_TIMEOUT_SECONDS=60
```

Body size is checked at the middleware layer (rejected with 413
before Pydantic sees it).

## Caching

The `/v1/analyze/{name}` endpoint uses a content-addressable cache
keyed on `(pattern, mode, model, trace_hash)`. The cache backend is
configurable:

```bash
# In-memory (default; per-process)
export VSTACK_API_CACHE_BACKEND=memory

# Redis
export VSTACK_API_CACHE_BACKEND=redis
export VSTACK_API_REDIS_URL=redis://localhost:6379/0

# No cache
export VSTACK_API_CACHE_BACKEND=none
```

The `/v1/diagnose` endpoint accepts a `cache` request body field
that controls the *runner-level* shared cache (different from the
response-level cache above).

## Observability

The server emits structured JSON logs and exposes Prometheus
metrics at `/metrics`:

- `vstack_api_request_duration_seconds{surface, pattern, mode, status}`
- `vstack_api_requests_total{surface, pattern, mode, status}`
- `vstack_api_pattern_errors_total{pattern, error_kind}`

Optional Sentry integration:

```bash
export SENTRY_DSN="https://..."
vstack-api
```

The `X-Request-ID` header round-trips automatically; if the caller
provides one, it's logged + echoed back; otherwise a UUID is
generated.

## CORS

Configured via:

```bash
export VSTACK_API_CORS_ALLOW_ORIGINS="https://app.example.com,https://staging.example.com"
```

Defaults to no CORS allowance (same-origin only).

## Deploying to production

The server is a standard FastAPI app — deploy as you would any
FastAPI service:

- **Uvicorn** for single-process: `uvicorn vstack.api._app:app`
- **Gunicorn + Uvicorn workers** for multi-process:
  `gunicorn vstack.api._app:app -w 4 -k uvicorn.workers.UvicornWorker`
- **Behind a reverse proxy** (nginx, Caddy, Envoy) for TLS + HTTP/2.
- **In Kubernetes** with the included Dockerfile + Helm chart
  (under `_docker/` and `_charts/` in the source repo).

## Graceful shutdown

vstack-api drains in-flight requests on SIGTERM. The readiness
probe flips to `draining` so a Kubernetes service stops sending
traffic before the process exits. Default drain window is 30
seconds; tune via `VSTACK_API_DRAIN_TIMEOUT_SECONDS`.

## See also

- `_api/lib/_app.py` source for the application factory
- v0.18.0 changelog for the `/v1/diagnose` endpoint details
- v0.6.0 changelog for the production-hardening additions
- Tutorial 05 for the MCP variant of the same surface
