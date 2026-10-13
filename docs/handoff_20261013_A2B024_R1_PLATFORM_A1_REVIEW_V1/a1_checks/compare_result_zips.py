"""A1 independent comparison of two platform result ZIPs.
Prints ONLY anonymous aggregates (no well IDs, dates or values).
Usage: python -I compare_result_zips.py OLD.zip NEW.zip
"""
import csv, datetime, hashlib, io, json, math, sys, zipfile

def load(path):
    rows, info = {}, {"members": 0, "bom": 0, "crlf": 0, "padded_dates": 0, "rows": 0, "order": []}
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name in z.namelist():
            assert "/" not in name and "\\" not in name and name.endswith(".csv")
            body = z.read(name); info["members"] += 1
            info["bom"] += body.startswith(b"\xef\xbb\xbf"); info["crlf"] += b"\r\n" in body
            r = csv.DictReader(io.StringIO(body.decode("utf-8-sig"), newline=""))
            assert r.fieldnames == ["WELL_ID", "NY", "RCYL"]
            for row in r:
                y, m, d = (int(x) for x in row["NY"].split("/"))
                day = datetime.date(y, m, d)
                info["padded_dates"] += len(row["NY"]) == 10
                key = (row["WELL_ID"], day.isoformat())
                assert key not in rows
                v = float(row["RCYL"]); assert math.isfinite(v) and v >= 0
                rows[key] = (v, row["RCYL"]); info["rows"] += 1; info["order"].append(key)
    return rows, info

def canonical_digest(rows, order):
    h = hashlib.sha256()
    for k in order:
        h.update(f"{k[0]},{k[1]},{rows[k][1]}\n".encode())
    return h.hexdigest()

old, oi = load(sys.argv[1]); new, ni = load(sys.argv[2])
same_keys = set(old) == set(new)
diffs = [abs(old[k][0] - new[k][0]) for k in old if k in new]
out = {
    "old": {k: v for k, v in oi.items() if k != "order"},
    "new": {k: v for k, v in ni.items() if k != "order"},
    "same_key_set_after_date_parsing": same_keys,
    "same_row_order_after_date_parsing": oi["order"] == ni["order"],
    "rcyl_lexeme_equal_rows": sum(old[k][1] == new[k][1] for k in old if k in new),
    "rcyl_max_abs_diff": max(diffs) if diffs else None,
    "canonical_prediction_digest_old": canonical_digest(old, oi["order"]),
    "canonical_prediction_digest_new": canonical_digest(new, ni["order"]),
}
out["predictions_identical"] = same_keys and out["rcyl_lexeme_equal_rows"] == len(old) == len(new)
print(json.dumps(out, indent=1))
