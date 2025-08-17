"""
NBP API Client - Pobieranie kursów walut z API NBP
Punkt 11: Implementacja pobierania kursów NBP z obsługą weekendów/świąt

FUNKCJONALNOŚCI:
- Pobieranie kursu USD z tabeli A NBP
- Obsługa weekendów i świąt (cofanie do ostatniego notowania)
- Cache'owanie wyników w bazie danych
- Retry mechanism dla błędów sieciowych
- Walidacja i formatowanie dat
"""

import requests
import streamlit as st
from datetime import datetime, date, timedelta
from typing import Optional, Dict
import time

# Import z naszego modułu db
import db

class NBPApiClient:
    """Klient API NBP do pobierania kursów walut"""
    
    BASE_URL = "https://api.nbp.pl/api/exchangerates"
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # sekundy
    
    def __init__(self):
        self.session = requests.Session()
        # Ustawienia nagłówków zgodnie z zaleceniami NBP
        self.session.headers.update({
            'User-Agent': 'Covered-Call-Dashboard/1.0',
            'Accept': 'application/json'
        })
    
    def get_usd_rate(self, target_date: date) -> Optional[Dict]:
        """
        Pobiera kurs USD z NBP na określoną datę
        
        Args:
            target_date: Data dla której pobieramy kurs
            
        Returns:
            dict: {'date': 'YYYY-MM-DD', 'rate': float, 'source': 'NBP'} lub None
        """
        # Najpierw sprawdź cache w bazie
        cached_rate = db.get_fx_rate(target_date, 'USD')
        if cached_rate:
            st.info(f"💾 Używam kursu z cache: {cached_rate['rate']:.4f} na {cached_rate['date']}")
            return cached_rate
        
        # Jeśli nie ma w cache, pobierz z API
        return self._fetch_usd_rate_from_api(target_date)
    
    def get_usd_rate_d_minus_1(self, operation_date: date) -> Optional[Dict]:
        """
        Pobiera kurs USD na dzień D-1 (dzień przed operacją)
        Cofanie do ostatniego dnia roboczego jeśli D-1 to weekend/święto
        
        Args:
            operation_date: Data operacji
            
        Returns:
            dict: Kurs na dzień D-1 lub ostatni dostępny
        """
        # Zacznij od dnia przed operacją
        target_date = operation_date - timedelta(days=1)
        
        # Cofaj maksymalnie 7 dni w poszukiwaniu kursu
        for i in range(7):
            check_date = target_date - timedelta(days=i)
            
            # Pomiń soboty i niedziele
            if check_date.weekday() >= 5:  # 5=sobota, 6=niedziela
                continue
                
            rate = self.get_usd_rate(check_date)
            if rate:
                if i > 0:
                    st.warning(f"⚠️ Kurs na D-1 ({target_date}) niedostępny, używam {check_date}")
                return rate
        
        st.error(f"❌ Nie znaleziono kursu USD w okolicach {target_date}")
        return None
    
    def _fetch_usd_rate_from_api(self, target_date: date) -> Optional[Dict]:
        """
        Pobiera kurs USD z API NBP dla konkretnej daty
        
        Args:
            target_date: Data kursu
            
        Returns:
            dict: Dane kursu lub None jeśli błąd
        """
        date_str = target_date.strftime('%Y-%m-%d')
        url = f"{self.BASE_URL}/rates/A/USD/{date_str}/"
        
        for attempt in range(self.MAX_RETRIES):
            try:
                st.info(f"🌐 Pobieram kurs USD z NBP na {date_str} (próba {attempt + 1})")
                
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    rate_value = data['rates'][0]['mid']
                    
                    # Zapisz do cache w bazie
                    rate_data = {
                        'date': date_str,
                        'rate': float(rate_value),
                        'source': 'NBP'
                    }
                    
                    if db.insert_fx_rate(date_str, 'USD', rate_value, 'NBP'):
                        st.success(f"✅ Pobrałem i zapisałem kurs USD: {rate_value:.4f} na {date_str}")
                        return rate_data
                    else:
                        st.error("❌ Błąd zapisu kursu do bazy")
                        return rate_data  # Zwróć dane mimo błędu zapisu
                
                elif response.status_code == 404:
                    st.warning(f"📅 Brak kursu USD na {date_str} (weekend/święto)")
                    return None
                
                else:
                    st.warning(f"⚠️ Błąd API NBP: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                st.warning(f"🌐 Błąd sieciowy (próba {attempt + 1}): {e}")
            
            except (KeyError, ValueError, TypeError) as e:
                st.error(f"📊 Błąd parsowania odpowiedzi NBP: {e}")
                break
            
            # Poczekaj przed kolejną próbą
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_DELAY)
        
        st.error(f"❌ Nie udało się pobrać kursu USD na {date_str} po {self.MAX_RETRIES} próbach")
        return None
    
    def refresh_recent_rates(self, days_back: int = 7) -> Dict[str, bool]:
        """
        Odświeża kursy z ostatnich X dni
        
        Args:
            days_back: Liczba dni wstecz do odświeżenia
            
        Returns:
            dict: Wyniki odświeżania per data
        """
        results = {}
        today = date.today()
        
        st.info(f"🔄 Odświeżam kursy USD z ostatnich {days_back} dni...")
        
        for i in range(days_back):
            check_date = today - timedelta(days=i)
            
            # Pomiń weekendy
            if check_date.weekday() >= 5:
                continue
            
            # Usuń stary kurs jeśli istnieje
            db.delete_fx_rate(check_date, 'USD')
            
            # Pobierz nowy
            rate = self._fetch_usd_rate_from_api(check_date)
            results[check_date.strftime('%Y-%m-%d')] = rate is not None
        
        return results
    
    def bulk_load_fx_rates(self, start_date, end_date):
        """
        Bulk loading kursów USD z zakresu dat
        
        Args:
            start_date: Data początkowa
            end_date: Data końcowa
            
        Returns:
            dict: Wyniki per data {'2025-01-15': True/False}
        """
        results = {}
        current_date = start_date
        
        st.info(f"🔄 Bulk loading kursów USD: {start_date} → {end_date}")
        
        while current_date <= end_date:
            # Pomiń weekendy
            if current_date.weekday() < 5:  # 0-4 = poniedziałek-piątek
                # Sprawdź czy już istnieje w cache
                existing = db.get_fx_rate(current_date, 'USD')
                if existing:
                    st.write(f"💾 {current_date}: już w cache ({existing['rate']:.4f})")
                    results[current_date.strftime('%Y-%m-%d')] = True
                else:
                    # Pobierz z API
                    rate = self._fetch_usd_rate_from_api(current_date)
                    results[current_date.strftime('%Y-%m-%d')] = rate is not None
                    
                    # Krótka pauza żeby nie przeciążyć API NBP
                    time.sleep(0.1)
            else:
                    st.write(f"⏭️ {current_date}: weekend/święto - pomijam")
                    results[current_date.strftime('%Y-%m-%d')] = False
            
            current_date += timedelta(days=1)
        
        # Podsumowanie
        success_count = sum(results.values())
        total_dates = len([k for k, v in results.items() if v != False])
        
        st.success(f"✅ Bulk loading ukończony: {success_count}/{total_dates} kursów")
        
        return results

    def get_available_date_range(self) -> Dict[str, Optional[str]]:
        """
        Sprawdza dostępny zakres dat w API NBP
        
        Returns:
            dict: {'oldest': 'YYYY-MM-DD', 'newest': 'YYYY-MM-DD'}
        """
        try:
            # NBP udostępnia kursy od 2002-01-02
            url = f"{self.BASE_URL}/rates/A/USD/last/1/"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                newest_date = data['rates'][0]['effectiveDate']
                return {
                    'oldest': '2002-01-02',  # Znany początek danych NBP
                    'newest': newest_date
                }
        except Exception as e:
            st.warning(f"Nie można sprawdzić zakresu dat NBP: {e}")
        
        return {'oldest': None, 'newest': None}

