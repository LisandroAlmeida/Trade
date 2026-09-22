import streamlit as st

from lib.calculations import build_dashboard, build_resumo
from lib.db import get_operacoes, get_parametros
from lib.ui import badge_confirmado, fmt_brl, fmt_pct, header, setup_page

setup_page("Dashboard", "📈")
header("Controle de Day Trade", "WIN e WDO — visão geral da conta", "📈")

parametros = get_parametros()
operacoes = get_operacoes()

if operacoes.empty:
    st.info("Nenhuma operação lançada ainda. Vá em **Lançar Operação** no menu à esquerda para começar.")
    st.stop()

df = build_dashboard(operacoes, parametros)
resumo = build_resumo(df, parametros)
ultima = df.iloc[-1]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Saldo atual", fmt_brl(resumo["saldo_atual"]))
col2.metric("Retorno sobre capital inicial", fmt_pct(resumo["retorno_sobre_capital_inicial"]))
col3.metric("Taxa de acerto", fmt_pct(resumo["taxa_acerto"]))
if ultima["sequencia_gains"] > 0:
    sequencia_txt = f"{int(ultima['sequencia_gains'])} gains seguidos"
elif ultima["sequencia_losses"] > 0:
    sequencia_txt = f"{int(ultima['sequencia_losses'])} losses seguidos"
else:
    sequencia_txt = "—"
col4.metric("Sequência atual", sequencia_txt)

st.write("")
st.subheader("Evolução do saldo")
chart_df = df.set_index("data")[["saldo_acumulado"]].rename(columns={"saldo_acumulado": "Saldo (R$)"})
st.line_chart(chart_df, color="#3DD68C")

st.write("")
st.subheader("Operações recentes")
tabela = df.sort_values("data", ascending=False).head(15).copy()
tabela["Data"] = tabela["data"].dt.strftime("%d/%m/%Y")
tabela["Confirmado"] = tabela["valor_confirmado"].map({True: "✓ real", False: "⏳ estimado"})

st.dataframe(
    tabela[[
        "Data", "ativo_nome", "resultado_pontos", "resultado_realizado", "resultado_final",
        "Confirmado", "motivo_saida", "saldo_acumulado",
    ]].rename(columns={
        "ativo_nome": "Ativo",
        "resultado_pontos": "Pontos",
        "resultado_realizado": "Bruto (R$)",
        "resultado_final": "Após taxas (R$)",
        "motivo_saida": "Motivo",
        "saldo_acumulado": "Saldo (R$)",
    }),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Bruto (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Após taxas (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Saldo (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Pontos": st.column_config.NumberColumn(format="%.0f"),
    },
)

pendentes = df[~df["valor_confirmado"]]
if len(pendentes):
    st.warning(
        f"⏳ **{len(pendentes)} operação(ões)** ainda com valor estimado — "
        "confirme com o valor real assim que a corretora liberar, na aba **Lançar Operação**.",
        icon="⏳",
    )
