from datetime import date

import streamlit as st

from lib.db import (
    delete_aporte,
    get_ativos,
    get_aportes,
    get_parametros,
    insert_aporte,
    update_ativo,
    update_parametros,
)
from lib.ui import fmt_brl, header, setup_page

setup_page("Parâmetros", "⚙️")
header("Parâmetros", "Conta e ativos — tudo abaixo recalcula automaticamente", "⚙️")

tab_conta, tab_ativos, tab_aportes = st.tabs(["Conta", "Ativos", "Aportes/Resgate"])

with tab_conta:
    p = get_parametros()
    with st.form("parametros_conta"):
        capital_inicial = st.number_input(
            "Capital inicial da conta (R$)", value=p.capital_inicial, step=0.01, format="%.2f"
        )
        irrf_pct = st.number_input(
            "Alíquota IRRF day trade (%, sobre ganho líquido do dia)",
            value=p.aliquota_irrf * 100, step=0.1, format="%.2f",
            help="Mesma alíquota vale pra qualquer ativo (é regra da Receita, não da corretora).",
        )
        qtd_contratos = st.number_input(
            "Qtd. de contratos padrão (sugestão ao lançar operação)",
            value=p.qtd_contratos_padrao, step=1, min_value=1,
        )
        if st.form_submit_button("Salvar", type="primary"):
            update_parametros({
                "capital_inicial": capital_inicial,
                "aliquota_irrf": irrf_pct / 100,
                "qtd_contratos_padrao": int(qtd_contratos),
            })
            st.success("Parâmetros da conta atualizados.")
            st.cache_data.clear()

    st.divider()
    st.subheader("Reiniciar ciclo")
    if p.data_inicio_ciclo:
        st.caption(
            f"Ciclo atual começou em **{p.data_inicio_ciclo.strftime('%d/%m/%Y')}** — operações e aportes "
            "antes dessa data ficam guardados no banco, mas não aparecem mais em nenhuma tela."
        )
    else:
        st.caption(
            "Use isso pra 'zerar' o controle sem apagar nada: define uma data de corte e um capital novo. "
            "O dashboard, resumo e saldo passam a considerar só o que acontecer a partir dessa data — o "
            "que já foi lançado continua no banco, só sai de vista."
        )
    with st.form("reiniciar_ciclo"):
        c1, c2 = st.columns(2)
        nova_data_inicio = c1.date_input("Reiniciar a partir de", value=date.today(), format="DD/MM/YYYY")
        novo_capital = c2.number_input(
            "Capital no início do novo ciclo (R$)", min_value=0.0, step=0.01, format="%.2f",
            value=p.capital_inicial,
        )
        col_reiniciar, col_limpar = st.columns(2)
        reiniciar = col_reiniciar.form_submit_button("Reiniciar ciclo", type="primary")
        limpar = col_limpar.form_submit_button("Remover corte (ver tudo de novo)", disabled=not p.data_inicio_ciclo)
        if reiniciar:
            update_parametros({
                "capital_inicial": novo_capital,
                "data_inicio_ciclo": nova_data_inicio.isoformat(),
            })
            st.success(f"Ciclo reiniciado em {nova_data_inicio.strftime('%d/%m/%Y')} com R$ {novo_capital:,.2f}.")
            st.cache_data.clear()
            st.rerun()
        if limpar:
            update_parametros({"data_inicio_ciclo": None})
            st.success("Corte removido — o app volta a considerar todo o histórico.")
            st.cache_data.clear()
            st.rerun()

