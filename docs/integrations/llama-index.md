# LlamaIndex Integration Playbook

> Goal: integrate vstack diagnostics into LlamaIndex agent and
> retrieval-augmented pipelines. Covers the LlamaIndex adapter,
> RAG-specific failure modes, and the 8 patterns most useful in
> retrieval-heavy workloads.

---

## When to use vstack with LlamaIndex

LlamaIndex is the canonical framework for retrieval-augmented
agents. The integration sweet spot:

- A RAG pipeline is returning confidently-wrong answers (stale
  index, wrong chunks).
- A multi-step LlamaIndex agent is dropping retrieval context
  between steps.
- A query engine is over-retrieving (latency cost) or under-
  retrieving (incompleteness).
- A multi-agent setup using LlamaIndex agents is failing at
  coordination.

---

## Install

```bash
pip install valanistack llama-index-core llama-index-llms-anthropic
```

---

## Quick start — diagnose a LlamaIndex query

```python
from llama_index.core import VectorStoreIndex, Document
from llama_index.llms.anthropic import Anthropic

from vstack.adapters.llama_index_adapter import llama_index_to_agent_trace
from vstack import diagnose

# Standard LlamaIndex setup.
documents = [Document(text=t) for t in raw_texts]
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(llm=Anthropic(model="flagship"))

# Run a query and capture.
response = query_engine.query("What's the deployment policy?")

# Convert to vstack trace.
trace = llama_index_to_agent_trace(
    response=response,
    goal="Answer user's deployment policy question.",
)

# Diagnose.
report = diagnose(trace=trace, llm_client=llm)
print(report.to_markdown())
```

---

## Patterns most useful for LlamaIndex

### 1. Lewin (`#01`)

When a RAG answer is wrong, was it the model (internal) or the
retrieval (environmental)? Lewin is the canonical first call —
the OVERTURNS verdict typically points to a stale index.

### 2. Motivation Traps (`#09`)

LlamaIndex agents often over-retrieve because the eval metric
rewards "more sources." Motivation Traps surfaces the trap.

### 3. Yerkes-Dodson (`#06`)

Long retrieval contexts saturate the agent. Yerkes-Dodson
identifies the saturation point.

### 4. Trust Triangle (`#18`)

When the agent's claim doesn't match the retrieved evidence,
Authenticity leg breaks.

### 5. Johari (`#03`)

The agent's claimed capability (answer Q from corpus) vs actual
behaviour. BLIND SPOT failures are common in RAG.

### 6. Stone-Heen Triggers (`#22`)

When users push back on wrong RAG answers, Truth-trigger rejection
is common. Stone-Heen identifies which trigger fired.

### 7. SMART Goal Generator (`#24`)

RAG goals are often vague ("answer the question"). SMART rewrites
into measurable form ("answer with verified citation from the
indexed corpus").

### 8. AAR (`#30`)

Per-query retro for failure analysis.

---

## Trace capture from LlamaIndex

### Query engines

```python
response = query_engine.query("...")
trace = llama_index_to_agent_trace(response=response, goal="...")
```

### Chat engines

```python
response = chat_engine.chat("...")
trace = llama_index_to_agent_trace_chat(response=response, goal="...")
```

### Agents (ReAct, OpenAI agent, etc.)

```python
response = agent.chat("...")
trace = llama_index_to_agent_trace_agent(response=response, goal="...")
```

### Multi-step queries (sub-question generator)

The sub-question generator produces a tree of queries. The adapter
captures each leaf:

```python
response = sub_question_engine.query("...")
trace = llama_index_to_agent_trace(
    response=response,
    goal="...",
    capture_sub_questions=True,
)

# For tree-shape diagnostics, run as team trace.
team_trace = llama_index_to_team_trace(response=response, goal="...")
team_report = diagnose(trace=team_trace, llm_client=llm)
```

---

## RAG-specific diagnostics

### Retrieval relevance audit

When the answer is wrong, vstack can run a retrieval-relevance
audit before the model audit:

```python
from vstack.adapters.llama_index_adapter import audit_retrieval_relevance

relevance = audit_retrieval_relevance(
    response=response,
    user_query="...",
    expected_answer="...",
)

if relevance.score < 0.5:
    # Retrieval failed — don't blame the model.
    # Reindex or change retrieval mode.
    pass
else:
    # Retrieval was good — model failed.
    # Run Lewin to confirm.
    pass
```

### Citation verification

```python
from vstack.adapters.llama_index_adapter import audit_citations

bad_citations = audit_citations(
    response=response,
    citation_resolver=resolve_doi,
)

if bad_citations:
    # Citation trap detected. Run Motivation Traps for the full diagnosis.
    pass
```

### Index drift audit

When a RAG fleet's quality silently degrades over time:

```python
from vstack.adapters.llama_index_adapter import audit_index_drift

drift = audit_index_drift(
    index=index,
    baseline_index_id="2026-Q1-baseline",
    sample_queries=[...],
)

if drift.coverage_dropped:
    # Re-index needed.
    pass
```

---

## Common LlamaIndex pathologies

### Stale-index answer

The agent returns a confident answer from an outdated chunk.

Run: **Lewin** (forensic mode) + **Motivation Traps**.

Common fix: re-index + add freshness filter.

### Over-retrieval

The agent retrieves 50 chunks for a simple question.

Run: **Motivation Traps** + **Yerkes-Dodson** + **Grant Strengths
overplayed**.

Common fix: top-k bound + relevance threshold.

### Citation fabrication

The agent's answer cites sources that don't appear in the
retrieved chunks.

Run: **Motivation Traps** (citation trap) + **Hallucination
Cascade recipe**.

Common fix: enforce citation = chunk_id via post-validator.

### Chat memory drift

In multi-turn chat engines, the agent loses earlier context.

Run: **Yerkes-Dodson** + **SDT relatedness**.

Common fix: tighter memory window + explicit user-state carry.

---

## Production wiring

```python
from llama_index.core.query_engine import BaseQueryEngine
from vstack.adapters.llama_index_adapter import llama_index_to_agent_trace
from vstack import diagnose
from vstack.aar import AARAnalyzer
from vstack.dashboard import render_report

def diagnosed_query(query_engine: BaseQueryEngine, query: str, goal: str):
    response = query_engine.query(query)
    trace = llama_index_to_agent_trace(response=response, goal=goal)

    report = diagnose(trace=trace, llm_client=llm)

    if any(f.severity == "high" for f in report.findings):
        aar = AARAnalyzer(llm).run(trace, prior_findings=report.findings)
        persist_lesson(aar.lessons)

    html = render_report(report)
    write_html_report(html)

    return response
```

---

## See also

- LangChain integration: [`langchain.md`](./langchain.md)
- Pydantic-AI integration: [`pydantic-ai.md`](./pydantic-ai.md)
- RAG cookbook: `examples/cookbook/04_hallucination_cascade.py`
