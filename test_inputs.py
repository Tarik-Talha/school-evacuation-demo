"""Checks for population accounting and unsupported school input claims."""
import copy
import json
import unittest

from validate import ROOT, population_snapshot, validate_package


class InputTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((ROOT / "school_profile.json").read_text(encoding="utf-8"))
        self.scenarios = json.loads((ROOT / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]

    def test_user_population(self):
        value = population_snapshot(self.profile, self.scenarios[0])
        self.assertEqual(value["students_by_floor"], {"1": 22, "2": 10, "3": 44, "4": 35})
        self.assertEqual(value["students"], 111)
        self.assertEqual(value["modeled_population"], 111)

    def test_adults_are_excluded_by_user_scope(self):
        value = population_snapshot(self.profile, self.scenarios[0])
        self.assertFalse(value["adults_included"])
        self.assertEqual(value["modeled_population"], 111)

    def test_lunch_relocation_preserves_people(self):
        value = population_snapshot(self.profile, self.scenarios[1])
        self.assertEqual(value["students_by_floor"], {"B1": 111})
        self.assertIsNone(value["evacuation_time_seconds"])

    def test_lab_visit_moves_existing_class(self):
        value = population_snapshot(self.profile, self.scenarios[7])
        self.assertEqual(value["students_by_floor"], {"1": 22, "2": 10, "3": 24, "4": 35, "5": 20})
        self.assertEqual(value["students"], 111)

    def test_unknown_locations_stay_unknown(self):
        value = population_snapshot(self.profile, self.scenarios[2])
        self.assertEqual(value["students_by_floor"], {"unallocated": 111})

    def test_scope_change_requires_explicit_update(self):
        self.profile["population_scope"] = "all_occupants"
        with self.assertRaises(ValueError):
            population_snapshot(self.profile, self.scenarios[0])

    def test_duplicate_class_rejected(self):
        self.profile["classes"].append(copy.deepcopy(self.profile["classes"][0]))
        with self.assertRaises(ValueError):
            population_snapshot(self.profile, self.scenarios[0])

    def test_unknown_class_move_rejected(self):
        scenario = copy.deepcopy(self.scenarios[7])
        scenario["placement"]["class_destinations"]["imaginary"] = "5"
        with self.assertRaises(ValueError):
            population_snapshot(self.profile, scenario)

    def test_nonexistent_destination_rejected(self):
        scenario = copy.deepcopy(self.scenarios[1])
        scenario["placement"]["destination_floor"] = "99"
        with self.assertRaises(ValueError):
            population_snapshot(self.profile, scenario)

    def test_all_scenarios_retain_uncertainty(self):
        report = validate_package(self.profile, self.scenarios)
        self.assertTrue(report["population_conserved_in_all_scenarios"])
        self.assertFalse(report["quantitative_simulation_ready"])
        self.assertIsNone(report["casualty_estimate"])


if __name__ == "__main__":
    unittest.main()
