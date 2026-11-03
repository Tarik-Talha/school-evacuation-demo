"""Bounded scenario optimizer. Produces model drafts, never an approved emergency plan."""
from collections import Counter
from dataclasses import asdict,dataclass,replace
import hashlib,json,math,random,statistics

from engine import Settings,ROUTES,ROUTE_LABELS,build_network,candidate_path,simulate,unit_id
from experiments import quantile,placement_fingerprint

@dataclass(frozen=True)
class SearchConfig:
    budget:int=48
    search_runs:int=4
    validation_runs:int=20
    max_extra_delay:float=0.
    objective:str='balanced'
    minimum_gain:float=.02

    def validate(self):
        for value,low,high in ((self.budget,2,96),(self.search_runs,2,12),(self.validation_runs,5,50)):
            if type(value) is not int or not low<=value<=high:raise ValueError('Arama boyutu sınır dışında.')
        if self.objective not in WEIGHTS:raise ValueError('Bilinmeyen planlama hedefi.')
        for value,limit in ((self.max_extra_delay,15),(self.minimum_gain,.2)):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=limit:
                raise ValueError('Geçersiz arama sınırı.')

WEIGHTS={'balanced':(.6,.25,.15),'time':(.85,.1,.05),'waiting':(.3,.5,.2)}
OBJECTIVES={'balanced':'Süre ve beklemeyi dengele','time':'Saha varış süresini azalt','waiting':'Beklemeyi azalt'}

def fingerprint(profile,settings,config):
    from pathlib import Path
    root=Path(__file__).parent
    code=b''.join((root/name).read_bytes() for name in ('engine.py','planner.py','recess.py','building_geometry.json'))
    return hashlib.sha256(code+json.dumps([profile,asdict(settings),asdict(config)],sort_keys=True).encode()).hexdigest()

def _summary(rows,horizon):
    times=[r['assembly_seconds_after_shaking'] for r in rows if r['unresolved']==0]
    return {'runs':rows,'requested_runs':len(rows),'complete_runs':len(times),'incomplete_runs':len(rows)-len(times),
        'median_seconds':quantile(times,.5),'p05_seconds':quantile(times,.05),'p95_seconds':quantile(times,.95),
        'mean_wait_seconds':statistics.mean(r['mean_wait_seconds'] for r in rows),
        'p95_max_wait_seconds':quantile([r['max_wait_seconds'] for r in rows],.95),
        'mean_peak_queue':statistics.mean(r['peak_queue'] for r in rows),
        'max_peak_queue':max(r['peak_queue'] for r in rows),'max_unresolved':max(r['unresolved'] for r in rows),
        'horizon_seconds':horizon}

def objective_score(summary,reference,objective):
    if summary['incomplete_runs']:return None
    values=(summary['p95_seconds'],summary['mean_wait_seconds'],summary['mean_peak_queue'])
    base=(reference['p95_seconds'] or reference['horizon_seconds'],reference['mean_wait_seconds'],reference['mean_peak_queue'])
    # Offsets make the unchanged baseline exactly 1 even for zero waiting.
    return round(sum(weight*(value+1)/(before+1) for weight,value,before in zip(WEIGHTS[objective],values,base)),10)

def _plan_id(routes,extra):
    return 'plan_'+hashlib.sha256(json.dumps([routes,extra],sort_keys=True).encode()).hexdigest()[:10]

def _paired(reference,candidate,objective):
    if reference['incomplete_runs'] or candidate['incomplete_runs']:
        return {'median_seconds_saved':None,'p05_seconds_saved':None,'p95_seconds_saved':None,
                'median_percent_saved':None,'faster_runs':None,'objective_better_runs':None}
    changes=[a['assembly_seconds_after_shaking']-b['assembly_seconds_after_shaking'] for a,b in zip(reference['runs'],candidate['runs'])]
    percentages=[100*d/a['assembly_seconds_after_shaking'] if a['assembly_seconds_after_shaking'] else 0
                 for a,d in zip(reference['runs'],changes)]
    wins=0
    for a,b in zip(reference['runs'],candidate['runs']):
        if objective_score(_summary([b],candidate['horizon_seconds']),_summary([a],reference['horizon_seconds']),objective)<1-1e-8:wins+=1
    return {'median_seconds_saved':quantile(changes,.5),'p05_seconds_saved':quantile(changes,.05),
            'p95_seconds_saved':quantile(changes,.95),'median_percent_saved':quantile(percentages,.5),
            'faster_runs':sum(d>1e-8 for d in changes),'objective_better_runs':wins}

