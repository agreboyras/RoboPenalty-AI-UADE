import unittest
import numpy as np
from .support import hull,margin
from .maneuver import Transfer,partial,PROTOCOL
from experiments.free_keeper4b.policy import JOINTS

def history():
    t=np.arange(1.5,2.,.002)
    return dict(time=list(t),load=[np.array([172.,172.]) for _ in t],point=[np.array([4.1,.15,.13]) for _ in t])

class SupportTests(unittest.TestCase):
    def test_hull_ignores_interior_duplicates(self):
        h=hull([[0,0],[1,0],[1,1],[0,1],[.5,.5],[0,0]])
        self.assertEqual(len(h),4);self.assertAlmostEqual(margin([.5,.5],h),.5)
        self.assertAlmostEqual(margin([2,.5],h),-1.)
    def test_degenerate_support_not_a_false_positive(self):self.assertIsNone(margin([0,0],hull([[0,0],[1,0]])))
    def test_partial_unload_requires_support_not_flight(self):
        self.assertFalse(partial([0,0],172,344));self.assertFalse(partial([50,10],172,344))
        self.assertTrue(partial([260,80],172,344))
    def test_partial_requires_both_share_and_baseline_reduction(self):
        self.assertFalse(partial([400,120],172,344));self.assertFalse(partial([190,105],172,344))
    def test_start_has_no_reference_jump(self):
        b=Transfer(JOINTS,'transfer',344);h=history();b.observe(2.,dict(load=np.array([172,172]),clearance=[0,0]),h)
        np.testing.assert_array_equal(b.residual(2.),np.zeros(29));self.assertEqual(b.start,2.)
    def test_only_four_transfer_joints_are_modified(self):
        b=Transfer(JOINTS,'transfer',344);b.start=2.;b.state='TRANSFER'
        q=b.residual(2.5);self.assertEqual(np.flatnonzero(q).tolist(),[1,5,7,11])
        np.testing.assert_allclose(q[[1,5,7,11]],[-.12,.12,-.12,.12])
    def test_quintic_transfer_and_recovery_bounds(self):
        b=Transfer(JOINTS,'transfer',344);b.start=2.;b.state='TRANSFER'
        t=np.arange(2.,3.2,.002);rows=[b.residual(x) for x in t];last=b.residual(3.2)
        b.begin_recovery(3.2,'test');np.testing.assert_array_equal(last,b.residual(3.2))
        rows.extend(b.residual(x) for x in np.arange(3.2,4.,.002));q=np.array(rows)
        self.assertLess(abs(np.diff(q,axis=0)/.002).max(),PROTOCOL['reference_speed_rad_s'])
        self.assertLess(abs(np.diff(q,n=2,axis=0)/.002**2).max(),PROTOCOL['reference_acc_rad_s2'])
        np.testing.assert_array_equal(q[-1],np.zeros(29))
    def test_late_unload_does_not_enable_lift(self):
        b=Transfer(JOINTS,'block',344);h=history();last=dict(load=np.array([172,172]),clearance=[0,0])
        b.observe(2.,last,h)
        for t in np.arange(2.02,2.48,.02):
            h['time'].append(t-.002);h['load'].append(np.array([172.,172.]));h['point'].append(np.array([4.1,.15,.13]))
            b.observe(t,last,h)
        self.assertEqual(b.state,'RECOVERY');self.assertFalse(any(e['state']=='LIFT' for e in b.events))
    def test_deadline_frozen(self):self.assertEqual(PROTOCOL['deadline_s'],.874)
    def test_sustained_interval_spans_full_40ms(self):
        from .analyze import sustained
        t=np.arange(2.,2.06,.002);result=sustained(t,np.ones(len(t),dtype=bool))
        self.assertAlmostEqual(result['elapsed_confirmed_s'],.04)

if __name__=='__main__':unittest.main()
