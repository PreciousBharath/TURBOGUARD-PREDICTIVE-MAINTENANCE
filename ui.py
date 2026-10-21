"""Small HTML components (hero banner, KPI cards, result cards) used across pages."""
import streamlit as st


def hero(title, subtitle, emoji=""):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p><span class="emoji">{emoji}</span></div>', unsafe_allow_html=True)


def kpis(items):
    """items: list of (icon, label, value, sub)"""
    cols = st.columns(len(items))
    for i, (col, (icon, label, value, sub)) in enumerate(zip(cols, items)):
        col.markdown(
            f'<div class="kpi" style="animation-delay:{i * 70}ms"><div class="ic">{icon}</div>'
            f'<div><div class="lbl">{label}</div><div class="val">{value}</div><div class="sub">{sub}</div></div></div>',
            unsafe_allow_html=True,
        )


def result_card(title, value, text, color1, color2, icon=""):
    st.markdown(
        f'<div class="result" style="background:linear-gradient(135deg,{color1},{color2})"><small>{icon} {title}</small><h2>{value}</h2><p>{text}</p></div>',
        unsafe_allow_html=True,
    )


def badge(text, kind=""):
    return f'<span class="badge {kind}">{text}</span>'


def sidebar_brand(app, user):
    st.sidebar.markdown(
        f'<div class="sidebar-brand"><span class="logo">{app["icon"]}</span><div><b>{app["name"]}</b><small>{app["short"]}</small></div></div>'
        f'<div class="user-chip"><span class="av">{user["name"][0].upper()}</span><div><b>{user["name"]}</b><small>{user["email"]} · {user["role"]}</small></div></div>',
        unsafe_allow_html=True,
    )
