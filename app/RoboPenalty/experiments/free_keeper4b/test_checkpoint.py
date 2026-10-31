"""Explicit local-checkpoint tests. No physics and no checkpoint redistribution."""
import argparse
from pathlib import Path
import unittest
import numpy as np
from .policy import Locomotion


class CheckpointTests(unittest.TestCase):
    deploy = None

    @classmethod
    def setUpClass(cls):
        cls.policy = Locomotion(cls.deploy)

    def setUp(self):
        self.policy.reset()

    def test_reset_clears_both_states_and_last_action(self):
        p = self.policy
        p.decide(p.observe(p.home, np.zeros(29), [1, 0, 0, 0], [0, 0, 0]))
        self.assertGreater(p.recurrent_max(), 0)
        p.reset()
        self.assertEqual(p.recurrent_max(), 0)
        np.testing.assert_array_equal(p.last_action, np.zeros(29))

    def test_normalizer_formula_and_frozen_buffers(self):
        p = self.policy
        x = p.torch.arange(96, dtype=p.torch.float32).reshape(1, 96)*0.001
        with p.torch.inference_mode():
            actual = p.module.normalizer(x)
            expected = (x-p.module.normalizer._mean)/(p.module.normalizer._std+p.module.normalizer.eps)
        self.assertTrue(p.torch.equal(actual, expected))
        self.assertTrue(p.normalizer_unchanged())

    def test_adapter_matches_direct_exported_inference(self):
        p = self.policy
        obs = p.observe(p.home, np.zeros(29), [1, 0, 0, 0], [0, 0, 0])
        np.testing.assert_array_equal(obs[6:9], np.zeros(3))
        with p.torch.inference_mode():
            raw = p.module(p.torch.from_numpy(obs[None]).clamp(-100, 100)).clamp(-100, 100).numpy().reshape(29)
        expected = p.to_motor(p.default+0.25*raw)
        p.reset()
        np.testing.assert_array_equal(p.decide(obs), expected)

    def test_replay_is_exact_after_reset(self):
        p = self.policy
        sequences = []
        for _ in range(2):
            p.reset()
            seq = []
            for i in range(20):
                obs = p.observe(p.home, np.zeros(29), [1, 0, 0, 0], [i*0.001, 0, 0])
                seq.append(p.decide(obs))
            sequences.append(seq)
        np.testing.assert_array_equal(sequences[0], sequences[1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deploy', type=Path, required=True)
    args, rest = parser.parse_known_args()
    CheckpointTests.deploy = args.deploy
    unittest.main(argv=['test_checkpoint', *rest])
