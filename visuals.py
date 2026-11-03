"""Schematic playback and model-only comparison charts."""
import plotly.graph_objects as go

from engine import LEVELS, ROUTE_LABELS, position_at

COLORS = {"protecting": "#8b93a6", "preparing": "#a5adbd", "queued": "#e8a02a",
          "moving": "#3194e8", "assembled": "#1aaf91", "unreachable": "#dc5965",
          "outside_unassembled": "#b865cd", "timeout": "#dc5965"}
STATE_LABELS = {"protecting": "Korunma", "preparing": "Harekete hazırlanma", "queued": "Bekleme",
                "moving": "İlerleme", "assembled": "Sahaya vardı", "unreachable": "Rota yok",
                "outside_unassembled": "Dışarıda, sahaya ulaşamadı", "timeout": "Süre sınırında"}


def animated_chart(figure, height):
    """Embed Plotly's offline player so animation frames are actually registered.

    Streamlit's native chart renderer displays the figure but does not register
    its frames. The self-contained player loads no external scripts or data.
    """
    import json
    import streamlit as st
    labels=[step.label for step in figure.layout.sliders[0].steps]
    active=figure.layout.sliders[0].active or 0
    player=go.Figure(figure)
    player.update_layout(height=height-84,margin={"b":10})
    player.layout.updatemenus=()
    player.layout.sliders=()
    script="""
const plot=document.getElementById('{plot_id}');
const labels=LABELS, timeline=document.getElementById('timeline'), clock=document.getElementById('clock');
function show(index){timeline.value=index;clock.textContent='An: '+labels[index]+' sn';}
plot.on('plotly_animatingframe',event=>show(Number(event.name)));
document.getElementById('play').onclick=()=>{
  let start=Number(timeline.value);if(start>=labels.length-1)start=-1;
  Plotly.animate(plot,labels.map((_,i)=>String(i)).slice(start+1),
    {mode:'immediate',frame:{duration:160,redraw:false},transition:{duration:0}});
};
document.getElementById('pause').onclick=()=>Plotly.animate(plot,[null],
  {mode:'immediate',frame:{duration:0,redraw:false},transition:{duration:0}});
timeline.oninput=()=>{show(Number(timeline.value));Plotly.animate(plot,[String(timeline.value)],
  {mode:'immediate',frame:{duration:0,redraw:false},transition:{duration:0}});};
let width=0;new ResizeObserver(()=>{const next=document.documentElement.clientWidth;
  if(next>0&&next!==width){width=next;Plotly.relayout(plot,{width:next});}
}).observe(document.documentElement);
""".replace('LABELS',json.dumps(labels))
    html=player.to_html(include_plotlyjs=True,full_html=False,auto_play=False,post_script=script,
        config={"responsive":True,"displayModeBar":False},default_width="100%")
    controls=f'''<div class="controls"><button id="play">▶ Oynat</button>
<button id="pause">Ⅱ Duraklat</button><output id="clock">An: {labels[active]} sn</output>
<input id="timeline" aria-label="Animasyon zamanı" type="range" min="0" max="{len(labels)-1}" value="{active}"></div>'''
    style='''<style>html,body{margin:0;background:white;overflow:hidden;font:13px Arial;color:#194c65}
.controls{padding:6px 4px;box-sizing:border-box;height:84px}button{padding:8px 10px;border:1px solid #b9d3d0;
border-radius:6px;background:#eef8f5;color:#194c65;cursor:pointer}output{margin-left:8px}input{display:block;width:98%;margin-top:10px;accent-color:#138b80}</style>'''
    st.iframe(style+controls+html,
        height=height,alt=figure.layout.title.text.replace('<br>',' · '))


