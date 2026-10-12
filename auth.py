import os
import streamlit as st
import streamlit.components.v1 as components

DEFAULT_PIN = "1234"


def get_expected_pin() -> str:
    try:
        if "APP_PIN" in st.secrets and st.secrets["APP_PIN"]:
            return str(st.secrets["APP_PIN"]).strip()
    except Exception:
        pass
    return os.getenv("APP_PIN", DEFAULT_PIN).strip()


def is_authenticated() -> bool:
    """Weryfikacja wyłącznie w ramach bieżącej sesji. Zamknięcie aplikacji wylogowuje."""
    return st.session_state.get("authenticated", False)


def logout():
    """Wylogowanie i wyczyszczenie sesji."""
    st.session_state["authenticated"] = False
    st.rerun()


def render_login_screen():
    expected_pin = get_expected_pin()

    # Sprawdzenie czy z biometrii w JS przesłano flagę logowania w bieżącej sesji
    if st.session_state.get("authenticated", False):
        return

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
        # Obsługa logowania biometrycznego z komponentu HTML (wyłącznie na urządzeniach mobilnych)
        bio_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    text-align: center;
                }}
                .mobile-bio-container {{
                    display: block;
                    margin-bottom: 10px;
                }}
                .faceid-btn {{
                    width: 100%;
                    background: rgba(143, 151, 121, 0.22);
                    border: 1px solid rgba(143, 151, 121, 0.45);
                    color: #EDE8DF;
                    padding: 10px 14px;
                    border-radius: 12px;
                    font-size: 13.5px;
                    font-weight: 600;
                    cursor: pointer;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    box-sizing: border-box;
                    transition: all 0.2s ease;
                }}
                .faceid-btn:active {{
                    transform: scale(0.98);
                    background: rgba(143, 151, 121, 0.4);
                }}
                .bio-msg {{
                    font-size: 11px;
                    color: #A3AD8C;
                    margin-top: 5px;
                    line-height: 1.35;
                }}
            </style>
        </head>
        <body>
            <div id="mobileBioBox" class="mobile-bio-container">
                <button type="button" class="faceid-btn" onclick="handleFaceID()">
                    Zaloguj przez Face ID
                </button>
                <div id="bioStatus" class="bio-msg">Dotknij, aby użyć Face ID na telefonie</div>
            </div>

            <script>
                // Weryfikacja czy użytkownik jest na telefonie / tablecie
                const isMobileUA = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent || "");
                const screenW = window.screen ? window.screen.width : window.innerWidth;

                // Na komputerze ukryj komponent całkowicie (nie wyświetlaj przycisku ani okna USB)
                if (!isMobileUA || screenW > 800) {{
                    const box = document.getElementById("mobileBioBox");
                    if (box) box.style.display = "none";
                    if (window.frameElement) {{
                        window.frameElement.style.display = "none";
                        window.frameElement.style.height = "0px";
                    }}
                }}

                async function handleFaceID() {{
                    const status = document.getElementById("bioStatus");
                    const isHttps = window.location.protocol === "https:" || window.location.hostname === "localhost";
                    
                    // 1. Sprawdź WebAuthn (wymaga HTTPS na telefonie)
                    if (window.PublicKeyCredential && isHttps) {{
                        try {{
                            status.innerText = "Weryfikacja Face ID...";
                            const challenge = new Uint8Array(32);
                            window.crypto.getRandomValues(challenge);
                            
                            const getOptions = {{
                                publicKey: {{
                                    challenge: challenge,
                                    timeout: 60000,
                                    userVerification: "required"
                                }}
                            }};
                            await navigator.credentials.get(getOptions);
                            fillAndSubmitParent();
                            return;
                        }} catch (e) {{
                            // W razie błędu fallback do pola PIN
                        }}
                    }}
                    
                    // 2. Jeśli połączenie lokalne HTTP (192.168.1.XX):
                    status.innerText = "Dotknij pola PIN poniżej – Safari użyje Face ID z pęku kluczy.";
                    fillAndSubmitParent();
                }}

                function fillAndSubmitParent() {{
                    try {{
                        const parentDoc = window.parent.document;
                        const pinInput = parentDoc.querySelector('input[type="password"]');
                        if (pinInput) {{
                            pinInput.setAttribute("autocomplete", "current-password");
                            pinInput.focus();
                        }}
                    }} catch (e) {{}}
                }}

                window.addEventListener("load", () => {{
                    try {{
                        const parentDoc = window.parent.document;
                        const pinInput = parentDoc.querySelector('input[type="password"]');
                        if (pinInput) {{
                            pinInput.setAttribute("autocomplete", "current-password");
                        }}
                    }} catch (e) {{}}
                }});
            </script>
        </body>
        </html>
        """
        components.html(bio_html, height=65)

        entered_pin = st.text_input(
            "Kod PIN:",
            type="password",
            max_chars=10,
            key="text_pin_input"
        )

        if st.button("Zaloguj", use_container_width=True, type="primary"):
            if entered_pin == expected_pin:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Nieprawidłowy kod PIN.")
