"""Read-only, zero-fit training OOF diagnostics. Never accepts test data."""
from r14 import *
import itertools,math

def weights(panel,pred):
    require('RCYL' in panel and len(panel)==len(pred) and (panel.groupby('WELL_ID',sort=False).horizon.agg(list).map(lambda x:x==list(range(1,13)))).all(),'ERROR_BUDGET_TRAIN_OOF_SHAPE')
    y=panel.RCYL.to_numpy(float);p=np.asarray(pred,float)
    require(np.isfinite(y).all() and (y>=0).all() and np.isfinite(p).all() and (p>=0).all(),'ERROR_BUDGET_FINITE_NONNEGATIVE')
    e=p-y;return np.abs(e)/(np.abs(p)+np.abs(y)+1e-6)*2.**(-panel.horizon.to_numpy(float)),e

def group_labels(panel,metadata,folds):
    require(metadata.WELL_ID.is_unique and set(metadata.WELL_ID)==set(panel.WELL_ID),'GROUP_METADATA_COHORT')
    m=metadata.set_index('WELL_ID');assigned={};rules=[]
    for k,(tr,va) in enumerate(folds,1):
        train=list(dict.fromkeys(panel.iloc[tr].WELL_ID));valid=list(dict.fromkeys(panel.iloc[va].WELL_ID));require(not set(train)&set(valid),'GROUP_CUTPOINT_OVERLAP')
        v=m.loc[train,'production_level'].to_numpy(float);v=v[np.isfinite(v)]
        require(len(v)>0,'EMPTY_TRAIN_PRODUCTION_QUANTILES');lo,hi=np.quantile(v,[1/3,2/3])
        # Numeric cutpoints stay in memory; publish definitions and support counts.
        rules.append({'fold':k,'cutpoints_source':'outer training wells only; legal-history mean nonnegative finite RCYL tertiles','training_wells':len(train),'validation_wells':len(valid),'outer_validation_used_for_cutpoints':0})
        for wid in valid:
            r=m.loc[wid];level=r.production_level;ratio=r.M_ratio;days=r.M_SCTS_fraction
            assigned[wid]={'production_tertile':'missing' if not np.isfinite(level) else ('low' if level<=lo else 'middle' if level<=hi else 'high'), 'M_anomaly':'missing' if not np.isfinite(ratio) else 'below_0.5' if ratio<.5 else '0.5_to_2' if ratio<=2 else 'above_2','M_operating_fraction':'missing' if not np.isfinite(days) else 'below_0.8' if days<.8 else 'other','scale_fallback':'fallback' if r.scale_fallback else 'positive_raw_scale'}
    require(set(assigned)==set(panel.WELL_ID),'GROUP_OOF_COVERAGE');return assigned,rules

def budget(panel,pred,metadata,folds):
    w,e=weights(panel,pred);n=panel.WELL_ID.nunique();total=float(w.sum()/n);h=panel.horizon.to_numpy();periods={}
    require(abs(total-(1.-old.summary(panel,pred)['official_score']/100.))<1e-12,'ERROR_BUDGET_OFFICIAL_MISMATCH')
    for name,mask in [('month1',h==1),('month2',h==2),('months3_4',(h>=3)&(h<=4)),('months5_12',h>=5)]:
        v=float(w[mask].sum()/n);periods[name]={'weighted_loss':v,'fraction_of_total_loss':v/total if total>0 else None}
    directions={}
    for name,mask in [('month1',h==1),('month2',h==2),('full',h>0)]:
        directions[name]={d:float(w[mask&sgn].sum()/n) for d,sgn in [('over_prediction',e>0),('under_prediction',e<0)]}
    labels,rules=group_labels(panel,metadata,folds);groups={}
    for field in next(iter(labels.values())):
        support={name:{wid for wid,r in labels.items() if r[field]==name} for name in {r[field] for r in labels.values()}}
        if any(len(members)<5 for members in support.values()):
            groups[field]=[{'status':'SUPPRESSED_FAMILY_LT5','reason':'prevent reconstruction of a small remainder from cohort totals'}]
            continue
        groups[field]=[]
        for name,members in sorted(support.items()):
            count=len(members)
            if count<5:groups[field].append({'group':name,'status':'SUPPRESSED_LT5','wells':'<5'});continue
            mask=panel.WELL_ID.isin(members).to_numpy();sumloss=float(w[mask].sum())
            groups[field].append({'group':name,'status':'REPORTED','wells':count,'group_mean_weighted_loss':sumloss/count,'contribution_to_total_loss':sumloss/n,'fraction_of_total_loss':sumloss/(total*n) if total else None})
    perwell=pd.Series(w).groupby(panel.WELL_ID.to_numpy(),sort=False).sum().to_numpy();top=math.ceil(.1*n)
    return {'wells':n,'total_weighted_loss':total,'horizon_buckets':periods,'direction_contributions':directions,'groups':groups,'cutpoint_evidence':rules,'group_members_vary_across_repeat_splits':True,'top10pct_wells':top,'top10pct_loss_fraction':float(np.sort(perwell)[-top:].sum()/perwell.sum()) if perwell.sum() else None,'fits':{'model':0,'preprocessor':0},'scope':'training OOF only; no test features or distributions'}

def pairs(panel,predictions):
    out=[]
    for a,b in itertools.combinations(sorted(predictions),2):
        pa,pb=predictions[a],predictions[b];_,ea=weights(panel,pa);_,eb=weights(panel,pb)
        cor=float(np.corrcoef(ea,eb)[0,1]) if np.std(ea)>0 and np.std(eb)>0 else None
        sa=old.summary(panel,pa)['official_score'];sb=old.summary(panel,pb)['official_score'];blend=old.summary(panel,(pa+pb)/2)['official_score']
        out.append({'a':a,'b':b,'signed_row_error_Pearson':cor,'equal_blend_score':blend,'equal_blend_gain_over_a':blend-sa,'equal_blend_gain_over_b':blend-sb,'equal_blend_gain_over_better_member':blend-max(sa,sb),'row_error_definition':'prediction minus observed RCYL; aligned row keys asserted by caller','fits_added':0})
    return out
