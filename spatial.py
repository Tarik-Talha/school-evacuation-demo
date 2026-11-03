"""Visual plan anchors; physical scale and class-room mapping retain provenance."""
import base64
import copy
import hashlib
import json
import math
from pathlib import Path

import plotly.graph_objects as go

from engine import LEVELS
from visuals import COLORS, STATE_LABELS
from building_geometry import building,center,geometry_room,origin_seat
from source_assets import source_plan
from state_store import read_json,write_json

ROOT = Path(__file__).resolve().parent


# =========================================================
# SOURCE PLANS, TENTATIVE MAPPINGS AND LOCAL USER OVERRIDES
# =========================================================
def load_layout():
    layout = json.loads((ROOT / "plan_layout.json").read_text(encoding="utf-8"))
    return read_json("user_layout.json",layout)


def validate_layout(layout, profile):
    expected = {row["id"]: row["home_floor"] for row in profile["classes"]}
    if set(layout["class_mapping"]) != set(expected):
        raise ValueError("Oda eşleştirmesinde şube eksik veya fazla.")
    assigned = set()
    for key, row in layout["class_mapping"].items():
        if row["floor"] != expected[key] or row["room_id"] not in layout["floors"][row["floor"]]["rooms"]:
            raise ValueError("Şube odası verilen ders katında olmalı.")
        slot = (row["floor"], row["room_id"])
        if slot in assigned:
            raise ValueError("Aynı derslik iki şubeye atanamaz.")
        assigned.add(slot)
        if type(row["user_confirmed"]) is not bool:
            raise ValueError("Eşleşme doğrulaması açıkça belirtilmeli.")
    for floor in layout["floors"].values():
        for point in [floor["hub"], *floor["stairs"].values(), *[r["center"] for r in floor["rooms"].values()], *[r["door"] for r in floor["rooms"].values()]]:
            if len(point) != 2 or not all(isinstance(v, (int,float)) and math.isfinite(v) for v in point):
                raise ValueError("Geçersiz plan koordinatı.")
    for value in layout["world"].values():
        if not isinstance(value,(int,float)) or not math.isfinite(value) or not .1 <= value <= 200:
            raise ValueError("Geçersiz örnek 3B boyutu.")
    return layout


def save_layout(layout, profile):
    validate_layout(layout, profile)
    write_json("user_layout.json",layout)


def node_floor(result, key):
    metadata = result["network"]["nodes"].get(key, {})
    if metadata.get("floor"):
        return metadata["floor"]
    if key.startswith("hall_"):
        return key[5:]
    for route in ("left", "right", "fire"):
        if key.startswith(route + "_"):
            return key[len(route)+1:]
    for group in result["network"]["groups"]:
        if group["origin"] == key:
            return 'SITE' if group.get('origin_kind')=='yard' else group["floor"]
    return "SITE"


def room_for(result, layout, key):
    if result['settings']['context']=='recess':
        group = next((row for row in result["network"]["groups"] if row["origin"] == key), None)
        metadata = result["network"]["nodes"].get(key, {})
        floor = group["floor"] if group and group.get("origin_kind") == "room" else metadata.get("floor")
        room_id = group.get("room_id") if group else metadata.get("room_id")
        if floor and room_id:
            return building(layout)["floors"][floor]["rooms"].get(room_id)
        return None
    group = next((row for row in result["network"]["groups"] if row["origin"] == key), None)
    if group is None:
        return None
    floor = group["floor"]
    if key == "dining":
        room_id = "dining"
    elif result["settings"]["context"] == "lab" and group["class_id"] == result["settings"]["lab_class"]:
        room_id = "lab_5" if floor == "5" else "lab_B2"
    else:
        room_id = layout["class_mapping"][group["class_id"]]["room_id"]
    return layout["floors"][floor]["rooms"][room_id]


def anchor(result, layout, key):
    floor = node_floor(result, key)
    if floor == "SITE":
        return None
    plan = layout["floors"][floor]
    group=next((g for g in result['network']['groups'] if g['origin']==key and 'point' in g),None)
    if group:
        xmin,xmax,ymin,ymax=plan['viewport'];x,y=group['point']
        return [xmin+x/21*(xmax-xmin),ymax-y/17*(ymax-ymin)]
    room = room_for(result, layout, key)
    if room and result['network']['nodes'].get(key,{}).get('kind') == 'recess_room_door':
        return room['door']
    if room:
        return room["center"]
    if key.startswith("hall_"):
        return plan["hub"]
    route = key.split("_",1)[0]
    return plan["stairs"].get(route, plan["hub"])


