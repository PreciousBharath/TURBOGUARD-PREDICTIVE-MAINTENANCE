"""Five switchable themes, accent colours and animated CSS for Streamlit, plus a matching Plotly template."""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

THEMES = {
    "Light": dict(bg="#f5f6fb", surface="#ffffff", surface2="#f1f3f9", text="#171a2b", muted="#6b7088", border="#e3e5f0", dark=False),
    "Dark": dict(bg="#0f1117", surface="#181b26", surface2="#1f2330", text="#e8eaf3", muted="#9096ad", border="#2a2f3e", dark=True),
    "Midnight": dict(bg="#070b1d", surface="#0f1736", surface2="#152048", text="#e6ecff", muted="#8d9bd0", border="#1f2c5c", dark=True),
    "Sepia": dict(bg="#f4ecdf", surface="#fbf6ee", surface2="#f2e8d8", text="#3b2f22", muted="#85715a", border="#e2d4bd", dark=False),
    "Forest": dict(bg="#0c1a14", surface="#11241c", surface2="#173026", text="#e3f5ec", muted="#8fb8a5", border="#1f3d31", dark=True),
}
ACCENTS = {"Violet": "#7c3aed", "Ocean": "#0ea5e9", "Emerald": "#10b981", "Sunset": "#f97316", "Rose": "#e11d48", "Gold": "#d4a017"}


def current():
    t = THEMES[st.session_state.get("theme", "Light")]
    a = ACCENTS[st.session_state.get("accent", st.session_state.get("default_accent", "Violet"))]
    return t, a


def theme_controls():
    st.session_state.setdefault("theme", "Light")
    st.session_state.setdefault("accent", st.session_state.get("default_accent", "Violet"))
    with st.sidebar.expander("🎨 Appearance", expanded=False):
        st.selectbox("Theme", list(THEMES), key="theme")
        st.selectbox("Accent", list(ACCENTS), key="accent")
        st.toggle("Animations", value=True, key="anim")


