"""Check attached code metadata/bytes only. Never unpickle models or save private content."""
import argparse,ast,csv,hashlib,io,json,re,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def main(a):
    with zipfile.ZipFile(a.new_code) as z:
        integrity=json.loads(z.read('INTEGRITY.json'));verified=0
        for n,expected in integrity['files'].items():assert sha(z.read(n))==expected;verified+=1
        assert integrity['status']=='R1_PLATFORM_EXPLORATION_ORIGINAL_CONFIRMATION_FAILED'
        roots=set(n for n in z.namelist() if '/' not in n)
        assert {'README.md','predict.py','requirements.txt'}<=roots
        code={n:z.read(n).decode('utf-8-sig') for n in z.namelist() if n.endswith('.py')}
        cli_names=[n for n,s in code.items() if 'argparse.ArgumentParser' in s and "if __name__" in s]
        root_entries=[n for n in cli_names if '/' not in n]
        complete_dual_arm_training_cli_present=any('fit' in code[n] and 'train' in n for n in root_entries)
        runtime={'python_version':integrity['python_version'],'versions':integrity['runtime_versions']}
        source_paths=sorted(code)
        old_entry_in_new='run_a2b013_safe_submission.py' in z.namelist()
    oldrows={};newrows={}
    for path,out in [(a.old_result,oldrows),(a.new_result,newrows)]:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                rr=list(csv.DictReader(io.StringIO(z.read(n).decode('utf-8-sig'))));out[rr[0]['WELL_ID']]=rr
    assert set(oldrows)==set(newrows)
    changed_dates=0;changed_prediction_lexemes=0
    for w in oldrows:
        for old,new in zip(oldrows[w],newrows[w]):
            assert old['WELL_ID']==new['WELL_ID']
            y,m,d=map(int,old['NY'].split('/'));assert new['NY']==f'{y:04d}/{m:02d}/{d:02d}'
            changed_dates+=old['NY']!=new['NY'];changed_prediction_lexemes+=old['RCYL']!=new['RCYL']
    result={'code_integrity_manifest_members_verified':verified,'code_has_root_contract':True,'code_under_5GB':Path(a.new_code).stat().st_size<5_000_000_000,
        'runtime_enforced_by_source':runtime,'runtime_server_compatibility_verified':False,'old_training_entry_in_new_package':old_entry_in_new,
        'root_CLI_entries':root_entries,'dual_arm_full_training_CLI_detected':complete_dual_arm_training_cli_present,
        'generic_training_library_included':'src/oil_uplift/training.py' in source_paths,
        'changed_date_lexemes_rows':changed_dates,'changed_prediction_lexemes_rows':changed_prediction_lexemes,
        'old_to_new_CSV_field_difference_only_date_padding':changed_dates==120 and changed_prediction_lexemes==0,
        'private_contents_or_model_values_saved':False,'model_deserializations':0,'real_fits':0}
    with (HERE/'PACKAGE_METADATA_A2.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['new-code','old-result','new-result']:p.add_argument('--'+n,required=True)
    main(p.parse_args())
