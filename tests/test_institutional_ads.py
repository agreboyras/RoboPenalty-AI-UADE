"""Visual-only tests; require the installed MuJoCo execution packages."""
import sys
from pathlib import Path
import math
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/RoboPenalty'))
import mujoco
import numpy as np
from phase7d.institutional_ads import advertisements, PREFIX, MAX_GEOMS
from phase7d.visual_scene import StadiumScene
from phase7c.integrity import model_signature
from phase7c.scoreboard import FONT


class InstitutionalAdsTests(unittest.TestCase):
    def model(self):
        return mujoco.MjModel.from_xml_string('''<mujoco><asset>
          <texture type="skybox" builtin="gradient" width="512" height="3072"/>
          <texture name="groundplane" type="2d" builtin="checker" width="32" height="32"/>
          <material name="groundplane" texture="groundplane"/></asset>
          <worldbody><geom type="plane" size="20 20 .1"/></worldbody></mujoco>''')

    def test_bounded_perimeter_without_official_assets_or_pitch_overlap(self):
        items=advertisements()
        self.assertLessEqual(len(items),MAX_GEOMS)
        self.assertEqual(len(items),len({p.name for p in items}))
        self.assertEqual(sum(p.name.endswith('_frame') for p in items),8)
        for p in items:
            dx=abs(math.cos(p.yaw))*p.size[0]+abs(math.sin(p.yaw))*p.size[1]
            dy=abs(math.sin(p.yaw))*p.size[0]+abs(math.cos(p.yaw))*p.size[1]
            x,y,_=p.position
            self.assertTrue(x-dx>5 or x+dx<-15 or y-dy>12 or y+dy<-12,p.name)
            self.assertTrue(p.name.startswith(PREFIX))

    def test_rear_boards_have_two_readable_faces_and_no_prototype_caption(self):
        items=advertisements()
        self.assertFalse(any('caption' in p.name for p in items))
        for i in range(2):
            prefix=f'{PREFIX}rear_{i}'
            self.assertTrue(any(p.name.startswith(prefix+'_text_-1') for p in items))
            self.assertTrue(any(p.name.startswith(prefix+'_text_1') for p in items))
            self.assertLess(max(p.position[2]+p.size[2] for p in items if p.name.startswith(prefix)),1.)

    def test_does_not_modify_historical_font(self):
        self.assertNotIn('U',FONT)
        self.assertNotIn('D',FONT)
        self.assertEqual(advertisements(),advertisements())

    def test_static_boards_survive_five_score_updates(self):
        m=self.model();s=StadiumScene(m)
        expected=[p for p in s.primitives if p.name.startswith(PREFIX)]
        for penalty in range(1,6):
            s.update_status(dict(penalty=penalty,total=5,goals=penalty//2,saves=penalty-penalty//2))
            self.assertEqual(expected,[p for p in s.primitives if p.name.startswith(PREFIX)])
        self.assertTrue(expected)

    def test_toggle_keeps_original_stadium_and_scoreboard(self):
        m=self.model();on=StadiumScene(m);off=StadiumScene(m,institutional_ads=False)
        self.assertEqual([p for p in on.primitives if not p.name.startswith(PREFIX)],off.primitives)
        self.assertFalse(StadiumScene(m,'none').institutional_ads)
        self.assertTrue(StadiumScene(m,'low').institutional_ads)

    def test_low_detail_simplifies_stands_and_net_and_keeps_score_and_ads(self):
        model = self.model()
        full = StadiumScene(model)
        low = StadiumScene(model, 'low')
        status = dict(penalty=3, total=5, goals=2, saves=1)
        full.update_status(status)
        low.update_status(status)
        self.assertLess(len(low.primitives), len(full.primitives) * 0.65)
        for prefix in ('turf_', 'screen_', PREFIX):
            self.assertEqual([p for p in low.primitives if p.name.startswith(prefix)],
                             [p for p in full.primitives if p.name.startswith(prefix)])
        for prefix in ('bowl_', 'net_'):
            self.assertLess(0, sum(p.name.startswith(prefix) for p in low.primitives))
            self.assertLess(sum(p.name.startswith(prefix) for p in low.primitives),
                            sum(p.name.startswith(prefix) for p in full.primitives))

    def test_population_is_decorative_and_leaves_model_and_state_exact(self):
        m=self.model();d=mujoco.MjData(m);before=model_signature(m)
        arrays=[x.copy() for x in (d.qpos,d.qvel,d.ctrl)]
        s=StadiumScene(m);scene=mujoco.MjvScene(m,maxgeom=2500)
        s.populate(scene)
        for i,p in enumerate(s.primitives):
            if p.name.startswith(PREFIX):
                self.assertEqual(scene.geoms[i].objid,-1)
                self.assertEqual(scene.geoms[i].category,mujoco.mjtCatBit.mjCAT_DECOR)
        self.assertEqual(before,model_signature(m))
        for a,b in zip(arrays,(d.qpos,d.qvel,d.ctrl)):np.testing.assert_array_equal(a,b)


if __name__=='__main__':unittest.main()
