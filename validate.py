"""Validate school scenario inputs; this module does not estimate evacuation time."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# =========================================================
# POPULATION CONSERVATION AND EXPLICIT UNKNOWN LOCATIONS
# =========================================================
def population_snapshot(profile, scenario):
    classes = profile["classes"]
    identifiers = [row["id"] for row in classes]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate class identifier")
    floors = {row["id"] for row in profile["plan_levels"]}
    for row in classes:
        if type(row["students"]) is not int or row["students"] <= 0:
            raise ValueError("Student counts must be positive integers")
        if row["home_floor"] not in floors:
            raise ValueError("Class floor has no plan")
    if profile["population_scope"] != "students_only":
        raise ValueError("This input package supports the requested student-only scope")
    placement = scenario["placement"]
    mode = placement["mode"]
    if mode not in {"home_floors", "unknown", "all_students", "move_classes"}:
        raise ValueError("Unknown placement mode")
    destinations = placement.get("class_destinations", {})
    if set(destinations) - set(identifiers):
        raise ValueError("Movement references an unknown class")
    by_floor = Counter()
    for row in classes:
        if mode == "unknown":
            floor = "unallocated"
        elif mode == "all_students":
            floor = placement["destination_floor"]
        elif mode == "move_classes":
            floor = destinations.get(row["id"], row["home_floor"])
        else:
            floor = row["home_floor"]
        if floor != "unallocated" and floor not in floors:
            raise ValueError("Destination floor has no plan")
        by_floor[floor] += row["students"]
    students = sum(row["students"] for row in classes)
    assert sum(by_floor.values()) == students
    return {
        "scenario_id": scenario["id"],
        "students": students,
        "students_by_floor": dict(by_floor),
        "population_scope": "students_only",
        "modeled_population": students,
        "adults_included": False,
        "complete_building_population_known": False,
        "evacuation_time_seconds": None,
        "assembly_time_seconds": None,
    }


# =========================================================
# MISSING EVIDENCE BLOCKS QUANTITATIVE EVACUATION CLAIMS
# =========================================================
def validate_package(profile, scenarios):
    identifiers = [row["id"] for row in scenarios]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate scenario identifier")
    snapshots = [population_snapshot(profile, row) for row in scenarios]
    source_ids = {row["id"] for row in profile["plan_levels"]}
    assert {row["home_floor"] for row in profile["classes"]} <= source_ids
    assert all(row["requires_field_validation"] for row in scenarios)
    assert all(not row["operationally_approved"] for row in scenarios)
    assert profile["location"]["site_ground_motion"] is None
    assert not profile["assembly"]["operationally_approved"]
    return {
        "input_validation": "passed",
        "scenario_count": len(scenarios),
        "student_total": snapshots[0]["students"],
        "student_floor_totals": population_snapshot(profile, scenarios[0])["students_by_floor"],
        "teachers_roster": profile["teachers"]["roster_count"],
        "population_scope": "students_only",
        "modeled_population": snapshots[0]["students"],
        "adults_included": False,
        "population_conserved_in_all_scenarios": True,
        "input_package_ready": True,
        "quantitative_simulation_ready": False,
        "reason": "Measured geometry, class-to-room mapping and safe route/assembly geometry are unverified",
        "snapshots": snapshots,
        "evacuation_time_seconds": None,
        "structural_damage_estimate": None,
        "casualty_estimate": None,
    }


def main():
    profile = json.loads((ROOT / "school_profile.json").read_text(encoding="utf-8"))
    scenarios = json.loads((ROOT / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    report = validate_package(profile, scenarios)
    (ROOT / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "snapshots"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