# =========================================================
# SCHEMATIC STUDENT PLAYBACK, NOT A MEASURED FLOOR PLAN
# =========================================================
def student_trace(result, timestamp):
    xs, ys, colors, labels, sizes = [], [], [], [], []
    for index, person in enumerate(result["persons"]):
        x, y, state = position_at(result, person, timestamp)
        # Small deterministic display offsets prevent dots hiding one another.
        final = state == "assembled"
        xs.append(x + ((index % 12) - 5.5) * (.7 if final else .22))
        ys.append(y + ((index // 12) - 4.5) * (1.1 if final else .20))
        sizes.append(4 if final else 7)
        colors.append(COLORS.get(state, "#dc5965"))
        labels.append(f"{person['id']} · {STATE_LABELS.get(state, state)}")
    return go.Scatter(x=xs, y=ys, mode="markers", marker={"size": sizes, "color": colors, "opacity": .9},
                      text=labels, hovertemplate="%{text}<extra></extra>", name="111 öğrenci", showlegend=False)


def playback(result):
    network = result["network"]
    xs, ys = [], []
    for edge in network["edges"].values():
        source, target = network["nodes"][edge["source"]], network["nodes"][edge["target"]]
        xs.extend([source["x"], target["x"], None])
        ys.extend([source["y"], target["y"], None])
    base = go.Scatter(x=xs, y=ys, mode="lines", line={"color": "#c4d0df", "width": 2},
                      hoverinfo="skip", showlegend=False)
    end = max(1., result["metrics"]["elapsed_seconds_from_onset"])
    timestamps = sorted(set([0., result["settings"]["shaking_seconds"], end] + [end * i / 70 for i in range(71)]))
    timestamps = [value for value in timestamps if value <= end]
    frames = [go.Frame(name=str(i), data=[student_trace(result, value)], traces=[1])
              for i, value in enumerate(timestamps)]
    fig = go.Figure(data=[base, student_trace(result, 0)], frames=frames)
    annotations = [dict(x=20, y=53, text="SOL İÇ", showarrow=False),
                   dict(x=30, y=53, text="SAĞ İÇ", showarrow=False),
                   dict(x=40, y=53, text="YANGIN", showarrow=False),
                   dict(x=61, y=-20, text="ÖNERİLEN SAHA", showarrow=False),
                   dict(x=51, y=-31, text="Ortak geçiş<br>(varsayım)", showarrow=False)]
    for key, node in network["nodes"].items():
        if key.startswith("room_") or key == "dining":
            annotations.append(dict(x=node["x"], y=node["y"] + 1.7, text=node["label"],
                                    showarrow=False, font={"size": 10, "color": "#63758b"}))
    fig.update_layout(height=610, margin={"l": 40, "r": 15, "t": 65, "b": 130, "autoexpand": False},
        paper_bgcolor="#ffffff", plot_bgcolor="#f7fafc", font={"color": "#23334a", "family": "Arial"},
        title={"text": "Şematik öğrenci akışı<br><sup>Ölçekli plan değildir</sup>", "font": {"size": 16}},
        xaxis={"range": [-2, 69], "visible": False, "fixedrange": True},
        shapes=[{"type": "rect", "x0": 44, "x1": 69, "y0": -33, "y1": 1,
                 "fillcolor": "#e6f6ee", "line": {"width": 0}, "layer": "below"}],
        yaxis={"range": [-34, 56], "tickvals": [height * 8 for height in LEVELS.values()],
               "ticktext": ["Zemin" if key == "G" else "Asma" if key == "M" else key + ". kat" if key.isdigit() else key for key in LEVELS],
               "gridcolor": "#e7edf4", "zeroline": False, "fixedrange": True}, annotations=annotations,
        updatemenus=[{"type": "buttons", "direction": "left", "x": 0, "y": -0.20,
            "xanchor": "left", "yanchor": "top",
            "buttons": [{"label": "▶ Oynat", "method": "animate", "args": [None, {"frame": {"duration": 140, "redraw": False}, "transition": {"duration": 0}, "fromcurrent": True}]},
                        {"label": "Ⅱ Duraklat", "method": "animate", "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]}]}],
        sliders=[{"active": 0, "x": 0, "len": 1., "y": -0.03,
                  "currentvalue": {"prefix": "An: ", "suffix": " sn", "font": {"size": 11}},
                  "steps": [{"label": str(round(value)), "method": "animate",
                             "args": [[str(i)], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}}]}
                            for i, value in enumerate(timestamps)]}])
    return fig


def cumulative(result):
    end = result["metrics"]["elapsed_seconds_from_onset"]
    times = sorted(set([0., end] + [person["outside_at"] for person in result["persons"] if person["outside_at"] is not None]
                       + [person["arrived_at"] for person in result["persons"] if person["arrived_at"] is not None]))
    fig = go.Figure()
    for key, label, color in [("outside_at", "Dışarı çıkan", "#3194e8"), ("arrived_at", "Sahaya varan", "#1aaf91")]:
        values = [sum(person[key] is not None and person[key] <= t for person in result["persons"]) for t in times]
        fig.add_trace(go.Scatter(x=times, y=values, mode="lines", line={"shape": "hv", "color": color}, name=label))
    fig.add_vrect(x0=0, x1=result["settings"]["shaking_seconds"], fillcolor="#d8dfe8", opacity=.4, line_width=0)
    fig.update_layout(height=275, margin={"l": 25, "r": 15, "t": 15, "b": 35},
                      xaxis_title="Deprem başlangıcından geçen süre (sn)", yaxis_title="Öğrenci",
                      yaxis={"range": [0, len(result["persons"]) + 5]}, legend={"orientation": "h", "y": 1.2},
                      paper_bgcolor="white", plot_bgcolor="#f7fafc")
    return fig
