"""Read-only Git/blob audit of imported source dependencies; never import them."""
import argparse, hashlib, io, json, pathlib, subprocess, zipfile

def run(repo,bundle,out):
    c='4ea326798ca1da0736cde4bc41f33b7ff8b58cf9'
    path='docs/handoff_20261010_A2B023_B/A2B023_READONLY_REVIEW_BUNDLE_v1.zip'
    data=subprocess.check_output(['git','show',f'{c}:{path}'],cwd=repo)
    lock=json.loads((bundle/'evidence/IMPLEMENTATION_PRETRAIN_LOCK.json').read_bytes())
    hashes=set(lock['source_inputs'].values());records=[]
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('BUNDLE_MANIFEST.json'))['files']
        for name,record in manifest.items():
            assert hashlib.sha256(z.read(name)).hexdigest()==record['sha256']
            assert len(z.read(name))==record['bytes']
        for name in z.namelist():
            if name.endswith('.py'):
                raw=z.read(name);digest=hashlib.sha256(raw).hexdigest()
                if digest in hashes:
                    records.append(dict(path=name,sha256=digest,bytes=len(raw)))
                    target=out/'upstream_sources'/name
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        old=json.loads(z.read('execution/FINAL_RESULT.json'))['research'][0]
        new=json.loads((bundle/'evidence/FIXED_REPLAY.json').read_bytes())
        errors=[]
        for arm in ('B0','C1'):
            for key in ('official_score','worst_fold','fold_std_ddof0'):
                errors.append(abs(old['arms'][arm][key]-new['arms'][arm][key]))
            for key in ('fold_scores','monthly_unweighted_relative_error','monthly_official_weighted_loss'):
                errors.extend(abs(x-y) for x,y in zip(old['arms'][arm][key],new['arms'][arm][key],strict=True))
        assert max(errors)<1e-10
    current=json.loads((bundle/'RUNTIME_SOURCE_BINDINGS.json').read_bytes())
    covered={r['sha256'] for r in records}|{r['sha256'] for r in current.values()}
    result=dict(source_commit=c,archive_path=path,archive_sha256=hashlib.sha256(data).hexdigest(),archive_manifest_entries=len(manifest),imported_source_matches=records,matched_current_and_upstream_distinct_hashes=len(covered),A23_fixed_replay_comparisons=len(errors),A23_fixed_replay_max_error=max(errors),remaining_source_inputs_without_matching_public_bytes=sum(h not in covered for h in lock['source_inputs'].values()),scope='Byte identity and aggregate replay consistency; no upstream module execution or private input reading')
    (out/'UPSTREAM_CHECK_A.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='imported_source_matches'}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=pathlib.Path,required=True);p.add_argument('--bundle',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();run(a.repo,a.bundle,a.out)
