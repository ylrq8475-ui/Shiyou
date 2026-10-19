"""Per-file privacy evidence, including final serialized metadata; zero fitting.

Private markers stay in memory. Test CSVs are never parsed: identifier markers
are obtained from manifest filenames using training filename/identifier pairs.
"""
import argparse,csv,hashlib,io,json,re,zipfile
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone,timedelta
import yaml

def sha(x):return hashlib.sha256(x).hexdigest()
def encoded(x):return (json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def decode_name(inf):
    name=inf.filename
    if not inf.flag_bits&0x800:
        try:name=name.encode('cp437').decode('gb18030')
        except UnicodeError:pass
    return name.replace('\\','/')
def markers(archive,manifest,config):
    cfg=yaml.safe_load(Path(config).read_bytes());decl=json.loads(Path(manifest).read_bytes())
    tokens={'well':set(),'date':set(),'month':set(),'candidate':set()};styles=set()
    with zipfile.ZipFile(archive) as z:
        entries={decode_name(inf):inf for inf in z.infolist() if not inf.is_dir()};by_decl={}
        assert len(entries)==decl['file_count']==len(decl['files'])==100
        for row in decl['files']:
            rel=row['relative_path'].replace('\\','/');hits=[n for n in entries if n==rel or n.endswith('/'+rel)];assert len(hits)==1
            raw=z.read(entries[hits[0]]);assert len(raw)==row['bytes'] and sha(raw)==row['sha256'];by_decl[rel]=hits[0]
        well,date=cfg['anchors']['well_column'],cfg['anchors']['date_column'];settings=cfg['data']['csv']
        for filename in cfg['data']['sources']['train']['history']:
            rel=filename.replace('\\','/');raw=z.read(entries[by_decl[rel]]).decode(settings.get('encoding','utf-8-sig'));ids=set()
            for row in csv.DictReader(io.StringIO(raw),delimiter=settings.get('delimiter',',')):
                value=str(row[well]);ids.add(value);tokens['well'].add(value);d=str(row[date]);tokens['date'].add(d)
                match=re.match(r'^(\d{4})[-/](\d{1,2})',d);assert match;tokens['month'].add(f'{match[1]}-{int(match[2]):02d}')
            stem=PurePosixPath(rel).stem
            assert len(ids)==1,'TRAIN_FILENAME_HAS_MULTIPLE_WELLS'
            value=next(iter(ids));assert value in stem,'WELL_MARKER_NOT_BOUND_TO_FILENAME'
            i=stem.index(value);styles.add((stem[:i],stem[i+len(value):]))
        test_ids=set()
        for filename in cfg['data']['sources']['test']['history']:
            stem=PurePosixPath(filename.replace('\\','/')).stem;matches=set()
            for pre,suf in styles:
                if stem.startswith(pre) and stem.endswith(suf):
                    stop=len(stem)-len(suf) if suf else len(stem)
                    value=stem[len(pre):stop]
                    if value:matches.add(value)
            assert len(matches)==1,'TEST_IDENTIFIER_FILENAME_AMBIGUOUS'
            test_ids|=matches
        assert len(test_ids)==10 and len(tokens['well'])==88 and not tokens['well']&test_ids
        tokens['well']|=test_ids
    tokens['candidate']={str(x) for x in cfg['anchors']['eligible_event_values'] if isinstance(x,str) and len(x)>=2}
    return tokens
def scan(data,tokens):
    text=data.decode('utf-8-sig')
    # The authorized shape formula has implicit multiplication; recognize this
    # exact public arithmetic context, not an occurrence of a formation value.
    layer_text=text.replace('b<.9a','b<0.9*a').replace('b>1.1a','b>1.1*a')
    private={kind:sum(bool(re.search(r'(?<![\w])'+re.escape(token)+r'(?![\w])',layer_text if kind=='plan_layer_strings' else text)) for token in values if token) for kind,values in tokens.items()}
    generic=int(bool(re.search(r'(?i)(?:gh[pousr]_[a-z0-9]{20,}|github_'+'pat_'+r'[a-z0-9_]{20,}|C:[\\/]Users[\\/][a-z0-9_. -]+|wx'+'id_'+r'[a-z0-9_]{5,})',text)))
    assert sum(private.values())==generic==0,'PRIVACY_HIT_BLOCK_PUBLICATION'
    return {'private_marker_hits':private,'credential_or_private_path_hits':generic,'result':'PASS'}

def main(a):
    folder=Path(a.directory);prefix=a.repository_directory.rstrip('/')
    inputs={'archive':a.archive,'manifest':a.manifest,'config':a.config}
    before={k:sha(Path(p).read_bytes()) for k,p in inputs.items()}
    tokens=markers(a.archive,a.manifest,a.config)
    meta={'PRIVACY_SCAN_RAW.json','SHA256SUMS.json','PRIVACY_COVERAGE_MAP.md'}
    names=sorted([p.name for p in folder.iterdir() if p.is_file() and p.name not in meta]+list(meta))
    assert len(names)==len(set(names))
    ids={n:f'A033FIX01-PRIVACY-{i:03d}' for i,n in enumerate(names,1)}
    coverage='# A2B-033-R11-FIX-01 逐文件隐私覆盖\n\n账户B执行与交付。每份发布文件含最终元数据均扫描，无豁免。只发布文档、差异、匿名身份和检查证据。新版正式ZIP、私有配置、result.zip、权重和逐井值不发布。\n\n标记仅在内存，沿用已授权的赛事归档/清单/配置读取；不解析任何测试CSV，也不加载模型。数值原值不是可穷尽正则集合，发布清单和数据流人工复核共同约束匿名范围。\n\n| 文件 | 扫描记录 | 结果 |\n|---|---|---|\n'+'\n'.join('| `'+prefix+'/'+n+'` | `'+ids[n]+'` | PASS，私有标记/凭据命中0 |' for n in names)+'\n\n扫描原始JSON及SHA清单的最终序列化字节也由同一扫描函数检查。扫描JSON自身摘要由SHA清单绑定；SHA清单自身由Git与外部回取凭证绑定，不伪造循环自哈希。两个元数据记录的sha256/bytes为null，只是身份绑定位置说明，不是扫描豁免。\n'
    (folder/'PRIVACY_COVERAGE_MAP.md').write_bytes(coverage.encode())
    records=[]
    for name in names:
        if name in ('PRIVACY_SCAN_RAW.json','SHA256SUMS.json'):
            records.append({'record_id':ids[name],'path':prefix+'/'+name,'sha256':None,'bytes':None,'binding':'scan JSON bound by SHA manifest; manifest by fixed Git and external remote verification','private_marker_hits':dict.fromkeys(tokens,0),'credential_or_private_path_hits':0,'result':'PASS','scan_method':'exact final serialized bytes before persistence'})
        else:
            raw=(folder/name).read_bytes();records.append({'record_id':ids[name],'path':prefix+'/'+name,'sha256':sha(raw),'bytes':len(raw),'scan_method':'exact existing original bytes',**scan(raw,tokens)})
    evidence={'task':'A2B-033-R11-FIX-01','role':'账户B执行与交付','published_files':len(names),'scan_records':len(records),'all_pass':True,'exemptions':0,'model_fits':0,'preprocessor_fits':0,'test_CSVs_parsed':0,'model_weights_loaded':False,'marker_counts':{k:len(v) for k,v in tokens.items()},'records':records}
    raw_bytes=encoded(evidence)
    checksum=[]
    for n in names:
        if n=='SHA256SUMS.json':continue
        data=raw_bytes if n=='PRIVACY_SCAN_RAW.json' else (folder/n).read_bytes()
        checksum.append({'path':prefix+'/'+n,'sha256':sha(data),'bytes':len(data)})
    hash_bytes=encoded({'algorithm':'SHA256 original bytes','files':checksum,'self_exclusion':'own digest bound by fixed Git blob and remote byte receipt; own final bytes privacy scanned'})
    assert scan(raw_bytes,tokens)['result']==scan(hash_bytes,tokens)['result']=='PASS'
    (folder/'PRIVACY_SCAN_RAW.json').write_bytes(raw_bytes);(folder/'SHA256SUMS.json').write_bytes(hash_bytes)
    for n in names:assert scan((folder/n).read_bytes(),tokens)['result']=='PASS'
    assert before=={k:sha(Path(p).read_bytes()) for k,p in inputs.items()}
    Path(a.receipt).write_bytes(encoded({'files':[{'path':prefix+'/'+n,'sha256':sha((folder/n).read_bytes()),'bytes':(folder/n).stat().st_size,'privacy_result':'PASS'} for n in names],'all_files_including_metadata_scanned':True,'test_labels_read':False,'models_fit':0,'preprocessors_fit':0,'raw_inputs_unchanged':True}))
    print(json.dumps({'published_files':len(names),'privacy_records':len(records),'all_passed':True,'model_fits':0,'preprocessor_fits':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('directory','repository-directory','archive','manifest','config','receipt'):p.add_argument('--'+n,required=True)
    main(p.parse_args())
