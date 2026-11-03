"""Illustrative, capacity-limited student network; not a validated egress model."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import math
import random
import hashlib

import simpy

ROUTES = ("left", "right", "fire")
ROUTE_LABELS = {"left": "Sol iç merdiven", "right": "Sağ iç merdiven", "fire": "Yangın merdiveni"}
LEVELS = {"B2": -2., "B1": -1., "G": 0., "M": .5, **{str(i): float(i) for i in range(1, 7)}}
DOWN = {"6": "5", "5": "4", "4": "3", "3": "2", "2": "1", "1": "M", "M": "G", "B2": "B1", "B1": "G"}


# =========================================================
# EDITABLE EXAMPLE ASSUMPTIONS, NEVER MEASURED GEOMETRY
# =========================================================
@dataclass(frozen=True)
class Settings:
    context: str = "lesson"
    lab_class: str = "10A"
    lab_floor: str = "5"
    policy: str = "balanced"
    closed_routes: tuple[str, ...] = ()
    gate_open: bool = True
    door_width: float = .9
    dining_door_width: float = 1.2
    corridor_width: float = 1.6
    stair_width: float = 1.1
    exit_width: float = 1.2
    gate_width: float = 1.8
    corridor_length: float = 10.
    stair_length_per_floor: float = 8.
    outdoor_length: float = 20.
    walking_speed: float = 1.
    stair_speed: float = .5
    reaction_mean: float = 12.
    reaction_spread: float = 6.
    shaking_seconds: float = 20.
    flow_per_m: float = 1.2
    stair_flow_per_m: float = .8
    storage_persons_per_m2: float = 2.
    horizon_seconds: float = 900.
    seed: int = 42
    placement_seed: int = 42
    speed_cv: float = 0.
    class_reaction_spread: float = 0.
    group_mode: bool = False
    release_interval: float = 0.
    release_order: tuple[str, ...] = ()
    edge_overrides: tuple[tuple[str, float, float], ...] = ()
    class_routes: tuple[tuple[str, str], ...] = ()
    class_delays: tuple[tuple[str, float], ...] = ()

    def validate(self):
        if self.context not in {"lesson", "lunch", "lab", "recess"} or self.policy not in {"balanced", "shortest"}:
            raise ValueError("Unsupported scenario or route allocation")
        if set(self.closed_routes) - set(ROUTES) or type(self.gate_open) is not bool:
            raise ValueError("Invalid route closure")
        if self.lab_floor not in {"5", "B2"}:
            raise ValueError("Select one of the two observed laboratory floors")
        for name in ("door_width", "dining_door_width", "corridor_width", "stair_width", "exit_width", "gate_width"):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or not .3 <= value <= 10:
                raise ValueError(f"Invalid example width: {name}")
        bounds = {"corridor_length": (.5, 200), "stair_length_per_floor": (1, 100),
                  "outdoor_length": (.5, 500), "walking_speed": (.1, 3), "stair_speed": (.1, 2),
                  "reaction_mean": (0, 300), "reaction_spread": (0, 300), "shaking_seconds": (0, 300),
                  "flow_per_m": (.05, 5), "stair_flow_per_m": (.05, 5),
                  "storage_persons_per_m2": (.1, 5), "horizon_seconds": (1, 3600),
                  "speed_cv": (0, .5), "class_reaction_spread": (0, 120), "release_interval": (0, 60)}
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"Invalid example parameter: {name}")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("Invalid repeatability seed")
        if type(self.placement_seed) is not int or not 0 <= self.placement_seed < 2**32:
            raise ValueError("Invalid recess placement seed")
        if type(self.group_mode) is not bool or len(set(self.release_order)) != len(self.release_order):
            raise ValueError("Invalid class movement setting")
        seen = set()
        for key, length, width in self.edge_overrides:
            if key in seen or not isinstance(key,str) or not key:
                raise ValueError("Duplicate or invalid measured edge")
            seen.add(key)
            if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (length,width)) or not .1 <= length <= 500 or not .3 <= width <= 10:
                raise ValueError("Invalid user-entered edge measurements")
        for assignments,route_values in ((self.class_routes,True),(self.class_delays,False)):
            assigned=set()
            for class_id,value in assignments:
                if not isinstance(class_id,str) or not class_id or class_id in assigned:
                    raise ValueError('Duplicate or invalid class plan entry')
                assigned.add(class_id)
                if route_values:
                    valid_routes = ROUTES + (("yard",) if self.context == "recess" else ())
                    if value not in valid_routes or value in self.closed_routes:raise ValueError('Class plan uses an unavailable route')
                elif isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=60:
                    raise ValueError('Invalid additional class delay')


def unit_id(item):
    """Class movement unit normally; a pair/trio movement unit during recess."""
    return item.get("group_id", item["class_id"])


def student_groups(profile, settings):
    from validate import population_snapshot
    placement = {"mode": "home_floors"}
    if settings.context == "lunch":
        placement = {"mode": "all_students", "destination_floor": "B1"}
    elif settings.context == "lab":
        placement = {"mode": "move_classes", "class_destinations": {settings.lab_class: settings.lab_floor}}
    population_snapshot(profile, {"id": "model", "placement": placement})
    if settings.context == "recess":
        from recess import placement_groups
        return placement_groups(profile, settings.placement_seed)
    result = []
    for row in profile["classes"]:
        floor = "B1" if settings.context == "lunch" else row["home_floor"]
        if settings.context == "lab" and row["id"] == settings.lab_class:
            floor = settings.lab_floor
        result.append({"class_id": row["id"], "students": row["students"], "floor": floor,
                       "origin": "dining" if settings.context == "lunch" else "room_" + row["id"]})
    return result


# =========================================================
# SHARED STAIR SEGMENTS, INTERMEDIATE MEZZANINE AND FIELD GATE
# =========================================================
def build_network(profile, settings):
    settings.validate()
    groups = student_groups(profile, settings)
    nodes, edges = {}, {}
    overrides = {key:(length,width) for key,length,width in settings.edge_overrides}
    def node(key, x, y, label=""):
        nodes[key] = {"x": x, "y": y, "label": label}
    def edge(key, source, target, length, width, kind, label):
        measured = key in overrides
        if measured:
            length,width = overrides[key]
        edges[key] = {"id": key, "source": source, "target": target, "length": length,
                      "width": width, "kind": kind, "label": label,
                      "geometry_source": "user-entered measurement; not independently verified" if measured else "editable illustration; not site measurements"}
    for floor, height in LEVELS.items():
        node("hall_" + floor, 12, height * 8)
        for route, x in zip(ROUTES, (20, 30, 40)):
            if route == "fire" and height < 0:
                continue  # No unverified basement/fire-stair connection is invented.
            node(f"{route}_{floor}", x, height * 8)
            if route not in settings.closed_routes:
                edge(f"corridor_{route}_{floor}", "hall_" + floor, f"{route}_{floor}",
                     settings.corridor_length, settings.corridor_width, "walk", f"{floor} · {ROUTE_LABELS[route]} bağlantısı")
                if floor != "G":
                    lower = DOWN[floor]
                    distance = abs(LEVELS[floor] - LEVELS[lower]) * settings.stair_length_per_floor
                    edge(f"stair_{route}_{floor}", f"{route}_{floor}", f"{route}_{lower}",
                         distance, settings.stair_width, "stair", f"{ROUTE_LABELS[route]} · {floor} → {lower}")
    origin_counts = Counter()
    for group in groups:
        if group["origin"] in nodes:
            continue
        slot = origin_counts[group["floor"]]
        origin_counts[group["floor"]] += 1
        node(group["origin"], 2 + slot * 4, LEVELS[group["floor"]] * 8,
             group.get("area_label", "Yemekhane" if settings.context == "lunch" else group["class_id"]))
        if settings.context == "recess":
            from building_geometry import default_building
            yard = group["origin_kind"] == "yard"
            if yard:
                target_point = [26., 5.]
                edge("recess_link_" + group["origin"], group["origin"], "field_gate",
                     max(.5, math.dist(group["point"], target_point)), settings.corridor_width,
                     "walk", group["area_label"] + " bağlantısı")
            elif group["origin_kind"] == "room":
                room_id = group["room_id"]
                room = default_building()["floors"][group["floor"]]["rooms"][room_id]
                door_node = f"recess_door_{group['floor']}_{room_id}"
                node(door_node, *room["door"], "Oda kapısı · " + room["label"])
                nodes[door_node].update(kind="recess_room_door", floor=group["floor"], room_id=room_id)
                edge("recess_link_" + group["origin"], group["origin"], door_node,
                     max(.5, math.dist(group["point"], room["door"])), settings.corridor_width,
                     "walk", room["label"] + " içi bağlantı")
                door_edge = f"recess_roomdoor_{group['floor']}_{room_id}"
                if door_edge not in edges:
                    edge(door_edge, door_node, "hall_" + group["floor"], 1.,
                         settings.dining_door_width if room["kind"] == "dining" else settings.door_width,
                         "door", room["label"] + " kapısı")
            else:
                target_point = default_building()["floors"][group["floor"]]["hall"]
                edge("recess_link_" + group["origin"], group["origin"], "hall_" + group["floor"],
                     max(.5, math.dist(group["point"], target_point)), settings.corridor_width,
                     "walk", group["area_label"] + " bağlantısı")
            continue
        edge("door_" + group["origin"], group["origin"], "hall_" + group["floor"], 1.,
             settings.dining_door_width if settings.context == "lunch" else settings.door_width,
             "door", "Yemekhane kapısı" if settings.context == "lunch" else group["class_id"] + " kapısı")
    node("field_gate", 50, -26, "Saha geçişi")
    node("assembly", 62, -26, "Önerilen saha")
    for route, x in zip(ROUTES, (46, 48, 50)):
        node("yard_" + route, x, -3, "Dışarıda")
        if route not in settings.closed_routes:
            edge("exit_" + route, f"{route}_G", "yard_" + route, 1., settings.exit_width, "exit",
                 ROUTE_LABELS[route] + " dış çıkışı")
            edge("outside_" + route, "yard_" + route, "field_gate", settings.outdoor_length,
                 settings.corridor_width, "walk", ROUTE_LABELS[route] + " → saha yolu")
    if settings.gate_open:
        edge("field_gate_edge", "field_gate", "assembly", 2., settings.gate_width, "gate", "Ortak saha geçişi")
    network = {"nodes": nodes, "edges": edges, "groups": groups,
               "inactive_or_unknown_measurement_ids": sorted(set(overrides)-set(edges))}
    if settings.context == "recess":
        from recess import placement_fingerprint
        network["placement_fingerprint"] = placement_fingerprint(groups)
    return network


def candidate_path(network, group, route, settings):
    if group.get("origin_kind") == "yard":
        if route != "yard":
            return None
        path = ["recess_link_" + group["origin"]]
        if settings.gate_open:
            path.append("field_gate_edge")
        return path if all(key in network["edges"] for key in path) else None
    floor = group["floor"]
    if route in settings.closed_routes or (route == "fire" and LEVELS[floor] < 0):
        return None
    connector = "recess_link_" if settings.context == "recess" else "door_"
    path = [connector + group["origin"]]
    if settings.context == "recess" and group.get("origin_kind") == "room":
        path.append(f"recess_roomdoor_{floor}_{group['room_id']}")
    path.append(f"corridor_{route}_{floor}")
    while floor != "G":
        path.append(f"stair_{route}_{floor}")
        floor = DOWN[floor]
    path.append("exit_" + route)
    if settings.gate_open:
        path.extend(["outside_" + route, "field_gate_edge"])
    if not all(key in network["edges"] for key in path):
        return None
    return path


# =========================================================
# FIFO ADMISSION, FINITE STORAGE AND UPSTREAM BACKPRESSURE
# =========================================================
class Passage:
    def __init__(self, env, definition, settings):
        self.env, self.definition = env, definition
        stair = definition["kind"] == "stair"
        self.speed = settings.stair_speed if stair else settings.walking_speed
        flow = settings.stair_flow_per_m if stair else settings.flow_per_m
        self.headway = 1 / (definition["width"] * flow)
        self.slots = max(1, math.floor(definition["length"] * definition["width"] * settings.storage_persons_per_m2))
        self.space = simpy.Resource(env, self.slots)
        self.admission = simpy.Resource(env, 1)
        self.next_entry = 0.
        self.waiting, self.peak_queue, self.entered, self.wait_seconds, self.peak_occupancy = 0, 0, 0, 0., 0

    def enter(self):
        started = self.env.now
        self.waiting += 1
        self.peak_queue = max(self.peak_queue, self.waiting)
        with self.admission.request() as turn:
            yield turn
            token = self.space.request()
            yield token
            yield self.env.timeout(max(0., self.next_entry - self.env.now))
            self.next_entry = self.env.now + self.headway
            self.waiting -= 1
            self.entered += 1
            self.wait_seconds += self.env.now - started
            self.peak_occupancy = max(self.peak_occupancy, self.space.count)
        return token


def simulate(profile, settings=Settings()):
    network = build_network(profile, settings)
    env = simpy.Environment()
    passages = {key: Passage(env, value, settings) for key, value in network["edges"].items()}
    loads, persons = Counter(), []
    classes = [unit_id(group) for group in network["groups"]]
    if set(settings.release_order) - set(classes):
        raise ValueError("Release order references an unknown class")
    if (set(dict(settings.class_routes))|set(dict(settings.class_delays)))-set(classes):
        raise ValueError('Class plan references an unknown class')
    forced_routes=dict(settings.class_routes);class_delays=dict(settings.class_delays)
    order = list(settings.release_order) + [key for key in classes if key not in settings.release_order]

    # =========================================================
    # KEYED RANDOM DRAWS AND CLASS START, ROUTE AND PACE
    # =========================================================
    def random_stream(label):
        digest = hashlib.sha256(f"{settings.seed}:{label}".encode()).digest()
        return random.Random(int.from_bytes(digest[:8], "big"))

    behaviors = {}
    for group in network["groups"]:
        class_offset = random_stream(group["class_id"] + ":class_delay").uniform(-.5, .5) * settings.class_reaction_spread
        members = []
        for index in range(group["students"]):
            identifier = group["members"][index]["id"] if settings.context == "recess" else f"{group['class_id']}_{index + 1:02d}"
            noise = random_stream(identifier + ":reaction").uniform(-.5, .5) * settings.reaction_spread
            sigma = math.sqrt(math.log1p(settings.speed_cv**2))
            factor = random_stream(identifier + ":speed").lognormvariate(-sigma**2 / 2, sigma)
            factor = min(1.6, max(.5, factor))
            ready = max(0., settings.reaction_mean + class_offset + noise)
            ready += order.index(unit_id(group)) * settings.release_interval
            ready += class_delays.get(unit_id(group),0.)
            item = {"speed_factor": factor, "ready_seconds": ready}
            behaviors[identifier] = item
            members.append(item)
        if settings.group_mode or settings.context == "recess":
            pace, ready = min(item["speed_factor"] for item in members), max(item["ready_seconds"] for item in members)
            for item in members:
                item.update(speed_factor=pace, ready_seconds=ready)

    def travel(person, path):
        if path is None:
            person["status"] = "unreachable"
            person["active"] = {"start": 0., "node": person["origin"], "state": "unreachable"}
            return
        departure = settings.shaking_seconds + person["ready_seconds"]
        person["departure_at"] = departure
        person["segments"].append({"start": 0., "end": settings.shaking_seconds, "state": "protecting", "node": person["origin"]})
        person["segments"].append({"start": settings.shaking_seconds, "end": departure, "state": "preparing", "node": person["origin"]})
        person["active"] = {"start": 0., "node": person["origin"], "state": "protecting"}
        yield env.timeout(departure)
        previous, held = None, None
        for key in path:
            passage = passages[key]
            edge = passage.definition
            started = env.now
            person["active"] = {"start": started, "node": edge["source"], "state": "queued", "edge": key}
            token = yield env.process(passage.enter())
            if previous is not None:
                previous.space.release(held)
            person["segments"].append({"start": started, "end": env.now, "state": "queued", "node": edge["source"], "edge": key})
            person["wait_seconds"] += env.now - started
            duration = edge["length"] / (passage.speed * person["speed_factor"])
            end = env.now + duration
            segment = {"start": env.now, "end": end, "state": "moving", "edge": key}
            person["segments"].append(segment)
            person["active"] = segment.copy()
            yield env.timeout(duration)
            if edge["kind"] == "exit":
                person["outside_at"] = env.now
            previous, held = passage, token
        if previous is not None:
            previous.space.release(held)
        if settings.gate_open:
            person["status"], person["arrived_at"] = "assembled", env.now
            node = "assembly"
        else:
            person["status"] = "outside_unassembled"
            node = network["edges"][path[-1]]["target"]
        person["active"] = {"start": env.now, "node": node, "state": person["status"]}

    for group in network["groups"]:
        routes = ("yard",) if group.get("origin_kind") == "yard" else ROUTES
        candidates = [(route, candidate_path(network, group, route, settings)) for route in routes]
        candidates = [(route, path) for route, path in candidates if path is not None]
        if unit_id(group) in forced_routes:
            candidates=[row for row in candidates if row[0]==forced_routes[unit_id(group)]]
            if not candidates:raise ValueError('Class plan has no connected route for '+unit_id(group))
        group_choice = None
        for index in range(group["students"]):
            def score(candidate):
                route, path = candidate
                free_time = sum(network["edges"][key]["length"] / passages[key].speed for key in path)
                route_wait = loads[route] * max((passages[key].headway for key in path if key.startswith(("stair_", "exit_"))), default=0.)
                return free_time + (route_wait if settings.policy == "balanced" else 0.)
            cohesive = settings.group_mode or settings.context == "recess"
            if cohesive and group_choice is not None:
                route, path = group_choice
            else:
                route, path = min(candidates, key=score) if candidates else (None, None)
                if cohesive:
                    group_choice = (route, path)
            if route:
                loads[route] += 1
            identifier = group["members"][index]["id"] if settings.context == "recess" else f"{group['class_id']}_{index + 1:02d}"
            person = {"id": identifier, "class_id": group["class_id"],
                      "floor": group["floor"], "origin": group["origin"], "route": route,
                      "status": "pending", "outside_at": None, "arrived_at": None,
                      "wait_seconds": 0., "segments": [], "active": None, "departure_at": None,
                      **behaviors[identifier]}
            if settings.context == "recess":
                person.update(group_id=group["group_id"], origin_kind=group["origin_kind"],
                              initial_point=group["members"][index]["point"])
                if group["origin_kind"] == "yard":
                    person["outside_at"] = 0.
            persons.append(person)
            person["process"] = env.process(travel(person, path))
    complete = simpy.events.AllOf(env, [person["process"] for person in persons])
    env.run(until=complete | env.timeout(settings.horizon_seconds))
    for person in persons:
        del person["process"]
        if person["status"] == "pending":
            person["status"] = "timeout"
            if person["active"] and person["active"]["state"] == "queued":
                person["wait_seconds"] += env.now - person["active"]["start"]
    total = len(persons)
    assembled = sum(person["arrived_at"] is not None for person in persons)
    outside = sum(person["outside_at"] is not None for person in persons)
    last_assembly = max((person["arrived_at"] for person in persons if person["arrived_at"] is not None), default=None)
    last_exit = max((person["outside_at"] for person in persons if person["outside_at"] is not None), default=None)
    queues = [{**passage.definition, "peak_queue": passage.peak_queue, "entered": passage.entered,
               "total_wait_seconds": passage.wait_seconds, "storage_slots": passage.slots,
               "peak_occupancy": passage.peak_occupancy}
              for passage in passages.values()]
    return {"schema_version": 2, "model_status": "illustrative_uncalibrated", "population_scope": "students_only",
            "settings": asdict(settings), "network": network, "persons": persons,
            "metrics": {"students": total, "assembled": assembled, "outside": outside,
                "unresolved": total - assembled, "unreachable": sum(p["status"] == "unreachable" for p in persons),
                "timed_out": sum(p["status"] == "timeout" for p in persons),
                "assembly_seconds_after_shaking": last_assembly - settings.shaking_seconds if assembled == total and last_assembly is not None else None,
                "exit_seconds_after_shaking": last_exit - settings.shaking_seconds if outside == total and last_exit is not None else None,
                "mean_wait_seconds": sum(p["wait_seconds"] for p in persons) / total if total else 0.,
                "max_wait_seconds": max((p["wait_seconds"] for p in persons), default=0.),
                "elapsed_seconds_from_onset": env.now},
            "queues": sorted(queues, key=lambda item: item["total_wait_seconds"], reverse=True),
            "route_allocations": dict(loads)}


def position_at(result, person, timestamp):
    nodes = result["network"]["nodes"]
    for segment in person["segments"]:
        if segment["start"] <= timestamp < segment["end"]:
            if segment["state"] == "moving":
                edge = result["network"]["edges"][segment["edge"]]
                start, end = nodes[edge["source"]], nodes[edge["target"]]
                ratio = (timestamp - segment["start"]) / (segment["end"] - segment["start"])
                return start["x"] + ratio * (end["x"] - start["x"]), start["y"] + ratio * (end["y"] - start["y"]), "moving"
            node = nodes[segment["node"]]
            return node["x"], node["y"], segment["state"]
    segment = person["active"] or {"node": person["origin"], "state": "preparing"}
    if segment.get("node"):
        node = nodes[segment["node"]]
    else:
        edge = result["network"]["edges"][segment["edge"]]
        node = nodes[edge["target"]] if timestamp >= segment["end"] else nodes[edge["source"]]
    return node["x"], node["y"], segment["state"]