def plan_rows(result,settings):
    rows=[];extra=dict(settings.class_delays)
    for group in result['network']['groups']:
        key=unit_id(group)
        people=[p for p in result['persons'] if unit_id(p)==key]
        counts=Counter(p['route'] for p in people)
        label=' · '.join((('Bahçeden saha' if route=='yard' else ROUTE_LABELS.get(route,'Bağlantı yok'))+f' ({count})') for route,count in counts.items())
        rows.append({'class_id':group['class_id'],'unit_id':key,'group_id':group.get('group_id'),
          'class_ids':sorted({p['class_id'] for p in people}),'area_label':group.get('area_label'),
          'students':len(people),'floor':group['floor'],
          'route':next(iter(counts)) if len(counts)==1 else 'mixed','route_label':label,
          'additional_delay_seconds':extra.get(key,0.),
          'assembled':sum(p['arrived_at'] is not None for p in people)})
    return rows

# =========================================================
# BOUNDED CLASS-ROUTE SEARCH WITH HELD-OUT RANDOM SEEDS
# =========================================================
def recommend_plan(profile,settings,config=SearchConfig(),progress=None):
    settings.validate();config.validate()
    if settings.seed+10000+config.validation_runs>=2**32:raise ValueError('Doğrulama için koşu numarası aralığı kalmadı.')
    network=build_network(profile,settings);groups=network['groups'];units=[unit_id(g) for g in groups]
    fixed=dict(settings.class_routes);minimum_delay=dict(settings.class_delays)
    allowed={unit_id(g):[route for route in (('yard',) if g.get('origin_kind')=='yard' else ROUTES)
                        if candidate_path(network,g,route,settings) is not None
                        and (unit_id(g) not in fixed or fixed[unit_id(g)]==route)] for g in groups}
    signature=fingerprint(profile,settings,config)
    report={'schema_version':1,'status':'searching','fingerprint':signature,'config':asdict(config),
      'objective_label':OBJECTIVES[config.objective],'baseline_settings':asdict(settings),
      'recommended_settings':None,'recommended_id':None,'baseline_run':None,'recommended_run':None,
      'training':[],'validation':None,'candidate_count':0,'school_approval':'not_approved_model_draft',
      'planning_unit':'friend_group' if settings.context=='recess' else 'class',
      'placement_seed':settings.placement_seed if settings.context=='recess' else None,
      'placement_fingerprint':None,'placement_verified_runs':0,
      'scope':f"{sum(g['students'] for g in groups)}-student model; not a live emergency controller",
      'interpretation':'Finite search, not a global optimum. Holdout variability is not real-world confidence.',
      'sources':{'validation':'https://www.nist.gov/publications/process-verification-and-validation-building-fire-evacuation-models',
                 'earthquake':'https://afad.gov.tr/deprem-oncesi-ani-ve-sonrasi-alabileceginiz-onlemleri-biliyor-musunuz'}}
    if not settings.gate_open or any(not routes for routes in allowed.values()):
        report.update(status='infeasible',reason='Saha geçişi kapalı.' if not settings.gate_open else
                      ('Bazı arkadaş grupları için açık ve bağlı güzergâh yok.' if settings.context=='recess' else 'Bazı şubeler için açık ve bağlı güzergâh yok.'),
                      unreachable_classes=[c for c,routes in allowed.items() if not routes],
                      unreachable_units=[c for c,routes in allowed.items() if not routes])
        return report
    baseline_run=simulate(profile,settings);report['baseline_run']=baseline_run
    expected_placement=placement_fingerprint(baseline_run)
    report['placement_fingerprint']=expected_placement
    report['placement_verified_runs']=1 if expected_placement is not None else 0
    train_seeds=[settings.seed+i for i in range(config.search_runs)]
    holdout_seeds=[settings.seed+10000+i for i in range(config.validation_runs)]
    report['search_seeds']=train_seeds;report['holdout_seeds']=holdout_seeds
    completed=0;maximum=config.budget*config.search_runs+2*config.validation_runs
    def evaluate(parameters,seeds,stage):
        nonlocal completed
        rows=[]
        for seed in seeds:
            result=simulate(profile,replace(parameters,seed=seed))
            placement=placement_fingerprint(result)
            if settings.context=='recess':
                if placement!=expected_placement:
                    raise ValueError('Plan karşılaştırmasında teneffüs yerleşimi değişti; arama durduruldu.')
                report['placement_verified_runs']+=1
            peak=max((q['peak_queue'] for q in result['queues']),default=0)
            rows.append({'seed':seed,**result['metrics'],'peak_queue':peak,'placement_fingerprint':placement})
            completed+=1
            if progress:progress(min(.99,completed/maximum),stage)
        return _summary(rows,parameters.horizon_seconds)
    baseline_summary=evaluate(settings,train_seeds,'Mevcut düzen değerlendiriliyor')
    evaluated=[{'id':'current','settings':asdict(settings),'summary':baseline_summary,
                'score':objective_score(baseline_summary,baseline_summary,config.objective)}]
    parameter_sets={'current':settings}
    route_map={c:Counter(p['route'] for p in baseline_run['persons'] if unit_id(p)==c).most_common(1)[0][0] for c in units}
    seen=set()
    if settings.group_mode or all(len({p['route'] for p in baseline_run['persons'] if unit_id(p)==c})==1 for c in units):
        seen.add(_plan_id(route_map,{}))
    pending=[]
    def propose(routes,extra=None):
        extra={key:float(value) for key,value in (extra or {}).items() if value>0}
        identity=_plan_id(routes,extra)
        if identity in seen:return
        if any(routes[c] not in allowed[c] for c in units):return
        if any(value>config.max_extra_delay or minimum_delay.get(key,0)+value>60 for key,value in extra.items()):return
        seen.add(identity);pending.append((identity,dict(routes),extra))
    orders=[groups,sorted(groups,key=lambda g:-g['students']),sorted(groups,key=lambda g:-float(g['floor']) if g['floor'].isdigit() else 0),list(reversed(groups))]
    for order in orders:
        loads=Counter();routes={}
        for g in order:
            def cost(route):
                path=candidate_path(network,g,route,settings)
                speed=lambda key:settings.stair_speed if network['edges'][key]['kind']=='stair' else settings.walking_speed
                travel=sum(network['edges'][key]['length']/speed(key) for key in path)
                headways=[1/(network['edges'][key]['width']*(settings.stair_flow_per_m if network['edges'][key]['kind']=='stair' else settings.flow_per_m))
                          for key in path if key.startswith(('stair_','exit_'))]
                if not headways:
                    headways=[1/(network['edges'][key]['width']*settings.flow_per_m) for key in path]
                capacity=max(headways,default=0.)
                return travel+(loads[route]+g['students']/2)*capacity
            route=min(allowed[unit_id(g)],key=cost);routes[unit_id(g)]=route;loads[route]+=g['students']
        propose(routes)
    for offset in range(3):
        propose({c:allowed[c][(i+offset)%len(allowed[c])] for i,c in enumerate(units)})
    for route in ROUTES:
        propose({c:route if route in allowed[c] else allowed[c][0] for c in units})
    propose(route_map)
    if config.max_extra_delay:
        propose(route_map,{c:config.max_extra_delay*(i%3)/2 for i,c in enumerate(units)})
        propose(route_map,{c:config.max_extra_delay*((len(units)-i-1)%3)/2 for i,c in enumerate(units)})
    rng=random.Random(settings.seed^0x5A17)
    attempts=0
    while len(evaluated)<config.budget and attempts<config.budget*100:
        attempts+=1
        if not pending:
            ranked=sorted((r for r in evaluated if r['score'] is not None),key=lambda r:(r['score'],r['id']))[:4]
            if ranked and rng.random()<.75:
                parent=parameter_sets[rng.choice(ranked)['id']]
                routes={**route_map,**dict(parent.class_routes)}
                extra={c:max(0,dict(parent.class_delays).get(c,0)-minimum_delay.get(c,0)) for c in units}
                for _ in range(1 if rng.random()<.75 else 2):
                    c=rng.choice(units);routes[c]=rng.choice(allowed[c])
                if config.max_extra_delay and rng.random()<.45:
                    c=rng.choice(units);extra[c]=rng.choice([0,config.max_extra_delay/2,config.max_extra_delay])
            else:
                routes={c:rng.choice(allowed[c]) for c in units};extra={}
            propose(routes,extra)
            if not pending:continue
        identity,routes,extra=pending.pop(0)
        delays={c:minimum_delay.get(c,0)+extra.get(c,0) for c in units}
        parameters=replace(settings,class_routes=tuple((c,routes[c]) for c in units),
                            class_delays=tuple((c,delays[c]) for c in units if delays[c]>0))
        summary=evaluate(parameters,train_seeds,f'{len(evaluated)+1}. model seçeneği deneniyor')
        row={'id':identity,'settings':asdict(parameters),'summary':summary,'score':objective_score(summary,baseline_summary,config.objective)}
        evaluated.append(row);parameter_sets[identity]=parameters
    report['training']=evaluated;report['candidate_count']=len(evaluated)
    complete=[row for row in evaluated if row['score'] is not None]
    if not complete:
        report.update(status='no_complete_candidate',reason='Taranan seçeneklerin tüm denemelerini tamamlayan bir düzen yok.')
        if progress:progress(1.,'Arama tamamlandı')
        return report
    winner=min(complete,key=lambda row:(row['score'],0 if row['id']=='current' else 1,row['id']))
    report['training_winner_id']=winner['id']
    held_reference=evaluate(settings,holdout_seeds,'Aramada kullanılmayan denemelerle mevcut düzen kontrol ediliyor')
    held_candidate=held_reference if winner['id']=='current' else evaluate(parameter_sets[winner['id']],holdout_seeds,'Seçilen taslak bağımsız koşu numaralarıyla kontrol ediliyor')
    score=objective_score(held_candidate,held_reference,config.objective)
    paired=_paired(held_reference,held_candidate,config.objective)
    gain=(1-score)*100 if score is not None and not held_reference['incomplete_runs'] else None
    accepted=not held_candidate['incomplete_runs'] and winner['id']!='current' and (
        held_reference['incomplete_runs']>0 or (gain is not None and gain>=config.minimum_gain*100
          and paired['objective_better_runs']>=math.ceil(.6*config.validation_runs)))
    if accepted:
        selected_id=winner['id'];status='recommended'
        reason='Seçilen taslak, aramada kullanılmayan denemelerde de hedefe göre yeterli kazanım gösterdi.'
    elif not held_reference['incomplete_runs']:
        selected_id='current';status='current_retained'
        reason=('Taranan seçeneklerde mevcut düzenden daha iyi bir aday bulunmadı; kontrol koşularında mevcut düzen korundu.' if winner['id']=='current'
                else 'Bağımsız denemelerde yeterli ve tutarlı kazanım doğrulanmadı; mevcut düzen korundu.')
    else:
        selected_id=None;status='no_validated_candidate';reason='Kontrol denemelerinin tamamını geçen bir plan bulunamadı.'
    report.update(status=status,reason=reason,recommended_id=selected_id,
       validation={'reference':held_reference,'candidate':held_candidate,'candidate_id':winner['id'],
                   'candidate_accepted':bool(accepted),'objective_gain_percent':gain,'paired':paired})
    if selected_id is not None:
        chosen=parameter_sets[selected_id];sample=baseline_run if selected_id=='current' else simulate(profile,chosen)
        if settings.context=='recess' and placement_fingerprint(sample)!=expected_placement:
            raise ValueError('Gösterilecek planın teneffüs yerleşimi başlangıçla eşleşmiyor.')
        report.update(recommended_settings=asdict(chosen),recommended_run=sample,class_plan=plan_rows(sample,chosen),
            recommended_summary=held_candidate if accepted else held_reference,
            displayed_paired=paired if accepted else _paired(held_reference,held_reference,config.objective))
    if progress:progress(1.,'Plan karşılaştırması tamamlandı')
    # Reject accidental NaN/Infinity before a report reaches the UI or a download.
    json.dumps(report,allow_nan=False)
    return report
