from datetime import date

import pandas as pd
import streamlit as st

from lib.calculations import calc_resultado_apos_taxas_estimado, calc_resultado_realizado
from lib.db import get_ativos, get_operacoes, get_parametros, insert_operacao, update_operacao
from lib.ui import header, setup_page

setup_page("Lançar Operação", "📝")
header("Lançar Operação", "Registre o resultado do dia — o resto é calculado sozinho", "📝")

parametros = get_parametros()
ativos = get_ativos(apenas_habilitados=True)
ativos_por_nome = {a.nome: a for a in ativos}

with st.form("nova_operacao", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    data_op = c1.date_input("Data", value=date.today(), format="DD/MM/YYYY")
    ativo_nome = c2.selectbox("Ativo", options=list(ativos_por_nome.keys()))
    contratos = c3.number_input("Contratos (padrão)", min_value=1, value=parametros.qtd_contratos_padrao, step=1)

    c4, c5 = st.columns(2)
    resultado_pontos = c4.number_input("Resultado do dia (pontos)", step=1.0, format="%.0f")
    contratos_operados = c5.number_input(
        "Contratos operados no dia (total, p/ estimar taxas)",
        min_value=0, step=1, value=0,
        help="Se não souber agora, deixe 0 e preencha depois — a estimativa de taxas fica em branco até lá.",
    )

    motivo_saida = st.selectbox("Motivo da saída", ["Stop Gain", "Stop Loss", "Saída manual", "Outro"])
    observacoes = st.text_input("Observações (opcional)")

    enviado = st.form_submit_button("Salvar operação", type="primary", use_container_width=True)

    if enviado:
        ativo = ativos_por_nome[ativo_nome]
        resultado_realizado = calc_resultado_realizado(resultado_pontos, ativo.valor_por_ponto, contratos)
        c_operados = int(contratos_operados) if contratos_operados else None
        estimado = calc_resultado_apos_taxas_estimado(
            resultado_realizado, c_operados, ativo.emolumento_por_contrato, parametros.aliquota_irrf
        )
        insert_operacao({
            "data": data_op.isoformat(),
            "ativo_codigo": ativo.codigo,
            "contratos": int(contratos),
            "resultado_pontos": resultado_pontos,
            "resultado_realizado": resultado_realizado,
            "contratos_operados": c_operados,
            "resultado_apos_taxas_estimado": estimado,
            "motivo_saida": motivo_saida,
            "observacoes": observacoes or None,
        })
        if estimado is not None:
            msg = f"Operação de {data_op.strftime('%d/%m/%Y')} salva. Estimativa após taxas: R$ {estimado:,.2f}."
        elif ativo.emolumento_por_contrato is None:
            msg = (
                f"Operação de {data_op.strftime('%d/%m/%Y')} salva. "
                f"O ativo {ativo.nome} ainda não tem um emolumento calibrado em Parâmetros — "
                "sem isso não dá pra estimar; confirme o valor real quando a corretora liberar."
            )
        else:
            msg = f"Operação de {data_op.strftime('%d/%m/%Y')} salva. Faltou 'contratos operados' para estimar as taxas."
        st.success(msg)
        st.cache_data.clear()

st.divider()
st.subheader("Confirmar valor real")
st.caption(
    "Como o extrato da corretora normalmente só aparece no dia seguinte, essas operações mostram só a "
    "estimativa (ou nada, se o ativo ainda não tem taxa calibrada). Preencha a coluna **Valor real** com "
    "o que a corretora confirmou e clique em salvar — isso substitui a estimativa em todo o app."
)

operacoes = get_operacoes()
pendentes = operacoes[operacoes["resultado_apos_taxas_real"].isna()].sort_values("data", ascending=False).copy()

if pendentes.empty:
    st.info("Nenhuma operação pendente de confirmação. Tudo em dia! ✅")
else:
    pendentes["Data"] = pendentes["data"].dt.strftime("%d/%m/%Y")
    pendentes["Valor real (R$)"] = None
    grade = pendentes[[
        "id", "Data", "ativo_nome", "resultado_realizado", "contratos_operados",
        "resultado_apos_taxas_estimado", "Valor real (R$)",
    ]].rename(columns={
        "ativo_nome": "Ativo",
        "resultado_realizado": "Bruto (R$)",
        "contratos_operados": "Contratos operados",
        "resultado_apos_taxas_estimado": "Estimado (R$)",
    })

    editado = st.data_editor(
        grade,
        hide_index=True,
        use_container_width=True,
        disabled=["id", "Data", "Ativo", "Bruto (R$)", "Estimado (R$)"],
        column_config={
            "id": None,  # esconde o id, mas mantém disponível pra salvar
            "Bruto (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Estimado (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Valor real (R$)": st.column_config.NumberColumn(format="R$ %.2f", step=0.01),
            "Contratos operados": st.column_config.NumberColumn(step=1),
        },
        key="editor_confirmacoes",
    )

    if st.button("Salvar confirmações", type="primary"):
        salvos = 0
        for _, row in editado.iterrows():
            valor_real = row["Valor real (R$)"]
            if valor_real is None or pd.isna(valor_real):
                continue
            campos = {"resultado_apos_taxas_real": float(valor_real)}
            contratos_op = row["Contratos operados"]
            if contratos_op is not None and not pd.isna(contratos_op):
                campos["contratos_operados"] = int(contratos_op)
            update_operacao(int(row["id"]), campos)
            salvos += 1
        if salvos:
            st.success(f"{salvos} operação(ões) confirmada(s) com o valor real.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.info("Nenhum valor novo pra salvar — preencha a coluna 'Valor real (R$)' primeiro.")