def active_segment(person, timestamp):
    for segment in person["segments"]:
        if segment["start"] <= timestamp < segment["end"]:
            return segment
    return person["active"] or {"node":person["origin"],"state":"preparing","start":0}


def interpolate(points, ratio):
    distances = [math.dist(a,b) for a,b in zip(points,points[1:])]
    target, total = sum(distances) * ratio, 0.
    for a,b,distance in zip(points,points[1:],distances):
        if target <= total+distance and distance:
            t=(target-total)/distance
            return [a[i]+t*(b[i]-a[i]) for i in range(len(a))]
        total+=distance
    return list(points[-1])


def edge_plan_points(result, layout, edge):
    source, target = edge["source"], edge["target"]
    floor = node_floor(result,source)
    if floor == "SITE" or floor != node_floor(result,target):
        return None
    points=[anchor(result,layout,source)]
    if edge["kind"] == "door":
        points.append(room_for(result,layout,source)["door"])
    elif edge["id"].startswith("corridor_"):
        route = edge["id"].split("_")[1]
        points.extend(layout["floors"][floor]["approaches"].get(route,[]))
    points.append(anchor(result,layout,target))
    return points


def locate_on_plan(result, layout, person, timestamp):
    segment = active_segment(person,timestamp)
    if segment["state"] != "moving":
        key=segment.get("node",person["origin"])
        if key==person['origin'] and 'initial_point' in person and person.get('origin_kind')!='yard':
            xmin,xmax,ymin,ymax=layout['floors'][person['floor']]['viewport'];x,y=person['initial_point']
            return person['floor'],[xmin+x/21*(xmax-xmin),ymax-y/17*(ymax-ymin)],segment['state']
        return node_floor(result,key),anchor(result,layout,key),segment["state"]
    edge=result["network"]["edges"][segment["edge"]]
    ratio=min(1.,max(0.,(timestamp-segment["start"])/(segment["end"]-segment["start"])))
    points=edge_plan_points(result,layout,edge)
    if points:
        return node_floor(result,edge["source"]),interpolate(points,ratio),"moving"
    floor=node_floor(result,edge["source"] if ratio<.5 else edge["target"])
    key=edge["source"] if ratio<.5 else edge["target"]
    return floor,anchor(result,layout,key),"moving"


