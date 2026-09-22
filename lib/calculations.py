"""
Regras de cálculo do controle de day trade (WIN + WDO).

Cada ativo (WIN, WDO, ...) tem seu próprio valor por ponto, emolumento estimado,
margem e stop padrão — carregados da tabela `ativos`. `Parametros` guarda só o que
é da conta como um todo (capital inicial, alíquota de IRRF, qtd. de contratos padrão).

Testado contra os valores reais da planilha original (16/09 a 21/09/2026 — ver
tests_manual.py) e contra o valor de ponto do WDO confirmado via fontes públicas
(R$10,00/ponto).
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd


def _round2(value) -> float:
    """Arredondamento comercial (igual ao ROUND do Sheets/Excel), 2 casas decimais."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass
class Parametros:
    capital_inicial: float
    aliquota_irrf: float  # ex.: 0.01 = 1%
    qtd_contratos_padrao: int


@dataclass
class Ativo:
    codigo: str
    nome: str
    valor_por_ponto: float
    emolumento_por_contrato: float | None
    margem_por_contrato: float | None
    stop_loss_pontos: int | None
    stop_gain_pontos: int | None
    habilitado: bool = True


def calc_resultado_realizado(resultado_pontos: float, valor_por_ponto: float, contratos: int) -> float | None:
    """Resultado bruto do dia, em R$."""
    if resultado_pontos is None:
        return None
    return _round2(resultado_pontos * valor_por_ponto * contratos)


def calc_resultado_apos_taxas_estimado(
    resultado_realizado: float,
    contratos_operados: int,
    emolumento_por_contrato: float | None,
    aliquota_irrf: float,
) -> float | None:
    """
    Estimativa do resultado líquido do dia:
      1. desconta o emolumento estimado (contratos_operados * taxa/contrato do ativo)
      2. se o que sobrar for positivo, desconta o IRRF sobre esse valor
    Retorna None se faltar resultado, contratos operados, ou o ativo ainda não tiver
    um emolumento calibrado (nesse caso, só dá pra mostrar o resultado real depois).
    """
    if resultado_realizado is None or contratos_operados is None or emolumento_por_contrato is None:
        return None

    emolumento = _round2(contratos_operados * emolumento_por_contrato)
    liquido_pre_irrf = resultado_realizado - emolumento

    if liquido_pre_irrf > 0:
        irrf = _round2(liquido_pre_irrf * aliquota_irrf)
    else:
        irrf = 0.0

    return _round2(liquido_pre_irrf - irrf)


def resultado_final(row: pd.Series) -> float | None:
    """Usa o valor REAL (confirmado pela corretora) quando existir; senão, a estimativa."""
    real = row.get("resultado_apos_taxas_real")
    if real is not None and not pd.isna(real):
        return real
    est = row.get("resultado_apos_taxas_estimado")
    return None if pd.isna(est) else est


def build_dashboard(operacoes: pd.DataFrame, parametros: Parametros) -> pd.DataFrame:
    """
    Recebe as operações (já com ativo_nome/ativo_codigo, ordenadas por data) e devolve
    o DataFrame com as colunas calculadas: resultado_final, valor_confirmado,
    saldo_acumulado, pct_sobre_capital_inicial, sequencia_losses, sequencia_gains.
    """
    df = operacoes.sort_values("data").reset_index(drop=True).copy()

    df["resultado_final"] = df.apply(resultado_final, axis=1)
    df["valor_confirmado"] = df["resultado_apos_taxas_real"].notna()

    saldo = parametros.capital_inicial
    saldos, seq_losses, seq_gains = [], [], []
    losses_atual = gains_atual = 0

    for valor in df["resultado_final"]:
        if valor is None or pd.isna(valor):
            saldos.append(saldo)
            seq_losses.append(losses_atual)
            seq_gains.append(gains_atual)
            continue

        saldo = _round2(saldo + valor)
        if valor < 0:
            losses_atual += 1
            gains_atual = 0
        elif valor > 0:
            gains_atual += 1
            losses_atual = 0
        else:
            losses_atual = gains_atual = 0

        saldos.append(saldo)
        seq_losses.append(losses_atual)
        seq_gains.append(gains_atual)

    df["saldo_acumulado"] = saldos
    df["sequencia_losses"] = seq_losses
    df["sequencia_gains"] = seq_gains
    df["pct_sobre_capital_inicial"] = df["resultado_final"].apply(
        lambda v: None if v is None or pd.isna(v) else v / parametros.capital_inicial
    )
    return df


def build_resumo(df_calculado: pd.DataFrame, parametros: Parametros) -> dict:
    """Métricas agregadas (equivalente à aba Resumo da planilha original)."""
    com_resultado = df_calculado.dropna(subset=["resultado_final"])
    ganhos = com_resultado[com_resultado["resultado_final"] > 0]
    perdas = com_resultado[com_resultado["resultado_final"] < 0]

    total_realizado = df_calculado["resultado_realizado"].sum(skipna=True)
    total_apos_taxas = com_resultado["resultado_final"].sum()

    return {
        "total_operacoes": int(df_calculado["resultado_realizado"].notna().sum()),
        "operacoes_com_resultado": int(len(com_resultado)),
        "operacoes_gain": int(len(ganhos)),
        "operacoes_loss": int(len(perdas)),
        "taxa_acerto": (len(ganhos) / len(com_resultado)) if len(com_resultado) else 0.0,
        "maior_sequencia_losses": int(df_calculado["sequencia_losses"].max() or 0),
        "maior_sequencia_gains": int(df_calculado["sequencia_gains"].max() or 0),
        "resultado_total_pontos": float(df_calculado["resultado_pontos"].sum(skipna=True) or 0),
        "resultado_total_realizado": float(total_realizado or 0),
        "resultado_total_apos_taxas": float(total_apos_taxas or 0),
        "total_taxas_pagas": float((total_realizado or 0) - (total_apos_taxas or 0)),
        "saldo_atual": float(parametros.capital_inicial + (total_apos_taxas or 0)),
        "retorno_sobre_capital_inicial": float((total_apos_taxas or 0) / parametros.capital_inicial)
        if parametros.capital_inicial
        else 0.0,
    }
