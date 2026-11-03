import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from engine import ROUTES,Settings,simulate
from experiments import compare_drill,milestone,paired_trials,run_trials,strategy_trials
from scene_export import scene_payload,usda_text
from spatial import load_layout,locate_on_plan,plan_figure,validate_layout,world_position

ROOT=Path(__file__).parent
PROFILE=json.loads((ROOT/'school_profile.json').read_text(encoding='utf-8'))


class BehaviorTests(unittest.TestCase):
    def test_person_heterogeneity_is_repeatable(self):
        settings=Settings(speed_cv=.2,class_reaction_spread=10)
        a,b=simulate(PROFILE,settings),simulate(PROFILE,settings)
        self.assertEqual(a,b)
        self.assertGreater(len({round(p['speed_factor'],5) for p in a['persons']}),100)
        self.assertEqual(a['metrics']['assembled'],111)

    def test_common_randomness_survives_route_change(self):
        settings=Settings(speed_cv=.2,class_reaction_spread=10)
        a=simulate(PROFILE,settings);b=simulate(PROFILE,replace(settings,closed_routes=('fire',)))
        for p,q in zip(a['persons'],b['persons']):
            self.assertEqual((p['id'],p['speed_factor'],p['ready_seconds']),(q['id'],q['speed_factor'],q['ready_seconds']))

    def test_group_mode_shares_start_route_and_pace(self):
        result=simulate(PROFILE,Settings(speed_cv=.2,class_reaction_spread=8,group_mode=True))
        for row in PROFILE['classes']:
            people=[p for p in result['persons'] if p['class_id']==row['id']]
            self.assertEqual(len({(p['route'],p['departure_at'],p['speed_factor']) for p in people}),1)
        self.assertEqual(result['metrics']['students'],111)

    def test_measured_edge_used_and_unknown_reported(self):
        result=simulate(PROFILE,Settings(edge_overrides=(('door_room_5A',4.,1.5),('not_active',3.,1.))))
        edge=result['network']['edges']['door_room_5A']
        self.assertEqual((edge['length'],edge['width']),(4.,1.5))
        self.assertIn('user-entered',edge['geometry_source'])
        self.assertEqual(result['network']['inactive_or_unknown_measurement_ids'],['not_active'])

    def test_bad_new_settings_rejected(self):
        for settings in [Settings(speed_cv=-1),Settings(group_mode='yes'),Settings(release_order=('5A','5A')),
            Settings(edge_overrides=(('x',2.,0.),)),Settings(release_order=('imaginary',))]:
            with self.subTest(settings=settings),self.assertRaises(ValueError):simulate(PROFILE,settings)


class ExperimentTests(unittest.TestCase):
    def test_equal_paired_conditions_produce_zero_difference(self):
        s=Settings(speed_cv=.2,class_reaction_spread=8)
        report=paired_trials(PROFILE,s,s,8)
        self.assertTrue(report['all_pairs_complete'])
        self.assertEqual(report['median_seconds_saved'],0)
        self.assertEqual(report['selected_faster_run_count'],0)

    def test_failed_runs_never_become_an_improvement(self):
        report=paired_trials(PROFILE,Settings(),Settings(closed_routes=ROUTES),4)
        self.assertEqual(report['selected']['complete_runs'],0)
        self.assertIsNone(report['selected']['median_seconds_completed_only'])
        self.assertIsNone(report['median_seconds_saved'])

    def test_partial_completion_is_reported(self):
        summary=run_trials(PROFILE,Settings(horizon_seconds=130,speed_cv=.2),8)
        self.assertEqual(summary['complete_runs']+summary['incomplete_runs'],8)
        self.assertGreater(summary['incomplete_runs'],0)

    def test_counts_and_context_rejected(self):
        for count in (1,201,True):
            with self.subTest(count=count),self.assertRaises(ValueError):run_trials(PROFILE,Settings(),count)
        with self.assertRaises(ValueError):paired_trials(PROFILE,Settings(),Settings(context='lunch'),3)

    def test_strategy_variants_use_same_seeds(self):
        report=strategy_trials(PROFILE,Settings(speed_cv=.15),3)
        self.assertEqual(len(report['variants']),4)
        self.assertEqual({tuple(row['seed'] for row in v['summary']['runs']) for v in report['variants']},{(42,43,44)})


