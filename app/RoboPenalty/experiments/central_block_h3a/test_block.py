import unittest
from .run import verdict,CRITERIA

class VerdictTests(unittest.TestCase):
    def setUp(self):
        self.e=dict(physical_valid=True,has_keeper_contact=True,goal_detected=False,trajectory_changed=True)
        self.ref=dict(physical_valid=True,goal_detected=True)
    def test_valid_counterfactual_contact_save(self):self.assertEqual(verdict(self.e,self.ref),'ATAJADA DEMOSTRADA')
    def test_goal_after_contact_is_not_save(self):
        self.e['goal_detected']=True;self.assertEqual(verdict(self.e,self.ref),'CONTACTO SIN ATAJADA')
    def test_invalid_or_incomplete_trial_is_not_save(self):
        self.e['physical_valid']=False;self.assertEqual(verdict(self.e,self.ref),'CONTACTO SIN ATAJADA')
    def test_no_contact_even_without_goal(self):
        self.e['has_keeper_contact']=False;self.assertEqual(verdict(self.e,self.ref),'SIN CONTACTO')
    def test_absent_reference_is_not_save(self):self.assertEqual(verdict(self.e,None),'CONTACTO SIN ATAJADA')
    def test_invalid_reference_is_not_save(self):
        self.ref['physical_valid']=False;self.assertEqual(verdict(self.e,self.ref),'CONTACTO SIN ATAJADA')
    def test_reference_miss_is_not_save(self):
        self.ref['goal_detected']=False;self.assertEqual(verdict(self.e,self.ref),'CONTACTO SIN ATAJADA')
    def test_contact_without_change_is_not_save(self):
        self.e['trajectory_changed']=False;self.assertEqual(verdict(self.e,self.ref),'CONTACTO SIN ATAJADA')
    def test_full_window_and_declared_limits(self):
        self.assertEqual((CRITERIA['duration_s'],CRITERIA['steps']),(14.,7000))
        self.assertEqual(CRITERIA['max_joint_speed_rad_s'],20.)
        self.assertEqual(CRITERIA['max_penetration_m'],.02)
        self.assertEqual(CRITERIA['max_joint_excess_rad'],.03)

if __name__=='__main__':unittest.main()
