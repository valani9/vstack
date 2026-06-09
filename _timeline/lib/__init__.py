"""vstack.timeline — chronological event view + sparklines.

The timeline module renders findings as a time-bucketed series for
visual review:

  - Buckets findings by hour / day / week.
  - Stacks severity per bucket.
  - Renders ASCII sparkline.
  - Renders Markdown timeline.
  - Computes velocity (findings per period).

Quick start
-----------

    from vstack.timeline import (
        Timeline,
        build_timeline,
        render_sparkline,
    )

    timeline = build_timeline(findings, bucket="hour")
    print(render_sparkline(timeline))
    print(timeline.to_markdown())
    print(f"Findings/hour: {timeline.velocity_per_hour():.1f}")
"""

from __future__ import annotations

from ._timeline import (
    Bucket,
    Timeline,
    build_timeline,
    render_markdown_timeline,
    render_sparkline,
)

__all__ = [
    "Bucket",
    "Timeline",
    "build_timeline",
    "render_markdown_timeline",
    "render_sparkline",
]
