import os
import re
import warnings
from typing import Tuple, Optional
import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore", category=FutureWarning)

# Kolejność modeli do sprawdzenia
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
]


def get_gemini_api_key() -> str:
    """Pobiera klucz API Gemini z sesji Streamlit, secrets.toml lub zmiennych środowiskowych."""
    # 1. Sesja Streamlit (jeśli użytkownik wpisał w interfejsie)
    if "gemini_api_key" in st.session_state and st.session_state["gemini_api_key"]:
        key = str(st.session_state["gemini_api_key"]).strip()
        if key:
            return key

    # 2. st.secrets (.streamlit/secrets.toml)
    try:
        if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
        if "GOOGLE_API_KEY" in st.secrets and st.secrets["GOOGLE_API_KEY"]:
            return str(st.secrets["GOOGLE_API_KEY"]).strip()
    except Exception:
        pass

    # 3. Zmienne środowiskowe OS
    return os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()


def format_hours(val: float) -> str:
    """Formatuje liczbę godzin: np. 11.0 -> '11', 6.5 -> '6.5', 2.25 -> '2.25'."""
    try:
        val = float(val)
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}".rstrip("0").rstrip(".")
    except Exception:
        return "0"


def calculate_category_hours(df: pd.DataFrame) -> Tuple[float, float]:
    """Oblicza sumę godzin dla barku oraz technikaliów (ścianki)."""
    if df.empty:
        return 0.0, 0.0

    df_copy = df.copy()
    df_copy["hours_worked"] = df_copy["hours_worked"].astype(float)

    climbing_mask = df_copy["role_name"].str.contains("wspinaczkowa|technik", case=False, na=False)
    bar_mask = df_copy["role_name"].str.contains("barek|barku|recepcj", case=False, na=False)

    climbing_hours = float(df_copy[climbing_mask]["hours_worked"].sum())
    bar_hours = float(df_copy[bar_mask]["hours_worked"].sum())

    return bar_hours, climbing_hours


def generate_fallback_summary(df: pd.DataFrame) -> str:
    """Lokalne podsumowanie zadań bez użycia API (np. brak klucza lub brak połączenia)."""
    if df.empty:
        return "• Brak odnotowanych zadań w wybranym miesiącu."

    trivial_words = {"barek", "dyżur", "dyzur", "zmiana", "praca", "brak", "-", "", "szkolenie wstępne"}
    unique_tasks = []
    seen = set()

    df_sorted = df.sort_values(by="entry_date", ascending=True)
    for _, row in df_sorted.iterrows():
        notes = str(row.get("notes", "") or "").strip()
        if not notes:
            continue
        parts = [p.strip() for p in re.split(r"[,;\n]+", notes) if p.strip()]
        for p in parts:
            p_norm = p.lower()
            if p_norm not in trivial_words and p_norm not in seen:
                seen.add(p_norm)
                formatted = p[0].upper() + p[1:] if len(p) > 1 else p.upper()
                unique_tasks.append(f"• {formatted}")

    if not unique_tasks:
        return "• Standardowa obsługa zmianowa (brak odnotowanych szczególnych prac technicznych)."

    return "\n".join(unique_tasks)


def clean_bullet_points(raw_text: str) -> str:
    """Czyści tekst z AI, ujednolicając wypunktowanie do symbolu • i usuwając zbędne nagłówki."""
    cleaned_lines = []
    for line in raw_text.splitlines():
        l = line.strip()
        if not l:
            continue
        # Usuwamy ewentualne pogrubienia z początku linii jeśli AI dało np. **Zadania:**
        if re.match(r"^\*+[a-zA-Ząćęłńóśźż\s:]+\*+$", l, re.IGNORECASE):
            continue
        if l.lower().startswith(("podsumowanie:", "zadania:", "kluczowe:", "oto lista:")):
            continue

        if l.startswith("•"):
            item_text = l.lstrip("•").strip()
            l = f"• {item_text}"
        elif l.startswith(("* ", "- ", "+ ")):
            item_text = l[2:].strip()
            l = f"• {item_text}"
        elif re.match(r"^\d+[\.\)]\s*", l):
            item_text = re.sub(r"^\d+[\.\)]\s*", "", l).strip()
            l = f"• {item_text}"
        else:
            l = f"• {l}"

        cleaned_lines.append(l)

    if not cleaned_lines:
        return "• Standardowa obsługa zmianowa (brak odnotowanych szczególnych prac technicznych)."

    return "\n".join(cleaned_lines)


