"""Independently verify aggregate identities, event order and public evidence."""
import ast
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
B=ROOT/'sources'/'B030';S=ROOT/'sources'/'shared_R5'
def read(folder,name):return json.loads((folder/name).read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
checks=[]
def check(name,ok):checks.append({'check':name,'passed':bool(ok)})
def close(a,b):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)

r=read(B,'RESULT_A2B030.json');r5=read(S,'RESULT_A2B028_029.json')
manifest=read(B,'SHA256SUMS.json');privacy=read(B,'PRIVACY_SCAN_RAW.json')
names={p.name for p in B.iterdir() if p.is_file()}
check('B030_exact_file_count',len(names)==26)
check('manifest_covers_all_other_files',{Path(x['path']).name for x in manifest['files']}==names-{'SHA256SUMS.json'})
for x in manifest['files']:
    path=B/Path(x['path']).name;check('manifest_original_bytes_'+path.name,path.stat().st_size==x['bytes'] and sha(path)==x['sha256'])
check('privacy_covers_every_file',{Path(x['path']).name for x in privacy['records']}==names and len(privacy['records'])==26)
for x in privacy['records']:
    name=Path(x['path']).name
    check('privacy_zero_counts_'+name,x['result']=='PASS' and not any(x['private_marker_hits'].values()) and x['credential_or_private_path_hits']==0)
    if x['sha256'] is not None:check('privacy_original_identity_'+name,sha(B/name)==x['sha256'] and (B/name).stat().st_size==x['bytes'])
    else:check('privacy_self_metadata_binding_'+name,name in {'PRIVACY_SCAN_RAW.json','SHA256SUMS.json'} and x['scan_method']=='same checker on exact final serialized bytes before persistence')
