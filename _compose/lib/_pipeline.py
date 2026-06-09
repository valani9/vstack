"""Declarative pattern pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class Stop(Exception):
    """Raised by a callback to stop the pipeline."""


@dataclass
class PipelineStep:
    """A single step in a pipeline."""

    kind: str  # "pattern" | "conditional" | "callback" | "diagnose"
    pattern: str | None = None
    mode: str = "standard"
    condition: Callable[[Any], bool] | None = None
    callback: Callable[[Any], Any] | None = None
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of running a pipeline against a trace."""

    pipeline_name: str
    steps_run: list[str]
    findings: list[dict] = field(default_factory=list)
    per_pattern: dict[str, Any] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    stopped_early: bool = False

    def dimension_summary(self) -> dict[str, int]:
        """Count findings by severity."""
        summary = {"high": 0, "medium": 0, "low": 0}
        for f in self.findings:
            sev = f.get("severity") if isinstance(f, dict) else getattr(f, "severity", None)
            if sev in summary:
                summary[sev] += 1
        return summary

    def has_high(self) -> bool:
        return self.dimension_summary()["high"] > 0

    def top_findings(self, n: int = 5) -> list[dict]:
        order = {"high": 0, "medium": 1, "low": 2}

        def key(f):
            sev = f.get("severity") if isinstance(f, dict) else getattr(f, "severity", "low")
            return order.get(sev, 99)

        return sorted(self.findings, key=key)[:n]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_name": self.pipeline_name,
            "steps_run": self.steps_run,
            "findings_count": len(self.findings),
            "dimension_summary": self.dimension_summary(),
            "errors_count": len(self.errors),
            "stopped_early": self.stopped_early,
            "metadata": self.metadata,
        }


