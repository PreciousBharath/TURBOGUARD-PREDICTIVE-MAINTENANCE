"""TurboGuard engine: run-to-failure sensor simulation, RUL regression, failure-window classification,
failure-mode diagnosis and Isolation-Forest anomaly scoring."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_absolute_error, mean_squared_error, r2_score, roc_auc_score, roc_curve
from sklearn.model_selection import GroupShuffleSplit

SENSORS = ["temperature", "vibration", "pressure", "rpm", "current", "oil_quality"]
UNITS = {"temperature": "°C", "vibration": "mm/s", "pressure": "bar", "rpm": "rpm", "current": "A", "oil_quality": "%"}
TYPES = {"Turbine": "🌀", "Compressor": "🗜️", "Pump": "💧", "Motor": "⚙️"}
MODES = ["Bearing wear", "Overheating", "Seal leak", "Electrical fault"]
MODE_EFFECT = {  # sensor -> extra degradation weight per failure mode
    "Bearing wear": {"vibration": 2.4, "temperature": 0.6, "rpm": -0.4},
    "Overheating": {"temperature": 2.6, "current": 0.8, "oil_quality": -0.8},
    "Seal leak": {"pressure": -2.2, "oil_quality": -1.6, "vibration": 0.5},
    "Electrical fault": {"current": 2.5, "rpm": -1.0, "temperature": 0.7},
}
BASE = {"temperature": 70, "vibration": 2.2, "pressure": 6.0, "rpm": 3000, "current": 42, "oil_quality": 95}
SCALE = {"temperature": 9, "vibration": 1.6, "pressure": 0.9, "rpm": 180, "current": 6, "oil_quality": 9}
WINDOW = 30
COST = {"preventive": 45000, "corrective": 320000, "downtime_per_cycle": 18000}


def _machine(rng, mid, mode, life, running_to=None):
    t = np.arange(life)
    health = (t / life) ** 2.6  # 0 → 1 accelerating degradation
    load = 0.85 + 0.15 * np.sin(t / 9 + rng.random() * 6) + rng.normal(0, 0.03, life)
    rows = {"cycle": t + 1}
    for s in SENSORS:
        w = MODE_EFFECT[mode].get(s, 0.25 * rng.choice([-1, 1]))
        noise = rng.normal(0, 0.18, life)
        rows[s] = BASE[s] + SCALE[s] * (w * health * 1.6 + (load - 0.85) * 1.5 * (s in ("temperature", "current")) + noise)
    df = pd.DataFrame(rows)
    df["load"] = load
    df["machine"] = mid
    df["mode"] = mode
    df["RUL"] = life - df["cycle"]
    if running_to is not None:
        df = df.iloc[:running_to]
    return df


def generate(n_hist=120, n_fleet=36, seed=5):
    rng = np.random.default_rng(seed)
    hist = []
    for i in range(n_hist):
        mode = MODES[i % 4]
        life = int(rng.integers(160, 360))
        hist.append(_machine(rng, f"H{i:03d}", mode, life))
    hist = pd.concat(hist, ignore_index=True)
    fleet, meta = [], []
    for i in range(n_fleet):
        mode = MODES[int(rng.integers(0, 4))]
        life = int(rng.integers(180, 360))
        frac = rng.choice([rng.uniform(0.25, 0.6), rng.uniform(0.6, 0.85), rng.uniform(0.86, 0.97)], p=[0.5, 0.32, 0.18])
        run = int(life * frac)
        mid = f"{list(TYPES)[i % 4][:3].upper()}-{101 + i}"
        fleet.append(_machine(rng, mid, mode, life, running_to=run))
        meta.append({"machine": mid, "type": list(TYPES)[i % 4], "line": f"Line {1 + i % 4}", "x": 1 + (i % 9), "y": 1 + i // 9,
                     "installed": f"20{20 + i % 6}", "criticality": rng.choice(["High", "Medium", "Low"], p=[0.35, 0.45, 0.2]), "true_mode": mode, "true_RUL": life - run})
    return hist, pd.concat(fleet, ignore_index=True), pd.DataFrame(meta)


def features(df, win=10):
    df = df.reset_index(drop=True)
    g = df.groupby("machine", sort=False)
    out = df[["machine", "cycle"]].copy()
    roll = g[SENSORS].rolling(win, min_periods=1)
    mean = roll.mean().reset_index(level=0, drop=True).sort_index()
    std = g[SENSORS].rolling(win, min_periods=2).std().reset_index(level=0, drop=True).sort_index().fillna(0)
    diff = g[SENSORS].diff(win).fillna(0) / win
    first = g[SENSORS].transform(lambda x: x.iloc[:20].mean())
    for s in SENSORS:
        out[s] = df[s]
        out[f"{s}_mean"] = mean[s]
        out[f"{s}_std"] = std[s]
        out[f"{s}_slope"] = diff[s]
        out[f"{s}_drift"] = df[s] - first[s]
    out["load"] = df["load"]
    return out


def feat_cols(f):
    return [c for c in f.columns if c not in ("machine", "cycle")]


def train_all(hist):
    f = features(hist)
    cols = feat_cols(f)
    y_rul = hist["RUL"].clip(upper=150)  # piece-wise linear RUL target (standard for turbofan data)
    y_fail = (hist["RUL"] <= WINDOW).astype(int)
    y_mode = hist["mode"]
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=1)
    tr, te = next(gss.split(f, groups=hist["machine"]))
    tr = tr[::2]  # every other cycle is plenty for training and keeps the app snappy
    rul_models = {
        "Gradient Boosting": HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, random_state=0),
        "Random Forest": RandomForestRegressor(n_estimators=80, max_depth=16, min_samples_leaf=4, n_jobs=-1, random_state=0),
    }
    res = {"cols": cols, "test_idx": te}
    res["rul"] = {}
    for n, m in rul_models.items():
        m.fit(f.iloc[tr][cols], y_rul.iloc[tr])
        p = m.predict(f.iloc[te][cols])
        d = p - y_rul.iloc[te].values
        nasa = float(np.sum(np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1)) / len(d))
        res["rul"][n] = {"model": m, "pred": p, "RMSE": mean_squared_error(y_rul.iloc[te], p) ** 0.5, "MAE": mean_absolute_error(y_rul.iloc[te], p), "R²": r2_score(y_rul.iloc[te], p), "NASA score": nasa, "resid_std": float(np.std(d))}
    clf = RandomForestClassifier(n_estimators=120, max_depth=14, min_samples_leaf=3, class_weight="balanced", n_jobs=-1, random_state=0)
    clf.fit(f.iloc[tr][cols], y_fail.iloc[tr])
    pf = clf.predict_proba(f.iloc[te][cols])[:, 1]
    fpr, tpr, _ = roc_curve(y_fail.iloc[te], pf)
    res["fail"] = {"model": clf, "proba": pf, "y": y_fail.iloc[te].values, "AUC": roc_auc_score(y_fail.iloc[te], pf), "fpr": fpr, "tpr": tpr,
                   "F1": f1_score(y_fail.iloc[te], pf > 0.5), "Accuracy": accuracy_score(y_fail.iloc[te], pf > 0.5)}
    # failure mode is only identifiable once degradation is visible → train on the last 40% of life
    late = hist["RUL"] / (hist["RUL"] + hist["cycle"]) < 0.4
    tr_l = [i for i in tr if late.iloc[i]]
    te_l = [i for i in te if late.iloc[i]]
    mclf = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.08, random_state=0)
    mclf.fit(f.iloc[tr_l][cols], y_mode.iloc[tr_l])
    pm = mclf.predict(f.iloc[te_l][cols])
    res["mode"] = {"model": mclf, "Accuracy": accuracy_score(y_mode.iloc[te_l], pm), "cm": confusion_matrix(y_mode.iloc[te_l], pm, labels=MODES)}
    healthy = hist[hist["cycle"] <= 60]
    iso = IsolationForest(n_estimators=200, contamination=0.02, random_state=0).fit(healthy[SENSORS])
    res["iso"] = iso
    res["y_rul_te"] = y_rul.iloc[te].values
    return res


def assess(res, fleet, meta, rul_model="Gradient Boosting"):
    f = features(fleet)
    last = f.groupby("machine").tail(1).set_index("machine")
    cols = res["cols"]
    m = res["rul"][rul_model]
    out = meta.set_index("machine").copy()
    out["cycle"] = last["cycle"]
    out["RUL"] = np.clip(m["model"].predict(last[cols]), 0, None).round()
    out["RUL_lo"] = np.clip(out["RUL"] - 1.28 * m["resid_std"], 0, None).round()
    out["RUL_hi"] = (out["RUL"] + 1.28 * m["resid_std"]).round()
    out["p_fail"] = res["fail"]["model"].predict_proba(last[cols])[:, 1]
    mp = res["mode"]["model"].predict_proba(last[cols])
    out["mode"] = np.array(res["mode"]["model"].classes_)[mp.argmax(1)]
    out["mode_conf"] = mp.max(1)
    raw = fleet.groupby("machine").tail(1).set_index("machine")[SENSORS]
    s = -res["iso"].score_samples(raw)
    out["anomaly"] = s
    out["health"] = np.clip(100 * (out["RUL"] / 150) * (1 - 0.5 * out["p_fail"]), 0, 100).round()
    out["status"] = np.select([(out["p_fail"] > 0.6) | (out["RUL"] <= 25), (out["p_fail"] > 0.25) | (out["RUL"] <= 60)], ["Critical", "Warning"], "Healthy")
    return out.reset_index()


def importance(res, rul_model="Gradient Boosting", top=12):
    m = res["rul"][rul_model]["model"]
    if hasattr(m, "feature_importances_"):
        s = pd.Series(m.feature_importances_, index=res["cols"])
    else:
        s = pd.Series(res["fail"]["model"].feature_importances_, index=res["cols"])
    return s.sort_values().tail(top)


ACTIONS = {
    "Bearing wear": ["Inspect & re-grease bearings", "Check shaft alignment and balance", "Order replacement bearing set"],
    "Overheating": ["Clean heat exchanger / cooling fins", "Verify coolant flow and fan operation", "Reduce load until inspected"],
    "Seal leak": ["Replace mechanical seals & gaskets", "Top up and test lubricant", "Pressure-test housing"],
    "Electrical fault": ["Thermal-scan motor windings & terminals", "Check insulation resistance (megger test)", "Inspect VFD and supply phases"],
}
