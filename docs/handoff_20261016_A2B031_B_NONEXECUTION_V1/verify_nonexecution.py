"""Offline verification of public R7 nonexecution evidence. Standard library only."""
import argparse,hashlib,json,unittest
from pathlib import Path
def selected(q1,q2):
    allowed1,allowed2=q1=='允许',q2=='允许'
    if allowed1 and allowed2:return ['B0_G','B0_G_D']
    if allowed1:return ['B0_G']
    if allowed2:return ['B0_D']
    return []
def verify(folder):
    folder=Path(folder);read=lambda n:json.loads((folder/n).read_bytes())
    receipt=read('SOURCE_RECEIPT.json')
    for item in receipt['received']:
        if 'received_as' in item:
            raw=(folder/item['received_as']).read_bytes()
            assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    source=read('RECEIVED_CODEX_RESULT_031.json');result=read('RESULT_A2B031.json');plan=read('PREREG_A2B031.json');counts=read('FIT_COUNTS.json')
    assert source['Claude_instruction_commit']==result['Claude_instruction_commit']=='be03e6caeb6b70278c8e5a137b178130700aab72'
    assert result['Codex_compliance_commit']=='87df63be2287f6c8175146423ca01056e027afa1'
    q1,q2=(source['questions'][q]['decision'] for q in ('Q1','Q2'))
    assert selected(q1,q2)==result['enabled_configs']==plan['enabled_configs']==[]
    assert result['enabled_config_count']==0 and source['execution_configs_allowed']==[]
    assert counts and all(isinstance(x,int) and x==0 for x in counts.values()) and result['fit_counts']==counts
    assert plan['current_enabled_model_budget']==plan['current_enabled_preprocessor_budget']==0
    assert not result['new_scores_generated'] and result['candidates']==[]
    assert result['G_train_coverage'] is None and result['D_train_coverage'] is None
    assert not result['baseline_retrained'] and not result['competition_data_read'] and not result['test_data_read']
    assert all(result[k] is None for k in ('best_score','delta','paired_fold_deltas','positive_folds','worst_fold','weighted_losses'))
    assert all(result['hard_gates'][k]=='UNKNOWN' for k in ('泄漏','错位','井级隔离','指标'))
    return {'verified':True,'Q1':q1,'Q2':q2,'enabled_configs':0,'model_fits':0,'preprocessor_fits':0,'competition_data_read':False}
class RoutingChecks(unittest.TestCase):
    def test_both(self):self.assertEqual(selected('允许','允许'),['B0_G','B0_G_D'])
    def test_geology(self):self.assertEqual(selected('允许','UNKNOWN'),['B0_G'])
    def test_design(self):self.assertEqual(selected('UNKNOWN','允许'),['B0_D'])
    def test_unknown(self):self.assertEqual(selected('UNKNOWN','UNKNOWN'),[])
    def test_denied(self):self.assertEqual(selected('不允许','不允许'),[])
    def test_unknown_denied(self):self.assertEqual(selected('UNKNOWN','不允许'),[])
    def test_baseline_arithmetic(self):
        folds=[71.45331390948151,77.53642908897099,75.12924056181325,64.62686399621428,79.96598872591244]
        self.assertAlmostEqual(sum(s*n for s,n in zip(folds,[17,16,16,16,16]))/81,73.71410733861434,places=12)
    def test_offline_package(self):self.assertTrue(verify(FOLDER)['verified'])
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',default=str(Path(__file__).resolve().parent));a=parser.parse_args();FOLDER=Path(a.directory)
    outcome=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RoutingChecks))
    if not outcome.wasSuccessful():raise SystemExit(2)
    print(json.dumps(verify(FOLDER),ensure_ascii=True))
