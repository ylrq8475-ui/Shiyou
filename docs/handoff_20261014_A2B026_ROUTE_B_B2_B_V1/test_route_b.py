"""Synthetic checks for contracts, formula, metrics and fit budget; zero fits."""
import unittest
import numpy as np
import pandas as pd
from route_b_core import *

class FakeClassifier:
    def __init__(self,classes,proba):self.classes_=np.array(classes);self.proba=np.array(proba)
    def predict_proba(self,x):return self.proba

class Contracts(unittest.TestCase):
    def test_exact_zero(self):self.assertEqual(zero_labels([0,-0.,1e-20,2]).tolist(),[1,1,0,0])
    def test_negative_nonfinite_rejected(self):
        for a in ([-1],[np.nan],[np.inf]):
            with self.assertRaises(GateError):zero_labels(a)
    def test_raw_fallback(self):np.testing.assert_equal(raw_scale([np.nan,np.inf,0,-1,1,2]),[1,1,1,1,1,2])
    def test_strict_routing(self):
        p,r=route_prediction([8,9,10],[.44,.45,.46],.45);np.testing.assert_equal(p,[8,9,0]);np.testing.assert_equal(r,[False,False,True])
    def test_class_columns(self):
        np.testing.assert_equal(zero_probability(FakeClassifier([1,0],[[.7,.3]]),[[0]]),[.7])
    def test_one_class(self):
        for classes,expected in [([0],0),([1],1)]:np.testing.assert_equal(zero_probability(FakeClassifier(classes,[[1]]),[[0]]),[expected])
    def test_tau_formula(self):self.assertAlmostEqual(tau_from_folds([.2,.2,.2])[0],4/9)
    def test_tau_bad_folds(self):
        for x in ([.1,.2],[.1,np.nan,.2],[.1,-.2,.3]):
            with self.assertRaises(GateError):tau_from_folds(x)
    def test_inner_equal_fold_mean(self):self.assertAlmostEqual(tau_from_folds([.1,.2,.6])[1],.3)
    def test_unscaled_weight(self):
        f=pd.DataFrame({'WELL_ID':['synthetic_a']*12,'horizon':range(1,13),'RCYL':np.ones(12)});p=np.ones(12);p[0]=0
        s=numeric_summary(f,p);self.assertAlmostEqual(s['official_score'],100*(1-.5/(1+1e-6)))
    def test_conditional_positive_well_mean(self):
        f=pd.DataFrame({'WELL_ID':['synthetic_a']*12+['synthetic_b']*12,'horizon':list(range(1,13))*2,'RCYL':[1]*12+[0]*12});p=np.array([0.]*24)
        v,c=positive_inner_loss(f,p);self.assertAlmostEqual(v,1/(1+1e-6));self.assertEqual(c['positive_target_wells'],1)
    def test_decision_edges(self):
        self.assertEqual(decision(1,True),TABLE.splitlines()[3]);self.assertEqual(decision(1e-12,True),TABLE.splitlines()[4]);self.assertEqual(decision(0,True),TABLE.splitlines()[5]);self.assertEqual(decision(3,False),TABLE.splitlines()[2])
    def test_budget25(self):
        b=FitBudget()
        for _ in range(25):b.enter('model','inner_regressor');b.completed('model')
        with self.assertRaises(GateError):b.enter('model','inner_regressor')
    def test_preprocessing20(self):
        b=FitBudget()
        for _ in range(20):b.enter('preprocessor','inner_regressor');b.completed('preprocessor')
        with self.assertRaises(GateError):b.enter('preprocessor','inner_regressor')

if __name__=='__main__':unittest.main()
