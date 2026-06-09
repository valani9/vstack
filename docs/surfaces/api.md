# Surface — REST API (`vstack-api`)

> Production HTTP server exposing every vstack pattern + diagnose +
> recipe as REST endpoints. Built on FastAPI with auth, rate
> limiting, observability, and OpenAPI documentation.

---

## Quick start

```bash
vstack-api serve --port 7777

# Smoke test:
curl http://localhost:7777/healthz
curl http://localhost:7777/openapi.json | jq '.paths | keys'
```

The server starts in 1-2 seconds; no warm-up needed.

---

## Endpoint matrix

### Per-pattern endpoints (one per shipped pattern)

```
POST /v1/lewin             — Lewin Attribution
POST /v1/goleman-ei        — Goleman 4-Domain EI
POST /v1/johari            — Johari Window
POST /v1/danva             — DANVA Emotion Reader
POST /v1/reappraisal       — Cognitive Reappraisal
POST /v1/yerkes-dodson     — Yerkes-Dodson Workload
POST /v1/hexaco            — HEXACO Personality
POST /v1/grant             — Grant Strengths-as-Weaknesses
POST /v1/motivation-traps  — Motivation Traps
POST /v1/sdt               — SDT Intrinsic Reward
POST /v1/mcgregor          — McGregor Orchestrator Mode
POST /v1/vroom             — Vroom Expectancy
POST /v1/grpi              — GRPI Working Agreement
POST /v1/process-gain-loss — Process Gain/Loss
POST /v1/social-loafing    — Social Loafing
POST /v1/heffernan         — Heffernan Superflocks
POST /v1/lencioni          — Lencioni 5 Dysfunctions
POST /v1/trust-triangle    — Trust Triangle
POST /v1/mcallister        — McAllister Trust
POST /v1/edmondson         — Edmondson Psych Safety
POST /v1/glaser            — Glaser Conversation
POST /v1/stone-heen        — Stone-Heen Triggers
POST /v1/plus-delta        — Plus-Delta Feedback
POST /v1/smart-goal        — SMART Goal Generator
POST /v1/group-decision    — Group Decision Models
POST /v1/group-pathology   — Group Pathology
POST /v1/bias-stack        — Bias Stack
POST /v1/devils-advocate   — Devil's Advocate
POST /v1/thomas-kilmann    — Thomas-Kilmann
POST /v1/aar               — AAR Generator
POST /v1/schein            — Schein Iceberg
POST /v1/robbins-judge     — Robbins-Judge
POST /v1/org-structure     — Org Structure
POST /v1/span-of-control   — Span of Control
```

### Cross-pattern endpoint

```
POST /v1/diagnose          — Multi-pattern runner
```

### Recipe + catalog endpoints

```
GET  /v1/recipes           — List all recipes
GET  /v1/recipes/{name}    — Single recipe detail
POST /v1/recipes/match     — Free-text routing
```

### Health + observability

```
GET  /healthz              — Liveness
GET  /readyz               — Readiness (incl. LLM connectivity)
GET  /metrics              — Prometheus metrics
GET  /openapi.json         — OpenAPI schema
GET  /docs                 — Swagger UI
GET  /redoc                — ReDoc UI
```

---

## Request shape

All POST endpoints accept JSON:

```json
{
  "trace": {
    "goal": "...",
    "steps": [
      {"type": "thought", "content": "..."},
      {"type": "tool_call", "content": "..."},
      {"type": "observation", "content": "..."}
    ],
    "outcome": "...",
    "success": false
  },
  "mode": "standard",          // optional: quick | standard | forensic
  "shape": "individual"        // optional: individual | team | org
}
```

For multi-agent traces, include `agents` and `handoffs` in the trace.

For org-shape traces, use `fleet_id` + `samples`.

---

## Response shape

```json
{
  "pattern": "lewin",
  "mode": "standard",
  "shape": "individual",
  "findings": [
    {
      "severity": "high",
      "confidence": 0.82,
      "title": "...",
      "evidence": ["..."],
      "intervention": "..."
    }
  ],
  "metadata": {
    "run_id": "...",
    "duration_ms": 1234,
    "llm_calls": 2,
    "tokens_in": 1500,
    "tokens_out": 320,
    "cost_usd": 0.022
  }
}
```

---

## Diagnose endpoint

The `/v1/diagnose` endpoint runs multiple patterns at once:

```bash
curl -X POST http://localhost:7777/v1/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "trace": {...},
    "recipe": "stuck_in_loop",
    "mode": "standard"
  }'
```

Or with explicit patterns:

```bash
curl -X POST http://localhost:7777/v1/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "trace": {...},
    "patterns": ["lewin", "yerkes_dodson", "aar"]
  }'
```

Response:

```json
{
  "shape": "individual",
  "patterns_run": 4,
  "per_pattern": {
    "lewin": {...},
    "yerkes_dodson": {...},
    "motivation_traps": {...},
    "aar": {...}
  },
  "findings": [
    {"pattern": "lewin", "severity": "high", ...},
    {"pattern": "yerkes_dodson", "severity": "medium", ...},
    ...
  ],
  "errors": [],
  "metadata": {
    "total_duration_ms": 3456,
    "total_llm_calls": 8,
    "total_cost_usd": 0.087
  }
}
```

---

## Auth

Configure auth via env:

```bash
export VSTACK_API_AUTH=bearer
export VSTACK_API_TOKEN=secret-token-here
vstack-api serve
```

Modes:

| Mode    | Header                      |
|---------|----------------------------|
| `none`  | (no auth — dev only)        |
| `bearer`| `Authorization: Bearer ...` |
| `hmac`  | `X-Signature: hex-hmac`     |
| `apikey`| `X-API-Key: ...`            |

The `hmac` mode signs the request body; configure via
`VSTACK_API_HMAC_SECRET`.

---

## Rate limiting

Token-bucket per-client. Configure via env:

```bash
export VSTACK_API_RATE_LIMIT_PER_MINUTE=60
export VSTACK_API_RATE_LIMIT_BURST=10
```

Default: 60/min, burst 10. Per-client (auth subject or IP if no
auth).

Rate-limited responses return `429 Too Many Requests` with
`Retry-After` header.

---

## Observability

### Structured logs

JSON logs to stdout by default. Each request emits:

```json
{
  "ts": "2026-06-09T12:34:56Z",
  "level": "INFO",
  "msg": "request",
  "method": "POST",
  "path": "/v1/lewin",
  "status_code": 200,
  "duration_ms": 1234,
  "run_id": "...",
  "client": "...",
  "tokens_in": 1500,
  "tokens_out": 320,
  "cost_usd": 0.022
}
```

Configure log destination via standard Python logging config:

```bash
export VSTACK_API_LOG_DEST=stdout    # or syslog | file
export VSTACK_API_LOG_FILE=/var/log/vstack-api.log
```

### Prometheus metrics

`GET /metrics` returns standard Prometheus exposition format. See
[Tutorial 10](../tutorials/10_observability.md) for the full
metrics surface.

### OpenTelemetry

If `OTEL_EXPORTER_OTLP_ENDPOINT` env is set, the server auto-emits
OpenTelemetry spans:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
vstack-api serve
```

Each request emits a parent span; each pattern emits a child span.

---

## CORS

Configure CORS via env:

```bash
export VSTACK_API_CORS_ORIGINS="https://app.example.com,https://staging.example.com"
```

Default: no CORS (server-to-server only).

---

## Error handling

All errors return JSON:

```json
{
  "error": "validation_error",
  "message": "trace.steps required",
  "details": {"field": "trace.steps"},
  "run_id": "..."
}
```

Status codes:

| Code  | Class                              |
|-------|------------------------------------|
| 200   | Success                            |
| 400   | Validation error                   |
| 401   | Authentication failed              |
| 403   | Authorization failed               |
| 429   | Rate limit exceeded                |
| 500   | Internal server error              |
| 502   | LLM provider error (retryable)     |
| 503   | LLM provider unavailable           |
| 504   | LLM provider timeout (retryable)   |

---

## Production deployment

```yaml
# docker-compose.yml
version: "3.8"
services:
  vstack-api:
    image: ghcr.io/valani9/vstack:latest
    ports:
      - "7777:7777"
    environment:
      VSTACK_API_AUTH: bearer
      VSTACK_API_TOKEN: ${VSTACK_API_TOKEN}
      VSTACK_API_RATE_LIMIT_PER_MINUTE: 600
      VSTACK_ANTHROPIC_API_KEY: ${ANTHROPIC_KEY}
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7777/healthz"]
      interval: 30s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### Reverse proxy

Run behind a reverse proxy with TLS:

```nginx
upstream vstack {
    server vstack-api:7777;
}

server {
    listen 443 ssl;
    server_name vstack.example.com;
    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;

    location / {
        proxy_pass http://vstack;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
```

---

## Per-pattern endpoint reference

Each per-pattern endpoint accepts the pattern's specific trace
schema. See per-pattern WALKTHROUGH.md for the trace shape and
expected response.

---

## See also

- Tutorial 6: FastAPI deployment
- Tutorial 10: Observability
- Source: `_api/lib/`
