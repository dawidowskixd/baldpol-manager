import os
from datetime import datetime, date
import pandas as pd
import streamlit as st

import auth
from db import get_db, DEFAULT_ROLES, ROLE_ICONS

# 1. Konfiguracja strony Streamlit
st.set_page_config(
    page_title="Dziennik Pracy | Wspinaczka & Recepcja",
    page_icon="🧗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 2. Załadowanie arkusza CSS z motywem Frosted Glass & Earth Tones
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# 3. Weryfikacja autoryzacji (PIN / Face ID)
if not auth.is_authenticated():
    auth.render_login_screen()
    st.stop()

# 4. Inicjalizacja bazy danych
db = get_db()

# Pomocnicze nazwy miesięcy w języku polskim
MONTH_NAMES_PL = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
    5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień",
    9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
}

def format_month_label(month_key: str) -> str:
    """Konwertuje '2026-10' na 'Październik 2026'."""
    try:
        y, m = month_key.split("-")
        return f"{MONTH_NAMES_PL.get(int(m), m)} {y}"
    except Exception:
        return month_key

# Stan sesji dla formularza dodawania wpisu
if "form_hours" not in st.session_state:
    st.session_state.form_hours = 8.0
if "editing_entry_id" not in st.session_state:
    st.session_state.editing_entry_id = None

# =====================================================================
# NAGŁÓWEK GŁÓWNY (GLASS HEADER)
# =====================================================================
status_badge_html = """
    <span class="status-badge">☁️ Supabase</span>
""" if db.is_supabase else """
    <span class="status-badge local">💾 Tryb lokalny (SQLite)</span>
"""

