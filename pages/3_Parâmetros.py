import streamlit as st

from lib.db import get_ativos, get_parametros, update_ativo, update_parametros
from lib.ui import header, setup_page

setup_page("Parâmetros", "⚙️")
header("Parâmetros", "Conta e ativos — tudo abaixo recalcula automaticamente", "⚙️")

tab_conta, tab_ativos = st.tabs(["Conta", "Ativos"])

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
