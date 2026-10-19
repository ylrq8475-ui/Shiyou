"""Zero-fit R9 arithmetic and byte-column projection; no ML imports."""
import hashlib,json,math
from collections import Counter
import numpy as np
import pandas as pd

def require(ok,code):
    if not ok:raise RuntimeError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(x):return (json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def fingerprint(x):return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def csv_spans(raw,delimiter=44):
    """Yield byte spans. Unselected fields are never decoded or interpreted.

    This lexes CSV framing for projection only, not cell content. In particular
    it does not test missingness or numeric validity of an unselected cell.
    """
    start=i=0;quoted=False;spans=[]
    while i<len(raw):
        value=raw[i]
        if value==34:
            if quoted and i+1<len(raw) and raw[i+1]==34:i+=2;continue
            quoted=not quoted
        if not quoted and value in (delimiter,10,13):
            spans.append((start,i));start=i+1
            if value in (10,13):
                if value==13 and i+1<len(raw) and raw[i+1]==10:i+=1;start=i+1
                if len(spans)>1 or spans[0][1]>spans[0][0]:yield spans
                spans=[]
        i+=1
    require(not quoted,'UNTERMINATED_CSV_QUOTE')
    if start<len(raw) or spans:spans.append((start,len(raw)));yield spans
def cell(raw,span,encoding='utf-8-sig'):
    value=raw[span[0]:span[1]]
    if value.startswith(b'"'):require(value.endswith(b'"'),'BAD_SELECTED_QUOTE');value=value[1:-1].replace(b'""',b'"')
    return value.decode(encoding)
def header_and_rows(raw,delimiter):
    require(len(delimiter.encode())==1,'CSV_DELIMITER_UNSUPPORTED')
    rows=iter(csv_spans(raw,delimiter.encode()[0]));spans=next(rows)
    header=[cell(raw,s) for s in spans];require(len(header)==len(set(header)),'DUPLICATE_HEADER');return header,rows
def key_projection(raw,well,date,encoding,delimiter):
    header,rows=header_and_rows(raw,delimiter);wi,di=header.index(well),header.index(date);keys=[]
    for spans in rows:
        require(len(spans)==len(header),'CSV_WIDTH');keys.append((cell(raw,spans[wi],encoding),cell(raw,spans[di],encoding)))
    return keys,header
def permitted_test_history(raw,well,date,event,target,origin,encoding,delimiter):
    header,rows=header_and_rows(raw,delimiter);indexes={x:header.index(x) for x in (well,date,event,target)};out=[];skipped=0;decoded=Counter()
    for spans in rows:
        require(len(spans)==len(header),'CSV_WIDTH')
        date_value=cell(raw,spans[indexes[date]],encoding);decoded['key_date']+=1
        month=pd.Timestamp(date_value).to_period('M')
        if month>=origin:
            skipped+=1;continue  # never decode even WELL_ID/event/RCYL here
        wid=cell(raw,spans[indexes[well]],encoding);ev=cell(raw,spans[indexes[event]],encoding);value=cell(raw,spans[indexes[target]],encoding)
        decoded['prewindow_well']+=1;decoded['prewindow_event']+=1;decoded['prewindow_RCYL']+=1
        out.append((wid,month,ev,value))
    return out,{'test_window_rows_skipped_before_dynamic_cell_decode':skipped,'test_window_RCYL_decoded':0,'test_window_event_decoded':0,'test_window_other_dynamic_decoded':0,'decoded_cells':dict(decoded)}
def segments(months):
    out=[]
    for month in sorted(set(months)):
        if not out or month!=out[-1][1]+1:out.append([month,month])
        else:out[-1][1]=month
    return out
def distribution(values):return {str(k):int(v) for k,v in sorted(Counter(values).items())}
def modes(values):
    counts=Counter(values)
    if not counts:return []
    return sorted(k for k,v in counts.items() if v==max(counts.values()))
def alignment(test_pairs,train_pairs):
    ts,te=modes([x[0] for x in test_pairs]),modes([x[1] for x in test_pairs]);rs,re=modes([x[0] for x in train_pairs]),modes([x[1] for x in train_pairs])
    unique=all(len(x)==1 for x in (ts,te,rs,re));joint=sum(x==(ts[0],te[0]) for x in test_pairs) if len(ts)==len(te)==1 else None
    # Require the same test well to match both modal differences. Report the
    # marginal counts too so no ambiguity is hidden by a single percentage.
    match=bool(unique and ts==rs and te==re and joint>=8 and len(test_pairs)==10)
    return {'ALIGN_MATCH':match,'test_k_start_modes':ts,'test_k_end_modes':te,'train_k_start_modes':rs,'train_k_end_modes':re,'test_joint_modal_wells':joint,'test_start_modal_wells':sum(x[0] in ts for x in test_pairs),'test_end_modal_wells':sum(x[1] in te for x in test_pairs),'unique_modes':unique,'test_origin_threshold_denominator':10,'mode_consistency_definition':'same well matches BOTH unique marginal modes; >=8/10; ties are unresolved and do not get arbitrarily selected'}
def number(value):
    value=pd.to_numeric(value,errors='coerce');return float(value) if not pd.isna(value) and math.isfinite(float(value)) else None
def score(truth,predictions):
    y=np.asarray(truth,dtype=float);p=np.asarray(predictions,dtype=float)
    require(y.ndim==2 and y.shape[1]==12 and y.shape==p.shape and len(y)>0,'SCORE_SHAPE')
    require(np.isfinite(y).all() and np.isfinite(p).all() and (y>=0).all() and (p>=0).all(),'INVALID_SCORE_VALUES')
    losses=np.abs(y-p)/(np.abs(y)+np.abs(p)+1e-6)*np.power(.5,np.arange(1,13,dtype=float))
    perwell=100*(1-losses.sum(axis=1))
    return {'official_score':float(perwell.mean()),'well_count':len(y),'monthly_weighted_loss':{f'm1_to_{n}':float(losses[:,:n].sum(axis=1).mean()) for n in (1,2,4,12)},'weights':'2^-t, t=1..12; no renormalization; no leading 2','epsilon':1e-6,'aggregation':'calculate each well then equal mean; no row outputs persisted'}
def persistence(records,which):
    truth=[];prediction=[];excluded=Counter()
    for record in records:
        v=record[which]
        if v is None:excluded['missing_or_nonfinite_exact_month_RCYL']+=1;continue
        if v<0:excluded['negative_exact_month_RCYL']+=1;continue
        truth.append(record['truth']);prediction.append([v]*12)
    complete=len(truth)==len(records)
    return {'status':'COMPLETE' if complete else 'INCOMPLETE_NO_IMPUTATION','well_denominator':len(records),'valid_wells':len(truth),'excluded_counts':dict(excluded),'all_well_score':score(truth,prediction) if complete else None,'valid_subset_only':None if complete or not truth else score(truth,prediction),'imputation_or_latest_available_substitution':False}
