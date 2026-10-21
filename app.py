"""TurboGuard — AI predictive maintenance for industrial machines (Streamlit + scikit-learn)."""
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import auth
import model as M
import theme
from ui import badge, hero, kpis, result_card, sidebar_brand

APP = dict(
    name="TurboGuard", short="Predictive maintenance", icon="⚙️", tagline="Fix machines before they fail.",
    description="Remaining-useful-life prediction, failure-mode diagnosis and live anomaly detection for your whole fleet of turbines, pumps, compressors and motors.",
    features=["RUL regression with uncertainty (Gradient Boosting / Random Forest)", "30-cycle failure-risk classifier (AUC ≈ 0.99)", "Failure-mode diagnosis & recommended actions", "Live sensor monitor, maintenance planner & cost optimiser"],
    card1="⚠️ PUM-111 · RUL 38 cycles · Overheating", card2="💰 ₹27.5 L downtime avoided",
    demo_name="Bharath Kumar", demo_email="demo@turboguard.app", demo_password="Demo@1234",
    roles=["Maintenance engineer", "Plant manager", "Reliability analyst", "Student"],
)
STATUS_C = {"Healthy": "#10b981", "Warning": "#f59e0b", "Critical": "#ef4444"}
inr = lambda v: f"₹{v / 1e5:,.1f} L" if v >= 1e5 else f"₹{v:,.0f}"

st.set_page_config(page_title="TurboGuard — Predictive Maintenance", page_icon="⚙️", layout="wide")
theme.inject("Sunset")


@st.cache_data(show_spinner="Simulating 120 run-to-failure histories and a 36-machine fleet…")
def load():
    return M.generate()


@st.cache_resource(show_spinner="Training RUL, failure-risk, failure-mode and anomaly models (≈20 s, first run only)…")
def models():
    return M.train_all(load()[0])


if "user" not in st.session_state:
    auth.auth_page(APP)
    st.stop()

user = st.session_state.user
sidebar_brand(APP, user)
PAGES = ["🏭 Fleet overview", "🔧 Machine detail", "📡 Live sensor monitor", "🗓️ Maintenance planner", "🤖 Model lab", "👤 Account"]
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
rul_name = st.sidebar.selectbox("RUL model", ["Gradient Boosting", "Random Forest"])
theme.theme_controls()
if st.sidebar.button("Log out", width="stretch"):
    auth.logout()

hist, fleet, meta = load()
R = models()
A = M.assess(R, fleet, meta, rul_name)
A["icon"] = A["type"].map(M.TYPES)

# ------------------------------------------------------------------ Fleet
if page == PAGES[0]:
    hero("Fleet health overview", f'<span class="live-dot"></span>{len(A)} machines across 4 production lines · model: {rul_name}', "🏭")
    crit, warn = (A.status == "Critical").sum(), (A.status == "Warning").sum()
    risk_cost = (A.p_fail * M.COST["corrective"]).sum()
    kpis([
        ("🟢", "Healthy", f"{(A.status == 'Healthy').sum()}", f"avg health {A.health.mean():.0f}/100"),
        ("🟠", "Warning", f"{warn}", "schedule within 2 weeks"),
        ("🔴", "Critical", f"{crit}", "act now"),
        ("💸", "Expected failure cost", inr(risk_cost), "if no action is taken"),
    ])
    st.write("")
    c1, c2 = st.columns([1.35, 1])
    with c1:
        fig = go.Figure()
        for stt, col in STATUS_C.items():
            s = A[A.status == stt]
            fig.add_trace(go.Scatter(x=s.x, y=s.y, mode="markers+text", name=stt, text=s.icon, textfont=dict(size=20),
                                     marker=dict(size=46, color=col, opacity=0.25, line=dict(color=col, width=3)),
                                     customdata=np.stack([s.machine, s.RUL, s.p_fail * 100, s.line], axis=1),
                                     hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[3]}<br>RUL %{customdata[1]:.0f} cycles<br>Failure risk %{customdata[2]:.0f}%<extra></extra>"))
        for i in range(1, 5):
            fig.add_hrect(y0=i - 0.45, y1=i + 0.45, line_width=0, fillcolor="rgba(148,163,184,.08)")
            fig.add_annotation(x=0.2, y=i, text=f"Line {i}", showarrow=False, font=dict(size=11))
        fig.update_layout(title="Plant floor — hover a machine", height=420, xaxis=dict(visible=False, range=[-0.3, 9.6]), yaxis=dict(visible=False, range=[0.4, 4.6], autorange="reversed"), legend=dict(orientation="h", y=-0.05))
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = px.histogram(A, x="RUL", color="status", nbins=20, color_discrete_map=STATUS_C, title="Remaining useful life distribution")
        fig.update_layout(height=200, bargap=0.05, showlegend=False)
        st.plotly_chart(fig, width="stretch")
        fig = px.sunburst(A, path=["line", "type", "status"], color="status", color_discrete_map={**STATUS_C, "(?)": "#94a3b8"}, title="Fleet composition")
        fig.update_layout(height=230, margin=dict(t=40, l=0, r=0, b=0))
        st.plotly_chart(fig, width="stretch")
    st.markdown("#### 🚨 Priority list")
    view = A.sort_values(["p_fail", "RUL"], ascending=[False, True])[["icon", "machine", "type", "line", "criticality", "status", "health", "RUL", "p_fail", "mode"]]
    view["mode"] = np.where(A.loc[view.index, "status"] == "Healthy", "—", view["mode"])
    st.dataframe(view.rename(columns={"icon": "", "p_fail": "Failure risk", "mode": "Likely failure mode", "health": "Health"}), hide_index=True, width="stretch",
                 column_config={"Failure risk": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"), "Health": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"), "RUL": st.column_config.NumberColumn("RUL (cycles)", format="%d")})

