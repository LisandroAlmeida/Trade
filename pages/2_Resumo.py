import streamlit as st

from lib.calculations import build_dashboard, build_resumo
from lib.db import get_operacoes, get_parametros
from lib.ui import fmt_brl, fmt_pct, header, setup_page

setup_page("Resumo", "📊")
header("Resumo de Desempenho", "Métricas agregadas e o registro completo", "📊")

parametros = get_parametros()
operacoes = get_operacoes()

if operacoes.empty:
    st.info("Nenhuma operação lançada ainda.")
    st.stop()

df = build_dashboard(operacoes, parametros)
r = build_resumo(df, parametros)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de operações", r["total_operacoes"])
col2.metric("Taxa de acerto", fmt_pct(r["taxa_acerto"]))
col3.metric("Maior sequência gains", r["maior_sequencia_gains"])
col4.metric("Maior sequência losses", r["maior_sequencia_losses"])

st.write("")
linhas = [
    ("Resultado total (pontos)", f"{r['resultado_total_pontos']:,.0f}".replace(",", ".")),
    ("Resultado total realizado (bruto)", fmt_brl(r["resultado_total_realizado"])),
    ("Resultado total após taxas", fmt_brl(r["resultado_total_apos_taxas"])),
    ("Total de taxas/corretagem pagas", fmt_brl(r["total_taxas_pagas"])),
    ("Saldo atual da conta", fmt_brl(r["saldo_atual"])),
    ("Retorno sobre o capital inicial (após taxas)", fmt_pct(r["retorno_sobre_capital_inicial"])),
]
for label, valor in linhas:
    c1, c2 = st.columns([3, 1])
    c1.write(label)
    c2.write(f"**{valor}**")

st.divider()
st.subheader("Registro completo")
tabela = df.sort_values("data", ascending=False).copy()
tabela["Data"] = tabela["data"].dt.strftime("%d/%m/%Y")
tabela["Confirmado"] = tabela["valor_confirmado"].map({True: "real", False: "estimado"})
st.dataframe(
    tabela[[
        "Data", "ativo_nome", "resultado_pontos", "contratos", "resultado_realizado", "contratos_operados",
        "resultado_final", "Confirmado", "motivo_saida", "saldo_acumulado",
        "pct_sobre_capital_inicial", "sequencia_losses", "sequencia_gains", "observacoes",
    ]].rename(columns={
        "ativo_nome": "Ativo", "resultado_pontos": "Pontos", "contratos": "Contratos",
        "resultado_realizado": "Bruto (R$)", "contratos_operados": "Contratos operados",
        "resultado_final": "Após taxas (R$)", "motivo_saida": "Motivo", "saldo_acumulado": "Saldo (R$)",
        "pct_sobre_capital_inicial": "% capital inicial", "sequencia_losses": "Seq. losses",
        "sequencia_gains": "Seq. gains", "observacoes": "Observações",
    }),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Bruto (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Após taxas (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Saldo (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "% capital inicial": st.column_config.NumberColumn(format="%.2f%%"),
    },
)

st.download_button(
    "⬇️ Baixar CSV",
    tabela.to_csv(index=False).encode("utf-8"),
    file_name="registro_operacoes.csv",
    mime="text/csv",
)
