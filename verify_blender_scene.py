"""Reopen the generated blend and compare identities and endpoints with the source data."""
import json
from pathlib import Path
import sys
import bpy

folder=Path(sys.argv[sys.argv.index('--')+1]).resolve()
payload=json.loads((folder/'school_evacuation_v02.json').read_text(encoding='utf-8'))
objects={obj.name.removeprefix('Student_'):obj for obj in bpy.data.objects if obj.name.startswith('Student_')}
assert set(objects)==set(payload['student_ids'])
errors=[]
for time,expected in [(0,payload['frames'][0]),(bpy.context.scene.frame_end,payload['frames'][-1])]:
    bpy.context.scene.frame_set(time)
    for index,key in enumerate(payload['student_ids']):
        errors.append(max(abs(objects[key].location[axis]-expected['points'][index][axis]) for axis in range(3)))
assert max(errors)<.002,max(errors)
report={'reopened_saved_blend':True,'student_objects':len(objects),'max_endpoint_error_m':max(errors),
        'frame_end':bpy.context.scene.frame_end,'compared_endpoints':2,'omniverse_tested':False}
(folder/'blend_reopen_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
