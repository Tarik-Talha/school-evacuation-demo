"""Reproducible, hypothetical recess groups across accessible school spaces.

These positions describe a scenario draw, never observed student locations.
They do not depend on the evacuation strategy or behavior trial seed.
"""
from __future__ import annotations

import hashlib
import json
import math
import random

from building_geometry import default_building, inside


# =========================================================
# WALKABLE PATCHES AND ACCESSIBLE ROOM TYPES
# =========================================================
FLOORS = ("B2", "B1", "G", "M", "1", "2", "3", "4", "5", "6")
COMMON_PATCHES = {
    floor: ((7.1, 6.2, 10.2, 9.3), (11.1, 8.0, 15.4, 9.3))
    for floor in FLOORS
}
# B1's coarse dining polygon occupies the central hall. Use its free east
# circulation area rather than placing recess students through dining tables.
COMMON_PATCHES["B1"] = ((16.2, 7.25, 17.55, 8.9), (17.8, 7.25, 20.5, 9.0))
COMMON_PATCHES["5"] = ((10.9, 8.25, 13.6, 9.5), (13.8, 8.25, 15.4, 9.5),
                       (5.5, 4.5, 11.5, 5.9))
YARD_PATCHES = ((22.5, 3.0, 24.5, 8.5),)


def _in_rect(point, rect):
    x, y = point
    x0, y0, x1, y1 = rect
    return x0 < x < x1 and y0 < y < y1


def is_walkable(floor, point, origin_kind="common"):
    """Validate points against an illustrated accessible area, not a measured plan."""
    if origin_kind == "yard":
        return floor == "G" and any(_in_rect(point, p) for p in YARD_PATCHES)
    if floor not in FLOORS:
        return False
    geometry = default_building()["floors"][floor]
    if origin_kind == "common":
        if floor not in COMMON_PATCHES or not any(_in_rect(point, p) for p in COMMON_PATCHES[floor]):
            return False
        if not inside(point, geometry["outline"]):
            return False
        # Entrance and mezzanine hall polygons are accessible common areas.
        forbidden = [room["polygon"] for room in geometry["rooms"].values()
                     if room["kind"] != "hall"]
        forbidden += [room["polygon"] for room in geometry["service_rooms"]]
        if any(inside(point, polygon) for polygon in forbidden):
            return False
    elif origin_kind == "room":
        room_id = point[2] if len(point) > 2 else None
        room = geometry["rooms"].get(room_id)
        if room is None or room["kind"] not in {"classroom", "lab", "dining"}:
            return False
        if not inside(point[:2], room["polygon"]):
            return False
    else:
        return False
    return not any(_in_rect(point[:2], stair["bounds"]) for stair in geometry["stairs"].values())


def _sizes(count, rng):
    if type(count) is not int or count < 2:
        raise ValueError("Teneffüs grupları için her sınıfta en az iki öğrenci gerekir.")
    result = []
    while count:
        size = count if count <= 3 else (2 if count == 4 else rng.choice((2, 3)))
        result.append(size)
        count -= size
    return result


# =========================================================
# BOUNDED LOCATION SAMPLING WITH ALTERNATIVES ON THE SAME FLOOR
# =========================================================
def _sample_location(floor, location, count, rng, used_centers):
    kind = location['kind']
    room_id = location.get('room_id')
    if kind == 'room':
        polygon = location['room']['polygon']
        x0, y0 = min(p[0] for p in polygon), min(p[1] for p in polygon)
        x1, y1 = max(p[0] for p in polygon), max(p[1] for p in polygon)
    else:
        patches = YARD_PATCHES if kind == 'yard' else COMMON_PATCHES[floor]
        x0, y0, x1, y1 = patches[location.get('patch', 0)]
    if x1 - x0 <= .64 or y1 - y0 <= .64:
        return None
    for _ in range(256):
        center = [rng.uniform(x0 + .32, x1 - .32), rng.uniform(y0 + .32, y1 - .32)]
        angle = rng.uniform(0, 2 * math.pi)
        points = [[round(center[0] + .24 * math.cos(angle + i * 2 * math.pi / count), 6),
                   round(center[1] + .24 * math.sin(angle + i * 2 * math.pi / count), 6)]
                  for i in range(count)]
        if all(is_walkable(floor, [*point, room_id] if kind == 'room' else point, kind) for point in points) and all(
                math.dist(center, other) >= .5 for other in used_centers):
            return center, points
    return None


def placement_groups(profile, placement_seed):
    """Keep original IDs/classes, form pairs/trios, then spread them across school."""
    if type(placement_seed) is not int or not 0 <= placement_seed < 2**32:
        raise ValueError("Invalid recess placement seed")
    signature = json.dumps(profile["classes"], sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(f"recess-v1:{placement_seed}:{signature}".encode()).digest()
    rng = random.Random(int.from_bytes(digest[:16], "big"))
    groups = []
    for row in profile["classes"]:
        members = [{"id": f"{row['id']}_{i + 1:02d}", "class_id": row["id"]}
                   for i in range(row["students"])]
        rng.shuffle(members)
        cursor = 0
        for size in _sizes(row["students"], rng):
            group_id = f"R{len(groups) + 1:02d}"
            groups.append({"class_id": row["id"], "group_id": group_id,
                           "students": size, "members": members[cursor:cursor + size],
                           "origin": "recess_" + group_id})
            cursor += size

    # Keep groups spread across every modeled floor and the courtyard, then draw
    # a room/common-area location within each assigned floor.
    areas = list(FLOORS) + ["yard"]
    rng.shuffle(areas)
    destinations = [areas[index % len(areas)] for index in range(len(groups))]
    rng.shuffle(destinations)
    geometry = default_building()["floors"]
    floor_locations = {}
    for floor in FLOORS:
        locations = [{"kind": "common", "patch": patch}
                     for patch in range(len(COMMON_PATCHES[floor]))]
        locations.extend({"kind": "room", "room_id": room_id, "room": room}
                         for room_id, room in geometry[floor]["rooms"].items()
                         if room["kind"] in {"classroom", "lab", "dining"})
        floor_locations[floor] = locations
    occupied = {}
    for group, destination in zip(groups, destinations):
        yard = destination == "yard"
        floor = "G" if yard else destination
        options = [{"kind": "yard", "patch": 0}] if yard else floor_locations[floor]
        preferred = options[0] if yard else rng.choice(options)
        # A drawn patch can be unusable after room/stair exclusions. Try other
        # allowed spaces on that floor instead of retrying an impossible patch.
        for location in [preferred] + [option for option in options if option != preferred]:
            kind = location['kind']
            room_id = location.get('room_id')
            room = location.get('room')
            key = (floor, kind, room_id, location.get('patch', 0))
            used_centers = occupied.setdefault(key, [])
            sample = _sample_location(floor, location, group['students'], rng, used_centers)
            if sample is not None:
                center, points = sample
                break
        else:
            raise ValueError(f"Teneffüs ortak alanlarına çakışmasız yerleşim üretilemedi ({group['group_id']} · {floor}).")
        used_centers.append(center)
        group.update(floor=floor, origin_kind=kind, room_id=room_id,
                     point=[round(v, 6) for v in center],
                     area_label=("Bahçe / açık ortak alan" if yard else
                                 f"{floor} · {room['label']}" if kind == "room" else
                                 f"{floor} · ortak dolaşım alanı"))
        for member, point in zip(group["members"], points):
            member["point"] = point
    return groups


def placement_fingerprint(groups):
    return hashlib.sha256(json.dumps(groups, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()
