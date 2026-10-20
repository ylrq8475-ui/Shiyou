"""Pure synthetic checks: aggregation, horizon priority and leaf sample units."""
import unittest
from decimal import Decimal as D
def loss(p,y):return sum(2**(-t)*abs(a-b)/(abs(a)+abs(b)+1e-6) for t,(a,b) in enumerate(zip(p,y),1))
def diversity(a,b):return sum(abs(x-y)/(abs(x)+abs(y)+1e-6) for x,y in zip(a,b))/len(a)
class Checks(unittest.TestCase):
 def test_screenshot_delta(self):self.assertEqual(D('79.3643')-D('79.4717'),D('-0.1074'))
 def test_equal_well_fold_pooling(self):
  scores=[100,0];counts=[17,16]
  self.assertNotEqual(sum(scores)/2,sum(s*n for s,n in zip(scores,counts))/sum(counts))
 def test_unweighted_diversity_can_prefer_late_only_change(self):
  base=[1.0]*12;late=base[:4]+[10.0]*8;early=[10.0,10.0]+base[2:]
  self.assertGreater(diversity(base,late),diversity(base,early))
  self.assertLess(loss(late,base),loss(early,base))
 def test_first_two_weight(self):self.assertEqual(sum(2**(-t) for t in [1,2]),.75)
 def test_leaf_count_unit_changes(self):
  stacked_one_well=[('synthetic_well',t) for t in range(1,13)]
  self.assertGreaterEqual(len(stacked_one_well),10)
  self.assertLess(len(set(w for w,t in stacked_one_well)),10)
if __name__=='__main__':unittest.main(verbosity=2)
