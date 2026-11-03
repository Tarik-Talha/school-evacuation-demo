"""Room-shaped school cutaway and offline 3D playback with page-friendly controls."""
import html,json,math
import plotly.graph_objects as go
from building_geometry import building,bounds,center,geometry_room,origin_seat,seats
from engine import LEVELS
from spatial import active_segment,world_position,world_edge_points
from visuals import COLORS,STATE_LABELS

CLASS_COLORS=['#2563eb','#8b5cf6','#db2777','#ea580c','#0891b2','#4f46e5','#059669','#be123c','#7c3aed','#0284c7']

def triangulate(poly):
    """Ear clipping preserves the concave outline instead of filling its recesses."""
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))
    indices=list(range(len(poly))) if area>0 else list(reversed(range(len(poly))))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    triangles=[]
    while len(indices)>3:
        for n,index in enumerate(indices):
            a,b,c=indices[n-1],index,indices[(n+1)%len(indices)]
            if cross(poly[a],poly[b],poly[c])<=1e-9:continue
            if any(all(cross(poly[u],poly[v],poly[p])>=-1e-9 for u,v in ((a,b),(b,c),(c,a)))
                   for p in indices if p not in (a,b,c)):continue
            triangles.append((a,b,c));indices.pop(n);break
        else:raise ValueError('Kat çevresi üçgenlenemedi; geometriyi kontrol edin.')
    return triangles+[tuple(indices)]

class Mesh:
    def __init__(self):self.vertices=[];self.faces=[];self.colors=[]
    def surface(self,poly,z,color):
        offset=len(self.vertices);self.vertices.extend([[x,y,z] for x,y in poly])
        for triangle in triangulate(poly):self.faces.append(tuple(offset+i for i in triangle));self.colors.append(color)
    def wall(self,a,b,z,height,color):
        offset=len(self.vertices);self.vertices.extend([[*a,z],[*b,z],[*b,z+height],[*a,z+height]])
        self.faces.extend([(offset,offset+1,offset+2),(offset,offset+2,offset+3)]);self.colors.extend([color,color])
    def box(self,x,y,z,w,d,h,color):
        poly=[[x-w/2,y-d/2],[x+w/2,y-d/2],[x+w/2,y+d/2],[x-w/2,y+d/2]]
        self.surface(poly,z+h,color)
        for a,b in zip(poly,poly[1:]+poly[:1]):self.wall(a,b,z,h,color)
    def trace(self,name,opacity=1):
        return go.Mesh3d(x=[p[0] for p in self.vertices],y=[p[1] for p in self.vertices],z=[p[2] for p in self.vertices],
            i=[f[0] for f in self.faces],j=[f[1] for f in self.faces],k=[f[2] for f in self.faces],facecolor=self.colors,
            flatshading=True,opacity=opacity,hoverinfo='skip',name=name,showlegend=False,
            lighting={'ambient':.8,'diffuse':.55,'specular':.1},lightposition={'x':0,'y':-25,'z':50})

def room_walls(mesh,polygon,door,z,height,color):
    doors=[] if door is None else [door] if isinstance(door[0],(int,float)) else door
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        gaps=[]
        for opening in doors:
            t=((opening[0]-a[0])*dx+(opening[1]-a[1])*dy)/(length*length)
            distance=math.dist([a[0]+t*dx,a[1]+t*dy],opening)
            if 0<=t<=1 and distance<.25:gaps.append((max(0,t-.55/length),min(1,t+.55/length)))
        cursor=0
        for lo,hi in sorted(gaps)+[(1,1)]:
            if lo>cursor:mesh.wall([a[0]+cursor*dx,a[1]+cursor*dy],[a[0]+lo*dx,a[1]+lo*dy],z,height,color)
            cursor=max(cursor,hi)

def level_z(layout,floor,separated=False):
    return LEVELS[floor]*layout['world']['floor_height_m_assumed']+(LEVELS[floor]+2)*1.25 if separated else LEVELS[floor]*layout['world']['floor_height_m_assumed']

