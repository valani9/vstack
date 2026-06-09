# Operations — Troubleshooting

> Common production issues and their resolutions. Diagnoses are
> ordered from most-common to least-common.

---

## Findings quality is low

### Symptom 1: Many low-confidence findings

Cause: LLM is uncertain — usually because the trace is incomplete.

Fix:
- Ensure trace has all fields the pattern expects (see pattern's
  schema).
- Run in `forensic` mode for higher confidence.
- Switch to a flagship model if using a smaller model.

### Symptom 2: All findings same severity

Cause: Severity calibration drifted — usually after a model update.

Fix:
- Re-fit the calibration curve against a held-out eval set:
  ```python
  from vstack.lewin import fit_calibration_curve, load_eval_set
  eval_set = load_eval_set("eval/lewin-2026-Q2.yaml")
  curve = fit_calibration_curve(eval_set)
  save_calibration_curve(curve, "calibrations/lewin-2026-Q2.json")
  ```

### Symptom 3: Findings don't match human intuition

Cause: Wrong pattern for the failure mode.

Fix:
- Use the recipe router: `vstack-recipes match "your symptom"`.
- Re-read the pattern's WALKTHROUGH "When to reach for this
  pattern" section.

---

## Cost is too high

### Symptom 1: Hourly cost spike

Cause: Either request volume rose or a client is recursing.

Fix:
- Check `vstack_requests_total` rate per client.
- Rate-limit the offending client.
- Check `vstack_errors_total` for retry loops.

### Symptom 2: Cost per call is high

Cause: Forensic mode used unnecessarily.

Fix:
- Switch default to quick mode.
- Use adaptive escalation (see SLA doc).

### Symptom 3: One pattern dominates cost

Cause: That pattern's bundle entry runs on every call.

Fix:
- Use a smaller per-pattern bundle:
  ```python
  diagnose(trace=trace, patterns=["lewin", "aar"])
  ```
- Switch to a cheaper model for that pattern only.

---

## Latency is too high

### Symptom 1: p99 latency spike

Cause: LLM provider slow or pattern uses forensic mode.

Fix:
- Check provider status page.
- Reduce mode if forensic was used.
- Increase `timeout=` to surface clearer error.

### Symptom 2: All patterns slow

Cause: vstack-api saturated or LLM provider rate-limited.

Fix:
- Scale vstack-api horizontally.
- Reduce inbound rate limit.
- Switch to async mode (Tutorial 9).

---

## Errors

### Error: `ValidationError: trace.steps required`

Cause: Trace JSON is missing required field.

Fix: Provide all required fields. Use the schema:

```python
from vstack.aar import AgentTrace
schema = AgentTrace.model_json_schema()
print(schema)
```

### Error: `RateLimitError`

Cause: LLM provider rate-limited the client.

Fix:
- Reduce request rate.
- Switch to backup provider via `FailoverClient`.
- Wait for rate window to clear.

### Error: `AuthenticationError`

Cause: API key invalid or expired.

Fix:
- Verify `VSTACK_ANTHROPIC_API_KEY` (or `VSTACK_OPENAI_API_KEY`).
- Check key is provisioned at the provider.
- Check the key isn't expired.

### Error: `InvalidRequestError: content too long`

Cause: Trace exceeds the model's context window.

Fix:
- Reduce trace size: drop unnecessary steps.
- Use a model with larger context.
- Run `Yerkes-Dodson` first to confirm context-load issue.

### Error: `ServerError 500: Internal Server Error` from provider

Cause: Transient LLM-side error.

Fix:
- Automatic retry should handle this.
- If persistent, check provider status.
- If sustained, switch primary provider.

---

## Dashboard issues

### Dashboard returns empty

Cause: No reports submitted yet, or store flushed.

Fix:
- Submit a report via `POST /v1/reports`.
- If persistence configured, check the store path.

### Charts not rendering

Cause: Tailwind/Chart.js CDN unreachable.

Fix:
- Pass `bundle_assets=True` to `DashboardConfig`.
- Self-host Tailwind/Chart.js and point the dashboard at the local
  copy.

### Dashboard crashes on big reports

Cause: Report exceeds in-memory size.

Fix:
- Reduce trace size before submitting.
- Use streaming render mode for large reports.

---

## MCP issues

### Tool not appearing in Claude Desktop

Cause: Config file not picked up.

Fix:
1. Verify path: `~/Library/Application Support/Claude/claude_desktop_config.json`.
2. Check JSON syntax with `jq < path/to/config`.
3. Fully restart Claude Desktop (not just close window).
4. Check Claude Desktop's developer console for MCP errors.

### Tool errors with "command not found"

Cause: `vstack-mcp` not in PATH.

Fix:
- Use absolute path in config: `/usr/local/bin/vstack-mcp`.
- Or pin to the venv: `~/projects/myproject/.venv/bin/vstack-mcp`.

### Tool errors with auth failure

Cause: LLM API key not in env.

Fix:
- Add to `env:` block in claude_desktop_config.json:
  ```json
  {
    "vstack": {
      "command": "vstack-mcp",
      "args": ["stdio"],
      "env": {"VSTACK_ANTHROPIC_API_KEY": "sk-..."}
    }
  }
  ```

---

## Framework adapter issues

### LangChain adapter: tool names mismatched

Cause: LangChain tool names have framework prefix.

Fix: Use `tool_name_map=` on the adapter.

### CrewAI adapter: manager decisions missing

Cause: `include_manager_decisions=False` (default).

Fix: Pass `include_manager_decisions=True`.

### AutoGen adapter: messages out of order

Cause: AutoGen GroupChat doesn't preserve absolute order in all
modes.

Fix: Use the `preserve_order=True` flag on the adapter, which
forces a re-sort by timestamp.

---

## See also

- Operations: runbook
- Operations: SLA-and-budgets
- Tutorial 10: Observability
