"""Independent read-only boundary audit; no B imports, model fits, or row output."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import math
import os
from pathlib import Path
import sys

def month_number(value):
    parts=str(value).strip().split("T")[0].split(" ")[0].replace("/","-").split("-")
    if len(parts) not in (2,3):
        raise ValueError("Invalid calendar month")
    year,month=int(parts[0]),int(parts[1])
    dt.date(year,month,int(parts[2]) if len(parts)==3 else 1)
    return year*12+month-1

def last_segment(months):
    if not months:
        raise ValueError("No eligible event")
    ordered=sorted(set(months)); start=end=ordered[-1]
    for item in reversed(ordered[:-1]):
        if item != start-1:
            break
        start=item
    return start,end

def target_months(months,interpretation):
    start,end=last_segment(months)
    anchors={"latest_segment_end":end,"latest_independent_record":max(months),"latest_segment_start":start}
    if interpretation not in anchors:
        raise ValueError("Unknown interpretation")
    return tuple(anchors[interpretation]+offset for offset in range(1,13))

def before_month(rows,first_excluded):
    return tuple(row for row in rows if row[0]<first_excluded)

def unique_month_map(rows,date_column):
    result={}
    for row in rows:
        month=month_number(row[date_column])
        if month in result:
            raise ValueError("Duplicate well-month")
        result[month]=row
    return result

def finite_nonnegative(value):
    try:
        number=float(value)
        return math.isfinite(number) and number>=0
    except (TypeError,ValueError):
        return False

def read_role(config,split,role):
    root=Path(config["data"]["input_dir"]); opts=config["data"].get("csv",{})
    rows=[]; header=None
    for relative in config["data"]["sources"][split][role]:
        with (root/relative).open(encoding=opts.get("encoding","utf-8-sig"),newline="") as stream:
            reader=csv.DictReader(stream,delimiter=opts.get("delimiter",","))
            if header is None:
                header=reader.fieldnames
            if reader.fieldnames != header:
                raise ValueError("Inconsistent declared schema")
            rows.extend(reader)
    if not rows:
        raise ValueError("Empty declared role")
    return rows

def audit(config_path):
    import yaml
    config=yaml.safe_load(config_path.read_text(encoding="utf-8")); anchor=config["anchors"]
    well,date,event=(anchor[key] for key in ("well_column","date_column","event_column"))
    eligible=set(anchor["eligible_event_values"]); groups={}; events={}
    for split in ("train","test"):
        local={}
        for row in read_role(config,split,"history"):
            local.setdefault(row[well],[]).append(row)
        groups[split]={key:unique_month_map(rows,date) for key,rows in local.items()}
        events[split]={key:[month for month,row in rows.items() if row[event] in eligible] for key,rows in groups[split].items()}
    if set(groups["train"]) & set(groups["test"]):
        raise ValueError("Train/test overlap")
    complete=[]
    for key,months in events["train"].items():
        if all(m in groups["train"][key] and finite_nonnegative(groups["train"][key][m]["RCYL"]) for m in target_months(months,"latest_segment_end")):
            complete.append(key)
    templates={}
    for row in read_role(config,"test","template"):
        if not finite_nonnegative(row.get("RCYL")):
            templates.setdefault(row[well],[]).append(row)
    if set(templates)!=set(groups["test"]):
        raise ValueError("Template cohort changed")
    for key,rows in templates.items():
        if tuple(sorted(unique_month_map(rows,date)))!=target_months(events["test"][key],"latest_segment_end"):
            raise ValueError("Template window changed")
    for split in ("train","test"):
        for months in events[split].values():
            if target_months(months,"latest_segment_end")!=target_months(months,"latest_independent_record"):
                raise ValueError("Observational equivalence falsified")
    counts={"train_history_wells":len(groups["train"]),"complete_train_wells":len(complete),"test_wells":len(templates),"test_rows":sum(map(len,templates.values())),"train_test_overlap":0}
    if counts!={"train_history_wells":88,"complete_train_wells":81,"test_wells":10,"test_rows":120,"train_test_overlap":0}:
        raise ValueError("Frozen cohort changed")
    sensitivity={}
    for split,keys in (("train",complete),("test",list(templates))):
        changed=removed=0
        for key in keys:
            start,end=last_segment(events[split][key]); changed+=start!=end
            removed+=sum(start<=month<end for month in groups[split][key])
        sensitivity[split]={"wells_examined":len(keys),"wells_with_stricter_segment_start_cutoff":changed,"record_rows_between_segment_start_and_end":removed}
    return {"audit_id":"A-015-01-SELFVALIDATION-20261009","checks_passed":True,"cohort":counts,
        "observational_equivalence":{"history_wells_checked":sum(len(g) for g in groups.values()),"different_anchors_or_target_windows":0,"interpretations_distinguished_by_monthly_data":False},
        "cutoff_sensitivity":sensitivity,"data_inferred_output_rule":"latest eligible record month plus one, exact official template keys",
        "existing_rules_matrix_reused":True,"event_semantics_status":"UNKNOWN","forecast_time_status":"UNKNOWN","official_compliance_proven":False,
        "model_fit_calls":0,"candidate_model_saves":0,"ZIP_generated":False,"platform_uploaded":False,"row_level_outputs_written":False}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True,type=Path,help="Authorized private local config; never commit it")
    args=parser.parse_args()
    try:
        if os.environ.get("COMPETITION_DATA_ACCESS_ACK")!="I_AM_AUTHORIZED":
            raise PermissionError("Raw data access not acknowledged")
        if sys.version_info[:3]!=(3,13,7):
            raise RuntimeError("Registered Python version required")
        print(json.dumps(audit(args.config),ensure_ascii=True,sort_keys=True))
    except Exception as exc:
        # Do not expose a private filename/date/value in tracebacks.
        print(json.dumps({"audit_id":"A-015-01-SELFVALIDATION-20261009","checks_passed":False,"error_type":type(exc).__name__},sort_keys=True))
        sys.exit(1)
