from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.db import (
    delete_mesa_resultado,
    get_mesa_parametros,
    get_mesa_resultados,
    insert_mesa_resultado,
    update_mesa_parametros,
)
from lib.ui import fmt_brl, fmt_pct, header, mini_card, setup_page

COR_GANHO = "#3DD68C"
COR_PERDA = "#E66767"

setup_page("Mesa", "💼")
header("Mesa", "Conta de mesa proprietária (ex.: Canário) — separada da conta real", "💼")

p = get_mesa_parametros()
resultados = get_mesa_resultados()

saldo_acumulado = float(resultados["valor"].sum()) if not resultados.empty else 0.0
dias_operados = int(resultados["data"].dt.date.nunique()) if not resultados.empty else 0
dias_min = p.get("dias_min_operados")
saldo_min_saque = p.get("saldo_minimo_saque")

st.caption(
    f"{p.get('conta_numero') or '—'} · {p.get('metodo') or p.get('plano') or '—'}"
    if (p.get("conta_numero") or p.get("metodo") or p.get("plano"))
    else "Preencha os dados da conta em **Parâmetros da mesa**, mais abaixo."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Saldo acumulado", fmt_brl(saldo_acumulado))
col2.metric(
    "Ciclo atual",
    f"#{p['ciclo_numero']}" if p.get("ciclo_numero") else "—",
    help=(
        f"{p['ciclo_inicio']} a {p['ciclo_fim']}"
        if p.get("ciclo_inicio") and p.get("ciclo_fim")
        else None
    ),
)
col3.metric("Status do pagamento", p.get("status_pagamento") or "—")
col4.metric(
    "Dias operados",
    f"{dias_operados}/{dias_min}" if dias_min else str(dias_operados),
)

if saldo_min_saque:
    falta = max(saldo_min_saque - saldo_acumulado, 0)
    if falta > 0:
        st.progress(
            min(saldo_acumulado / saldo_min_saque, 1.0),
            text=f"Faltam {fmt_brl(falta)} para atingir o saldo mínimo de saque ({fmt_brl(saldo_min_saque)}).",
        )
    else:
        st.success(f"Saldo já passou do mínimo de saque ({fmt_brl(saldo_min_saque)}).")

if p.get("status_saque_texto"):
    st.caption(f"Status do saque: {p['status_saque_texto']}")

st.write("")
st.subheader("Lançar resultado do dia")
with st.form("novo_resultado_mesa", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 1, 3])
    data_resultado = c1.date_input("Data", value=date.today(), format="DD/MM/YYYY")
    contratos_dia = c2.number_input("Contratos (opcional)", min_value=0, step=1, value=0)
    valor_resultado = c3.number_input(
        "Resultado do dia (R$) — negativo para loss", step=1.0, format="%.2f"
    )
    obs_resultado = st.text_input("Observações (opcional)")
    if st.form_submit_button("Adicionar", type="primary"):
        insert_mesa_resultado({
            "data": data_resultado.isoformat(),
            "valor": valor_resultado,
            "contratos": int(contratos_dia) or None,
            "observacoes": obs_resultado or None,
        })
        st.success(f"Resultado de {fmt_brl(valor_resultado)} lançado para {data_resultado.strftime('%d/%m/%Y')}.")
        st.cache_data.clear()
        st.rerun()

st.write("")
if not resultados.empty:
    st.subheader("Evolução do P&L")
    evolucao = resultados.sort_values("data").copy()
    evolucao["acumulado"] = evolucao["valor"].cumsum()

    melhor_dia = evolucao["valor"].max()
    pior_dia = evolucao["valor"].min()
    dias_positivos_pct = (evolucao["valor"] > 0).mean()

    mc1, mc2, mc3 = st.columns(3)
    mc1.markdown(mini_card("Melhor dia", fmt_brl(melhor_dia), ""), unsafe_allow_html=True)
    mc2.markdown(mini_card("Pior dia", fmt_brl(pior_dia), ""), unsafe_allow_html=True)
    mc3.markdown(mini_card("Dias positivos", fmt_pct(dias_positivos_pct, 0), ""), unsafe_allow_html=True)

    y = evolucao["acumulado"]
    y_pos = y.clip(lower=0)
    y_neg = y.clip(upper=0)
    custom = evolucao["acumulado"].map(fmt_brl)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=evolucao["data"], y=y_pos, name="Ganho", mode="lines",
        line=dict(color=COR_GANHO, width=2, shape="spline"),
        fill="tozeroy", fillcolor="rgba(61, 214, 140, 0.18)",
        customdata=custom, hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=evolucao["data"], y=y_neg, name="Perda", mode="lines",
        line=dict(color=COR_PERDA, width=2, shape="spline"),
        fill="tozeroy", fillcolor="rgba(230, 103, 103, 0.18)",
        customdata=custom, hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.add_hline(y=0, line=dict(color="#383835", width=1))
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=10, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E6EDF3"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, tickformat="%d/%m"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False, tickprefix="R$ "),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.write("")
    tabela = resultados.sort_values("data", ascending=False).copy()
    tabela["Data"] = tabela["data"].dt.strftime("%d/%m/%Y")
    for _, linha in tabela.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 4, 1])
        c1.write(linha["Data"])
        c2.write(fmt_brl(linha["valor"]))
        c3.write(f"{int(linha['contratos'])}c" if pd.notna(linha["contratos"]) else "—")
        c4.write(linha["observacoes"] or "—")
        if c5.button("🗑️", key=f"del_mesa_{linha['id']}", help="Excluir"):
            delete_mesa_resultado(int(linha["id"]))
            st.cache_data.clear()
            st.rerun()
