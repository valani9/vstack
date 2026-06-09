# Tutorial 04 — Building a custom vstack pattern

The 34 shipped patterns cover most failure modes you'll encounter,
but some scenarios are domain-specific (e.g., "my agent is making
the same kind of legal-doc redaction error across runs"). This
tutorial walks through building a new pattern from scratch and
wiring it into the diagnose runner.

## What a pattern is

A vstack pattern is a Python sub-package that exports:

1. **An input Pydantic model** describing the agent trace shape the
   pattern accepts.
2. **An output Pydantic model** describing the detection / generation
   result.
3. **A main analyzer class** with `run(trace) -> detection`.
4. **An async mirror** (optional but recommended).
5. **A prompts module** with the LLM prompts the analyzer uses.
6. **A schema module** describing detection / evidence / intervention
   classes.
7. **A playbooks module** mapping detected severity to suggested
   playbooks.
8. **A composition module** declaring which other vstack patterns
   compose well downstream / upstream.
9. **CITATIONS.md** with the literature anchors.
10. **README.md** with the user-facing docs.

The skeleton looks like this:

```
module-X-{individual|team|organization}/NN-my-pattern/
├── lib/
│   ├── __init__.py        # public surface; re-exports analyzer + schema
│   ├── _composition.py    # MY_PATTERN_COMPOSITION manifest
│   ├── _playbooks.py      # MY_PATTERN_PLAYBOOKS map
│   ├── CITATIONS.md       # literature anchors
│   ├── cli.py             # `vstack-my-pattern` CLI entry point
│   ├── clients.py         # re-exports StubClient + AnthropicClient
│   ├── generator.py       # main analyzer class
│   ├── prompts.py         # LLM prompt templates
│   └── schema.py          # Pydantic input + output models
├── tests/
│   ├── conftest.py
│   └── test_my_pattern.py
├── demo/
│   └── my_pattern_demo.py
├── README.md
└── essay.md               # narrative essay (recommended)
```

## Minimal example: a `verbosity_audit` pattern

Suppose you want a pattern that detects when an agent emits a
600-word response to a yes/no question. Here's the minimum viable
implementation.

### 1. Schema (`lib/schema.py`)

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class VerbosityTrace(BaseModel):
    """One user-agent exchange."""

    agent_id: str
    task: str
    user_question: str
    agent_response: str
    expected_answer_length: int = Field(
        default=50, description="Word count the user reasonably expected"
    )
    outcome: str = ""
    success: bool = False


class VerbosityEvidence(BaseModel):
    severity: Literal["none", "low", "medium", "high", "critical"]
    score: float = Field(ge=0.0, le=1.0)
    explanation: str
    evidence_quotes: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class VerbosityIntervention(BaseModel):
    intervention_type: Literal[
        "add_max_word_count",
        "prompt_patch_for_brevity",
        "add_length_eval",
        "new_eval",
        "human_review",
    ]
    description: str
    suggested_implementation: str
    estimated_impact: Literal["high", "medium", "low"] = "medium"
    rationale: str = ""


class VerbosityDetection(BaseModel):
    agent_id: str
    word_count: int
    expected_word_count: int
    word_count_ratio: float
    severity: Literal["none", "low", "medium", "high", "critical"]
    evidence: list[VerbosityEvidence] = Field(default_factory=list)
    interventions: list[VerbosityIntervention] = Field(default_factory=list)
```

### 2. Prompts (`lib/prompts.py`)

```python
VERBOSITY_SYSTEM_PROMPT = """You are a brevity diagnostician for AI agents.
You judge whether an agent's response was appropriately concise for
the question asked.

Grounding: Grice (1975) maxim of quantity; Brown 2018 'Dare to Lead'
on the cost of unbounded verbosity.

When asked for JSON, return JSON only. No prose around it.
"""


VERBOSITY_SCORING_PROMPT = """Score the verbosity of this exchange.

Task: {task}
User question: {user_question}
Agent response: {agent_response}
Expected answer length: {expected_word_count} words

INSTRUCTIONS:
- score in [0, 1]; 1.0 = severely verbose, 0.0 = appropriately concise
- severity per the standard 5-band scale
- evidence_quotes must be verbatim substrings of the agent response

OUTPUT SCHEMA (literal JSON object representing VerbosityEvidence):
{{
  "severity": "none" | "low" | "medium" | "high" | "critical",
  "score": <float in [0.0, 1.0]>,
  "explanation": "<1-3 sentences anchored in Grice 1975 or Brown 2018>",
  "evidence_quotes": ["<verbatim substring>", ...],
  "confidence": <float in [0.0, 1.0]>
}}

Return only the JSON object.
"""
```

### 3. Generator (`lib/generator.py`)

```python
import json

from vstack.aar import LLMClient, extract_json_object, with_retry

from .prompts import VERBOSITY_SYSTEM_PROMPT, VERBOSITY_SCORING_PROMPT
from .schema import (
    VerbosityDetection,
    VerbosityEvidence,
    VerbosityIntervention,
    VerbosityTrace,
)


class VerbosityAuditor:
    """Detects unbounded-verbosity failures in agent responses."""

    def __init__(self, llm_client: LLMClient, *, mode: str = "standard"):
        self.llm = llm_client
        self.mode = mode

    def run(self, trace: VerbosityTrace) -> VerbosityDetection:
        word_count = len(trace.agent_response.split())
        ratio = word_count / max(1, trace.expected_answer_length)

        # Cheap deterministic floor: if word_count <= expected, no LLM call.
        if ratio <= 1.2:
            return VerbosityDetection(
                agent_id=trace.agent_id,
                word_count=word_count,
                expected_word_count=trace.expected_answer_length,
                word_count_ratio=ratio,
                severity="none",
                evidence=[],
                interventions=[],
            )

        # LLM judgment
        prompt = VERBOSITY_SCORING_PROMPT.format(
            task=trace.task,
            user_question=trace.user_question,
            agent_response=trace.agent_response,
            expected_word_count=trace.expected_answer_length,
        )
        raw = with_retry(
            lambda: self.llm.complete(
                prompt=prompt, system=VERBOSITY_SYSTEM_PROMPT
            )
        )
        evidence_dict = extract_json_object(raw)
        evidence = VerbosityEvidence(**evidence_dict)

        # Intervention: a simple word-count cap on the prompt.
        intervention = VerbosityIntervention(
            intervention_type="add_max_word_count",
            description=f"Cap responses at {trace.expected_answer_length} words",
            suggested_implementation=(
                f"Append to system prompt: 'Keep responses under "
                f"{trace.expected_answer_length} words unless the user "
                f"explicitly asks for more depth.'"
            ),
            estimated_impact="high",
            rationale=f"Word count {word_count} is {ratio:.1f}x expected.",
        )

        return VerbosityDetection(
            agent_id=trace.agent_id,
            word_count=word_count,
            expected_word_count=trace.expected_answer_length,
            word_count_ratio=ratio,
            severity=evidence.severity,
            evidence=[evidence],
            interventions=[intervention],
        )
```

### 4. Public surface (`lib/__init__.py`)

```python
from .generator import VerbosityAuditor
from .schema import (
    VerbosityDetection,
    VerbosityEvidence,
    VerbosityIntervention,
    VerbosityTrace,
)

__all__ = [
    "VerbosityAuditor",
    "VerbosityDetection",
    "VerbosityEvidence",
    "VerbosityIntervention",
    "VerbosityTrace",
]
```

### 5. Register with the diagnose runner

In `_diagnose/lib/registry.py`, add an entry:

```python
PatternInfo(
    name="verbosity_audit",
    module="vstack.verbosity_audit",
    analyzer="VerbosityAuditor",
    analyzer_async=None,  # add VerbosityAuditorAsync later
    shapes=("individual",),
    module_id=99,
    pattern_id=35,
    summary="Detects unbounded-verbosity failures in agent responses.",
    tags=("brevity", "grice", "ux"),
)
```

After this, `verbosity_audit` is callable from:

- `diagnose(trace=..., patterns=["verbosity_audit"])`
- `vstack-diagnose --patterns verbosity_audit ...`
- The MCP `vstack_verbosity_audit` tool (auto-generated from
  `_mcp/lib/_registry.py` — add the registry entry there too).
- The FastAPI `/v1/analyze/verbosity_audit` endpoint
  (auto-generated similarly).

## Optional: register an adapter override

If the smart extractor in `_diagnose/lib/adapters.py` doesn't extract
findings correctly from your output schema, register an override:

```python
from vstack.diagnose import Finding, register_adapter


@register_adapter("verbosity_audit")
def _adapt_verbosity(result):
    out = []
    for ev in result.evidence:
        out.append(
            Finding(
                pattern="verbosity_audit",
                severity=ev.severity,
                title=f"verbosity {result.word_count_ratio:.1f}x expected",
                evidence=ev.evidence_quotes[0] if ev.evidence_quotes else "",
                intervention=(
                    result.interventions[0].description
                    if result.interventions
                    else ""
                ),
            )
        )
    return out
```

## Optional: ship an essay

Each vstack pattern ships a narrative essay explaining the OB
lineage, the LLM-agent analog, and the design decisions that
shaped the pattern. The essays at `module-*/NN-*/essay.md` set the
tone — they're 1,500-3,000 words of literature review + scenario +
walkthrough. Write yours in the same voice.

## See also

- Any of the 34 shipped patterns under `module-1-individual/`,
  `module-2-team/`, `module-3-organization/` for full reference
  implementations.
- The Lewin pattern (`module-1-individual/01-lewin-formula/`) is the
  best-documented; copy its structure.
- The Span-of-Control pattern (`module-3-organization/34-span-of-control/`)
  is the simplest; copy its structure for a deterministic pattern
  that needs no LLM at all.
