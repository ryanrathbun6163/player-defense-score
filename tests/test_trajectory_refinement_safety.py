import unittest

from src.court.refine_player_court_trajectories import (
    initialize_refinement_fields,
    refine_player_rows,
    select_trusted_path,
)
from src.visualization.render_player_court_coordinates import (
    validate_coordinate_contract,
)


def trajectory_row(frame_index, x, y, inside):
    return {
        "frame_index": frame_index,
        "player_id": "white_p1",
        "confidence": 0.9,
        "raw_x": x,
        "raw_y": y,
        "raw_inside": inside,
    }


class TrajectoryRefinementSafetyTests(unittest.TestCase):
    def test_implausible_outside_sample_is_not_boundary_protected(self):
        rows = [
            trajectory_row(0, 10.0, 10.0, True),
            trajectory_row(1, 100.0, 100.0, False),
            trajectory_row(2, 11.0, 10.0, True),
        ]
        trusted = select_trusted_path(
            rows,
            fps=25.0,
            maximum_speed=45.0,
        )

        self.assertEqual(trusted, {0, 2})

        initialize_refinement_fields(rows, trusted, set())
        refine_player_rows(
            rows,
            trusted,
            maximum_extrapolation_observations=2,
            extrapolation_anchor_count=5,
            half_length=42.0,
            court_width=50.0,
        )

        corrected = rows[1]
        self.assertTrue(corrected["refinement_applied"])
        self.assertEqual(
            corrected["refinement_method"],
            "linear_interpolation",
        )
        self.assertAlmostEqual(corrected["refined_x"], 10.5)
        self.assertAlmostEqual(corrected["refined_y"], 10.0)
        self.assertTrue(corrected["refined_inside"])

    def test_final_review_compares_coordinate_report_to_raw_boundary_state(self):
        rows_by_frame = {}
        team_by_player = {}

        for index in range(10):
            team = "white" if index < 5 else "dark"
            player_id = f"{team}_p{index % 5 + 1}"
            team_by_player[player_id] = team
            rows_by_frame[index] = [
                {
                    "reconciled_team": team,
                    "source_observation_available": True,
                    "raw_court_position_in_half_court": index != 0,
                    "court_position_in_half_court": True,
                }
            ]

        coordinate_report = {
            "status": "validated_player_court_coordinates_exported",
            "validation": {
                "row_count": 10,
                "unique_player_count": 10,
                "players_by_team": {"dark": 5, "white": 5},
            },
            "court_position_audit": {
                "outside_half_court_row_count": 1,
            },
        }

        team_counts = validate_coordinate_contract(
            rows_by_frame,
            team_by_player,
            10,
            coordinate_report,
        )

        self.assertEqual(team_counts, {"dark": 5, "white": 5})


if __name__ == "__main__":
    unittest.main()
