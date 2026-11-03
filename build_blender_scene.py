"""Run with Blender --background --python; creates only the named pilot output files."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:]
source,out=Path(args[0]).resolve(),Path(args[1]).resolve()
if not out.is_dir():out.mkdir(parents=True)
payload=json.loads(source.read_text(encoding='utf-8'))
if payload.get('model_status')!='illustrative_uncalibrated' or len(payload['student_ids'])!=111:
    raise ValueError('Expected the anonymous 111-student pilot payload')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12
scene.render.resolution_x=1000;scene.render.resolution_y=750;scene.render.resolution_percentage=100
scene.render.fps=1;scene.frame_start=0;scene.frame_end=math.ceil(payload['frames'][-1]['time_seconds_from_onset'])
scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.93,.96,1.,1.)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8


def material(name,color,alpha=1.):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,alpha);mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(*color,alpha)
    bsdf.inputs['Alpha'].default_value=alpha
    return mat


def line(name,a,b,color=(.06,.4,.48),radius=.045):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=radius;curve.bevel_resolution=1
    poly=curve.splines.new('POLY');poly.points.add(1)
    poly.points[0].co=(*a,1);poly.points[1].co=(*b,1)
    obj=bpy.data.objects.new(name,curve);scene.collection.objects.link(obj);obj.data.materials.append(material(name+'_mat',color))


world=payload['layout']['world'];w,d,h=world['width_m_assumed'],world['depth_m_assumed'],world['floor_height_m_assumed']
for floor,height in [('B2',-2),('B1',-1),('G',0),('M',.5)]+[(str(i),i) for i in range(1,7)]:
    z=height*h;corners=[(0,0,z),(w,0,z),(w,d,z),(0,d,z),(0,0,z)]
    for i,(a,b) in enumerate(zip(corners,corners[1:])):line(f'Floor_{floor}_{i}',a,b,(.42,.5,.6),.025)
    bpy.ops.object.text_add(location=(-2,-1.5,z+.15),rotation=(math.pi/2,0,0))
    text=bpy.context.object;text.name='Label_'+floor;text.data.body={'G':'ZEMIN','M':'ASMA'}.get(floor,floor+'. KAT');text.data.size=.65
    text.data.materials.append(material('Text_'+floor,(.08,.16,.25)))
for path in payload['paths']:line('Path_'+path['id'],path['a'],path['b'])
for index,identifier in enumerate(payload['student_ids']):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.18)
    obj=bpy.context.object;obj.name='Student_'+identifier;obj['anonymous_student_id']=identifier
    mat=material('Color_'+identifier,(.2,.5,.8));obj.data.materials.append(mat)
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    for frame in payload['frames']:
        t=frame['time_seconds_from_onset'];obj.location=frame['points'][index];obj.keyframe_insert(data_path='location',frame=t)
        color=(*frame['colors'][index],1.)
        bsdf.inputs['Base Color'].default_value=color;bsdf.inputs['Base Color'].keyframe_insert(data_path='default_value',frame=t)
    if obj.animation_data and obj.animation_data.action:
        for curve in getattr(obj.animation_data.action,'fcurves',[]):
            for key in curve.keyframe_points:key.interpolation='LINEAR'
bpy.ops.object.camera_add(location=(43,-38,33))
camera=bpy.context.object;camera.rotation_euler=(Vector((12,8,6))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=48
bpy.ops.object.light_add(type='AREA',location=(10,-10,35));bpy.context.object.data.energy=1800;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=30
bpy.ops.mesh.primitive_cube_add(size=1,location=(30,5,-.08));field=bpy.context.object;field.name='ProposedField_Illustrative'
field.scale=(6,5,.05);field.data.materials.append(material('Field',(.64,.84,.73)))
scene['model_status']='Illustrative student-flow model; no surveyed geometry or structural analysis'
scene.frame_set(round(scene.frame_end*.55))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'school_evacuation_v02.blend'))
scene.render.filepath=str(out/'school_evacuation_v02.png')
bpy.ops.render.render(write_still=True)
# Validate the independently generated USD using Blender's USD reader in this isolated scene.
usd=source.with_suffix('.usda');usd_result=None
if usd.is_file():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    status=bpy.ops.wm.usd_import(filepath=str(usd))
    usd_result={'status':sorted(status),'objects':len(bpy.data.objects),
                'point_clouds':{o.name:len(o.data.points) for o in bpy.data.objects if o.type=='POINTCLOUD'}}
(out/'blender_verification.json').write_text(json.dumps({'student_meshes_saved':111,'frames':len(payload['frames']),
    'usd_import':usd_result,'omniverse_tested':False},indent=2),encoding='utf-8')
