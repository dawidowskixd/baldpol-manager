import os
from datetime import datetime, date
import pandas as pd
import streamlit as st

import auth
from db import get_db, DEFAULT_ROLES
from ai_reporter import generate_ai_monthly_report

# Konfiguracja strony
st.set_page_config(
    page_title="Dziennik Pracy",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Załadowanie stylów CSS
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Weryfikacja logowania (sesja wygasa po zamknięciu karty/aplikacji)
if not auth.is_authenticated():
    auth.render_login_screen()
    st.stop()

db = get_db()

MONTH_NAMES_PL = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
    5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień",
    9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
}

WEEKDAY_NAMES_PL = [
    "Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"
]

def format_month_label(month_key: str) -> str:
    try:
        y, m = month_key.split("-")
        return f"{MONTH_NAMES_PL.get(int(m), m)} {y}"
    except Exception:
        return month_key


def generate_detailed_report(df: pd.DataFrame, selected_month: str) -> str:
    month_label = format_month_label(selected_month)
    total_hours = df["hours_worked"].sum()
    total_payout = df["total_earned"].sum()
    total_bonus = df["bonus"].sum() if "bonus" in df.columns else 0.0
    unique_days = df["entry_date"].nunique()

    climbing_mask = df["role_name"].str.contains("wspinaczkowa", case=False, na=False)
    bar_mask = df["role_name"].str.contains("barku|recepcja", case=False, na=False)

    climbing_hours = df[climbing_mask]["hours_worked"].sum()
    climbing_earned = df[climbing_mask]["total_earned"].sum()

    bar_hours = df[bar_mask]["hours_worked"].sum()
    bar_earned = df[bar_mask]["total_earned"].sum()

    lines = []
    lines.append(f"RAPORT MIESIĘCZNY: {month_label.upper()}")
    lines.append("=" * 48)
    lines.append("PODSUMOWANIE:")
    lines.append(f"• Łączna liczba godzin: {total_hours:.2f} h")
    lines.append(f"• Liczba przepracowanych dni: {unique_days}")
    if total_bonus > 0:
        lines.append(f"• W tym premie: {total_bonus:.2f} zł")
    lines.append(f"• Łączne wynagrodzenie do wypłaty: {total_payout:,.2f} zł")
    lines.append("")
    lines.append("ROZBICIE NA STANOWISKA:")
    lines.append(f"• Ścianka wspinaczkowa: {climbing_hours:.2f} h | {climbing_earned:,.2f} zł")
    lines.append(f"• Barek / Recepcja: {bar_hours:.2f} h | {bar_earned:,.2f} zł")
    lines.append("")
    lines.append("=" * 48)
    lines.append("SZCZEGÓŁOWY WYKAZ PRZEPRACOWANYCH DNI I ZADAŃ:")
    lines.append("")

    df_sorted = df.sort_values(by="entry_date", ascending=True)
    entries_by_date = {}
    for _, row in df_sorted.iterrows():
        d = str(row["entry_date"])
        if d not in entries_by_date:
            entries_by_date[d] = []
        entries_by_date[d].append(row)

    for idx, (d_str, items) in enumerate(entries_by_date.items(), start=1):
        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            formatted_d = d_obj.strftime("%d.%m.%Y")
            w_idx = d_obj.weekday()
            weekday_str = WEEKDAY_NAMES_PL[w_idx] if 0 <= w_idx < len(WEEKDAY_NAMES_PL) else ""
        except Exception:
            formatted_d = d_str
            weekday_str = ""

        day_hours = sum(float(it["hours_worked"]) for it in items)
        day_earned = sum(float(it["total_earned"]) for it in items)
        multi_str = f" ({len(items)} zmiany)" if len(items) > 1 else ""

        lines.append(f"{idx}. {formatted_d} ({weekday_str}){multi_str} - Razem: {day_hours:.2f} h | {day_earned:,.2f} zł")
        for it in items:
            role = it["role_name"]
            h = float(it["hours_worked"])
            rate = float(it["hourly_rate"])
            bon = float(it.get("bonus", 0.0) or 0.0)
            earned = float(it["total_earned"])
            notes = str(it.get("notes", "") or "").strip()

            bon_str = f" + {bon:.2f} zł premii" if bon > 0 else ""
            lines.append(f"   - {role}: {h:.2f} h × {rate:.2f} zł/h{bon_str} = {earned:,.2f} zł")
            if notes:
                lines.append(f"     Co robiono: {notes}")
            else:
                lines.append("     Co robiono: -")
        lines.append("")

    lines.append("=" * 48)
    lines.append("Wygenerowano z aplikacji Dziennik Pracy")
    return "\n".join(lines)


if "editing_id" not in st.session_state:
    st.session_state["editing_id"] = None

