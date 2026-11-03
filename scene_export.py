"""Portable point animation from the same model trajectories; no Omniverse runtime required."""
import json
import math
import copy

from engine import LEVELS
from spatial import world_position, world_node,world_edge_points
from building_geometry import building
from visuals import COLORS


def color_rgb(state):
    value=COLORS.get(state,"#dc5965").lstrip("#")
    return [int(value[i:i+2],16)/255 for i in (0,2,4)]


def scene_payload(result,layout,samples=80):
    if type(samples) is not int or not 2<=samples<=300:
        raise ValueError("2–300 görsel örnek seçin.")
    end=max(1.,result["metrics"]["elapsed_seconds_from_onset"])
    times=sorted(set([0.,end]+[end*i/(samples-1) for i in range(samples)]))
    frames=[]
    for time in times:
        locations=[world_position(result,layout,person,time) for person in result["persons"]]
        # Offset only points in the proposed field to make coincident arrivals legible.
        points=[]
        for index,(point,state) in enumerate(locations):
            point=list(point)
            if state=="assembled":
                point[0]+=(index%12-5.5)*.25
                point[1]+=(index//12-4.5)*.25
            point[2]+=.25
            points.append(point)
        frames.append({"time_seconds_from_onset":time,"points":points,
                       "colors":[color_rgb(state) for _,state in locations]})
    paths=[{"id":edge["id"],"a":world_node(result,layout,edge["source"]),
            "b":world_node(result,layout,edge["target"]),'points':world_edge_points(result,layout,edge)} for edge in result["network"]["edges"].values()]
    export_layout=copy.deepcopy(layout);export_layout['building_geometry']=copy.deepcopy(building(layout))
    return {"schema_version":2,"model_status":"illustrative_uncalibrated","units":"assumed metres; dimensions not surveyed",
            "time_codes_per_second":1,"student_ids":[p["id"] for p in result["persons"]],
            "settings":result["settings"],"layout":export_layout,"frames":frames,"paths":paths,
            "note":"Sampled animation of model trajectories; positions between samples are interpolated; no RTX/Omniverse test performed"}


# =========================================================
# OPENUSD POINTS WITH TIME SAMPLES AND EXPLICIT PROVENANCE
# =========================================================
def usda_text(payload):
    def vec(value): return "("+", ".join(f"{number:.6f}" for number in value)+")"
    frames=payload["frames"];layout=payload["layout"];world=layout["world"]
    lines=['#usda 1.0','(', '    defaultPrim = "School"','    upAxis = "Z"','    metersPerUnit = 1',
           '    timeCodesPerSecond = 1','    framesPerSecond = 1','    startTimeCode = 0',
           f'    endTimeCode = {frames[-1]["time_seconds_from_onset"]:.6f}',
           '    customLayerData = { string modelStatus = "illustrative_uncalibrated_not_surveyed" }',')',
           'def Xform "School" {','    custom string scope = "111 students only; sample geometry; not an approved evacuation plan"']
    from school_scene import Mesh,room_walls
    for floor,height in LEVELS.items():
        plan=building(layout)['floors'][floor];z=height*world['floor_height_m_assumed'];mesh=Mesh()
        mesh.surface(plan['outline'],z,'#dce5ef')
        for room in plan['rooms'].values():room_walls(mesh,room['polygon'],room['door'],z,1.2,'#b9cadc')
        lines.extend([f'    def Mesh "Floor_{floor}" {{',
            '        point3f[] points = ['+', '.join(vec(p) for p in mesh.vertices)+']',
            '        int[] faceVertexCounts = ['+', '.join('3' for _ in mesh.faces)+']',
            '        int[] faceVertexIndices = ['+', '.join(str(i) for face in mesh.faces for i in face)+']',
            '        uniform token subdivisionScheme = "none"',
            '        bool doubleSided = true',
            '        color3f[] primvars:displayColor = [(0.7, 0.78, 0.86)]',
            '        float[] primvars:displayOpacity = [0.55]','    }'])
    lines.extend(['    def BasisCurves "Paths" {','        uniform token type = "linear"',
        '        uniform token wrap = "nonperiodic"',
        '        int[] curveVertexCounts = ['+', '.join(str(len(edge.get('points',[edge['a'],edge['b']]))) for edge in payload['paths'])+']',
        '        point3f[] points = ['+', '.join(vec(p) for edge in payload['paths'] for p in edge.get('points',[edge['a'],edge['b']]))+']',
        '        float[] widths = [0.06] (interpolation = "constant")',
        '        color3f[] primvars:displayColor = [(0.2, 0.55, 0.6)]','    }',
        '    def Points "Students" {',
        '        int64[] ids = ['+', '.join(str(i) for i in range(len(payload["student_ids"])))+']',
        '        custom string[] studentLabels = '+json.dumps(payload["student_ids"]),
        '        float[] widths = [0.24] (interpolation = "constant")',
        '        point3f[] points.timeSamples = {'])
    for frame in frames:
        lines.append(f'            {frame["time_seconds_from_onset"]:.6f}: ['+', '.join(vec(p) for p in frame["points"])+'],')
    lines.extend(['        }','        color3f[] primvars:displayColor (interpolation = "vertex")',
                  '        color3f[] primvars:displayColor.timeSamples = {'])
    for frame in frames:
        lines.append(f'            {frame["time_seconds_from_onset"]:.6f}: ['+', '.join(vec(c) for c in frame["colors"])+'],')
    lines.extend(['        }','    }','}'])
    return '\n'.join(lines)+'\n'