def student_frame(result,layout,time,floors,separated):
    colors={key:CLASS_COLORS[i%len(CLASS_COLORS)] for i,key in enumerate(dict.fromkeys(p['class_id'] for p in result['persons']))}
    heads={'x':[],'y':[],'z':[],'color':[],'text':[],'ids':[]};body={'x':[],'y':[],'z':[]}
    counts={'rooms':0,'moving':0,'waiting':0,'field':0,'other':0}
    for person in result['persons']:
        position,state=world_position(result,layout,person,time);segment=active_segment(person,time)
        if state=='assembled':category='field'
        elif state=='moving':category='moving'
        elif state=='queued' and segment.get('node')!=person['origin']:category='waiting'
        elif state in ('protecting','preparing','queued'):category='rooms'
        else:category='other'
        counts[category]+=1
        # Show people on their current level; cutting a floor never changes the model population.
        floor_height=position[2]/layout['world']['floor_height_m_assumed']
        if len(floors)==1 and abs(floor_height-LEVELS[floors[0]])>.48:continue
        if separated:position=[position[0],position[1],position[2]+(floor_height+2)*1.25]
        x,y,z=position
        heads['x'].append(x);heads['y'].append(y);heads['z'].append(z+.86)
        heads['color'].append(colors[person['class_id']] if category=='rooms' else COLORS.get(state,'#dc5965'))
        group_label=(' · arkadaş grubu '+person['group_id']) if 'group_id' in person else ''
        heads['text'].append(person['class_id']+' · '+person['id']+group_label+' · '+STATE_LABELS.get(state,state));heads['ids'].append(person['id'])
        body['x'].extend([x,x,None]);body['y'].extend([y,y,None]);body['z'].extend([z+.18,z+.64,None])
    shaking=result['settings']['shaking_seconds']
    location='öğrenciler yemekhanede' if result['settings']['context']=='lunch' else 'öğrenciler başlangıç odalarında'
    if result['settings']['context']=='recess':location='arkadaş grupları teneffüs konumlarında'
    phase='Sarsıntı · '+location if time<shaking else 'Hazırlık / tahliye' if counts['field']<111 else 'Koşu tamamlandı'
    return {'time':round(time,2),'heads':heads,'body':body,'counts':counts,'visible':len(heads['ids']),'phase':phase}