# ------------------------------------------------------------------ Machine detail
elif page == PAGES[1]:
    order = A.sort_values("p_fail", ascending=False).machine.tolist()
    mid = st.selectbox("Machine", order, format_func=lambda m: f"{A.set_index('machine').loc[m, 'icon']} {m} — {A.set_index('machine').loc[m, 'status']}")
    r = A.set_index("machine").loc[mid]
    d = fleet[fleet.machine == mid]
    hero(f"{r.icon} {mid} · {r.type}", f"{r.line} · installed {r.installed} · criticality {r.criticality} · cycle {int(r.cycle)}", "🔧")
    c1, c2, c3 = st.columns([1, 1, 1.2])
    with c1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=r.health, title={"text": "Health score"}, number={"suffix": "/100"},
                                     gauge={"axis": {"range": [0, 100]}, "bar": {"color": STATUS_C[r.status]}, "steps": [{"range": [0, 30], "color": "#ef444433"}, {"range": [30, 60], "color": "#f59e0b33"}, {"range": [60, 100], "color": "#10b98133"}]}))
        fig.update_layout(height=260)
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=r.p_fail * 100, title={"text": f"Failure risk (next {M.WINDOW} cycles)"}, number={"suffix": "%"},
                                     gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#ef4444" if r.p_fail > 0.5 else "#f59e0b" if r.p_fail > 0.25 else "#10b981"}}))
        fig.update_layout(height=260)
        st.plotly_chart(fig, width="stretch")
    with c3:
        result_card("Remaining useful life", f"{r.RUL:.0f} cycles", f"80% interval {r.RUL_lo:.0f}–{r.RUL_hi:.0f} cycles · status {r.status}", STATUS_C[r.status], "#1f2937", "⏳")
        if r.status != "Healthy":
            st.markdown(f"**Likely failure mode:** {badge(r['mode'], 'bad')} {r.mode_conf * 100:.0f}% confidence", unsafe_allow_html=True)
        else:
            st.markdown(f"**Failure mode:** {badge('No dominant degradation pattern yet', 'good')}", unsafe_allow_html=True)
    st.markdown("#### 📈 Sensor trends")
    iso_scores = -R["iso"].score_samples(d[M.SENSORS])
    thr = np.quantile(-R["iso"].score_samples(hist[hist.cycle <= 60][M.SENSORS]), 0.98)
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2, cols=3, subplot_titles=[f"{s.replace('_', ' ').title()} ({M.UNITS[s]})" for s in M.SENSORS], vertical_spacing=0.14)
    an = d[iso_scores > thr]
    for i, s in enumerate(M.SENSORS):
        rr, cc = i // 3 + 1, i % 3 + 1
        fig.add_trace(go.Scatter(x=d.cycle, y=d[s], line=dict(width=1.6), showlegend=False), rr, cc)
        fig.add_trace(go.Scatter(x=d.cycle, y=d[s].rolling(10, min_periods=1).mean(), line=dict(width=2.5, color="#f59e0b"), showlegend=False), rr, cc)
        fig.add_trace(go.Scatter(x=an.cycle, y=an[s], mode="markers", marker=dict(color="#ef4444", size=5), showlegend=False), rr, cc)
    fig.update_layout(height=520, title="Raw (blue), 10-cycle mean (orange), anomalies flagged by Isolation Forest (red)")
    st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns([1, 1])
    with c1:
        imp = M.importance(R, rul_name)
        fig = px.bar(imp, orientation="h", title="What the RUL model looks at")
        fig.update_layout(height=380, showlegend=False, yaxis_title="", xaxis_title="importance")
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.markdown("#### 🛠️ Recommended actions")
        acts = M.ACTIONS[r["mode"]] if r.status != "Healthy" else ["Continue routine inspection schedule", "Log vibration & oil sample next shift", "No intervention required"]
        for i, a in enumerate(acts, 1):
            st.markdown(f'<div class="card" style="margin-bottom:8px"><b>{i}.</b> {a}</div>', unsafe_allow_html=True)
        save = M.COST["corrective"] + M.COST["downtime_per_cycle"] * 6 - M.COST["preventive"]
        st.markdown(f'<div class="card">💰 Acting now saves an estimated <b>{inr(save * r.p_fail)}</b> in expected failure cost.</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ Live monitor
elif page == PAGES[2]:
    hero("Live sensor monitor", "Streaming readings scored in real time by the Isolation Forest anomaly detector", "📡")
    c1, c2, c3 = st.columns([1.2, 1, 1])
    mid = c1.selectbox("Machine", A.sort_values("p_fail", ascending=False).machine)
    inject = c2.selectbox("Inject fault", ["None", "Vibration spike", "Overheat", "Pressure drop", "Current surge"])
    run = c3.toggle("▶️ Live", value=False)
    key = f"live_{mid}"
    if key not in st.session_state:
        base = fleet[fleet.machine == mid].tail(40)
        st.session_state[key] = base[M.SENSORS].to_dict("records")
        st.session_state.setdefault("alarms", [])
    if run:
        last = st.session_state[key][-1]
        rng = np.random.default_rng(int(time.time() * 1000) % 2**32)
        new = {s: last[s] + rng.normal(0, M.SCALE[s] * 0.06) + (M.BASE[s] - last[s]) * 0.02 for s in M.SENSORS}
        if inject == "Vibration spike":
            new["vibration"] += M.SCALE["vibration"] * 2.5
        elif inject == "Overheat":
            new["temperature"] += M.SCALE["temperature"] * 2.2
        elif inject == "Pressure drop":
            new["pressure"] -= M.SCALE["pressure"] * 2.5
        elif inject == "Current surge":
            new["current"] += M.SCALE["current"] * 2.4
        st.session_state[key] = (st.session_state[key] + [new])[-120:]
    live = pd.DataFrame(st.session_state[key])
    live["t"] = range(len(live))
    live["score"] = -R["iso"].score_samples(live[M.SENSORS])
    thr = np.quantile(-R["iso"].score_samples(hist[hist.cycle <= 60][M.SENSORS]), 0.98)
    cur = live.iloc[-1]
    is_anom = cur.score > thr
    if is_anom and run:
        worst = max(M.SENSORS, key=lambda s: abs(cur[s] - M.BASE[s]) / M.SCALE[s])
        st.session_state.alarms.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "machine": mid, "sensor": worst, "value": round(cur[worst], 2), "score": round(cur.score, 3)})
    kp = [(("🔥" if s == "temperature" else "📳" if s == "vibration" else "🧭" if s == "pressure" else "🔄" if s == "rpm" else "⚡" if s == "current" else "🛢️"), s.replace("_", " ").title(), f"{cur[s]:.1f}", M.UNITS[s]) for s in M.SENSORS]
    kpis(kp[:3])
    st.write("")
    kpis(kp[3:])
    if is_anom:
        st.error(f"🚨 ANOMALY detected on {mid} — score {cur.score:.3f} > threshold {thr:.3f}")
    else:
        st.success(f"✅ {mid} operating within normal envelope (score {cur.score:.3f})")
    c1, c2 = st.columns([1.6, 1])
    with c1:
        fig = go.Figure()
        for s in ["temperature", "vibration", "pressure", "current"]:
            z = (live[s] - M.BASE[s]) / M.SCALE[s]
            fig.add_trace(go.Scatter(x=live.t, y=z, name=s, mode="lines"))
        fig.update_layout(title="Normalised sensor streams (z-score)", height=340, hovermode="x unified")
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = go.Figure(go.Scatter(x=live.t, y=live.score, fill="tozeroy", line=dict(color="#ef4444" if is_anom else "#10b981")))
        fig.add_hline(y=thr, line_dash="dash", annotation_text="threshold")
        fig.update_layout(title="Anomaly score", height=340)
        st.plotly_chart(fig, width="stretch")
    st.markdown("#### 🔔 Alarm log")
    if st.session_state.get("alarms"):
        st.dataframe(pd.DataFrame(st.session_state.alarms[:50]), hide_index=True, width="stretch")
    else:
        st.caption("No alarms yet — switch Live on and inject a fault to see detection in action.")
    if run:
        time.sleep(1.5)
        st.rerun()

