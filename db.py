import os
import uuid
import calendar
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_ROLES = {
    "Ścianka wspinaczkowa (prace techniczne)": 35.00,
    "Barek / Recepcja (praca zmianowa)": 31.40,
}


def _get_secret(key: str, default: str = "") -> str:
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
        self.error_message = None

        if self.supabase_url:
            self.supabase_url = self.supabase_url.replace("/rest/v1/", "").replace("/rest/v1", "").rstrip("/")

        if not self.supabase_url or not self.supabase_key:
            self.error_message = "Brak konfiguracji SUPABASE_URL lub SUPABASE_KEY w Secrets."
            return

        try:
            from supabase import create_client
            self.client = create_client(self.supabase_url, self.supabase_key)
            # Test połączenia z tabelą
            self.client.table("work_entries").select("id").limit(1).execute()
            self.is_supabase = True
        except Exception as e:
            self.is_supabase = False
            self.client = None
            self.error_message = f"Błąd połączenia z Supabase: {str(e)}"

    def add_entry(
        self,
        entry_date: date | str,
        role_name: str,
        hourly_rate: float,
        hours_worked: float,
        bonus: float = 0.0,
        notes: str = ""
    ) -> Dict[str, Any]:
        if not (self.is_supabase and self.client):
            raise RuntimeError(self.error_message or "Brak połączenia z chmurą Supabase.")

        date_str = str(entry_date)
        total_earned = round(float(hourly_rate) * float(hours_worked) + float(bonus), 2)
        now_iso = datetime.now().isoformat()
        new_id = str(uuid.uuid4())

        data = {
            "id": new_id,
            "entry_date": date_str,
            "role_name": role_name,
            "hourly_rate": float(hourly_rate),
            "hours_worked": float(hours_worked),
            "bonus": float(bonus),
            "total_earned": total_earned,
            "notes": (notes or "").strip(),
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        try:
            res = self.client.table("work_entries").insert(data).execute()
            if res.data:
                return res.data[0]
            return data
        except Exception as e:
            if "bonus" in str(e):
                data_no_bonus = {k: v for k, v in data.items() if k != "bonus"}
                res = self.client.table("work_entries").insert(data_no_bonus).execute()
                if res.data:
                    return res.data[0]
                return data
            raise e

    def get_entries(self, month_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        if not (self.is_supabase and self.client):
            return []

        query = self.client.table("work_entries").select("*")
        if month_prefix:
            try:
                y_str, m_str = month_prefix.split("-")
                y, m = int(y_str), int(m_str)
                last_day = calendar.monthrange(y, m)[1]
                start_date = f"{y:04d}-{m:02d}-01"
                end_date = f"{y:04d}-{m:02d}-{last_day:02d}"
                query = query.gte("entry_date", start_date).lte("entry_date", end_date)
            except Exception as e_date:
                print(f"[Date parse error]: {e_date}")

        query = query.order("entry_date", desc=True).order("created_at", desc=True)
        res = query.execute()
        return res.data or []

    def update_entry(
        self,
        entry_id: str,
        entry_date: date | str,
        role_name: str,
        hourly_rate: float,
        hours_worked: float,
        bonus: float = 0.0,
        notes: str = ""
    ) -> bool:
        if not (self.is_supabase and self.client):
            raise RuntimeError(self.error_message or "Brak połączenia z chmurą Supabase.")

        date_str = str(entry_date)
        total_earned = round(float(hourly_rate) * float(hours_worked) + float(bonus), 2)
        now_iso = datetime.now().isoformat()

        update_payload = {
            "entry_date": date_str,
            "role_name": role_name,
            "hourly_rate": float(hourly_rate),
            "hours_worked": float(hours_worked),
            "bonus": float(bonus),
            "total_earned": total_earned,
            "notes": (notes or "").strip(),
            "updated_at": now_iso,
        }

        try:
            self.client.table("work_entries").update(update_payload).eq("id", entry_id).execute()
            return True
        except Exception as e:
            if "bonus" in str(e):
                up_no_bonus = {k: v for k, v in update_payload.items() if k != "bonus"}
                self.client.table("work_entries").update(up_no_bonus).eq("id", entry_id).execute()
                return True
            raise e

    def delete_entry(self, entry_id: str) -> bool:
        if not (self.is_supabase and self.client):
            raise RuntimeError(self.error_message or "Brak połączenia z chmurą Supabase.")

        self.client.table("work_entries").delete().eq("id", entry_id).execute()
        return True

    def get_all_months(self) -> List[str]:
        months = set()
        entries = self.get_entries()
        for e in entries:
            d = str(e.get("entry_date", ""))
            if len(d) >= 7:
                months.add(d[:7])

        curr_month = datetime.now().strftime("%Y-%m")
        months.add(curr_month)
        return sorted(list(months), reverse=True)


def get_db() -> DatabaseService:
    return DatabaseService()
