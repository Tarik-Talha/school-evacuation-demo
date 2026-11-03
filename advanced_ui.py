"""Plan placement, repeated experiments, drill input and portable 3D views."""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from experiments import compare_drill, paired_trials, strategy_trials
from scene_export import scene_payload, usda_text
from spatial import load_layout, plan_figure, save_layout, validate_layout, view3d
from visuals import animated_chart
from school_scene import show_scene
from state_store import read_json,write_json

ROOT=Path(__file__).resolve().parent


def signature(settings,reference,profile):
    code=''.join((ROOT/name).read_text(encoding='utf-8') for name in ('engine.py','experiments.py'))
    return hashlib.sha256((code+json.dumps([asdict(settings),asdict(reference),profile],sort_keys=True)).encode()).hexdigest()


def read_measurements(context):
    rows=read_json(f'measurements_{context}.json',[])
    return tuple((row['id'],float(row['length']),float(row['width'])) for row in rows)


# =========================================================
# PLAN VIEW AND EXPLICIT CLASS-ROOM CONFIRMATION
# =========================================================
def plans_page(result,profile):
    layout=validate_layout(load_layout(),profile)
    st.markdown('#### Kat planı üzerinde öğrenci akışı')
    confirmed=sum(row['user_confirmed'] for row in layout['class_mapping'].values())
    st.info(f'{confirmed}/10 oda eşleşmesi kullanıcı tarafından doğrulandı. Diğerleri örnek atamadır. Noktalı bağlantılar görsel işaretlemedir; ölçülü kaçış güzergâhı değildir.')
    levels=list(layout['floors'])
    default='B1' if result['settings']['context']=='lunch' else result['settings']['lab_floor'] if result['settings']['context']=='lab' else '1'
    floor=st.selectbox('Görüntülenen kat',levels,index=levels.index(default),key='plan_floor_'+result['settings']['context'])
    end=max(1.,result['metrics']['elapsed_seconds_from_onset'])
    time=st.slider('Plan oynatıcısı başlangıç anı · deprem başlangıcından sn',0.,end,0.,key='plan_time')
    try:
        fig,count=plan_figure(result,layout,floor,time)
        animated_chart(fig,620)
        st.caption(f'Seçilen başlangıç anında bu katta: {count} / 111. Oynat düğmesi grafiğin kendi saatini ilerletir. Diğer öğrenciler başka katlarda, katlar arası geçişte veya dışarıdadır. Merdivendeki nokta geçişin yarısında sonraki kata yansıtılır; bu bir gösterim kuralıdır.')
    except ValueError as error:st.error(str(error))
    with st.expander('Sınıfları plandaki odalara yerleştir'):
        with st.form('room_mapping'):
            updated=copy.deepcopy(layout)
            for row in profile['classes']:
                key=row['id'];floor_id=row['home_floor'];options=list(layout['floors'][floor_id]['rooms'])
                current=layout['class_mapping'][key]
                room=st.selectbox(f"{key} · {floor_id}. kat",options,index=options.index(current['room_id']),
                    format_func=lambda value,floor_id=floor_id:layout['floors'][floor_id]['rooms'][value]['label'],key='mapping_'+key)
                verified=st.checkbox(f'{key} oda bilgisini okuldan doğruladım',value=current['user_confirmed'],key='confirmed_'+key)
                updated['class_mapping'][key]={'floor':floor_id,'room_id':room,'user_confirmed':verified}
            save=st.form_submit_button('Oda eşleşmelerini kaydet')
        if save:
            try:save_layout(updated,profile);st.success('Bu oturumun eşleşmeleri kaydedildi. Görünüm yenileniyor.');st.rerun()
            except ValueError as error:st.error(str(error))
        st.caption('Oda eşleştirmesi görsel başlangıç konumunu değiştirir. Yol süreleri pikselden hesaplanmaz; ölçülen geçiş değerleri ayrıca Tatbikat / Ölçüler bölümünde girilir.')