else:
    st.caption("Nenhum resultado lançado ainda.")

st.write("")
with st.expander("⚙️ Parâmetros da mesa"):
    st.caption(
        "Taxa de corretagem da mesa costuma ser diferente da conta real — deixe em branco "
        "até você confirmar o valor. O stop diário pessoal é só um registro da sua própria "
        "decisão (não é calculado nem sugerido pelo app)."
    )
    with st.form("parametros_mesa"):
        c1, c2 = st.columns(2)
        conta_numero = c1.text_input("Conta", value=p.get("conta_numero") or "")
        metodo = c2.text_input("Método/Plano", value=p.get("metodo") or p.get("plano") or "")

        c1, c2, c3 = st.columns(3)
        ciclo_numero = c1.number_input("Ciclo nº", min_value=0, step=1, value=int(p.get("ciclo_numero") or 0))
        ciclo_inicio = c2.date_input(
            "Início do ciclo",
            value=date.fromisoformat(p["ciclo_inicio"]) if p.get("ciclo_inicio") else date.today(),
            format="DD/MM/YYYY",
        )
        ciclo_fim = c3.date_input(
            "Fim do ciclo",
            value=date.fromisoformat(p["ciclo_fim"]) if p.get("ciclo_fim") else date.today(),
            format="DD/MM/YYYY",
        )

        c1, c2 = st.columns(2)
        status_pagamento = c1.text_input("Status do pagamento", value=p.get("status_pagamento") or "")
        status_saque_texto = c2.text_input("Status do saque (texto livre)", value=p.get("status_saque_texto") or "")

        c1, c2, c3 = st.columns(3)
        perda_diaria_maxima = c1.number_input(
            "Perda diária máxima (R$)", min_value=0.0, step=10.0, format="%.2f",
            value=float(p.get("perda_diaria_maxima") or 0.0),
        )
        perda_total_maxima = c2.number_input(
            "Perda total máxima (R$)", min_value=0.0, step=10.0, format="%.2f",
            value=float(p.get("perda_total_maxima") or 0.0),
        )
        saldo_minimo_saque = c3.number_input(
            "Saldo mínimo para saque (R$)", min_value=0.0, step=10.0, format="%.2f",
            value=float(p.get("saldo_minimo_saque") or 0.0),
        )

        c1, c2, c3 = st.columns(3)
        repasse_pct = c1.number_input(
            "Repasse (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
            value=float(p.get("repasse_pct") or 0.0) * 100,
        )
        qtd_contratos_max = c2.number_input(
            "Qtd. de contratos máxima", min_value=0, step=1, value=int(p.get("qtd_contratos_max") or 0),
        )
        dias_min_operados_input = c3.number_input(
            "Dias mínimos operados", min_value=0, step=1, value=int(p.get("dias_min_operados") or 0),
        )

        c1, c2 = st.columns(2)
        taxa_corretagem = c1.number_input(
            "Taxa de corretagem por contrato (R$) — manual",
            min_value=0.0, step=0.01, format="%.4f",
            value=float(p.get("taxa_corretagem_contrato") or 0.0),
            help="Deixe 0 até você descobrir o valor real cobrado pela mesa.",
        )
        stop_diario_pessoal = c2.number_input(
            "Seu stop diário pessoal (R$) — só registro",
            min_value=0.0, step=10.0, format="%.2f",
            value=float(p.get("stop_diario_pessoal") or 0.0),
        )

        if st.form_submit_button("Salvar", type="primary"):
            update_mesa_parametros({
                "conta_numero": conta_numero or None,
                "metodo": metodo or None,
                "ciclo_numero": int(ciclo_numero) or None,
                "ciclo_inicio": ciclo_inicio.isoformat(),
                "ciclo_fim": ciclo_fim.isoformat(),
                "status_pagamento": status_pagamento or None,
                "status_saque_texto": status_saque_texto or None,
                "perda_diaria_maxima": perda_diaria_maxima or None,
                "perda_total_maxima": perda_total_maxima or None,
                "saldo_minimo_saque": saldo_minimo_saque or None,
                "repasse_pct": (repasse_pct / 100) if repasse_pct else None,
                "qtd_contratos_max": int(qtd_contratos_max) or None,
                "dias_min_operados": int(dias_min_operados_input) or None,
                "taxa_corretagem_contrato": taxa_corretagem or None,
                "stop_diario_pessoal": stop_diario_pessoal or None,
            })
            st.success("Parâmetros da mesa atualizados.")
            st.cache_data.clear()
            st.rerun()