# ------------------------------------------------------------------ Planner
elif page == PAGES[3]:
    hero("Maintenance planner", "Optimise when to service each machine — preventive vs. run-to-failure economics", "🗓️")
    c1, c2, c3 = st.columns(3)
    prev = c1.number_input("Preventive job cost (₹)", 10000, 500000, M.COST["preventive"], 5000)
    corr = c2.number_input("Breakdown repair cost (₹)", 50000, 2000000, M.COST["corrective"], 10000)
    techs = c3.slider("Technician crews available", 1, 6, 3)
    risk_thr = st.slider("Schedule machines with failure risk above", 0.05, 0.9, 0.2, 0.05, format="%.2f")
    todo = A[(A.p_fail >= risk_thr) | (A.RUL <= 60)].sort_values(["RUL"]).copy()
    start = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    jobs = []
    crew_free = [start] * techs
    for r in todo.itertuples():
        c = int(np.argmin(crew_free))
        deadline = start + timedelta(days=max(1, int(r.RUL_lo // 3)))
        s = max(crew_free[c], start)
        dur = timedelta(hours={"Turbine": 10, "Compressor": 7, "Pump": 5, "Motor": 4}[r.type])
        e = s + dur
        crew_free[c] = e + timedelta(hours=14) if e.hour >= 18 else e
        jobs.append({"Machine": r.machine, "Crew": f"Crew {c + 1}", "Start": s, "Finish": e, "Status": r.status, "Mode": r.mode, "Deadline": deadline, "On time": e <= deadline})
    J = pd.DataFrame(jobs)
    expected_fail = (todo.p_fail * corr).sum()
    plan_cost = len(todo) * prev
    kpis([
        ("🧰", "Jobs scheduled", f"{len(todo)}", f"{techs} crews"),
        ("💸", "Plan cost", inr(plan_cost), "preventive work"),
        ("🔥", "Avoided failure cost", inr(expected_fail), "expected"),
        ("📈", "Net saving", inr(expected_fail - plan_cost), f"ROI {((expected_fail - plan_cost) / max(plan_cost, 1)) * 100:.0f}%"),
    ])
    if len(J):
        fig = px.timeline(J, x_start="Start", x_end="Finish", y="Crew", color="Status", text="Machine", color_discrete_map=STATUS_C, title="Work-order schedule")
        fig.update_layout(height=320)
        st.plotly_chart(fig, width="stretch")
        late = (~J["On time"]).sum()
        if late:
            st.warning(f"⚠️ {late} job(s) finish after the machine's conservative RUL deadline — add a crew or raise priority.")
        st.dataframe(J.assign(Start=J.Start.dt.strftime("%d %b %H:%M"), Finish=J.Finish.dt.strftime("%d %b %H:%M"), Deadline=J.Deadline.dt.strftime("%d %b")), hide_index=True, width="stretch")
        st.download_button("⬇️ Export work orders (CSV)", J.to_csv(index=False), "turboguard_work_orders.csv", "text/csv", type="primary")
    thr_grid = np.linspace(0.05, 0.9, 18)
    curve = [{"threshold": t, "total": ((A.p_fail >= t) | (A.RUL <= 60)).sum() * prev + (A.p_fail * corr * ~((A.p_fail >= t) | (A.RUL <= 60))).sum()} for t in thr_grid]
    cv = pd.DataFrame(curve)
    fig = px.line(cv, x="threshold", y="total", markers=True, title="Total expected cost vs scheduling threshold (lower is better)")
    best = cv.loc[cv.total.idxmin()]
    fig.add_vline(x=best.threshold, line_dash="dot", annotation_text=f"optimum ≈ {best.threshold:.2f}")
    fig.update_layout(height=330, yaxis_title="₹")
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ Model lab
elif page == PAGES[4]:
    hero("Model lab", "Evaluated on 30 machines held out by machine ID (no leakage across a unit’s life)", "🤖")
    rows = {n: {k: v[k] for k in ["RMSE", "MAE", "R²", "NASA score"]} for n, v in R["rul"].items()}
    st.markdown("##### ⏳ RUL regression (target capped at 150 cycles)")
    st.dataframe(pd.DataFrame(rows).T.round(3), width="stretch")
    kpis([("🎯", "Failure-risk AUC", f"{R['fail']['AUC']:.3f}", f"F1 {R['fail']['F1']:.3f}"), ("🩺", "Failure-mode accuracy", f"{R['mode']['Accuracy'] * 100:.1f}%", "late-life cycles"), ("🌲", "Anomaly detector", "Isolation Forest", "trained on healthy cycles")])
    c1, c2 = st.columns(2)
    with c1:
        sel = R["rul"][rul_name]
        dd = pd.DataFrame({"actual": R["y_rul_te"], "pred": sel["pred"]}).sample(2500, random_state=0)
        fig = px.scatter(dd, x="actual", y="pred", opacity=0.35, title=f"{rul_name}: predicted vs actual RUL")
        fig.add_shape(type="line", x0=0, y0=0, x1=150, y1=150, line=dict(dash="dot"))
        fig.update_layout(height=380)
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = go.Figure(go.Scatter(x=R["fail"]["fpr"], y=R["fail"]["tpr"], fill="tozeroy", name="ROC"))
        fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(dash="dot"))
        fig.update_layout(title=f"Failure within {M.WINDOW} cycles — ROC (AUC {R['fail']['AUC']:.3f})", height=380, xaxis_title="False positive rate", yaxis_title="True positive rate")
        st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.imshow(R["mode"]["cm"], x=M.MODES, y=M.MODES, text_auto=True, color_continuous_scale="Oranges", title="Failure-mode confusion matrix", labels=dict(x="Predicted", y="Actual"))
        fig.update_layout(height=380)
        st.plotly_chart(fig, width="stretch")
    with c2:
        ex = hist[hist.machine == "H003"]
        fig = px.line(ex, x="cycle", y="RUL", title="Example run-to-failure unit: true RUL vs capped target")
        fig.add_scatter(x=ex.cycle, y=ex.RUL.clip(upper=150), name="capped target", line=dict(dash="dash"))
        fig.update_layout(height=380)
        st.plotly_chart(fig, width="stretch")
    st.info("Features per sensor: raw value, 10-cycle rolling mean & std, slope over 10 cycles and drift from the unit’s own early-life baseline — 31 features in total.")

# ------------------------------------------------------------------ Account
else:
    hero(f"Hi, {user['name'].split()[0]} 👋", f"{user['email']} · {user['role']} · member since {user['created'][:10]}", "👤")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🔒 Change password")
        with st.form("pw"):
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            if st.form_submit_button("Update password", type="primary"):
                try:
                    auth.change_password(user["email"], old, new)
                    st.success("Password updated")
                except ValueError as e:
                    st.error(str(e))
    with c2:
        st.markdown("##### 🏭 Data")
        st.markdown(f'<div class="card">{hist.machine.nunique()} historical run-to-failure units ({len(hist):,} cycles) and a live fleet of {len(meta)} machines with 6 sensors each. Registered users: <b>{auth.user_count()}</b>.</div>', unsafe_allow_html=True)
        st.download_button("⬇️ Fleet assessment (CSV)", A.to_csv(index=False), "turboguard_fleet.csv", "text/csv")
