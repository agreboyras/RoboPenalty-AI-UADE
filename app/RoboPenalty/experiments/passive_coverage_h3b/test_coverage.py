import unittest
from .run import category,validate_reference,ACTIONS

class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.e=dict(physical_valid=True,has_keeper_contact=True,goal_detected=False,trajectory_changed=True)
        self.ref=dict(physical_valid=True,goal_detected=True)
    def test_goal_prevents_save(self):
        self.e['goal_detected']=True;self.assertEqual(category(self.e,self.ref),'CONTACTO SIN ATAJADA')
    def test_verified_contact_save(self):self.assertEqual(category(self.e,self.ref),'ATAJADA')
    def test_no_contact_is_not_save(self):
        self.e['has_keeper_contact']=False;self.assertEqual(category(self.e,self.ref),'SIN CONTACTO')
    def test_invalid_trial_is_inconclusive(self):
        self.e['physical_valid']=False;self.assertEqual(category(self.e,self.ref),'RESULTADO NO CONCLUYENTE')
    def test_invalid_trial_without_contact_is_still_inconclusive(self):
        self.e.update(physical_valid=False,has_keeper_contact=False)
        self.assertEqual(category(self.e,self.ref),'RESULTADO NO CONCLUYENTE')
    def test_no_reference_is_inconclusive(self):self.assertEqual(category(self.e,None),'RESULTADO NO CONCLUYENTE')
    def test_reference_miss_is_inconclusive(self):
        self.ref['goal_detected']=False;self.assertEqual(category(self.e,self.ref),'RESULTADO NO CONCLUYENTE')
    def test_no_velocity_change_is_inconclusive(self):
        self.e['trajectory_changed']=False;self.assertEqual(category(self.e,self.ref),'RESULTADO NO CONCLUYENTE')
    def test_reference_action_and_hash_are_required(self):
        for row in (dict(action='center',placement='aside',calibration_sha256='bad'),dict(action='right_open_m100',placement='aside',calibration_sha256='hash'),dict(action='center',placement='center',calibration_sha256='hash')):
            with self.assertRaises(ValueError):validate_reference(row,'center','hash')
        validate_reference(dict(action='center',placement='aside',calibration_sha256='hash'),'center','hash')
    def test_catalog_is_exact(self):
        self.assertEqual(ACTIONS,('center','left_near_b060','right_inter_m080','right_open_m100','right_corner_m140'))

if __name__=='__main__':unittest.main()