col_head_title, col_head_act = st.columns([3, 1])
with col_head_title:
    st.markdown(f"""
        <div class="app-header">
            <div>
                <h1 class="app-title">🧗 Dziennik Pracy</h1>
                <p class="app-subtitle">Rozliczanie godzin i zarobków</p>
            </div>
            <div>
                {status_badge_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_head_act:
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    if st.button("🚪 Wyloguj", use_container_width=True, help="Wyloguj i zablokuj dostęp"):
        auth.logout()

# =====================================================================
# GŁÓWNA NAWIGACJA ZAKŁADKOWA
# =====================================================================
tab_add, tab_stats, tab_journal, tab_settings = st.tabs([
    "➕ Nowy wpis",
    "📊 Miesiąc & Zarobki",
    "📖 Dziennik / Notatnik",
    "⚙️ Baza & Ustawienia",
])


# =====================================================================
# ZAKŁADKA 1: NOWY WPIS (SZYBKI ZAPIS DNIA)
# =====================================================================
with tab_add:
    st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
    st.markdown("### 📝 Zarejestruj czas pracy")

    # 1. Wybór daty
    c_date, c_role = st.columns([1, 1])
    with c_date:
        entry_date = st.date_input("Data:", value=date.today(), format="DD.MM.YYYY")

    with c_role:
        role_options = list(DEFAULT_ROLES.keys())
        selected_role = st.selectbox(
            "Stanowisko:",
            options=role_options,
            index=0,
        )

    # 2. Stawka godzinowa
    default_rate = DEFAULT_ROLES.get(selected_role, 35.00)
    col_rate_toggle, col_rate_input = st.columns([1, 1])
    with col_rate_toggle:
        custom_rate_enabled = st.checkbox("Niestandardowa stawka / premia", value=False)
    with col_rate_input:
        if custom_rate_enabled:
            hourly_rate = st.number_input("Stawka zł/h:", value=float(default_rate), min_value=1.0, step=0.5)
        else:
            hourly_rate = default_rate
            st.markdown(f"""
                <div style="padding-top: 8px; font-size: 0.95rem; color: #D6DEC8;">
                    Stawka: <b style="color: #F0CA86; font-size: 1.15rem;">{hourly_rate:.2f} zł / h</b>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='border: none; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 15px 0;'>", unsafe_allow_html=True)

    # 3. Czas pracy: Szybkie przyciski + Suwak
    st.markdown("<label style='font-size: 0.9rem; font-weight: 600; color: #EDE8DF;'>Przepracowane godziny:</label>", unsafe_allow_html=True)
    
    # Szybkie kafelki godzin
    q_col1, q_col2, q_col3, q_col4, q_col5, q_col6 = st.columns(6)
    with q_col1:
        if st.button("4h", key="quick_4", use_container_width=True):
            st.session_state.form_hours = 4.0
            st.rerun()
    with q_col2:
        if st.button("6h", key="quick_6", use_container_width=True):
            st.session_state.form_hours = 6.0
            st.rerun()
    with q_col3:
        if st.button("7h", key="quick_7", use_container_width=True):
            st.session_state.form_hours = 7.0
            st.rerun()
    with q_col4:
        if st.button("8h", key="quick_8", use_container_width=True):
            st.session_state.form_hours = 8.0
            st.rerun()
    with q_col5:
        if st.button("10h", key="quick_10", use_container_width=True):
            st.session_state.form_hours = 10.0
            st.rerun()
    with q_col6:
        if st.button("12h", key="quick_12", use_container_width=True):
            st.session_state.form_hours = 12.0
            st.rerun()

    # Precyzyjny suwak z krokiem 0.25h (15 min)
    hours_worked = st.slider(
        "Dostosuj suwakiem (krok 15 min):",
        min_value=0.5,
        max_value=16.0,
        value=float(st.session_state.form_hours),
        step=0.25,
        key="slider_hours",
        format="%.2f h"
    )
    # Zsynchronizuj stan
    st.session_state.form_hours = hours_worked

    # 4. Notatnik dzienny
    notes = st.text_area(
        "Co robiono w danym dniu (notatka):",
        placeholder="np. Prace na boulderowni: czyszczenie chwytów, nakręcenie 3 obwodów w sektorze lewym...",
        height=90,
    )

    # 5. Podgląd wyliczonego wynagrodzenia w locie
    calculated_total = round(hourly_rate * hours_worked, 2)
    st.markdown(f"""
        <div class="live-calc-box">
            <div>
                <div class="live-calc-title">WYKAZ DNIA: {hours_worked:.2f} godz. × {hourly_rate:.2f} zł/h</div>
                <div style="font-size: 0.82rem; color: #B3BEA4;">{selected_role}</div>
            </div>
            <div style="text-align: right;">
                <div class="live-calc-title">DO WYPŁATY:</div>
                <div class="live-calc-amount">{calculated_total:,.2f} zł</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 6. Przycisk zapisu
    if st.button("💾 Zapisz wpis do dziennika", type="primary", use_container_width=True):
        db.add_entry(
            entry_date=entry_date,
            role_name=selected_role,
            hourly_rate=hourly_rate,
            hours_worked=hours_worked,
            notes=notes
        )
        st.success(f"✅ Zapisano wpis za dzień {entry_date.strftime('%d.%m.%Y')} ({calculated_total:.2f} zł)!")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# ZAKŁADKA 2: MIESIĄC I PODSUMOWANIE (KPI & ANALITYKA)
# =====================================================================
with tab_stats:
    all_months = db.get_all_months()
    curr_month_str = datetime.now().strftime("%Y-%m")

    # Wybór miesiąca
    col_sel_month, col_exp_btn = st.columns([2, 1])
    with col_sel_month:
        selected_month = st.selectbox(
            "Wybierz rozliczany miesiąc:",
            options=all_months,
            format_func=format_month_label,
            index=0 if curr_month_str in all_months else 0
        )

    entries = db.get_entries(month_prefix=selected_month)
    df = pd.DataFrame(entries) if entries else pd.DataFrame()

    if df.empty:
        st.info(f"Brak wpisów dla miesiąca {format_month_label(selected_month)}. Dodaj pierwszy wpis w zakładce 'Nowy wpis'!")
    else:
        # Konwersja kolumn
        df["hours_worked"] = df["hours_worked"].astype(float)
        df["total_earned"] = df["total_earned"].astype(float)

        total_hours = df["hours_worked"].sum()
        total_payout = df["total_earned"].sum()
        unique_days = df["entry_date"].nunique()
        avg_per_day = round(total_payout / unique_days, 2) if unique_days > 0 else 0.0

        # Rozbicie na stanowiska
        climbing_mask = df["role_name"].str.contains("wspinaczkowa", case=False, na=False)
        bar_mask = df["role_name"].str.contains("barku|recepcja", case=False, na=False)

        climbing_hours = df[climbing_mask]["hours_worked"].sum()
        climbing_earned = df[climbing_mask]["total_earned"].sum()

        bar_hours = df[bar_mask]["hours_worked"].sum()
        bar_earned = df[bar_mask]["total_earned"].sum()

        # Eksport do CSV
        with col_exp_btn:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            csv_data = df[["entry_date", "role_name", "hours_worked", "hourly_rate", "total_earned", "notes"]].to_csv(index=False)
            st.download_button(
                label="📥 Pobierz CSV",
                data=csv_data,
                file_name=f"Dziennik_Pracy_{selected_month}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # 4 Kafelki KPI w stylu Frosted Glass
        st.markdown(f"""
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-label">Łączny Zarobek</div>
                    <div class="kpi-value" style="color: #F0CA86;">{total_payout:,.2f} zł</div>
                    <div class="kpi-sub">{unique_days} dni pracy</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Łączny Czas</div>
                    <div class="kpi-value">{total_hours:.1f} h</div>
                    <div class="kpi-sub">śr. {avg_per_day:.1f} zł / dzień</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">🧗 Ścianka Tech</div>
                    <div class="kpi-value" style="color: #C5CEB8;">{climbing_hours:.1f} h</div>
                    <div class="kpi-sub">{climbing_earned:,.2f} zł</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">☕ Barek / Recepcja</div>
                    <div class="kpi-value" style="color: #E2C29B;">{bar_hours:.1f} h</div>
                    <div class="kpi-sub">{bar_earned:,.2f} zł</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Podział proporcjonalny
        if total_payout > 0:
            climbing_pct = int(round((climbing_earned / total_payout) * 100))
            bar_pct = 100 - climbing_pct
            st.markdown(f"""
                <div class="glass-panel" style="padding: 1rem 1.2rem;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;">
                        <span style="color: #C5CEB8;">🧗 Ścianka: {climbing_pct}% ({climbing_earned:,.2f} zł)</span>
                        <span style="color: #E2C29B;">☕ Barek: {bar_pct}% ({bar_earned:,.2f} zł)</span>
                    </div>
                    <div style="width: 100%; height: 10px; background: rgba(0,0,0,0.3); border-radius: 5px; overflow: hidden; display: flex;">
                        <div style="width: {climbing_pct}%; background: #7E8A6B; height: 100%;"></div>
                        <div style="width: {bar_pct}%; background: #A27035; height: 100%;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # Zestawienie dniowe - prosty wykres godzin
        st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
        st.markdown("#### 📅 Godziny przepracowane w dniach:")
        daily_summary = df.groupby("entry_date")["hours_worked"].sum().reset_index()
        daily_summary = daily_summary.sort_values("entry_date")
        st.bar_chart(data=daily_summary.set_index("entry_date"), color="#8F9779")
        st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# ZAKŁADKA 3: DZIENNIK I HISTORIA (NOTATNIK DNI)
# =====================================================================
with tab_journal:
    st.markdown("### 📖 Dziennik Przepracowanych Dni")
    
    # Filtr miesiąca dla dziennika
    journal_month = st.selectbox(
        "Filtruj wg miesiąca:",
        options=all_months,
        format_func=format_month_label,
        key="journal_month_select"
    )

    j_entries = db.get_entries(month_prefix=journal_month)

    if not j_entries:
        st.info("Brak wpisów w tym miesiącu.")
    else:
        # Grupowanie wg daty
        entries_by_date = {}
        for item in j_entries:
            d = item["entry_date"]
            if d not in entries_by_date:
                entries_by_date[d] = []
            entries_by_date[d].append(item)

        for d_str, day_items in entries_by_date.items():
            # Parsowanie daty
            try:
                date_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                formatted_d = date_obj.strftime("%d.%m.%Y")
                weekday_name = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"][date_obj.weekday()]
            except Exception:
                formatted_d = d_str
                weekday_name = ""

            day_total_hours = sum(float(i["hours_worked"]) for i in day_items)
            day_total_earned = sum(float(i["total_earned"]) for i in day_items)

            # Nagłówek dnia z łącznym podsumowaniem (jeśli wielokrotne wpisy)
            multi_note = f" ({len(day_items)} zmiany)" if len(day_items) > 1 else ""
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin: 16px 0 6px 0; border-bottom: 1px solid rgba(143, 151, 121, 0.25); padding-bottom: 4px;">
                    <div>
                        <span style="font-size: 1.15rem; font-weight: 700; color: #F5F2EB;">📅 {formatted_d}</span>
                        <span style="font-size: 0.85rem; color: #A8B29A; margin-left: 8px;">{weekday_name}{multi_note}</span>
                    </div>
                    <div style="font-size: 0.95rem; font-weight: 600; color: #F0CA86;">
                        Łącznie: {day_total_hours:.2f} h | {day_total_earned:,.2f} zł
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Renderowanie poszczególnych zmian w tym dniu
            for idx, entry in enumerate(day_items):
                is_climbing = "wspinaczkowa" in entry["role_name"].lower()
                role_class = "climbing" if is_climbing else "bar"
                role_icon = "🧗" if is_climbing else "☕"
                role_badge_class = "climbing" if is_climbing else "bar"

                st.markdown(f"""
                    <div class="entry-card {role_class}">
                        <div class="entry-header">
                            <span class="entry-role-pill {role_badge_class}">
                                {role_icon} {entry['role_name']}
                            </span>
                            <span class="entry-earned">{float(entry['total_earned']):,.2f} zł</span>
                        </div>
                        <div class="entry-stats">
                            <span class="entry-stat-item">⏱️ <b>{float(entry['hours_worked']):.2f} h</b></span>
                            <span class="entry-stat-item">💵 {float(entry['hourly_rate']):.2f} zł/h</span>
                        </div>
                        {f'<div class="entry-notes"><b>Notatka:</b> {entry["notes"]}</div>' if entry.get("notes") else '<div style="font-size: 0.8rem; color: #8C967E; font-style: italic;">Brak notatek z tego dnia.</div>'}
                    </div>
                """, unsafe_allow_html=True)

                # Przycisk edycji i usuwania w expanderze
                with st.expander(f"⚙️ Zarządzaj wpisem: {entry['role_name']} ({entry['hours_worked']} h)"):
                    e_col1, e_col2 = st.columns([1, 1])
                    with e_col1:
                        new_role = st.selectbox(
                            "Zmień stanowisko:",
                            options=list(DEFAULT_ROLES.keys()),
                            index=0 if is_climbing else 1,
                            key=f"edit_role_{entry['id']}"
                        )
                        new_hours = st.number_input(
                            "Godziny:",
                            value=float(entry["hours_worked"]),
                            step=0.25,
                            key=f"edit_hours_{entry['id']}"
                        )
                    with e_col2:
                        new_rate = st.number_input(
                            "Stawka zł/h:",
                            value=float(entry["hourly_rate"]),
                            step=0.5,
                            key=f"edit_rate_{entry['id']}"
                        )
                        new_notes = st.text_area(
                            "Notatki:",
                            value=entry.get("notes", ""),
                            key=f"edit_notes_{entry['id']}"
                        )

                    btn_c1, btn_c2 = st.columns([1, 1])
                    with btn_c1:
                        if st.button("💾 Zapisz zmiany", key=f"btn_save_{entry['id']}", use_container_width=True):
                            db.update_entry(
                                entry_id=entry["id"],
                                entry_date=entry["entry_date"],
                                role_name=new_role,
                                hourly_rate=new_rate,
                                hours_worked=new_hours,
                                notes=new_notes
                            )
                            st.success("Zaktualizowano wpis!")
                            st.rerun()
                    with btn_c2:
                        if st.button("🗑️ Usuń wpis", key=f"btn_del_{entry['id']}", type="secondary", use_container_width=True):
                            db.delete_entry(entry["id"])
                            st.warning("Wpis został usunięty.")
                            st.rerun()


# =====================================================================
# ZAKŁADKA 4: USTAWIENIA & SUPABASE
# =====================================================================
with tab_settings:
    st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
    st.markdown("### ☁️ Połączenie z Bazą Danych Supabase")

    if db.is_supabase:
        st.success("🟢 Aplikacja jest połączona z Twoją bazą danych Supabase!")
        st.markdown(f"Adres URL: `{db.supabase_url}`")
    else:
        st.warning("""
            🟡 **Aplikacja działa obecnie w lokalnym trybie SQLite.**  
            Dane są bezpiecznie zapisywane na Twoim komputerze w pliku `local_work_tracker.db`.
        """)

        st.markdown("""
            #### Jak połączyć się z Supabase w 3 prostych krokach:
            1. Wejdź na [supabase.com](https://supabase.com) i utwórz bezpłatny projekt (np. `baldpol-tracker`).
            2. W konsoli Supabase wejdź w zakładkę **SQL Editor**, wklej i uruchom zawartość pliku `schema.sql`.
            3. Wejdź w **Project Settings -> Data API**, skopiuj **Project URL** oraz **anon public key**, a następnie wklej je do pliku `.streamlit/secrets.toml`:
        """)

        st.code("""
# .streamlit/secrets.toml
SUPABASE_URL = "https://twoj-projekt.supabase.co"
SUPABASE_KEY = "twoj-anon-klucz"
APP_PIN = "1234"
        """, language="toml")

    # Przycisk migracji lokalnych wpisów do Supabase
    if db.is_supabase:
        st.markdown("---")
        st.markdown("#### 🔄 Migracja danych lokalnych")
        st.caption("Jeśli przed połączeniem z Supabase dodawałeś wpisy w trybie lokalnym, możesz przenieść je do chmury:")
        if st.button("🚀 Wyślij lokalne wpisy do Supabase"):
            count, msg = db.migrate_local_to_supabase()
            st.info(msg)

    st.markdown("</div>", unsafe_allow_html=True)

    # Informacje o stanowiskach i stawkach
    st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
    st.markdown("### 🧗 Stanowiska i Stawki Domyślne")
    for r_name, r_rate in DEFAULT_ROLES.items():
        icon = ROLE_ICONS.get(r_name, "💼")
        st.markdown(f"- {icon} **{r_name}**: `{r_rate:.2f} zł / h`")
    st.caption("Stawkę możesz również nadpisać manualnie przy każdym wpisie za pomocą opcji 'Niestandardowa stawka'.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Bezpieczeństwo i PIN
    st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
    st.markdown("### 🔐 Zmiana Kodu PIN i Bezpieczeństwo")
    st.write(f"Aktualny kod PIN: `••••` (długość: {len(auth.get_expected_pin())} cyfry)")
    st.caption("Aby zmienić kod PIN, otwórz plik `.streamlit/secrets.toml` i ustaw wartość `APP_PIN = 'twój_nowy_pin'`.")
    st.markdown("</div>", unsafe_allow_html=True)
