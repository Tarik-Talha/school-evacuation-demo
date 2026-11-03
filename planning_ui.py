"""TwinOps-style inputs → bounded search → explained comparison → 3D preview."""
from dataclasses import asdict
import json
from pathlib import Path
from state_store import write_json
import streamlit as st
from engine import Settings,ROUTE_LABELS
from planner import SearchConfig,OBJECTIVES,fingerprint,recommend_plan

ROOT=Path(__file__).parent

def _seconds(value):return 'Tamamlanmadı' if value is None else f'{value:.1f} sn'

def planning_panel(profile,settings,current):
    st.markdown('#### 2. Bu koşullar için model planını bul')
    recess=settings.context=='recess'
    context={'lesson':'Dersliklerde','lunch':'Yemekhanede','lab':'Örnek laboratuvar yerleşiminde',
             'recess':'Teneffüste · okul geneline dağılmış arkadaş grupları'}[settings.context]
    opened=[name for route,name in ROUTE_LABELS.items() if route not in settings.closed_routes]
    st.caption(f"{context} · {sum(g['students'] for g in current['network']['groups'])} öğrenci · sarsıntı {settings.shaking_seconds:g} sn · açık rota: {', '.join(opened) or 'yok'}")
    allocation='Dağıtılmış model akışı' if settings.policy=='balanced' else 'En kısa model rotası'
    st.caption('Başlangıç rota kuralı: '+allocation+'. Mevcut düzen, seçili başlangıç modelidir; okulun ölçülmüş/onaylı planı değildir.')
    if recess:
        st.caption(f"{len(current['network']['groups'])} arkadaş grubu planlanır; aynı şubenin öğrencileri farklı yerlerde olabilir. "
                   f"Yerleşim {settings.placement_seed}: bütün seçeneklerde ve kontrol koşularında aynı öğrenciler aynı yerde kalır; "
                   '2–3 kişilik arkadaş grupları birlikte hareket eder. Bahçedekiler iç merdiven kullanmaz.')
    target=st.selectbox('Planlamada öncelik',list(OBJECTIVES),format_func=lambda key:OBJECTIVES[key],key='planner_objective')
    with st.expander('Arama sınırları'):
        effort=st.selectbox('Arama ayrıntısı',['Hızlı','Standart','Ayrıntılı'],index=1,key='planner_effort')
        delay=st.slider('Arkadaş grubu başına izin verilen ilave başlangıç beklemesi (sn)' if recess else
                        'Şube başına izin verilen ilave başlangıç beklemesi (sn)',0,15,0,key='planner_delay')
        st.caption('0 seçilirse plan araması ilave bekleme ekleyemez. Hızlar, kapı genişlikleri, sarsıntı ve kapalı rotalar sabittir. '+
                   ('Arkadaş grupları her seçenekte ortak başlangıç, rota ve tempoyu korur; yerleşim aramayla değiştirilmez.' if recess else
                    'Şubelerin aynı tempoda kalması soldaki sınıfça hareket ayarına bağlıdır.'))
    budget,trials,held={'Hızlı':(24,3,10),'Standart':(48,4,20),'Ayrıntılı':(96,6,30)}[effort]
    config=SearchConfig(budget=budget,search_runs=trials,validation_runs=held,max_extra_delay=float(delay),objective=target)
    sig=fingerprint(profile,settings,config)
    if st.button('Bu koşullar için plan öner',type='primary',key='recommend_plan'):
        bar=st.progress(0.,text='Model seçenekleri hazırlanıyor…')
        try:
            with st.spinner('Aynı öğrenci koşullarıyla planlar karşılaştırılıyor…'):
                report=recommend_plan(profile,settings,config,lambda value,stage:bar.progress(value,text=stage))
            st.session_state['planner_report']=(sig,report)
            write_json('last_planner_report.json',report)
        except ValueError as error:st.error(str(error))
        finally:bar.empty()
    saved=st.session_state.get('planner_report')
    if not saved:
        st.caption('Arama çalıştırılana kadar mevcut düzen gösterilir. Sarsıntı süresi başlangıcı öteler; bina hasarı veya rota güvenliği bu sayıdan hesaplanmaz. '+
                   ('Teneffüs yerleşimi rastgele bir model örneğidir; okulda gözlenmiş dağılım değildir.' if recess else ''))
        return current,settings,None
    if saved[0]!=sig:
        st.info('Girdiler veya arama sınırları değişti. Önceki öneri bu koşullarda uygulanmıyor; yeniden plan ara.')
        return current,settings,None
    report=saved[1]
    if report['recommended_settings'] is None:
        st.error('Bu model koşullarında tamamlanan bir plan önerilemedi. '+report.get('reason',''))
        st.caption('Kapalı yollar otomatik açılmadı; öğrenci veya güzergâh eklenmedi.')
        st.download_button('Arama sonucunu indir',json.dumps(report,ensure_ascii=False,indent=2),file_name='school_plan_search.json',mime='application/json',key='failed_plan_download')
        return current,settings,report
    st.markdown('**Model önerisi · okulda doğrulama ve onay bekleyen taslak**')
    if report['status']=='recommended':st.success(report['reason'])
    else:st.info(report['reason'])
    validation=report['validation'];base=validation['reference'];chosen=report['recommended_summary'];paired=report['displayed_paired']
    delta=paired['median_seconds_saved']
    if delta is not None and abs(delta)>.05:
        st.markdown(f"**Kontrol koşularında ortanca {abs(delta):.1f} sn {'daha kısa' if delta>0 else 'daha uzun'}.**")
    elif delta is None:st.caption('Tamamlanmayan başlangıç koşulları için süre farkı hesaplanmadı; tamamlanma sayıları ayrıntıda gösteriliyor.')
    else:st.caption('Mevcut düzen korunuyor; gösterilen plan farkı 0 sn.')
    with st.expander('Sonuç farkları ve bu planın gerekçesi'):
        a,b,c=st.columns(3)
        a.markdown('**Mevcut düzen · ortanca**\n\n'+_seconds(base['median_seconds']))
        b.markdown('**Seçilen düzen · ortanca**\n\n'+_seconds(chosen['median_seconds']))
        saved_seconds=paired['median_seconds_saved']
        c.markdown('**Eşlenmiş ortanca fark**\n\n'+('Karşılaştırılamaz' if saved_seconds is None else f'{saved_seconds:+.1f} sn'))
        st.caption('Süreler sarsıntı bitişinden itibaren. Pozitif fark seçilen düzenin daha kısa sürdüğünü gösterir. Aynı koşuların fark ortancası, iki ayrı ortancanın farkından farklı olabilir.')
        st.dataframe([
           {'Düzen':'Mevcut','Tamamlanan':f"{base['complete_runs']}/{held}",'Süre %95 eşiği (sn)':base['p95_seconds'],
            'Ortalama bekleme (sn)':base['mean_wait_seconds'],'En yüksek bekleme talebi':base['max_peak_queue']},
           {'Düzen':'Seçilen','Tamamlanan':f"{chosen['complete_runs']}/{held}",'Süre %95 eşiği (sn)':chosen['p95_seconds'],
            'Ortalama bekleme (sn)':chosen['mean_wait_seconds'],'En yüksek bekleme talebi':chosen['max_peak_queue']}],hide_index=True,width='stretch')
        if saved_seconds is not None and saved_seconds<-.05:
            st.info(f'Seçilen hedefte bekleme kazanımı olsa da varış süresi ortanca {abs(saved_seconds):.1f} sn uzuyor. Bu farkı birlikte değerlendir.')
        validation_label='Mevcut düzen' if report['training_winner_id']=='current' else 'Seçilen aday ve mevcut düzen'
        st.write(f"{report['candidate_count']} model seçeneği tarandı; her biri {trials} ortak koşuyla değerlendirildi. {validation_label}, aramada kullanılmayan {held} koşuyla kontrol edildi.")
        st.caption('Sonuç denenmiş seçenekler içindir; bütün olası planların matematiksel optimumu değildir. %5–%95 eşikleri model değişkenliğidir. Bekleme talebi, güvenli kalabalık yoğunluğu sınırı değildir.')
        if recess:
            st.caption(f"Yerleşim bütün {report['placement_verified_runs']} hesapta değişmeden korundu. Kontrol koşuları bu sabit yerleşimdeki davranış değişkenliğini dener; bütün olası teneffüs dağılımlarını kapsamaz.")
        if validation['candidate_id']!='current' and not validation['candidate_accepted']:
            candidate_gain=validation['objective_gain_percent']
            st.caption('Arama adayı kontrol aşamasında elendi. '+(f'Hedef puanı değişimi %{candidate_gain:.2f}; kabul için en az %{config.minimum_gain*100:g} azalma ve kontrol koşularının en az %60’ında hedefte kazanım aranır.' if candidate_gain is not None else 'Adayın bütün kontrol koşuları tamamlanmadı.'))
        st.markdown('**Neden bu düzen?**')
        if report['status']=='recommended':
            gain=validation['objective_gain_percent']
            st.write(f"Hedef: {report['objective_label']}. "+(f"Süre, bekleme ve kuyruk bileşenlerinden oluşan hedef puanı kontrol koşularında %{gain:.1f} azaldı." if gain is not None else 'Mevcut düzenin tamamlanmayan koşuları varken seçilen taslak bütün kontrol koşularını tamamladı.'))
        else:st.write('Arama, yeterli kazanım bulamadığında mevcut düzeni değiştirmiyor. Başka koşullarda yeniden denenebilir.')
        before=next((q['label'] for q in report['baseline_run']['queues'] if q['total_wait_seconds']>.001),'Belirgin bekleme yok')
        after=next((q['label'] for q in report['recommended_run']['queues'] if q['total_wait_seconds']>.001),'Belirgin bekleme yok')
        st.caption(f'Örnek koşuda en çok toplam bekleme biriken geçiş: mevcutta {before}; seçilen düzende {after}. Bu, çoklu koşu ortalaması değildir.')
    with st.expander('Arkadaş gruplarını ve arama ayrıntılarını incele' if recess else 'Şube dağılımını ve arama ayrıntılarını incele'):
        if recess:
            st.dataframe([{'Arkadaş grubu':r['group_id'],'Şube':', '.join(r['class_ids']),'Öğrenci':r['students'],
                           'Başlangıç katı':r['floor'],'Başlangıç alanı':r['area_label'],
                           'Model güzergâhı':r['route_label'],'Plan beklemesi (sn)':r['additional_delay_seconds']}
                          for r in report['class_plan']],hide_index=True,width='stretch')
        else:
            st.dataframe([{'Şube':r['class_id'],'Öğrenci':r['students'],'Başlangıç katı':r['floor'],
              'Model güzergâhı':r['route_label'],'Plan beklemesi (sn)':r['additional_delay_seconds']} for r in report['class_plan']],hide_index=True,width='stretch')
        st.dataframe([{'Seçenek':'Mevcut' if r['id']=='current' else r['id'],'Tamamlanan':f"{r['summary']['complete_runs']}/{trials}",
           'Ortanca (sn)':r['summary']['median_seconds'],'Hedef puanı · düşük daha iyi':r['score']} for r in report['training']],hide_index=True,width='stretch')
        st.caption('Ek başlangıç beklemeleri gerçek zamanda uygulanacak emir değildir. Bina bağlantıları, oda eşleştirmeleri ve gerçek tatbikat sonuçları doğrulanmadan okul planı olarak kullanılmaz.')
        st.markdown('[Model doğrulama yaklaşımı · NIST](https://www.nist.gov/publications/process-verification-and-validation-building-fire-evacuation-models)')
    st.download_button('Planı ve karşılaştırma raporunu indir',json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),file_name='school_model_plan.json',mime='application/json',key='planner_download')
    labels=['Mevcut düzen','Modelin seçtiği düzen']
    view=st.radio('3B sahnede göster',labels,index=1 if report['status']=='recommended' else 0,horizontal=True,key='planner_view_'+sig[:12])
    if view==labels[1]:return report['recommended_run'],Settings(**report['recommended_settings']),report
    return current,settings,report