# =========================================================
# REPEATED RUN DISTRIBUTIONS WITHOUT SURVIVOR BIAS
# =========================================================
def trials_page(settings,reference,profile):
    st.markdown('#### Tek sayı yerine denemelerin dağılımı')
    st.write('Aynı öğrenci grubu farklı örnek hız ve hazırlık çekilişleriyle tekrar çalıştırılır. İki tarafta aynı koşu numaraları kullanılır. %5–%95 aralığı model değişkenliğidir; gerçek deprem için güven aralığı değildir.')
    count=st.select_slider('Eşlenmiş deneme sayısı',options=[20,50,100,200],value=100,key='trials_count')
    sig=signature(settings,reference,profile)+str(count)
    if st.button('Çoklu karşılaştırmayı çalıştır',key='run_trials'):
        bar=st.progress(0.,text='Aynı başlangıçlarla karşılaştırılıyor…')
        with st.spinner(f'{count} referans ve {count} seçili deneme çalışıyor…'):
            report=paired_trials(profile,reference,settings,count,lambda value:bar.progress(value))
        st.session_state['trials_report']=(sig,report);bar.empty()
    saved=st.session_state.get('trials_report')
    if not saved:return
    if saved[0]!=sig:st.info('Ayarlar veya deneme sayısı değişti. Güncel sonuç için yeniden çalıştır.');return
    report=saved[1]
    def row(label,summary):
        return {'Koşul':label,'Tamamlanan':f"{summary['complete_runs']}/{summary['requested_runs']}",
                'Ortanca süre (sn)':summary['median_seconds_completed_only'],'%5 eşiği (sn)':summary['p05_seconds_completed_only'],
                '%95 eşiği (sn)':summary['p95_seconds_completed_only'],'En çok ulaşamayan':summary['max_unresolved']}
    st.dataframe([row('Referans',report['reference']),row('Seçili',report['selected'])],hide_index=True,width='stretch')
    if report['all_pairs_complete']:
        saved_seconds=report['median_seconds_saved']
        st.success(f"Eşlenmiş denemelerde ortanca süre farkı: {saved_seconds:+.1f} sn. Pozitif değer seçili koşunun daha kısa sürdüğünü gösterir. {report['selected_faster_run_count']}/{count} denemede seçili koşu daha kısa sürdü.")
    else:st.warning('Tamamlanmayan denemeler var. Süre dağılımları yalnız tamamlananlara aittir; iyileşme sonucu verilmiyor.')
    fig=go.Figure()
    for key,label,color in [('reference','Referans','#9aa8ba'),('selected','Seçili','#188d83')]:
        values=[run['assembly_seconds_after_shaking'] for run in report[key]['runs'] if run['assembly_seconds_after_shaking'] is not None]
        if values:fig.add_trace(go.Histogram(x=values,name=label,opacity=.6,marker_color=color))
    fig.update_layout(barmode='overlay',height=300,xaxis_title='Sarsıntı sonrası saha varışı (sn)',yaxis_title='Tamamlanan deneme sayısı',margin={'l':30,'r':15,'t':25,'b':40})
    st.plotly_chart(fig,width='stretch',key='trial_hist')
    st.write('Seçili koşuda en sık toplam bekleme biriken geçişler:')
    st.dataframe([{'Geçiş':key,'Deneme sayısı':value} for key,value in report['selected']['bottleneck_frequency'].items()][:6],hide_index=True,width='stretch')
    st.download_button('Çoklu koşu raporunu indir',json.dumps(report,ensure_ascii=False,indent=2),file_name='school_paired_trials.json',mime='application/json',key='trials_download')


def strategies_page(settings,profile):
    st.markdown('#### Akış düzenlerini aynı koşullarda dene')
    st.write('Dört deney düzeni karşılaştırılır. Sınıfça mod ortak başlangıç, rota ve tempo kullanır; birleşen kuyruklarda sınıfların arasına girme ayrıca engellenmez. Başlangıç aralığı profil dosyasındaki şube sırasını kullanır; bu sıra güvenlik önceliği değildir.')
    count=st.select_slider('Düzen başına deneme',options=[10,20,30,50,100],value=30,key='strategies_count')
    sig=signature(settings,settings,profile)+str(count)
    if st.button('Dört akış düzenini karşılaştır',key='run_strategies'):
        bar=st.progress(0.,text='Deney düzenleri çalışıyor…')
        report=strategy_trials(profile,settings,count,lambda value:bar.progress(value));bar.empty()
        st.session_state['strategies_report']=(sig,report)
    saved=st.session_state.get('strategies_report')
    if not saved:return
    if saved[0]!=sig:st.info('Ayarlar değişti; düzen karşılaştırmasını yeniden çalıştır.');return
    report=saved[1]
    st.dataframe([{'Düzen':r['label'],'Tamamlanan':f"{r['summary']['complete_runs']}/{count}",
        'Ortanca (sn)':r['summary']['median_seconds_completed_only'],'%95 eşiği (sn)':r['summary']['p95_seconds_completed_only'],
        'Ortalama bekleme (sn)':r['summary']['mean_wait_seconds']} for r in report['variants']],hide_index=True,width='stretch')
    if report['fastest_complete_model_variant']:
        st.info('Tamamlanan model koşuları içinde en kısa ortancaya sahip düzen: '+report['fastest_complete_model_variant']+'. Bu, uygulanabilirlik veya güvenlik onayı değildir.')
    else:st.warning('Bütün denemeleri tamamlayan düzen yok; öneri üretilmedi.')
    st.download_button('Düzen karşılaştırmasını indir',json.dumps(report,ensure_ascii=False,indent=2),file_name='school_strategy_trials.json',mime='application/json')


