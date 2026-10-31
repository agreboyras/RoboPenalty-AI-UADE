import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from .posture_targets import effective_caps,extend
from .runtime import components

NAMES=['left_shoulder_roll_joint','right_shoulder_roll_joint','left_shoulder_pitch_joint',
       'right_shoulder_pitch_joint','left_elbow_joint','right_elbow_joint','waist_roll_joint','left_knee_joint']


class ExperimentTests(unittest.TestCase):
    def test_hip_roll_uses_effective_88_not_software_139(self):
        model=SimpleNamespace(actuator_ctrllimited=[1,1],actuator_ctrlrange=np.array([[-88,88],[-5,5]]),
            jnt_actfrclimited=[1,1],jnt_actfrcrange=np.array([[-88,88],[-5,5]]))
        keeper=SimpleNamespace(joints=[0,1],actuators=[0,1])
        np.testing.assert_array_equal(effective_caps(model,keeper,[139,25]),[88,5])

    def test_software_limit_remains_a_limit(self):
        model=SimpleNamespace(actuator_ctrllimited=[1],actuator_ctrlrange=np.array([[-88,88]]),
            jnt_actfrclimited=[1],jnt_actfrcrange=np.array([[-88,88]]))
        np.testing.assert_array_equal(effective_caps(model,SimpleNamespace(joints=[0],actuators=[0]),[20]),[20])

    def test_non_reaction_is_exact_and_input_not_mutated(self):
        q=np.arange(8,dtype=float);before=q.copy()
        np.testing.assert_array_equal(extend(q,NAMES,'RECOVERY'),before)
        extend(q,NAMES,'LEFT');np.testing.assert_array_equal(q,before)

    def test_world_left_selects_anatomical_right_and_preserves_knee(self):
        q=np.zeros(8);q[-1]=.3;p=extend(q,NAMES,'LEFT')
        self.assertEqual(p[1],-.95);self.assertEqual(p[5],.40);self.assertEqual(p[6],-.08)
        self.assertEqual(p[0],0.);self.assertEqual(p[-1],.3)
        right=extend(q,NAMES,'RIGHT');self.assertEqual(right[0],.95);self.assertEqual(right[6],.08)

    def test_half_extension_interpolates_without_changing_other_references(self):
        q=np.zeros(8);full=extend(q,NAMES,'RIGHT')
        np.testing.assert_allclose(extend(q,NAMES,'RIGHT',.5),full*.5)

    def test_disabled_returns_original_factories_without_wrapper(self):
        original=(type('Original',(),{}),type('Selector',(),{}))
        with patch('experiments.keeper_saves.runtime.stable_components',return_value=original):
            result=components(object())
        self.assertIs(result[0],original[0]);self.assertIs(result[1],original[1])

    def test_live_camera_defaults_distinguish_laboratory_and_shot(self):
        from .live_viewer import camera_for
        self.assertEqual(camera_for('no-ball'),'keeper')
        self.assertEqual(camera_for('nominal'),'behind')
        self.assertEqual(camera_for('nominal','goal'),'goal')

    def test_keeper_view_only_sets_diagnostic_camera(self):
        from .live_viewer import open_presenter
        from unittest.mock import Mock
        fake=Mock()
        with patch('experiments.keeper_saves.live_viewer.LivePresenter',return_value=fake):
            self.assertIs(open_presenter(object(),'.','keeper'),fake)
        self.assertEqual(fake.view,'keeper')
        self.assertEqual(fake.camera['lookat'],[4.2,0,.85])
        fake.apply_camera.assert_called_once()

    def test_live_close_joins_resources_and_distinguishes_finished_trial(self):
        from . import live_viewer
        from unittest.mock import Mock
        import tempfile,json,sys
        from pathlib import Path
        scratch=Path(__file__).resolve().parent/'results';scratch.mkdir(exist_ok=True)
        for finished in (False,True):
            with tempfile.TemporaryDirectory(dir=scratch) as folder:
                root=Path(folder);out=root/'output';presenter=Mock();presenter.summary.return_value={}
                observer=Mock();observer.presenter=presenter
                if finished:presenter.pause.side_effect=live_viewer.ViewerClosed('closed')
                with patch.object(live_viewer.bootstrap,'PROJECT',root),patch.object(sys,'argv',['live','--output',str(out)]),\
                     patch.object(live_viewer,'NoBallObserver',return_value=observer),\
                     patch.object(live_viewer,'no_ball',return_value={'passed':True},side_effect=None if finished else live_viewer.ViewerClosed('closed')):
                    live_viewer.main()
                presenter.close.assert_called_once()
                report=json.loads((out/'live.json').read_text())
                self.assertEqual(report['termination'],'completed_viewer_closed' if finished else 'viewer_closed')


if __name__=='__main__':unittest.main()