def scene_figure(result,layout,timestamp=0,floor='3',mode='floor',routes=False):
    geometry=building(layout);floors=[floor] if mode=='floor' else list(geometry['floors']);separated=mode=='separated'
    slabs=Mesh();walls=Mesh();furniture=Mesh();glass=Mesh();lines_x=[];lines_y=[];lines_z=[];texts=[];tx=[];ty=[];tz=[]
    for level in floors:
        plan=geometry['floors'][level];z=level_z(layout,level,separated);height=.85 if len(floors)>1 else 1.25
        slabs.surface(plan['outline'],z-.06,'#e5e9ee')
        room_walls(walls,plan['outline'],[[0,12],[21,11],[12.2,17],[16,2]] if level=='G' else None,z,height,'#cbd5e1')
        for service in plan['service_rooms']:
            slabs.surface(service['polygon'],z+.005,'#e2e8f0');room_walls(walls,service['polygon'],None,z,height*.65,'#e2e8f0')
        for room_id,room in plan['rooms'].items():
            groups=[g for g in result['network']['groups'] if g['floor']==level and geometry_room(result,layout,g['origin']) is room]
            # Room dict identity is stable within this loaded geometry.
            if not groups:
                groups=[g for g in result['network']['groups'] if g['floor']==level and geometry_room(result,layout,g['origin'])==room]
            label=' / '.join(dict.fromkeys(g['class_id'] for g in groups)) if groups else room['label']
            if groups and result['settings']['context']=='recess':
                label=f"Teneffüs · {label} ({sum(g['students'] for g in groups)} öğrenci)"
            if room['kind']=='dining':label='Yemekhane · 111 öğrenci' if result['settings']['context']=='lunch' else 'Yemekhane'
            slabs.surface(room['polygon'],z+.01,'#dceaf8' if groups else '#f1f5f9')
            room_walls(walls,room['polygon'],room['door'],z,height,'#b9cadc')
            x0,y0,x1,y1=bounds(room['polygon'])
            if len(floors)==1:
                tx.append((x0+x1)/2);ty.append(y1+.27);tz.append(z+height+.1);texts.append(label)
            people=[p for p in result['persons'] if any(p['origin']==g['origin'] for g in groups)]
            if result['settings']['context']!='recess' and (len(floors)==1 or level in ('1','2','3','4')):
                for person in people:
                    x,y=origin_seat(result,layout,person)
                    furniture.box(x+.27,y,z,.45,.36,.43,'#aec4d4')
            # A simple board identifies teaching rooms without fabricating a facade.
            if room['kind'] in ('classroom','lab'):
                furniture.wall([x0+.4,y1-.08],[min(x1-.3,x0+2.4),y1-.08],z+.5,.45,'#447d76')
        for name,stair in plan['stairs'].items():
            x0,y0,x1,y1=stair['bounds'];slabs.surface([[x0,y0],[x1,y0],[x1,y1],[x0,y1]],z+.02,'#d7e7e4')
            for step in range(10):
                y=y0+(y1-y0)*step/10
                lines_x.extend([x0+.15,x1-.15,None]);lines_y.extend([y,y,None]);lines_z.extend([z+.06,z+.06,None])
            if len(floors)==1:
                tx.append((x0+x1)/2);ty.append(y1+.32);tz.append(z+.15);texts.append({'left':'İç merdiven','right':'İç merdiven','fire':'Yangın merdiveni'}[name])
            if len(floors)>1:
                previous=[f for f in floors if LEVELS[f]<LEVELS[level]]
                if previous:
                    lower=max(previous,key=lambda f:LEVELS[f]);low_z=level_z(layout,lower,separated)
                    cx,cy=stair['center'];span=z-low_z
                    for step in range(12):
                        t=step/11;x=cx+(.7 if t<.5 else -.7);y=cy-1.05+2.1*(t*2 if t<.5 else (1-t)*2)
                        furniture.box(x,y,low_z+t*span,.7,.20,.08,'#94b6b2')
        if len(floors)>1:
            tx.append(-1);ty.append(0);tz.append(z+.25);texts.append({'G':'Zemin','M':'Asma','B1':'B1 · Yemekhane','B2':'B2'}.get(level,level+'. kat'))
    if len(floors)>1 or floor=='G':
        field=geometry['site']['proposed_field'];x0,y0,x1,y1=field
        slabs.surface([[x0,y0],[x1,y0],[x1,y1],[x0,y1]],-.1,'#cce8d6')
        tx.append((x0+x1)/2);ty.append(y1+1);tz.append(.1);texts.append('Önerilen saha')
        slabs.surface([[-2,-3],[35,-3],[35,20],[-2,20]],-.2,'#f0f4f3')
    fig=go.Figure([slabs.trace('Katlar ve odalar',.94 if len(floors)==1 else .58),walls.trace('Kesit duvarları',.85),furniture.trace('Sıralar ve merdivenler')])
    fig.add_trace(go.Scatter3d(x=lines_x,y=lines_y,z=lines_z,mode='lines',line={'color':'#548a86','width':2},hoverinfo='skip',showlegend=False))
    fig.add_trace(go.Scatter3d(x=tx,y=ty,z=tz,mode='text',text=texts,textfont={'color':'#38516b','size':11},hoverinfo='skip',showlegend=False))
    if routes:
        xs,ys,zs=[],[],[]
        for edge in result['network']['edges'].values():
            points=world_edge_points(result,layout,edge)
            if len(floors)==1 and any(abs(p[2]/3-LEVELS[floor])>.48 for p in points):continue
            for x,y,z in points:
                xs.append(x);ys.append(y);zs.append(z+(z/3+2)*1.25+.08 if separated else z+.08)
            xs.append(None);ys.append(None);zs.append(None)
        fig.add_trace(go.Scatter3d(x=xs,y=ys,z=zs,mode='lines',line={'color':'#53a398','width':3},hoverinfo='skip',showlegend=False))
    initial=student_frame(result,layout,timestamp,floors,separated);body_index=len(fig.data)
    fig.add_trace(go.Scatter3d(**initial['body'],mode='lines',line={'color':'#4474a5','width':4},hoverinfo='skip',showlegend=False))
    head_index=len(fig.data);head=initial['heads']
    fig.add_trace(go.Scatter3d(x=head['x'],y=head['y'],z=head['z'],ids=head['ids'],mode='markers',
        marker={'size':4 if len(floors)==1 else 3.5,'color':head['color'],'line':{'width':0}},
        text=head['text'],hovertemplate='%{text}<extra></extra>',showlegend=False))
    floor_view=len(floors)==1;zmin=level_z(layout,floors[0],separated)-.5 if floor_view else -6.5
    zmax=zmin+3 if floor_view else level_z(layout,'6',separated)+2
    fig.update_layout(height=480,margin={'l':0,'r':0,'t':0,'b':0},paper_bgcolor='#f7f9fc',showlegend=False,
        uirevision='school-room-camera',scene={'aspectmode':'manual','aspectratio':{'x':1.25 if floor_view else .95,'y':1,'z':.24 if floor_view else 1.35},
        'xaxis':{'visible':False,'range':[-1,22 if floor_view else 35]},'yaxis':{'visible':False,'range':[-1,18.5]},
        'zaxis':{'visible':False,'range':[zmin,zmax]},'bgcolor':'#f7f9fc','dragmode':'orbit',
        'camera':{'eye':{'x':.85 if floor_view else 1.3,'y':-1.05 if floor_view else -1.6,'z':1.45 if floor_view else 1.2},'up':{'x':0,'y':0,'z':1},'projection':{'type':'orthographic'}}})
    return fig,body_index,head_index,floors,separated

