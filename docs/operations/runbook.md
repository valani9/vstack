# Operations — Runbook

> Runbook for operating vstack in production. Covers monitoring,
> alerting, incident response, and routine maintenance.

---

## Service inventory

A typical vstack production deployment has:

- **`vstack-api`** — FastAPI HTTP server (one or more replicas).
- **`vstack-dashboard`** — FastAPI dashboard server.
- **`vstack-mcp`** — MCP servers (typically one per dev workstation
  rather than centrally hosted).
- **LLM provider** (Anthropic / OpenAI / Ollama) — external dependency.

---

## Routine monitoring

### Daily

- Check `/metrics` for cost spike:
  - `vstack_llm_cost_usd_total` rate over last 24h.
  - Alert if > 2x rolling 7-day average.
- Check `/metrics` for error spike:
  - `vstack_errors_total` rate over last 24h.
  - Alert if > 1% of `vstack_requests_total`.
- Check dashboard for high-severity findings backlog:
  - If > 100 unresolved high-severity findings, triage.

### Weekly

- Review pattern-cost distribution. If one pattern dominates, consider:
  - Switching to a cheaper model for that pattern.
  - Reducing the pattern's max-tokens.
  - Removing the pattern from the default bundle.
- Run baseline drift checks against last week's runs.
- Audit the eval suite still passes against the latest LLM model.

### Monthly

- Update Robbins-Judge fleet culture baseline.
- Update Schein assumption-layer baseline.
- Review WALKTHROUGH cross-references for broken links.
- Update LlamaIndex / LangChain adapter compatibility (frameworks
  release often).

---

## Alerts

### P1 — Service Down

Conditions:
- `/healthz` returns non-200 for > 1 min.
- `/readyz` returns non-200 for > 5 min.
- Error rate > 50% for > 2 min.

Response:
1. Page on-call.
2. Check LLM provider status (Anthropic / OpenAI status page).
3. Check container logs for stack traces.
4. Roll back to previous image if recent deploy.
5. If LLM provider down, switch primary client via env.

### P1 — Cost Spike

Conditions:
- Hourly cost > 5x rolling 7-day average.
- Single pattern cost > $100 in 1 hour.

Response:
1. Page on-call.
2. Check whether a new caller is responsible (request volume per
   client).
3. Rate-limit the offending client.
4. Check whether a specific trace is recursing (max_retries
   exceeded).

### P2 — Drift Detected

Conditions:
- Baseline drift detector reports `is_regression=True` on a
  production agent.

Response:
1. File an incident ticket.
2. Identify recent prompt / RLHF changes.
3. Run forensic mode on the agent's failing traces.
4. Decide: rollback or accept new behaviour.
5. If accept, update the baseline.

### P3 — High-severity findings rate

Conditions:
- > 10% of runs produce high-severity findings (sustained > 4
  hours).

Response:
1. Investigate the dominant finding pattern.
2. Identify upstream cause (prompt / model / scaffolding).
3. Decide on intervention.
4. Track resolution in the dashboard.

---

## Incident response runbooks

### Incident: LLM provider rate-limited

Symptoms:
- 429 errors from the LLM provider.
- Increased latency on all patterns.

Steps:
1. Check current request rate vs provider limit.
2. Reduce `VSTACK_API_RATE_LIMIT_PER_MINUTE` to throttle inbound.
3. If multi-provider, switch primary to backup.
4. Wait for rate limit window to clear.
5. Increase back to baseline rate.

### Incident: LLM provider responses degraded

Symptoms:
- Findings quality drops without code changes.
- Calibration drift detected.

Steps:
1. Run the eval suite against the current model.
2. Compare against last-week's eval result.
3. If degraded, pin the model to the previous version via
   `VSTACK_LLM_MODEL` env.
4. File incident with provider.
5. Adjust calibration curve if needed.

### Incident: Dashboard data loss

Symptoms:
- Reports missing from dashboard after restart.

Steps:
1. Check `VSTACK_DASHBOARD_STORE` setting.
2. If `memory`, reports are gone (expected on restart).
3. If `filesystem`, check the store path is mounted and writable.
4. If reports lost from filesystem, check backup.
5. Configure persistence if not already (recommended).

### Incident: vstack-api memory leak

Symptoms:
- Memory usage grows monotonically over hours.

Steps:
1. Take a heap dump (`py-spy dump --pid <pid>`).
2. Look for accumulated trace objects or LLM responses.
3. Check for unbounded caches in custom code.
4. If found, restart the service.
5. Plan a fix release with bounded cache.

---

## Routine maintenance

### Upgrade vstack

```bash
# Production:
pip install --upgrade valanistack
systemctl restart vstack-api
systemctl restart vstack-dashboard

# Verify:
curl http://localhost:7777/healthz
curl http://localhost:7878/healthz
```

Verify migration guide for breaking changes:
`docs/migrations/`.

### Update LLM provider models

```bash
# Update env var:
export VSTACK_ANTHROPIC_MODEL=anthropic-flagship-v5
systemctl restart vstack-api
```

Run the eval suite to verify findings quality on the new model:

```bash
vstack-bench run --pattern lewin --mode standard
vstack-bench run --pattern all --mode quick
```

If eval suite fails, roll back to previous model.

### Backup dashboard state

```bash
# Filesystem store:
rsync -a /var/lib/vstack-dashboard/ s3://backups/vstack-dashboard/
```

Backup daily. Restore tested quarterly.

### Rotate auth tokens

```bash
# Generate new token:
openssl rand -hex 32 > /etc/vstack/api-token.new

# Configure new token (clients): update gradually.

# Set new token:
export VSTACK_API_TOKEN=$(cat /etc/vstack/api-token.new)
systemctl restart vstack-api
```

---

## Capacity planning

### Per-pattern cost

Each pattern's per-call cost (typical):

| Pattern              | Quick mode | Standard | Forensic |
|----------------------|------------|----------|----------|
| Lewin                | $0.02      | $0.05    | $0.55    |
| Goleman EI           | $0.02      | $0.05    | $0.50    |
| Johari               | $0.02      | $0.05    | $0.45    |
| DANVA                | $0.02      | $0.05    | $0.35    |
| Yerkes-Dodson        | $0.02      | $0.05    | $0.55    |
| HEXACO               | $0.02      | $0.04    | $0.40    |
| (other individual)   | $0.02      | $0.04    | $0.40    |
| GRPI                 | $0.03      | $0.06    | $0.55    |
| Trust Triangle       | $0.03      | $0.06    | $0.55    |
| Lencioni             | $0.03      | $0.06    | $0.55    |
| (other team)         | $0.02      | $0.05    | $0.45    |
| Schein Iceberg       | $0.03      | $0.06    | $0.55    |
| Robbins-Judge        | $0.02      | $0.04    | $0.40    |
| (other org)          | $0.02      | $0.04    | $0.40    |
| AAR                  | $0.02      | $0.05    | $0.55    |

Default bundle (6 patterns) typical cost: $0.30-$3.30 depending
on mode.

### Throughput

Single `vstack-api` replica handles:
- ~10 requests/second sync.
- ~50 requests/second async with `max_concurrent=10`.

Scale horizontally for higher volume. The server is stateless.

---

## See also

- Tutorial 10: Observability
- Operations: deploy (`docs/operations/deploy.md`)
- Operations: security (`docs/operations/security.md`)
