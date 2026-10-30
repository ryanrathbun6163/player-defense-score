"""Completed-phase replay against authorized captured producer records.

Clean clones without ignored experiment evidence skip; corrupt present evidence
must fail. These checks hash saved artifacts but perform no model/policy work.
"""
from contextlib import ExitStack, redirect_stdout
import copy
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from src.ball_tracking import nba_ball_distractor_evaluation as evaluation
from src.ball_tracking import nba_ball_distractor_policy as policy

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/evaluation.OUTPUT
CAPTURED = all((OUTPUT/name).is_file() for name in
               ("completion.json","emission_completion.json","evaluation_completion.json","emissions/manifest.json"))


def prohibit_work():
    stack = ExitStack()
    for owner,name in ((evaluation.screen,"load_model"),(evaluation.screen,"encode"),
                       (evaluation.classifier,"fit"),(evaluation.classifier,"score"),
                       (evaluation.emission,"extract"),(policy,"apply"),(policy,"evaluate"),
                       (evaluation.d,"write_once")):
        stack.enter_context(patch.object(owner,name,side_effect=AssertionError(f"Replay invoked {name}")))
    stack.enter_context(redirect_stdout(io.StringIO()))
    return stack


@unittest.skipUnless(CAPTURED,"Requires completed ignored producer evidence")
class CompletedEvaluationTests(unittest.TestCase):
    def test_both_phases_return_exact_existing_completion_without_work_or_writes(self):
        paths = [OUTPUT/name for name in ("completion.json","fit_started.json","fit.json","emission_completion.json",
            "evaluation_completion.json","emission_scores.json","policy.json","evaluation_report.json")]
        before = {p:p.read_bytes() for p in paths}
        with prohibit_work():
            features = evaluation.feature_pass(ROOT)
            compared = evaluation.compare(ROOT)
        self.assertEqual(features,evaluation.d.read_json(OUTPUT/"emission_completion.json"))
        self.assertEqual(compared,evaluation.d.read_json(OUTPUT/"evaluation_completion.json"))
        self.assertEqual(compared["decision"],"rejected_no_adoption")
        self.assertEqual({p:p.read_bytes() for p in paths},before)

    def test_changed_completed_score_binding_is_rejected_before_work(self):
        original = evaluation.d.read_json
        target = OUTPUT/"emission_completion.json"
        def changed(path):
            record = original(path)
            if Path(path).resolve() == target:
                record = copy.deepcopy(record); record["scores"]["sha256"] = "0"*64
            return record
        with prohibit_work(),patch.object(evaluation.d,"read_json",side_effect=changed):
            with self.assertRaisesRegex(ValueError,"Bound file changed.*emission_scores"):
                evaluation.feature_pass(ROOT)

    def test_current_bound_policy_implementation_change_is_rejected(self):
        original = evaluation.d.digest
        target = Path(policy.__file__).resolve()
        def changed(path):
            return "0"*64 if Path(path).resolve() == target else original(path)
        with prohibit_work(),patch.object(evaluation.d,"digest",side_effect=changed):
            with self.assertRaisesRegex(ValueError,"Bound file changed.*nba_ball_distractor_policy"):
                evaluation.compare(ROOT)


if __name__ == "__main__": unittest.main()
