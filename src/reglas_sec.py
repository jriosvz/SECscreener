"""Reglas explícitas sobre hechos presentados; no usan ceros imputados."""
import numpy as np


def resolver_documento(facts, cik, adsh, period):
    """Devuelve métricas resueltas y filas completas de evidencia.

    Algunas identidades fueron verificadas solo para los documentos de la
    muestra; esas reglas se limitan al accession revisado, no a todo año.
    El CAPEX genérico se define como pagos de PP&E en inversión. La regla
    no equipara toda adquisición, financiación o arrendamiento con CAPEX.
    """
    current = facts.loc[facts.adsh.eq(adsh) & facts.ddate.eq(period)].copy()
    result = {}

    def pick(tag, stmt, qtrs):
        candidates = current.loc[current.tag.eq(tag) & current.stmt.eq(stmt)
                                 & current.qtrs.eq(qtrs)].copy()
        reviewed_custom = (adsh == '0001628280-25-003063'
                           and tag == 'PaymentsForSolarEnergySystemsNetOfSales')
        if not reviewed_custom:
            candidates = candidates.loc[candidates.version.ne(adsh)].copy()
        values = candidates.value.dropna().unique()
        if len(values) != 1 or not np.isfinite(values[0]):
            return None
        return float(values[0]), candidates

    def record(name, value, rule, parts, definition):
        import pandas as pd
        if np.isfinite(value):
            result[name] = (value, rule, pd.concat(parts, ignore_index=True), definition)

    # El total presentado es distinto de los subtotales de ventas/servicios.
    total = current.loc[current.stmt.eq('IS') & current.qtrs.eq(4)
                        & current.version.ne(adsh)
                        & current.tag.isin(['Revenues',
                            'RevenueFromContractWithCustomerExcludingAssessedTax'])
                        & current.plabel.fillna('').str.contains(
                            r'(?i)^total\s+(?:net\s+)?(?:revenues?|sales)', regex=True)]
    values = total.value.dropna().unique()
    if len(values) == 1:
        record('ingresos', values[0], 'TOTAL_EXPLICITO_PRESENTADO', [total],
               'Ingresos totales presentados; no subtotales')

    # JPM: net interest + noninterest = total net revenue, regla de su 10-K.
    if adsh in ['0000019617-25-000270','0001281761-25-000010']:
        parts = [pick(tag, 'IS', 4) for tag in ['InterestIncomeExpenseNet', 'NoninterestIncome']]
        if all(part is not None for part in parts):
            record('ingresos', sum(part[0] for part in parts), 'INGRESOS_NETOS_BANCARIOS',
                   [part[1] for part in parts], 'Ingreso neto bancario; no comparable a ventas industriales')

    # Balance: activos = pasivos + patrimonio total + patrimonio temporal.
    reviewed_balance = {
        '0000104169-25-000021': ['RedeemableNoncontrollingInterestEquityCarryingAmount'],
        '0000021344-25-000011': [],
        '0000050863-25-000009': [],
    }
    if adsh in reviewed_balance:
        parts = [pick('Assets','BS',0),
                 pick('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','BS',0)]
        parts += [pick(tag,'BS',0) for tag in reviewed_balance[adsh]]
        if all(part is not None for part in parts):
            value = parts[0][0] - sum(part[0] for part in parts[1:])
            if value >= 0:
                record('pasivos_totales', value, 'IDENTIDAD_BALANCE_REVISADA',
                       [part[1] for part in parts], 'Activos menos patrimonio total y patrimonio temporal identificado')

    # Estos balances no publican Liabilities como total etiquetado.
    # En los dos reportes revisados, el patrimonio total es StockholdersEquity;
    # no hay interés minoritario o patrimonio temporal fuera de ese total.
    if adsh in ['0000029905-25-000006','0001018724-25-000004']:
        assets=pick('Assets','BS',0)
        equity=pick('StockholdersEquity','BS',0)
        if assets is not None and equity is not None and assets[0]>=equity[0]:
            record('pasivos_totales',assets[0]-equity[0],'IDENTIDAD_BALANCE_REVISADA',
                   [assets[1],equity[1]],'Balance revisado: activos menos patrimonio total presentado')
    # Dover separa operaciones continuadas/discontinuadas en el flujo.
    if adsh=='0000029905-25-000006':
        parts=[pick(tag,'CF',4) for tag in [
            'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
            'CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations']]
        if all(part is not None for part in parts):
            record('flujo_operativo',sum(part[0] for part in parts),'CFO_CONTINUADAS_Y_DISCONTINUADAS',
                   [part[1] for part in parts],'Flujo operativo total, incluidas operaciones discontinuadas')
    # CAT muestra ProfitLoss y el interés minoritario, con signo negativo.
    if adsh == '0000018230-25-000008':
        profit = pick('ProfitLoss','IS',4)
        nci = pick('NetIncomeLossAttributableToNoncontrollingInterest','IS',4)
        if profit is not None and nci is not None:
            record('beneficio_neto', profit[0]-nci[0], 'BENEFICIO_MATRIZ_REVISADO',
                   [profit[1],nci[1]], 'Resultado consolidado menos atribuible a minoritarios')

    # Todos los componentes adicionales requieren evidencia explícita.
    capex = pick('PaymentsToAcquirePropertyPlantAndEquipment','CF',4)
    if capex is None and not current.loc[current.tag.eq('PaymentsToAcquirePropertyPlantAndEquipment')
                                       & current.stmt.eq('CF') & current.qtrs.eq(4)].shape[0]:
        capex = pick('PaymentsToAcquireProductiveAssets','CF',4)
    if capex is not None and capex[0] >= 0:
        parts, definition = [capex], 'Pagos de PP&E en actividades de inversión'
        extras = {'0001628280-25-003063': ['PaymentsForSolarEnergySystemsNetOfSales'],
                  '0000018230-25-000008': ['PaymentsToAcquireEquipmentOnLease']}
        if adsh in extras:
            parts += [pick(tag,'CF',4) for tag in extras[adsh]]
            definition += '; incluye componentes separados revisados del documento'
        # No confundir el subtotal PP&E de Berkshire con su medida gerencial.
        if all(part is not None and part[0] >= 0 for part in parts):
            record('capex', sum(part[0] for part in parts), 'PAGOS_CAPEX_DEFINIDOS',
                   [part[1] for part in parts], definition)
    return result
