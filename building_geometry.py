"""Plan-informed visual geometry and deterministic, room-contained seating."""
from functools import lru_cache
import json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parent

@lru_cache(maxsize=1)
def default_building():
    return json.loads((ROOT/'building_geometry.json').read_text(encoding='utf-8'))

def building(layout):return layout.get('building_geometry') or default_building()

def inside(point,polygon):
    x,y=point;odd=False
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:odd=not odd
    return odd

def bounds(polygon):
    return min(p[0] for p in polygon),min(p[1] for p in polygon),max(p[0] for p in polygon),max(p[1] for p in polygon)

def center(polygon):
    x0,y0,x1,y1=bounds(polygon)
    return [(x0+x1)/2,(y0+y1)/2]

def seats(polygon,count,exclusions=()):
    """Return distinct interior seats without inventing additional people."""
    if count<1:return []
    x0,y0,x1,y1=bounds(polygon);width=x1-x0;height=y1-y0
    columns=max(1,math.ceil(math.sqrt(count*width/height)))
    for density in range(1,20):
        cols=columns+density-1;rows=max(1,math.ceil(count/cols))+density-1
        candidates=[[x0+width*(i+.5)/cols,y0+height*(j+.5)/rows] for j in range(rows) for i in range(cols)]
        valid=[p for p in candidates if inside(p,polygon) and not any(inside(p,hole) for hole in exclusions)]
        if len(valid)>=count:return [valid[math.floor(i*len(valid)/count)] for i in range(count)]
    raise ValueError('Derslik içinde öğrenci yerleşimi üretilemedi.')

def geometry_room(result,layout,origin):
    if result['settings']['context']=='recess':
        group=next((g for g in result['network']['groups'] if g['origin']==origin),None)
        metadata=result['network']['nodes'].get(origin,{})
        floor=group['floor'] if group and group.get('origin_kind')=='room' else metadata.get('floor')
        room_id=group.get('room_id') if group else metadata.get('room_id')
        return building(layout)['floors'][floor]['rooms'].get(room_id) if floor and room_id else None
    group=next((g for g in result['network']['groups'] if g['origin']==origin),None)
    if group is None:return None
    floor=group['floor'];rooms=building(layout)['floors'][floor]['rooms']
    if origin=='dining':key='dining'
    elif result['settings']['context']=='lab' and group['class_id']==result['settings']['lab_class']:
        key='lab_5' if floor=='5' else 'lab_B2'
    else:key=layout['class_mapping'][group['class_id']]['room_id']
    return rooms[key]

def origin_seat(result,layout,person):
    if 'initial_point' in person:return list(person['initial_point'])
    room=geometry_room(result,layout,person['origin'])
    people=[p for p in result['persons'] if p['origin']==person['origin']]
    index=next(i for i,p in enumerate(people) if p['id']==person['id'])
    floor=building(layout)['floors'][person['floor']]
    holes=[]
    if room['kind']=='dining':
        for stair in floor['stairs'].values():
            x0,y0,x1,y1=stair['bounds'];holes.append([[x0,y0],[x1,y0],[x1,y1],[x0,y1]])
    return seats(room['polygon'],len(people),holes)[index]
