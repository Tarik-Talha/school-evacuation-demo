"""School evacuation scenario explorer, isolated from TwinOps and SchoolWatch."""
from dataclasses import asdict, replace
import hashlib
import importlib
import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# =========================================================
# RELOAD LOCAL MODEL MODULES WHEN THE EXISTING PREVIEW RERUNS
# =========================================================
# Streamlit reruns app.py in a long-lived process. Reload project modules in
# dependency order so new Settings fields and the recess adapter do not remain
# stale until a server restart.
for _module_name in ('building_geometry','recess','engine','visuals','spatial',
                     'experiments','planner','scene_export','school_scene','external_response',
                     'advanced_ui','planning_ui'):
    if _module_name in sys.modules:
        importlib.reload(sys.modules[_module_name])

from engine import ROUTES, ROUTE_LABELS, Settings, simulate
from visuals import animated_chart, cumulative, playback
from advanced_ui import plans_page, trials_page, strategies_page, drill_page, scene_page, read_measurements
from planning_ui import planning_panel
from external_response import estimate_external_arrivals, format_duration
from source_assets import source_plan

ROOT = Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / "school_profile.json").read_text(encoding="utf-8"))
MODEL_FINGERPRINT = hashlib.sha256(b''.join((ROOT / name).read_bytes() for name in ('engine.py','experiments.py','spatial.py','recess.py','building_geometry.json'))).hexdigest()
CONTEXTS = {"Ders sırasında": "lesson", "Öğle yemeği · 111 öğrenci B1'de": "lunch", "Örnek laboratuvar dersi": "lab", "Teneffüs · 2–3 kişilik arkadaş grupları": "recess"}
POLICIES = {"Dağıtılmış model akışı": "balanced", "En kısa model rotası": "shortest"}

