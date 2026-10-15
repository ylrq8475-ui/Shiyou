"""Receive only fixed public handoff files; never request competition data."""
import base64
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "review_git"
INDEX = "322eb504e1050a6076ee270eb1af9109ddfce86b"
B = "a0e762a87352877dde179dc505797c0d1638a757"
PREFIX = "docs/handoff_20261015_A2B027_STAGE0_B_V1"
R4 = "b383fbc3cc7b4c5a382970ecd6234d7b2dcb3c47"
R4_SHA256 = "523dbf070126f03592e39714076a67ba4295837cf89f2317746b7c9c693a6e62"


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError("Public source identity changed")
    else:
        with path.open("xb") as stream:
            stream.write(payload)


def git(*args):
    result = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError("Fixed public Git tree unavailable")
    return result.stdout.decode("utf-8").strip()


def receive(item):
    label, commit, path = item
    name = PurePosixPath(path).name
    if len(commit) != 40 or PurePosixPath(path).suffix not in {".md", ".json", ".py", ".txt"}:
        raise RuntimeError("Non-public-data file type rejected")
    url = "https://raw.githubusercontent.com/ylrq8475-ui/Shiyou/" + commit + "/" + path
    target = ROOT / "sources" / label / name
    if label == "B" and name == "SYNTHETIC_LOG.txt":
        envelope = json.loads((ROOT / "exact_blob_envelope.json").read_bytes())
        payload = base64.b64decode(envelope["content"])
        target = ROOT / "sources_exact" / label / name
        save(target, payload)
    elif target.exists():
        payload = target.read_bytes()
    else:
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Account-A2-fixed-source-audit"}), timeout=25) as response:
                    payload = response.read()
                break
            except Exception:
                if attempt == 2:
                    raise
    sha = hashlib.sha256(payload).hexdigest()
    if label == "Claude" and name == "INSTRUCTION_ORIGINAL.md" and sha != R4_SHA256:
        raise RuntimeError("User-provided R4 SHA256 mismatch")
    save(target, payload)
    return {"label": label, "commit": commit, "path": path, "local": target.relative_to(ROOT).as_posix(),
            "bytes": len(payload), "sha256": sha,
            "git_blob": hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()}


def main():
    tree = git("ls-tree", "-r", B, "--", PREFIX).splitlines()
    blobs = {line.split("\t")[1]: line.split("\t")[0].split()[2] for line in tree}
    if not blobs:
        raise RuntimeError("No files in pinned B delivery")
    items = [("B", B, path) for path in blobs]
    items += [("index", INDEX, "LATEST.json")]
    items += [("Claude", R4, "docs/handoff_20261015_A2B027_CLAUDE_INSTRUCTIONS_R4/" + n) for n in ("INSTRUCTION_ORIGINAL.md", "SHA256SUMS.json")]
    items += [("rules", "0536eafab45b71ffd5f8f0160ee7957f1edd661d", "docs/handoff_20261014_THREE_ACCOUNT_PROMPTS_V3/" + n) for n in ("PROMPT_CODEX.md", "DELIVERY_REGISTRATION_RULES.md")]
    items += [("competition_rules", "8b112a767a3355a1ea208038915028ba4c4525e4", "docs/handoff_20261014_COMPETITION_RULES_A2_V1/" + n) for n in ("RULE_SOURCES.json", "RULE_COVERAGE.json")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(receive, items))
    if any(row["git_blob"] != blobs[row["path"]] for row in rows if row["label"] == "B"):
        raise RuntimeError("Pinned B Git blob identity mismatch")
    index = json.loads((ROOT / "sources/index/LATEST.json").read_bytes())
    entries = [entry for entry in index["entries"] if entry["role"] == "B" and entry["task"].startswith("A2B-027/")]
    if entries[-1]["commit"] != B:
        raise RuntimeError("Reviewed B is not newest A2B-027 B in pinned index")
    receipt = {"index_commit": INDEX, "B_commit": B, "B_prefix": PREFIX, "B_files": len(blobs),
               "R4_commit": R4, "R4_sha256_verified": True, "all_public_sources": len(rows),
               "B_git_blobs_match": True, "raw_data_read": False, "files": rows}
    save(ROOT / "SOURCE_RETRIEVAL_CODEX.json", (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({key: value for key, value in receipt.items() if key != "files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
