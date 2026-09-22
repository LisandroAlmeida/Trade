"""Componentes visuais compartilhados entre as páginas do app."""
import streamlit as st

CSS = """
<style>
    #MainMenu, footer {visibility: hidden;}

    .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1100px;}

    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px 18px 12px 18px;
    }
    [data-testid="stMetricLabel"] { font-size: 0.82rem; opacity: 0.75; }
    [data-testid="stMetricValue"] { font-size: 1.55rem; }

    .twt-header {
        display: flex; align-items: center; gap: 14px;
        padding-bottom: 4px; margin-bottom: 6px;
    }
    .twt-header .icon {
        font-size: 1.9rem; line-height: 1;
        background: rgba(61, 214, 140, 0.12);
        border-radius: 10px; padding: 8px 10px;
    }
    .twt-header h1 { font-size: 1.55rem; margin: 0; }
    .twt-header .subtitle { opacity: 0.65; font-size: 0.88rem; margin-top: 2px; }

    .twt-badge {
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 500;
    }
    .twt-badge.real { background: rgba(61, 214, 140, 0.16); color: #3DD68C; }
    .twt-badge.estimado { background: rgba(230, 180, 60, 0.16); color: #E6B43C; }

    div[data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
    }

    .twt-mini-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px dashed rgba(255, 255, 255, 0.18);
        border-radius: 10px;
        padding: 10px 12px 8px 12px;
    }
    .twt-mini-card .label { font-size: 0.74rem; opacity: 0.65; }
    .twt-mini-card .value { font-size: 1.1rem; font-weight: 600; margin-top: 2px; }
    .twt-mini-card .delta { font-size: 0.74rem; color: #3DD68C; margin-top: 2px; }
</style>
"""


def setup_page(title: str, icon: str) -> None:
    st.set_page_config(page_title=f"{title} — Trade WIN", page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def header(title: str, subtitle: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="twt-header">
            <div class="icon">{icon}</div>
            <div>
                <h1>{title}</h1>
                <div class="subtitle">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fmt_brl(valor) -> str:
    """Formata número no padrão brasileiro: R$ 1.234,56"""
    if valor is None:
        return "—"
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {texto}"


def fmt_pct(valor, casas: int = 1) -> str:
    if valor is None:
        return "—"
    return f"{valor * 100:.{casas}f}%".replace(".", ",")


def badge_confirmado(confirmado: bool) -> str:
    if confirmado:
        return '<span class="twt-badge real">✓ real</span>'
    return '<span class="twt-badge estimado">⏳ estimado</span>'


def mini_card(titulo: str, valor: str, legenda: str) -> str:
    """Card pequeno com borda tracejada — usado pra deixar claro que é uma projeção/estimativa,
    não um número real calculado a partir das operações lançadas."""
    return f"""
    <div class="twt-mini-card">
        <div class="label">{titulo}</div>
        <div class="value">{valor}</div>
        <div class="delta">{legenda}</div>
    </div>
    """
