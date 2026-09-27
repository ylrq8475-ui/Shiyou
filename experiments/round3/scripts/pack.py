import zipfile, json, sys
from pathlib import Path
root=Path.home()/"work/repo"; variant=sys.argv[1]; out=Path(sys.argv[2])
roots=["README.md","pyproject.toml","requirements.txt","requirements-lock.txt","requirements-candidate-verified.txt","reproduce_candidate.py",
       "predict.py","train.py","infer.py","validate_submission.py","audit_data.py","package_delivery.py","reproduce_submission.py"]
files=[root/r for r in roots]+[root/"configs/default.yaml"]
files+=sorted((root/"scripts").glob("*.py"))+sorted((root/"src/oil_uplift").glob("*.py"))+sorted((root/"tests").glob("test_*.py"))
out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
    for f in files:
        info=zipfile.ZipInfo(f.relative_to(root).as_posix(),date_time=(2026,9,27,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,f.read_bytes())
    info=zipfile.ZipInfo("submission_variant.json",date_time=(2026,9,27,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(info,json.dumps({"variant":variant})+"\n")
names=zipfile.ZipFile(out).namelist()
bad=[n for n in names if n.startswith(("private_logs","models","configs/private","data/")) or n.endswith((".csv",".xlsx",".joblib",".zip"))]
assert not bad, bad
print(f"{out.name}: members={len(names)} bytes={out.stat().st_size}")
