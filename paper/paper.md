---
title: 'vstack: Organizational-behavior diagnostics for AI agents and multi-agent systems'
tags:
  - Python
  - artificial intelligence
  - AI agents
  - multi-agent systems
  - agent observability
  - organizational behavior
authors:
  - name: Ilhan Valani
    orcid: 0009-0000-0000-0000
    affiliation: 1
affiliations:
  - name: Boston University, United States
    index: 1
date: 23 June 2026
bibliography: paper.bib
---

<!-- NOTE [ILHAN]: replace the placeholder `orcid` above with your real ORCID iD before any JOSS submission. -->

# Summary

`vstack` is a Python library that diagnoses why AI agents and multi-agent
systems fail, using the vocabulary of organizational-behavior (OB) research.
Large language model (LLM) agents fail in recognizable, recurring shapes —
looping on a broken approach, patching symptoms instead of causes, hiding
errors, or escalating commitment to a clearly-failing plan. These are the
same failure modes that seventy years of OB research catalogued in human
teams. `vstack` ports 34 of the most-cited OB frameworks — Wharton's
After-Action Review [@usarmy1993], Lencioni's Five Dysfunctions
[@lencioni2002], Edmondson's psychological safety [@edmondson1999], Lewin's
$B = f(I, E)$ attribution model [@lewin1936], Schein's culture model
[@schein2010], and 29 others — into runnable analyzers that operate on a
structured agent trace and return named findings, each with a root cause and
a recommended intervention.

Every pattern consumes the same `AgentTrace` data model, so a single trace
flows through one analyzer or a curated bundle of them. The same 34 patterns
are exposed through thirteen invocation surfaces — Python imports, per-pattern
and workflow command-line tools, a Model Context Protocol server, a FastAPI
REST service, a multi-architecture container image, Claude Code skills,
native adapters for ten agent frameworks (LangChain, LangGraph, CrewAI,
AutoGen, LlamaIndex, Pydantic AI, smolagents, Agno, Google ADK, and AWS
Strands), and a GitHub Action — so the patterns can be used from any agent
stack without re-implementing them.

# Statement of need

Tooling for LLM agents is concentrated on two activities: *evaluation*
(pass/fail scores, often via an LLM-as-judge) and *observability* (tracing,
token and latency metrics). Both answer *whether* and *how expensively* a run
behaved, but neither names *why* a run went wrong in a way that points to a
specific fix. Practitioners building production multi-agent systems repeatedly
hit the same failure modes and lack a shared, precise vocabulary for them.

The contribution of `vstack` is to supply that vocabulary from an existing,
citable body of theory. OB research is unusually well suited to the task
because its findings are *specific*: a named failure mode, its root cause,
and a named intervention. Escalation of commitment [@staw1976], groupthink
[@janis1972], the bias stack [@tversky1974], social loafing in groups
[@latane1979], the arousal–performance curve [@yerkes1908], and
intrinsic-motivation collapse [@deci2000] all describe behaviors that appear,
almost unchanged, in agent traces. `vstack` makes that mapping concrete and executable: it turns a
forensic post-mortem of an agent run into a structured object with named
findings and interventions, and it makes that diagnosis reproducible across
frameworks and embeddable in CI (a diagnosis can fail a build when a finding
crosses a severity threshold).

`vstack` is aimed at three audiences: engineers operating production agent
crews who need to name and fix recurring failures; evaluation researchers who
want diagnostic vocabulary rather than only pass/fail signal; and researchers
mapping agent behavior onto the human OB literature. It is implemented in
typed Python, covered by an extensive test suite, and distributed on PyPI.

# Acknowledgements

The framing of agent failures through organizational-behavior theory grew out
of coursework in Management & Organizations at Boston University.

# References
