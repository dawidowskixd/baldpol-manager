# 🧗 Dziennik Pracy – Wspinaczka & Recepcja

Aplikacja webowa napisana w **Pythonie (Streamlit)** z bazą w chmurze **Supabase** (oraz automatycznym trybem offline SQLite), stworzona do ewidencjonowania godzin pracy, zadań dziennych i precyzyjnego wyliczania miesięcznych wynagrodzeń.

Działa na komputerze oraz na telefonie (**iPhone / Safari**), zaprojektowana w stylistyce **Frosted Glass (szkło akrylowe)** w **palecie barw ziemistych (khaki, butelkowa zieleń, brąz, beż)**.

---

## 🚀 Jak uruchomić aplikację lokalnie

1. Upewnij się, że masz zainstalowane biblioteki (są już w Twoim środowisku):
   ```bash
   pip install -r requirements.txt
   ```

2. Uruchom aplikację komendą:
   ```bash
   streamlit run app.py
   ```

3. Aplikacja otworzy się w przeglądarce pod adresem: `http://localhost:8501`.
   - **Domyślny PIN:** `1234`

---

## 📱 Dostęp z iPhone'a (Face ID i stały link)

### Opcja 1: Darmowy hosting w chmurze (Zalecane na stałe)
Aplikację możesz w 3 minuty wdrożyć na darmowym **[Streamlit Community Cloud](https://share.streamlit.io/)**:
1. Wrzuć projekt na darmowe repozytorium GitHub.
2. Połącz konto ze Streamlit Cloud i wskaż plik `app.py`.
3. W ustawieniach *Secrets* na Streamlit Cloud wklej zawartość swojego pliku `.streamlit/secrets.toml`.
4. Otrzymasz stały, bezpieczny link HTTPS (np. `twoja-nazwa.streamlit.app`).
5. Na iPhonie w Safari otwórz link i kliknij **Udostępnij -> Dodaj do ekranu początkowego** — aplikacja będzie zachowywać się jak natywna apka iOS z obsługą Face ID!

### Opcja 2: Ta sama sieć Wi-Fi w domu
Podczas uruchomienia `streamlit run app.py` w terminalu wyświetli się adres **Network URL** (np. `http://192.168.1.XX:8501`). Wpisz ten adres w Safari na iPhonie podłączonym do tego samego Wi-Fi.

---

## ☁️ Konfiguracja Bazy Danych Supabase

Aplikacja działa "out of the box" w trybie lokalnym SQLite, ale w dowolnym momencie możesz podpiąć bezpłatną bazę Supabase:

1. Zarejestruj się bezpłatnie na **[supabase.com](https://supabase.com)** i utwórz nowy projekt.
2. W menu bocznym wejdź w **SQL Editor**, kliknij **New Query**, wklej zawartość pliku `schema.sql` i kliknij **Run**.
3. Wejdź w **Project Settings -> Data API**:
   - Skopiuj **Project URL**
   - Skopiuj **anon public key**
4. Wklej te dane do pliku `.streamlit/secrets.toml`:
   ```toml
   SUPABASE_URL = "https://twoj-projekt.supabase.co"
   SUPABASE_KEY = "twoj-anon-klucz"
   APP_PIN = "1234"
   ```
5. Przeładuj aplikację. Status w nagłówku zmieni się na zielony badge `☁️ Supabase`.
6. Jeśli przed połączeniem dodałeś jakieś wpisy lokalnie, wejdź w zakładkę **⚙️ Baza & Ustawienia** i kliknij przycisk **🚀 Wyślij lokalne wpisy do Supabase**.

---

## 🧗 Stanowiska i Stawki

- **🧗 Prace techniczne na ściance wspinaczkowej:** `35.00 zł / h`
- **☕ Praca zmianowa na barku/recepcji:** `31.40 zł / h`
- **🎁 Stała premia miesięczna:** `300.00 zł` (doliczana automatycznie w podsumowaniu miesiąca)
- **⏰ Wyznaczanie czasu:** możliwość podania dokładnych godzin rozpoczęcia i zakończenia (np. 10:00 – 18:00) lub wpisania łącznej liczby godzin z ręki.
- Obsługa wielu wpisów w tym samym dniu (np. 3h ścianka + 4h barek).