class Pipeline:
    """A fluent builder for declarative pattern composition.

    Pipelines are immutable: each builder method returns a NEW
    Pipeline with the step appended.
    """

    def __init__(
        self,
        name: str,
        steps: list[PipelineStep] | None = None,
        baseline_path: str | None = None,
    ):
        self.name = name
        self._steps: list[PipelineStep] = list(steps) if steps else []
        self.baseline_path = baseline_path

    def _append(self, step: PipelineStep) -> Pipeline:
        return Pipeline(
            name=self.name,
            steps=[*self._steps, step],
            baseline_path=self.baseline_path,
        )

    def step(
        self,
        pattern: str,
        *,
        mode: str = "standard",
        label: str | None = None,
    ) -> Pipeline:
        """Add a pattern call to the pipeline."""
        return self._append(
            PipelineStep(
                kind="pattern",
                pattern=pattern,
                mode=mode,
                label=label or pattern,
            )
        )

    def then(self, pattern: str, *, mode: str = "standard") -> Pipeline:
        """Alias for step() — for readability when chaining."""
        return self.step(pattern, mode=mode)

    def when_severity(
        self,
        severity: str,
        *,
        run: str,
        mode: str = "standard",
    ) -> Pipeline:
        """Conditionally run a pattern if prior step found `severity`."""

        def has_severity(prev_result: Any) -> bool:
            if not isinstance(prev_result, dict):
                return False
            for f in prev_result.get("findings", []):
                f_sev = f.get("severity") if isinstance(f, dict) else getattr(f, "severity", None)
                if f_sev == severity:
                    return True
            return False

        return self._append(
            PipelineStep(
                kind="conditional",
                pattern=run,
                mode=mode,
                condition=has_severity,
                label=f"when_severity({severity})→{run}",
            )
        )

    def when(
        self,
        predicate: Callable[[Any], bool],
        *,
        run: str,
        mode: str = "standard",
    ) -> Pipeline:
        """Conditionally run a pattern based on a custom predicate."""
        return self._append(
            PipelineStep(
                kind="conditional",
                pattern=run,
                mode=mode,
                condition=predicate,
                label=f"when(...)→{run}",
            )
        )

    def callback(
        self,
        fn: Callable[[Any], Any],
        *,
        label: str | None = None,
    ) -> Pipeline:
        """Insert a side-effect callback. Raise Stop to halt early."""
        return self._append(
            PipelineStep(
                kind="callback",
                callback=fn,
                label=label or "callback",
            )
        )

    def diagnose(
        self,
        recipe: str | None = None,
        *,
        mode: str = "standard",
    ) -> Pipeline:
        """Run the full diagnose() runner with an optional recipe."""
        return self._append(
            PipelineStep(
                kind="diagnose",
                pattern=recipe,  # repurposed slot
                mode=mode,
                label=f"diagnose({recipe or 'default'})",
            )
        )

    def with_baseline(self, path: str) -> Pipeline:
        """Configure a baseline JSON path for downstream comparison."""
        return Pipeline(
            name=self.name,
            steps=list(self._steps),
            baseline_path=path,
        )

    def run(
        self,
        trace: Any,
        *,
        llm_client: Any,
        max_findings_per_step: int = 50,
    ) -> PipelineResult:
        """Execute the pipeline against a trace."""
        result = PipelineResult(
            pipeline_name=self.name,
            steps_run=[],
            metadata={
                "n_steps": len(self._steps),
                "baseline_path": self.baseline_path,
            },
        )
        last_step_result: Any = None

        for step in self._steps:
            try:
                if step.kind == "pattern":
                    step_out = self._run_pattern(
                        step.pattern,  # type: ignore[arg-type]
                        trace,
                        llm_client,
                        mode=step.mode,
                    )
                    result.steps_run.append(step.label or step.pattern)  # type: ignore[arg-type]
                    self._merge_findings(result, step.pattern, step_out, max_findings_per_step)
                    last_step_result = step_out

                elif step.kind == "conditional":
                    if step.condition and step.condition(last_step_result):
                        step_out = self._run_pattern(
                            step.pattern,  # type: ignore[arg-type]
                            trace,
                            llm_client,
                            mode=step.mode,
                        )
                        result.steps_run.append(step.label or step.pattern)  # type: ignore[arg-type]
                        self._merge_findings(result, step.pattern, step_out, max_findings_per_step)
                        last_step_result = step_out
                    else:
                        result.steps_run.append(f"skip:{step.label}")

                elif step.kind == "callback":
                    if step.callback is not None:
                        step.callback(last_step_result)
                    result.steps_run.append(step.label or "callback")

                elif step.kind == "diagnose":
                    diag_out = self._run_diagnose(
                        trace,
                        llm_client,
                        recipe=step.pattern,  # type: ignore[arg-type]
                        mode=step.mode,
                    )
                    result.steps_run.append(step.label or "diagnose")
                    self._merge_findings(result, "diagnose", diag_out, max_findings_per_step)
                    last_step_result = diag_out

            except Stop:
                result.stopped_early = True
                break
            except Exception as exc:
                result.errors.append(
                    {
                        "step": step.label,
                        "pattern": step.pattern,
                        "error": str(exc),
                        "error_class": type(exc).__name__,
                    }
                )

        return result

    @staticmethod
    def _run_pattern(pattern: str, trace: Any, llm_client: Any, *, mode: str) -> Any:
        from vstack.diagnose import diagnose

        return diagnose(
            trace=trace,
            llm_client=llm_client,
            patterns=[pattern],
            mode=mode,
        )

    @staticmethod
    def _run_diagnose(
        trace: Any,
        llm_client: Any,
        *,
        recipe: str | None,
        mode: str,
    ) -> Any:
        from vstack.diagnose import diagnose

        kwargs: dict[str, Any] = {
            "trace": trace,
            "llm_client": llm_client,
            "mode": mode,
        }
        if recipe:
            kwargs["recipe"] = recipe
        return diagnose(**kwargs)

    @staticmethod
    def _merge_findings(
        result: PipelineResult,
        pattern: str | None,
        step_out: Any,
        max_findings: int,
    ) -> None:
        if step_out is None:
            return

        # Capture per-pattern result.
        if pattern:
            result.per_pattern[pattern] = step_out

        # Merge findings.
        findings = []
        if isinstance(step_out, dict):
            findings = step_out.get("findings", [])
        elif hasattr(step_out, "findings"):
            findings = list(step_out.findings)

        for f in findings[:max_findings]:
            if isinstance(f, dict):
                result.findings.append(f)
            else:
                result.findings.append(
                    {
                        "pattern": getattr(f, "pattern", pattern),
                        "severity": getattr(f, "severity", "low"),
                        "title": getattr(f, "title", ""),
                        "intervention": getattr(f, "intervention", ""),
                    }
                )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the pipeline definition (not the result)."""
        return {
            "name": self.name,
            "steps": [
                {
                    "kind": s.kind,
                    "pattern": s.pattern,
                    "mode": s.mode,
                    "label": s.label,
                }
                for s in self._steps
            ],
            "baseline_path": self.baseline_path,
        }

    def __len__(self) -> int:
        return len(self._steps)