st.set_page_config(page_title="School Evacuation · Senaryo Atölyesi", page_icon="🏫", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{padding-top:1.8rem;max-width:1200px}
[data-testid=stMetric]{background:#f1f6fa;border:1px solid #e0e8f0;border-radius:12px;padding:15px}
h1{letter-spacing:-.7px;font-size:clamp(1.5rem,4vw,2.4rem)!important;line-height:1.15!important} [data-testid=stSidebar]{background:#f1f5fa}
.eyebrow{color:#188d83;font-size:.8rem;letter-spacing:2px;font-weight:700}
</style>""", unsafe_allow_html=True)


# =========================================================
# SCENARIO CONTROLS AND EXPLICIT UNMEASURED ASSUMPTIONS
# =========================================================
st.markdown('<div class="eyebrow">OKULA ÖZEL SENARYO ATÖLYESİ</div>', unsafe_allow_html=True)
st.title("Okulunuzun 3B tahliye modeli")
st.caption("Şerifali · 09.00–16.10 · öğle yemeği 12.00–13.00 · yalnızca 111 öğrenci")
st.caption("v0.7 · Ders, yemek, laboratuvar ve teneffüs için tahliye modeli; ambulans ve itfaiye için İstanbul geneli referans varışları. Oda eşleştirmeleri ve fiziksel ölçüler henüz doğrulanmadı; sonuçlar model taslağıdır.")
with st.expander('1. Senaryo girdileri · konum, sarsıntı ve açık yollar'):
    context_label = st.selectbox("Deprem hangi anda?", list(CONTEXTS), key="context")
    context = CONTEXTS[context_label]
    lab_class, lab_floor = "10A", "5"
    placement_seed = 42
    if context == 'recess':
        if 'recess_placement_seed' not in st.session_state:
            st.session_state['recess_placement_seed'] = 42
        def next_recess_placement():
            st.session_state['recess_placement_seed'] = (st.session_state['recess_placement_seed']+1) % 10001
        st.button('Yeni teneffüs dağılımı oluştur',key='new_recess_placement',on_click=next_recess_placement)
        placement_seed = st.number_input('Teneffüs yerleşim numarası',0,10000,key='recess_placement_seed')
        st.caption('111 öğrenci, aynı şubeden 2–3 kişilik arkadaş gruplarıyla derslik, laboratuvar, yemekhane, kat ortak alanları ve bahçeye rastgele yerleşir. Kütüphane, WC ve servis alanları dahil değildir. Bu gözlenmiş konum verisi değil, örnek bir teneffüs dağılımıdır; oda ve kapı geometrileri plandan yorumlanmıştır. Aynı numara aynı yerleşimi üretir, plan araması yerleri değiştirmez.')
    if context == "lab":
        lab_class = st.selectbox("Yer değiştiren şube", [row["id"] for row in PROFILE["classes"]], index=5)
        lab_floor_label = st.selectbox("Örnek laboratuvar konumu", ["5. kat", "2. bodrum"])
        lab_floor = "5" if lab_floor_label == "5. kat" else "B2"
        st.caption("Ders programı bilinmiyor. Seçim mevcut öğrencileri taşır; yeni öğrenci eklemez.")
    st.markdown("**Modelde açık güzergâhlar**")
    route_states = {route: st.checkbox(ROUTE_LABELS[route], value=True, key="route_" + route) for route in ROUTES}
    gate_open = st.checkbox("Sahaya ortak geçiş açık", value=True)
    st.caption("Üç bağımsız rota ve ortak saha geçişi örnek ağ kabulüdür. Bodrum yangın bağlantısı varsayılmadı.")
    shaking = st.slider("Örnek sarsıntı süresi (sn)", 0, 90, 20,key='shaking_seconds')
    st.caption('Konum senaryosu deprem başlangıcındaki dağılımı belirler. Öğrenciler sarsıntı sırasında başlangıç yerlerinde kalır; hazırlık ve tahliye daha sonra canlandırılır.')
    response_call_delay = st.slider("Sarsıntı sonrası acil durum bildirimi gecikmesi (sn)", 0, 600, 0, 30,
                                    help="Bu gecikme, sarsıntı bittikten sonra her iki ekibin bildirildiği varsayımına eklenir.")
    st.caption("0 sn, bildirimin sarsıntı biter bitmez yapıldığı varsayımıdır. İBB'nin İstanbul geneli 2024 ortalamaları referans alınır; okul adresi veya deprem sonrası trafik için ölçüm değildir.")
with st.sidebar:
    st.markdown("### Ayrıntılı model ayarları")
    st.caption("111 öğrenci · öğretmen ve personel kapsam dışı")
    policy_label = st.selectbox("Modelde akış dağılımı", list(POLICIES), key="policy")
    st.caption("Bu, karşılaştırmanın başlangıç modelidir; ölçülmüş okul performansı değildir.")
    reaction = st.slider("Sarsıntı sonrası harekete hazırlık (sn)", 0, 90, 12)
    with st.expander("Ölçülmemiş geçiş varsayımları"):
        st.caption("Değerler örnektir. Plandan veya sahadan ölçüldüğünde burada değiştirilebilir.")
        stair_width = st.slider("Merdiven net genişliği · örnek (m)", .5, 3., 1.1, .1)
        door_width = st.slider("Sınıf kapısı · örnek (m)", .5, 2., .9, .1)
        dining_width = st.slider("Yemekhane kapısı · örnek (m)", .5, 3., 1.2, .1)
        exit_width = st.slider("Dış çıkış genişliği · örnek (m)", .5, 3., 1.2, .1)
        gate_width = st.slider("Ortak saha geçişi · örnek (m)", .5, 4., 1.8, .1)
        corridor_width = st.slider("Koridor genişliği · örnek (m)", .5, 4., 1.6, .1)
        corridor_length = st.slider("Oda–merdiven yolu · örnek (m)", 2., 40., 10., 1.)
        stair_length = st.slider("Tam kat başına merdiven yolu · örnek (m)", 3., 20., 8., 1.)
        outdoor_length = st.slider("Çıkış–saha yolu · örnek (m)", 5., 100., 20., 5.)
        walk_speed = st.slider("Düz yolda hız · örnek (m/sn)", .3, 1.8, 1., .1)
        stair_speed = st.slider("Merdivende hız · örnek (m/sn)", .2, 1.2, .5, .1)
    with st.expander("Model akış kabulleri"):
        flow = st.number_input("Düz geçiş akışı · kişi/(m·sn)", .1, 3., 1.2, .1)
        stair_flow = st.number_input("Merdiven akışı · kişi/(m·sn)", .1, 3., .8, .1)
        storage = st.number_input("Geçiş depolama katsayısı · kişi/m²", .5, 4., 2., .1)
        st.caption("Bunlar kalibre edilmemiş model katsayılarıdır; güvenli yoğunluk sınırı veya okul ölçümü değildir.")
        seed = st.number_input("Tekrarlanabilir koşu numarası", 0, 10000, 42)
    with st.expander("Öğrenci ve sınıf davranışı"):
        speed_cv=st.slider("Öğrenciler arası örnek hız değişkenliği",0.,.4,.15,.05)
        class_spread=st.slider("Sınıflar arası örnek hazırlık farkı (sn)",0.,40.,8.,1.)
        if context == 'recess':
            group_mode=True
            st.caption('Teneffüste sınıf yerine 2–3 kişilik arkadaş grubu ortak başlangıç, rota ve tempo kullanır. Bahçedeki öğrenciler merdiven kullanmaz; saha geçişine ilerler. Kuyrukta grubun araya başka öğrenci girmeden ilerlemesi ayrıca modellenmez.')
        else:
            group_mode=st.checkbox("Sınıfça ortak başlangıç, rota ve tempo",value=True)
        release_interval=st.slider("Deneysel arkadaş grupları arası başlangıç aralığı (sn)" if context=='recess' else "Deneysel şubeler arası başlangıç aralığı (sn)",0.,10.,0.,1.)
        st.caption("Sıra: "+", ".join(row['id'] for row in PROFILE['classes'])+". Bu sıra güvenlik önceliği değildir. Hızlar öğrenci ölçümü değildir.")
        use_measurements=st.checkbox("Kaydedilmiş geçiş ölçülerini kullan",value=True)
    st.caption("School Evacuation Pilot v0.6 · yerel çalışma")

try:
    measured_edges=read_measurements(context) if use_measurements else ()
except (ValueError,KeyError,TypeError) as error:
    st.error('Kaydedilmiş ölçüm okunamadı: '+str(error));st.stop()

settings = Settings(context=context, lab_class=lab_class, lab_floor=lab_floor, policy=POLICIES[policy_label],
    closed_routes=tuple(route for route in ROUTES if not route_states[route]), gate_open=gate_open,
    reaction_mean=float(reaction), shaking_seconds=float(shaking), stair_width=stair_width,
    door_width=door_width, dining_door_width=dining_width, exit_width=exit_width, gate_width=gate_width,
    corridor_width=corridor_width, corridor_length=corridor_length, stair_length_per_floor=stair_length,
    outdoor_length=outdoor_length, walking_speed=walk_speed, stair_speed=stair_speed,
    flow_per_m=float(flow), stair_flow_per_m=float(stair_flow), storage_persons_per_m2=float(storage), seed=int(seed),
    speed_cv=speed_cv,class_reaction_spread=class_spread,group_mode=group_mode,release_interval=release_interval,
    edge_overrides=measured_edges,placement_seed=int(placement_seed))
# Same population context, shaking duration and random draws in each paired comparison.
reference_settings = Settings(context=context, lab_class=lab_class, lab_floor=lab_floor,
                              shaking_seconds=float(shaking), seed=int(seed),speed_cv=speed_cv,
                              class_reaction_spread=class_spread,edge_overrides=measured_edges,group_mode=group_mode,
                              placement_seed=int(placement_seed))


@st.cache_data(show_spinner=False, max_entries=30)
def run_model(parameters, profile_text, engine_fingerprint):
    return simulate(json.loads(profile_text), Settings(**parameters))


def seconds(value):
    return "Tamamlanmadı" if value is None else f"{value:.0f} sn"


profile_text = json.dumps(PROFILE, ensure_ascii=False)
with st.spinner("Öğrenci akışı hesaplanıyor…"):
    selected = run_model(asdict(settings), profile_text, MODEL_FINGERPRINT)
    reference = run_model(asdict(reference_settings), profile_text, MODEL_FINGERPRINT)
metrics, baseline = selected["metrics"], reference["metrics"]


# =========================================================
# EXPLAINABLE RESULTS AND PAIRED MODEL COMPARISON
# =========================================================
if selected['network']['inactive_or_unknown_measurement_ids']:
    st.info('Bu koşulda kullanılmayan ölçüm girişleri: '+', '.join(selected['network']['inactive_or_unknown_measurement_ids']))
if measured_edges:
    st.caption(f'{len(measured_edges)} geçiş ölçüsü kullanıcı girişinden alındı; ilgili geçişlerde genel kaydırıcılardan önceliklidir. Referansta da aynı ölçüler kullanılır.')
tab_scene, tab_plan, tab_flow, tab_compare, tab_trials, tab_strategies, tab_drill, tab_inputs = st.tabs(
    ["3B okul", "Kat planı", "Akış ve sonuçlar", "Referans ile karşılaştır", "Çoklu deneme", "Deney atölyesi", "Tatbikat / Ölçüler", "Veriler ve varsayımlar"])
with tab_scene:
    manual_settings=settings
    selected,settings,plan_report=planning_panel(PROFILE,manual_settings,selected)
    if plan_report and plan_report.get('recommended_settings'):
        reference_settings=manual_settings
        reference=run_model(asdict(reference_settings),profile_text,MODEL_FINGERPRINT)
        metrics,baseline=selected['metrics'],reference['metrics']
    scene_page(selected,PROFILE)
external_response = estimate_external_arrivals(
    shaking_seconds=float(settings.shaking_seconds),
    call_delay_after_shaking_seconds=float(response_call_delay),
)
with tab_plan:plans_page(selected,PROFILE)
with tab_trials:trials_page(settings,reference_settings,PROFILE)
with tab_strategies:strategies_page(settings,PROFILE)
with tab_drill:drill_page(selected,PROFILE)
with tab_flow:
    cols = st.columns(4)
    cols[0].metric("Koşu sonunda sahada", f"{metrics['assembled']} / {metrics['students']}")
    cols[1].metric("Sahaya varış süresi", seconds(metrics["assembly_seconds_after_shaking"]), help="Son öğrencinin önerilen sahaya varışı; sarsıntı bitişinden itibaren.")
    cols[2].metric("Ortalama geçiş beklemesi", seconds(metrics["mean_wait_seconds"]))
    cols[3].metric("Sahaya ulaşamayan", str(metrics["unresolved"]))
    st.caption("Varış süreleri sarsıntının bitişinden itibaren ölçülür; hazırlık ve yolculuk dahildir. Animasyon saati deprem başlangıcından başlar. Yoklama ve yetişkin akışı bu sürümde hesaplanmaz.")
    st.caption("Üstteki kartlar koşunun son sonucunu; animasyon zaman çizgisindeki anı gösterir.")

    st.markdown("#### Acil ekipler için örnek varış zamanı")
    response_columns = st.columns(2)
    for column, service, title in (
        (response_columns[0], "ambulance", "Ambulans"),
        (response_columns[1], "fire", "İtfaiye"),
    ):
        estimate = external_response["services"][service]
        column.metric(
            f"{title} · deprem başlangıcından",
            estimate["arrival_from_earthquake_label"],
            help=f"Sarsıntı sonundan: {estimate['arrival_after_shaking_label']}. Referans: {estimate['reference_label']}.",
        )
        column.caption(f"Çağrıdan sonra referans süre: {format_duration(estimate['reference_seconds'])} · [İBB kaynağı]({estimate['reference_url']})")
    st.caption(
        f"Varsayım: her iki ekibe de sarsıntı bittikten {format_duration(response_call_delay)} sonra bildirim yapılıyor; "
        "bildirimden sonra 2024 İstanbul geneli ortalaması uygulanıyor. Bu bir okul/rota ETA'sı değildir; "
        "deprem kaynaklı trafik, yol kapanması ve ekip yoğunluğu henüz hesaba katılmıyor."
    )
    if metrics["unresolved"] == 0 and metrics["assembly_seconds_after_shaking"] is not None:
        evacuation_seconds = metrics["assembly_seconds_after_shaking"]
        ambulance_seconds = external_response["services"]["ambulance"]["arrival_after_shaking_seconds"]
        fire_seconds = external_response["services"]["fire"]["arrival_after_shaking_seconds"]
        first_response = min(ambulance_seconds, fire_seconds)
        if evacuation_seconds <= first_response:
            st.info(f"Bu model koşusunda son öğrenci, ilk dış ekip varış referansından {format_duration(first_response-evacuation_seconds)} önce sahaya ulaşıyor.")
        else:
            st.info(f"Bu model koşusunda ilk dış ekip varış referansı, son öğrencinin sahaya ulaşmasından {format_duration(evacuation_seconds-first_response)} önceye denk geliyor.")

    if metrics["unresolved"]:
        st.error(f"{metrics['unresolved']} öğrenci sahaya ulaşamadı. Dışarı çıkan: {metrics['outside']}. Rota bulunamayan: {metrics['unreachable']}. Süre sınırına takılan: {metrics['timed_out']}. Tam tahliye süresi ve iyileşme yüzdesi verilmiyor.")
    else:
        top = next((row for row in selected["queues"] if row["total_wait_seconds"] > .01), None)
        if top:
            st.info(f"Bu koşuda en fazla toplam bekleme: {top['label']}. Burada bekleme talepleri en çok {top['peak_queue']} kişiye ulaştı. Bu, örnek modelin bulgusudur.")

    animated_chart(playback(selected),610)
    st.caption("Gri: korunma/hazırlık · Mavi: ilerleme · Sarı: bekleme · Yeşil: sahada · Kırmızı: rota yok · Mor: dışarıda, sahaya ulaşamadı. Noktalar anonim model öğrencileridir; çizim ölçekli kat planı değildir.")
    st.plotly_chart(cumulative(selected), width="stretch", theme=None, config={"displayModeBar": False}, key="cumulative")
    table = [{"Geçiş": row["label"], "En çok bekleme talebi": row["peak_queue"],
              "Toplam bekleme (kişi·sn)": round(row["total_wait_seconds"], 1), "Geçen öğrenci": row["entered"]}
             for row in selected["queues"] if row["entered"] and row["total_wait_seconds"] > .01][:8]
    st.markdown("#### Beklemenin biriktiği geçişler")
    st.dataframe(table, width="stretch", hide_index=True)
with tab_compare:
    st.markdown("#### Aynı yerleşim, aynı öğrenci grubu")
    st.write("Referans, seçtiğin ders/yemek/laboratuvar/teneffüs yerleşiminin başlangıç ayarlarıdır. Ölçülmüş mevcut okul performansı değildir. Sarsıntı süresi, davranış çekilişleri ve teneffüs yerleşimi iki tarafta aynıdır.")
    a, b, c = st.columns(3)
    a.metric("Referans saha varışı", seconds(baseline["assembly_seconds_after_shaking"]))
    b.metric("Seçili koşu saha varışı", seconds(metrics["assembly_seconds_after_shaking"]))
    bt, now = baseline["assembly_seconds_after_shaking"], metrics["assembly_seconds_after_shaking"]
    if bt is not None and now is not None and bt > 0:
        change = (bt - now) / bt * 100
        c.metric("Modelde süre değişimi", f"{abs(change):.1f}% {'kısaldı' if change > 0 else 'uzadı' if change < 0 else 'aynı'}")
    else:
        c.metric("Modelde süre değişimi", "Karşılaştırılamaz")
    differences = [{"Ayar": key, "Referans": str(value), "Seçili": str(asdict(settings)[key])}
                   for key, value in asdict(reference_settings).items() if value != asdict(settings)[key]]
    if differences:
        st.dataframe(differences, hide_index=True, width="stretch")
    else:
        st.info("Ayarlar referansla aynı. Bir merdiveni kapatmayı veya geçiş genişliğini değiştirmeyi deneyebilirsin.")
    st.markdown("#### Şube bazında seçili koşu")
    class_table = []
    for row in PROFILE['classes']:
        people = [p for p in selected["persons"] if p["class_id"] == row['id']]
        all_arrived = all(p["arrived_at"] is not None for p in people)
        class_table.append({"Şube": row['id'], "Başlangıç katı": ', '.join(dict.fromkeys(p['floor'] if p.get('origin_kind')!='yard' else 'Bahçe' for p in people)), "Öğrenci": len(people),
            "Sahaya varan": sum(p["arrived_at"] is not None for p in people),
            "Son varış (sarsıntı sonrası sn)": round(max(p["arrived_at"] for p in people) - settings.shaking_seconds, 1) if all_arrived else None})
    st.dataframe(class_table, hide_index=True, width="stretch")
    export = {"notice": "Illustrative uncalibrated student-only network; external response values are citywide references, not school-specific ETAs; not a verified emergency plan", "external_response": external_response, "reference": reference, "selected": selected}
    st.download_button("Koşuyu ve varsayımları JSON indir", json.dumps(export, ensure_ascii=False, indent=2),
                       file_name="school_evacuation_model_run.json", mime="application/json")
with tab_inputs:
    st.markdown("#### Bildiğimiz veriler")
    st.dataframe(pd.DataFrame(PROFILE["classes"])[["id", "students", "home_floor"]].rename(
        columns={"id": "Şube", "students": "Öğrenci", "home_floor": "Ders katı"}), hide_index=True, width="stretch")
    st.write("Öğrenci sayıları ve katlar kullanıcıdan. Öğle yemeğine birlikte gidiliyor; yemek salonu eski planda B1'de. Yangın merdivenleri kullanıcı beyanına göre açık. Kütüphane ziyareti kapalı.")
    with st.expander("Kaynak plan fotoğrafını göster"):
        manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
        plan_labels = {row["title"]: row for row in manifest["images"]}
        plan_choice = st.selectbox("Kaynak plan", list(plan_labels), index=5, key="source_plan")
        plan = plan_labels[plan_choice]
        try:
            image_path = source_plan(plan["file"],plan["sha256"])
            st.image(str(image_path), caption="2020 tarihli kaynak çizim; güncel ölçülü ağ veya bina performansı doğrulaması değildir.", width="stretch")
        except ValueError as error:
            st.error(str(error))
    st.markdown("#### Bu modelde örnek olanlar")
    st.write("Oda–merdiven bağlantıları, üç bağımsız çıkış, ortak saha geçişi, tüm uzunluk/genişlikler, hızlar ve akış katsayıları. Bunlar 2020 çiziminden otomatik ölçülmedi. Asma kat modelde ayrıca geçilir; bodrum yangın merdivenine bağlanmaz.")
    st.write("Geçişler sınırlı kapasite, giriş aralığı ve bekleme sırasıyla modellenir. Dolu sonraki geçiş önceki geçişi tutabilir. Bu ağ modeli; beden çarpışması, ezilme, düşme, hasar veya kalabalık basıncı hesaplamaz. Basit dağıtım politikası tüm alt geçişlerdeki kuyrukları önceden bilen bir optimizer değildir.")
    st.markdown("#### Henüz çalıştırılmayan senaryolar")
    st.write("Teneffüsün oda, ortak alan ve bahçeye dağılan rastgele örnek yerleşimi çalışır; gerçek teneffüs konumları gözlenmedi. Öğle geçişi/16.10 konumları, refakat ihtiyacı ve artçı davranışı için başlangıç verisi eksik. Saha yoklaması ayrıca eklenecek.")
    st.json(asdict(settings), expanded=False)
    st.markdown("[AFAD okul deprem rehberi](https://afad.gov.tr/deprem-oncesi-ani-ve-sonrasi-alabileceginiz-onlemleri-biliyor-musunuz) · [NIST merdiven hareketi araştırması](https://www.nist.gov/publications/movement-stairs-during-building-evacuations)")
