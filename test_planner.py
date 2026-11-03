"""Constraint preservation, held-out rejection and current/proposed UI integration."""
import copy,json,unittest
from dataclasses import asdict,replace
from pathlib import Path
from unittest.mock import patch
from engine import Settings,ROUTES,simulate
from planner import SearchConfig,objective_score,recommend_plan

ROOT=Path(__file__).parent
PROFILE=json.loads((ROOT/'school_profile.json').read_text(encoding='utf-8'))
SMALL=SearchConfig(budget=6,search_runs=2,validation_runs=5)

class PlanEngineTests(unittest.TestCase):
    def test_forced_class_route_and_delay_preserve_other_behavior(self):
        s=Settings(group_mode=True,speed_cv=.15)
        base=simulate(PROFILE,s)
        changed=simulate(PROFILE,replace(s,class_routes=(('5A','right'),),class_delays=(('5A',3.),)))
        self.assertEqual(changed['metrics']['assembled'],111)
        for a,b in zip(base['persons'],changed['persons']):
            self.assertEqual(a['id'],b['id']);self.assertEqual(a['speed_factor'],b['speed_factor'])
            self.assertAlmostEqual(b['ready_seconds']-a['ready_seconds'],3 if a['class_id']=='5A' else 0)
            if b['class_id']=='5A':self.assertEqual(b['route'],'right')
            self.assertGreaterEqual(b['departure_at'],s.shaking_seconds)

    def test_invalid_explicit_plans_are_rejected(self):
        bad=[Settings(class_routes=(('missing','left'),)),Settings(class_routes=(('5A','invalid'),)),
             Settings(class_routes=(('5A','fire'),),closed_routes=('fire',)),
             Settings(class_routes=(('5A','fire'),),context='lunch'),
             Settings(class_delays=(('5A',-1),)),Settings(class_delays=(('5A',float('nan')),)),
             Settings(class_routes=(('5A','left'),('5A','right')))]
        for s in bad:
            with self.subTest(s=s),self.assertRaises(ValueError):simulate(PROFILE,s)

