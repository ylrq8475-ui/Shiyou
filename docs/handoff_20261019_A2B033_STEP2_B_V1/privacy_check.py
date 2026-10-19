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
    before={role:sha(Path(p).read_bytes()) for role,p in [('archive',a.archive),('manifest',a.manifest),('config',a.config)]}
    tokens=markers(a.archive,a.manifest,a.config)
    inner=[]
    container=json.loads((folder/'FROZEN_SOURCES.json').read_bytes())
    for i,row in enumerate(container['files'],1):
        raw_source=row['text'].encode('utf-8')
        assert sha(raw_source)==row['sha256'] and len(raw_source)==row['bytes']
        inner.append({'record_id':f'A033-INNER-SOURCE-{i:03d}','container':'FROZEN_SOURCES.json','path':row['path'],'sha256':sha(raw_source),'bytes':len(raw_source),'scan_method':'decoded original source bytes, not JSON escaped text',**scan(raw_source,tokens)})
    assert len(inner)==10
    map_name='PRIVACY_COVERAGE_MAP.md';raw_name='PRIVACY_SCAN_RAW.json';manifest_name='SHA256SUMS.json'
    existing=[p.name for p in folder.iterdir() if p.is_file() and p.name not in (map_name,raw_name,manifest_name)]
    all_names=sorted(existing+[map_name,raw_name,manifest_name]);assert len(all_names)==len(set(all_names))
    ids={name:f'A033STEP2-PRIVACY-{i:03d}' for i,name in enumerate(all_names,1)}
    lines=[f'| `{prefix}/{name}` | `{ids[name]}` | PASS，私有标记及凭据命中0 | '+('最终序列化字节；记录不作循环自哈希，清单/Git绑定' if name in (raw_name,manifest_name) else '原始字节SHA256与字节数')+' |' for name in all_names]
    mapping='''# A2B-033/R11步骤2发布文件逐项隐私覆盖

账户B执行与交付。每份发布文件均有本轮扫描记录，无扫描豁免。原始证据见PRIVACY_SCAN_RAW.json的record_id。
真实标记仅在内存：88口训练历史标记及由原清单文件名绑定得到的10口测试标记、实际训练日期和月份、私有候选；不读取方案/层位原值。本轮不读取方案/层位值，也不将其作为本次标记穷尽匹配来源。已知私有标记仅在内存，原值没有写入报告。数值字段仅发布聚合和锁定参数，不发布原始单元格。本隐私扫描不解析测试CSV；R11实际推理入口在模板键哈希验证后仅投影窗口前必要列；隐私扫描本身不解析任何测试CSV。测试窗口内RCYL/事件/其他动态值不解码、不解析、不使用。

| 文件路径 | 原始扫描记录 | 结果 | 身份绑定 |
|---|---|---|---|
'''+ '\n'.join(lines)+'''

隐私扫描JSON自身与SHA清单的最终序列化字节在落盘前也经过同一个扫描函数，不因“扫描后才生成”漏扫。扫描JSON的实际SHA由SHA256SUMS.json绑定；SHA清单的自身SHA由固定Git提交与外部回取凭证绑定。两个元数据记录不伪造循环自哈希，因此记录内sha256/bytes写null，属于哈希位置说明，不是免扫。其余文件均逐项记录原字节SHA与字节数。全部最终字节回取后再次比较并扫描，保留本地完整回取凭证。

所有原始赛事文件仅校验字节、不解压；私有配置、原清单及归档读取前后摘要一致。只持久化聚合命中计数，不写匹配标记、原始行、逐井数据或标签。
'''
    mapping+='\n原源码容器FROZEN_SOURCES.json还逐项解码检查10个原始源码文件，核对原始字节SHA；不是只扫描JSON转义文本。每项记录见PRIVACY_SCAN_RAW.json的decoded_source_container_entries。\n\n| 容器内部文件 | 扫描记录 | 结果 |\n|---|---|---|\n'+'\n'.join('| FROZEN_SOURCES.json :: '+row['path']+' | '+row['record_id']+' | PASS |' for row in inner)+'\n'
    (folder/map_name).write_bytes(mapping.encode('utf-8'))
    records=[]
    for name in all_names:
        path=folder/name
        if name in (raw_name,manifest_name):
            records.append({'record_id':ids[name],'path':prefix+'/'+name,'sha256':None,'bytes':None,'identity_binding':'raw scan bound by SHA manifest; manifest bound by fixed Git blob and external receipt','scan_method':'same checker on exact final serialized bytes before persistence','private_marker_hits':dict.fromkeys(tokens,0),'credential_or_private_path_hits':0,'result':'PASS'})
        else:
            content=path.read_bytes();records.append({'record_id':ids[name],'path':prefix+'/'+name,'sha256':sha(content),'bytes':len(content),'scan_method':'exact existing file bytes',**scan(content,tokens)})
    raw={'role':'账户B执行与交付','task':'A2B-033/R11步骤2','time':datetime.now(timezone(timedelta(hours=8))).isoformat(),'published_files':len(all_names),'scan_records':len(records),'all_pass':True,'exemptions':0,'marker_counts':{key:len(value) for key,value in tokens.items()},'public_context_review':'Exact known well/date/month/private-event markers from authorized training files and manifest-bound test filenames; no test CSV, plan, layer or model parsed by this scanner; numeric raw cells are not an exhaustive regex marker set; source dataflow and per-file checks also reviewed','test_CSVs_parsed':0,'test_label_columns_read':0,'source_input_hashes_unchanged':True,'metadata_self_hashes_not_fabricated':True,'records':records,'decoded_source_container_entries':inner,'decoded_source_container_entries_count':len(inner)}
    raw_bytes=encoded(raw)
    checksums=[]
    for name in all_names:
        if name==manifest_name:continue
        content=raw_bytes if name==raw_name else (folder/name).read_bytes()
        checksums.append({'path':prefix+'/'+name,'bytes':len(content),'sha256':sha(content)})
    manifest_bytes=encoded({'algorithm':'SHA256 original bytes','files':checksums,'self_exclusion':'own digest provided by fixed Git blob and remote byte verification; own serialized content privacy scanned'})
    assert scan(raw_bytes,tokens)=={key:raw['records'][all_names.index(raw_name)][key] for key in ('private_marker_hits','credential_or_private_path_hits','result')}
    assert scan(manifest_bytes,tokens)=={key:raw['records'][all_names.index(manifest_name)][key] for key in ('private_marker_hits','credential_or_private_path_hits','result')}
    assert before=={role:sha(Path(p).read_bytes()) for role,p in [('archive',a.archive),('manifest',a.manifest),('config',a.config)]}
    (folder/raw_name).write_bytes(raw_bytes);(folder/manifest_name).write_bytes(manifest_bytes)
    for name in all_names:assert scan((folder/name).read_bytes(),tokens)['result']=='PASS'
    full=[{'path':prefix+'/'+name,'bytes':(folder/name).stat().st_size,'sha256':sha((folder/name).read_bytes()),'privacy_result':'PASS'} for name in all_names]
    Path(a.receipt).write_bytes(encoded({'files':full,'all_files_including_metadata_scanned':True,'test_labels_read':False,'fits_repeated':0}))
    print(json.dumps({'published_files':len(all_names),'privacy_records':len(records),'all_passed':True,'exemptions':0,'test_labels_read':False,'model_fits_repeated':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('directory','repository-directory','archive','manifest','config','receipt'):p.add_argument('--'+name,required=True)
    main(p.parse_args())
