"""Synthetic contracts for R8 date and segment logic; no fit API exists here."""
import unittest
import pandas as pd
from compute_evidence import segments, conditions
def p(x):return pd.Period(x,freq='M')
def d(x):return pd.Series(pd.to_datetime(x,format='mixed'))
class Contracts(unittest.TestCase):
    def test_contiguous(self):self.assertEqual(segments([p('2099-02'),p('2099-01'),p('2099-04')]),[[p('2099-01'),p('2099-02')],[p('2099-04'),p('2099-04')]])
    def test_single_month_impossible(self):self.assertEqual(conditions([[p('2099-01'),p('2099-01')]],d(['2099-01-01']),1),[True,True,True,False])
    def test_early_within_segment(self):self.assertEqual(conditions([[p('2099-01'),p('2099-03')]],d(['2099-02-01']),1),[True]*4)
    def test_before_segment(self):self.assertEqual(conditions([[p('2099-01'),p('2099-03')]],d(['2098-12-01']),1),[True,True,False,True])
    def test_after_segment(self):self.assertEqual(conditions([[p('2099-01'),p('2099-03')]],d(['2099-04-01']),1),[True,True,False,False])
    def test_repeated_same_date(self):self.assertTrue(all(conditions([[p('2099-01'),p('2099-03')]],d(['2099-02-01']*2),2)))
    def test_two_days_same_month(self):self.assertEqual(conditions([[p('2099-01'),p('2099-03')]],d(['2099-02-01','2099-02-02']),2),[True,False,False,False])
    def test_missing(self):self.assertEqual(conditions([[p('2099-01'),p('2099-03')]],d([None]),1),[True,False,False,False])
    def test_multi_current_segment(self):self.assertEqual(conditions([[p('2098-01'),p('2098-01')],[p('2099-01'),p('2099-03')]],d(['2099-02-01']),1),[False,True,True,True])
    def test_year_boundary(self):self.assertTrue(all(conditions([[p('2098-12'),p('2099-01')]],d(['2098-12-31']),1)))
if __name__=='__main__':unittest.main(verbosity=2)
