"""Synthetic official-loss and diagnostic oracles written by Codex."""
import math, statistics, sys, unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent/'sources/reference/reference'))
import diagnostics_reference as d

def manual_loss(p,y):
    return math.fsum(2**(-t)*abs(a-b)/(abs(a)+abs(b)+1e-6) for t,(a,b) in enumerate(zip(p,y),1))

class IndependentChecks(unittest.TestCase):
    def test_metric_epsilon_and_unscaled_weight(self):
        p=[0.0]*12;y=[0.0]*12;y[0]=1e-6
        self.assertAlmostEqual(d.well_loss(p,y),0.25,places=14)
    def test_weight_order_and_unnormalized_total(self):
        p=[2.0]*12;y=[1.0]*12
        self.assertAlmostEqual(d.well_loss(p,y),(1-2**-12)/(3+1e-6),places=14)
        self.assertEqual(math.fsum(2**(-i) for i in range(1,5)),0.9375)
    def test_equal_well_mean_against_manual(self):
        pairs=[([0.0]*12,[0.0]*12),([3.0]*12,[1.0]*12)]
        expect=100*(1-statistics.mean(manual_loss(p,y) for p,y in pairs))
        self.assertAlmostEqual(d.score(pairs),expect,places=12)
    def test_zero_budget_is_supremum_not_actual_tiny_prediction_gain(self):
        y=[0.0]+[1.0]*11;p=[1e-9]+[1.0]*11
        budget=d.zero_month_mass([y])['max_recoverable_points_if_perfect_zero_detection']
        true_gain=100*manual_loss(p,y)
        self.assertEqual(budget,50.0)
        self.assertLess(true_gain,0.05)
    def test_leave_one_well_median_matches_independent_prediction(self):
        targets=[[1.0]*12,[2.0]*12,[20.0]*12]
        anchors=[1.0,2.0,4.0]
        predictions=[]
        for i in range(3):
            multiplier=statistics.median(targets[j][0]/anchors[j] for j in range(3) if j!=i)
            predictions.append([multiplier*anchors[i]]*12)
        expected=100*(1-statistics.mean(manual_loss(p,y) for p,y in zip(predictions,targets)))
        self.assertAlmostEqual(d.anchored_persistence_score(targets,anchors)['score'],expected,places=12)
    def test_both_anchor_filter_uses_same_wells(self):
        targets=[[1.0]*12]*6
        result=d.compare_anchors(targets,[1,2,3,0,float('nan'),5],[1,2,3,4,5,-1])
        self.assertEqual(result['wells_compared'],3)
        self.assertEqual(result['delta_score_M_minus_M1'],0)
    def test_nonfinite_metric_rejected(self):
        with self.assertRaises(ValueError):d.well_loss([float('inf')]*12,[1.0]*12)
    def test_finite_oracle_cannot_imply_universal_ceiling(self):
        # This tests the scope, not the expensive real-data oracle.
        self.assertEqual(len(d._B_GRID),261)
        self.assertEqual(len(d._A_GRID),801)
        self.assertEqual(d.DECISION['G_CEIL']['declare_95_not_credible_if_smooth_plus_zero_oracle_lt'],90.0)

if __name__=='__main__':unittest.main()
