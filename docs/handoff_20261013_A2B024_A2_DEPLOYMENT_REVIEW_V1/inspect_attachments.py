"""Inspect attached old/new ZIPs in memory; never extract identifiers or weights."""
import argparse,ast,csv,hashlib,io,json,math,re,zipfile
from datetime import datetime
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
def need(ok,msg):
    if not ok:raise RuntimeError(msg)
sha=lambda b:hashlib.sha256(b).hexdigest()
def zip_contents(path):
    b=Path(path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        need(z.testzip() is None,'ATTACHMENT_CRC');infos=z.infolist()
        need(sum(i.file_size for i in infos)<1_000_000_000,'ATTACHMENT_SIZE')
        need(len(infos)==len({i.filename.casefold() for i in infos}),'ATTACHMENT_DUPLICATE')
        for i in infos:
            p=PurePosixPath(i.filename);need(not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename and ':' not in i.filename,'ATTACHMENT_PATH')
        return {i.filename:z.read(i) for i in infos if not i.is_dir()},{'archive_sha256':sha(b),'bytes':len(b),'members':sum(not i.is_dir() for i in infos),'CRC_passed':True}
def result(path):
    members,summary=zip_contents(path);rows=[];values={};tokens=set();csvbytes={}
    for n,b in members.items():
        need('/' not in n and n.lower().endswith('.csv'),'RESULT_ROOT_FLAT_CSV')
        reader=csv.DictReader(io.StringIO(b.decode('utf-8-sig')))
        need(reader.fieldnames==['WELL_ID','NY','RCYL'],'RESULT_COLUMNS')
        local=list(reader);need(len(local)==12,'RESULT_WELL_MONTH_COUNT')
        ids={r['WELL_ID'] for r in local};need(len(ids)==1,'RESULT_CROSS_WELL')
        well=next(iter(ids));need(n==well+'.csv','RESULT_FILENAME')
        tokens.add(well);dates=[]
        for r in local:
            key=(well,r['NY']);need(key not in values,'RESULT_DUPLICATE_KEY')
            d=datetime.strptime(r['NY'],'%Y/%m/%d');dates.append(d)
            v=float(r['RCYL']);need(math.isfinite(v) and v>=0,'RESULT_FINITE_NONNEGATIVE')
            values[key]=v;rows.append((well,d,v));
        ix=[d.year*12+d.month-1 for d in dates];need(ix==list(range(ix[0],ix[0]+12)),'RESULT_CONSECUTIVE_MONTHS')
        csvbytes[well]=b
    summary.update({'wells':len(tokens),'rows':len(rows),'root_flat':True,'columns_correct':True,'all_values_finite_nonnegative':True,'all_windows_12_contiguous_months':True,
                    'canonical_padded_dates':all(re.fullmatch(r'\d{4}/\d{2}/\d{2}',r[1]) for r in values),
                    'per_well_or_per_value_outputs_saved':False})
    return summary,rows,values,tokens,csvbytes
def main(a):
    oldcode,oc=zip_contents(a.old_code);newcode,nc=zip_contents(a.new_code)
    old,orows,ov,ot,ob=result(a.old_result);new,nrows,nv,nt,nb=result(a.new_result)
    # Compare semantic keys as well as byte identity, so date padding is not mistaken for model change.
    oldmap={(w,d):v for w,d,v in orows};newmap={(w,d):v for w,d,v in nrows}
    common=set(oldmap)&set(newmap);different=sum(oldmap[k]!=newmap[k] for k in common)
    maxdiff=max((abs(oldmap[k]-newmap[k]) for k in common),default=0.)
    public=HERE/'deploy_bundle/source';matches=[];diffs=[]
    for n,b in newcode.items():
        if not n.endswith('.py'):continue
        p=public/n
        if p.is_file():
            (matches if p.read_bytes()==b else diffs).append(n)
    oldpy={n:b for n,b in oldcode.items() if n.endswith('.py')}
    newpy={n:b for n,b in newcode.items() if n.endswith('.py')}
    shared=set(oldpy)&set(newpy)
    changes={'old_python_files':len(oldpy),'new_python_files':len(newpy),'same_python_paths':len(shared),
             'unchanged_shared_python_paths':sorted(n for n in shared if oldpy[n]==newpy[n]),
             'changed_shared_python_paths':sorted(n for n in shared if oldpy[n]!=newpy[n]),
             'new_python_paths':sorted(set(newpy)-set(oldpy))}
    # Only inspect text metadata; never deserialize or execute attached model objects.
    models=[b for n,b in newcode.items() if PurePosixPath(n).suffix.lower() in {'.joblib','.pkl','.pickle'}]
    bclaims=json.loads((HERE/'sources/deploy/DEPLOYMENT_ACCEPTANCE_B.json').read_bytes())
    evidence={'signature':'账户A（新接手）独立审核与交付','old_code_user_confirmed_previous_version':True,'old_result_user_confirmed_previous_version':True,
        'old_code':oc,'new_code':nc,'old_result':old,'new_result':new,
        'new_code_matches_B_delivered_archive':nc['archive_sha256']==bclaims['code_zip']['sha256'],
        'new_result_matches_B_delivered_archive':new['archive_sha256']==bclaims['result_zip']['sha256'],
        'new_code_model_members':len(models),'new_model_bytes_match_B_identity':any(sha(b)==bclaims['model_sha256'] for b in models),
        'attached_models_deserialized_or_executed':False,
        'attached_new_python_matches_reviewed_public_files':matches,'attached_new_python_mismatches_reviewed_public_files':diffs,
        'code_change_summary':changes,
        'prediction_comparison':{'same_well_sets':ot==nt,'same_semantic_date_keys':set(oldmap)==set(newmap),'same_lexical_date_keys':set(ov)==set(nv),
            'comparable_rows':len(common),'changed_prediction_rows':different,'max_abs_prediction_change':maxdiff,
            'same_per_well_row_order_and_semantic_dates':[(w,d) for w,d,v in orows]==[(w,d) for w,d,v in nrows],
            'unchanged_csv_bytes_count':sum(w in nb and b==nb[w] for w,b in ob.items()),
            'same_result_zip_bytes':old['archive_sha256']==new['archive_sha256'],
            'individual_identifiers_values_or_hashes_not_reported':True},
        'known_private_identifiers_available_for_scan':len(ot|nt),'actual_original_data_access':False,'real_fits':0}
    out=HERE/'ATTACHMENT_COMPARISON_A2.json'
    with out.open('x',encoding='utf-8') as f:json.dump(evidence,f,ensure_ascii=False,indent=2)
    print(json.dumps(evidence,ensure_ascii=False))
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for x in ['old-code','old-result','new-code','new-result']:ap.add_argument('--'+x,required=True)
    main(ap.parse_args())
