"""Métricas anuales auditables sobre una copia de datos FSDS completos.

Sin normalizadores que rellenen ceros, alteren signos o elijan candidatos
ambiguos. resultado.originales conserva la fuente; estados son vistas largas.
"""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from reglas_sec import resolver_documento
from ausencias_sec import ausencia_revisada, IMPACTOS

@dataclass
class ResultadoSEC:
    tabla: pd.DataFrame
    auditoria: pd.DataFrame
    candidatos: pd.DataFrame
    estados: dict
    originales: dict = field(default_factory=dict)

CONCEPTOS = {
    'ingresos': ('IS',4,['Revenues','SalesRevenueNet',
                        'RevenueFromContractWithCustomerExcludingAssessedTax']),
    'beneficio_neto': ('IS',4,['NetIncomeLoss']),
    'activos_totales': ('BS',0,['Assets']),
    'activos_corrientes': ('BS',0,['AssetsCurrent']),
    'pasivos_totales': ('BS',0,['Liabilities']),
    'pasivos_corrientes': ('BS',0,['LiabilitiesCurrent']),
    'flujo_operativo': ('CF',4,['NetCashProvidedByUsedInOperatingActivities']),
}

def procesar_bag(bag,cik,tags_capex=None):
    cik=int(cik)
    all_sub=bag.sub_df.loc[pd.to_numeric(bag.sub_df.cik).eq(cik)].copy()
    ids=all_sub.adsh.tolist()
    originals={'sub':all_sub,'num':bag.num_df.loc[bag.num_df.adsh.isin(ids)].copy(),
               'pre':bag.pre_df.loc[bag.pre_df.adsh.isin(ids)].copy()}
    if hasattr(bag,'tag_df'): originals['tag']=bag.tag_df.copy()
    sub=all_sub.loc[all_sub.form.eq('10-K')].copy()
    if sub.empty: raise ValueError(f'No hay 10-K para CIK {cik}')
    sub['period']=pd.to_numeric(sub['period'],errors='raise').astype('int64')
    # FY es una etiqueta; su ausencia no impide calcular hechos de un
    # documento con fecha y duración explícitas. Se conserva sin inventarla.
    sub['fy']=pd.to_numeric(sub['fy'].replace('',pd.NA),errors='raise').astype('Int64')
    if sub.adsh.duplicated().any() or sub.loc[sub.fy.notna(),['cik','fy']].duplicated().any() or sub[['cik','period']].duplicated().any():
        raise ValueError('Documentos duplicados por CIK/FY: resolver antes de combinar')
    raw=originals['num'].loc[originals['num'].adsh.isin(sub.adsh)].copy()
    for column in ['ddate','qtrs','value']:
        raw[column]=pd.to_numeric(raw[column].replace('',np.nan),errors='raise')
    for column in ['coreg','segments']:
        raw[column]=raw[column].astype('string').fillna('').str.strip()
    presentations=originals['pre'][['adsh','tag','version','stmt','plabel']].drop_duplicates()
    facts=raw.merge(presentations,on=['adsh','tag','version'],how='left')
    table=sub[['cik','name','fy','adsh','period','filed']].rename(
        columns={'name':'empresa','period':'fecha_cierre'}).copy()
    table['fecha_cierre_dataset']=table.fecha_cierre
    table['fy_dataset']=table.fy
    table['fy_ausente_dataset']=table.fy.isna()
    table['base_fecha_cierre']='Fecha FSDS redondeada; no día exacto del XBRL'
    table['sic']=pd.to_numeric(sub.set_index('adsh')['sic'],errors='coerce').reindex(table.adsh).to_numpy() if 'sic' in sub else np.nan
    table['requiere_reglas_sectoriales']=table.sic.between(6000,6999) | table.sic.isna()
    evidence=[]; audits=[]
    for index,row in table.iterrows():
        current=facts.loc[facts.adsh.eq(row.adsh)&facts.ddate.eq(row.fecha_cierre)
            &facts.uom.eq('USD')&facts.coreg.eq('')&facts.segments.eq('')].copy()
        official=current.loc[current.version.ne(row.adsh)].copy()
        for concept,(statement,quarters,tags) in CONCEPTOS.items():
            allowed=['IS','CF','EQ'] if concept=='beneficio_neto' else [statement]
            candidates=official.loc[official.qtrs.eq(quarters)&official.tag.isin(tags)
                                    &official.stmt.isin(allowed)].copy()
            values=candidates.value.dropna().unique()
            valid=len(values)==1 and np.isfinite(values[0])
            value=float(values[0]) if valid else np.nan
            status='OK_HECHO_DIRECTO' if valid else 'SIN_HECHO' if not len(values) else 'AMBIGUO'
            table.loc[index,concept]=value
            candidates['concepto']=concept; evidence.append(candidates)
            audits.append(dict(cik=cik,fy=row.fy,adsh=row.adsh,concepto=concept,
                estado=status,utilizable=bool(valid),valor_resuelto=value,
                etiquetas=' | '.join(sorted(candidates.tag.unique())),
                fecha_cierre=row.fecha_cierre,qtrs=quarters,unidad='USD',
                valores_distintos=len(values),regla='HECHO_OFICIAL_UNICO'))
        table.loc[index,'capex']=np.nan
        audits.append(dict(cik=cik,fy=row.fy,adsh=row.adsh,concepto='capex',
            estado='REQUIERE_REGLA_CAPEX',utilizable=False,valor_resuelto=np.nan,
            fecha_cierre=row.fecha_cierre,qtrs=4,unidad='USD'))
        capex_candidates=official.loc[official.qtrs.eq(4)&official.stmt.eq('CF')&official.tag.isin([
            'PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets'])]
        for _, group in capex_candidates.groupby('tag'):
            vals=group.value.dropna().unique()
            if len(vals)>1:
                audits[-1].update(estado='AMBIGUO',valores_distintos=len(vals))
        solutions=resolver_documento(current,cik,row.adsh,row.fecha_cierre)
        if tags_capex is not None:
            custom_selection=official.loc[official.qtrs.eq(4)&official.stmt.eq('CF')
                                           &official.tag.isin(tags_capex)]
            values=custom_selection.value.dropna().unique()
            if len(values)==1 and np.isfinite(values[0]) and values[0]>=0:
                solutions['capex']=(float(values[0]),'REGLA_EXPLICITA_USUARIO',
                                   custom_selection,'Alcance de etiquetas explícitas del usuario')
            else: solutions.pop('capex',None)
        for concept,(value,rule,parts,definition) in solutions.items():
            table.loc[index,concept]=value
            if concept=='capex': table.loc[index,'alcance_capex']=definition
            parts=parts.copy(); parts['concepto']=concept; parts['regla']=rule; evidence.append(parts)
            audit=next(a for a in audits if a['adsh']==row.adsh and a['concepto']==concept)
            audit.update(estado='OK_REGLA_DOCUMENTADA',utilizable=True,regla=rule,
                         valor_resuelto=value,definicion=definition,
                         etiquetas=' | '.join(sorted(parts.tag.unique())))
        for audit in [a for a in audits if a['adsh']==row.adsh and not a['utilizable']]:
            concept=audit['concepto']
            audit['calculos_afectados']=IMPACTOS.get(concept, 'Filtros que requieran esta métrica')
            # Una contradicción es pendiente, aunque exista un antecedente de ausencia.
            if audit['estado'] == 'AMBIGUO':
                audit['causa']='Hay candidatos contradictorios; requiere revisión'
                continue
            verified=ausencia_revisada(cik,row.adsh,concept)
            if verified:
                audit.update(verified)
            else:
                audit['causa']='No se resolvió con las reglas actuales; ausencia en el reporte aún no verificada'
    table['definicion_beneficio_neto']='Resultado atribuible a matriz; distinto del consolidado'
    table['definicion_capex']='Pagos de inversión según alcance_capex; no FCF ajustado del emisor'
    table['fcf']=table.flujo_operativo-table.capex
    table['ncav']=table.activos_corrientes-table.pasivos_totales
    table['capital_trabajo']=table.activos_corrientes-table.pasivos_corrientes
    table['margen_fcf']=table.fcf/table.ingresos.where(table.ingresos.ne(0))
    table['razon_corriente']=table.activos_corrientes/table.pasivos_corrientes.where(table.pasivos_corrientes.ne(0))
    for name in ['ncav','capital_trabajo','razon_corriente','fcf','margen_fcf']:
        table['disponible_'+name]=np.isfinite(table[name])
        table['apto_filtro_industrial_'+name]=table['disponible_'+name] & ~table.requiere_reglas_sectoriales
    table['datos_completos_filtrador']=table[list(CONCEPTOS)+['capex']].notna().all(axis=1)
    table['apto_filtro_industrial_basico']=table.datos_completos_filtrador & ~table.requiere_reglas_sectoriales
    audit_frame=pd.DataFrame(audits)
    audit_frame['resolucion']=audit_frame.get('resolucion',pd.Series(index=audit_frame.index,dtype='object')).fillna(
        pd.Series(np.where(audit_frame.utilizable,'CERRADO_CON_CIFRA','PENDIENTE'),index=audit_frame.index))
    return ResultadoSEC(table.sort_values('fy').reset_index(drop=True),audit_frame,
        pd.concat(evidence,ignore_index=True),
        {name:facts.loc[facts.stmt.eq(name)].copy() for name in ['IS','BS','CF']},originals)

def procesar_extraido(tablas,cik):
    from types import SimpleNamespace
    bag=SimpleNamespace(sub_df=tablas['sub'],num_df=tablas['num'],pre_df=tablas['pre'],tag_df=tablas['tag'])
    return procesar_bag(bag,cik)

