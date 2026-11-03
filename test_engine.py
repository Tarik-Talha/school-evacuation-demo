"""Numerical conservation and failure cases for the illustrative network."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from engine import ROUTES, Settings, position_at, simulate

PROFILE = json.loads((Path(__file__).parent / "school_profile.json").read_text(encoding="utf-8"))


class EngineTests(unittest.TestCase):
    def test_single_student_has_analytical_travel_time(self):
        profile = copy.deepcopy(PROFILE)
        profile["classes"] = [{"id": "one", "students": 1, "home_floor": "1"}]
        result = simulate(profile, Settings(reaction_spread=0))
        # 12 s preparation + 1 door + 10 corridor + 16 stairs + 1 exit + 20 outdoors + 2 gate.
        self.assertAlmostEqual(result["metrics"]["assembly_seconds_after_shaking"], 62.)
        self.assertAlmostEqual(result["metrics"]["mean_wait_seconds"], 0.)

    def test_all_111_arrive_and_never_move_during_shaking(self):
        result = simulate(PROFILE)
        self.assertEqual(result["metrics"]["assembled"], 111)
        self.assertEqual(result["metrics"]["unresolved"], 0)
        self.assertEqual(len({p["id"] for p in result["persons"]}), 111)
        for person in result["persons"]:
            for segment in person["segments"]:
                if segment["state"] == "moving":
                    self.assertGreaterEqual(segment["start"], 20.)
            self.assertLessEqual(person["outside_at"], person["arrived_at"])

    def test_shared_segments_never_exceed_storage(self):
        result = simulate(PROFILE)
        for passage in result["queues"]:
            self.assertLessEqual(passage["peak_occupancy"], passage["storage_slots"])
        lower = next(row for row in result["queues"] if row["id"] == "stair_left_M")
        self.assertGreater(lower["entered"], 0)
        self.assertTrue(any(p["total_wait_seconds"] > 0 for p in result["queues"]))

    def test_closing_all_routes_does_not_report_success(self):
        result = simulate(PROFILE, Settings(closed_routes=ROUTES))
        self.assertEqual(result["metrics"]["unreachable"], 111)
        self.assertIsNone(result["metrics"]["assembly_seconds_after_shaking"])
        self.assertIsNone(result["metrics"]["exit_seconds_after_shaking"])

    def test_closed_field_gate_preserves_outside_vs_assembly(self):
        result = simulate(PROFILE, Settings(gate_open=False))
        self.assertEqual(result["metrics"]["outside"], 111)
        self.assertEqual(result["metrics"]["assembled"], 0)
        self.assertEqual(result["metrics"]["unresolved"], 111)
        self.assertIsNone(result["metrics"]["assembly_seconds_after_shaking"])
        self.assertIsNotNone(result["metrics"]["exit_seconds_after_shaking"])

    def test_lunch_has_one_shared_door_and_111_students(self):
        result = simulate(PROFILE, Settings(context="lunch"))
        self.assertEqual({p["floor"] for p in result["persons"]}, {"B1"})
        self.assertEqual(len([key for key in result["network"]["edges"] if key.startswith("door_")]), 1)
        self.assertEqual(result["metrics"]["assembled"], 111)

    def test_no_invented_basement_fire_stair(self):
        result = simulate(PROFILE, Settings(context="lunch", closed_routes=("left", "right")))
        self.assertEqual(result["metrics"]["unreachable"], 111)

    def test_lab_moves_class_instead_of_adding_students(self):
        result = simulate(PROFILE, Settings(context="lab"))
        moved = [p for p in result["persons"] if p["class_id"] == "10A"]
        self.assertEqual(len(moved), 20)
        self.assertEqual({p["floor"] for p in moved}, {"5"})
        self.assertEqual(result["metrics"]["students"], 111)

    def test_finite_horizon_never_claims_full_arrival(self):
        result = simulate(PROFILE, Settings(horizon_seconds=5))
        self.assertEqual(result["metrics"]["timed_out"], 111)
        self.assertIsNone(result["metrics"]["assembly_seconds_after_shaking"])

    def test_same_seed_repeats_exactly(self):
        a, b = simulate(PROFILE), simulate(PROFILE)
        self.assertEqual(a, b)

    def test_bad_parameters_rejected(self):
        for settings in [Settings(stair_width=float("nan")), Settings(door_width=0),
                         Settings(closed_routes=("invented",)), Settings(walking_speed=-1)]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                simulate(PROFILE, settings)

    def test_narrow_dining_door_delays_the_controlled_lunch_case(self):
        a = simulate(PROFILE, Settings(context="lunch", dining_door_width=.5))
        b = simulate(PROFILE, Settings(context="lunch", dining_door_width=2.5))
        self.assertGreater(a["metrics"]["assembly_seconds_after_shaking"], b["metrics"]["assembly_seconds_after_shaking"])

    def test_animation_preserves_population_and_final_state(self):
        result = simulate(PROFILE)
        for timestamp in [0, 20, 60, result["metrics"]["elapsed_seconds_from_onset"]]:
            points = [position_at(result, p, timestamp) for p in result["persons"]]
            self.assertEqual(len(points), 111)
            if timestamp == 0:
                self.assertEqual({point[2] for point in points}, {"protecting"})
        final = [position_at(result, p, result["metrics"]["elapsed_seconds_from_onset"])[2] for p in result["persons"]]
        self.assertEqual(set(final), {"assembled"})


class UiTests(unittest.TestCase):
    def test_default_screen_and_lunch_selector(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).parent / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "111 / 111")
        app.selectbox(key="context").select("Öğle yemeği · 111 öğrenci B1'de").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "111 / 111")

    def test_closed_routes_do_not_show_full_evacuation(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).parent / "app.py"), default_timeout=30).run()
        for route in ROUTES:
            app.checkbox(key="route_" + route).uncheck()
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0 / 111")
        self.assertEqual(app.metric[1].value, "Tamamlanmadı")


if __name__ == "__main__":
    unittest.main()
