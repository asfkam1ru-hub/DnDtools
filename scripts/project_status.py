#!/usr/bin/env python3
"""
Parse ROADMAP.md and print deterministic MVP progress.

Only numbered checkbox steps (e.g. ``- [x] 3.7 Tool Validation``) count.
Non-numbered automation checklist items are ignored.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


STEP_RE = re.compile(
    r"^-\s*\[([ xX])\]\s+(?:\*\*)?(\d+)\.(\d+)(?:\*\*)?\s+(.+?)\s*$"
)
PHASE_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")


@dataclass(frozen=True)
class RoadmapStep:
    phase: int
    step: int
    title: str
    completed: bool


@dataclass(frozen=True)
class PhaseProgress:
    phase: int
    name: str
    completed: int
    total: int

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100.0


def parse_roadmap(text: str) -> tuple[list[RoadmapStep], dict[int, str]]:
    steps: list[RoadmapStep] = []
    phase_names: dict[int, str] = {}
    current_phase: int | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        phase_match = PHASE_RE.match(line)
        if phase_match:
            current_phase = int(phase_match.group(1))
            phase_names[current_phase] = phase_match.group(2).strip()
            continue

        step_match = STEP_RE.match(line)
        if not step_match:
            continue

        completed = step_match.group(1).lower() == "x"
        phase = int(step_match.group(2))
        step_num = int(step_match.group(3))
        title = step_match.group(4).strip()
        # Prefer explicit phase heading; fall back to step's major number.
        resolved_phase = current_phase if current_phase is not None else phase
        steps.append(
            RoadmapStep(
                phase=resolved_phase,
                step=step_num,
                title=title,
                completed=completed,
            )
        )

    return steps, phase_names


def build_phase_progress(
    steps: list[RoadmapStep],
    phase_names: dict[int, str],
) -> list[PhaseProgress]:
    totals: dict[int, list[RoadmapStep]] = {}
    for step in steps:
        totals.setdefault(step.phase, []).append(step)

    phases: list[PhaseProgress] = []
    for phase in sorted(totals):
        items = totals[phase]
        completed = sum(1 for item in items if item.completed)
        name = phase_names.get(phase, f"Phase {phase}")
        phases.append(
            PhaseProgress(
                phase=phase,
                name=name,
                completed=completed,
                total=len(items),
            )
        )
    return phases


def next_incomplete(steps: list[RoadmapStep]) -> RoadmapStep | None:
    for step in steps:
        if not step.completed:
            return step
    return None


def current_phase_label(
    phases: list[PhaseProgress],
    nxt: RoadmapStep | None,
) -> str:
    if nxt is not None:
        for phase in phases:
            if phase.phase == nxt.phase:
                return f"{phase.phase}. {phase.name}"
        return str(nxt.phase)
    for phase in phases:
        if phase.completed < phase.total:
            return f"{phase.phase}. {phase.name}"
    if phases:
        last = phases[-1]
        return f"{last.phase}. {last.name}"
    return "unknown"


def format_report(steps: list[RoadmapStep], phase_names: dict[int, str]) -> str:
    phases = build_phase_progress(steps, phase_names)
    completed = sum(1 for step in steps if step.completed)
    total = len(steps)
    percentage = (completed / total) * 100.0 if total else 0.0
    nxt = next_incomplete(steps)

    lines: list[str] = []
    lines.append(f"MVP: {completed}/{total} ({percentage:.1f}%)")
    lines.append("")
    for phase in phases:
        lines.append(
            f"Phase {phase.phase}: {phase.completed}/{phase.total} "
            f"({phase.percentage:.1f}%)"
        )
    lines.append("")
    lines.append(f"Current phase: {current_phase_label(phases, nxt)}")
    if nxt is None:
        lines.append("Next: (all numbered steps complete)")
    else:
        lines.append(f"Next: {nxt.phase}.{nxt.step} {nxt.title}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    root = Path(__file__).resolve().parent.parent
    roadmap_path = Path(argv[0]) if argv else root / "ROADMAP.md"
    if not roadmap_path.is_file():
        print(f"ROADMAP not found: {roadmap_path}", file=sys.stderr)
        return 1

    text = roadmap_path.read_text(encoding="utf-8")
    steps, phase_names = parse_roadmap(text)
    if not steps:
        print("No numbered roadmap steps found.", file=sys.stderr)
        return 1

    sys.stdout.write(format_report(steps, phase_names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
