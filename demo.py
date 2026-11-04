"""Offline quality checks and auditable metrics for a small SEC filing sample."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from motor_sec import procesar_extraido

def load_tables(folder=ROOT / 'data'):
    return {name: pd.read_csv(folder / (name+'.tsv'), sep='\t', dtype=str,
             keep_default_na=False) for name in ('sub','num','pre','tag')}

def validate(tables):
    """Structural preflight; no silent coercion or resolution of conflicts."""
    issues=[]
    required={'sub':['adsh','cik','form','period','fy','filed'],
              'num':['adsh','tag','version','ddate','qtrs','uom','value','coreg','segments'],
              'pre':['adsh','tag','version','stmt','plabel'], 'tag':['tag','version']}
    for name,cols in required.items():
        missing=sorted(set(cols)-set(tables[name].columns))
        if missing: issues.append({'table':name,'check':'missing_columns','count':len(missing),'detail':','.join(missing)})
    if issues: return issues
    ids=set(tables['sub'].adsh)
    definitions=set(tables['tag'][['tag','version']].itertuples(index=False,name=None))
    for name in ('num','pre'):
        df=tables[name]
        orphan=int((~df.adsh.isin(ids)).sum())
        unknown=sum(pair not in definitions for pair in df[['tag','version']].itertuples(index=False,name=None))
        if orphan: issues.append({'table':name,'check':'orphan_accession','count':orphan})
        if unknown: issues.append({'table':name,'check':'undefined_tag','count':unknown})
    for name,key in [('sub',['adsh']),('tag',['tag','version'])]:
        n=int(tables[name].duplicated(key,keep=False).sum())
        if n: issues.append({'table':name,'check':'duplicate_key','count':n})
    n=tables['num']
    key=['adsh','tag','version','ddate','qtrs','uom','coreg','segments']
    conflicts=n.groupby(key,dropna=False).value.nunique().gt(1)
    if conflicts.any(): issues.append({'table':'num','check':'conflicting_values','count':int(conflicts.sum())})
    duplicates=int(n.duplicated(keep=False).sum())
    if duplicates: issues.append({'table':'num','check':'duplicate_row','count':duplicates})
    values=pd.to_numeric(n.value.replace('',float('nan')),errors='coerce')
    invalid=n.value.ne('') & (values.isna() | values.isin([float('inf'),float('-inf')]))
    if invalid.any(): issues.append({'table':'num','check':'invalid_numeric_value','count':int(invalid.sum())})
    return issues

def run(output):
    output.mkdir(parents=True,exist_ok=True)
    provenance=json.loads((ROOT/'data/provenance.json').read_text())
    for name,expected in provenance['files'].items():
        if hashlib.sha256((ROOT/'data'/name).read_bytes()).hexdigest()!=expected['sha256']:
            raise ValueError('Sample integrity mismatch: '+name)
    tables=load_tables()
    issues=validate(tables)
    report={'sample':provenance['selection'],'rows':{k:len(v) for k,v in tables.items()},
            'structural_status':'PASS' if not issues else 'BLOCKED','issues':issues,
            'scope':'Structural checks and selected annual metrics; not full XBRL reconciliation or investment advice.'}
    if not issues:
        result=procesar_extraido(tables,320193)
        result.tabla.to_csv(output/'metrics.csv',index=False)
        result.auditoria.to_csv(output/'metric_audit.csv',index=False)
        result.candidatos.to_csv(output/'evidence.csv',index=False)
        report['metric_status_counts']=result.auditoria.estado.value_counts().to_dict()
        report['unresolved_metrics']=result.auditoria.loc[~result.auditoria.utilizable,'concepto'].tolist()
    (output/'quality_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 1 if issues else 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs')
    args=parser.parse_args()
    raise SystemExit(run(args.output))
