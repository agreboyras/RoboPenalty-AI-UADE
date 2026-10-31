"""Regression tests for contact identity and conservative outcome reporting."""
from types import SimpleNamespace
import unittest
from .observe_reference import contact_geometry_ids, classify_result


class ObserverTests(unittest.TestCase):
    def test_canonical_ids_ignore_stale_deprecated_fields(self):
        c = SimpleNamespace(geom=[7,19], geom1=0, geom2=0)
        self.assertEqual(contact_geometry_ids(c), (7,19))

    def test_non_goal_without_contact_is_not_save(self):
        self.assertEqual(classify_result(False,False,True,True,False),
                         'NO_ROBOT_CONTACT_NO_GOAL')

    def test_contact_without_causal_evidence_is_not_save(self):
        for aimed,reversed_after,frame in [(False,True,False),(True,False,False),(True,True,True)]:
            self.assertEqual(classify_result(False,True,aimed,reversed_after,frame),
                             'ROBOT_CONTACT_NO_GOAL_SAVE_NOT_PROVEN')

    def test_goal_has_precedence_over_contact(self):
        self.assertEqual(classify_result(True,True,True,True,False),'GOAL')

    def test_rebound_label_retains_observation_qualification(self):
        self.assertEqual(classify_result(False,True,True,True,False),
                         'ROBOT_REBOUND_PRECONTACT_AIM_INSIDE_NO_GOAL_OBSERVED')


if __name__ == '__main__': unittest.main()