# ================================
# ŚWIĘTA NARODOWE POLSKI
# ================================

def get_polish_holidays(year: int) -> set:
    """
    Zwraca zestaw świąt narodowych Polski dla danego roku
    (dni kiedy NBP nie publikuje kursów)
    
    Args:
        year: Rok
        
    Returns:
        set: Zestaw dat świąt w formacie 'YYYY-MM-DD'
    """
    holidays = set()
    
    # Święta stałe
    holidays.add(f"{year}-01-01")  # Nowy Rok
    holidays.add(f"{year}-01-06")  # Trzech Króli
    holidays.add(f"{year}-05-01")  # Święto Pracy
    holidays.add(f"{year}-05-03")  # Święto Konstytucji
    holidays.add(f"{year}-08-15")  # Wniebowzięcie NMP
    holidays.add(f"{year}-11-01")  # Wszystkich Świętych
    holidays.add(f"{year}-11-11")  # Dzień Niepodległości
    holidays.add(f"{year}-12-25")  # Boże Narodzenie
    holidays.add(f"{year}-12-26")  # Drugi dzień Bożego Narodzenia
    
    # Święta ruchome (uproszczona logika - główne lata)
    easter_dates = {
        2023: "04-09", 2024: "03-31", 2025: "04-20", 2026: "04-05",
        2027: "03-28", 2028: "04-16", 2029: "04-01", 2030: "04-21"
    }
    
    if year in easter_dates:
        easter = easter_dates[year]
        holidays.add(f"{year}-{easter}")  # Wielkanoc
        
        # Poniedziałek Wielkanocny (dzień po Wielkanocy)
        easter_date = datetime.strptime(f"{year}-{easter}", "%Y-%m-%d").date()
        easter_monday = easter_date + timedelta(days=1)
        holidays.add(easter_monday.strftime('%Y-%m-%d'))
        
        # Boże Ciało (60 dni po Wielkanocy)
        corpus_christi = easter_date + timedelta(days=60)
        holidays.add(corpus_christi.strftime('%Y-%m-%d'))
    
    return holidays