# Nagłówek aplikacji
status_text = "Supabase" if db.is_supabase else "Tryb lokalny"
status_class = "status-badge" if db.is_supabase else "status-badge local"

col_head_title, col_head_act = st.columns([3, 1])
with col_head_title:
    st.markdown(f"""
        <div class="app-header">
            <div>
                <h1 class="app-title">Dziennik Pracy</h1>
                <p class="app-subtitle">Rozliczenie godzin</p>
            </div>
            <div>
                <span class="{status_class}">{status_text}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_head_act:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if st.button("Wyloguj", use_container_width=True):
        auth.logout()

# Zakładki
tab_add, tab_stats, tab_journal = st.tabs([
    "Nowy wpis",
    "Podsumowanie",
    "Dziennik",
])


# =====================================================================
# ZAKŁADKA 1: NOWY WPIS
# =====================================================================
with tab_add:
    # Potwierdzenie zapisu wpisu
    if st.session_state.get("entry_saved_success", False):
        st.success("Wpis został pomyślnie zapisany.")
        st.session_state["entry_saved_success"] = False

    c_date, c_role = st.columns([1, 1])
    with c_date:
        entry_date = st.date_input("Data:", value=date.today(), format="DD.MM.YYYY")
    with c_role:
        role_options = list(DEFAULT_ROLES.keys())
        selected_role = st.selectbox("Stanowisko:", options=role_options, index=0)

    hourly_rate = DEFAULT_ROLES.get(selected_role, 35.00)

    st.markdown(f"""
        <div style="font-size: 0.9rem; color: #D6DEC8; margin-bottom: 8px;">
            Stawka: <b style="color: #F0CA86;">{hourly_rate:.2f} zł / h</b>
        </div>
    """, unsafe_allow_html=True)

    c_hours, c_bonus = st.columns([1, 1])
    with c_hours:
        hours_worked = st.number_input(
            "Godziny:",
            min_value=0.25,
            max_value=24.0,
            value=8.0,
            step=0.25,
            format="%.2f"
        )
    with c_bonus:
        bonus = st.number_input(
            "Premia (zł):",
            min_value=0.0,
            value=0.0,
            step=10.0,
            format="%.2f"
        )

    notes = st.text_area("Notatki:", height=75)

    calculated_total = round(hourly_rate * hours_worked + bonus, 2)
    st.markdown(f"""
        <div class="live-calc-box">
            <div>
                <div class="live-calc-title">{hours_worked:.2f} h × {hourly_rate:.2f} zł/h {f'+ {bonus:.2f} zł premii' if bonus > 0 else ''}</div>
                <div style="font-size: 0.8rem; color: #B3BEA4;">{selected_role}</div>
            </div>
            <div style="text-align: right;">
                <div class="live-calc-title">Razem:</div>
                <div class="live-calc-amount">{calculated_total:,.2f} zł</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Zapisz", type="primary", use_container_width=True):
        db.add_entry(
            entry_date=entry_date,
            role_name=selected_role,
            hourly_rate=hourly_rate,
            hours_worked=hours_worked,
            bonus=bonus,
            notes=notes
        )
        st.session_state["entry_saved_success"] = True
        st.rerun()


# =====================================================================
# ZAKŁADKA 2: PODSUMOWANIE MIESIĘCZNE
# =====================================================================
with tab_stats:
    all_months = db.get_all_months()
    curr_month_str = datetime.now().strftime("%Y-%m")

    selected_month = st.selectbox(
        "Miesiąc:",
        options=all_months,
        format_func=format_month_label,
        index=0 if curr_month_str in all_months else 0
    )

    entries = db.get_entries(month_prefix=selected_month)
    df = pd.DataFrame(entries) if entries else pd.DataFrame()

    if df.empty:
        st.info("Brak wpisów dla wybranego miesiąca.")
    else:
        df["hours_worked"] = df["hours_worked"].astype(float)
        df["total_earned"] = df["total_earned"].astype(float)
        if "bonus" not in df.columns:
            df["bonus"] = 0.0
        else:
            df["bonus"] = df["bonus"].fillna(0.0).astype(float)

        total_hours = df["hours_worked"].sum()
        total_payout = df["total_earned"].sum()
        unique_days = df["entry_date"].nunique()
        avg_per_day = round(total_payout / unique_days, 2) if unique_days > 0 else 0.0

        climbing_mask = df["role_name"].str.contains("wspinaczkowa", case=False, na=False)
        bar_mask = df["role_name"].str.contains("barku|recepcja", case=False, na=False)

        climbing_hours = df[climbing_mask]["hours_worked"].sum()
        climbing_earned = df[climbing_mask]["total_earned"].sum()

        bar_hours = df[bar_mask]["hours_worked"].sum()
        bar_earned = df[bar_mask]["total_earned"].sum()

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
                    <div class="kpi-label">Ścianka Tech</div>
                    <div class="kpi-value" style="color: #C5CEB8;">{climbing_hours:.1f} h</div>
                    <div class="kpi-sub">{climbing_earned:,.2f} zł</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Barek / Recepcja</div>
                    <div class="kpi-value" style="color: #E2C29B;">{bar_hours:.1f} h</div>
                    <div class="kpi-sub">{bar_earned:,.2f} zł</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='font-size: 0.9rem; font-weight: 600; margin: 12px 0 6px 0;'>Godziny w dniach:</div>", unsafe_allow_html=True)
        daily_summary = df.groupby("entry_date")["hours_worked"].sum().reset_index()
        daily_summary = daily_summary.sort_values("entry_date")
        st.bar_chart(data=daily_summary.set_index("entry_date"), color="#8F9779")

        # Sekcja: Raport miesięczny AI
        st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #F5F2EB; margin: 20px 0 8px 0;'>Raport miesięczny</div>", unsafe_allow_html=True)

        col_btn_gen, col_btn_csv = st.columns([2, 1])
        with col_btn_gen:
            gen_clicked = st.button("Generuj raport", type="primary", use_container_width=True)
        with col_btn_csv:
            export_cols = [c for c in ["entry_date", "role_name", "hours_worked", "hourly_rate", "bonus", "total_earned", "notes"] if c in df.columns]
            csv_data = df[export_cols].to_csv(index=False)
            st.download_button(
                label="Pobierz CSV",
                data=csv_data,
                file_name=f"Rozliczenie_{selected_month}.csv",
                mime="text/csv",
                use_container_width=True
            )

        report_session_key = f"ai_report_{selected_month}"
        err_session_key = f"ai_report_err_{selected_month}"

        if gen_clicked:
            with st.spinner("Generowanie raportu przez AI..."):
                month_label = format_month_label(selected_month)
                rep_text, rep_err = generate_ai_monthly_report(df, month_label)
                st.session_state[report_session_key] = rep_text
                st.session_state[err_session_key] = rep_err

        if report_session_key in st.session_state:
            rep_text = st.session_state[report_session_key]
            rep_err = st.session_state.get(err_session_key)

            if rep_err:
                st.info(rep_err)

            with st.container(border=True):
                st.markdown("<div style='font-size: 0.82rem; color: #A8B29A; margin-bottom: 6px;'>Podgląd raportu (kliknij ikonę w rogu, aby skopiować):</div>", unsafe_allow_html=True)
                st.code(rep_text, language="text")

                st.download_button(
                    label="Pobierz raport (TXT)",
                    data=rep_text,
                    file_name=f"Raport_{selected_month}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        else:
            st.markdown("<div style='font-size: 0.85rem; color: #8F9779; margin-top: 6px;'>Kliknij <b>Generuj raport</b>, aby utworzyć podsumowanie godzin i zadań za pomocą AI.</div>", unsafe_allow_html=True)

        with st.expander("Szczegółowy wykaz zmian (roboczy)", expanded=False):
            detailed_text = generate_detailed_report(df, selected_month)
            st.code(detailed_text, language="text")


# =====================================================================
# ZAKŁADKA 3: DZIENNIK
# =====================================================================
with tab_journal:
    all_months = db.get_all_months()
    journal_month = st.selectbox(
        "Miesiąc:",
        options=all_months,
        format_func=format_month_label,
        key="journal_month_select"
    )

    j_entries = db.get_entries(month_prefix=journal_month)

    if not j_entries:
        st.info("Brak wpisów dla wybranego miesiąca.")
    else:
        entries_by_date = {}
        for item in j_entries:
            d = item["entry_date"]
            if d not in entries_by_date:
                entries_by_date[d] = []
            entries_by_date[d].append(item)

        for d_str, day_items in entries_by_date.items():
            try:
                date_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                formatted_d = date_obj.strftime("%d.%m.%Y")
                weekday_name = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"][date_obj.weekday()]
            except Exception:
                formatted_d = d_str
                weekday_name = ""

            day_total_hours = sum(float(i["hours_worked"]) for i in day_items)
            day_total_earned = sum(float(i["total_earned"]) for i in day_items)
            multi_note = f" ({len(day_items)} zmiany)" if len(day_items) > 1 else ""

            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin: 14px 0 6px 0; border-bottom: 1px solid rgba(143, 151, 121, 0.25); padding-bottom: 3px;">
                    <div>
                        <span style="font-size: 1.05rem; font-weight: 700; color: #F5F2EB;">{formatted_d}</span>
                        <span style="font-size: 0.8rem; color: #A8B29A; margin-left: 6px;">{weekday_name}{multi_note}</span>
                    </div>
                    <div style="font-size: 0.9rem; font-weight: 600; color: #F0CA86;">
                        {day_total_hours:.2f} h | {day_total_earned:,.2f} zł
                    </div>
                </div>
            """, unsafe_allow_html=True)

            for entry in day_items:
                entry_id = entry["id"]

                # Kontener wpisu: zarówno podgląd, jak i formularz edycji oraz przycisk Edytuj są wewnątrz tej samej ramki
                with st.container(border=True):
                    # TRYB EDYCJI W TYM SAMYM MIEJSCU
                    if st.session_state.get("editing_id") == entry_id:
                        st.markdown("<div style='font-size: 0.9rem; font-weight: 700; color: #F5F2EB; margin-bottom: 8px;'>Edycja wpisu</div>", unsafe_allow_html=True)

                        ed_c1, ed_c2 = st.columns([1, 1])
                        with ed_c1:
                            try:
                                parsed_date = datetime.strptime(entry["entry_date"], "%Y-%m-%d").date()
                            except Exception:
                                parsed_date = date.today()
                            edit_date = st.date_input("Data:", value=parsed_date, key=f"edit_date_{entry_id}")
                            
                            is_climb = "wspinaczkowa" in entry["role_name"].lower()
                            edit_role = st.selectbox(
                                "Stanowisko:",
                                options=list(DEFAULT_ROLES.keys()),
                                index=0 if is_climb else 1,
                                key=f"edit_role_{entry_id}"
                            )
                        with ed_c2:
                            edit_hours = st.number_input(
                                "Godziny:",
                                min_value=0.25,
                                max_value=24.0,
                                value=float(entry["hours_worked"]),
                                step=0.25,
                                format="%.2f",
                                key=f"edit_hours_{entry_id}"
                            )
                            edit_bonus = st.number_input(
                                "Premia (zł):",
                                min_value=0.0,
                                value=float(entry.get("bonus", 0.0) or 0.0),
                                step=10.0,
                                format="%.2f",
                                key=f"edit_bonus_{entry_id}"
                            )

                        edit_notes = st.text_area("Notatki:", value=entry.get("notes", ""), height=65, key=f"edit_notes_{entry_id}")

                        col_b_save, col_b_cancel, col_b_del = st.columns([1, 1, 1])
                        with col_b_save:
                            if st.button("Zapisz", key=f"save_{entry_id}", type="primary", use_container_width=True):
                                rate = DEFAULT_ROLES.get(edit_role, float(entry.get("hourly_rate", 35.0)))
                                db.update_entry(
                                    entry_id=entry_id,
                                    entry_date=edit_date,
                                    role_name=edit_role,
                                    hourly_rate=rate,
                                    hours_worked=edit_hours,
                                    bonus=edit_bonus,
                                    notes=edit_notes
                                )
                                st.session_state["editing_id"] = None
                                st.rerun()

                        with col_b_cancel:
                            if st.button("Anuluj", key=f"cancel_{entry_id}", use_container_width=True):
                                st.session_state["editing_id"] = None
                                st.rerun()

                        with col_b_del:
                            if st.button("Usuń", key=f"del_{entry_id}", use_container_width=True):
                                db.delete_entry(entry_id)
                                st.session_state["editing_id"] = None
                                st.rerun()

                    # TRYB ZWYKŁY (PODGLĄD KARTY Z PRZYCISKIEM EDYTUJ W ŚRODKU)
                    else:
                        is_climbing = "wspinaczkowa" in entry["role_name"].lower()
                        role_class = "climbing" if is_climbing else "bar"
                        bonus_val = float(entry.get("bonus", 0.0) or 0.0)
                        bonus_str = f" | Premia: {bonus_val:.2f} zł" if bonus_val > 0 else ""

                        col_r, col_e = st.columns([3, 1])
                        with col_r:
                            st.markdown(f'<span class="entry-role-pill {role_class}">{entry["role_name"]}</span>', unsafe_allow_html=True)
                        with col_e:
                            st.markdown(f'<div class="entry-earned" style="text-align: right;">{float(entry["total_earned"]):,.2f} zł</div>', unsafe_allow_html=True)

                        st.markdown(f'<div class="entry-stats"><b>{float(entry["hours_worked"]):.2f} h</b> &nbsp;|&nbsp; {float(entry["hourly_rate"]):.2f} zł/h{bonus_str}</div>', unsafe_allow_html=True)

                        if entry.get("notes"):
                            st.markdown(f'<div class="entry-notes">{entry["notes"]}</div>', unsafe_allow_html=True)

                        # Przycisk Edytuj w środku prostokąta danego dnia
                        c_space, c_btn = st.columns([4, 1])
                        with c_btn:
                            if st.button("Edytuj", key=f"edit_btn_{entry_id}", use_container_width=True):
                                st.session_state["editing_id"] = entry_id
                                st.rerun()
