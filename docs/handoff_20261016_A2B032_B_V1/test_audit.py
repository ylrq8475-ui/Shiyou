"""Synthetic poison-cell, framing, alignment and official-metric contracts."""
import unittest
import numpy as np,pandas as pd
from audit_core import *
class Tests(unittest.TestCase):
    def test_keys_do_not_decode_dynamic_cells(self):
        raw=b'WELL_ID,NY,CSLB,RCYL\r\nfiction,2099/01/01,\xff,\xff\r\n';keys,_=key_projection(raw,'WELL_ID','NY','utf-8-sig',',');self.assertEqual(keys,[('fiction','2099/01/01')])
    def test_window_poison_not_decoded(self):
        raw=b'WELL_ID,NY,CSLB,RCYL\nfiction,2099/01/01,allowed,7\n\xff,2099/02/01,\xff,\xff\n'
        records,a=permitted_test_history(raw,'WELL_ID','NY','CSLB','RCYL',pd.Period('2099-02','M'),'utf-8-sig',',');self.assertEqual(len(records),1);self.assertEqual(a['test_window_RCYL_decoded'],0)
    def test_future_value_poison_invariance(self):
        a=b'WELL_ID,NY,CSLB,RCYL\na,2099/01/01,event,5\na,2099/02/01,secret,999\n';b=a.replace(b'secret,999',b'"anything,else",\xff')
        f=lambda raw:permitted_test_history(raw,'WELL_ID','NY','CSLB','RCYL',pd.Period('2099-02','M'),'utf-8-sig',',')
        self.assertEqual(f(a),f(b))
    def test_quotes_and_newlines(self):
        raw=b'WELL_ID,NY,CSLB,RCYL\r\n"f,iction",2099/01/01,"line\ntext",7\r\n';keys,_=key_projection(raw,'WELL_ID','NY','utf-8-sig',',');self.assertEqual(keys[0][0],'f,iction')
    def test_escaped_quote(self):
        raw=b'WELL_ID,NY\n"a""b",2099/01/01\n';self.assertEqual(key_projection(raw,'WELL_ID','NY','utf-8-sig',',')[0][0][0],'a"b')
    def test_calendar_cross_year(self):self.assertEqual(pd.Period('2099-01','M').ordinal-pd.Period('2098-12','M').ordinal,1)
    def test_segments(self):self.assertEqual(len(segments([pd.Period('2099-01','M'),pd.Period('2099-02','M'),pd.Period('2099-04','M')])),2)
    def test_joint_threshold_8(self):self.assertTrue(alignment([(1,1)]*8+[(2,1)]*2,[(1,1)]*81)['ALIGN_MATCH'])
    def test_joint_threshold_7(self):self.assertFalse(alignment([(1,1)]*7+[(2,1)]*3,[(1,1)]*81)['ALIGN_MATCH'])
    def test_mode_mismatch(self):self.assertFalse(alignment([(1,1)]*10,[(2,1)]*81)['ALIGN_MATCH'])
    def test_mode_tie_not_selected(self):self.assertFalse(alignment([(1,1)]*5+[(2,1)]*5,[(1,1)]*81)['unique_modes'])
    def test_perfect_score(self):self.assertEqual(score(np.ones((2,12)),np.ones((2,12)))['official_score'],100.)
    def test_no_normalization_or_factor_two(self):
        v=score(np.ones((1,12)),np.zeros((1,12)));self.assertAlmostEqual(v['official_score'],100*(1-sum(.5**t for t in range(1,13))/(1+1e-6)),12)
    def test_equal_wells_prefix(self):
        x=score(np.array([[0]*12,[1]*12]),np.zeros((2,12)));self.assertAlmostEqual(x['monthly_weighted_loss']['m1_to_1'],.25/(1+1e-6))
    def test_missing_persistence_not_imputed(self):self.assertIsNone(persistence([{'truth':[1]*12,'P1':None}],'P1')['all_well_score'])
if __name__=='__main__':unittest.main(verbosity=2)
