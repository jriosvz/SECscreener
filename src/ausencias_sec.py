"""Ausencias revisadas por documento, nunca extrapoladas a otro año.

El hecho observado y su interpretación se registran por separado.
No requiere EdgarTools ni conexiones de red durante el cálculo.
"""
IMPACTOS = {
    'activos_corrientes': 'ncav | capital_trabajo | razon_corriente',
    'pasivos_corrientes': 'capital_trabajo | razon_corriente',
    'capex': 'fcf | margen_fcf',
}
JPM_FUENTE = 'https://jpmorganchaseco.gcs-web.com/static-files/3aebe5f5-2964-42cb-980b-8f9b86533663'
BRK_FUENTE = 'https://www.berkshirehathaway.com/2024ar/2024ar.pdf'

def ausencia_revisada(cik, adsh, concepto):
    """Devuelve evidencia solo para la combinación exacta revisada."""
    if (int(cik), adsh) == (19617, '0000019617-25-000270'):
        fuente = JPM_FUENTE
        if concepto in ['activos_corrientes', 'pasivos_corrientes']:
            seccion = '10-K 2024, balance p.174; Liquidity Risk Management pp.108–115'
            hecho = 'El balance no clasifica totales corrientes; los hechos XBRL tampoco contienen esos totales estándar.'
            causa = 'Presentación bancaria por tipos de activos y obligaciones, sin subtotales corrientes.'
            interpretacion = 'Su evaluación de liquidez requiere reglas bancarias; no reconstruir vencimientos sumando partidas del balance.'
        elif concepto == 'capex':
            seccion = '10-K 2024, flujos p.176 y nota 16 p.285'
            hecho = 'No se identificó un total separado de pagos cash de CAPEX en flujos, nota 16 o hechos XBRL revisados.'
            causa = 'El flujo publicado no desglosa un total de CAPEX compatible con la definición del motor.'
            interpretacion = 'La nota 16 publica saldos netos con depreciación y derechos de uso; su variación no equivale a pagos cash. No está documentado el motivo de no desglosar CAPEX.'
        else:
            return None
    elif (int(cik), adsh) == (1067983, '0000950170-25-025210') and concepto in ['activos_corrientes', 'pasivos_corrientes']:
        fuente = BRK_FUENTE
        seccion = 'Informe 2024, K-66/K-67 (PDF pp.88/89); nota 1(a), K-71 (PDF p.93)'
        hecho = 'El balance agrupa negocios sin publicar totales consolidados corrientes; los hechos XBRL tampoco contienen esos totales estándar.'
        causa = 'Balance sin clasificación corriente/no corriente, separado por Insurance and Other y Railroad, Utilities and Energy.'
        interpretacion = 'La nota 1(a) justifica separar negocios por PP&E, inversión y deuda y ausencia de garantías de Berkshire. Relacionar esa estructura con los subtotales ausentes es una interpretación, no una razón explícita del emisor.'
    elif (int(cik),adsh) in [
        (80661,'0000080661-25-000007'),(726728,'0000726728-25-000055'),
        (1281761,'0001281761-25-000010')
    ] and concepto in ['activos_corrientes','pasivos_corrientes']:
        fuente=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace("-","")}/'
        seccion='Balance consolidado del 10-K 2024; copia y hechos en carpeta edgar del CIK'
        hecho='El balance revisado no publica subtotales consolidados corrientes; no están presentes AssetsCurrent/LiabilitiesCurrent en los hechos XBRL.'
        causa='Balance presentado sin clasificación corriente/no corriente consolidada.'
        interpretacion='La presentación por naturaleza de los activos y obligaciones explica la falta de subtotales. El motivo específico de elegirla no está declarado en la evidencia revisada.'
    elif (int(cik),adsh) in [
        (726728,'0000726728-25-000055'),(1281761,'0001281761-25-000010')
    ] and concepto=='capex':
        return dict(estado='REQUIERE_DEFINICION_SECTORIAL',resolucion='PENDIENTE',
                    causa='Hay inversión publicada; el alcance no equivale automáticamente a pagos de PP&E del motor',
                    hecho_observado='Realty publica inversión inmobiliaria; Regions presenta Net purchases of other assets',
                    interpretacion='Definir y revisar el alcance sectorial antes de combinar adquisiciones, ventas netas y CAPEX',
                    fuente=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace("-","")}/',
                    seccion='Estado consolidado de flujos y notas de inversiones del 10-K 2024',
                    certeza='Pendiente de definición; no es ausencia confirmada',
                    calculos_afectados=IMPACTOS[concepto],importancia='ALTA_PARA_CALCULOS_AFECTADOS')
    else:
        return None
    return dict(estado='AUSENCIA_VERIFICADA_FUENTE_PRIMARIA',
                resolucion='CERRADO_SIN_CIFRA', fuente=fuente, seccion=seccion,
                hecho_observado=hecho, causa=causa, interpretacion=interpretacion,
                certeza='Ausencia observada; interpretación delimitada',
                importancia='ALTA_PARA_CALCULOS_AFECTADOS',
                calculos_afectados=IMPACTOS[concepto],
                verificador='Reporte del emisor y XBRL del accession exacto; contraste provisional independiente')