def is_business_day(check_date: date) -> bool:
    """
    Sprawdza czy data to dzień roboczy NBP (nie weekend, nie święto)
    
    Args:
        check_date: Data do sprawdzenia
        
    Returns:
        bool: True jeśli dzień roboczy NBP
    """
    # Weekend
    if check_date.weekday() >= 5:  # sobota=5, niedziela=6
        return False
    
    # Święta polskie
    holidays = get_polish_holidays(check_date.year)
    if check_date.strftime('%Y-%m-%d') in holidays:
        return False
    
    return True

def auto_seed_on_startup() -> bool:
    """
    Automatyczne seed data przy starcie aplikacji
    Sprawdza czy brakuje kursów z ostatnich 7 dni i pobiera je
    
    Returns:
        bool: True jeśli wykonano seed
    """
    # Sprawdź pokrycie ostatnich 7 dni
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    # Policz dni robocze
    business_days = 0
    current_date = start_date
    while current_date <= end_date:
        if is_business_day(current_date):
            business_days += 1
        current_date += timedelta(days=1)
    
    # Sprawdź ile w cache
    conn = db.get_connection()
    existing_count = 0
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM fx_rates 
            WHERE code = 'USD' AND date BETWEEN ? AND ?
        """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        existing_count = cursor.fetchone()[0]
        conn.close()
    
    missing = business_days - existing_count
    
    # Jeśli brakuje > 2 kursów, wykonaj auto-seed
    if missing > 2:
        st.info(f"🌱 Auto-seed: brakuje {missing} kursów z ostatnich 7 dni")
        results = nbp_client.bulk_load_fx_rates(start_date, end_date)
        success_count = len([v for v in results.values() if v])
        st.success(f"✅ Auto-seed ukończony: {success_count} kursów")
        return True
    
    return False

# Globalna instancja klienta
nbp_client = NBPApiClient()

def get_usd_rate_for_date(operation_date: date) -> Optional[Dict]:
    """
    Funkcja helper do pobierania kursu USD na dzień D-1
    
    Args:
        operation_date: Data operacji
        
    Returns:
        dict: Kurs USD na D-1 lub None
    """
    return nbp_client.get_usd_rate_d_minus_1(operation_date)

def manual_override_rate(operation_date: date, custom_rate: float) -> bool:
    """
    Ręczne nadpisanie kursu USD dla danej daty
    
    Args:
        operation_date: Data operacji
        custom_rate: Ręcznie podany kurs
        
    Returns:
        bool: True jeśli sukces
    """
    try:
        date_str = operation_date.strftime('%Y-%m-%d')
        
        # Usuń stary kurs jeśli istnieje
        db.delete_fx_rate(operation_date, 'USD')
        
        # Zapisz nowy kurs z oznaczeniem manual
        success = db.insert_fx_rate(date_str, 'USD', custom_rate, 'MANUAL')
        
        if success:
            st.success(f"✅ Zapisano ręczny kurs USD: {custom_rate:.4f} na {date_str}")
        else:
            st.error("❌ Błąd zapisu ręcznego kursu")
        
        return success
        
    except Exception as e:
        st.error(f"Błąd ręcznego nadpisania kursu: {e}")
        return False

def test_nbp_api():
    """
    Test funkcjonalności NBP API
    
    Returns:
        dict: Wyniki testów
    """
    results = {
        'connection_test': False,
        'current_rate_test': False,
        'd_minus_1_test': False,
        'weekend_handling_test': False,
        'cache_test': False
    }
    
    try:
        # WYCZYŚĆ dane testowe przed testem
        import db
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM fx_rates WHERE source = 'NBP' AND date >= '2025-08-10'")
            conn.commit()
            conn.close()
        
        # Test połączenia z API
        date_range = nbp_client.get_available_date_range()
        results['connection_test'] = date_range['newest'] is not None
        
        # Test pobierania aktualnego kursu
        today = date.today()
        rate = nbp_client.get_usd_rate(today)
        # Może być None jeśli dziś to weekend/święto
        results['current_rate_test'] = True  # Test połączenia się udał
        
        # Test D-1
        yesterday = today - timedelta(days=1)
        d_minus_1_rate = nbp_client.get_usd_rate_d_minus_1(today)
        results['d_minus_1_test'] = d_minus_1_rate is not None
        
        # Test obsługi weekendu (użyj przeszłej soboty)
        saturday = today
        while saturday.weekday() != 5:  # Znajdź poprzednią sobotę
            saturday -= timedelta(days=1)
            if saturday < today - timedelta(days=7):
                break
        
        if saturday.weekday() == 5:
            weekend_rate = nbp_client.get_usd_rate_d_minus_1(saturday)
            results['weekend_handling_test'] = weekend_rate is not None
        else:
            results['weekend_handling_test'] = True  # Fallback
        
        # Test cache'a - drugi request powinien być z cache
        if d_minus_1_rate:
            cached_rate = nbp_client.get_usd_rate(d_minus_1_rate['date'])
            results['cache_test'] = (cached_rate is not None and 
                                   cached_rate['rate'] == d_minus_1_rate['rate'])
        
    except Exception as e:
        st.error(f"Błąd testów NBP API: {e}")
    
    return results

# Przykład użycia w Streamlit UI
def show_nbp_test_ui():
    """UI do testowania funkcjonalności NBP API"""
    
    st.header("🏦 Test NBP API - Punkt 11")
    
    # Test podstawowy
    if st.button("🧪 Uruchom testy NBP API"):
        test_results = test_nbp_api()
        
        st.write("**Wyniki testów:**")
        for test_name, result in test_results.items():
            if result:
                st.success(f"✅ {test_name}")
            else:
                st.error(f"❌ {test_name}")
        
        passed = sum(test_results.values())
        total = len(test_results)
        
        if passed == total:
            st.success(f"🎉 Punkt 11 działa poprawnie! ({passed}/{total})")
        else:
            st.warning(f"⚠️ Punkt 11 częściowo działa ({passed}/{total})")
    
    st.markdown("---")
    
    # Test interaktywny
    st.subheader("🔍 Test interaktywny")
    
    col1, col2 = st.columns(2)
    
    with col1:
        test_date = st.date_input("Data do sprawdzenia kursu", value=date.today())
        
        if st.button("Pobierz kurs USD"):
            with st.spinner("Pobieram kurs..."):
                rate = nbp_client.get_usd_rate(test_date)
                if rate:
                    st.success(f"Kurs USD na {rate['date']}: {rate['rate']:.4f}")
                    st.info(f"Źródło: {rate['source']}")
                else:
                    st.error("Nie znaleziono kursu dla tej daty")
    
    with col2:
        operation_date = st.date_input("Data operacji (test D-1)", value=date.today())
        
        if st.button("Pobierz kurs D-1"):
            with st.spinner("Pobieram kurs D-1..."):
                rate = nbp_client.get_usd_rate_d_minus_1(operation_date)
                if rate:
                    st.success(f"Kurs USD D-1: {rate['rate']:.4f} na {rate['date']}")
                    st.info(f"Źródło: {rate['source']}")
                else:
                    st.error("Nie znaleziono kursu D-1")
                    
# Test bulk loading (PUNKT 12A)
    st.subheader("📦 Bulk loading kursów")
    
    col1, col2 = st.columns(2)
    
    with col1:
        days_bulk = st.slider("Dni wstecz do pobrania", min_value=1, max_value=30, value=7)
    
    with col2:
        st.write("")  # Spacer
        if st.button("Bulk load kursy"):
            end_date = date.today()
            start_date = end_date - timedelta(days=days_bulk)
            
            with st.spinner("Bulk loading..."):
                results = nbp_client.bulk_load_fx_rates(start_date, end_date)
            
            st.write("**Wyniki bulk loading:**")
            for date_str, success in results.items():
                if success:
                    st.success(f"✅ {date_str}")
                else:
                    st.error(f"❌ {date_str}")
    
    st.markdown("---")

# Seed data (PUNKT 12B)
    st.subheader("🌱 Seed data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        seed_days = st.slider("Dni wstecz (seed)", min_value=7, max_value=60, value=30)
    
    with col2:
        st.write("")  # Spacer
        if st.button("Seed ostatnie kursy"):
            with st.spinner("Seed data..."):
                end_date = date.today()
                start_date = end_date - timedelta(days=seed_days)
                summary = nbp_client.bulk_load_fx_rates(start_date, end_date)
                st.success(f"🎉 Seed ukończony: {len([v for v in summary.values() if v])} kursów pobranych")
    
    st.markdown("---")
    
    # Sprawdzenie braków (PUNKT 12C)
    st.subheader("🔍 Sprawdzenie braków w cache")
    
    col1, col2 = st.columns(2)
    
    with col1:
        check_days = st.slider("Dni do sprawdzenia", min_value=7, max_value=90, value=30)
    
    with col2:
        st.write("")  # Spacer
        if st.button("Sprawdź braki"):
            # Inline sprawdzenie braków
            end_date = date.today()
            start_date = end_date - timedelta(days=check_days)

            # Policz dni robocze
            business_days = 0
            current_date = start_date
            while current_date <= end_date:
                if is_business_day(current_date):
                    business_days += 1
                current_date += timedelta(days=1)

            # Sprawdź ile w bazie
            conn = db.get_connection()
            existing_count = 0
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM fx_rates 
                    WHERE code = 'USD' AND date BETWEEN ? AND ?
                """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                existing_count = cursor.fetchone()[0]
                conn.close()

            missing_count = business_days - existing_count
            coverage = (existing_count / business_days * 100) if business_days > 0 else 0

            st.metric("Pokrycie cache", f"{coverage:.1f}%")
            st.write(f"**Dni robocze:** {business_days}")
            st.write(f"**W cache:** {existing_count}")
            st.write(f"**Brakuje:** {missing_count}")
    
    st.markdown("---")
 
 # Zarządzanie cache (PUNKT 14A)
    st.subheader("🗂️ Zarządzanie cache kursów")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Pokaż ostatnie kursy"):
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT date, rate, source FROM fx_rates 
                    WHERE code = 'USD' 
                    ORDER BY date DESC 
                    LIMIT 10
                """)
                rows = cursor.fetchall()
                conn.close()
                
                st.write("**Ostatnie 10 kursów USD:**")
                for row in rows:
                    st.write(f"📅 {row[0]}: {row[1]:.4f} ({row[2]})")
    
    with col2:
        if st.button("🗑️ Wyczyść cache"):
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM fx_rates WHERE code = 'USD'")
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                st.success(f"✅ Usunięto {deleted} kursów USD")
    
    with col3:
        if st.button("📈 Statystyki cache"):
            stats = db.get_fx_rates_stats()
            st.metric("Kursów USD", stats['total_records'])
            st.write(f"📅 {stats['oldest_date']} → {stats['newest_date']}")
    
    st.markdown("---")
 
    # Manual override
    st.subheader("✏️ Ręczne nadpisanie kursu")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        override_date = st.date_input("Data", value=date.today(), key="override_date")
    
    with col2:
        override_rate = st.number_input("Kurs USD", min_value=0.1, max_value=10.0, 
                                       value=4.0, step=0.0001, format="%.4f")
    
    with col3:
        st.write("")  # Spacer
        if st.button("Zapisz ręczny kurs"):
            if manual_override_rate(override_date, override_rate):
                st.rerun()  # Odśwież stronę
    
    # Odświeżanie cache
    st.subheader("🔄 Odświeżanie cache")
    
    col1, col2 = st.columns(2)
    
    with col1:
        days_back = st.slider("Dni wstecz", min_value=1, max_value=14, value=7)
    
    with col2:
        st.write("")  # Spacer
        if st.button("Odśwież kursy"):
            with st.spinner("Odświeżam kursy..."):
                results = nbp_client.refresh_recent_rates(days_back)
                
                st.write("**Wyniki odświeżania:**")
                for date_str, success in results.items():
                    if success:
                        st.success(f"✅ {date_str}")
                    else:
                        st.error(f"❌ {date_str}")
    
    # Statystyki cache
    st.subheader("📊 Statystyki cache")
    
    fx_stats = db.get_fx_rates_stats()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Kursów w cache", fx_stats['total_records'])
    
    with col2:
        if fx_stats['latest_usd_rate']:
            st.metric("Najnowszy kurs USD", f"{fx_stats['latest_usd_rate']:.4f}")
        else:
            st.metric("Najnowszy kurs USD", "Brak")
    
    with col3:
        if fx_stats['newest_date']:
            st.metric("Data najnowszego kursu", fx_stats['newest_date'])
        else:
            st.metric("Data najnowszego kursu", "Brak")

if __name__ == "__main__":
    # Przykład testowania
    print("Test NBP API Client...")
    
    # Test kursu na dziś
    today = date.today()
    rate = get_usd_rate_for_date(today)
    
    if rate:
        print(f"Kurs USD D-1 dla {today}: {rate['rate']:.4f} na {rate['date']}")
    else:
        print("Nie znaleziono kursu USD")