def inject(default_accent="Violet"):
    st.session_state.setdefault("default_accent", default_accent)
    t, a = current()
    anim = "" if st.session_state.get("anim", True) else "*{animation:none!important;transition:none!important}"
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root {{ --bg:{t['bg']}; --surface:{t['surface']}; --surface2:{t['surface2']}; --text:{t['text']}; --muted:{t['muted']}; --border:{t['border']}; --accent:{a}; --accent2: color-mix(in srgb, {a} 60%, #ec4899); --soft: color-mix(in srgb, {a} 14%, transparent); }}
html, body, [class*="css"], .stApp, .stMarkdown, p, label, li, span, div {{ font-family:'Plus Jakarta Sans', system-ui, sans-serif; }}
.stApp {{ background: var(--bg); color: var(--text); }}
.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp span, .stMarkdown, [data-testid="stMetricValue"], [data-testid="stWidgetLabel"] p {{ color: var(--text); }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: var(--surface); border-right: 1px solid var(--border); }}
[data-testid="stSidebar"] * {{ color: var(--text); }}
.block-container {{ padding-top: 2rem; max-width: 1350px; animation: pageIn .5s cubic-bezier(.2,.8,.2,1); }}
[data-testid="stCaptionContainer"], .stCaption, small {{ color: var(--muted) !important; }}
div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {{ background: var(--surface2) !important; color: var(--text) !important; border-color: var(--border) !important; border-radius: 10px !important; }}
div[data-baseweb="popover"] li {{ color: #111; }}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{ border-radius: 10px; font-weight: 700; border: 1px solid var(--border); background: var(--surface2); color: var(--text); transition: transform .15s, box-shadow .2s; }}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{ transform: translateY(-2px); border-color: var(--accent); color: var(--accent); }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{ background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #fff !important; border: 0; box-shadow: 0 6px 18px color-mix(in srgb, var(--accent) 35%, transparent); }}
.stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] p {{ color:#fff !important; }}
[data-testid="stForm"] {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 18px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{ border-radius: 10px 10px 0 0; padding: 8px 14px; }}
.stTabs [aria-selected="true"] p {{ color: var(--accent) !important; font-weight: 700; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--accent); }}
[data-testid="stMetric"] {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 14px 16px; box-shadow: 0 8px 24px rgba(20,22,40,.06); animation: pop .5s both; }}
[data-testid="stExpander"] {{ background: var(--surface); border: 1px solid var(--border) !important; border-radius: 14px; }}
[data-testid="stDataFrame"], .stPlotlyChart {{ border-radius: 14px; overflow: hidden; }}
.stSlider [data-baseweb="slider"] div[role="slider"] {{ background: var(--accent); }}
hr {{ border-color: var(--border); }}
/* ---------- custom components ---------- */
.hero {{ position: relative; overflow: hidden; border-radius: 22px; padding: 28px 30px; color: #fff; background: radial-gradient(circle at 88% 12%, rgba(255,255,255,.28), transparent 42%), linear-gradient(120deg, var(--accent), var(--accent2)); box-shadow: 0 20px 50px color-mix(in srgb, var(--accent) 30%, transparent); animation: fadeUp .6s both; margin-bottom: 18px; }}
.hero h1 {{ color: #fff !important; margin: 0 0 6px; font-size: 2rem; letter-spacing: -.02em; }}
.hero p {{ color: rgba(255,255,255,.9) !important; margin: 0; }}
.hero .emoji {{ position: absolute; right: 30px; top: 18px; font-size: 80px; line-height: 1; animation: float 4s ease-in-out infinite; }}
.hero *, .result *, .auth-hero *, .hero h1 span, .result h2 span {{ color: #fff !important; }}
.user-chip b, .user-chip small {{ display: block; }} .user-chip small {{ font-size: .75rem; }}
.kpi {{ background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 16px 18px; display: flex; gap: 14px; align-items: center; box-shadow: 0 8px 24px rgba(20,22,40,.06); animation: pop .55s both; transition: transform .25s, box-shadow .25s; }}
.kpi:hover {{ transform: translateY(-4px); box-shadow: 0 18px 40px rgba(20,22,40,.14); }}
.kpi .ic {{ width: 48px; height: 48px; border-radius: 14px; display: grid; place-items: center; font-size: 22px; background: var(--soft); flex-shrink: 0; }}
.kpi .lbl {{ color: var(--muted); font-size: .8rem; font-weight: 700; }}
.kpi .val {{ font-size: 1.55rem; font-weight: 800; letter-spacing: -.02em; color: var(--text); }}
.kpi .sub {{ font-size: .78rem; color: var(--muted); }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 18px; box-shadow: 0 8px 24px rgba(20,22,40,.06); animation: fadeUp .5s both; }}
.badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .75rem; font-weight: 800; background: var(--soft); color: var(--accent); }}
.badge.good {{ background: rgba(16,185,129,.15); color: #10b981; }} .badge.warn {{ background: rgba(245,158,11,.18); color: #d97706; }} .badge.bad {{ background: rgba(239,68,68,.14); color: #ef4444; }}
.result {{ border-radius: 20px; padding: 22px; color: #fff; animation: pop .55s cubic-bezier(.2,1.3,.4,1) both; box-shadow: 0 16px 40px rgba(0,0,0,.18); }}
.result h2 {{ color: #fff !important; margin: 4px 0; font-size: 2rem; }} .result p, .result small {{ color: rgba(255,255,255,.92) !important; }}
.pill-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.pill {{ padding: 6px 12px; border-radius: 999px; background: var(--surface2); border: 1px solid var(--border); font-size: .85rem; font-weight: 600; }}
.sidebar-brand {{ display: flex; gap: 10px; align-items: center; padding: 4px 0 12px; }}
.sidebar-brand .logo {{ width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; font-size: 22px; background: linear-gradient(135deg, var(--accent), var(--accent2)); box-shadow: 0 8px 20px color-mix(in srgb, var(--accent) 35%, transparent); }}
.sidebar-brand b {{ font-size: 1.15rem; }} .sidebar-brand small {{ display:block; }}
.user-chip {{ display:flex; gap:10px; align-items:center; padding:10px; border-radius:12px; background: var(--surface2); border:1px solid var(--border); margin: 8px 0; }}
.user-chip .av {{ width:34px; height:34px; border-radius:50%; display:grid; place-items:center; background: var(--soft); color: var(--accent); font-weight:800; }}
.live-dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; background:#ef4444; margin-right:6px; animation: pulse 1.6s infinite; }}
.pw-meter {{ height: 8px; border-radius: 99px; background: var(--surface2); overflow: hidden; border:1px solid var(--border); }} .pw-meter div {{ height: 100%; transition: width .4s; }}
/* auth */
.auth-hero {{ position: relative; overflow: hidden; border-radius: 26px; min-height: 640px; padding: 46px; color: #fff; background: linear-gradient(140deg, color-mix(in srgb, var(--accent) 85%, #000), var(--accent2)); display:flex; align-items:center; }}
.auth-inner {{ position: relative; z-index: 2; }}
.auth-hero h1 {{ color:#fff !important; font-size: 2.6rem; line-height:1.1; margin: 22px 0 10px; }}
.auth-hero p {{ color: rgba(255,255,255,.9) !important; font-size: 1.05rem; }}
.auth-hero .brand {{ display:flex; gap:10px; align-items:center; font-size:1.3rem; }} .auth-hero .brand b {{ color:#fff; }}
.auth-hero .logo {{ width:46px; height:46px; border-radius:14px; display:grid; place-items:center; font-size:24px; background: rgba(255,255,255,.2); }}
.hero-points {{ list-style:none; padding:0; margin:22px 0; }} .hero-points li {{ color:#fff !important; display:flex; gap:10px; align-items:center; margin: 10px 0; animation: slideIn .5s both; }}
.hero-points span {{ width:22px; height:22px; border-radius:50%; display:grid; place-items:center; background: rgba(255,255,255,.22); font-size:12px; color:#fff !important; }}
.float-row {{ display:flex; gap:14px; flex-wrap:wrap; margin-top: 18px; }}
.float-card {{ background: rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.25); backdrop-filter: blur(10px); border-radius: 14px; padding: 10px 14px; color:#fff !important; animation: float 5s ease-in-out infinite; font-weight:600; }}
.blob {{ position:absolute; border-radius:50%; filter: blur(50px); animation: blob 14s ease-in-out infinite; }}
.b1 {{ width:380px; height:380px; background:#fff; top:-120px; right:-80px; opacity:.18; }} .b2 {{ width:300px; height:300px; background:#ffd166; bottom:-100px; left:-60px; opacity:.25; animation-delay:-5s; }} .b3 {{ width:220px; height:220px; background:#06d6a0; top:40%; left:45%; opacity:.2; animation-delay:-9s; }}
.auth-spacer {{ height: 70px; }}
@keyframes fadeUp {{ from {{ opacity:0; transform: translateY(14px); }} to {{ opacity:1; transform:none; }} }}
@keyframes pageIn {{ from {{ opacity:0; transform: translateY(8px); }} to {{ opacity:1; transform:none; }} }}
@keyframes pop {{ from {{ opacity:0; transform: scale(.94); }} to {{ opacity:1; transform:none; }} }}
@keyframes slideIn {{ from {{ opacity:0; transform: translateX(-12px); }} to {{ opacity:1; transform:none; }} }}
@keyframes float {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-10px); }} }}
@keyframes blob {{ 0%,100% {{ transform: translate(0,0) scale(1); }} 33% {{ transform: translate(40px,-30px) scale(1.1); }} 66% {{ transform: translate(-30px,30px) scale(.92); }} }}
@keyframes pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(239,68,68,.6); }} 70% {{ box-shadow: 0 0 0 9px rgba(239,68,68,0); }} 100% {{ box-shadow:0 0 0 0 rgba(239,68,68,0); }} }}
{anim}
</style>""",
        unsafe_allow_html=True,
    )
    _plotly_template(t, a)


def _plotly_template(t, a):
    base = "plotly_dark" if t["dark"] else "plotly_white"
    tpl = go.layout.Template(pio.templates[base])
    tpl.layout.update(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color=t["text"]),
        colorway=[a, "#f59e0b", "#10b981", "#0ea5e9", "#ec4899", "#8b5cf6", "#ef4444", "#14b8a6"],
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor=t["border"], zerolinecolor=t["border"]),
        yaxis=dict(gridcolor=t["border"], zerolinecolor=t["border"]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    pio.templates["app"] = tpl
    pio.templates.default = "app"


def accent():
    return current()[1]
