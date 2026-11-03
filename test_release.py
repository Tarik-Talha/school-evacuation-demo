"""Release regressions for portable assets, recess and independent visitors."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from engine import Settings, ROUTES, simulate
from recess import placement_groups, is_walkable
from scene_export import scene_payload, usda_text
from school_scene import student_frame
from source_assets import source_plan
from spatial import load_layout
from state_store import read_json, write_json

ROOT = Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / 'school_profile.json').read_text(encoding='utf-8'))


class PortableAssetTests(unittest.TestCase):
    def test_every_source_image_is_bundled_and_hash_verified(self):
        manifest = json.loads((ROOT / 'source_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['images']), 11)
        for entry in manifest['images']:
            with self.subTest(plan=entry['id']):
                path = source_plan(entry['file'], entry['sha256'])
                self.assertTrue(path.is_relative_to(ROOT))

    def test_external_paths_and_changed_images_are_rejected(self):
        for path in ['../../outside.jpeg', str(ROOT / 'app.py'), 'assets/plans/missing.jpeg']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                source_plan(path)
        with self.assertRaises(ValueError):
            source_plan('assets/plans/P01.jpeg', '0' * 64)


class RecessReleaseTests(unittest.TestCase):
    def test_pairs_and_trios_preserve_every_student_at_walkable_positions(self):
        expected = {f"{row['id']}_{i+1:02d}" for row in PROFILE['classes'] for i in range(row['students'])}
        for seed in [0, 1, 42, 197, 10000]:
            with self.subTest(seed=seed):
                groups = placement_groups(PROFILE, seed)
                members = [member for group in groups for member in group['members']]
                self.assertEqual(len(members), 111)
                self.assertEqual({member['id'] for member in members}, expected)
                self.assertTrue(all(group['students'] in (2, 3) for group in groups))
                for group in groups:
                    for member in group['members']:
                        self.assertEqual(member['class_id'], group['class_id'])
                        point = member['point'] + [group['room_id']] if group['origin_kind'] == 'room' else member['point']
                        self.assertTrue(is_walkable(group['floor'], point, group['origin_kind']))

    def test_recess_placement_is_repeatable_and_independent_of_strategy(self):
        settings = Settings(context='recess', placement_seed=197)
        a = simulate(PROFILE, settings)
        b = simulate(PROFILE, replace(settings, policy='shortest', seed=87, closed_routes=('fire',)))
        self.assertEqual(a['network']['placement_fingerprint'], b['network']['placement_fingerprint'])
        def initial(result):
            return {p['id']: (p['floor'], p['origin'], p['initial_point']) for p in result['persons']}
        self.assertEqual(initial(a), initial(b))
        self.assertEqual(a, simulate(PROFILE, settings))
        self.assertNotEqual(a['network']['placement_fingerprint'], simulate(PROFILE, replace(settings, placement_seed=198))['network']['placement_fingerprint'])

    def test_closed_stairs_do_not_teleport_indoor_students_outside(self):
        result = simulate(PROFILE, Settings(context='recess', closed_routes=ROUTES))
        inside = [p for p in result['persons'] if p['origin_kind'] != 'yard']
        yard = [p for p in result['persons'] if p['origin_kind'] == 'yard']
        self.assertTrue(inside and yard)
        self.assertTrue(all(p['status'] == 'unreachable' and p['arrived_at'] is None for p in inside))
        self.assertTrue(all(p['status'] == 'assembled' for p in yard))
        self.assertEqual(result['metrics']['unresolved'], len(inside))
        self.assertIsNone(result['metrics']['assembly_seconds_after_shaking'])

    def test_all_contexts_keep_population_in_scene_and_export(self):
        layout = load_layout()
        for context in ['lesson', 'lunch', 'lab', 'recess']:
            with self.subTest(context=context):
                result = simulate(PROFILE, Settings(context=context))
                self.assertEqual(result['metrics']['students'], 111)
                self.assertEqual(result['metrics']['assembled'], 111)
                payload = scene_payload(result, layout, 8)
                self.assertEqual(len(set(payload['student_ids'])), 111)
                self.assertTrue(all(len(frame['points']) == 111 for frame in payload['frames']))
                self.assertIn('points.timeSamples', usda_text(payload))
                for timestamp in [0, 20, result['metrics']['elapsed_seconds_from_onset']]:
                    frame = student_frame(result, layout, timestamp, list(layout['floors']), False)
                    self.assertEqual(sum(frame['counts'].values()), 111)


class SessionIsolationTests(unittest.TestCase):
    def test_browser_edits_never_change_another_visitor_or_shared_disk(self):
        visitor_a, visitor_b = {}, {}
        baseline = {'marker': ['default']}
        with patch('state_store.session_state', return_value=visitor_a):
            write_json('user_layout.json', {'marker': ['visitor A']})
            first = read_json('user_layout.json', baseline)
            first['marker'].append('unsaved edit')
            self.assertEqual(read_json('user_layout.json')['marker'], ['visitor A'])
        with patch('state_store.session_state', return_value=visitor_b):
            self.assertEqual(read_json('user_layout.json', baseline), baseline)
            write_json('user_layout.json', {'marker': ['visitor B']})
        with patch('state_store.session_state', return_value=visitor_a):
            self.assertEqual(read_json('user_layout.json')['marker'], ['visitor A'])

    def test_non_finite_measurements_cannot_be_saved(self):
        with patch('state_store.session_state', return_value={}):
            with self.assertRaises(ValueError):
                write_json('measurements_lesson.json', {'length': float('nan')})


class ReleaseUiTests(unittest.TestCase):
    def test_all_four_contexts_open_without_errors_and_new_recess_draw_works(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=40).run()
        labels = ['Ders sırasında', 'Öğle yemeği · 111 öğrenci B1\'de', 'Örnek laboratuvar dersi', 'Teneffüs · 2–3 kişilik arkadaş grupları']
        for label in labels:
            with self.subTest(label=label):
                app.selectbox(key='context').select(label).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertEqual(app.metric[0].value, '111 / 111')
        before = app.number_input(key='recess_placement_seed').value
        app.button(key='new_recess_placement').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(app.number_input(key='recess_placement_seed').value, before + 1)


if __name__ == '__main__':
    unittest.main()
