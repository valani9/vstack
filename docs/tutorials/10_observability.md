# Tutorial 10 — Observability and Cost Tracking

> Goal: instrument vstack diagnostics for production observability.
> Covers structured logging, OpenTelemetry tracing, Prometheus
> metrics, and cost dashboards.

---

## Part 1 — Structured logging

vstack emits structured JSON logs at every meaningful event. Each
log line carries a `run_id` for correlation across a single
trace's analysis.

```python
import logging
import sys

# Configure JSON logging.
import json
from logging import LogRecord


class JsonFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        log = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        # Pick up the structured extras.
        for k, v in record.__dict__.items():
            if k.startswith("vstack_"):
                log[k] = v
        return json.dumps(log)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.getLogger("vstack").addHandler(handler)
logging.getLogger("vstack").setLevel(logging.INFO)
```

### Log structure

Every log line includes:
- `ts` — ISO timestamp.
- `level` — INFO / WARNING / ERROR.
- `vstack_run_id` — correlation ID for the analysis run.
- `vstack_pattern` — pattern name (e.g., "lewin").
- `vstack_mode` — analysis mode (quick / standard / forensic).

Cost-event logs add:
- `vstack_cost_tokens_in` / `vstack_cost_tokens_out`
- `vstack_cost_usd`
- `vstack_llm_provider`
- `vstack_llm_model`

---

## Part 2 — Prometheus metrics

The FastAPI server exposes Prometheus metrics at `/metrics`:

```bash
vstack-api serve --port 7777

curl http://localhost:7777/metrics
```

### Metrics surface

| Metric                                  | Type      | Labels                          |
|-----------------------------------------|-----------|---------------------------------|
| `vstack_requests_total`                 | counter   | pattern, mode, status_code      |
| `vstack_request_duration_seconds`       | histogram | pattern, mode                   |
| `vstack_llm_calls_total`                | counter   | provider, model                 |
| `vstack_llm_tokens_total`               | counter   | provider, model, direction      |
| `vstack_llm_cost_usd_total`             | counter   | provider, model                 |
| `vstack_findings_total`                 | counter   | pattern, severity               |
| `vstack_errors_total`                   | counter   | pattern, error_class            |

### Grafana dashboard

A sample Grafana dashboard JSON is bundled under
`docs/operations/grafana-dashboard.json`. Import via Grafana UI
or via API:

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/operations/grafana-dashboard.json \
  $GRAFANA/api/dashboards/db
```

Panels included:
- Request rate per pattern.
- p50 / p95 / p99 latency per pattern.
- Cost by provider + model.
- Error rate per pattern + class.
- Finding severity distribution.

---

## Part 3 — OpenTelemetry integration

For distributed tracing, integrate with OpenTelemetry:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

trace.set_tracer_provider(TracerProvider())
exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))


# vstack auto-detects OpenTelemetry and emits spans:
from vstack import diagnose
from vstack.aar.clients import AnthropicClient

# Each diagnose() call emits a parent span; each pattern emits a child span.
report = diagnose(trace=agent_trace, llm_client=AnthropicClient())
```

### Span attributes

Each vstack span carries:
- `vstack.pattern` — pattern name.
- `vstack.mode` — analysis mode.
- `vstack.run_id` — correlation ID.
- `vstack.severity` — top finding's severity.
- `vstack.llm.tokens_in` / `vstack.llm.tokens_out`.
- `vstack.llm.provider` / `vstack.llm.model`.
- `vstack.llm.cost_usd`.

### Trace structure

```
diagnose (span)
  ├── lewin (span)
  │   ├── llm_call (span)
  │   └── llm_call (span)
  ├── goleman_ei (span)
  └── aar (span)
```

---

## Part 4 — Cost dashboards

### Per-day cost tracking

```python
from vstack.aar import get_cost_summary, reset_cost_summary

# At day boundary:
summary = get_cost_summary()
persist_daily_cost(date=today, summary=summary)
reset_cost_summary()
```

### Per-pattern cost attribution

```python
from vstack.aar import get_cost_by_pattern

per_pattern = get_cost_by_pattern()
for pattern, cost in per_pattern.items():
    print(f"{pattern}: ${cost.total_usd:.2f}")
```

### Cost alerts

```python
def check_cost_alert():
    summary = get_cost_summary()
    if summary.total_cost > DAILY_BUDGET:
        send_alert(f"Daily vstack cost exceeded: ${summary.total_cost:.2f}")
```

Wire into a cron job or a midnight tick.

---

## Part 5 — Sampling for high-volume

At 1M+ traces per day, you don't need to diagnose every one.

### Strategy 1: random sampling

```python
import random

def maybe_diagnose(trace, sample_rate: float = 0.01):
    if random.random() < sample_rate:
        return diagnose(trace=trace, llm_client=llm)
    return None
```

### Strategy 2: failure-only diagnostic

```python
def diagnose_on_failure(trace):
    if not trace.success:
        return diagnose(trace=trace, llm_client=llm)
    return None
```

### Strategy 3: tail sampling (recommended for production)

```python
import random


def diagnose_tail(trace, fail_sample_rate: float = 1.0, success_sample_rate: float = 0.01):
    """Diagnose 100% of failures + 1% of successes."""
    rate = fail_sample_rate if not trace.success else success_sample_rate
    if random.random() < rate:
        return diagnose(trace=trace, llm_client=llm)
    return None
```

Tail sampling maximizes coverage of the *interesting* traces
(failures) while keeping cost bounded.

### Strategy 4: severity-triggered upsampling

```python
def diagnose_adaptive(trace):
    """Run quick mode on everything; upgrade to standard mode if
    findings exist; upgrade to forensic if severity high.
    """
    # Quick mode is cheap.
    quick = diagnose(trace=trace, llm_client=llm, mode="quick")

    if not quick.findings:
        return quick

    # Has findings — re-run in standard mode.
    standard = diagnose(trace=trace, llm_client=llm, mode="standard")

    if any(f.severity == "high" for f in standard.findings):
        # High severity — escalate to forensic.
        return diagnose(trace=trace, llm_client=llm, mode="forensic")

    return standard
```

This is the recommended production strategy. Quick mode is cheap
enough to run on everything; forensic mode is expensive enough
that you only want to pay for it when the signal is strong.

---

## Part 6 — Alerting

### High-severity finding alerts

```python
def diagnose_with_alerts(trace, alert_fn):
    report = diagnose(trace=trace, llm_client=llm)

    high = [f for f in report.findings if f.severity == "high"]
    if high:
        alert_fn(
            title=f"High-severity vstack findings ({len(high)})",
            findings=high,
            trace_id=trace.id,
        )

    return report
```

### Drift alerts

```python
def check_baseline_drift(report, baseline):
    drift = compare_to_baseline(report, baseline)
    if drift.is_regression:
        alert(
            title="vstack drift detected",
            kind=drift.regression_kind,
            from_=drift.from_state,
            to=drift.to_state,
        )
```

### Cost alerts

```python
def check_cost_threshold():
    summary = get_cost_summary()
    if summary.hourly_rate > COST_RATE_THRESHOLD:
        alert(f"vstack hourly cost rate: ${summary.hourly_rate:.2f}/hr")
```

---

## See also

- Tutorial 6: FastAPI deployment
- Tutorial 7: Dashboard deployment
- Operations docs: `docs/operations/`
- Cost source: `_aar/lib/_cost_tracking.py`
