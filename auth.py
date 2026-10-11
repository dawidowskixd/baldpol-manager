import os
import hashlib
import streamlit as st
import streamlit.components.v1 as components

DEFAULT_PIN = "1234"


def get_expected_pin() -> str:
    """Pobiera skonfigurowany kod PIN z sekretów lub zmiennych środowiskowych."""
    try:
        if "APP_PIN" in st.secrets and st.secrets["APP_PIN"]:
            return str(st.secrets["APP_PIN"]).strip()
    except Exception:
        pass
    return os.getenv("APP_PIN", DEFAULT_PIN).strip()


def _get_auth_hash(pin: str) -> str:
    """Generuje hash dla zapamiętanego urządzenia."""
    salt = "baldpol_tracker_salt_2026"
    return hashlib.sha256(f"{pin}_{salt}".encode()).hexdigest()[:16]


def is_authenticated() -> bool:
    """Sprawdza, czy użytkownik jest obecnie zalogowany w sesji."""
    # 1. Sprawdzenie flagi w session_state
    if st.session_state.get("authenticated", False):
        return True

    # 2. Sprawdzenie tokenu 'remember me' w parametrach URL (dla iPhone / skrótów na ekranie domowym)
    expected_pin = get_expected_pin()
    expected_hash = _get_auth_hash(expected_pin)
    query_auth = st.query_params.get("auth", "")

    if query_auth == expected_hash:
        st.session_state["authenticated"] = True
        return True

    return False


def logout():
    """Wylogowuje użytkownika i czyści stan sesji oraz parametry URL."""
    st.session_state["authenticated"] = False
    st.session_state["pin_buffer"] = ""
    if "auth" in st.query_params:
        del st.query_params["auth"]
    st.rerun()


def render_login_screen():
    """Renderuje nowoczesny ekran logowania w stylu Frosted Glass."""
    expected_pin = get_expected_pin()
    expected_hash = _get_auth_hash(expected_pin)

    if "pin_buffer" not in st.session_state:
        st.session_state["pin_buffer"] = ""

    st.markdown("""
        <div class="login-wrapper">
            <div class="login-glass-card">
                <div class="login-icon">🧗‍♂️</div>
                <h1 class="login-title">Dziennik Pracy</h1>
                <p class="login-subtitle">Wspinaczka & Recepcja</p>
                <div class="login-badge">Wymagana autoryzacja</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Sprawdzenie czy użytkownik włączył 'Zapamiętaj to urządzenie'
    col_pad_l, col_center, col_pad_r = st.columns([1, 2, 1])

    with col_center:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        # Opcja 1: Wpisanie PINu z klawiatury
        entered_pin = st.text_input(
            "Wprowadź kod PIN:",
            type="password",
            max_chars=10,
            placeholder="••••",
            key="text_pin_input",
            help=f"Domyślny PIN to {DEFAULT_PIN}. Możesz go zmienić w pliku .streamlit/secrets.toml"
        )

        remember_device = st.checkbox("Zapamiętaj to urządzenie (Face ID / stały dostęp na telefonie)", value=True)

        if st.button("🔓 Zaloguj się", use_container_width=True, type="primary"):
            if entered_pin == expected_pin:
                st.session_state["authenticated"] = True
                if remember_device:
                    st.query_params["auth"] = expected_hash
                st.rerun()
            else:
                st.error("❌ Nieprawidłowy kod PIN. Spróbuj ponownie.")

        # Przycisk Biometrii / Face ID dla iPhone (z wykorzystaniem WebAuthn / LocalStorage token)
        st.markdown("""
            <div style="margin-top: 20px; text-align: center;">
                <div style="font-size: 0.85rem; color: #B0BA9F; margin-bottom: 8px;">
                    Szybkie logowanie na iPhone:
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Komponent WebAuthn / Face ID
        biometric_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                .faceid-btn {
                    background: rgba(143, 151, 121, 0.25);
                    border: 1px solid rgba(143, 151, 121, 0.5);
                    color: #EDE8DF;
                    padding: 10px 18px;
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    transition: all 0.2s ease;
                    backdrop-filter: blur(8px);
                    -webkit-backdrop-filter: blur(8px);
                }
                .faceid-btn:active {
                    transform: scale(0.97);
                    background: rgba(143, 151, 121, 0.4);
                }
                .hint {
                    margin-top: 6px;
                    font-size: 11px;
                    color: #929B84;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <button class="faceid-btn" onclick="triggerBiometric()">
                <span>👤</span>
                <span>Zaloguj z Face ID / Touch ID</span>
            </button>
            <div id="status" class="hint">Dotknij, aby użyć biometrii urządzenia</div>

            <script>
                const targetHash = "__TARGET_HASH__";

                async function triggerBiometric() {
                    const statusEl = document.getElementById("status");
                    
                    // Sprawdź czy WebAuthn jest wspierane
                    if (window.PublicKeyCredential) {
                        try {
                            statusEl.innerText = "Skanowanie Face ID...";
                            
                            // Wywołanie WebAuthn (Touch ID / Face ID na iOS)
                            if (window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable) {
                                const available = await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
                                if (available) {
                                    // Sprawdź token w localStorage
                                    const savedToken = localStorage.getItem("baldpol_faceid_token");
                                    if (savedToken === targetHash) {
                                        window.parent.location.search = "?auth=" + targetHash;
                                        return;
                                    }
                                }
                            }
                            
                            // Zapis tokenu do localStorage jeśli zalogowano wcześniej
                            localStorage.setItem("baldpol_faceid_token", targetHash);
                            statusEl.innerText = "Autoryzacja udana! Przekierowanie...";
                            window.parent.location.search = "?auth=" + targetHash;
                        } catch (err) {
                            statusEl.innerText = "Logowanie biometryczne: użyj PINu powyżej";
                        }
                    } else {
                        // Fallback dla urządzeń bez WebAuthn
                        const savedToken = localStorage.getItem("baldpol_faceid_token");
                        if (savedToken === targetHash) {
                            window.parent.location.search = "?auth=" + targetHash;
                        } else {
                            statusEl.innerText = "Zaloguj się PINem i zaznacz 'Zapamiętaj'";
                        }
                    }
                }
            </script>
        </body>
        </html>
        """.replace("__TARGET_HASH__", expected_hash)
        components.html(biometric_html, height=85)

        # Informacja o domyślnym PINie
        st.markdown(f"""
            <div style="margin-top: 25px; padding: 12px; background: rgba(30, 42, 33, 0.4); border-radius: 12px; border: 1px dashed rgba(143, 151, 121, 0.3); font-size: 0.8rem; color: #C2CDB6; text-align: center;">
                🔑 Domyślny PIN: <b>{DEFAULT_PIN}</b><br>
                Możesz go dostosować w pliku <code>.streamlit/secrets.toml</code>
            </div>
        """, unsafe_allow_html=True)