class DrillTests(unittest.TestCase):
    def test_synthetic_milestones_have_zero_error_without_claiming_calibration(self):
        result=simulate(PROFILE)
        observations=[{'event':event,'seconds_after_shaking':milestone(result,event)} for event in ('first_move','last_exit','last_assembly')]
        report=compare_drill(result,observations)
        self.assertEqual(report['mae_seconds'],0)
        self.assertFalse(report['model_calibrated'])

    def test_missing_arrival_has_no_invented_error(self):
        report=compare_drill(simulate(PROFILE,Settings(gate_open=False)),[{'event':'last_assembly','seconds_after_shaking':150}])
        self.assertEqual(report['matched_count'],0);self.assertIsNone(report['mae_seconds'])

    def test_invalid_observations_rejected(self):
        result=simulate(PROFILE)
        cases=[[{'event':'last_exit','seconds_after_shaking':float('nan')}],
          [{'event':'last_exit','seconds_after_shaking':1},{'event':'last_exit','seconds_after_shaking':2}],
          [{'event':'first_move','seconds_after_shaking':30},{'event':'last_exit','seconds_after_shaking':20}],
          [{'event':'last_exit','class_id':'imaginary','seconds_after_shaking':10}]]
        for rows in cases:
            with self.subTest(rows=rows),self.assertRaises(ValueError):compare_drill(result,rows)


class SpatialTests(unittest.TestCase):
    def setUp(self):
        self.layout=json.loads((ROOT/'plan_layout.json').read_text(encoding='utf-8'))
        self.result=simulate(PROFILE)

    def test_all_proposed_mappings_remain_unconfirmed(self):
        validate_layout(self.layout,PROFILE)
        self.assertTrue(all(not row['user_confirmed'] for row in self.layout['class_mapping'].values()))

    def test_duplicate_room_and_wrong_floor_rejected(self):
        self.layout['class_mapping']['7A']['room_id']=self.layout['class_mapping']['5A']['room_id']
        with self.assertRaises(ValueError):validate_layout(self.layout,PROFILE)

    def test_plan_population_conserved_across_floors(self):
        for time in (0,50,100,self.result['metrics']['elapsed_seconds_from_onset']):
            locations=[locate_on_plan(self.result,self.layout,p,time) for p in self.result['persons']]
            self.assertEqual(len(locations),111)
            self.assertTrue(all(floor in self.layout['floors'] or floor=='SITE' for floor,_,_ in locations))

    def test_original_image_can_be_used_without_mutation(self):
        fig,count=plan_figure(self.result,self.layout,'2',0)
        self.assertEqual(count,10)
        self.assertTrue(fig.layout.images[0].source.startswith('data:image/jpeg;base64,'))
        # The photograph and student coordinates must share the image-pixel axes.
        # Plotly defaults to paper coordinates, which places this large image off-screen.
        self.assertEqual((fig.layout.images[0].xref,fig.layout.images[0].yref),('x','y'))

    def test_scene_identity_and_final_arrival(self):
        payload=scene_payload(self.result,self.layout,12)
        self.assertEqual(len(set(payload['student_ids'])),111)
        self.assertTrue(all(len(f['points'])==len(f['colors'])==111 for f in payload['frames']))
        self.assertEqual({world_position(self.result,self.layout,p,self.result['metrics']['elapsed_seconds_from_onset'])[1] for p in self.result['persons']},{'assembled'})
        text=usda_text(payload)
        self.assertTrue(text.startswith('#usda 1.0'))
        self.assertIn('upAxis = "Z"',text)
        self.assertIn('points.timeSamples',text)


class AdvancedUiTests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file(str(ROOT/'app.py'),default_timeout=45).run()

    def test_repeated_trial_button_and_stale_result(self):
        app=self.app()
        app.button(key='run_trials').click().run()
        self.assertFalse(app.exception)
        report=app.session_state['trials_report'][1]
        self.assertEqual(report['paired_complete_runs'],100)
        self.assertEqual(report['median_seconds_saved'],0)
        app.checkbox(key='route_fire').uncheck().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Ayarlar veya deneme' in info.value for info in app.info))

    def test_empty_drill_input_is_rejected(self):
        app=self.app();app.button(key='compare_drill').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('En az bir ölçüm' in error.value for error in app.error))

    def test_duplicate_room_form_is_rejected(self):
        app=self.app();app.selectbox(key='mapping_7A').select('room_5')
        next(button for button in app.button if button.label=='Oda eşleşmelerini kaydet').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('iki şubeye' in error.value for error in app.error))

    def test_export_button_preserves_111_identities(self):
        app=self.app();app.button(key='prepare_scene').click().run()
        self.assertFalse(app.exception)
        payload=app.session_state['scene_payload'][1]
        self.assertEqual(len(payload['student_ids']),111)


if __name__=='__main__':unittest.main()
