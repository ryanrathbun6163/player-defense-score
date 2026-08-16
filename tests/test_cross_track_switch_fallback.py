import unittest

import numpy as np

from src.identity.review_cross_track_switches import (
    MAX_LOCAL_SAMPLE_FALLBACK_FRAME_GAP,
    build_boundary_record,
    choose_clean_review_rows,
)


def tracked_row(frame_index, track_id=1):
    return {
        "frame_index": frame_index,
        "track_id": track_id,
        "player_id": "dark_p1",
        "confidence": 0.9,
        "x1": 10.0,
        "y1": 10.0,
        "x2": 30.0,
        "y2": 70.0,
        "floor_x": float(frame_index),
        "floor_y": 70.0,
    }


def appearance_sample(frame_index, track_id=1):
    return {
        "frame_index": frame_index,
        "track_id": track_id,
        "confidence": 0.9,
        "embedding": np.asarray([1.0, 0.0], dtype=np.float32),
    }


def boundary_record(sample_frame, reviewed_track_id):
    before_row = tracked_row(10)
    after_row = tracked_row(11)
    rows_by_frame = {
        10: [before_row],
        11: [after_row],
    }
    rows_by_identity = {
        "dark_p1": [before_row, after_row],
    }

    return build_boundary_record(
        boundary=10,
        team_player_ids=["dark_p1"],
        rows_by_frame=rows_by_frame,
        rows_by_identity=rows_by_identity,
        samples_by_identity={
            "dark_p1": [appearance_sample(sample_frame)],
        },
        reid_review={
            "manual_split_after_frames": {
                str(reviewed_track_id): [10],
            }
        },
        stage_before_start=1,
        stage_after_end=20,
    )


class CrossTrackSampleFallbackTests(unittest.TestCase):
    def test_nearby_sample_from_continuing_track_is_audited_fallback(self):
        record = boundary_record(
            sample_frame=10,
            reviewed_track_id=99,
        )

        self.assertEqual(record["analysis_status"], "analyzed")
        self.assertEqual(
            record["second_sample_fallbacks"],
            {
                "dark_p1": {
                    "sample_frame_index": 10,
                    "sample_track_id": 1,
                    "frame_gap": 1,
                    "requested_window": [11, 50],
                }
            },
        )
        self.assertEqual(
            record["assignments"][0]["assignment_type"],
            "same_label_anchor",
        )
        self.assertEqual(
            record["assignments"][0]["clean_review_status"],
            "insufficient_rows",
        )

    def test_reviewed_split_track_never_borrows_across_boundary(self):
        record = boundary_record(
            sample_frame=10,
            reviewed_track_id=1,
        )

        self.assertEqual(
            record["analysis_status"],
            "skipped_missing_appearance_samples",
        )
        self.assertEqual(
            record["missing_second_sample_player_ids"],
            ["dark_p1"],
        )
        self.assertEqual(record["second_sample_fallbacks"], {})
        self.assertEqual(record["assignments"], [])

    def test_missing_clean_review_window_returns_no_optional_frames(self):
        selected = choose_clean_review_rows(
            player_id="dark_p1",
            rows_by_identity={"dark_p1": []},
            rows_by_frame={},
            first_frame=1,
            last_frame=10,
            side="PRE",
        )

        self.assertEqual(selected, [])

    def test_sample_beyond_bounded_gap_is_not_reused(self):
        record = boundary_record(
            sample_frame=(
                11 - MAX_LOCAL_SAMPLE_FALLBACK_FRAME_GAP - 1
            ),
            reviewed_track_id=99,
        )

        self.assertEqual(
            record["analysis_status"],
            "skipped_missing_appearance_samples",
        )
        self.assertEqual(
            record["missing_second_sample_player_ids"],
            ["dark_p1"],
        )


if __name__ == "__main__":
    unittest.main()
