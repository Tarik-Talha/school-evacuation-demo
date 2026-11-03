"""Architectural placement, population and playback regressions."""
import json,math,unittest
from pathlib import Path
from engine import Settings,simulate
from building_geometry import building,inside,geometry_room
from spatial import load_layout,world_position,world_edge_points,interpolate
from school_scene import scene_html,scene_figure,student_frame,triangulate

ROOT=Path(__file__).parent
PROFILE=json.loads((ROOT/'school_profile.json').read_text(encoding='utf-8'))

class SceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.layout=load_layout();cls.result=simulate(PROFILE)

    def test_all_students_start_distinctly_inside_their_assigned_room(self):
        positions=[]
        for p in self.result['persons']:
            xyz,state=world_position(self.result,self.layout,p,0)
            self.assertEqual(state,'protecting')
            self.assertTrue(inside(xyz[:2],geometry_room(self.result,self.layout,p['origin'])['polygon']))
            self.assertEqual(xyz,world_position(self.result,self.layout,p,19)[0])
            positions.append(tuple(xyz))
        self.assertEqual(len(set(positions)),111)

    def test_lunch_seats_exclude_staircases(self):
        result=simulate(PROFILE,Settings(context='lunch'));points=[]
        for p in result['persons']:
            xyz,_=world_position(result,self.layout,p,0);points.append(tuple(xyz))
            self.assertEqual(p['floor'],'B1')
            for stair in building(self.layout)['floors']['B1']['stairs'].values():
                a,b,c,d=stair['bounds']
                self.assertFalse(a<xyz[0]<c and b<xyz[1]<d)
        self.assertEqual(len(set(points)),111)

    def test_lab_context_uses_the_destination_room(self):
        for floor in ('5','B2'):
            result=simulate(PROFILE,Settings(context='lab',lab_class='10A',lab_floor=floor))
            for p in result['persons']:
                if p['class_id']!='10A':continue
                xyz,_=world_position(result,self.layout,p,0)
                self.assertTrue(inside(xyz[:2],building(self.layout)['floors'][floor]['rooms']['lab_5' if floor=='5' else 'lab_B2']['polygon']))

    def test_cutaway_never_changes_whole_school_counters(self):
        for t in (0,20,60,self.result['metrics']['elapsed_seconds_from_onset']):
            frame=student_frame(self.result,self.layout,t,['3'],False)
            self.assertEqual(sum(frame['counts'].values()),111)
        frame=student_frame(self.result,self.layout,0,['3'],False)
        self.assertEqual(frame['visible'],44);self.assertEqual(frame['counts']['rooms'],111)
        all_floors=list(building(self.layout)['floors'])
        last=student_frame(self.result,self.layout,self.result['metrics']['elapsed_seconds_from_onset'],all_floors,False)
        self.assertEqual(last['counts']['field'],111);self.assertEqual(last['visible'],111)

    def test_concave_floor_mesh_preserves_plan_area(self):
        for floor in building(self.layout)['floors'].values():
            poly=floor['outline']
            area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2
            mesh_area=0
            for a,b,c in triangulate(poly):
                p,q,r=poly[a],poly[b],poly[c]
                mesh_area+=abs((q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]))/2
            self.assertAlmostEqual(area,mesh_area)

    def test_outdoor_visual_routes_stay_outside_the_building(self):
        outline=building(self.layout)['floors']['G']['outline']
        for edge in self.result['network']['edges'].values():
            if not edge['id'].startswith('outside_'):continue
            path=world_edge_points(self.result,self.layout,edge)
            for i in range(41):self.assertFalse(inside(interpolate(path,i/40)[:2],outline))

    def test_offline_player_and_all_views_can_be_created(self):
        for mode in ('floor','building','separated'):
            figure,body,heads,floors,separated=scene_figure(self.result,self.layout,mode=mode)
            self.assertEqual(figure.data[heads].type,'scatter3d')
            self.assertTrue(any(t.type=='mesh3d' for t in figure.data))
        text=scene_html(self.result,self.layout)
        self.assertNotIn('<script src=',text)
        self.assertIn('3B animasyon zamanı',text)
        self.assertIn('scrollZoom',text)

class SceneUiTests(unittest.TestCase):
    def test_three_d_is_the_primary_view_and_floor_controls_work(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=45).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.tabs[0].label,'3B okul')
        self.assertEqual(app.selectbox(key='scene_floor_lesson').value,'3')
        app.radio(key='scene_mode').set_value('Okulun tamamı').run()
        self.assertFalse(app.exception)
        app.radio(key='scene_mode').set_value('Katları ayır').run()
        self.assertFalse(app.exception)

if __name__=='__main__':unittest.main()