def generate_ai_monthly_report(
    df: pd.DataFrame,
    month_label: str,
    api_key: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Generuje raport miesięczny w ściśle określonym formacie:
    liczba godzin barek: x
    liczba godzin technikalia : x

    *wypunktowana lista najważniejszych zadań od kropek •*

    Zwraca krotkę: (pełna_treść_raportu, ewentualny_komunikat_ostrzeżenia).
    """
    bar_hours, climbing_hours = calculate_category_hours(df)
    header = (
        f"liczba godzin barek: {format_hours(bar_hours)}\n"
        f"liczba godzin technikalia : {format_hours(climbing_hours)}"
    )

    if df.empty:
        return f"{header}\n\n• Brak wpisów w wybranym miesiącu.", None

    has_notes = any(bool(str(r.get("notes", "") or "").strip()) for _, r in df.iterrows())
    if not has_notes:
        return f"{header}\n\n• Standardowa obsługa zmianowa (brak odnotowanych szczególnych prac technicznych).", None

    resolved_key = (api_key or get_gemini_api_key()).strip()
    if not resolved_key:
        fallback_bullets = generate_fallback_summary(df)
        report = f"{header}\n\n{fallback_bullets}"
        return report, "Brak klucza API Gemini. Zastosowano automatyczne podsumowanie lokalne."

    # Przygotowanie danych do promptu
    notes_list = []
    df_sorted = df.sort_values(by="entry_date", ascending=True)
    for _, row in df_sorted.iterrows():
        d = str(row.get("entry_date", ""))
        role = str(row.get("role_name", ""))
        h = str(row.get("hours_worked", ""))
        notes = str(row.get("notes", "") or "").strip()
        if notes:
            notes_list.append(f"- Data: {d}, Stanowisko: {role}, Czas: {h}h, Notatka: {notes}")
        else:
            notes_list.append(f"- Data: {d}, Stanowisko: {role}, Czas: {h}h, Notatka: (brak)")

    notes_text = "\n".join(notes_list)

    prompt = f"""Jesteś precyzyjnym asystentem do generowania podsumowań pracowniczych dla kierownika.
Poniżej znajduje się lista dyżurów i notatek pracownika z miesiąca {month_label}:

{notes_text}

ZADANIE:
Przygotuj zwięzłą listę wypunktowaną od kropek (każdy punkt zaczyna się od znaku '• '), przedstawiającą najważniejsze rzeczy, którymi zajmował się pracownik.

KRYTYCZNE ZASADY SELEKCJI:
1. Program ma sam odrzucić mało ważne, banalne lub powtarzalne kwestie (np. rutynowa obsługa barku bez konkretów, same dyżury, ogólne słowa typu 'barek').
2. ZACHOWAJ i zwięźle opisz tylko najważniejsze kwestie warte wspomnienia (np. prace techniczne, serwisowe, montażowe, desetting, monitoring, szkolenia, większe porządki, nietypowe zadania).
3. Połącz powtarzające się czynności w syntetyczne punkty (np. zamiast kilkukrotnie pisać o kanciapie, zredaguj jeden zwięzły punkt).
4. Nie dodawaj ŻADNYCH emotikonów ani emoji.
5. Nie dodawaj nagłówków typu 'Podsumowanie:', 'Oto lista:' ani dopisków na dole. Zwróć WYŁĄCZNIE wypunktowaną listę od znaku '• '.
6. Nie korzystaj z profesjonalnego słownictwa, ma to być luźna informacja dla przełożonego czym pracownik zajmował sie w danym miesiącu, lista ma brzmieć naturalnie tak jakby było to pisane odręcznie.  
7. Desettingi zawsze opisuj tylko i wyłącznie w zwięzły sposób: 'desetting'.
8. Porządki na kanciapie opisuj w odzielnym punkcie i opisuj to tylko w prosty sposób: 'ogar kanciapy'.
"""

    try:
        import google.generativeai as genai
        genai.configure(api_key=resolved_key)

        last_err = None
        for model_name in GEMINI_MODELS:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    generation_config={"temperature": 0.2}
                )
                response = model.generate_content(prompt)
                ai_text = response.text.strip()
                if ai_text:
                    bullets = clean_bullet_points(ai_text)
                    return f"{header}\n\n{bullets}", None
            except Exception as e:
                last_err = e
                continue

        fallback_bullets = generate_fallback_summary(df)
        return (
            f"{header}\n\n{fallback_bullets}",
            f"Błąd Gemini ({str(last_err)}). Zastosowano podsumowanie lokalne."
        )

    except Exception as e:
        fallback_bullets = generate_fallback_summary(df)
        return (
            f"{header}\n\n{fallback_bullets}",
            f"Błąd inicjalizacji AI ({str(e)}). Zastosowano podsumowanie lokalne."
        )