# =========================================================
# MEASURED EDGE INPUT AND DRILL MILESTONE COMPARISON
# =========================================================
def drill_page(result,profile):
    st.markdown('#### Tatbikatla modelin farkını gör')
    st.write('Zamanları sarsıntının bitişinden itibaren saniye olarak gir. İlk hareket, modelde ilk geçişe giriş anıdır. Pozitif hata modelin daha geç, negatif hata daha erken tamamladığını gösterir. Karşılaştırma parametreleri otomatik değiştirmez.')
    event_labels={'İlk hareket':'first_move','Son dış çıkış':'last_exit','Son saha varışı':'last_assembly'}
    data=pd.DataFrame({'Olay':list(event_labels),'Şube':['Tümü']*3,'Ölçülen saniye':[None]*3})
    source=st.selectbox('Kayıt türü',['Örnek / doğrulanmamış','Gerçek tatbikat ölçümü'],key='drill_source')
    record_id=st.text_input('Tatbikat kayıt adı',placeholder='Örn. 2026-10-20 tatbikatı',key='drill_name')
    edited=st.data_editor(data,num_rows='dynamic',hide_index=True,key='drill_data',width='stretch',
        column_config={'Olay':st.column_config.SelectboxColumn(options=list(event_labels),required=True),
          'Şube':st.column_config.SelectboxColumn(options=['Tümü']+[r['id'] for r in profile['classes']],required=True),
          'Ölçülen saniye':st.column_config.NumberColumn(min_value=0,step=1)})
    if st.button('Tatbikatla karşılaştır',key='compare_drill'):
        observations=[]
        for row in edited.to_dict('records'):
            if pd.isna(row['Ölçülen saniye']):continue
            observations.append({'event':event_labels.get(row['Olay'],''),'class_id':'ALL' if row['Şube']=='Tümü' else row['Şube'],
                                 'seconds_after_shaking':float(row['Ölçülen saniye'])})
        try:
            if not observations:raise ValueError('En az bir ölçüm gir.')
            report=compare_drill(result,observations)
            st.dataframe(report['rows'],hide_index=True,width='stretch')
            st.write(f"Eşleşen ölçüm: {report['matched_count']}/{report['observation_count']}. Ortalama mutlak zaman farkı: {report['mae_seconds']:.1f} sn." if report['mae_seconds'] is not None else 'Karşılaştırılabilir model olayı yok; tamamlanmayan tahliye için süre uydurulmadı.')
            report.update(record_id=record_id,source=source,settings=result['settings'])
            if source=='Gerçek tatbikat ölçümü' and not record_id.strip():raise ValueError('Gerçek ölçümün izlenebilmesi için kayıt adı gir.')
            write_json('last_drill_comparison.json',report)
            st.download_button('Bu karşılaştırmayı indir',json.dumps(report,ensure_ascii=False,indent=2),file_name='school_drill_comparison.json',mime='application/json')
            st.caption('Bir tatbikat veya küçük hata tek başına doğrulama değildir. Farklı tatbikatlarla bağımsız kontrol gerekir; model hâlâ kalibre edilmiş olarak işaretlenmez.')
        except ValueError as error:st.error(str(error))
    with st.expander('Ölçülmüş bir geçiş değeri gir'):
        edges=result['network']['edges'];key=st.selectbox('Ölçülen geçiş',list(edges),format_func=lambda key:edges[key]['label'],key='measured_edge')
        edge=edges[key]
        with st.form('edge_measurement'):
            length=st.number_input('Ölçülen yol uzunluğu (m)',.1,500.,float(edge['length']),.1,key='measure_len_'+key)
            width=st.number_input('Ölçülen net genişlik (m)',.3,10.,float(edge['width']),.1,key='measure_width_'+key)
            evidence=st.text_input('Ölçümün kaynağı / notu',key='measure_note')
            save=st.form_submit_button('Ölçtüğüm değeri modele kaydet')
        if save:
            if not evidence.strip():st.error('Ölçümün kaynağını veya notunu yaz.')
            else:
                context=result['settings']['context']
                rows=read_json(f'measurements_{context}.json',[])
                rows=[row for row in rows if row['id']!=key]+[{'id':key,'length':length,'width':width,'source':evidence}]
                write_json(f'measurements_{context}.json',rows);st.rerun()
        st.caption('Ölçüm yalnız bu tarayıcı oturumunda ve bu yerleşim türünde saklanır. Kapalı veya farklı yerleşimde bulunmayan geçişler kullanılmaz ve ekranda bildirilir. Kullanıcı girişi bağımsız saha doğrulaması sayılmaz.')