class PlannerTests(unittest.TestCase):
    def test_search_preserves_inputs_and_uses_disjoint_control_runs(self):
        s=Settings(group_mode=True,closed_routes=('fire',),shaking_seconds=35,stair_width=.9,speed_cv=.15)
        original=asdict(s);report=recommend_plan(PROFILE,s,SMALL)
        self.assertLessEqual(report['candidate_count'],SMALL.budget)
        self.assertTrue(set(report['search_seeds']).isdisjoint(report['holdout_seeds']))
        for row in report['training']:
            for name,value in original.items():
                if name not in ('class_routes','class_delays'):self.assertEqual(row['settings'][name],value)
            self.assertTrue(all(route!='fire' for _,route in row['settings']['class_routes']))
        self.assertEqual(asdict(s),original)
        self.assertEqual(report['recommended_run']['metrics']['students'],111)

    def test_closed_gate_and_all_closed_routes_produce_no_plan(self):
        for s in (Settings(gate_open=False),Settings(closed_routes=ROUTES)):
            report=recommend_plan(PROFILE,s,SMALL)
            self.assertEqual(report['status'],'infeasible');self.assertIsNone(report['recommended_settings'])
            self.assertEqual(report['candidate_count'],0)

    def test_lunch_does_not_invent_a_fire_stair_connection(self):
        report=recommend_plan(PROFILE,Settings(context='lunch',closed_routes=('left','right')),SMALL)
        self.assertEqual(report['status'],'infeasible');self.assertEqual(len(report['unreachable_classes']),10)
        report=recommend_plan(PROFILE,Settings(context='lunch',group_mode=True),SMALL)
        for row in report['training']:
            self.assertTrue(all(route!='fire' for _,route in row['settings']['class_routes']))

    def test_single_route_keeps_current_plan_without_inventing_a_gain(self):
        report=recommend_plan(PROFILE,Settings(group_mode=True,closed_routes=('right','fire')),SMALL)
        self.assertEqual(report['status'],'current_retained')
        self.assertEqual(report['displayed_paired']['median_seconds_saved'],0)
        self.assertEqual(report['recommended_id'],'current')

    def test_failed_control_runs_reject_a_fast_training_winner(self):
        real_simulate=simulate
        def overfit(profile,settings):
            result=real_simulate(profile,settings)
            if settings.class_routes:
                if settings.seed<10000:result['metrics']['assembly_seconds_after_shaking']=1.
                else:
                    result['metrics'].update(unresolved=1,assembled=110,assembly_seconds_after_shaking=None)
                    result['persons'][0]['arrived_at']=None
            return result
        with patch('planner.simulate',side_effect=overfit):report=recommend_plan(PROFILE,Settings(group_mode=True),SMALL)
        self.assertNotEqual(report['training_winner_id'],'current')
        self.assertFalse(report['validation']['candidate_accepted'])
        self.assertEqual(report['recommended_id'],'current')

    def test_timeout_runs_are_not_ranked_as_fast_successes(self):
        report=recommend_plan(PROFILE,Settings(horizon_seconds=1),SMALL)
        self.assertEqual(report['status'],'no_complete_candidate')
        self.assertIsNone(report['recommended_settings'])
        self.assertTrue(all(r['score'] is None for r in report['training']))

    def test_shaking_duration_shifts_the_clock_without_changing_route_quality(self):
        a=recommend_plan(PROFILE,Settings(group_mode=True,speed_cv=.15,shaking_seconds=20),SMALL)
        b=recommend_plan(PROFILE,Settings(group_mode=True,speed_cv=.15,shaking_seconds=50),SMALL)
        self.assertEqual(a['recommended_id'],b['recommended_id'])
        self.assertAlmostEqual(a['recommended_summary']['median_seconds'],b['recommended_summary']['median_seconds'])
        self.assertAlmostEqual(b['recommended_run']['metrics']['elapsed_seconds_from_onset']-a['recommended_run']['metrics']['elapsed_seconds_from_onset'],30)

    def test_locked_routes_and_delay_bounds_are_respected(self):
        s=Settings(group_mode=True,class_routes=(('5A','right'),))
        report=recommend_plan(PROFILE,s,replace(SMALL,budget=16,max_extra_delay=2))
        self.assertTrue(any(row['settings']['class_delays'] for row in report['training']))
        for row in report['training']:
            self.assertEqual(dict(row['settings']['class_routes']).get('5A'),'right')
            self.assertTrue(all(0<=value<=2 for _,value in row['settings']['class_delays']))

    def test_objective_exposes_time_waiting_tradeoff(self):
        base={'incomplete_runs':0,'p95_seconds':100.,'mean_wait_seconds':10.,'mean_peak_queue':20.,'horizon_seconds':900}
        faster={**base,'p95_seconds':80.,'mean_wait_seconds':20.}
        self.assertLess(objective_score(faster,base,'time'),1)
        self.assertGreater(objective_score(faster,base,'waiting'),1)

    def test_invalid_search_sizes_rejected_before_search(self):
        for config in (SearchConfig(budget=1000),SearchConfig(search_runs=True),SearchConfig(max_extra_delay=-1),SearchConfig(objective='safest')):
            with self.subTest(config=config),self.assertRaises(ValueError):recommend_plan(PROFILE,Settings(),config)

class PlannerUiTests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()

    def test_search_and_changed_inputs_do_not_apply_stale_plans(self):
        app=self.app();app.selectbox(key='planner_effort').select('Hızlı')
        app.button(key='recommend_plan').click().run()
        self.assertFalse(app.exception)
        self.assertLessEqual(app.session_state['planner_report'][1]['candidate_count'],24)
        app.checkbox(key='route_fire').uncheck().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Önceki öneri' in item.value for item in app.info))
        app.button(key='prepare_scene').click().run()
        exported=app.session_state['scene_payload'][1]['settings']
        self.assertIn('fire',exported['closed_routes']);self.assertEqual(exported['class_routes'],())

    def test_blocked_inputs_show_no_recommended_plan(self):
        app=self.app()
        for route in ROUTES:app.checkbox(key='route_'+route).uncheck()
        app.button(key='recommend_plan').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['planner_report'][1]['status'],'infeasible')
        self.assertTrue(any('plan önerilemedi' in item.value for item in app.error))

    def test_selected_plan_is_the_one_exported_to_the_three_d_scene(self):
        app=self.app();app.selectbox(key='planner_effort').select('Hızlı')
        app.button(key='recommend_plan').click().run()
        signature,report=app.session_state['planner_report']
        app.radio(key='planner_view_'+signature[:12]).set_value('Modelin seçtiği düzen').run()
        app.button(key='prepare_scene').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(json.dumps(app.session_state['scene_payload'][1]['settings'],sort_keys=True),json.dumps(report['recommended_settings'],sort_keys=True))

if __name__=='__main__':unittest.main()
