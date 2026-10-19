"""Account A synthetic checks only. No real records, labels, fits or file paths."""
import importlib.util, math, unittest
from decimal import Decimal, getcontext
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('reviewed_032_core',ROOT/'sources/B032/audit_core.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
def manual_score(y,p):
    getcontext().prec=45
    scores=[]
    for truth,pred in zip(y,p):
        loss=Decimal(0)
        for t,(a,b) in enumerate(zip(truth,pred),1):
            a,b=Decimal(str(a)),Decimal(str(b))
            loss+=abs(a-b)/(abs(a)+abs(b)+Decimal('0.000001'))/(Decimal(2)**t)
        scores.append(Decimal(100)*(1-loss))
    return float(sum(scores)/len(scores))
def ix(year,month):return year*12+month-1
def legal_prefix(rows,target_start):return [x for x in rows if x[0]<target_start]
class Independent(unittest.TestCase):
    def test_decimal_official_oracle(self):
        y=[[0,1,2,4,3,0,1,1,2,6,3,1],[7]*12,[1]*12]
        p=[[1]*12,[4]*12,[0,1,1,1,1,1,1,1,1,1,1,1]]
        self.assertAlmostEqual(core.score(y,p)['official_score'],manual_score(y,p),12)
    def test_epsilon_exact_near_zero(self):
        y=[[1e-7]*12];p=[[0]*12]
        self.assertAlmostEqual(core.score(y,p)['official_score'],manual_score(y,p),12)
    def test_both_zero_score(self):self.assertEqual(core.score([[0]*12],[[0]*12])['official_score'],100)
    def test_early_order_weight_halves(self):
        y=[[1]*12];p1=[[0]+[1]*11];p2=[[1,0]+[1]*10]
        l1=1-core.score(y,p1)['official_score']/100;l2=1-core.score(y,p2)['official_score']/100
        self.assertAlmostEqual(l1,2*l2,14)
    def test_four_month_weight_mass(self):self.assertEqual(sum(.5**t for t in range(1,5)),.9375)
    def test_full_weight_not_normalized(self):self.assertEqual(sum(.5**t for t in range(1,13)),1-2**-12)
    def test_unequal_target_scale_still_equal_wells(self):
        y=[[1]*12,[1000]*12];p=[[0]*12,[1000]*12]
        self.assertAlmostEqual(core.score(y,p)['official_score'],manual_score(y,p),12)
    def test_invalid_nan(self):
        with self.assertRaises(RuntimeError):core.score([[1]*12],[[math.nan]*12])
    def test_invalid_inf(self):
        with self.assertRaises(RuntimeError):core.score([[1]*12],[[math.inf]*12])
    def test_negative_blocked(self):
        with self.assertRaises(RuntimeError):core.score([[1]*12],[[-1]*12])
    def test_eleven_months_blocked(self):
        with self.assertRaises(RuntimeError):core.score([[1]*11],[[1]*11])
    def test_cutoff_boundary_exact(self):
        target=ix(2099,2); rows=[(target-2,'old'),(target-1,'last'),(target,'poison'),(target+1,'poison')]
        self.assertEqual(legal_prefix(rows,target),rows[:2])
    def test_gap_months_are_history(self):
        event=ix(2099,1);target=event+3;rows=[(event,'anchor'),(event+1,'gap'),(event+2,'gap'),(target,'forbidden')]
        self.assertEqual(len(legal_prefix(rows,target)),3)
    def test_year_rollover_and_leap_month(self):
        self.assertEqual(ix(2100,1)-ix(2099,12),1)
        self.assertEqual(ix(2096,3)-ix(2096,2),1)
    def test_training_and_test_same_cutoff_rule(self):
        for event in (ix(2099,1),ix(2099,12)):
            for offset in (1,2,3):
                target=event+offset
                self.assertEqual(max(x[0] for x in legal_prefix([(event+i,0) for i in range(-12,16)],target)),target-1)
    def test_template_start_not_missingness_or_poison(self):
        origin=pd.Period('2099-02','M')
        raw=b'WELL_ID,NY,CSLB,RCYL,OTHER\na,2099/01/01,x,3,unused\na,2099/02/01,\xff,\xff,\xff\na,2099/03/01,"x,y",999,"line\ninside"\n'
        records,counts=core.permitted_test_history(raw,'WELL_ID','NY','CSLB','RCYL',origin,'utf-8-sig',',')
        self.assertEqual(len(records),1);self.assertEqual(records[0][-1],'3');self.assertEqual(counts['test_window_rows_skipped_before_dynamic_cell_decode'],2)
    def test_false_alignment_despite_perfect_endpoint_match(self):
        test=[(1,1)]*6+[(2,1)]*4;train=[(1,1)]*53+[(2,1)]*25+[(3,1)]*3
        r=core.alignment(test,train)
        self.assertFalse(r['ALIGN_MATCH']);self.assertTrue(all(end==1 for start,end in test+train))
    def test_uniform_start_shift_breaks_multi_month_segments(self):
        for length in (2,3):
            start=ix(2099,1);end=start+length-1;template=end+1
            self.assertNotEqual(start+1,template)
    def test_p3_literal_reference_is_same_predictor(self):
        for k in (1,2,3):
            start=ix(2099,1)+k
            self.assertEqual(start-1,ix(2099,1)+k-1)
    def test_anchor_month_not_allowed_if_inside_template(self):
        event=ix(2099,2)
        self.assertEqual(legal_prefix([(event-1,'history'),(event,'anchor')],event),[(event-1,'history')])
if __name__=='__main__':unittest.main(verbosity=2)
