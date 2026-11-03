"""Paired repeated trials and explicit drill comparisons, without safety claims."""
from collections import Counter
from dataclasses import asdict, replace
import math
import statistics
import hashlib
import json

from engine import Settings, simulate, unit_id


def quantile(values, probability):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * probability
    low, high = math.floor(pos), math.ceil(pos)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


# =========================================================
# REPEATED TRIALS WITH MATCHED PERSON RANDOMNESS
# =========================================================
def placement_fingerprint(result):
    """Hash the recess population and static placement, never the chosen routes."""
    if result['settings']['context'] != 'recess':
        return None
    groups=sorted(result['network']['groups'],key=unit_id)
    people=sorted(({'id':p['id'],'class_id':p['class_id'],'unit_id':unit_id(p),
                   'floor':p['floor'],'origin':p['origin'],'initial_point':p.get('initial_point')} for p in result['persons']),key=lambda p:p['id'])
    return hashlib.sha256(json.dumps({'groups':groups,'people':people},sort_keys=True,allow_nan=False).encode()).hexdigest()


def run_trials(profile, settings, count=100, progress=None):
    if type(count) is not int or not 2 <= count <= 200:
        raise ValueError("Deneme sayısı 2–200 arasında olmalı.")
    if settings.seed + count >= 2**32:
        raise ValueError("Koşu numarası aralığı çok büyük.")
    rows, bottlenecks = [], Counter()
    expected_placement=None
    for index in range(count):
        result = simulate(profile, replace(settings, seed=settings.seed + index))
        row={"seed": settings.seed + index, **result["metrics"]}
        if settings.context=='recess':
            actual_placement=placement_fingerprint(result)
            if expected_placement is not None and actual_placement!=expected_placement:
                raise ValueError('Teneffüs yerleşimi davranış denemeleri arasında değişti; karşılaştırma durduruldu.')
            expected_placement=actual_placement
            row['placement_fingerprint']=actual_placement
        rows.append(row)
        top = next((edge for edge in result["queues"] if edge["total_wait_seconds"] > .001), None)
        if top:
            bottlenecks[top["label"]] += 1
        if progress:
            progress((index + 1) / count)
    completed = [row["assembly_seconds_after_shaking"] for row in rows if row["unresolved"] == 0]
    return {"status": "model_variability_not_real_world_confidence", "settings": asdict(settings),
        "requested_runs": count, "complete_runs": len(completed), "incomplete_runs": count - len(completed),
        "median_seconds_completed_only": quantile(completed, .5),
        "p05_seconds_completed_only": quantile(completed, .05), "p95_seconds_completed_only": quantile(completed, .95),
        "slowest_complete_seconds": max(completed) if completed else None,
        "mean_wait_seconds": statistics.mean(row["mean_wait_seconds"] for row in rows),
        "max_unresolved": max(row["unresolved"] for row in rows),
        "bottleneck_frequency": dict(bottlenecks.most_common()), "runs": rows,
        "placement_fingerprint":expected_placement}


def paired_trials(profile, reference, selected, count=100, progress=None):
    if (reference.context, reference.lab_class, reference.lab_floor) != (selected.context, selected.lab_class, selected.lab_floor):
        raise ValueError("Eşlenmiş karşılaştırmada başlangıç yerleşimleri aynı olmalı.")
    if reference.context=='recess' and reference.placement_seed!=selected.placement_seed:
        raise ValueError('Eşlenmiş teneffüs karşılaştırmasında yerleşim numarası aynı olmalı.')
    selected = replace(selected, seed=reference.seed)
    left = run_trials(profile, reference, count, (lambda value: progress(value * .5)) if progress else None)
    right = run_trials(profile, selected, count, (lambda value: progress(.5 + value * .5)) if progress else None)
    if reference.context=='recess' and left['placement_fingerprint']!=right['placement_fingerprint']:
        raise ValueError('Eşlenmiş teneffüs karşılaştırmasında öğrenci yerleşimleri aynı değil.')
    differences = []
    for a, b in zip(left["runs"], right["runs"]):
        if a["unresolved"] == b["unresolved"] == 0:
            differences.append(a["assembly_seconds_after_shaking"] - b["assembly_seconds_after_shaking"])
    complete = len(differences) == count
    return {"reference": left, "selected": right, "paired_complete_runs": len(differences),
        "all_pairs_complete": complete,
        "median_seconds_saved": quantile(differences, .5) if complete else None,
        "p05_seconds_saved": quantile(differences, .05) if complete else None,
        "p95_seconds_saved": quantile(differences, .95) if complete else None,
        "selected_faster_run_count": sum(value > .000001 for value in differences) if complete else None,
        "interpretation": "Same student random draws; variability of this model, not a calibrated prediction interval"}


