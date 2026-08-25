"""Tests for scripts/project_status.py roadmap parsing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.project_status import (  # noqa: E402
    build_phase_progress,
    format_report,
    main,
    next_incomplete,
    parse_roadmap,
)

SAMPLE_ROADMAP = """# Roadmap

## 1. Foundation

Intro text.

- [x] 1.1 First
- [x] 1.2 Second

## 2. Characters

- [x] 2.1 Model
- [ ] 2.2 Schemas
- [ ] 2.3 API

## 3. AI Tools

- [x] **3.1** Config
- [ ] **3.2** Service

## Development Automation

Engineering infrastructure, excluded from MVP completion denominator.

- [x] Unified Makefile quality gates
- [ ] Architecture checks
"""


class ProjectStatusParserTests(unittest.TestCase):
    def test_counts_total_numbered_steps(self):
        steps, _ = parse_roadmap(SAMPLE_ROADMAP)
        self.assertEqual(len(steps), 7)

    def test_counts_completed(self):
        steps, _ = parse_roadmap(SAMPLE_ROADMAP)
        self.assertEqual(sum(1 for step in steps if step.completed), 4)

    def test_groups_phases(self):
        steps, names = parse_roadmap(SAMPLE_ROADMAP)
        report = format_report(steps, names)
        self.assertIn("Phase 1: 2/2 (100.0%)", report)
        self.assertIn("Phase 2: 1/3 (33.3%)", report)
        self.assertIn("Phase 3: 1/2 (50.0%)", report)

    def test_ignores_development_automation_non_numbered(self):
        steps, _ = parse_roadmap(SAMPLE_ROADMAP)
        titles = [step.title for step in steps]
        self.assertNotIn("Unified Makefile quality gates", titles)
        self.assertNotIn("Architecture checks", titles)

    def test_determines_next_step(self):
        steps, names = parse_roadmap(SAMPLE_ROADMAP)
        report = format_report(steps, names)
        self.assertIn("Next: 2.2 Schemas", report)
        self.assertIn("Current phase: 2. Characters", report)

    def test_mvp_percentage_deterministic(self):
        steps, names = parse_roadmap(SAMPLE_ROADMAP)
        report = format_report(steps, names)
        self.assertIn("MVP: 4/7 (57.1%)", report)

    def test_zero_steps_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ROADMAP.md"
            path.write_text("# Empty\n\n## Development Automation\n- [x] Only non-numbered\n")
            code = main([str(path)])
            self.assertEqual(code, 1)

    def test_supports_bold_step_markers(self):
        steps, _ = parse_roadmap(SAMPLE_ROADMAP)
        phase3 = [step for step in steps if step.phase == 3]
        self.assertEqual(phase3[0].title, "Config")
        self.assertEqual(f"{phase3[0].phase}.{phase3[0].step}", "3.1")


class RealRoadmapVerifiedStateTests(unittest.TestCase):
    """Regression guard for the verified numbered completion state."""

    @classmethod
    def setUpClass(cls):
        roadmap_path = ROOT / "ROADMAP.md"
        text = roadmap_path.read_text(encoding="utf-8")
        cls.steps, cls.phase_names = parse_roadmap(text)
        cls.phases = {
            phase.phase: phase
            for phase in build_phase_progress(cls.steps, cls.phase_names)
        }

    def test_total_numbered_steps_is_70(self):
        self.assertEqual(len(self.steps), 70)

    def test_completed_numbered_steps_is_28(self):
        completed = sum(1 for step in self.steps if step.completed)
        self.assertEqual(completed, 28)

    def test_phase_1_complete(self):
        phase = self.phases[1]
        self.assertEqual((phase.completed, phase.total), (10, 10))

    def test_phase_2_complete(self):
        phase = self.phases[2]
        self.assertEqual((phase.completed, phase.total), (10, 10))

    def test_phase_3_is_8_of_10(self):
        phase = self.phases[3]
        self.assertEqual((phase.completed, phase.total), (8, 10))

    def test_next_incomplete_is_agent_service(self):
        nxt = next_incomplete(self.steps)
        self.assertIsNotNone(nxt)
        self.assertEqual(nxt.phase, 3)
        self.assertEqual(nxt.step, 9)
        self.assertEqual(nxt.title, "Agent Service")


if __name__ == "__main__":
    unittest.main()
