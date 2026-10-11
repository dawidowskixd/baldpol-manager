import os
import sqlite3
import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe z .env, jeśli istnieje
load_dotenv()

DEFAULT_ROLES = {
    "Ścianka wspinaczkowa (prace techniczne)": 35.00,
    "Barek / Recepcja (praca zmianowa)": 31.40,
}

ROLE_ICONS = {
    "Ścianka wspinaczkowa (prace techniczne)": "🧗",
    "Barek / Recepcja (praca zmianowa)": "☕",
}

ROLE_COLORS = {
    "Ścianka wspinaczkowa (prace techniczne)": "#7E8A6B",  # Muted Sage/Khaki
    "Barek / Recepcja (praca zmianowa)": "#A27035",        # Warm Amber/Earth Brown
}

LOCAL_DB_FILE = "local_work_tracker.db"


def _get_secret(key: str, default: str = "") -> str:
    """Pobiera sekret z st.secrets lub zmiennych środowiskowych."""
    try:
        if key in st.secrets and st.secrets[key]:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, default).strip()


class DatabaseService:
    def __init__(self):
        self.supabase_url = _get_secret("SUPABASE_URL")
        self.supabase_key = _get_secret("SUPABASE_KEY")
        self.client = None
        self.is_supabase = False

        if self.supabase_url.startswith("http") and self.supabase_key:
            try:
                from supabase import create_client
                self.client = create_client(self.supabase_url, self.supabase_key)
                # Szybki test połączenia
                self.client.table("work_entries").select("id").limit(1).execute()
                self.is_supabase = True
            except Exception as e:
                # W przypadku błędu połączenia fallback do SQLite
                self.is_supabase = False
                self.client = None

        if not self.is_supabase:
            self._init_sqlite()

    def _init_sqlite(self):
        """Inicjalizacja lokalnej bazy SQLite w trybie offline/fallback."""
        with sqlite3.connect(LOCAL_DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_entries (
                    id TEXT PRIMARY KEY,
                    entry_date TEXT NOT NULL,
                    role_name TEXT NOT NULL,
                    hourly_rate REAL NOT NULL,
                    hours_worked REAL NOT NULL,
                    total_earned REAL NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_entries_date ON work_entries (entry_date DESC)")
            conn.commit()

    def add_entry(
        self,
        entry_date: date | str,
        role_name: str,
        hourly_rate: float,
        hours_worked: float,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Dodaje nowy wpis pracy."""
        date_str = str(entry_date)
        total_earned = round(float(hourly_rate) * float(hours_worked), 2)
        now_iso = datetime.now().isoformat()
        new_id = str(uuid.uuid4())

        data = {
            "id": new_id,
            "entry_date": date_str,
            "role_name": role_name,
            "hourly_rate": float(hourly_rate),
            "hours_worked": float(hours_worked),
            "total_earned": total_earned,
            "notes": (notes or "").strip(),
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        if self.is_supabase and self.client:
            try:
                res = self.client.table("work_entries").insert(data).execute()
                if res.data:
                    return res.data[0]
                return data
            except Exception as e:
                # Jeśli błąd w Supabase, zapisz lokalnie
                pass

        # SQLite
        with sqlite3.connect(LOCAL_DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO work_entries 
                (id, entry_date, role_name, hourly_rate, hours_worked, total_earned, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["entry_date"], data["role_name"], data["hourly_rate"],
                data["hours_worked"], data["total_earned"], data["notes"],
                data["created_at"], data["updated_at"]
            ))
            conn.commit()
        return data

    def get_entries(self, month_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Pobiera wpisy, opcjonalnie filtrowane po miesiącu (format 'YYYY-MM').
        Zwraca posortowane od najnowszych.
        """
        if self.is_supabase and self.client:
            try:
                query = self.client.table("work_entries").select("*")
                if month_prefix:
                    # np. '2026-10-01' do '2026-10-31'
                    start_date = f"{month_prefix}-01"
                    end_date = f"{month_prefix}-31"
                    query = query.gte("entry_date", start_date).lte("entry_date", end_date)
                query = query.order("entry_date", desc=True).order("created_at", desc=True)
                res = query.execute()
                return res.data or []
            except Exception:
                pass

        # SQLite
        with sqlite3.connect(LOCAL_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if month_prefix:
                cursor.execute("""
                    SELECT * FROM work_entries 
                    WHERE entry_date LIKE ? 
                    ORDER BY entry_date DESC, created_at DESC
                """, (f"{month_prefix}%",))
            else:
                cursor.execute("""
                    SELECT * FROM work_entries 
                    ORDER BY entry_date DESC, created_at DESC
                """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_entry(
        self,
        entry_id: str,
        entry_date: date | str,
        role_name: str,
        hourly_rate: float,
        hours_worked: float,
        notes: str = ""
    ) -> bool:
        """Aktualizuje istniejący wpis."""
        date_str = str(entry_date)
        total_earned = round(float(hourly_rate) * float(hours_worked), 2)
        now_iso = datetime.now().isoformat()

        update_payload = {
            "entry_date": date_str,
            "role_name": role_name,
            "hourly_rate": float(hourly_rate),
            "hours_worked": float(hours_worked),
            "total_earned": total_earned,
            "notes": (notes or "").strip(),
            "updated_at": now_iso,
        }

        if self.is_supabase and self.client:
            try:
                self.client.table("work_entries").update(update_payload).eq("id", entry_id).execute()
                return True
            except Exception:
                pass

        with sqlite3.connect(LOCAL_DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE work_entries 
                SET entry_date = ?, role_name = ?, hourly_rate = ?, hours_worked = ?, 
                    total_earned = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (
                update_payload["entry_date"], update_payload["role_name"],
                update_payload["hourly_rate"], update_payload["hours_worked"],
                update_payload["total_earned"], update_payload["notes"],
                update_payload["updated_at"], entry_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def delete_entry(self, entry_id: str) -> bool:
        """Usuwa wpis o danym ID."""
        if self.is_supabase and self.client:
            try:
                self.client.table("work_entries").delete().eq("id", entry_id).execute()
                return True
            except Exception:
                pass

        with sqlite3.connect(LOCAL_DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_entries WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_months(self) -> List[str]:
        """Zwraca unikalną listę miesięcy 'YYYY-MM' z istniejących wpisów."""
        months = set()
        entries = self.get_entries()
        for e in entries:
            d = e.get("entry_date", "")
            if len(d) >= 7:
                months.add(d[:7])
        
        # Zawsze dodaj bieżący miesiąc
        curr_month = datetime.now().strftime("%Y-%m")
        months.add(curr_month)
        
        return sorted(list(months), reverse=True)

    def migrate_local_to_supabase(self) -> Tuple[int, str]:
        """Migruje lokalne wpisy SQLite do Supabase po skonfigurowaniu kluczy."""
        if not (self.is_supabase and self.client):
            return 0, "Brak aktywnego połączenia z Supabase."

        if not os.path.exists(LOCAL_DB_FILE):
            return 0, "Brak lokalnej bazy do migracji."

        with sqlite3.connect(LOCAL_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM work_entries")
            rows = [dict(r) for r in cursor.fetchall()]

        if not rows:
            return 0, "Brak wpisów w lokalnej bazie."

        migrated_count = 0
        for row in rows:
            try:
                self.client.table("work_entries").upsert(row).execute()
                migrated_count += 1
            except Exception as e:
                return migrated_count, f"Błąd przy przenoszeniu wpisu {row['id']}: {str(e)}"

        return migrated_count, f"Pomyślnie zsynchronizowano {migrated_count} wpisów z Supabase!"


@st.cache_resource
def get_db() -> DatabaseService:
    """Zwraca zbuforowaną instancję DatabaseService."""
    return DatabaseService()