def scene_html(result,layout,floor='3',mode='floor',routes=False):
    fig,body_index,head_index,floors,separated=scene_figure(result,layout,0,floor,mode,routes)
    end=max(1.,result['metrics']['elapsed_seconds_from_onset'])
    times=sorted(set([0.,end,result['settings']['shaking_seconds']]+[end*i/60 for i in range(61)]))
    frames=[student_frame(result,layout,t,floors,separated) for t in times]
    camera=fig.layout.scene.camera.to_plotly_json()
    script=r"""
const plot=document.getElementById('{plot_id}'),frames=FRAMES,home=CAMERA;
const timeline=document.getElementById('time'),clock=document.getElementById('clock');
let index=0,timer=null,busy=false,pending=null,rotation=false,zoom=1;
function stop(){clearTimeout(timer);timer=null;document.getElementById('play').setAttribute('aria-pressed','false');}
async function show(value){if(busy){pending=value;return;}busy=true;index=value;const f=frames[value];
 timeline.value=value;clock.textContent=f.time.toFixed(1)+' sn';
 document.getElementById('phase').textContent=f.phase;
 document.getElementById('counts').textContent=ORIGIN_LABEL+f.counts.rooms+' · İlerleyen '+f.counts.moving+' · Bekleyen '+f.counts.waiting+' · Sahada '+f.counts.field+(f.counts.other?' · Diğer '+f.counts.other:'');
 document.getElementById('visible').textContent='Bu görünümde '+f.visible+' / 111 öğrenci';
 try{await Plotly.restyle(plot,{x:[f.body.x,f.heads.x],y:[f.body.y,f.heads.y],z:[f.body.z,f.heads.z],
    text:[null,f.heads.text],ids:[null,f.heads.ids],'marker.color':[null,f.heads.color]},[BODY,HEAD]);}finally{busy=false;
    if(pending!==null){const next=pending;pending=null;await show(next);}}
}
async function tick(){if(timer===null)return;if(index>=frames.length-1){stop();return;}
 await show(index+1);if(timer!==null)timer=setTimeout(tick,180/Number(document.getElementById('speed').value));}
document.getElementById('play').onclick=async()=>{stop();if(index>=frames.length-1)await show(0);
 timer=0;document.getElementById('play').setAttribute('aria-pressed','true');tick();};
document.getElementById('pause').onclick=stop;
document.getElementById('reset').onclick=()=>{stop();show(0);};
timeline.oninput=()=>{stop();show(Number(timeline.value));};
function cameraPreset(kind){let c=JSON.parse(JSON.stringify(home));
 if(kind==='top'){c.eye={x:0,y:0,z:1.65};c.up={x:0,y:1,z:0};}if(kind==='front')c.eye={x:0,y:-1.7,z:.75};
 zoom=1;Plotly.relayout(plot,{'scene.camera':c});}
document.getElementById('top').onclick=()=>cameraPreset('top');
document.getElementById('home').onclick=()=>cameraPreset('home');
document.getElementById('front').onclick=()=>cameraPreset('front');
function zoomBy(factor){const next=Math.max(.65,Math.min(1.55,zoom*factor)),ratio=next/zoom;
 const current=plot.layout.scene.camera||home,eye=current.eye||home.eye;
 Plotly.relayout(plot,{'scene.camera.eye':{x:eye.x*ratio,y:eye.y*ratio,z:eye.z*ratio}});zoom=next;}
document.getElementById('closer').onclick=()=>zoomBy(.88);
document.getElementById('farther').onclick=()=>zoomBy(1.12);
document.getElementById('rotate').onclick=()=>{rotation=!rotation;plot.style.pointerEvents=rotation?'auto':'none';
 document.getElementById('rotate').textContent=rotation?'Döndürme açık · kapat':'Fareyle döndür';
 document.getElementById('rotate').setAttribute('aria-pressed',String(rotation));};
plot.style.pointerEvents='none';
// The plot must never trap the page's wheel, even while rotation is enabled.
document.addEventListener('wheel',event=>{if(event.ctrlKey)return;
 const scroller=window.parent.document.querySelector('[data-testid="stMain"]');
 if(scroller){event.preventDefault();event.stopImmediatePropagation();
 scroller.scrollBy({top:event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?scroller.clientHeight:1),left:event.deltaX});}
},{passive:false,capture:true});
let width=0,height=0;const fit=()=>{const next=document.documentElement.clientWidth;
 const available=Math.max(260,window.innerHeight-document.querySelector('.player').offsetHeight-2);
 if(next>0&&(next!==width||height!==available)){width=next;height=available;Plotly.relayout(plot,{width:next,height:available});}};
new ResizeObserver(fit).observe(document.documentElement);new ResizeObserver(fit).observe(document.querySelector('.player'));
await show(0);document.getElementById('play').disabled=false;
"""
    origin_label='Başlangıç konumunda ' if result['settings']['context']=='recess' else 'Sınıfta '
    script=script.replace('ORIGIN_LABEL',json.dumps(origin_label,ensure_ascii=True)).replace('FRAMES',json.dumps(frames,ensure_ascii=True)).replace('CAMERA',json.dumps(camera)).replace('BODY',str(body_index)).replace('HEAD',str(head_index))
    # Plotly wraps post_script in a regular function; use an async IIFE for the first update.
    script='(async()=>{'+script+'})().catch(error=>{document.getElementById("phase").textContent="3B oynatıcı yüklenemedi";console.error(error);});'
    chart=fig.to_html(include_plotlyjs=True,full_html=False,auto_play=False,post_script=script,
        config={'responsive':True,'displayModeBar':False,'scrollZoom':False,'doubleClick':False},default_width='100%')
    controls=f'''<div class="player"><div class="row"><button id="play" disabled aria-pressed="false">▶ Oynat</button><button id="pause">Ⅱ Duraklat</button><button id="reset">↺ Başa al</button>
<select id="speed" aria-label="Oynatma hızı"><option value=".5">0,5×</option><option value="1" selected>1×</option><option value="2">2×</option></select><output id="clock">0.0 sn</output></div>
<input id="time" type="range" min="0" max="{len(frames)-1}" value="0" aria-label="3B animasyon zamanı">
<div id="phase">Sarsıntı · öğrenciler başlangıç yerlerinde</div><div id="counts">Sınıfta 111 · Sahada 0</div>
<div class="row views"><button id="home">Çapraz</button><button id="top">Üstten</button><button id="front">Önden</button><button id="closer" aria-label="Yakınlaştır">+</button><button id="farther" aria-label="Uzaklaştır">−</button><button id="rotate" aria-pressed="false">Fareyle döndür</button></div>
<div id="visible">111 model öğrencisi</div></div>'''
    style='''<style>html,body{margin:0;overflow:hidden;background:#f7f9fc;font:13px system-ui,sans-serif;color:#254660}
.player{padding:10px 10px 4px;box-sizing:border-box}.row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
button,select{padding:7px 10px;border:1px solid #cbd9e6;border-radius:7px;background:white;color:#254660;cursor:pointer;font:inherit}
button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #0d9488;outline-offset:2px}
button#play{background:#0d8f83;color:white;border-color:#0d8f83}button[aria-pressed=true]{box-shadow:inset 0 0 0 2px #5ac6b3}
button:disabled{opacity:.45}input{width:100%;accent-color:#0d9488;margin:12px 0}output{font-variant-numeric:tabular-nums;font-weight:650}
#phase{font-weight:650;margin:4px 0}#counts,#visible{font-size:12px;color:#526b80;margin:4px 0}.views{margin-top:9px}
</style>'''
    return style+controls+chart

def show_scene(result,layout,floor='3',mode='floor',routes=False):
    import streamlit as st
    st.iframe(scene_html(result,layout,floor,mode,routes),height=640,alt='Okulun 3B animasyonu')
