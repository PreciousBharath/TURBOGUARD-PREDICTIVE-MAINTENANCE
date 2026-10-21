"""Authentication: SQLite user store with salted PBKDF2-SHA256 hashing + Streamlit login/register UI."""
import hashlib
import os
import re
import sqlite3
from datetime import datetime

import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def _conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute(
        """CREATE TABLE IF NOT EXISTS users(
            email TEXT PRIMARY KEY, name TEXT, salt BLOB, hash BLOB,
            role TEXT, created TEXT, last_login TEXT)"""
    )
    return con


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)


def password_strength(pw: str):
    score = sum([
        len(pw) >= 8,
        len(pw) >= 12,
        bool(re.search(r"[A-Z]", pw) and re.search(r"[a-z]", pw)),
        bool(re.search(r"\d", pw)),
        bool(re.search(r"[^A-Za-z0-9]", pw)),
    ])
    labels = ["Very weak", "Weak", "Fair", "Good", "Strong", "Excellent"]
    colors = ["#ef4444", "#ef4444", "#f59e0b", "#eab308", "#10b981", "#10b981"]
    return score, labels[score], colors[score]


def create_user(name, email, password, role="analyst"):
    email = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError("Please enter a valid email address")
    if len(name.strip()) < 2:
        raise ValueError("Please enter your name")
    if password_strength(password)[0] < 3:
        raise ValueError("Password too weak — use 8+ characters with upper/lower case, a number and a symbol")
    con = _conn()
    if con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        raise ValueError("An account with this email already exists")
    salt = os.urandom(16)
    con.execute(
        "INSERT INTO users VALUES (?,?,?,?,?,?,?)",
        (email, name.strip(), salt, _hash(password, salt), role, datetime.now().isoformat(timespec="seconds"), None),
    )
    con.commit()


def verify(email, password):
    con = _conn()
    row = con.execute("SELECT name, salt, hash, role, created FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if not row:
        raise ValueError("No account found for this email")
    name, salt, h, role, created = row
    if _hash(password, salt) != h:
        raise ValueError("Incorrect password")
    con.execute("UPDATE users SET last_login=? WHERE email=?", (datetime.now().isoformat(timespec="seconds"), email.strip().lower()))
    con.commit()
    return {"name": name, "email": email.strip().lower(), "role": role, "created": created}


def change_password(email, old, new):
    verify(email, old)
    if password_strength(new)[0] < 3:
        raise ValueError("New password is too weak")
    salt = os.urandom(16)
    con = _conn()
    con.execute("UPDATE users SET salt=?, hash=? WHERE email=?", (salt, _hash(new, salt), email))
    con.commit()


def ensure_demo(name, email, password, role="admin"):
    con = _conn()
    if not con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        salt = os.urandom(16)
        con.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?)", (email, name, salt, _hash(password, salt), role, datetime.now().isoformat(timespec="seconds"), None))
        con.commit()


def user_count():
    return _conn().execute("SELECT COUNT(*) FROM users").fetchone()[0]


def logout():
    for k in ["user"]:
        st.session_state.pop(k, None)
    st.rerun()


def auth_page(app):
    """Full-screen login / register page. `app` is the APP config dict."""
    ensure_demo(app["demo_name"], app["demo_email"], app["demo_password"])
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        feats = "".join(f'<li style="animation-delay:{0.15 + i * 0.12:.2f}s"><span>✓</span>{f}</li>' for i, f in enumerate(app["features"]))
        st.markdown(
            f"""
            <div class="auth-hero">
              <div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div>
              <div class="auth-inner">
                <div class="brand"><span class="logo">{app['icon']}</span><b>{app['name']}</b></div>
                <h1>{app['tagline']}</h1>
                <p>{app['description']}</p>
                <ul class="hero-points">{feats}</ul>
                <div class="float-row">
                  <div class="float-card">{app['card1']}</div>
                  <div class="float-card" style="animation-delay:1s">{app['card2']}</div>
                </div>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="auth-spacer"></div>', unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["🔐 Log in", "✨ Create account"])
        with tab_login:
            with st.form("login"):
                st.markdown("#### Welcome back")
                email = st.text_input("Email", placeholder="you@example.com")
                pw = st.text_input("Password", type="password")
                c1, c2 = st.columns(2)
                go = c1.form_submit_button("Log in", type="primary", width="stretch")
                demo = c2.form_submit_button("⚡ Demo account", width="stretch")
            if go or demo:
                try:
                    st.session_state.user = verify(app["demo_email"] if demo else email, app["demo_password"] if demo else pw)
                    st.toast(f"Welcome, {st.session_state.user['name'].split()[0]}! 👋")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            st.caption(f"Demo login: `{app['demo_email']}` / `{app['demo_password']}`")
        with tab_reg:
            name = st.text_input("Full name", key="r_name")
            email_r = st.text_input("Email", key="r_email")
            role = st.selectbox("Role", app.get("roles", ["Analyst", "Manager", "Student"]), key="r_role")
            pw1 = st.text_input("Password", type="password", key="r_pw")
            score, label, color = password_strength(pw1)
            st.markdown(
                f'<div class="pw-meter"><div style="width:{score * 20}%;background:{color}"></div></div>'
                f'<small style="color:{color}">{label if pw1 else "Use 8+ chars with upper, lower, number & symbol"}</small>',
                unsafe_allow_html=True,
            )
            pw2 = st.text_input("Confirm password", type="password", key="r_pw2")
            agree = st.checkbox("I agree to the terms & privacy policy", key="r_agree")
            if st.button("Create account", type="primary", width="stretch"):
                try:
                    if pw1 != pw2:
                        raise ValueError("Passwords do not match")
                    if not agree:
                        raise ValueError("Please accept the terms")
                    create_user(name, email_r, pw1, role.lower())
                    st.session_state.user = verify(email_r, pw1)
                    st.balloons()
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
