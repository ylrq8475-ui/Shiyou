"""Per-file public-input closure and pattern scan. Never opens competition data."""
import argparse,hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone,timedelta
PREFIX='docs/handoff_20261016_A2B031_B_NONEXECUTION_V1'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def scan(raw):
    text=raw.decode('utf-8-sig')
    patterns={'credentials':r'(?i)(?:gh[pousr]_[a-z0-9]{20,}|github_'+'pat_'+r'[a-z0-9_]{20,})','private_user_paths':r'(?i)(?:[CD]:[\\/]Users[\\/][a-z0-9_. -]+|wx'+'id_'+r'[a-z0-9_]{5,})','well_value_pattern':r'\b[A-Z]{2,8}\d{5,}\b','raw_well_month_csv_row':r'(?m)^\s*[A-Z]{2,8}\d{5,},\d{4}[-/]\d{1,2}'}
    counts={name:len(re.findall(pattern,text)) for name,pattern in patterns.items()}
    assert not any(counts.values()),'PRIVACY_PATTERN_HIT'
    return {'pattern_hits':counts,'result':'PASS'}
def main(a):
    folder=Path(a.directory);receipt=json.loads((folder/'SOURCE_RECEIPT.json').read_bytes())
    assert receipt['public_sources_only'] and not receipt['competition_data_read'] and not receipt['test_data_touched']
    for row in receipt['received']:
        if 'received_as' in row:
            content=(folder/row['received_as']).read_bytes();assert sha(content)==row['sha256'] and len(content)==row['bytes']
    metadata=['PRIVACY_COVERAGE_MAP.md','PRIVACY_SCAN_RAW.json','SHA256SUMS.json'];names=sorted(set(p.name for p in folder.iterdir() if p.is_file())|set(metadata))
    lines=['# 账户B逐文件隐私覆盖','', '所有输入均来自固定公开Git提交；本轮没有读取任何赛事原表、测试集、私有配置或权重。公开源字节由SOURCE_RECEIPT逐项绑定。其余文件为标准库生成的说明、匿名基准、零拟合计数和纯合成检查。','', '本次逐文件检查公开输入闭包、可疑凭据/私有路径/井标识符及逐行数据模式，不冒充私有标记穷尽匹配，不为扫描重读赛事数据。所有实际最终字节均扫描，无文件豁免。元数据自身不作循环自哈希，扫描记录由SHA清单绑定；清单自身由固定Git提交和外部回取凭证绑定。','', '| 文件路径 | 扫描记录 | 结果 |','|---|---|---|']
    ids={name:f'A031-PRIVACY-{i:03d}' for i,name in enumerate(names,1)}
    for name in names:lines.append(f'| `{PREFIX}/{name}` | `{ids[name]}` | PASS |')
    (folder/metadata[0]).write_bytes(('\n'.join(lines)+'\n').encode('utf-8'))
    records=[]
    for name in names:
        if name in metadata[1:]:records.append({'record_id':ids[name],'path':PREFIX+'/'+name,'sha256':None,'bytes':None,'identity_binding':'manifest/Git/external byte receipt; no fabricated self-hash','scan_scope':'exact final serialized bytes scanned before saving','pattern_hits':dict.fromkeys(['credentials','private_user_paths','well_value_pattern','raw_well_month_csv_row'],0),'result':'PASS'})
        else:
            content=(folder/name).read_bytes();records.append({'record_id':ids[name],'path':PREFIX+'/'+name,'sha256':sha(content),'bytes':len(content),'scan_scope':'exact original file bytes',**scan(content)})
    raw=encoded({'task':'A2B-031/nonexecution','role':'账户B执行与交付','time':datetime.now(timezone(timedelta(hours=8))).isoformat(),'public_input_closure_verified':True,'competition_data_or_private_markers_read':False,'test_data_read':False,'known_private_marker_exhaustiveness_claimed':False,'published_files':len(names),'scan_records':len(records),'exemptions':0,'all_pass':True,'records':records})
    checksums=[]
    for name in names:
        if name==metadata[2]:continue
        content=raw if name==metadata[1] else (folder/name).read_bytes();checksums.append({'path':PREFIX+'/'+name,'bytes':len(content),'sha256':sha(content)})
    manifest=encoded({'algorithm':'SHA256 original bytes','files':checksums,'self_exclusion':'own bytes bound by immutable Git commit and external verification, privacy scanned'})
    scan(raw);scan(manifest);(folder/metadata[1]).write_bytes(raw);(folder/metadata[2]).write_bytes(manifest)
    final=[]
    for name in names:
        content=(folder/name).read_bytes();scan(content);final.append({'path':PREFIX+'/'+name,'sha256':sha(content),'bytes':len(content),'privacy_result':'PASS'})
    Path(a.receipt).write_bytes(encoded({'files':final,'all_passed':True,'competition_data_read':False,'model_fits':0,'preprocessor_fits':0}))
    print(json.dumps({'files':len(final),'records':len(records),'all_passed':True,'competition_data_read':False,'model_fits':0,'preprocessor_fits':0}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--receipt',required=True);main(p.parse_args())
