"""Original CSV parser and declared row order; only training history parsed."""
import hashlib, io, json, zipfile
from pathlib import Path, PurePosixPath
from route_b_core import require, fingerprint

def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def member_name(info):
    name=info.filename
    if not info.flag_bits&0x800:
        try:name=name.encode('cp437').decode('gb18030')
        except UnicodeError:pass
    name=name.replace('\\','/')
    require(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and ':' not in name,'UNSAFE_ARCHIVE_NAME')
    return name

class TrainingArchive:
    def __init__(self,archive,manifest):
        self.archive=Path(archive);self.manifest=Path(manifest)
        self.before={'archive':sha_file(self.archive),'manifest':sha_file(self.manifest)}
        self.zip=zipfile.ZipFile(self.archive,'r')
        infos=[i for i in self.zip.infolist() if not i.is_dir()]
        require(len(infos)==100 and sum(i.file_size for i in infos)<100_000_000,'RAW_INVENTORY_DRIFT')
        self.members={member_name(i):i for i in infos}
        require(len(self.members)==len(infos) and len({n.casefold() for n in self.members})==len(infos),'DUPLICATE_ARCHIVE_MEMBER')
        records=json.loads(self.manifest.read_bytes());require(records['file_count']==len(records['files'])==100,'MANIFEST_COUNT_DRIFT')
        self.declared={};used=set()
        for row in records['files']:
            rel=row['relative_path'].replace('\\','/')
            hits=[n for n in self.members if n==rel or n.endswith('/'+rel)]
            require(len(hits)==1 and hits[0] not in used,'MANIFEST_MEMBER_NOT_UNIQUE')
            raw=self.zip.read(self.members[hits[0]])
            require(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'RAW_MEMBER_IDENTITY_CHANGED')
            self.declared[rel]=hits[0];used.add(hits[0])
        require(len(used)==100,'UNLISTED_ARCHIVE_MEMBER')
        self.test_label_tables_parsed=0;self.test_prediction_rows_generated=0
    def load_train(self,config,table_type):
        import pandas as pd
        roles=config['data']['sources'];train=roles['train']['history']
        require(len(train)==88 and len(set(train))==88,'TRAIN_ROLE_DRIFT')
        train_names=[self.declared[x.replace('\\','/')] for x in train]
        test_names={self.declared[x.replace('\\','/')] for r in ('history','template') for x in roles['test'][r]}
        require(not set(train_names)&test_names,'TRAIN_TEST_SOURCE_OVERLAP')
        settings=config['data']['csv'];frames=[]
        for name in train_names:
            frames.append(pd.read_csv(io.BytesIO(self.zip.read(self.members[name])),encoding=settings.get('encoding','utf-8-sig'),sep=settings.get('delimiter',',')))
        require(all(list(f.columns)==list(frames[0].columns) for f in frames),'TRAIN_SCHEMA_DRIFT')
        self.role_hash=fingerprint(train_names)
        return table_type(pd.concat(frames,ignore_index=True),pd.DataFrame(),pd.DataFrame(),None)
    def unchanged(self):return self.before=={'archive':sha_file(self.archive),'manifest':sha_file(self.manifest)}
    def close(self):self.zip.close()
