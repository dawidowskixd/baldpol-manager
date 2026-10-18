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


    col_pad_l, col_center, col_pad_r = st.columns([1, 2, 1])

    with col_center:
        # Obsługa Face ID (na telefonie) oraz wymuszenie wyłącznie klawiatury numerycznej (0-9)
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

                // Na komputerze ukryj przycisk Face ID
                if (!isMobileUA || screenW > 800) {{
                    const box = document.getElementById("mobileBioBox");
                    if (box) box.style.display = "none";
                    if (window.frameElement) {{
                        window.frameElement.style.height = "0px";
                        window.frameElement.style.margin = "0px";
                        window.frameElement.style.padding = "0px";
                        window.frameElement.style.border = "none";
                    }}
                }}

                async function handleFaceID() {{
                    const status = document.getElementById("bioStatus");
                    const isHttps = window.location.protocol === "https:" || window.location.hostname === "localhost";
                    
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
                            focusPinInput();
                            return;
                        }} catch (e) {{}}
                    }}
                    
                    status.innerText = "Dotknij pola PIN poniżej – Safari użyje Face ID z pęku kluczy.";
                    focusPinInput();
                }}

                function focusPinInput() {{
                    try {{
                        const parentDoc = window.parent.document;
                        const pinInput = parentDoc.querySelector('input[type="password"], div[data-testid="stTextInput"] input');
                        if (pinInput) {{
                            pinInput.focus();
                        }}
                    }} catch (e) {{}}
                }}

                // Wymuszenie czysto numerycznej klawiatury (bez liter) na telefonach i blokada znaków niebędących cyframi
                function enforceNumericPinOnly() {{
                    try {{
                        const parentDoc = window.parent.document;
                        if (!parentDoc) return;

                        const inputs = parentDoc.querySelectorAll('input[type="password"], div[data-testid="stTextInput"] input');
                        inputs.forEach(input => {{
                            // Atrybuty wymuszające klawiaturę numeryczną (cyfry 0-9) na iOS Safari i Androidzie
                            if (input.getAttribute("inputmode") !== "numeric") {{
                                input.setAttribute("inputmode", "numeric");
                            }}
                            if (input.getAttribute("pattern") !== "[0-9]*") {{
                                input.setAttribute("pattern", "[0-9]*");
                            }}
                            if (input.getAttribute("autocomplete") !== "one-time-code") {{
                                input.setAttribute("autocomplete", "one-time-code");
                            }}
                            if (input.getAttribute("autocorrect") !== "off") {{
                                input.setAttribute("autocorrect", "off");
                            }}
                            if (input.getAttribute("autocapitalize") !== "off") {{
                                input.setAttribute("autocapitalize", "off");
                            }}
                            if (input.getAttribute("spellcheck") !== "false") {{
                                input.setAttribute("spellcheck", "false");
                            }}

                            if (!input.dataset.numericEnforced) {{
                                input.dataset.numericEnforced = "true";

                                // 1. Blokowanie klawiszy innych niż cyfry
                                input.addEventListener("keydown", function(e) {{
                                    const allowed = ["Backspace", "Delete", "Tab", "Enter", "ArrowLeft", "ArrowRight", "Escape"];
                                    if (allowed.includes(e.key)) return;
                                    if (e.ctrlKey || e.metaKey || e.altKey) return;

                                    if (!/^[0-9]$/.test(e.key)) {{
                                        e.preventDefault();
                                        e.stopPropagation();
                                    }}
                                }}, true);

                                // 2. Blokowanie zdarzenia beforeinput (kluczowe na klawiaturach mobilnych iOS / Android)
                                input.addEventListener("beforeinput", function(e) {{
                                    if (e.data && !/^[0-9]+$/.test(e.data)) {{
                                        e.preventDefault();
                                        e.stopPropagation();
                                    }}
                                }}, true);

                                // 3. Natychmiastowe usuwanie znaków niebędących cyframi (np. wklejenie)
                                input.addEventListener("input", function(e) {{
                                    const orig = this.value;
                                    const clean = orig.replace(/[^0-9]/g, "");
                                    if (orig !== clean) {{
                                        this.value = clean;
                                        this.dispatchEvent(new Event("input", {{ bubbles: true }}));
                                    }}
                                }}, true);

                                // 4. Blokowanie wklejania liter ze schowka
                                input.addEventListener("paste", function(e) {{
                                    const text = (e.clipboardData || window.clipboardData).getData('text');
                                    if (text && /[^0-9]/.test(text)) {{
                                        e.preventDefault();
                                        const cleanDigits = text.replace(/[^0-9]/g, "");
                                        document.execCommand('insertText', false, cleanDigits);
                                    }}
                                }}, true);
                            }}
                        }});
                    }} catch (e) {{}}
                }}

                // Uruchomienie natychmiastowe i cykliczne
                enforceNumericPinOnly();
                setInterval(enforceNumericPinOnly, 100);

                // Reakcja na dotknięcie ekranu / focus
                try {{
                    const parentDoc = window.parent.document;
                    if (parentDoc) {{
                        parentDoc.addEventListener("focusin", enforceNumericPinOnly, true);
                        parentDoc.addEventListener("touchstart", enforceNumericPinOnly, true);
                        parentDoc.addEventListener("pointerdown", enforceNumericPinOnly, true);

                        const observer = new MutationObserver(enforceNumericPinOnly);
                        observer.observe(parentDoc.body, {{ childList: true, subtree: true, attributes: true }});
                    }}
                }} catch (e) {{}}
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

        clean_entered_pin = "".join(filter(str.isdigit, entered_pin))

        if st.button("Zaloguj", use_container_width=True, type="primary"):
            if clean_entered_pin and clean_entered_pin == expected_pin:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Nieprawidłowy kod PIN.")

