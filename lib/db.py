"""Camada de acesso ao Supabase (config em st.secrets)."""
import pandas as pd
import streamlit as st
from supabase import create_client, Client

from lib.calculations import Ativo, Parametros


@st.cache_resource
def get_client() -> Client:
    return create_client(st.secrets["supabase_url"], st.secrets["supabase_key"])


def get_parametros() -> Parametros:
    client = get_client()
    row = client.table("parametros").select("*").eq("id", 1).single().execute().data
    return Parametros(
        capital_inicial=float(row["capital_inicial"]),
        aliquota_irrf=float(row["aliquota_irrf"]),
        qtd_contratos_padrao=int(row["qtd_contratos_padrao"]),
    )


def update_parametros(campos: dict) -> None:
    client = get_client()
    client.table("parametros").update(campos).eq("id", 1).execute()


def get_ativos(apenas_habilitados: bool = False) -> list[Ativo]:
    client = get_client()
    query = client.table("ativos").select("*").order("codigo")
    if apenas_habilitados:
        query = query.eq("habilitado", True)
    rows = query.execute().data
    return [
        Ativo(
            codigo=r["codigo"],
            nome=r["nome"],
            valor_por_ponto=float(r["valor_por_ponto"]),
            emolumento_por_contrato=float(r["emolumento_por_contrato"]) if r["emolumento_por_contrato"] is not None else None,
            margem_por_contrato=float(r["margem_por_contrato"]) if r["margem_por_contrato"] is not None else None,
            stop_loss_pontos=int(r["stop_loss_pontos"]) if r["stop_loss_pontos"] is not None else None,
            stop_gain_pontos=int(r["stop_gain_pontos"]) if r["stop_gain_pontos"] is not None else None,
            habilitado=bool(r["habilitado"]),
        )
        for r in rows
    ]


def get_ativo(codigo: str) -> Ativo | None:
    return next((a for a in get_ativos() if a.codigo == codigo), None)


def update_ativo(codigo: str, campos: dict) -> None:
    client = get_client()
    client.table("ativos").update(campos).eq("codigo", codigo).execute()


def get_operacoes() -> pd.DataFrame:
    """Operações com o nome/parâmetros do ativo já vindo junto (via view operacoes_calculadas)."""
    client = get_client()
    rows = client.table("operacoes_calculadas").select("*").order("data").execute().data
    colunas = [
        "id", "data", "ativo_codigo", "ativo_nome", "contratos", "resultado_pontos", "resultado_realizado",
        "contratos_operados", "resultado_apos_taxas_estimado", "resultado_apos_taxas_real",
        "resultado_apos_taxas_final", "valor_confirmado", "motivo_saida", "observacoes",
    ]
    if not rows:
        return pd.DataFrame(columns=colunas)
    df = pd.DataFrame(rows)
    df["data"] = pd.to_datetime(df["data"])
    return df


def insert_operacao(campos: dict) -> None:
    client = get_client()
    client.table("operacoes").insert(campos).execute()


def update_operacao(operacao_id: int, campos: dict) -> None:
    client = get_client()
    client.table("operacoes").update(campos).eq("id", operacao_id).execute()


def delete_operacao(operacao_id: int) -> None:
    client = get_client()
    client.table("operacoes").delete().eq("id", operacao_id).execute()
