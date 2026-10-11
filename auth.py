import os
import hashlib
import streamlit as st

DEFAULT_PIN = "1234"


def get_expected_pin() -> str:
    try:
        if "APP_PIN" in st.secrets and st.secrets["APP_PIN"]:
            return str(st.secrets["APP_PIN"]).strip()
    except Exception:
        pass
    return os.getenv("APP_PIN", DEFAULT_PIN).strip()


def _get_auth_hash(pin: str) -> str:
    salt = "baldpol_tracker_salt_2026"
    return hashlib.sha256(f"{pin}_{salt}".encode()).hexdigest()[:16]


def is_authenticated() -> bool:
    if st.session_state.get("authenticated", False):
        return True

    expected_pin = get_expected_pin()
    expected_hash = _get_auth_hash(expected_pin)
    query_auth = st.query_params.get("auth", "")

    if query_auth == expected_hash:
        st.session_state["authenticated"] = True
        return True

    return False


def logout():
    st.session_state["authenticated"] = False
    if "auth" in st.query_params:
        del st.query_params["auth"]
    st.rerun()


def render_login_screen():
    expected_pin = get_expected_pin()
    expected_hash = _get_auth_hash(expected_pin)

    st.markdown("""
        <div class="login-wrapper">
            <div class="login-glass-card">
                <h1 class="login-title">Dziennik Pracy</h1>
                <p class="login-subtitle">Wprowadź kod PIN</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_pad_l, col_center, col_pad_r = st.columns([1, 2, 1])

    with col_center:
        entered_pin = st.text_input(
            "Kod PIN:",
            type="password",
            max_chars=10,
            key="text_pin_input"
        )

        remember_device = st.checkbox("Zapamiętaj to urządzenie", value=True)

        if st.button("Zaloguj", use_container_width=True, type="primary"):
            if entered_pin == expected_pin:
                st.session_state["authenticated"] = True
                if remember_device:
                    st.query_params["auth"] = expected_hash
                st.rerun()
            else:
                st.error("Nieprawidłowy kod PIN.")