# =========================================================
# REAL PLAN IMAGE WITH VISUAL MODEL ANCHORS, NOT MEASURED ROUTES
# =========================================================
def plan_figure(result,layout,floor,timestamp):
    plan=layout["floors"][floor]
    file=source_plan(plan["image_file"],plan["image_sha256"])
    image="data:image/jpeg;base64,"+base64.b64encode(file.read_bytes()).decode()
    fig=go.Figure()
    for edge in result["network"]["edges"].values():
        if node_floor(result,edge["source"])==floor:
            points=edge_plan_points(result,layout,edge)
            if points:
                fig.add_trace(go.Scatter(x=[p[0] for p in points],y=[p[1] for p in points],mode="lines",
                    line={"color":"#138b80","width":2,"dash":"dot"},name=edge["label"],hovertemplate=edge["label"]+"<extra>Görsel bağlantı; ölçülmedi</extra>",showlegend=False))
    def trace_at(time):
        xs,ys,colors,labels,identifiers=[],[],[],[],[]
        for index,person in enumerate(result["persons"]):
            current,point,state=locate_on_plan(result,layout,person,time)
            if current==floor and point is not None:
                offset=0 if result['settings']['context']=='recess' else 1
                xs.append(point[0]+(index%9-4)*2*offset);ys.append(point[1]+(index//9%7-3)*2*offset)
                colors.append(COLORS.get(state,"#dc5965"));labels.append(person["id"]+" · "+STATE_LABELS.get(state,state));identifiers.append(person['id'])
        return go.Scatter(x=xs,y=ys,ids=identifiers,mode="markers",marker={"size":7,"color":colors},text=labels,hovertemplate="%{text}<extra></extra>",showlegend=False)
    student_index=len(fig.data);initial=trace_at(timestamp);fig.add_trace(initial)
    for key,room in plan["rooms"].items():
        fig.add_annotation(x=room["center"][0],y=room["center"][1]-18,text=room["label"],showarrow=False,
                           bgcolor="rgba(255,255,255,.85)",font={"size":10,"color":"#194c65"})
    w,h=layout["image_size"];xmin,xmax,ymin,ymax=plan["viewport"]
    fig.update_layout(images=[dict(source=image,xref="x",yref="y",x=0,y=0,sizex=w,sizey=h,xanchor="left",yanchor="top",sizing="stretch",layer="below")],
        xaxis={"range":[xmin,xmax],"visible":False,"fixedrange":False},
        yaxis={"range":[ymax,ymin],"visible":False,"scaleanchor":"x","scaleratio":1},
        height=620,margin={"l":5,"r":5,"t":40,"b":125,"autoexpand":False},paper_bgcolor="white",
        title={"text":f"{floor} · plan üzerinde model hareketi","font":{"size":15}})
    end=max(1.,result['metrics']['elapsed_seconds_from_onset'])
    times=sorted(set([timestamp]+[end*i/50 for i in range(51)]))
    fig.frames=[go.Frame(name=str(i),data=[trace_at(time)],traces=[student_index]) for i,time in enumerate(times)]
    fig.update_layout(updatemenus=[{'type':'buttons','direction':'left','x':0,'y':-.20,'xanchor':'left','yanchor':'top',
        'buttons':[{'label':'▶ Planı oynat','method':'animate','args':[None,{'frame':{'duration':160,'redraw':False},'transition':{'duration':0},'fromcurrent':True}]},
                   {'label':'Ⅱ Duraklat','method':'animate','args':[[None],{'mode':'immediate','frame':{'duration':0,'redraw':False}}]}]}],
        sliders=[{'x':0,'len':1.,'y':-.03,'active':times.index(timestamp),'currentvalue':{'prefix':'An: ','suffix':' sn'},
            'steps':[{'label':str(round(time)),'method':'animate','args':[[str(i)],{'mode':'immediate','frame':{'duration':0,'redraw':False}}]} for i,time in enumerate(times)]}])
    return fig,len(initial.x)


# =========================================================
# SAME TRAJECTORIES PROJECTED TO AN ASSUMED 3D BUILDING
# =========================================================
def world_node(result,layout,key):
    floor=node_floor(result,key)
    group=next((g for g in result['network']['groups'] if g['origin']==key and 'point' in g),None)
    if group:return [*group['point'],LEVELS[group['floor']]*layout['world']['floor_height_m_assumed']]
    if key=="assembly": return list(layout["field"]["position_assumed"])
    if key=="field_gate": return [26.,5.,0.]
    if floor=="SITE": return list({'yard_left':[-1.,12.,0.],'yard_right':[23.,11.,0.],'yard_fire':[12.2,18.,0.]}.get(key,[24.,7.,0.]))
    plan=building(layout)['floors'][floor]
    room=geometry_room(result,layout,key)
    if room and result['network']['nodes'].get(key,{}).get('kind')=='recess_room_door':point=room['door']
    elif room:point=center(room['polygon'])
    elif key.startswith('hall_'):point=plan['hall']
    else:point=plan['stairs'][key.split('_',1)[0]]['center']
    return [*point,LEVELS[floor]*layout['world']['floor_height_m_assumed']]


def world_point(layout,floor,point):
    x,y=point;xmin,xmax,ymin,ymax=layout["floors"][floor]["viewport"]
    world=layout["world"]
    return [(x-xmin)/(xmax-xmin)*world["width_m_assumed"],(ymax-y)/(ymax-ymin)*world["depth_m_assumed"],LEVELS[floor]*world["floor_height_m_assumed"]]


def world_position(result,layout,person,timestamp):
    segment=active_segment(person,timestamp)
    if segment["state"]!="moving":
        node=segment.get("node",person["origin"])
        if node==person['origin']:
            point=origin_seat(result,layout,person)
            return [*point,LEVELS[person['floor']]*layout['world']['floor_height_m_assumed']],segment['state']
        return world_node(result,layout,node),segment["state"]
    edge=result["network"]["edges"][segment["edge"]]
    ratio=min(1.,max(0.,(timestamp-segment["start"])/(segment["end"]-segment["start"])))
    points=world_edge_points(result,layout,edge,person)
    return interpolate(points,ratio),"moving"


def world_edge_points(result,layout,edge,person=None):
    """Architectural visual path; retains the simulation's original event times."""
    a,b=world_node(result,layout,edge['source']),world_node(result,layout,edge['target'])
    floor=node_floor(result,edge['source'])
    if edge['id'].startswith('recess_link_'):
        start=[*origin_seat(result,layout,person),a[2]] if person else a
        if floor=='SITE':return [start,[24.,start[1],0.],[24.,5.,0.],b]
        return [start,b]
    if edge['id']=='outside_left':return [a,[-1.,-1.,0.],[24.,-1.,0.],b]
    if edge['id']=='outside_fire':return [a,[23.,18.,0.],[24.,10.,0.],b]
    if floor!='SITE' and floor==node_floor(result,edge['target']):
        plan=building(layout)['floors'][floor];z=a[2]
        if edge['kind']=='door':
            room=geometry_room(result,layout,edge['source'])
            is_shared_recess_door=result['network']['nodes'].get(edge['source'],{}).get('kind')=='recess_room_door'
            start=room['door'] if is_shared_recess_door else origin_seat(result,layout,person) if person else center(room['polygon'])
            return [[*start,z],[*room['door'],z],*[[*p,z] for p in room['approach']],b]
        if edge['id'].startswith('corridor_'):
            route=edge['id'].split('_')[1]
            return [a,*[[*p,z] for p in plan['approaches'][route]],b]
    if floor!='SITE' and node_floor(result,edge['target'])!='SITE' and a[2]!=b[2]:
        middle=(a[2]+b[2])/2
        return [a,[a[0]+.75,a[1]-.8,middle],[b[0]-.75,b[1]-.8,middle],b]
    return [a,b]


def view3d(result,layout,timestamp,max_floor="6"):
    fig=go.Figure();world=layout["world"];w,d=world["width_m_assumed"],world["depth_m_assumed"]
    for floor,height in LEVELS.items():
        if height>LEVELS[max_floor]: continue
        z=height*world["floor_height_m_assumed"]
        fig.add_trace(go.Scatter3d(x=[0,w,w,0,0],y=[0,0,d,d,0],z=[z]*5,mode="lines",line={"color":"#bac8d8","width":2},name=floor,showlegend=False))
    xs,ys,zs=[],[],[]
    for edge in result["network"]["edges"].values():
        a,b=world_node(result,layout,edge["source"]),world_node(result,layout,edge["target"])
        if max(a[2],b[2])>LEVELS[max_floor]*world["floor_height_m_assumed"]:continue
        xs.extend([a[0],b[0],None]);ys.extend([a[1],b[1],None]);zs.extend([a[2],b[2],None])
    fig.add_trace(go.Scatter3d(x=xs,y=ys,z=zs,mode="lines",line={"color":"#78b6b0","width":3},hoverinfo="skip",showlegend=False))
    positions=[world_position(result,layout,p,timestamp) for p in result["persons"]]
    filtered=[(p,state,person) for (p,state),person in zip(positions,result["persons"]) if p[2]<=LEVELS[max_floor]*world["floor_height_m_assumed"]]
    fig.add_trace(go.Scatter3d(x=[p[0] for p,_,_ in filtered],y=[p[1] for p,_,_ in filtered],z=[p[2]+.3 for p,_,_ in filtered],
        mode="markers",marker={"size":4,"color":[COLORS.get(state,"#dc5965") for _,state,_ in filtered]},
        text=[person["id"] for _,_,person in filtered],hovertemplate="%{text}<extra></extra>",showlegend=False))
    fig.update_layout(height=570,margin={"l":0,"r":0,"t":35,"b":0},title="Aynı koşunun 3B görünümü · boyutlar örnek",
        scene={"aspectmode":"data","xaxis_title":"Örnek x (m)","yaxis_title":"Örnek y (m)","zaxis_title":"Örnek yükseklik (m)","camera":{"eye":{"x":1.6,"y":-1.7,"z":1.2}}})
    return fig