def strategy_trials(profile, settings, count=30, progress=None):
    if settings.context=='recess':
        variants=[
            ('Arkadaş grupları · kısa rota',replace(settings,policy='shortest',release_interval=0)),
            ('Arkadaş grupları · dağıtılmış',replace(settings,policy='balanced',release_interval=0)),
            ('Arkadaş grupları · 1 sn başlangıç aralığı',replace(settings,policy='balanced',release_interval=1)),
            ('Arkadaş grupları · 3 sn başlangıç aralığı',replace(settings,policy='balanced',release_interval=3)),
        ]
    else:variants = [
        ("Bireysel · kısa rota", replace(settings, policy="shortest", group_mode=False, release_interval=0)),
        ("Bireysel · dağıtılmış", replace(settings, policy="balanced", group_mode=False, release_interval=0)),
        ("Sınıfça · dağıtılmış", replace(settings, policy="balanced", group_mode=True, release_interval=0)),
        ("Sınıfça · 3 sn başlangıç aralığı", replace(settings, policy="balanced", group_mode=True, release_interval=3)),
    ]
    results = []
    for index, (label, parameters) in enumerate(variants):
        summary = run_trials(profile, parameters, count,
            (lambda value, index=index: progress((index + value) / len(variants))) if progress else None)
        results.append({"label": label, "summary": summary})
    ranked = sorted((row for row in results if row["summary"]["incomplete_runs"] == 0),
                    key=lambda row: row["summary"]["median_seconds_completed_only"])
    return {"variants": results, "fastest_complete_model_variant": ranked[0]["label"] if ranked else None,
            "note": ("Friend groups remain together in every variant; fixed placement, experimental group release order; not an approved evacuation instruction"
                     if settings.context=='recess' else "Experimental class order follows release_order; not an approved evacuation instruction")}


# =========================================================
# DRILL MILESTONES, COVERAGE AND ERROR WITHOUT AUTOMATIC FITTING
# =========================================================
EVENTS = {"first_move", "last_exit", "last_assembly"}


def milestone(result, event, class_id="ALL"):
    people = [person for person in result["persons"] if class_id == "ALL" or person["class_id"] == class_id]
    if not people:
        return None
    if event == "first_move":
        times = [segment["start"] for person in people for segment in person["segments"] if segment["state"] == "moving"]
        value = min(times) if times else None
    else:
        key = "outside_at" if event == "last_exit" else "arrived_at"
        times = [person[key] for person in people]
        value = max(times) if all(t is not None for t in times) else None
    return value - result["settings"]["shaking_seconds"] if value is not None else None


def compare_drill(result, observations):
    rows, errors, keys = [], [], set()
    class_ids = {person["class_id"] for person in result["persons"]} | {"ALL"}
    for row in observations:
        event, class_id, observed = row["event"], row.get("class_id", "ALL"), row["seconds_after_shaking"]
        if event not in EVENTS or class_id not in class_ids:
            raise ValueError("Bilinmeyen tatbikat olayı veya şube.")
        if isinstance(observed, bool) or not isinstance(observed, (float, int)) or not math.isfinite(observed) or observed < 0:
            raise ValueError("Tatbikat zamanı sonlu ve sıfır veya daha büyük olmalı.")
        if (event, class_id) in keys:
            raise ValueError("Aynı olay/şube için çift kayıt var.")
        keys.add((event, class_id))
        predicted = milestone(result, event, class_id)
        error = predicted - observed if predicted is not None else None
        if error is not None:
            errors.append(abs(error))
        rows.append({**row, "class_id": class_id, "model_seconds": predicted, "error_seconds": error})
    # Chronology is checked within the same observed population, never across unrelated classes.
    for class_id in class_ids:
        values = {row["event"]: row["seconds_after_shaking"] for row in rows if row["class_id"] == class_id}
        ordered = [values[event] for event in ("first_move", "last_exit", "last_assembly") if event in values]
        if ordered != sorted(ordered):
            raise ValueError("Tatbikat olaylarının zaman sırası hatalı.")
    return {"rows": rows, "matched_count": len(errors), "observation_count": len(rows),
            "mae_seconds": statistics.mean(errors) if errors else None,
            "model_calibrated": False, "note": "Comparison only; independent drill validation and parameter fitting are separate"}
