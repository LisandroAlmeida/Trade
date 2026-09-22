"""Validação rápida: confere se o motor de cálculo bate com os valores reais da planilha
(agora com o modelo multi-ativo: cada linha carrega o valor_por_ponto/emolumento do seu ativo)."""
import pandas as pd

from lib.calculations import (
    Ativo,
    Parametros,
    build_dashboard,
    build_resumo,
    calc_resultado_apos_taxas_estimado,
    calc_resultado_realizado,
)

parametros = Parametros(capital_inicial=983.37, aliquota_irrf=0.01, qtd_contratos_padrao=1)
win = Ativo(codigo="WIN", nome="Mini Índice (WIN)", valor_por_ponto=0.20, emolumento_por_contrato=0.50,
            margem_por_contrato=150.00, stop_loss_pontos=300, stop_gain_pontos=500)

rows = [
    # data, pontos, contratos, contratos_operados, resultado_apos_taxas_real (confirmado)
    ("2026-09-16", 675, 1, 15, 126.23),
    ("2026-09-17", 345, 1, 27, 54.95),
    ("2026-09-18", 355, 1, 8, None),
    ("2026-09-21", 535, 1, 8, None),
]

data = []
for data_str, pontos, contratos, c_operados, real in rows:
    realizado = calc_resultado_realizado(pontos, win.valor_por_ponto, contratos)
    estimado = calc_resultado_apos_taxas_estimado(realizado, c_operados, win.emolumento_por_contrato, parametros.aliquota_irrf)
    data.append({
        "data": data_str,
        "ativo_nome": win.nome,
        "resultado_pontos": pontos,
        "contratos": contratos,
        "resultado_realizado": realizado,
        "contratos_operados": c_operados,
        "resultado_apos_taxas_estimado": estimado,
        "resultado_apos_taxas_real": real,
    })

df = pd.DataFrame(data)
df["data"] = pd.to_datetime(df["data"])
calculado = build_dashboard(df, parametros)
print(calculado[[
    "data", "resultado_realizado", "resultado_apos_taxas_estimado", "resultado_apos_taxas_real",
    "resultado_final", "saldo_acumulado", "sequencia_gains", "sequencia_losses",
]])

resumo = build_resumo(calculado, parametros)
print("\nResumo:", resumo)

# Checagens contra os valores reais da planilha
expected_saldos = [1109.60, 1164.55, 1230.88, 1332.85]
assert list(calculado["saldo_acumulado"]) == expected_saldos, calculado["saldo_acumulado"].tolist()
assert calculado.loc[2, "resultado_final"] == 66.33, calculado.loc[2, "resultado_final"]
assert calculado.loc[3, "resultado_final"] == 101.97, calculado.loc[3, "resultado_final"]

# WDO: emolumento ainda não calibrado -> estimativa deve vir None (não pode inventar taxa)
wdo = Ativo(codigo="WDO", nome="Mini Dólar (WDO)", valor_por_ponto=10.00, emolumento_por_contrato=None,
            margem_por_contrato=None, stop_loss_pontos=None, stop_gain_pontos=None)
realizado_wdo = calc_resultado_realizado(20, wdo.valor_por_ponto, 1)
assert realizado_wdo == 200.00, realizado_wdo  # 20 pontos x R$10,00 x 1 contrato
estimado_wdo = calc_resultado_apos_taxas_estimado(realizado_wdo, 2, wdo.emolumento_por_contrato, parametros.aliquota_irrf)
assert estimado_wdo is None, estimado_wdo

print("\nOK: todos os valores batem com a planilha, e o WDO calcula o bruto certo (R$10,00/ponto) sem inventar taxa.")