check('privacy_has_no_exemptions',privacy['exemptions']==0 and privacy['all_pass'] and privacy['published_files']==26)
lock=read(B,'IMPLEMENTATION_PREDIAGNOSTIC_LOCK.json')
check('actual_implementation_bound',lock['source_sha256']==sha(B/'diagnose_030.py'))
check('prior_plan_bound',lock['plan_sha256']==sha(B/'PLAN_R6.json'))
check('R6_exact_bytes',sha(B/'CLAUDE_INSTRUCTION_ORIGINAL_R6.md')=='e9c6da7c400bf5385f98b84b01a8e1ed3a7b8322dc0053c40e18a91c441ce5d5')
check('zero_budget',lock['model_fit_budget']==lock['preprocessor_fit_budget']==0)
check('aggregate_fit_counts',all(v==0 for v in r['fit_counts'].values()) and r['fit_counts']==read(B,'ZERO_FIT_COUNTS.json'))
events=read(S,'EVENTS.json')
event_lookup={e['event']:e for e in events if e['event'] in {'A030_N1_N2_completed_zero_fits','baseline_reproduced','A030_N4_completed_same_process_memory_zero_fits'}}
check('three_required_events',len(event_lookup)==3)
first=event_lookup['A030_N1_N2_completed_zero_fits'];base=event_lookup['baseline_reproduced'];done=event_lookup['A030_N4_completed_same_process_memory_zero_fits']
check('N1_N2_before_any_fit',all(v==0 for v in first['fit_counts'].values()))
check('N4_after_baseline_immediately',done['sequence']==base['sequence']+1)
check('N4_no_new_fit_delta',done['fit_counts']==base['fit_counts'] and done['fit_counts']['model_completed']==done['fit_counts']['preprocessor_completed']==5)
check('baseline_exact',base['score']==r5['B0_reproduced']==73.71410733861434)
provenance=read(B,'N4_MEMORY_PROVENANCE.json')
check('N4_event_file_identity',sha(S/'EVENTS.json')==provenance['origin_events_sha256'])
raw5=(S/'RESULT_A2B028_029.json').read_bytes()
variants={hashlib.sha256(raw5).hexdigest(),hashlib.sha256(raw5.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')).hexdigest()}
check('N4_original_result_hash_or_CRLF_equivalent',provenance['origin_result_sha256'] in variants)
check('N4_no_recovery_or_persistence',not provenance['row_OOF_saved'] and not provenance['new_OOF_recovery_fit_for_A030'] and provenance['retrospective_groups_not_used_in_selection'])
serial=read(B,'PUBLIC_RESULT_SERIALIZATION.json');original=(B/'RESULT_A2B030.json').read_bytes()
check('public_result_sha_bound',hashlib.sha256(original).hexdigest()==serial['public_result_SHA256'])
check('execution_result_CRLF_relation',hashlib.sha256(original.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')).hexdigest()==serial['original_execution_SHA256'])
check('N1_separate_aggregate_matches',r['N1']==read(B,'N1_MAPPING.json'))
check('N2_separate_aggregate_matches',r['N2']==read(B,'N2_COVERAGE.json'))
check('N1_counts_order',0<=r['N1']['single_event_unique_date_at_or_before_start_count']<=r['N1_date_consistent_train']<=r['N1_single_event_train']<=81)
check('N1_no_invented_B',r['N1_evidence_level']=='C' and r['N1']['B_evidence_found'] is False)
check('test_only_coverage',r['N1']['test_field_coverage_only']['used_in_decision'] is False and close(r['N1']['test_field_coverage_only']['fraction'],7/10))
check('test_target_not_read',r['test_label_columns_read']==0 and r['test_fields_read']==['WELL_ID','NY','CSLB'])
for row in r['N2']['coverage']:
    c=row['field'];check('N2_denominator_'+c,row['well_denominator']==81)
    for count,fraction in [('last_valid_count','last_valid_coverage'),('slope_valid_count','slope_valid_coverage'),('combo_both_valid_count','combo_coverage')]:
        check('N2_fraction_'+c+'_'+count,close(row[fraction],row[count]/81))
    check('N2_joint_bounded_'+c,row['combo_both_valid_count']<=min(row['last_valid_count'],row['slope_valid_count']))
    check('N2_threshold_'+c,row['combo_passed']==(row['combo_coverage']>=.8))
check('N2_combo_count',r['N2_combo_pass_count']==sum(row['combo_passed'] for row in r['N2']['coverage'])==2)
column_count=sum(row['last_valid_coverage']>=.8 for row in r['N2']['coverage'])+sum(row['slope_valid_coverage']>=.8 for row in r['N2']['coverage'])
check('N2_joint_and_single_trigger_agree',(column_count>=1)==(r['N2_combo_pass_count']>=1))
groups=r['N4']['groups'];partition=['上升','下降','稳产']
for n in (1,2,4,12):
    k='m1_to_'+str(n);total=sum(groups[g][k]['well_count']*groups[g][k]['mean_per_well_weighted_loss'] for g in partition)
    check('N4_partition_size_'+k,sum(groups[g][k]['well_count'] for g in partition)==81)
    check('N4_partition_share_'+k,close(sum(groups[g][k]['total_loss_contribution_share'] for g in partition),1.))
    check('N4_baseline_loss_'+k,close(total/81,r5['baseline_summary']['weighted_losses'][k]))
    for g,records in groups.items():
        item=records[k]
        check('N4_score_loss_'+g+'_'+k,close(item['mean_per_well_score'],100*(1-item['mean_per_well_weighted_loss'])))
        check('N4_contribution_'+g+'_'+k,close(item['total_loss_contribution_share'],item['well_count']*item['mean_per_well_weighted_loss']/total))
check('N4_global_score',close(sum(groups[g]['m1_to_12']['well_count']*groups[g]['m1_to_12']['mean_per_well_score'] for g in partition)/81,73.71410733861434))
check('N4_zero_overlay_labeled',r['N4']['contains_zero_is_overlapping_overlay'] and r['N4']['retrospective_truth_groups_not_features_routing_or_selection'])
check('N1_two_applicable_rows',r['N1_evidence_level']=='C' and r['N1_single_event_train']<40)
check('N1_not_in_prereg_trigger',not(r['N1_single_event_train']>=40 and r['N1_evidence_level'] in ['A','B']))
check('N2_trigger_unchanged',r['N2_combo_pass_count']>=1)
structure=read(S,'STRUCTURE_GATES.json')
check('folds_well_isolated',all(x['validation_well_intersection_all_events']==0 for x in structure['folds']))
check('five_validation_fold_sizes',sum(x['validation_wells'] for x in structure['folds'])==81 and len(structure['folds'])==5)
check('source_cutoffs_and_horizon',structure['history_cutoff']=='M-1' and structure['targets']=='M+1..M+12')
check('locked_split_identity',structure['split_sha256']=='beadb191d075afdd138d6463f0b3a0e03999a76e07641f56ea24ec77e5e4d5f8')
source=(S/'run_experiment.py').read_text(encoding='utf-8')
check('same_process_direct_finish_call','d030.finish(a.diagnostics_output,r030,y,pred);r030=None;' in source)
check('N4_only_after_baseline_gate',source.index("require(r['B0_reproduction_passed']")<source.index('d030.finish(a.diagnostics_output,r030,y,pred)'))
check('N4_not_assigned_to_model_inputs','r030[' not in source and 'r030.get(' not in source)
for name in ['diagnose_030.py','privacy_check.py','test_030.py']:
    compile((B/name).read_bytes(),name,'exec');check('B_compiles_'+name,True)
spec=importlib.util.spec_from_file_location('privacy_030',B/'privacy_check.py');scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
tokens={'well':{'SYNTH_IDENTIFIER_A'},'date':{'SYNTH_DATE_A'},'month':{'SYNTH_MONTH_A'},'candidate':{'SYNTH_CANDIDATE_A'},'plan_layer_strings':{'SYNTH_LAYER_A'}}
check('privacy_negative_control',scanner.scan(b'Anonymous method counts only',tokens)['result']=='PASS')
for group,values in tokens.items():
    try:scanner.scan((' '+next(iter(values))+' ').encode(),tokens);blocked=False
    except AssertionError:blocked=True
    check('privacy_positive_control_'+group,blocked)
original_plan=read(B,'PLAN_R6.json')
check('N2_joint_rule_preregistered','4 field combinations' in original_plan['N2_combo'] and 'both finite' in original_plan['N2_combo'])
result={'task':'A2B-030','B_commit':'a2bc8d4c02eba88bea2cb468a5478a4a5f0b18c9','check_count':len(checks),'passed':all(x['passed'] for x in checks),'checks':checks,'N2_joint_combinations_passed':r['N2_combo_pass_count'],'N2_single_columns_passed':column_count,'A_actual_model_fits':0,'A_actual_preprocessor_fits':0,'real_raw_data_read':False,'B_real_counts_and_memory_origin_not_independently_reexecuted':True,'private_marker_inventory_accessed':False}
with (ROOT/'AGGREGATE_AUDIT_CODEX.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['checks']},ensure_ascii=False))
if not result['passed']:print(json.dumps([x for x in checks if not x['passed']]));sys.exit(1)