with tab_ativos:
    st.caption(
        "Cada ativo tem seu próprio valor por ponto (especificação fixa da B3), emolumento estimado, "
        "margem exigida pela corretora e stop padrão. Deixe em branco o que ainda não souber — o app "
        "avisa quando faltar algo pra estimar as taxas."
    )
    ativos = get_ativos()
    codigos = {a.codigo: a for a in ativos}
    escolhido = st.selectbox("Ativo", options=list(codigos.keys()))
    a = codigos[escolhido]

    with st.form(f"ativo_{a.codigo}"):
        st.number_input(
            "Valor por ponto (R$)", value=a.valor_por_ponto, step=0.01, format="%.2f",
            disabled=True, help="Especificação fixa do contrato na B3 — não é editável aqui.",
        )
        emolumento = st.number_input(
            "Emolumento estimado por contrato — day trade (R$)",
            value=a.emolumento_por_contrato if a.emolumento_por_contrato is not None else 0.0,
            step=0.01, format="%.2f",
            help="Recalibre sempre que confirmar um valor real da corretora e a diferença for relevante.",
        )
        margem = st.number_input(
            "Margem exigida pela corretora (R$/contrato)",
            value=a.margem_por_contrato if a.margem_por_contrato is not None else 0.0,
            step=1.0, format="%.2f",
            help="Varia com a volatilidade — confira periodicamente no seu home broker.",
        )
        c1, c2 = st.columns(2)
        stop_loss = c1.number_input("Stop Loss padrão (pontos)", value=a.stop_loss_pontos or 0, step=1)
        stop_gain = c2.number_input("Stop Gain padrão (pontos)", value=a.stop_gain_pontos or 0, step=1)

        if st.form_submit_button("Salvar", type="primary"):
            update_ativo(a.codigo, {
                "emolumento_por_contrato": emolumento or None,
                "margem_por_contrato": margem or None,
                "stop_loss_pontos": int(stop_loss) or None,
                "stop_gain_pontos": int(stop_gain) or None,
            })
            st.success(f"Parâmetros de {a.nome} atualizados.")
            st.cache_data.clear()
            st.rerun()

    st.write("")
    if a.stop_loss_pontos and a.stop_gain_pontos:
        risco = a.stop_loss_pontos * a.valor_por_ponto
        ganho_alvo = a.stop_gain_pontos * a.valor_por_ponto
        c1, c2, c3 = st.columns(3)
        c1.metric("Risco por operação (1 contrato)", f"R$ {risco:,.2f}")
        c2.metric("Ganho-alvo por operação (1 contrato)", f"R$ {ganho_alvo:,.2f}")
        c3.metric("Relação Ganho:Risco", f"{ganho_alvo / risco:.2f}x" if risco else "—")
    else:
        st.caption("Preencha o stop loss/gain acima pra ver risco e ganho-alvo calculados.")

with tab_aportes:
    st.caption(
        "Aporte: reforço de capital feito na conta. Resgate: saque feito da conta (ex.: retirada "
        "pela corretora). Os dois ficam separados do capital inicial de propósito — entram no saldo "
        "atual, mas não entram na % de retorno sobre capital inicial nem no gráfico de evolução, "
        "porque não são resultado de trading."
    )
    with st.form("novo_aporte", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 2])
        data_aporte = c1.date_input("Data", value=date.today(), format="DD/MM/YYYY")
        tipo_aporte = c2.radio("Tipo", ["Aporte", "Resgate"], horizontal=True)
        valor_aporte = c3.number_input("Valor (R$)", min_value=0.0, step=1.0, format="%.2f")
        obs_aporte = st.text_input("Observações (opcional)")
        if st.form_submit_button("Adicionar", type="primary"):
            if valor_aporte > 0:
                valor_final = valor_aporte if tipo_aporte == "Aporte" else -valor_aporte
                insert_aporte({
                    "data": data_aporte.isoformat(),
                    "valor": valor_final,
                    "observacoes": obs_aporte or None,
                })
                st.success(f"{tipo_aporte} de {fmt_brl(valor_aporte)} registrado.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Informe um valor maior que zero.")

    st.write("")
    aportes = get_aportes()
    if aportes.empty:
        st.caption("Nenhum aporte ou resgate registrado ainda.")
    else:
        st.metric("Saldo líquido de aportes/resgates", fmt_brl(float(aportes["valor"].sum())))
        tabela_aportes = aportes.sort_values("data", ascending=False).copy()
        tabela_aportes["Data"] = tabela_aportes["data"].dt.strftime("%d/%m/%Y")
        for _, linha in tabela_aportes.iterrows():
            c1, c2, c3, c4 = st.columns([2, 2, 4, 1])
            c1.write(linha["Data"])
            c2.write(fmt_brl(linha["valor"]))
            c3.write(linha["observacoes"] or "—")
            if c4.button("🗑️", key=f"del_aporte_{linha['id']}", help="Excluir"):
                delete_aporte(int(linha["id"]))
                st.cache_data.clear()
                st.rerun()
