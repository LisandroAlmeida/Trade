from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.calculations import build_dashboard, build_resumo
from lib.db import get_operacoes, get_parametros
from lib.ui import fmt_brl, fmt_pct, header, setup_page

# Cores reaproveitadas do tema do app (verde da marca) + vermelho validado pra
# contraste/leitura em daltonismo contra o fundo escuro (ver skill de dataviz).
COR_GANHO = "#3DD68C"
COR_PERDA = "#E66767"

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
col5, col6 = st.columns(2)
pontos_txt = f"{resumo['resultado_total_pontos']:,.0f}".replace(",", ".")
col5.metric("Resultado total (pontos)", pontos_txt)
col6.metric("Resultado total após taxas", fmt_brl(resumo["resultado_total_apos_taxas"]))

st.write("")
st.subheader("Evolução do resultado")

data_min, data_max = df["data"].min().date(), df["data"].max().date()
fc1, fc2, fc3 = st.columns([2, 1, 1])
periodo = fc1.date_input(
    "Período", value=(data_min, data_max), min_value=data_min, max_value=data_max, format="DD/MM/YYYY"
)
ativo_filtro = fc2.selectbox("Ativo", options=["Todos", "WIN", "WDO"])
metrica = fc3.radio("Valores em", ["%", "R$"], horizontal=True)

if isinstance(periodo, tuple) and len(periodo) == 2:
    ini, fim = periodo
else:
    ini, fim = data_min, data_max

filtrado = df[(df["data"].dt.date >= ini) & (df["data"].dt.date <= fim)].copy()
if ativo_filtro != "Todos":
    filtrado = filtrado[filtrado["ativo_codigo"] == ativo_filtro]

if filtrado.empty:
    st.info(
        f"Nenhuma operação de {ativo_filtro} nesse período — "
        "ainda não há dados pra desenhar o gráfico."
        if ativo_filtro != "Todos"
        else "Nenhuma operação nesse período."
    )
else:
    filtrado = filtrado.sort_values("data")
    filtrado["resultado_acumulado_rs"] = filtrado["resultado_final"].fillna(0).cumsum()
    filtrado["resultado_acumulado_pct"] = filtrado["resultado_acumulado_rs"] / parametros.capital_inicial * 100

    y_col = "resultado_acumulado_pct" if metrica == "%" else "resultado_acumulado_rs"
    y = filtrado[y_col]
    y_pos = y.clip(lower=0)
    y_neg = y.clip(upper=0)
    hover_fmt = "%{customdata}<extra></extra>"
    custom = (
        filtrado[y_col].map(lambda v: f"{v:+,.2f}%".replace(",", "§").replace(".", ",").replace("§", "."))
        if metrica == "%"
        else filtrado[y_col].map(lambda v: fmt_brl(v))
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=filtrado["data"], y=y_pos, name="Ganho", mode="lines",
        line=dict(color=COR_GANHO, width=2, shape="spline"),
        fill="tozeroy", fillcolor="rgba(61, 214, 140, 0.18)",
        customdata=custom, hovertemplate=hover_fmt,
    ))
    fig.add_trace(go.Scatter(
        x=filtrado["data"], y=y_neg, name="Perda", mode="lines",
        line=dict(color=COR_PERDA, width=2, shape="spline"),
        fill="tozeroy", fillcolor="rgba(230, 103, 103, 0.18)",
        customdata=custom, hovertemplate=hover_fmt,
    ))
    fig.add_hline(y=0, line=dict(color="#383835", width=1))
    fig.update_layout(
        height=340,
        margin=dict(l=0, r=10, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E6EDF3"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, tickformat="%d/%m"),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False,
            ticksuffix="%" if metrica == "%" else "",
            tickprefix="" if metrica == "%" else "R$ ",
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.write("")
st.subheader("Operações recentes")
tabela = df.sort_values("data", ascending=False).head(15).copy()
tabela["Data"] = tabela["data"].dt.strftime("%d/%m/%Y")
tabela["Confirmado"] = tabela["valor_confirmado"].map({True: "✓ real", False: "⏳ estimado"})

st.dataframe(
    tabela[[
        "Data", "ativo_codigo", "resultado_pontos", "resultado_realizado", "resultado_final",
        "Confirmado", "motivo_saida", "saldo_acumulado",
    ]].rename(columns={
        "ativo_codigo": "Ativo",
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
