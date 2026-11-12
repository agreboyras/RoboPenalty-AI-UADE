from bootstrap import *
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

from phase8c.catalog import Catalog
from phase8c.runtime import components
from phase9a.bus import InputBus
from phase9a.commands import LEFT_NEAR, LEFT_OPEN, interpret
from phase9a.exhibition import ExhibitionControl, ExhibitionRuntime, exhibition_catalog, fixed_selector
from phase9a.language import resolve_shot


class ExhibitionInputTests(unittest.TestCase):
    def test_automatic_exhibition_uses_the_rehearsed_catalog_action(self):
        catalog = exhibition_catalog(Catalog(PROJECT / 'phase8c/catalog_v1.json'))
        _, base = components(catalog)
        observation = base.observation_type(
            'long', 'agent', 0., 0., 0., .22, .115, (-1., 0., .115), (-2., 0., .8),
            available_actions=catalog.actions,
        )
        for action in (LEFT_NEAR, LEFT_OPEN):
            with self.subTest(action=action):
                selector = fixed_selector(base, action)()
                decision = selector.choose(observation, catalog.calibration, 'exhibition')
                self.assertEqual(decision['action'], action)
                self.assertEqual(decision['strategy'], 'fixed')

    def test_open_left_command_is_scoped_to_exhibition(self):
        self.assertEqual(interpret('Patea a la izquierda abierta'), 'unsupported:left_open')
        self.assertIsNone(interpret('Patea a la izquierda abierta o a la derecha', exhibition=True))
        self.assertEqual(interpret('Pateá a la izquierda abierta', exhibition=True), 'shot:' + LEFT_OPEN)
        self.assertEqual(interpret('Pateá abierto izquierdo', exhibition=True), 'shot:' + LEFT_OPEN)
        self.assertEqual(interpret('Patea abierto a la izquierda', exhibition=True), 'shot:' + LEFT_OPEN)

    def test_voice_fallback_uses_exhibition_actions(self):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(
            status='completed', output=[SimpleNamespace(
                type='function_call', name='patear', arguments='{"action":"left_open_b104"}')],
        )
        self.assertEqual(resolve_shot(client, 'mandala abierta ala isquierda', exhibition=True), 'shot:' + LEFT_OPEN)
        schema = client.responses.create.call_args.kwargs['tools'][0]['parameters']
        self.assertEqual(schema['properties']['action']['enum'], [LEFT_NEAR, LEFT_OPEN])
        self.assertIsNone(resolve_shot(client, 'mandala abierta ala isquierda'))

    def test_alternate_shot_is_rejected_and_window_stays_open(self):
        bus = InputBus(exhibition=True)
        control = ExhibitionControl(bus, emit=lambda *args, **kwargs: None)
        control.phase = 'PREPARING'
        control.open_selection()
        bus.submit('Patea a la derecha')
        control.pump()
        self.assertFalse(control.events[-1]['accepted'])
        self.assertTrue(control.awaiting_shot)
        bus.submit('Patea a la izquierda')
        control.pump()
        self.assertTrue(control.events[-1]['accepted'])
        self.assertEqual(control.pending_shot['action'], LEFT_NEAR)
        control.open_selection()
        bus.submit('Patea a la izquierda abierta')
        control.pump()
        self.assertTrue(control.events[-1]['accepted'])
        self.assertEqual(control.pending_shot['action'], LEFT_OPEN)


BUNDLE = PROJECT.parents[1]
POLICY_PYTHON = BUNDLE / 'validation/envs/keeper/Scripts/python.exe'
LOCO_DEPLOY = BUNDLE.parent / 'RoboNaldo_Deploy'
FREEKICK = PROJECT.parent / 'RoboNaldo_Deploy/policy/robonaldo/FreeKick.py'


@unittest.skipUnless(POLICY_PYTHON.is_file() and FREEKICK.is_file() and (
    LOCO_DEPLOY / 'policy/loco_mode/model/policy_29dof.pt').is_file(),
    'Requires the existing local FreeKick and H1 balance resources')
class ExhibitionPhysicsTests(unittest.TestCase):
    def test_same_kick_goes_in_with_guard_and_is_saved_by_the_dive(self):
        catalog = exhibition_catalog(Catalog(PROJECT / 'phase8c/catalog_v1.json'))
        with TemporaryDirectory() as directory:
            output = Path(directory)
            _, selector = components(catalog)
            runtime = ExhibitionRuntime(catalog, selector.observation_type, POLICY_PYTHON, LOCO_DEPLOY, output)
            try:
                for action in catalog.actions:
                    with self.subTest(action=action):
                        outcomes = []
                        initial_hashes = []
                        for enable_dive in (False, True):
                            path = output / f'{action}_{enable_dive}.json'
                            result, _, _ = runtime.execute(
                                'long', 'agent', path, lambda observation: action,
                                lambda: None, enable_dive=enable_dive,
                            )
                            outcomes.append(runtime.evaluate(result, 'long', action)[0])
                            initial_hashes.append(result['initial_state_sha256'])
                            self.assertLessEqual(result['ball_prefix_error_vs_historical_probe'], 1e-8)
                            if enable_dive:
                                self.assertGreaterEqual(
                                    result['free_keeper']['dive_start_s'],
                                    result['evaluation']['first_foot_ball']['time_sim_s'],
                                )
                                self.assertGreater(result['free_keeper']['maximum_lateral_reach_m'], .5)
                                contact = result['evaluation']['first_keeper_ball']
                                self.assertIsNotNone(contact)
                                if action == LEFT_OPEN:
                                    self.assertIn('wrist', contact['body'])
                                    self.assertLess(contact['position_w'][0], 5.)
                            elif action == LEFT_OPEN:
                                goal_y = result['evaluation']['goal_crossing_measured']['position_w'][1]
                                self.assertGreater(goal_y, .75)
                        self.assertEqual(outcomes, ['goal', 'save'])
                        self.assertEqual(*initial_hashes)
            finally:
                runtime.close()


if __name__ == '__main__':
    unittest.main()
