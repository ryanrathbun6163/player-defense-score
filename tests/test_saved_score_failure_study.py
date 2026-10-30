"""Integrity and additive-output guarantees for the record-only study runner."""
import json
from pathlib import Path
import tempfile
import unittest

from src.ball_tracking.saved_score_failure_study import (
    OUTPUT_BASE, binding, repository_path, run, verify_binding, write_json, write_rows,
)


class SavedScoreFailureRunnerTests(unittest.TestCase):
    def test_changed_frozen_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "scores.jsonl"
            path.write_text('{"logit":1}\n', encoding="utf-8")
            sealed = binding(root, path)
            path.write_text('{"logit":2}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Frozen binding differs"):
                verify_binding(root, sealed)

    def test_paths_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "outside repository"):
                repository_path(Path(temp), "../other/scores.jsonl")

    def test_existing_attempt_preserved_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / OUTPUT_BASE / "attempt_001"
            out.mkdir(parents=True)
            marker = out / "failed.json"
            marker.write_text("original failure", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run(root, "missing_spec.json", "missing_freeze.json", out)
            self.assertEqual(marker.read_text(encoding="utf-8"), "original failure")

    def test_output_cannot_overwrite_other_study(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / "data/outputs/other_study/attempt_001"
            with self.assertRaisesRegex(ValueError, "new attempt"):
                run(root, "missing_spec.json", "missing_freeze.json", out)
            self.assertFalse(out.exists())

    def test_missing_and_zero_survive_json_transport_and_writes_are_exclusive(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rows.jsonl"
            rows = [{"logit": None, "state": "missing"}, {"logit": 0.0, "state": "zero"}]
            write_rows(path, rows)
            self.assertEqual([json.loads(s) for s in path.read_text().splitlines()], rows)
            with self.assertRaises(FileExistsError):
                write_rows(path, [])
            with self.assertRaises(ValueError):
                write_json(Path(temp) / "bad.json", {"score": float("nan")})


if __name__ == "__main__":
    unittest.main()