# =========================================================
# 3D VIEW AND OPENUSD EXPORT OF THE SAME MODEL RUN
# =========================================================
def scene_page(result,profile):
    layout=validate_layout(load_layout(),profile)
    st.markdown('#### 3. Planı 3B incele')
    modes={'Katı incele':'floor','Okulun tamamı':'building','Katları ayır':'separated'}
    recess=result['settings']['context']=='recess'
    mode=st.radio('3B görünüm',list(modes),index=1 if recess else 0,horizontal=True,
                  key='scene_mode_recess' if recess else 'scene_mode')
    floors=['B2','B1','G','M','1','2','3','4','5','6']
    default='G' if recess else 'B1' if result['settings']['context']=='lunch' else result['settings']['lab_floor'] if result['settings']['context']=='lab' else '3'
    labels={'B2':'2. bodrum · laboratuvar','B1':'1. bodrum · yemekhane','G':'Zemin kat','M':'Asma kat'}
    floor=st.selectbox('İncelenen kat',floors,index=floors.index(default),format_func=lambda v:labels.get(v,v+'. kat'),key='scene_floor_'+result['settings']['context'],disabled=modes[mode]!='floor')
    routes=st.checkbox('Model güzergâhlarını göster',value=False,key='scene_routes')
    if recess:
        st.info(f"Başlangıçta 111 öğrenci, {len(result['network']['groups'])} arkadaş grubuna dağılmış durumda. Oda içleri, kat ortak alanları ve bahçe gösterilir; bu yerleşim rastgele model örneğidir, gözlem kaydı değildir.")
    st.caption('Tekerlek sayfayı kaydırır. Yakınlaştırma + / − ile; sahneyi çevirmek için Fareyle döndür düğmesini aç. Oynatıcı sıfırdan başlar.')
    show_scene(result,layout,floor,modes[mode],routes)
    st.caption(('Teneffüste her nokta bir öğrenciyi gösterir; gruplar derslik, laboratuvar, yemekhane, ortak alan ve bahçeye rastgele dağılır. ' if recess else 'Kat kesitinde yalnız görünen kattaki öğrenciler çizilir; ')+ 'Sayaçlar okulun 111 öğrencisini kapsar. Oda atamaları ve oranlar planlardan yorumlandı; ölçülü mimari model ve doğrulanmış tahliye planı değildir.')
    with st.expander('Blender / OpenUSD aktarımı'):
        if st.button('3B aktarım dosyalarını hazırla',key='prepare_scene'):
            payload=scene_payload(result,layout)
            st.session_state['scene_payload']=(hashlib.sha256(json.dumps([result['settings'],layout],sort_keys=True).encode()).hexdigest(),payload)
        saved=st.session_state.get('scene_payload')
        sig=hashlib.sha256(json.dumps([result['settings'],layout],sort_keys=True).encode()).hexdigest()
        if saved and saved[0]==sig:
            payload=saved[1]
            st.download_button('Animasyonlu OpenUSD dosyasını indir',usda_text(payload),file_name='school_evacuation.usda',mime='text/plain',key='usd_download')
            st.download_button('Blender aktarım verisini indir',json.dumps(payload,ensure_ascii=False),file_name='school_evacuation.json',mime='application/json',key='scene_json_download')
            st.caption('USD: metre birimi, Z yukarı; boyutlar örnektir. Omniverse testi yapılmadı. Hazır v0.2 Blender dosyası önceki sürümün arşividir; buradan güncel koşu indirilir.')
