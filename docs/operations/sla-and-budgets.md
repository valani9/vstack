# Operations — SLAs and Budgets

> Recommended SLAs and budget framework for production vstack
> deployments. Calibrated against typical agent-fleet usage.

---

## Latency SLAs

### Per-pattern, quick mode

| Pattern            | p50    | p95    | p99    |
|--------------------|--------|--------|--------|
| Lewin              | 800ms  | 2.0s   | 4.0s   |
| Goleman EI         | 800ms  | 2.0s   | 4.0s   |
| Johari             | 800ms  | 2.0s   | 4.0s   |
| DANVA              | 600ms  | 1.6s   | 3.5s   |
| Yerkes-Dodson      | 800ms  | 2.0s   | 4.0s   |
| HEXACO             | 700ms  | 1.8s   | 3.8s   |
| Trust Triangle     | 800ms  | 2.0s   | 4.0s   |
| AAR                | 1.0s   | 2.5s   | 5.0s   |

### Per-pattern, standard mode

Approximately 2x quick mode (2 LLM calls).

### Per-pattern, forensic mode

Approximately 4-5x quick mode (4 LLM calls).

### `/v1/diagnose` (default bundle, 6 patterns)

- Quick mode: p50 1.5s / p95 4s / p99 8s.
- Standard mode: p50 3s / p95 8s / p99 15s.
- Forensic mode: p50 8s / p95 20s / p99 35s.

(Parallel mode reduces these by ~3x.)

---

## Latency optimization tips

1. **Use quick mode by default.** Reserve standard/forensic for
   high-severity follow-up.
2. **Async fan-out.** See Tutorial 9.
3. **Caching.** Identical prompts get cached responses; configure
   `VSTACK_CACHE_TTL_SECONDS`.
4. **Use the closest LLM provider region.** Cross-region latency
   dominates.
5. **Reduce default bundle size.** Default has 6 patterns; drop to
   3 for fast triage.

---

## Cost budgets

### Recommended monthly budgets by scale

| Fleet size           | Monthly budget   | Recommended mode | Sampling   |
|----------------------|------------------|------------------|------------|
| < 10 agents          | $100             | Forensic everywhere | 100%      |
| 10-100 agents        | $500             | Standard everywhere | 100%      |
| 100-1,000 agents     | $2,000           | Quick + standard on failures | 100%  |
| 1,000-10,000 agents  | $10,000          | Quick + forensic on failures | 30%   |
| 10,000+ agents       | $40,000          | Tail sampling                | 10%   |

### Budget breakdown (1,000-agent fleet, $2,000/month)

Assuming ~50,000 traces/month at $0.04/trace average:

- LLM cost: $2,000.
- Self-hosted infrastructure: $200 (1 small instance for
  vstack-api + dashboard).
- LLM provider markup: 0 (direct API).
- Total: $2,200/month.

### Per-call budget enforcement

```python
from vstack import diagnose
from vstack.aar import get_call_cost_estimate

estimate = get_call_cost_estimate(
    pattern="lewin",
    mode="standard",
    trace_size_tokens=2000,
)

if estimate > MAX_PER_CALL_COST:
    # Use quick mode instead.
    report = diagnose(trace=trace, mode="quick")
else:
    report = diagnose(trace=trace, mode="standard")
```

---

## Sampling strategies

### Strategy 1: All failures + 1% successes (recommended)

```python
def should_diagnose(trace):
    if not trace.success:
        return True
    return random.random() < 0.01
```

Cost reduction: ~50x vs sampling everything.
Coverage: 100% of failures, 1% of successes (for drift detection).

### Strategy 2: Quick mode everything, upgrade selectively

```python
def diagnose_adaptive(trace):
    # Cheap quick mode on everything.
    report = diagnose(trace=trace, mode="quick")

    # Upgrade on any finding.
    if report.findings:
        report = diagnose(trace=trace, mode="standard")

        if any(f.severity == "high" for f in report.findings):
            # Upgrade further on high severity.
            report = diagnose(trace=trace, mode="forensic")

    return report
```

Cost: roughly 2x quick mode (since most traces don't escalate).
Coverage: 100% of all traces at quick mode baseline.

### Strategy 3: Drift-detection only

```python
# Run vstack only periodically against a fixed sample.
# Most traces: skip.
# Sampled traces: full diagnosis + drift check.

def should_diagnose(trace, hour: int):
    if hour % 6 == 0 and random.random() < 0.05:
        return True
    return False
```

Cost: minimal.
Coverage: drift detection without per-trace overhead.

---

## Service availability SLAs

### Recommended SLOs

| Surface             | Availability target | Latency target (p99) |
|---------------------|---------------------|----------------------|
| `vstack-api`        | 99.9%               | < 10s                |
| `vstack-dashboard`  | 99.5%               | < 5s                 |
| `vstack-mcp` (stdio)| N/A (in-process)    | < 5s                 |
| `vstack-mcp` (http) | 99.9%               | < 10s                |

### Downtime budget

- 99.9% allows 43 minutes/month of downtime.
- 99.5% allows 3.6 hours/month.

Most vstack downtime is *external* — LLM provider outages. Plan
for multi-provider failover if your SLA requires < 99% LLM-side.

---

## Multi-provider failover

```python
from vstack.aar.clients import AnthropicClient, OpenAIClient, FailoverClient

primary = AnthropicClient()
backup = OpenAIClient()
client = FailoverClient(primary=primary, backup=backup, threshold=3)

# Use as any client:
from vstack.lewin import LewinAttributionDetector
detector = LewinAttributionDetector(client)
```

The `FailoverClient` switches to backup after `threshold` consecutive
failures of the primary, and switches back when primary recovers.

---

## Capacity scaling

Single `vstack-api` replica handles ~10 req/s sync, ~50 req/s
async. Scale horizontally:

```yaml
# docker-compose.yml
services:
  vstack-api:
    image: ghcr.io/valani9/vstack:latest
    deploy:
      replicas: 4
    ports:
      - "7777:7777"
```

Front with a load balancer (HAProxy / nginx / AWS ALB). The server
is stateless; round-robin works.

### Dashboard scaling

The dashboard server is single-replica by default (reports live
in-memory). For HA:

```yaml
services:
  vstack-dashboard:
    image: ghcr.io/valani9/vstack:latest
    command: vstack-dashboard serve --port 7878
    environment:
      VSTACK_DASHBOARD_STORE: postgres
      VSTACK_DASHBOARD_DB_URL: postgresql://...
    deploy:
      replicas: 2
```

With Postgres backing store, multiple dashboard replicas share
state.

---

## See also

- Operations: runbook
- Tutorial 9: Async fan-out
- Tutorial 10: Observability
