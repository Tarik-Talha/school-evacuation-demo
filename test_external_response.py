import unittest

from external_response import estimate_external_arrivals, format_duration


class ExternalResponseTests(unittest.TestCase):
    def test_published_references_are_used_for_all_scenarios(self):
        result = estimate_external_arrivals(shaking_seconds=20)
        ambulance = result["services"]["ambulance"]
        fire = result["services"]["fire"]
        self.assertEqual(ambulance["reference_seconds"], 344)
        self.assertEqual(fire["reference_seconds"], 404)
        self.assertEqual(ambulance["arrival_after_shaking_seconds"], 344)
        self.assertEqual(fire["arrival_after_shaking_seconds"], 404)
        self.assertEqual(ambulance["arrival_from_earthquake_label"], "6 dk 04 sn")
        self.assertEqual(fire["arrival_from_earthquake_label"], "7 dk 04 sn")

    def test_call_delay_shifts_both_arrivals_and_is_exported(self):
        result = estimate_external_arrivals(shaking_seconds=30, call_delay_after_shaking_seconds=90)
        self.assertEqual(result["services"]["ambulance"]["arrival_after_shaking_seconds"], 434)
        self.assertEqual(result["services"]["fire"]["arrival_after_shaking_seconds"], 494)
        self.assertEqual(result["services"]["fire"]["arrival_from_earthquake_seconds"], 524)
        self.assertEqual(result["call_delay_after_shaking_seconds"], 90)
        self.assertIn("İstanbul geneli", result["reference_scope"])

    def test_invalid_inputs_are_rejected(self):
        for kwargs in (
            {"shaking_seconds": -1},
            {"shaking_seconds": True},
            {"shaking_seconds": 301},
            {"shaking_seconds": 20, "call_delay_after_shaking_seconds": 601},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                estimate_external_arrivals(**kwargs)

    def test_duration_formatting(self):
        self.assertEqual(format_duration(344), "5 dk 44 sn")
        self.assertEqual(format_duration(3661), "1 sa 1 dk 01 sn")


if __name__ == "__main__":
    unittest.main()
