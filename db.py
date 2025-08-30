"""
Moduł bazy danych SQLite dla Covered Call Dashboard
Punkt 3: Podstawowe połączenie z bazą danych
NAPRAWIONY - kompletny plik bez błędów składni
"""


import sqlite3
import streamlit as st
from datetime import datetime as _datetime
from datetime import datetime
from datetime import datetime as _dt
from datetime import date as _date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
from typing import List, Dict, Optional, Tuple

# Ścieżka do bazy danych
DB_PATH = "portfolio.db"

def get_connection():
    """
    Utworzenie połączenia z bazą danych SQLite (wzmocnione):
      - foreign_keys = ON  → respektuje klucze obce i kaskady
      - journal_mode = WAL → mniej blokad przy równoległych odczytach/zapisach
      - busy_timeout = 5000 ms → łagodzi chwilowe locki
      - row_factory = sqlite3.Row → dostęp do kolumn po nazwie
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # PRAGMA – ustaw raz na połączeniu
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")

        return conn
    except Exception as e:
        # Streamlit-friendly komunikat; zachowujemy poprzednie zachowanie
        st.error(f"Błąd połączenia z bazą danych: {e}")
        return None

def init_database():
    """Inicjalizacja bazy danych - sprawdzenie czy istnieje i ewentualny wpis startowy."""
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()

        # Tworzymy tabelę app_info (jeśli nie istnieje).
        # Dodane sensowne domyślne wartości (nie zmienia logiki — i tak wstawiamy jawnie).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_info (
                id INTEGER PRIMARY KEY,
                version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Czy jest jakikolwiek rekord?
        cur.execute("SELECT COUNT(*) FROM app_info")
        count = int(cur.fetchone()[0] or 0)

        # Jeśli brak — wstaw rekord startowy
        if count == 0:
            now = datetime.now().isoformat(timespec="seconds")
            cur.execute("""
                INSERT INTO app_info (version, created_at, last_updated)
                VALUES (?, ?, ?)
            """, ("0.1", now, now))
            conn.commit()
        else:
            # DDL w SQLite bywa autocommit, ale dbajmy o porządek transakcyjny:
            conn.commit()

        return True

    except Exception as e:
        # Jeżeli coś poszło nie tak, wycofujemy zmiany i raportujemy błąd.
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Błąd inicjalizacji bazy danych: {e}")
        return False

    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_app_info():
    """Pobiera informacje o aplikacji z bazy danych (ostatni rekord)"""
    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        # jawnie wybieramy potrzebne kolumny
        cur.execute("""
            SELECT version, created_at, last_updated
            FROM app_info
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cur.fetchone()

        if not row:
            return None

        return {
            'version': row['version'],
            'created_at': row['created_at'],
            'last_updated': row['last_updated'],
        }

    except Exception as e:
        st.error(f"Błąd pobierania informacji z bazy: {e}")
        return None

    finally:
        try:
            conn.close()
        except Exception:
            pass

def test_database_connection():
    """Test połączenia z bazą danych dla debugowania"""
    result = {
        'db_exists': os.path.exists(DB_PATH),
        'db_size': 0,
        'connection_ok': False,
        'tables_count': 0,
        'app_info': None
    }

    # Jeśli plik bazy istnieje → sprawdź jego rozmiar
    if result['db_exists']:
        try:
            result['db_size'] = os.path.getsize(DB_PATH)
        except Exception:
            # Jeśli nie uda się pobrać rozmiaru, po prostu zostaje 0
            result['db_size'] = 0

    conn = get_connection()
    if not conn:
        return result

    try:
        result['connection_ok'] = True
        cur = conn.cursor()

        # Liczba tabel w bazie
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        result['tables_count'] = int(cur.fetchone()[0] or 0)

        # Pobierz podstawowe info o aplikacji
        result['app_info'] = get_app_info()

    except Exception as e:
        st.error(f"Błąd testu bazy danych: {e}")

    finally:
        try:
            conn.close()
        except Exception:
            pass

    return result

# ================================
# OPERACJE CRUD DLA FX_RATES
# ================================

def insert_fx_rate(date, code='USD', rate=None, source='NBP'):
    """Dodanie kursu waluty do bazy (INSERT OR REPLACE)"""
    # Walidacje bez zmiany logiki zwracania
    if rate is None:
        st.error("Kurs waluty jest wymagany")
        return False
    try:
        rate = float(rate)
        if rate <= 0:
            st.error("Kurs waluty musi być dodatni")
            return False
    except Exception:
        st.error("Nieprawidłowa wartość kursu waluty")
        return False

    # Normalizacja daty do 'YYYY-MM-DD'
    if hasattr(date, 'strftime'):
        date_str = date.strftime('%Y-%m-%d')
    elif isinstance(date, str):
        # akceptuj już sformatowane stringi
        date_str = date
    elif isinstance(date, _date):
        date_str = date.isoformat()
    else:
        # fallback — nie zmieniamy logiki, ale sygnalizujemy błąd
        st.error("Nieprawidłowy typ daty")
        return False

    code_norm = (code or '').upper().strip()
    source_norm = (source or '').strip() or 'NBP'

    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO fx_rates (date, code, rate, source)
            VALUES (?, ?, ?, ?)
        """, (date_str, code_norm, rate, source_norm))
        conn.commit()
        return True

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Błąd dodawania kursu waluty: {e}")
        return False

    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_fx_rate(date, code='USD'):
    """Pobranie kursu waluty na określoną datę (dokładne dopasowanie date+code)"""
    # Normalizacja daty do 'YYYY-MM-DD'
    if hasattr(date, 'strftime'):
        date_str = date.strftime('%Y-%m-%d')
    elif isinstance(date, _date):
        date_str = date.isoformat()
    elif isinstance(date, str):
        date_str = date
    else:
        st.error("Nieprawidłowy typ daty")
        return None

    code_norm = (code or '').upper().strip()

    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT date, code, rate, source, created_at
            FROM fx_rates
            WHERE date = ? AND code = ?
            LIMIT 1
        """, (date_str, code_norm))
        row = cur.fetchone()

        if not row:
            return None

        # dzięki row_factory=sqlite3.Row możemy czytać po nazwach
        return {
            'date': row['date'],
            'code': row['code'],
            'rate': float(row['rate']),
            'source': row['source'],
            'created_at': row['created_at'],
        }

    except Exception as e:
        st.error(f"Błąd pobierania kursu waluty: {e}")
        return None

    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_latest_fx_rate(code='USD', before_date=None):
    """Pobranie najnowszego kursu waluty (opcjonalnie: do podanej daty włącznie)."""
    code_norm = (code or '').upper().strip()

    # Normalizacja daty (jeśli podana)
    if before_date is not None:
        if hasattr(before_date, 'strftime'):
            before_date_str = before_date.strftime('%Y-%m-%d')
        elif isinstance(before_date, _date):
            before_date_str = before_date.isoformat()
        elif isinstance(before_date, str):
            before_date_str = before_date
        else:
            st.error("Nieprawidłowy typ before_date")
            return None
    else:
        before_date_str = None

    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()

        if before_date_str:
            cur.execute("""
                SELECT date, code, rate, source, created_at
                FROM fx_rates
                WHERE code = ? AND date <= ?
                ORDER BY date DESC
                LIMIT 1
            """, (code_norm, before_date_str))
        else:
            cur.execute("""
                SELECT date, code, rate, source, created_at
                FROM fx_rates
                WHERE code = ?
                ORDER BY date DESC
                LIMIT 1
            """, (code_norm,))

        row = cur.fetchone()
        if not row:
            return None

        return {
            'date': row['date'],
            'code': row['code'],
            'rate': float(row['rate']),
            'source': row['source'],
            'created_at': row['created_at'],
        }

    except Exception as e:
        st.error(f"Błąd pobierania najnowszego kursu: {e}")
        return None

    finally:
        try:
            conn.close()
        except Exception:
            pass

def delete_fx_rate(date, code='USD'):
    """Usunięcie kursu waluty z określonej daty"""
    # Normalizacja daty do 'YYYY-MM-DD'
    if hasattr(date, 'strftime'):
        date_str = date.strftime('%Y-%m-%d')
    elif isinstance(date, _date):
        date_str = date.isoformat()
    elif isinstance(date, str):
        date_str = date
    else:
        st.error("Nieprawidłowy typ daty")
        return False

    code_norm = (code or '').upper().strip()

    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM fx_rates
            WHERE date = ? AND code = ?
        """, (date_str, code_norm))

        rows_affected = cur.rowcount
        conn.commit()

        return rows_affected > 0

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Błąd usuwania kursu waluty: {e}")
        return False

    finally:
        try:
            conn.close()
        except Exception:
            pass
            
def get_fx_rates_stats():
    """Pobranie statystyk tabeli fx_rates"""
    default = {
        'total_records': 0,
        'oldest_date': None,
        'newest_date': None,
        'currencies_count': 0,
        'latest_usd_rate': None,
        'latest_usd_date': None
    }

    conn = get_connection()
    if not conn:
        return default

    try:
        cur = conn.cursor()

        # Liczba rekordów
        cur.execute("SELECT COUNT(*) FROM fx_rates")
        total_count = int(cur.fetchone()[0] or 0)

        # Zakres dat (może zwrócić NULL gdy brak rekordów)
        cur.execute("SELECT MIN(date) AS oldest, MAX(date) AS newest FROM fx_rates")
        date_range = cur.fetchone()
        oldest = date_range['oldest'] if date_range else None
        newest = date_range['newest'] if date_range else None

        # Liczba unikalnych walut
        cur.execute("SELECT COUNT(DISTINCT code) FROM fx_rates")
        currencies_count = int(cur.fetchone()[0] or 0)

        # Najnowszy USD (korzysta z własnego połączenia)
        latest_usd = get_latest_fx_rate('USD')

        return {
            'total_records': total_count,
            'oldest_date': oldest,
            'newest_date': newest,
            'currencies_count': currencies_count,
            'latest_usd_rate': (float(latest_usd['rate']) if latest_usd else None),
            'latest_usd_date': (latest_usd['date'] if latest_usd else None),
        }

    except Exception as e:
        st.error(f"Błąd pobierania statystyk fx_rates: {e}")
        return default

    finally:
        try:
            conn.close()
        except Exception:
            pass

def test_fx_rates_operations():
    """Test operacji CRUD na tabeli fx_rates - NAPRAWIONY (ta sama logika, bezpieczniejsze wykonanie)"""
    results = {
        'fx_table_exists': False,
        'insert_test': False,
        'get_test': False,
        'latest_test': False,
        'delete_test': False,
        'stats_test': False
    }

    try:
        import structure
    except Exception as e:
        st.error(f"Błąd importu modułu 'structure': {e}")
        return results

    conn = get_connection()
    if not conn:
        return results

    try:
        # 1) Upewnij się, że tabela istnieje
        try:
            results['fx_table_exists'] = bool(structure.create_fx_rates_table(conn))
        except Exception as e:
            st.error(f"Błąd tworzenia tabeli fx_rates: {e}")
            results['fx_table_exists'] = False

        # 2) Wyczyść dane testowe (jak w oryginale)
        if results['fx_table_exists']:
            cur = conn.cursor()
            cur.execute("DELETE FROM fx_rates WHERE code = 'USD' AND source IN ('NBP', 'MANUAL')")
            conn.commit()

    except Exception as e:
        st.error(f"Błąd przygotowania testu fx_rates: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # 3) INSERT
    if results['fx_table_exists']:
        results['insert_test'] = insert_fx_rate('2025-01-15', 'USD', 4.2345, 'NBP')

    # 4) GET
    if results['insert_test']:
        rate = get_fx_rate('2025-01-15', 'USD')
        try:
            results['get_test'] = (rate is not None) and (float(rate['rate']) == 4.2345)
        except Exception:
            results['get_test'] = False

    # 5) LATEST
    if results['get_test']:
        latest = get_latest_fx_rate('USD')
        try:
            results['latest_test'] = (latest is not None) and (float(latest['rate']) == 4.2345)
        except Exception:
            results['latest_test'] = False

    # 6) STATS
    if results['latest_test']:
        stats = get_fx_rates_stats()
        results['stats_test'] = bool(stats and stats.get('total_records', 0) > 0)

    # 7) DELETE
    if results['stats_test']:
        results['delete_test'] = delete_fx_rate('2025-01-15', 'USD')

    return results

# ================================
# OPERACJE CRUD DLA CASHFLOWS
# ================================

def insert_cashflow(cashflow_type, amount_usd, date, fx_rate, description=None, ref_table=None, ref_id=None):
    """Dodanie przepływu pieniężnego do bazy (ta sama logika, bezpieczniejsze wykonanie)."""
    # 0) Szybka walidacja wejścia (bez zmiany logiki biznesowej)
    try:
        if amount_usd is None:
            st.error("Kwota nie może być pusta")
            return None
        amount_usd = float(amount_usd)
    except Exception:
        st.error("Kwota musi być liczbą")
        return None

    if amount_usd == 0:
        st.error("Kwota nie może być zerowa")
        return None

    try:
        fx_rate = float(fx_rate)
    except Exception:
        st.error("Kurs FX musi być liczbą")
        return None
    if fx_rate <= 0 or math.isinf(fx_rate) or math.isnan(fx_rate):
        st.error("Kurs FX musi być dodatni i skończony")
        return None

    # 1) Normalizacja daty
    if hasattr(date, 'strftime'):
        date_str = date.strftime('%Y-%m-%d')
    elif isinstance(date, _date):
        date_str = date.isoformat()
    elif isinstance(date, str):
        date_str = date
    else:
        st.error("Nieprawidłowy typ daty")
        return None

    # 2) Obliczenie amount_pln (wciąż 2 miejsca — ta sama logika zaokrąglenia)
    try:
        amt_pln_dec = (Decimal(str(amount_usd)) * Decimal(str(fx_rate))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        amount_pln = float(amt_pln_dec)
    except (InvalidOperation, ValueError):
        st.error("Błąd przeliczenia kwoty PLN")
        return None

    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln,
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (cashflow_type, amount_usd, date_str, fx_rate, amount_pln,
              description, ref_table, ref_id))

        cashflow_id = cur.lastrowid
        conn.commit()
        return cashflow_id

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Błąd dodawania cashflow: {e}")
        return None

    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_cashflow(cashflow_id):
    """Pobranie pojedynczego cashflow po ID"""
    # Prosta walidacja ID
    try:
        cf_id = int(cashflow_id)
        if cf_id <= 0:
            return None
    except Exception:
        return None

    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, type, amount_usd, date, fx_rate, amount_pln,
                   description, ref_table, ref_id, created_at, updated_at
            FROM cashflows
            WHERE id = ?
        """, (cf_id,))
        row = cur.fetchone()

        if not row:
            return None

        # Dzięki row_factory = sqlite3.Row możemy czytać po nazwach
        return {
            'id': row['id'],
            'type': row['type'],
            'amount_usd': (float(row['amount_usd']) if row['amount_usd'] is not None else None),
            'date': row['date'],
            'fx_rate': (float(row['fx_rate']) if row['fx_rate'] is not None else None),
            'amount_pln': (float(row['amount_pln']) if row['amount_pln'] is not None else None),
            'description': row['description'],
            'ref_table': row['ref_table'],
            'ref_id': row['ref_id'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    except Exception as e:
        st.error(f"Błąd pobierania cashflow: {e}")
        return None

    finally:
        try:
            conn.close()
        except Exception:
            pass

def delete_cashflow(cashflow_id):
    """Usunięcie cashflow"""
    # Prosta walidacja ID
    try:
        cf_id = int(cashflow_id)
        if cf_id <= 0:
            return False
    except Exception:
        return False

    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM cashflows WHERE id = ?", (cf_id,))
        rows_affected = cur.rowcount
        conn.commit()
        return rows_affected > 0

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Błąd usuwania cashflow: {e}")
        return False

    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_cashflows_stats():
    """Statystyki tabeli cashflows (ta sama logika, bezpieczniejsze wykonanie)."""
    default = {
        'total_records': 0,
        'oldest_date': None,
        'newest_date': None,
        'total_usd': 0.0,
        'total_pln': 0.0
    }

    conn = get_connection()
    if not conn:
        return default

    try:
        cur = conn.cursor()

        # Liczba rekordów
        cur.execute("SELECT COUNT(*) FROM cashflows")
        total_count_row = cur.fetchone()
        total_count = int(total_count_row[0] or 0) if total_count_row else 0

        # Zakres dat
        cur.execute("SELECT MIN(date), MAX(date) FROM cashflows")
        date_range = cur.fetchone()
        oldest_date = date_range[0] if date_range else None
        newest_date = date_range[1] if date_range else None

        # Sumy USD/PLN
        cur.execute("SELECT SUM(amount_usd), SUM(amount_pln) FROM cashflows")
        totals = cur.fetchone()
        total_usd = float(totals[0]) if totals and totals[0] is not None else 0.0
        total_pln = float(totals[1]) if totals and totals[1] is not None else 0.0

        return {
            'total_records': total_count,
            'oldest_date': oldest_date,
            'newest_date': newest_date,
            'total_usd': total_usd,
            'total_pln': total_pln
        }

    except Exception as e:
        st.error(f"Błąd statystyk cashflows: {e}")
        return default

    finally:
        try:
            conn.close()
        except Exception:
            pass

def update_cashflow(cashflow_id, **kwargs):
    """Aktualizacja cashflow (ta sama logika; bezpieczniej i w jednej transakcji)."""
    if not kwargs:
        return False

    # Dozwolone pola do UPDATE
    allowed = {'type', 'amount_usd', 'date', 'fx_rate', 'description', 'ref_table', 'ref_id'}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed:
            # Normalizacja daty, jeśli potrzeba
            if k == 'date':
                if hasattr(v, 'strftime'):
                    v = v.strftime('%Y-%m-%d')
                elif isinstance(v, _date):
                    v = v.isoformat()
                elif not isinstance(v, str):
                    st.error("Pole 'date' musi być datą albo stringiem YYYY-MM-DD")
                    return False
            updates[k] = v

    if not updates:
        return False

    # Walidacja ID
    try:
        cf_id = int(cashflow_id)
        if cf_id <= 0:
            return False
    except Exception:
        return False

    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()

        # 1) Pobierz bieżące wartości amount_usd i fx_rate (do ewentualnego przeliczenia amount_pln)
        cur.execute("SELECT amount_usd, fx_rate FROM cashflows WHERE id = ?", (cf_id,))
        row = cur.fetchone()
        if not row:
            return False

        current_amount_usd = row['amount_usd']
        current_fx_rate = row['fx_rate']

        # 2) Zbuduj SET dla dozwolonych pól
        set_parts = []
        params = []
        for field, value in updates.items():
            set_parts.append(f"{field} = ?")
            params.append(value)

        # 3) Zawsze aktualizujemy znacznik czasu
        set_parts.append("updated_at = CURRENT_TIMESTAMP")

        # 4) Wykonaj główne UPDATE
        sql = f"UPDATE cashflows SET {', '.join(set_parts)} WHERE id = ?"
        params.append(cf_id)
        cur.execute(sql, params)

        # 5) Jeśli zmieniło się 'amount_usd' albo 'fx_rate' → przelicz 'amount_pln'
        if ('amount_usd' in updates) or ('fx_rate' in updates):
            # Nowe wartości to: z 'updates' jeśli są, w przeciwnym razie dotychczasowe
            try:
                new_amount_usd = updates.get('amount_usd', current_amount_usd)
                new_fx_rate = updates.get('fx_rate', current_fx_rate)

                # rzutowania na Decimal i zaokrąglenie do 2 miejsc
                amt_pln = (Decimal(str(new_amount_usd)) * Decimal(str(new_fx_rate))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                cur.execute("UPDATE cashflows SET amount_pln = ? WHERE id = ?", (float(amt_pln), cf_id))
            except (InvalidOperation, TypeError, ValueError):
                # jeśli nowe wartości są nieprawidłowe, zwróć błąd i cofnij
                raise Exception("Nieprawidłowe wartości amount_usd lub fx_rate przy przeliczeniu amount_pln")

        conn.commit()
        return True

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Błąd aktualizacji cashflow: {e}")
        return False

    finally:
        try:
            conn.close()
        except Exception:
            pass

def test_cashflows_operations():
    """Test operacji CRUD na tabeli cashflows (ta sama logika, bezpieczniejsze wykonanie)."""
    results = {
        'table_exists': False,
        'insert_test': False,
        'get_test': False,
        'update_test': False,
        'delete_test': False,
        'stats_test': False
    }

    # 1) Upewnij się, że mamy strukturę tabeli
    try:
        import structure
    except Exception as e:
        st.error(f"Błąd importu modułu 'structure': {e}")
        return results

    conn = get_connection()
    if conn:
        try:
            results['table_exists'] = bool(structure.create_cashflows_table(conn))
        except Exception as e:
            st.error(f"Błąd tworzenia tabeli cashflows: {e}")
            results['table_exists'] = False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    cashflow_id = None

    # 2) INSERT
    if results['table_exists']:
        cashflow_id = insert_cashflow('deposit', 1000.0, '2025-01-15', 4.2345, 'Test deposit')
        results['insert_test'] = cashflow_id is not None

    # 3) GET
    if results['insert_test'] and cashflow_id is not None:
        cf = get_cashflow(cashflow_id)
        try:
            results['get_test'] = (cf is not None) and (float(cf['amount_usd']) == 1000.0)
        except Exception:
            results['get_test'] = False

    # 4) UPDATE
    if results['get_test'] and cashflow_id is not None:
        results['update_test'] = update_cashflow(cashflow_id, description='Updated test deposit')

    # 5) STATS
    if results['update_test']:
        stats = get_cashflows_stats()
        results['stats_test'] = bool(stats and stats.get('total_records', 0) > 0)

    # 6) DELETE
    if results['stats_test'] and cashflow_id is not None:
        results['delete_test'] = delete_cashflow(cashflow_id)

    return results

# ================================
# OPERACJE CRUD DLA LOTS
# ================================

def get_available_quantity(ticker):
    """Sprawdzenie dostępnej ilości akcji dla tickera (suma quantity_open)."""
    # Prosta walidacja / normalizacja
    if ticker is None:
        return 0
    ticker_norm = str(ticker).upper().strip()
    if not ticker_norm:
        return 0

    conn = get_connection()
    if not conn:
        return 0

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COALESCE(SUM(quantity_open), 0) AS qty
            FROM lots
            WHERE ticker = ?
        """, (ticker_norm,))
        row = cur.fetchone()
        total = int(row[0] or 0) if row else 0
        return total

    except Exception as e:
        st.error(f"Błąd sprawdzania dostępności {ticker_norm}: {e}")
        return 0

    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_lot(lot_id):
    """Pobranie pojedynczego LOT-a po ID"""
    # Walidacja ID
    try:
        lot_id_int = int(lot_id)
        if lot_id_int <= 0:
            return None
    except Exception:
        return None

    conn = get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, ticker, quantity_total, quantity_open, buy_price_usd,
                   broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln,
                   created_at, updated_at
            FROM lots
            WHERE id = ?
        """, (lot_id_int,))
        row = cur.fetchone()
        if not row:
            return None

        return {
            'id': row['id'],
            'ticker': row['ticker'],
            'quantity_total': row['quantity_total'],
            'quantity_open': row['quantity_open'],
            'buy_price_usd': (float(row['buy_price_usd']) if row['buy_price_usd'] is not None else None),
            'broker_fee_usd': (float(row['broker_fee_usd']) if row['broker_fee_usd'] is not None else None),
            'reg_fee_usd': (float(row['reg_fee_usd']) if row['reg_fee_usd'] is not None else None),
            'buy_date': row['buy_date'],
            'fx_rate': (float(row['fx_rate']) if row['fx_rate'] is not None else None),
            'cost_pln': (float(row['cost_pln']) if row['cost_pln'] is not None else None),
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    except Exception as e:
        st.error(f"Błąd pobierania LOT-a: {e}")
        return None

    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_lots_by_ticker(ticker, only_open=False, sell_date=None):
    """
    Pobierz LOT-y dla tickera z walidacją temporalną (buy_date <= sell_date),
    opcjonalnym filtrem only_open i sortowaniem FIFO (buy_date ASC, id ASC).
    """
    if not ticker:
        return []
    ticker_norm = str(ticker).upper().strip()
    if not ticker_norm:
        return []

    # Normalizacja sell_date → 'YYYY-MM-DD' (jeśli podany)
    sell_date_str = None
    if sell_date is not None:
        if hasattr(sell_date, 'strftime'):
            sell_date_str = sell_date.strftime('%Y-%m-%d')
        elif isinstance(sell_date, _date):
            sell_date_str = sell_date.isoformat()
        else:
            sell_date_str = str(sell_date)

    conn = get_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()

        query = """
            SELECT id, ticker, quantity_total, quantity_open, buy_price_usd,
                   broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln,
                   created_at, updated_at
            FROM lots
            WHERE ticker = ?
        """
        params = [ticker_norm]

        if sell_date_str is not None:
            query += " AND buy_date <= ?"
            params.append(sell_date_str)

        if only_open:
            query += " AND quantity_open > 0"

        query += " ORDER BY buy_date ASC, id ASC"

        cur.execute(query, params)
        rows = cur.fetchall()

        lots = []
        for row in rows:
            lots.append({
                'id': row['id'],
                'ticker': row['ticker'],
                'quantity_total': row['quantity_total'],
                'quantity_open': row['quantity_open'],
                'buy_price_usd': (float(row['buy_price_usd']) if row['buy_price_usd'] is not None else None),
                'broker_fee_usd': (float(row['broker_fee_usd']) if row['broker_fee_usd'] is not None else 0.0),
                'reg_fee_usd': (float(row['reg_fee_usd']) if row['reg_fee_usd'] is not None else 0.0),
                'buy_date': row['buy_date'],
                'fx_rate': (float(row['fx_rate']) if row['fx_rate'] is not None else None),
                'cost_pln': (float(row['cost_pln']) if row['cost_pln'] is not None else None),
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            })

        return lots

    except Exception as e:
        st.error(f"Błąd pobierania LOT-ów z walidacją temporalną: {e}")
        return []

    finally:
        try:
            conn.close()
        except Exception:
            pass    

def validate_sell_date_against_lots(ticker, sell_date, quantity_needed):
    """
    Walidacja temporalna: czy można sprzedać z danym dniem (buy_date <= sell_date)
    Zwraca:
      {
        'valid': bool,
        'available_quantity': int,
        'violating_lots': List[Dict],  # LOT-y kupione po sell_date
        'message': str
      }
    """
    # --- Walidacje wejścia (bez zmiany logiki biznesowej) ---
    if not ticker:
        return {'valid': False, 'available_quantity': 0, 'violating_lots': [], 'message': 'Brak tickera'}

    try:
        qty_needed = int(quantity_needed)
    except Exception:
        return {'valid': False, 'available_quantity': 0, 'violating_lots': [], 'message': 'quantity_needed musi być liczbą całkowitą'}
    if qty_needed < 0:
        return {'valid': False, 'available_quantity': 0, 'violating_lots': [], 'message': 'quantity_needed nie może być ujemne'}

    ticker_upper = str(ticker).upper().strip()

    # Normalizacja daty do 'YYYY-MM-DD'
    if hasattr(sell_date, 'strftime'):
        sell_date_str = sell_date.strftime('%Y-%m-%d')
    elif isinstance(sell_date, _date):
        sell_date_str = sell_date.isoformat()
    elif isinstance(sell_date, str):
        # Spróbuj doprowadzić string do formatu ISO, jeśli to możliwe
        try:
            sell_date_str = _datetime.strptime(sell_date, '%Y-%m-%d').date().isoformat()
        except Exception:
            # jeśli format niestandardowy, bierz jak jest (logika jak w Twojej wersji)
            sell_date_str = sell_date
    else:
        return {'valid': False, 'available_quantity': 0, 'violating_lots': [], 'message': 'Nieprawidłowy typ sell_date'}

    conn = get_connection()
    if not conn:
        return {'valid': False, 'available_quantity': 0, 'violating_lots': [], 'message': 'Brak połączenia z bazą'}

    try:
        cur = conn.cursor()
        # Bierzemy tylko LOT-y z dodatnim quantity_open (tak jak w Twojej wersji)
        cur.execute("""
            SELECT id, buy_date, quantity_open, quantity_total
            FROM lots
            WHERE ticker = ? AND quantity_open > 0
            ORDER BY buy_date ASC, id ASC
        """, (ticker_upper,))
        rows = cur.fetchall()

        if not rows:
            return {
                'valid': False,
                'available_quantity': 0,
                'violating_lots': [],
                'message': f'Brak LOT-ów dla {ticker_upper}'
            }

        valid_lots = []
        violating_lots = []

        # Podział względem daty sprzedaży (stringowe porównanie działa poprawnie dla ISO 'YYYY-MM-DD')
        for row in rows:
            buy_date = row['buy_date']
            lot_dict = {
                'id': row['id'],
                'buy_date': buy_date,
                'quantity_open': int(row['quantity_open'] or 0),
                'quantity_total': int(row['quantity_total'] or 0),
            }
            if buy_date <= sell_date_str:
                valid_lots.append(lot_dict)
            else:
                violating_lots.append(lot_dict)

        available_quantity = sum(l['quantity_open'] for l in valid_lots)

        if qty_needed <= available_quantity:
            return {
                'valid': True,
                'available_quantity': available_quantity,
                'violating_lots': violating_lots,
                'message': f'OK: {available_quantity} dostępne przed {sell_date_str}'
            }
        else:
            return {
                'valid': False,
                'available_quantity': available_quantity,
                'violating_lots': violating_lots,
                'message': f'BŁĄD: potrzeba {qty_needed}, dostępne {available_quantity} przed {sell_date_str}'
            }

    except Exception as e:
        return {
            'valid': False,
            'available_quantity': 0,
            'violating_lots': [],
            'message': f'Błąd walidacji: {e}'
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass

def update_lot_quantity(lot_id, new_quantity_open):
    """Aktualizacja quantity_open LOT-a (bez zmiany logiki)."""
    # Walidacje wejścia
    try:
        lot_id_int = int(lot_id)
        if lot_id_int <= 0:
            return False
    except Exception:
        return False

    try:
        new_qty = int(new_quantity_open)
    except Exception:
        st.error(f"Nieprawidłowa ilość: {new_quantity_open}")
        return False
    if new_qty < 0:
        st.error(f"Nieprawidłowa ilość: {new_quantity_open}")
        return False

    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()

        # Pobierz quantity_total dla walidacji (zamiast wołać get_lot -> jedna transakcja)
        cur.execute("SELECT quantity_total FROM lots WHERE id = ?", (lot_id_int,))
        row = cur.fetchone()
        if not row:
            return False

        quantity_total = int(row['quantity_total'] or 0)
        if new_qty > quantity_total:
            st.error(f"Nieprawidłowa ilość: {new_quantity_open}")
            return False

        # Aktualizacja
        cur.execute("""
            UPDATE lots
            SET quantity_open = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_qty, lot_id_int))

        conn.commit()
        return True

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Błąd aktualizacji LOT-a: {e}")
        return False

    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_lots_stats():
    """Statystyki tabeli lots (ta sama logika, bezpieczniejsze wykonanie)."""
    default = {
        'total_lots': 0,
        'total_shares': 0,
        'open_shares': 0,
        'total_cost_pln': 0.0
    }

    conn = get_connection()
    if not conn:
        return default

    try:
        cur = conn.cursor()

        # Liczba lotów
        cur.execute("SELECT COUNT(*) FROM lots")
        row = cur.fetchone()
        total_lots = int(row[0] or 0) if row else 0

        # Sumy (użyj COALESCE, żeby uniknąć None)
        cur.execute("""
            SELECT
                COALESCE(SUM(quantity_total), 0) AS qty_total,
                COALESCE(SUM(quantity_open), 0)  AS qty_open,
                COALESCE(SUM(cost_pln), 0.0)     AS cost_pln
            FROM lots
        """)
        totals = cur.fetchone()

        return {
            'total_lots': total_lots,
            'total_shares': int(totals['qty_total'] if totals else 0),
            'open_shares': int(totals['qty_open'] if totals else 0),
            'total_cost_pln': float(totals['cost_pln'] if totals else 0.0),
        }

    except Exception as e:
        st.error(f"Błąd statystyk lots: {e}")
        return default

    finally:
        try:
            conn.close()
        except Exception:
            pass


def test_lots_operations():
    """Test operacji CRUD na tabeli lots (ta sama logika, bezpieczniejsze wykonanie)."""
    results = {
        'table_exists': False,
        'insert_test': False,
        'get_test': False,
        'quantity_test': False,
        'fifo_test': False,
        'update_test': False,
        'stats_test': False
    }

    # import struktury
    try:
        import structure
    except Exception as e:
        st.error(f"Błąd importu modułu 'structure': {e}")
        return results

    lot_id = None

    # 1) Utwórz tabelę i wyczyść dane testowe AAPL
    conn = get_connection()
    if conn:
        try:
            results['table_exists'] = bool(structure.create_lots_table(conn))
            cur = conn.cursor()
            cur.execute("DELETE FROM lots WHERE ticker = ?", ('AAPL',))
            conn.commit()
        except Exception as e:
            st.error(f"Błąd przygotowania testu lots: {e}")
            results['table_exists'] = False
            try: conn.rollback()
            except Exception: pass
        finally:
            try: conn.close()
            except Exception: pass

    # 2) INSERT pierwszego lota
    if results['table_exists']:
        conn = get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO lots (
                        ticker, quantity_total, quantity_open, buy_price_usd,
                        broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ('AAPL', 100, 100, 150.50, 1.0, 0.5, '2025-01-15', 4.2345, 640.0))
                lot_id = cur.lastrowid
                conn.commit()
                results['insert_test'] = lot_id is not None
            except Exception as e:
                st.error(f"Błąd INSERT (lots #1): {e}")
                results['insert_test'] = False
                try: conn.rollback()
                except Exception: pass
            finally:
                try: conn.close()
                except Exception: pass

    # 3) GET
    if results['insert_test'] and lot_id is not None:
        lot = get_lot(lot_id)
        results['get_test'] = (lot is not None and lot.get('ticker') == 'AAPL')

    # 4) SUMA dostępnych
    if results['get_test']:
        available = get_available_quantity('AAPL')
        results['quantity_test'] = (available == 100)

    # 5) FIFO – dodaj drugi lot i sprawdź kolejność
    if results['quantity_test']:
        conn = get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO lots (
                        ticker, quantity_total, quantity_open, buy_price_usd,
                        broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ('AAPL', 50, 50, 155.00, 1.0, 0.5, '2025-01-16', 4.2500, 330.0))
                conn.commit()
            except Exception as e:
                st.error(f"Błąd INSERT (lots #2): {e}")
                try: conn.rollback()
                except Exception: pass
            finally:
                try: conn.close()
                except Exception: pass

        lots = get_lots_by_ticker('AAPL', only_open=True)
        results['fifo_test'] = (len(lots) >= 2 and lots[0]['buy_date'] <= lots[1]['buy_date'])

    # 6) UPDATE quantity_open na 75 dla pierwszego lota
    if results['fifo_test'] and lot_id is not None:
        results['update_test'] = update_lot_quantity(lot_id, 75)

    # 7) STATS
    if results['update_test']:
        stats = get_lots_stats()
        results['stats_test'] = bool(stats and stats.get('total_lots', 0) >= 2)

    return results


# ================================
# OPERACJE STOCK_TRADES (uproszczone)
# ================================

def test_stock_trades_operations():
    """Test operacji sprzedaży FIFO (uczciwy: bez udawania sprzedaży, bo brak implementacji sell)."""
    results = {
        'tables_exist': False,
        'setup_lots': False,
        'sell_test': False,       # zostaje False – brak realnej funkcji sprzedaży
        'fifo_test': False,
        'get_trade_test': False   # zostaje False – brak zapisu trade do tabeli
    }

    # 1) Utwórz wymagane tabele i wyczyść dane testowe dla MSFT
    try:
        import structure
    except Exception as e:
        st.error(f"Błąd importu modułu 'structure': {e}")
        return results

    conn = get_connection()
    if not conn:
        return results

    try:
        cur = conn.cursor()
        results['tables_exist'] = bool(
            structure.create_stock_trades_table(conn) and
            structure.create_stock_trade_splits_table(conn)
        )

        # Wyczyść poprzednie dane testowe
        cur.execute("DELETE FROM stock_trades WHERE ticker = ?", ('MSFT',))
        cur.execute("DELETE FROM lots WHERE ticker = ?", ('MSFT',))
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Błąd przygotowania testu stock_trades: {e}")
        results['tables_exist'] = False
    finally:
        try: conn.close()
        except Exception: pass

    if not results['tables_exist']:
        return results

    # 2) Dodaj dwa LOT-y dla MSFT do testu FIFO
    lot1_id = None
    try:
        conn = get_connection()
        if not conn:
            return results
        cur = conn.cursor()

        # LOT #1 – starszy
        cur.execute("""
            INSERT INTO lots (
                ticker, quantity_total, quantity_open, buy_price_usd,
                broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('MSFT', 100, 100, 300.00, 1.0, 0.5, '2025-01-10', 4.00, 120000.0))
        lot1_id = cur.lastrowid

        # LOT #2 – młodszy
        cur.execute("""
            INSERT INTO lots (
                ticker, quantity_total, quantity_open, buy_price_usd,
                broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('MSFT', 50, 50, 310.00, 1.0, 0.5, '2025-01-12', 4.05, 62000.0))

        conn.commit()
        results['setup_lots'] = lot1_id is not None
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Błąd wstawiania LOT-ów MSFT: {e}")
        results['setup_lots'] = False
    finally:
        try: conn.close()
        except Exception: pass

    # 3) Weryfikacja FIFO – kolejność LOT-ów po buy_date,id
    if results['setup_lots']:
        lots = get_lots_by_ticker('MSFT', only_open=True)
        results['fifo_test'] = (len(lots) >= 2 and lots[0]['buy_date'] <= lots[1]['buy_date'])

    # 4) Brak implementacji realnej sprzedaży i zapisu do stock_trades:
    #    - sell_test pozostaje False
    #    - get_trade_test pozostaje False

    return results

# ================================
# TEST OSTATNICH TABEL
# ================================

def test_final_tables_operations():
    """Test operacji na ostatnich tabelach (ta sama logika, bezpieczniejsze wykonanie)."""
    results = {
        'options_cc_table': False,
        'dividends_table': False,
        'market_prices_table': False,
        'options_insert': False,
        'dividends_insert': False,
        'market_prices_insert': False,
        'schema_complete': False
    }

    # Import struktury
    try:
        import structure
    except Exception as e:
        st.error(f"Błąd importu modułu 'structure': {e}")
        return results

    conn = get_connection()
    if not conn:
        return results

    try:
        cur = conn.cursor()

        # Utwórz wymagane tabele
        results['options_cc_table'] = bool(structure.create_options_cc_table(conn))
        results['dividends_table'] = bool(structure.create_dividends_table(conn))
        results['market_prices_table'] = bool(structure.create_market_prices_table(conn))

        # Wyczyść ewentualne stare dane testowe AAPL
        cur.execute("DELETE FROM options_cc   WHERE ticker = ?", ('AAPL',))
        cur.execute("DELETE FROM dividends    WHERE ticker = ?", ('AAPL',))
        cur.execute("DELETE FROM market_prices WHERE ticker = ?", ('AAPL',))
        conn.commit()

        # INSERT: options_cc
        if results['options_cc_table']:
            try:
                cur.execute("""
                    INSERT INTO options_cc (
                        ticker, contracts, strike_usd, premium_sell_usd,
                        open_date, expiry_date, fx_open, premium_sell_pln
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, ('AAPL', 1, 180.0, 2.50, '2025-01-15', '2025-02-21', 4.2500, 10.63))
                results['options_insert'] = True
            except Exception as e:
                st.error(f"Błąd wstawiania options_cc: {e}")

        # INSERT: dividends
        if results['dividends_table']:
            try:
                cur.execute("""
                    INSERT INTO dividends (
                        ticker, gross_usd, date_paid, fx_rate,
                        gross_pln, wht_15_pln, tax_4_pln, net_pln
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, ('AAPL', 0.25, '2025-01-15', 4.2500, 1.06, 0.16, 0.04, 0.86))
                results['dividends_insert'] = True
            except Exception as e:
                st.error(f"Błąd wstawiania dividends: {e}")

        # INSERT: market_prices
        if results['market_prices_table']:
            try:
                cur.execute("""
                    INSERT INTO market_prices (ticker, date, price_usd)
                    VALUES (?, ?, ?)
                """, ('AAPL', '2025-01-15', 185.50))
                results['market_prices_insert'] = True
            except Exception as e:
                st.error(f"Błąd wstawiania market_prices: {e}")

        # Zatwierdź inserty
        conn.commit()

        # Sprawdzenie kompletności schematu (jak w Twojej wersji)
        if results['options_cc_table'] and results['dividends_table'] and results['market_prices_table']:
            try:
                schema_info = structure.get_database_schema_info(conn)
                expected_tables = [
                    'fx_rates', 'cashflows', 'lots', 'stock_trades',
                    'stock_trade_splits', 'options_cc', 'dividends', 'market_prices'
                ]
                results['schema_complete'] = all(table in schema_info for table in expected_tables)
            except Exception as e:
                st.error(f"Błąd odczytu schematu bazy: {e}")
                results['schema_complete'] = False

        return results

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Błąd testów finalnych tabel: {e}")
        return results

    finally:
        try:
            conn.close()
        except Exception:
            pass


# ================================
# PODSUMOWANIE BAZY DANYCH
# ================================

def get_database_summary():
    """Pobranie podsumowania całej bazy danych (ta sama logika, bezpieczniej)."""
    default = {
        'total_tables': 0,
        'total_records': 0,
        'tables': {}
    }

    try:
        import structure
    except Exception as e:
        st.error(f"Błąd importu modułu 'structure': {e}")
        return default

    conn = get_connection()
    if not conn:
        return default

    try:
        schema_info = structure.get_database_schema_info(conn) or {}
    except Exception as e:
        st.error(f"Błąd podsumowania bazy: {e}")
        return default
    finally:
        try:
            conn.close()
        except Exception:
            pass

    try:
        total_tables = len(schema_info)
        total_records = sum(int(info.get('records', 0) or 0) for info in schema_info.values())
    except Exception:
        total_tables = 0
        total_records = 0

    return {
        'total_tables': total_tables,
        'total_records': total_records,
        'tables': schema_info
    }


# DODAJ NA KOŃCU db.py - PUNKT 52: REZERWACJE FIFO

# ================================
# OPERACJE REZERWACJI AKCJI (CC)
# ================================

# ZAMIEŃ CAŁĄ funkcję check_cc_coverage_with_chronology w db.py NA TĘ WERSJĘ:



def check_cc_coverage_with_chronology(ticker, contracts, cc_sell_date):
    """
    Sprawdza pokrycie CC na konkretną datę historyczną (AS-OF):
      - akcje posiadane do dnia cc (buy_date <= cc_date)
      - sprzedaże PRZED dniem cc (sell_date < cc_date)
      - rezerwacje z innych CC otwartych na ten dzień (open_date <= cc_date < close_date lub close_date IS NULL)
      - FIFO preview z realnych mapowań (cc_lot_mappings), bez sztucznego dzielenia.
    """
    # --- lokalne importy dla aliasów daty/czasu, bez zmiany sygnatury:
    from datetime import date as _date, datetime as _dt
    import sqlite3

    shares_needed = int(contracts) * 100
    try:
        # Normalizacja wejść
        ticker_upper = str(ticker).upper().strip()
        if hasattr(cc_sell_date, 'strftime'):
            cc_date_str = cc_sell_date.strftime('%Y-%m-%d')
        elif isinstance(cc_sell_date, _date):
            cc_date_str = cc_sell_date.isoformat()
        elif isinstance(cc_sell_date, str):
            # spróbuj wymusić ISO, jeśli to yyyy-mm-dd to ok
            try:
                cc_date_str = _dt.strptime(cc_sell_date, '%Y-%m-%d').date().isoformat()
            except Exception:
                cc_date_str = cc_sell_date
        else:
            return {
                'can_cover': False,
                'message': 'Nieprawidłowy typ cc_sell_date',
                'shares_needed': shares_needed,
                'shares_available': 0
            }

        conn = get_connection()
        if not conn:
            return {
                'can_cover': False,
                'message': 'Brak połączenia z bazą',
                'shares_needed': shares_needed,
                'shares_available': 0
            }

        # ✳️ zapewnij dostęp po kluczach: row['kolumna']
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass

        cur = conn.cursor()

        # 1) Akcje posiadane na datę CC (buy_date <= cc_date)
        cur.execute("""
            SELECT COALESCE(SUM(quantity_total), 0) AS owned_on_cc_date
            FROM lots
            WHERE ticker = ? AND buy_date <= ?
        """, (ticker_upper, cc_date_str))
        owned_on_cc_date = int((cur.fetchone()[0] if cur.fetchone is not None else 0) or 0)

        if owned_on_cc_date == 0:
            try: conn.close()
            except Exception: pass
            return {
                'can_cover': False,
                'message': f'Brak akcji {ticker_upper} posiadanych na {cc_date_str}',
                'shares_needed': shares_needed,
                'shares_available': 0
            }

        # 2) Sprzedane przed datą CC (sell_date < cc_date), z rozbiciem po LOT-ach
        cur.execute("""
            SELECT sts.lot_id, COALESCE(SUM(sts.qty_from_lot), 0) AS qty_sold
            FROM stock_trades st
            JOIN stock_trade_splits sts ON st.id = sts.trade_id
            JOIN lots l ON l.id = sts.lot_id
            WHERE l.ticker = ? AND st.sell_date < ?
            GROUP BY sts.lot_id
        """, (ticker_upper, cc_date_str))
        sold_rows = cur.fetchall() or []
        sold_map = {row['lot_id']: int(row['qty_sold'] or 0) for row in sold_rows}

        # 3) Rezerwacje CC otwartych AS-OF cc_date, z rozbiciem po LOT-ach
        #    (open_date <= cc_date AND (close_date IS NULL OR close_date > cc_date))
        reserved_total = 0
        reserved_map = {}

        # najpierw nowa tabela mapowań
        try:
            cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'")
            has_mappings = cur.fetchone() is not None
        except Exception:
            has_mappings = False

        if has_mappings:
            cur.execute("""
                SELECT m.lot_id, COALESCE(SUM(m.shares_reserved), 0) AS qty_reserved
                FROM cc_lot_mappings m
                JOIN options_cc cc ON cc.id = m.cc_id
                JOIN lots l ON l.id = m.lot_id
                WHERE cc.ticker = ?
                  AND cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
                  AND l.buy_date <= ?
                GROUP BY m.lot_id
            """, (ticker_upper, cc_date_str, cc_date_str, cc_date_str))
            rows = cur.fetchall() or []
            # zakładamy, że kursor zwraca tuple (lot_id, qty) albo Row; oba przypadki wspieramy
            for r in rows:
                lot_id = r['lot_id'] if hasattr(r, 'keys') else r[0]
                qty    = r['qty_reserved'] if hasattr(r, 'keys') else r[1]
                reserved_map[int(lot_id)] = int(qty or 0)
            reserved_total = sum(reserved_map.values())

        # fallback do starej tabeli jeśli brak danych
        if reserved_total == 0:
            try:
                cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='options_cc_reservations'")
                has_old = cur.fetchone() is not None
            except Exception:
                has_old = False

            if has_old:
                cur.execute("""
                    SELECT r.lot_id, COALESCE(SUM(r.qty_reserved), 0) AS qty_reserved
                    FROM options_cc_reservations r
                    JOIN options_cc cc ON cc.id = r.cc_id
                    JOIN lots l ON l.id = r.lot_id
                    WHERE cc.ticker = ?
                      AND cc.open_date <= ?
                      AND (cc.close_date IS NULL OR cc.close_date > ?)
                      AND l.buy_date <= ?
                    GROUP BY r.lot_id
                """, (ticker_upper, cc_date_str, cc_date_str, cc_date_str))
                rows = cur.fetchall() or []
                reserved_map = {}
                for r in rows:
                    lot_id = r['lot_id'] if hasattr(r, 'keys') else r[0]
                    qty    = r['qty_reserved'] if hasattr(r, 'keys') else r[1]
                    reserved_map[int(lot_id)] = int(qty or 0)
                reserved_total = sum(reserved_map.values())


        # 4) Wyliczenie dostępności AS-OF: owned - sold_before - reserved_asof
        sold_total = sum(sold_map.values()) if sold_map else 0
        available_on_cc_date = owned_on_cc_date - sold_total - reserved_total
        if available_on_cc_date < 0:
            available_on_cc_date = 0  # bezpieczeństwo, nie schodzimy poniżej zera

        can_cover = available_on_cc_date >= shares_needed

        # 5) FIFO preview oparte na realnych mapowaniach
        fifo_preview = []
        if can_cover:
            cur.execute("""
                SELECT l.id, l.quantity_total, l.buy_date, l.buy_price_usd, l.fx_rate, l.cost_pln
                FROM lots l
                WHERE l.ticker = ? AND l.buy_date <= ?
                ORDER BY l.buy_date ASC, l.id ASC
            """, (ticker_upper, cc_date_str))
            lots_data = cur.fetchall() or []

            remaining_needed = shares_needed
            for row in lots_data:
                if remaining_needed <= 0:
                    break
                lot_id = row['id']
                qty_total = int(row['quantity_total'] or 0)
                qty_sold  = int(sold_map.get(lot_id, 0))
                qty_res   = int(reserved_map.get(lot_id, 0))
                qty_available = qty_total - qty_sold - qty_res
                if qty_available <= 0:
                    continue

                take = min(remaining_needed, qty_available)
                fifo_preview.append({
                    'lot_id': lot_id,
                    'buy_date': str(row['buy_date']),
                    'buy_price_usd': float(row['buy_price_usd']) if row['buy_price_usd'] is not None else None,
                    'fx_rate': float(row['fx_rate']) if row['fx_rate'] is not None else None,
                    'cost_pln': float(row['cost_pln']) if row['cost_pln'] is not None else None,
                    'qty_total': qty_total,
                    'qty_available_on_date': qty_available,
                    'qty_to_reserve': take,
                    'qty_remaining_after': qty_available - take
                })
                remaining_needed -= take

        try:
            conn.close()
        except Exception:
            pass

        debug_info = {
            'cc_date': cc_date_str,
            'owned_on_date': owned_on_cc_date,
            'sold_before_total': sold_total,
            'reserved_asof_total': reserved_total,
            'available_calculated': available_on_cc_date
        }

        return {
            'can_cover': can_cover,
            'shares_needed': shares_needed,
            'shares_available': available_on_cc_date,
            'owned_on_date': owned_on_cc_date,
            'sold_before': sold_total,
            'cc_reserved_before': reserved_total,
            'fifo_preview': fifo_preview,
            'debug_info': debug_info,
            'message': (
                'OK'
                if can_cover else
                f'Brakuje {shares_needed - available_on_cc_date} akcji na {cc_date_str} '
                f'(miało {owned_on_cc_date}, sprzedano {sold_total}, zarezerwowano {reserved_total})'
            )
        }

    except Exception as e:
        print(f"❌ Błąd chronologii CC: {e}")
        import traceback; traceback.print_exc()
        return {
            'can_cover': False,
            'message': f'Błąd sprawdzania chronologii: {e}',
            'shares_needed': shares_needed,
            'shares_available': 0
        }


def reserve_shares_for_cc(ticker, contracts, cc_id):
    """
    Rezerwuje akcje FIFO dla otwartego CC na podstawie check_cc_coverage_with_chronology.
    - Datę AS-OF bierzemy z options_cc.open_date dla cc_id.
    - Zapis rezerwacji: cc_lot_mappings (autoratywna) + mirror do options_cc_reservations.
    - Nie zmieniamy quantity_open w lots (to osobny krok, jeśli go używasz).
    """
    import sqlite3
    from datetime import datetime as _dt

    shares_needed = int(contracts) * 100

    def _st_safe(call, *args, **kwargs):
        # Bezpieczne logowanie do Streamlit, jeśli jest importowany jako 'st'
        try:
            if 'st' in globals():
                return getattr(globals()['st'], call)(*args, **kwargs)
        except Exception:
            pass

    try:
        # 0) Połączenie + row_factory dla dostępu po kluczach
        conn = get_connection()
        if not conn:
            _st_safe('error', "❌ Brak połączenia z bazą")
            return False
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # 1) Pobierz open_date dla CC (AS-OF)
        cur.execute("SELECT id, ticker, open_date FROM options_cc WHERE id = ?", (cc_id,))
        cc_row = cur.fetchone()
        if not cc_row:
            _st_safe('error', f"❌ Nie znaleziono CC #{cc_id}")
            conn.close()
            return False

        cc_ticker = str(cc_row['ticker']).upper().strip()
        if str(ticker).upper().strip() != cc_ticker:
            # Ostrzegamy, ale pozwalamy działać — może być wywołanie z innym casingiem
            _st_safe('warning', f"⚠️ Parametr ticker='{ticker}' ≠ ticker z CC='{cc_ticker}'. Używam ticker z CC.")

        cc_open_date = cc_row['open_date']  # w SQLite jako tekst 'YYYY-MM-DD'
        asof_date = cc_open_date

        # 2) Sprawdź pokrycie na open_date
        coverage = check_cc_coverage_with_chronology(cc_ticker, contracts, asof_date)

        # Debug (tylko jeśli st jest)
        _st_safe('markdown', "### 🔍 DEBUG: Wynik check_cc_coverage_with_chronology")
        _st_safe('json', coverage)

        if not coverage or not coverage.get('can_cover'):
            msg = coverage.get('message', 'Brak pokrycia') if isinstance(coverage, dict) else 'Brak pokrycia'
            _st_safe('error', f"❌ Nie można zarezerwować {shares_needed} akcji {cc_ticker} na {asof_date}. Powód: {msg}")
            try: conn.close()
            except Exception: pass
            return False

        fifo_preview = coverage.get('fifo_preview', [])
        if not fifo_preview:
            _st_safe('error', "❌ coverage.can_cover=True, ale fifo_preview jest puste — przerwano.")
            try: conn.close()
            except Exception: pass
            return False

        # 3) Zapis rezerwacji w transakcji:
        #    - cc_lot_mappings: (cc_id, lot_id, shares_reserved, created_at)
        #    - options_cc_reservations: upsert (cc_id, lot_id, qty_reserved)
        try:
            cur.execute("BEGIN")

            # For safety — wyczyść wcześniejsze rezerwacje dla cc_id (jeśli istnieją dublujące się symulacje)
            cur.execute("DELETE FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
            cur.execute("DELETE FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))

            timestamp = _dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            total_reserved = 0
            for alloc in fifo_preview:
                lot_id = alloc.get('lot_id')
                qty_to_reserve = int(alloc.get('qty_to_reserve', 0) or 0)
                if not lot_id or qty_to_reserve <= 0:
                    continue

                # cc_lot_mappings — insert
                cur.execute("""
                    INSERT INTO cc_lot_mappings (cc_id, lot_id, shares_reserved, created_at)
                    VALUES (?, ?, ?, ?)
                """, (cc_id, lot_id, qty_to_reserve, timestamp))

                # options_cc_reservations — mirror (sumarycznie per lot)
                cur.execute("""
                    INSERT INTO options_cc_reservations (cc_id, lot_id, qty_reserved)
                    VALUES (?, ?, ?)
                """, (cc_id, lot_id, qty_to_reserve))

                total_reserved += qty_to_reserve

            if total_reserved < shares_needed:
                # Jeśli z jakiegoś powodu nie udało się wyklikać pełnej liczby z fifo_preview — rollback
                cur.execute("ROLLBACK")
                _st_safe('error', f"❌ Zarezerwowano {total_reserved}/{shares_needed} — przerwano.")
                try: conn.close()
                except Exception: pass
                return False

            cur.execute("COMMIT")
        except Exception as e_tx:
            try:
                cur.execute("ROLLBACK")
            except Exception:
                pass
            _st_safe('error', f"❌ Błąd transakcji rezerwacji: {e_tx}")
            try: conn.close()
            except Exception: pass
            return False

        _st_safe('success', f"✅ Zarezerwowano {shares_needed} akcji {cc_ticker} dla CC #{cc_id} (AS-OF {asof_date})")
        _st_safe('info', f"💡 Użyto {len(fifo_preview)} LOT-ów (FIFO)")

        # Opcjonalnie pokaż szczegóły
        if 'st' in globals():
            try:
                for alloc in fifo_preview:
                    globals()['st'].write(
                        f"   LOT #{alloc.get('lot_id')}: {alloc.get('qty_to_reserve', 0)} akcji (buy_date {alloc.get('buy_date')})"
                    )
            except Exception:
                pass

        try: conn.close()
        except Exception: pass
        return True

    except Exception as e:
        _st_safe('error', f"❌ Błąd rezerwacji akcji: {e}")
        return False


def get_cc_reservations_summary(ticker=None):
    """
    Podsumowanie rezerwacji akcji pod otwarte CC.
    Zwraca liczbę otwartych CC, sumę kontraktów oraz realnie zarezerwowane akcje
    (najpierw z cc_lot_mappings, a gdy brak danych – fallback do options_cc_reservations).
    """
    import sqlite3
    from datetime import date as _date

    try:
        conn = get_connection()
        if not conn:
            return {}

        # dostęp do kolumn po kluczach
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        today = _date.today().isoformat()
        params = []
        ticker_clause = ""
        if ticker:
            ticker_clause = "AND cc.ticker = ?"
            params.append(str(ticker).upper().strip())

        # 1) Otwarte CC (as-of today), zlicz też kontrakty
        #    Łączymy warunek status='open' z chronologią na wszelki wypadek.
        cur.execute(f"""
            SELECT COUNT(*) AS open_cc,
                   COALESCE(SUM(cc.contracts), 0) AS total_contracts
            FROM options_cc cc
            WHERE (cc.status = 'open')
              AND cc.open_date <= ?
              AND (cc.close_date IS NULL OR cc.close_date > ?)
              {ticker_clause}
        """, [today, today] + params)
        row = cur.fetchone()
        open_cc = int(row["open_cc"] if row and row["open_cc"] is not None else 0)
        total_contracts = int(row["total_contracts"] if row and row["total_contracts"] is not None else 0)

        # Jeśli nic otwartego – szybki zwrot
        if open_cc == 0:
            try: conn.close()
            except Exception: pass
            return {
                'open_cc_count': 0,
                'total_contracts': 0,
                'shares_reserved': 0,
                'message': 'Brak otwartych CC'
            }

        # 2) Realne rezerwacje: preferuj cc_lot_mappings, fallback do options_cc_reservations
        # cc_lot_mappings
        cur.execute(f"""
            SELECT COALESCE(SUM(m.shares_reserved), 0) AS shares_reserved
            FROM cc_lot_mappings m
            JOIN options_cc cc ON cc.id = m.cc_id
            WHERE cc.open_date <= ?
              AND (cc.close_date IS NULL OR cc.close_date > ?)
              {ticker_clause}
        """, [today, today] + params)
        row = cur.fetchone()
        shares_reserved = int(row["shares_reserved"] if row and row["shares_reserved"] is not None else 0)

        # Fallback, jeśli brak w mappings
        if shares_reserved == 0:
            cur.execute(f"""
                SELECT COALESCE(SUM(r.qty_reserved), 0) AS shares_reserved
                FROM options_cc_reservations r
                JOIN options_cc cc ON cc.id = r.cc_id
                WHERE cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
                  {ticker_clause}
            """, [today, today] + params)
            row = cur.fetchone()
            shares_reserved = int(row["shares_reserved"] if row and row["shares_reserved"] is not None else 0)

        try: conn.close()
        except Exception: pass

        return {
            'open_cc_count': open_cc,
            'total_contracts': total_contracts,
            'shares_reserved': shares_reserved,
            'message': f'{open_cc} otwartych CC, {total_contracts} kontraktów, zarezerwowane akcje: {shares_reserved}'
        }

    except Exception as e:
        try:
            if 'st' in globals():
                globals()['st'].error(f"Błąd statystyk rezerwacji: {e}")
        except Exception:
            pass
        return {}


def save_covered_call_to_database(cc_data):
    """
    Zapisuje covered call do bazy z rezerwacją akcji FIFO.
    Tworzy NETTO cashflow (po prowizjach) i utrwala rezerwacje w tabeli options_cc_reservations.
    (wersja z SAVEPOINT – bez kolizji z transakcją zewnętrzną)
    """
    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        cursor = conn.cursor()

        # Tabela rezerwacji (idempotentnie)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options_cc_reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cc_id INTEGER NOT NULL,
                lot_id INTEGER NOT NULL,
                qty_reserved INTEGER NOT NULL,
                FOREIGN KEY(cc_id) REFERENCES options_cc(id) ON DELETE CASCADE,
                FOREIGN KEY(lot_id) REFERENCES lots(id)
            )
        """)

        # 1) Double-check pokrycia
        coverage = check_cc_coverage_with_chronology(cc_data['ticker'], cc_data['contracts'], cc_data['open_date'])
        if not coverage.get('can_cover'):
            try: conn.close()
            except Exception: pass
            return {
                'success': False,
                'message': f"Brak pokrycia: {coverage.get('message', 'Nieznany błąd')}"
            }

        # 2) Daty → str
        open_date_str = cc_data['open_date']
        if hasattr(open_date_str, 'strftime'):
            open_date_str = open_date_str.strftime('%Y-%m-%d')

        expiry_date_str = cc_data['expiry_date']
        if hasattr(expiry_date_str, 'strftime'):
            expiry_date_str = expiry_date_str.strftime('%Y-%m-%d')

        # 🔒 STRAŻ TRANSAKCJI
        outer_tx = getattr(conn, 'in_transaction', False)
        cursor.execute("SAVEPOINT sp_cc_save")

        try:
            # 3) INSERT do options_cc
            cursor.execute("""
                INSERT INTO options_cc (
                    ticker, contracts, strike_usd, premium_sell_usd,
                    open_date, expiry_date, status, fx_open, premium_sell_pln
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cc_data['ticker'],
                cc_data['contracts'],
                cc_data['strike_usd'],
                cc_data['premium_sell_usd'],
                open_date_str,
                expiry_date_str,
                'open',
                cc_data['fx_open'],
                cc_data['premium_sell_pln']
            ))
            cc_id = cursor.lastrowid

            # 4) Rezerwacja FIFO + zapis do options_cc_reservations
            shares_to_reserve = cc_data['contracts'] * 100
            remaining = shares_to_reserve

            cursor.execute("""
                SELECT id, quantity_open
                FROM lots
                WHERE ticker = ? AND quantity_open > 0
                ORDER BY buy_date, id
            """, (cc_data['ticker'],))
            lots_rows = cursor.fetchall()

            for lot_id, qty_open in lots_rows:
                if remaining <= 0:
                    break
                take = min(remaining, qty_open)
                if take <= 0:
                    continue

                cursor.execute(
                    "UPDATE lots SET quantity_open = quantity_open - ? WHERE id = ?",
                    (take, lot_id)
                )

                cursor.execute("""
                    INSERT INTO options_cc_reservations (cc_id, lot_id, qty_reserved)
                    VALUES (?, ?, ?)
                """, (cc_id, lot_id, take))

                remaining -= take

            if remaining > 0:
                # rollback tylko do naszego savepointu (nie ruszamy transakcji zewnętrznej)
                cursor.execute("ROLLBACK TO SAVEPOINT sp_cc_save")
                cursor.execute("RELEASE SAVEPOINT sp_cc_save")
                try:
                    if not outer_tx:
                        conn.rollback()
                    conn.close()
                except Exception:
                    pass
                return {'success': False, 'message': f'Nie udało się zarezerwować {remaining} akcji'}

            # 5) CASHFLOW – NETTO
            gross_premium_usd = cc_data['premium_sell_usd'] * cc_data['contracts'] * 100
            total_fees_usd = cc_data.get('broker_fee', 0.00) + cc_data.get('reg_fee', 0.00)
            net_premium_usd = gross_premium_usd - total_fees_usd

            cashflow_description = (
                f"CC {cc_data['ticker']} {cc_data['contracts']}x ${cc_data['strike_usd']} "
                f"premium ${gross_premium_usd:.2f} fees ${total_fees_usd:.2f} | "
                f"FX NBP D-1: {cc_data.get('fx_open_date', '-')}"
            )

            cursor.execute("""
                INSERT INTO cashflows (
                    type, amount_usd, date, fx_rate, amount_pln,
                    description, ref_table, ref_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'option_premium',
                net_premium_usd,
                open_date_str,
                cc_data['fx_open'],
                round(net_premium_usd * cc_data['fx_open'], 2),
                cashflow_description,
                'options_cc',
                cc_id
            ))

            # ✅ transakcja lokalna OK
            cursor.execute("RELEASE SAVEPOINT sp_cc_save")
            if not outer_tx:
                conn.commit()
            conn.close()

            return {
                'success': True,
                'cc_id': cc_id,
                'message': f'CC #{cc_id} zapisane pomyślnie!',
                'reserved_shares': shares_to_reserve
            }

        except Exception as inner:
            # ❌ błąd wewnątrz – wycofaj tylko do naszego savepointu
            try:
                cursor.execute("ROLLBACK TO SAVEPOINT sp_cc_save")
                cursor.execute("RELEASE SAVEPOINT sp_cc_save")
            except Exception:
                pass
            try:
                if not outer_tx:
                    conn.rollback()
                conn.close()
            except Exception:
                pass
            return {'success': False, 'message': f'Błąd transakcji rezerwacji/cashflow: {inner}'}

    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd zapisu: {str(e)}'}



def check_cc_coverage(ticker, contracts):
    """
    Alias dla kompatybilności wstecznej
    """
    from datetime import date
    return check_cc_coverage_with_chronology(ticker, contracts, date.today())

# DODAJ TAKŻE FUNKCJĘ NAPRAWCZĄ:

def fix_existing_cc_reservations():
    """
    FUNKCJA NAPRAWCZA:
    Odbudowuje rezerwacje CC w cc_lot_mappings (i lustrzanie w options_cc_reservations)
    według FIFO na dzień open_date każdego CC. NIE modyfikuje lots.quantity_open.
    """
    import sqlite3
    from datetime import date as _date, datetime as _dt

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return "Brak połączenia z bazą"

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        today = _date.today().isoformat()

        # Bierzemy tylko CC realnie otwarte "as-of today" (chronologia + status)
        cur.execute("""
            SELECT id, ticker, contracts, open_date
            FROM options_cc
            WHERE status = 'open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
            ORDER BY id
        """, (today, today))
        open_cc_list = cur.fetchall()

        if not open_cc_list:
            try: conn.close()
            except Exception: pass
            return "Brak otwartych CC do naprawienia"

        fixed_count = 0
        failed = []

        for row in open_cc_list:
            cc_id = row["id"]
            ticker = str(row["ticker"]).upper().strip()
            contracts = int(row["contracts"])
            open_date = row["open_date"]  # 'YYYY-MM-DD' (tekst)

            shares_needed = contracts * 100

            # 1) Coverage AS-OF open_date
            coverage = check_cc_coverage_with_chronology(ticker, contracts, open_date)
            if not coverage or not coverage.get("can_cover"):
                failed.append((cc_id, f"Brak pokrycia: {coverage.get('message') if isinstance(coverage, dict) else 'Nieznany błąd'}"))
                continue

            fifo_preview = coverage.get("fifo_preview") or []
            if sum(int(a.get("qty_to_reserve", 0) or 0) for a in fifo_preview) < shares_needed:
                failed.append((cc_id, "FIFO preview nie pokrywa pełnej rezerwacji"))
                continue

            # 2) Transakcyjnie odbuduj rezerwacje w obu tabelach (bez dotykania lots)
            try:
                cur.execute("BEGIN")
                # wyczyść stare wpisy (jeśli jakieś są)
                cur.execute("DELETE FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
                cur.execute("DELETE FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))

                # upewnij się, że tabele istnieją (idempotentnie)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cc_lot_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cc_id INTEGER NOT NULL,
                        lot_id INTEGER NOT NULL,
                        shares_reserved INTEGER NOT NULL,
                        created_at TIMESTAMP,
                        FOREIGN KEY(cc_id) REFERENCES options_cc(id) ON DELETE CASCADE,
                        FOREIGN KEY(lot_id) REFERENCES lots(id)
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS options_cc_reservations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cc_id INTEGER NOT NULL,
                        lot_id INTEGER NOT NULL,
                        qty_reserved INTEGER NOT NULL,
                        FOREIGN KEY(cc_id) REFERENCES options_cc(id) ON DELETE CASCADE,
                        FOREIGN KEY(lot_id) REFERENCES lots(id)
                    )
                """)

                ts = _dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                total_reserved = 0

                for alloc in fifo_preview:
                    lot_id = alloc.get("lot_id")
                    qty = int(alloc.get("qty_to_reserve", 0) or 0)
                    if not lot_id or qty <= 0:
                        continue

                    # Autoratywna tabela rezerwacji
                    cur.execute("""
                        INSERT INTO cc_lot_mappings (cc_id, lot_id, shares_reserved, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (cc_id, lot_id, qty, ts))

                    # Lustrzane odwzorowanie (kompatybilność)
                    cur.execute("""
                        INSERT INTO options_cc_reservations (cc_id, lot_id, qty_reserved)
                        VALUES (?, ?, ?)
                    """, (cc_id, lot_id, qty))

                    total_reserved += qty

                if total_reserved < shares_needed:
                    cur.execute("ROLLBACK")
                    failed.append((cc_id, f"Zarezerwowano {total_reserved}/{shares_needed}"))
                    continue

                cur.execute("COMMIT")
                fixed_count += 1

            except Exception as txe:
                try:
                    cur.execute("ROLLBACK")
                except Exception:
                    pass
                failed.append((cc_id, f"Błąd transakcji: {txe}"))
                continue

        try:
            conn.close()
        except Exception:
            pass

        if not failed:
            return f"Naprawiono {fixed_count} z {len(open_cc_list)} CC"
        else:
            # zwięzły raport z błędami
            fails = "; ".join([f"CC#{cid}: {msg}" for cid, msg in failed])
            return f"Naprawiono {fixed_count} z {len(open_cc_list)} CC; Problemy: {fails}"

    except Exception as e:
        if conn:
            try: conn.rollback()
            except Exception: pass
            conn.close()
        return f"Błąd naprawki: {e}"


def get_covered_calls_summary(ticker=None, status=None):
    """
    Pobranie podsumowania covered calls

    Args:
        ticker: Opcjonalnie filtruj po tickerze
        status: Opcjonalnie filtruj po statusie ('open', 'expired', 'bought_back')

    Returns:
        list: Lista CC z podstawowymi danymi (list[dict])
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        # pozwala czytać po nazwach kolumn (bardziej odporne na kolejność)
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        query = """
            SELECT id, ticker, contracts, strike_usd, premium_sell_usd,
                   open_date, expiry_date, status, fx_open, premium_sell_pln,
                   premium_buyback_pln, pl_pln, created_at
            FROM options_cc
            WHERE 1=1
        """
        params = []

        if ticker:
            query += " AND UPPER(ticker) = ?"
            params.append(str(ticker).upper().strip())

        if status:
            query += " AND LOWER(status) = ?"
            params.append(str(status).lower().strip())

        query += " ORDER BY open_date DESC, id DESC"

        cur.execute(query, params)
        rows = cur.fetchall() or []

        cc_list = []
        for r in rows:
            # r może być Row albo tuple — obsłużmy oba warianty:
            if isinstance(r, sqlite3.Row):
                cc_list.append({
                    'id': r['id'],
                    'ticker': r['ticker'],
                    'contracts': int(r['contracts'] or 0),
                    'strike_usd': float(r['strike_usd'] or 0),
                    'premium_sell_usd': float(r['premium_sell_usd'] or 0),
                    'open_date': r['open_date'],
                    'expiry_date': r['expiry_date'],
                    'status': r['status'],
                    'fx_open': float(r['fx_open'] or 0),
                    'premium_sell_pln': float(r['premium_sell_pln'] or 0),
                    'premium_buyback_pln': float(r['premium_buyback_pln'] or 0) if r['premium_buyback_pln'] is not None else None,
                    'pl_pln': float(r['pl_pln'] or 0) if r['pl_pln'] is not None else None,
                    'created_at': r['created_at']
                })
            else:
                cc_list.append({
                    'id': r[0],
                    'ticker': r[1],
                    'contracts': int(r[2] or 0),
                    'strike_usd': float(r[3] or 0),
                    'premium_sell_usd': float(r[4] or 0),
                    'open_date': r[5],
                    'expiry_date': r[6],
                    'status': r[7],
                    'fx_open': float(r[8] or 0),
                    'premium_sell_pln': float(r[9] or 0),
                    'premium_buyback_pln': float(r[10] or 0) if r[10] is not None else None,
                    'pl_pln': float(r[11] or 0) if r[11] is not None else None,
                    'created_at': r[12]
                })

        return cc_list

    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Błąd pobierania CC: {e}")
        except Exception:
            pass
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def test_cc_save_operations():
    """Test operacji zapisu CC (bez skutków ubocznych). Sprawdza wywoływalność i podstawowe zwroty."""
    results = {
        'save_function_test': False,     # czy save_covered_call_to_database jest callable
        'summary_function_test': False,  # czy get_covered_calls_summary jest callable
        'rollback_test': False,          # czy summary zwraca listę (brak wyjątków)
        'details': {}
    }

    try:
        # 1) callable checks
        results['save_function_test'] = callable(save_covered_call_to_database)
        results['summary_function_test'] = callable(get_covered_calls_summary)

        # 2) pobierz listę CC (może być pusta)
        cc_list = get_covered_calls_summary()
        results['rollback_test'] = isinstance(cc_list, list)
        results['details']['cc_count'] = len(cc_list) if isinstance(cc_list, list) else None

        # 3) szybkie filtry (nie zapisują, tylko czytają)
        #    defensywnie: jeśli pusto, to test i tak przejdzie (ma nie rzucać wyjątków)
        _ = get_covered_calls_summary(status='open')
        _ = get_covered_calls_summary(status='expired')

        # 4) format pierwszego rekordu (jeśli jest)
        if isinstance(cc_list, list) and cc_list:
            sample = cc_list[0]
            # wymagane klucze z get_covered_calls_summary
            expected_keys = {
                'id','ticker','contracts','strike_usd','premium_sell_usd',
                'open_date','expiry_date','status','fx_open','premium_sell_pln',
                'premium_buyback_pln','pl_pln','created_at'
            }
            results['details']['sample_has_all_keys'] = expected_keys.issubset(set(sample.keys()))

    except Exception as e:
        try:
            if 'st' in globals():
                globals()['st'].error(f"Błąd testów CC save: {e}")
        except Exception:
            pass

    return results


def expire_covered_call(cc_id):
    """
    Expiry CC:
      - ustawia status 'expired' i close_date = expiry_date,
      - zapisuje fx_close (NBP D-1 z dnia expiry),
      - P/L w PLN = premium_sell_pln (cała premia zostaje),
      - ZWALNIA rezerwacje: usuwa wpisy w cc_lot_mappings i options_cc_reservations,
      - NIE modyfikuje lots.quantity_open.
    """
    import sqlite3
    from datetime import datetime as _dt, timedelta as _td

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # 1) Pobierz dane CC
        cur.execute("""
            SELECT id, ticker, contracts, premium_sell_usd, expiry_date,
                   status, premium_sell_pln, fx_open, open_date
            FROM options_cc
            WHERE id = ?
        """, (cc_id,))
        row = cur.fetchone()
        if not row:
            return {'success': False, 'message': f'CC #{cc_id} nie istnieje'}

        ticker = row['ticker']
        contracts = int(row['contracts'] or 0)
        expiry_date_str = row['expiry_date']
        status = row['status']
        premium_sell_pln = float(row['premium_sell_pln'] or 0.0)
        fx_open = float(row['fx_open'] or 0.0)

        if status != 'open':
            return {'success': False, 'message': f'CC #{cc_id} już zamknięte (status: {status})'}

        # 2) FX close = NBP D-1 dla expiry_date (fallback na fx_open)
        try:
            # expiry_date_str powinno być 'YYYY-MM-DD'
            exp_dt = _dt.strptime(expiry_date_str, "%Y-%m-%d").date()
            fx_close_date = (exp_dt - _td(days=1)).isoformat()
        except Exception:
            # na wypadek niestandardowego formatu — próbujmy użyć bezpośrednio
            fx_close_date = expiry_date_str

        fx_close = get_fx_rate_for_date(fx_close_date)
        try:
            fx_close = float(fx_close) if fx_close is not None else 0.0
        except Exception:
            fx_close = 0.0
        if fx_close <= 0.0:
            fx_close = fx_open  # awaryjnie

        # 3) P/L w PLN: opcja wygasła bezwartościowa → zatrzymana cała premia w PLN
        pl_pln = premium_sell_pln

        # 4) Oblicz, ile faktycznie jest zarezerwowane (z tabel rezerwacji)
        #    Preferuj cc_lot_mappings; jeśli 0 → spróbuj options_cc_reservations
        cur.execute("SELECT COALESCE(SUM(shares_reserved),0) AS s FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
        s1_row = cur.fetchone()
        shares_reserved_mappings = int(s1_row['s'] if s1_row and s1_row['s'] is not None else 0)

        shares_reserved_simple = 0
        if shares_reserved_mappings == 0:
            cur.execute("SELECT COALESCE(SUM(qty_reserved),0) AS s FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))
            s2_row = cur.fetchone()
            shares_reserved_simple = int(s2_row['s'] if s2_row and s2_row['s'] is not None else 0)

        shares_to_release = shares_reserved_mappings or shares_reserved_simple or (contracts * 100)

        # 5) Transakcyjnie: update CC + drop rezerwacje
        try:
            cur.execute("BEGIN")

            # a) update statusu CC
            cur.execute("""
                UPDATE options_cc
                SET status = 'expired',
                    close_date = ?,
                    fx_close = ?,
                    pl_pln = ?
                WHERE id = ?
            """, (expiry_date_str, fx_close, pl_pln, cc_id))

            # b) zwolnij rezerwacje → usuń wpisy w obu tabelach
            cur.execute("DELETE FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
            cur.execute("DELETE FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))

            cur.execute("COMMIT")
        except Exception as txe:
            try: cur.execute("ROLLBACK")
            except Exception: pass
            return {
                'success': False,
                'message': f'Błąd transakcji przy expiry: {txe}'
            }

        return {
            'success': True,
            'message': f'CC #{cc_id} oznaczone jako expired — rezerwacje zwolnione.',
            'pl_pln': pl_pln,
            'shares_released': shares_to_release,
            'lots_updated': 0,  # nie dotykamy LOT-ów
            'premium_kept_pln': premium_sell_pln,
            'expiry_date': expiry_date_str,
            'fx_close_date': fx_close_date,
            'fx_close': fx_close
        }

    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        try:
            import streamlit as st
            st.error(f"Błąd expiry CC: {e}")
        except Exception:
            pass
        return {
            'success': False,
            'message': f'Błąd expiry: {str(e)}'
        }
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def check_cc_restrictions_before_sell(ticker, quantity_to_sell):
    """
    PUNKT 61 NAPRAWKA (zaktualizowana): Poprawne sprawdzanie blokad CC

    Nowa logika:
    1) available_in_lots = SUM(lots.quantity_open) dla danego tickera
    2) reserved_as_of_today = SUM(rezerwacji z cc_lot_mappings) (fallback: options_cc_reservations)
       dla CC otwartych as-of dziś: open_date <= today AND (close_date IS NULL OR close_date > today)
    3) available_to_sell = max(0, available_in_lots - reserved_as_of_today)
    4) can_sell = available_to_sell >= quantity_to_sell
    """
    import sqlite3
    from datetime import date as _date

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'can_sell': False, 'message': 'Brak połączenia z bazą',
                    'available_to_sell': 0, 'reserved_for_cc': 0,
                    'total_available': 0, 'blocking_cc': []}

        # Umożliwia dostęp po kluczach
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        t = str(ticker).upper().strip()
        today = _date.today().isoformat()

        # 1) SUMA otwartych akcji w LOT-ach (nie korygujemy o CC w samej tabeli lots)
        cur.execute("""
            SELECT COALESCE(SUM(quantity_open), 0) AS available_in_lots
            FROM lots
            WHERE UPPER(ticker) = ?
        """, (t,))
        row = cur.fetchone()
        available_in_lots = int(row["available_in_lots"] if row and row["available_in_lots"] is not None else 0)

        # 2) Ile jest zarezerwowane pod otwarte CC (as-of dziś)
        #    Priorytet: cc_lot_mappings
        cur.execute("""
            SELECT COALESCE(SUM(m.shares_reserved), 0) AS reserved
            FROM cc_lot_mappings m
            JOIN options_cc cc ON cc.id = m.cc_id
            WHERE UPPER(cc.ticker) = ?
              AND cc.open_date <= ?
              AND (cc.close_date IS NULL OR cc.close_date > ?)
              AND cc.status = 'open'
        """, (t, today, today))
        row = cur.fetchone()
        reserved_from_mappings = int(row["reserved"] if row and row["reserved"] is not None else 0)

        reserved_for_cc = reserved_from_mappings
        if reserved_for_cc == 0:
            # Fallback: options_cc_reservations (kompatybilność wstecz)
            cur.execute("""
                SELECT COALESCE(SUM(r.qty_reserved), 0) AS reserved
                FROM options_cc_reservations r
                JOIN options_cc cc ON cc.id = r.cc_id
                WHERE UPPER(cc.ticker) = ?
                  AND cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
                  AND cc.status = 'open'
            """, (t, today, today))
            row = cur.fetchone()
            reserved_for_cc = int(row["reserved"] if row and row["reserved"] is not None else 0)

        # 3) Dostępne do sprzedaży po uwzględnieniu rezerwacji
        available_to_sell = available_in_lots - reserved_for_cc
        if available_to_sell < 0:
            available_to_sell = 0

        can_sell = available_to_sell >= int(quantity_to_sell)

        # 4) Jeśli nie można sprzedać — raport blokujących CC z realnymi rezerwacjami per CC
        blocking_cc = []
        total_shares_owned = 0
        if not can_sell:
            # total posiadanych (dla kontekstu)
            cur.execute("""
                SELECT COALESCE(SUM(quantity_total), 0) AS total_owned
                FROM lots
                WHERE UPPER(ticker) = ?
            """, (t,))
            row = cur.fetchone()
            total_shares_owned = int(row["total_owned"] if row and row["total_owned"] is not None else 0)

            # Rozbicie rezerwacji per CC (priorytet mappings, fallback reservations)
            cur.execute("""
                SELECT cc.id AS cc_id,
                       cc.contracts,
                       cc.strike_usd,
                       cc.expiry_date,
                       cc.open_date,
                       COALESCE(SUM(m.shares_reserved), 0) AS shares_reserved
                FROM options_cc cc
                LEFT JOIN cc_lot_mappings m ON m.cc_id = cc.id
                WHERE UPPER(cc.ticker) = ?
                  AND cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
                  AND cc.status = 'open'
                GROUP BY cc.id, cc.contracts, cc.strike_usd, cc.expiry_date, cc.open_date
                ORDER BY cc.open_date
            """, (t, today, today))
            rows = cur.fetchall() or []

            # Jeżeli mappings są puste (wszystkie 0), spróbuj na bazie options_cc_reservations
            if not rows or all(int(r["shares_reserved"] or 0) == 0 for r in rows):
                cur.execute("""
                    SELECT cc.id AS cc_id,
                           cc.contracts,
                           cc.strike_usd,
                           cc.expiry_date,
                           cc.open_date,
                           COALESCE(SUM(r.qty_reserved), 0) AS shares_reserved
                    FROM options_cc cc
                    LEFT JOIN options_cc_reservations r ON r.cc_id = cc.id
                    WHERE UPPER(cc.ticker) = ?
                      AND cc.open_date <= ?
                      AND (cc.close_date IS NULL OR cc.close_date > ?)
                      AND cc.status = 'open'
                    GROUP BY cc.id, cc.contracts, cc.strike_usd, cc.expiry_date, cc.open_date
                    ORDER BY cc.open_date
                """, (t, today, today))
                rows = cur.fetchall() or []

            blocking_cc = [{
                'cc_id': int(r['cc_id']),
                'contracts': int(r['contracts'] or 0),
                'shares_reserved': int(r['shares_reserved'] or 0),
                'strike_usd': float(r['strike_usd'] or 0),
                'expiry_date': r['expiry_date'],
                'open_date': r['open_date']
            } for r in rows]

        return {
            'can_sell': can_sell,
            'available_to_sell': available_to_sell,
            'reserved_for_cc': reserved_for_cc,
            'total_available': total_shares_owned,  # wszystkie posiadane (quantity_total)
            'blocking_cc': blocking_cc,
            'message': 'OK' if can_sell else f'Zarezerwowane pod {len(blocking_cc)} CC'
        }

    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Błąd check_cc_restrictions: {e}")
        except Exception:
            pass
        return {
            'can_sell': False,
            'message': f'Błąd: {str(e)}',
            'available_to_sell': 0,
            'reserved_for_cc': 0,
            'total_available': 0,
            'blocking_cc': []
        }
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def debug_cc_restrictions(ticker):
    """
    Funkcja diagnostyczna do debugowania blokad CC (read-only, bez skutków ubocznych).
    Pokazuje:
      - LOT-y (quantity_total, quantity_open)
      - otwarte CC as-of dziś
      - faktyczne rezerwacje z cc_lot_mappings (fallback: options_cc_reservations)
      - sumy i dostępne do sprzedaży
    """
    import sqlite3
    from datetime import date as _date

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return "Brak połączenia z bazą"

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        t = str(ticker).upper().strip()
        today = _date.today().isoformat()

        print(f"\n🔍 DIAGNOSTYKA CC dla {t} (as-of {today}):")

        # 1) LOT-y
        cur.execute("""
            SELECT id, quantity_total, quantity_open, buy_date
            FROM lots
            WHERE UPPER(ticker) = ?
            ORDER BY buy_date, id
        """, (t,))
        lots = cur.fetchall() or []
        print(f"📦 LOT-y ({len(lots)}):")
        for r in lots:
            print(f"   LOT #{r['id']}: open {r['quantity_open']}/{r['quantity_total']} (buy {r['buy_date']})")
        total_open = sum(int(r["quantity_open"] or 0) for r in lots)
        print(f"   📊 SUMA quantity_open: {total_open}")

        # 2) Otwarte CC (as-of dziś)
        cur.execute("""
            SELECT id, contracts, status, open_date, expiry_date, close_date, strike_usd
            FROM options_cc
            WHERE UPPER(ticker) = ?
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
              AND status = 'open'
            ORDER BY open_date, id
        """, (t, today, today))
        open_cc = cur.fetchall() or []
        print(f"🔓 OTWARTE CC (as-of dziś) ({len(open_cc)}):")
        for cc in open_cc:
            shares = int(cc["contracts"] or 0) * 100
            print(f"   CC #{cc['id']}: {cc['contracts']} contracts = {shares} shares, "
                  f"status='{cc['status']}', open={cc['open_date']}, expiry={cc['expiry_date']}")

        # 3) Rezerwacje per LOT z cc_lot_mappings (fallback: options_cc_reservations)
        cur.execute("""
            SELECT m.lot_id, COALESCE(SUM(m.shares_reserved),0) AS reserved
            FROM cc_lot_mappings m
            JOIN options_cc cc ON cc.id = m.cc_id
            WHERE UPPER(cc.ticker) = ?
              AND cc.open_date <= ?
              AND (cc.close_date IS NULL OR cc.close_date > ?)
              AND cc.status = 'open'
            GROUP BY m.lot_id
            ORDER BY m.lot_id
        """, (t, today, today))
        lot_res_rows = cur.fetchall() or []
        lot_reserved_map = {int(r["lot_id"]): int(r["reserved"] or 0) for r in lot_res_rows}
        reserved_total = sum(lot_reserved_map.values())

        if reserved_total == 0:
            # fallback — options_cc_reservations
            cur.execute("""
                SELECT r.lot_id, COALESCE(SUM(r.qty_reserved),0) AS reserved
                FROM options_cc_reservations r
                JOIN options_cc cc ON cc.id = r.cc_id
                WHERE UPPER(cc.ticker) = ?
                  AND cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
                  AND cc.status = 'open'
                GROUP BY r.lot_id
                ORDER BY r.lot_id
            """, (t, today, today))
            lot_res_rows = cur.fetchall() or []
            lot_reserved_map = {int(r["lot_id"]): int(r["reserved"] or 0) for r in lot_res_rows}
            reserved_total = sum(lot_reserved_map.values())

        print(f"🧷 REZERWACJE per LOT ({len(lot_reserved_map)}):")
        for lot_id, qty in lot_reserved_map.items():
            print(f"   LOT #{lot_id}: reserved {qty}")

        # 4) Rezerwacje per CC (żeby wiedzieć, co blokuje)
        cur.execute("""
            SELECT cc.id AS cc_id,
                   cc.contracts,
                   cc.strike_usd,
                   cc.expiry_date,
                   cc.open_date,
                   COALESCE(SUM(m.shares_reserved),0) AS shares_reserved
            FROM options_cc cc
            LEFT JOIN cc_lot_mappings m ON m.cc_id = cc.id
            WHERE UPPER(cc.ticker) = ?
              AND cc.open_date <= ?
              AND (cc.close_date IS NULL OR cc.close_date > ?)
              AND cc.status = 'open'
            GROUP BY cc.id, cc.contracts, cc.strike_usd, cc.expiry_date, cc.open_date
            ORDER BY cc.open_date, cc.id
        """, (t, today, today))
        per_cc = cur.fetchall() or []

        # jeśli mappings puste → fallback do options_cc_reservations
        if not per_cc or all(int(r["shares_reserved"] or 0) == 0 for r in per_cc):
            cur.execute("""
                SELECT cc.id AS cc_id,
                       cc.contracts,
                       cc.strike_usd,
                       cc.expiry_date,
                       cc.open_date,
                       COALESCE(SUM(r.qty_reserved),0) AS shares_reserved
                FROM options_cc cc
                LEFT JOIN options_cc_reservations r ON r.cc_id = cc.id
                WHERE UPPER(cc.ticker) = ?
                  AND cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
                  AND cc.status = 'open'
                GROUP BY cc.id, cc.contracts, cc.strike_usd, cc.expiry_date, cc.open_date
                ORDER BY cc.open_date, cc.id
            """, (t, today, today))
            per_cc = cur.fetchall() or []

        print(f"🎯 REZERWACJE per CC ({len(per_cc)}):")
        for r in per_cc:
            contracts = int(r["contracts"] or 0)
            shares_reserved = int(r["shares_reserved"] or 0)
            print(f"   CC #{r['cc_id']}: {contracts}x ({contracts*100} sh) → reserved={shares_reserved}, "
                  f"open={r['open_date']}, exp={r['expiry_date']}, strike={r['strike_usd']}")

        # 5) Podsumowanie dostępności
        available = total_open - reserved_total
        if available < 0:
            available = 0
        print(f"📊 PODSUMOWANIE: total_open={total_open}, reserved_total={reserved_total}")
        print(f"✅ DOSTĘPNE DO SPRZEDAŻY: {available}")

        return "OK - szczegóły w konsoli"

    except Exception as e:
        return f"Błąd diagnostyki: {e}"
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_total_quantity(ticker):
    """
    Pobiera łączną ilość posiadanych akcji dla danego tickera
    (łącznie z tymi, które są zarezerwowane pod CC).
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return 0

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # SUMA wszystkich akcji, niezależnie od rezerwacji CC
        cur.execute("""
            SELECT COALESCE(SUM(quantity_total), 0) AS total_shares
            FROM lots
            WHERE UPPER(ticker) = ?
        """, (str(ticker).upper().strip(),))

        row = cur.fetchone()
        total = int(row["total_shares"] if row and row["total_shares"] is not None else 0)

        return total

    except Exception:
        return 0
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_all_tickers():
    """
    Pobiera listę wszystkich tickerów z akcjami w portfelu.
    ✅ Uwzględnia również tickery, w których wszystkie akcje są zarezerwowane pod CC.
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Pobierz tickery, gdzie quantity_total > 0, a nie tylko quantity_open
        cur.execute("""
            SELECT DISTINCT ticker
            FROM lots
            WHERE quantity_total > 0
            ORDER BY UPPER(ticker)
        """)

        rows = cur.fetchall() or []
        return [r["ticker"] if isinstance(r, sqlite3.Row) else r[0] for r in rows]

    except Exception:
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_open_cc_for_ticker(ticker):
    """Pobiera listę otwartych Covered Calls dla danego tickera (as-of dziś, z realnymi rezerwacjami)."""
    import sqlite3
    from datetime import date as _date

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        t = str(ticker).upper().strip()
        today = _date.today().isoformat()

        # Otwarte CC as-of dziś (chronologia + status)
        cur.execute("""
            SELECT id, contracts, strike_usd, expiry_date, premium_sell_usd
            FROM options_cc
            WHERE UPPER(ticker) = ?
              AND status = 'open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
            ORDER BY expiry_date ASC, id ASC
        """, (t, today, today))
        rows = cur.fetchall() or []

        cc_list = []
        for r in rows:
            cc_id = int(r["id"])
            contracts = int(r["contracts"] or 0)
            strike_usd = float(r["strike_usd"] or 0)
            expiry_date = r["expiry_date"]
            premium_usd = float(r["premium_sell_usd"] or 0)

            # Rzeczywista liczba zarezerwowanych akcji dla tego CC
            cur.execute("SELECT COALESCE(SUM(shares_reserved),0) AS s FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
            row_map = cur.fetchone()
            shares_reserved = int(row_map["s"] if row_map and row_map["s"] is not None else 0)

            if shares_reserved == 0:
                # fallback do starej tabeli rezerwacji
                cur.execute("SELECT COALESCE(SUM(qty_reserved),0) AS s FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))
                row_res = cur.fetchone()
                shares_reserved = int(row_res["s"] if row_res and row_res["s"] is not None else 0)

            # jeśli nadal 0 (np. historyczne rekordy bez rezerwacji), pokaż nominalne contracts*100
            if shares_reserved == 0:
                shares_reserved = contracts * 100

            cc_list.append({
                'cc_id': cc_id,
                'contracts': contracts,
                'strike_usd': strike_usd,
                'expiry_date': expiry_date,
                'premium_usd': premium_usd,
                'shares_reserved': shares_reserved
            })

        return cc_list

    except Exception:
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_portfolio_summary():
    """Pobiera podsumowanie całego portfela dla dashboard (spójne z rezerwacjami CC)."""
    import sqlite3
    from datetime import date as _date

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {}

        # Row access po nazwach kolumn
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        today = _date.today().isoformat()

        # 1) Akcje w LOT-ach: bierzemy quantity_total (posiadane sztuki, niezależnie od rezerwacji)
        cur.execute("""
            SELECT UPPER(ticker) AS ticker,
                   COALESCE(SUM(quantity_total), 0) AS total_shares,
                   COALESCE(SUM(quantity_total * buy_price_usd
                         + COALESCE(broker_fee_usd,0)
                         + COALESCE(reg_fee_usd,0)), 0) AS total_cost_usd
            FROM lots
            GROUP BY UPPER(ticker)
        """)
        stock_rows = cur.fetchall() or []

        # Zainicjalizuj słownik portfela
        portfolio = {}
        for r in stock_rows:
            t = r["ticker"]
            portfolio[t] = {
                "total_shares": int(r["total_shares"] or 0),
                "cost_usd": float(r["total_cost_usd"] or 0.0),
                "cc_count": 0,
                "shares_reserved": 0,
                "shares_available": int(r["total_shares"] or 0),  # chwilowo = total; skorygujemy niżej
            }

        if not portfolio:
            return {}

        tickers = list(portfolio.keys())

        # 2) Otwarte CC per ticker (as-of dziś) — zlicz liczbę CC i kontrakty
        #    (użyjemy też do shares_reserved fallback)
        cur.execute(f"""
            SELECT UPPER(ticker) AS ticker,
                   COUNT(*) AS open_cc_count,
                   COALESCE(SUM(contracts),0) AS total_contracts
            FROM options_cc
            WHERE status = 'open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
              AND UPPER(ticker) IN ({",".join(["?"]*len(tickers))})
            GROUP BY UPPER(ticker)
        """, [today, today, *tickers])
        cc_agg = {row["ticker"]: {"open_cc_count": int(row["open_cc_count"] or 0),
                                  "total_contracts": int(row["total_contracts"] or 0)}
                  for row in (cur.fetchall() or [])}

        # 3) Rzeczywiste rezerwacje z cc_lot_mappings per ticker (as-of dziś)
        cur.execute(f"""
            SELECT UPPER(cc.ticker) AS ticker,
                   COALESCE(SUM(m.shares_reserved),0) AS shares_reserved
            FROM cc_lot_mappings m
            JOIN options_cc cc ON cc.id = m.cc_id
            WHERE cc.status = 'open'
              AND cc.open_date <= ?
              AND (cc.close_date IS NULL OR cc.close_date > ?)
              AND UPPER(cc.ticker) IN ({",".join(["?"]*len(tickers))})
            GROUP BY UPPER(cc.ticker)
        """, [today, today, *tickers])
        reserved_map = {row["ticker"]: int(row["shares_reserved"] or 0) for row in (cur.fetchall() or [])}

        # 4) Fallback do options_cc_reservations tam, gdzie mappings nie mają danych
        #    (tylko dla tickerów, które nie mają jeszcze rezerwacji w reserved_map)
        need_fallback = [t for t in tickers if reserved_map.get(t, 0) == 0]
        if need_fallback:
            cur.execute(f"""
                SELECT UPPER(cc.ticker) AS ticker,
                       COALESCE(SUM(r.qty_reserved),0) AS shares_reserved
                FROM options_cc_reservations r
                JOIN options_cc cc ON cc.id = r.cc_id
                WHERE cc.status = 'open'
                  AND cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
                  AND UPPER(cc.ticker) IN ({",".join(["?"]*len(need_fallback))})
                GROUP BY UPPER(cc.ticker)
            """, [today, today, *need_fallback])
            for row in cur.fetchall() or []:
                reserved_map[row["ticker"]] = int(row["shares_reserved"] or 0)

        # 5) Złóż wszystko do portfolio
        for t in tickers:
            cc_info = cc_agg.get(t, {"open_cc_count": 0, "total_contracts": 0})
            reserved = int(reserved_map.get(t, 0))

            # Uzupełnij cc_count
            portfolio[t]["cc_count"] = cc_info["open_cc_count"]

            # Rzeczywiste rezerwacje (nie nominalne contracts*100)
            portfolio[t]["shares_reserved"] = reserved

            # Wolne akcje = posiadane - zarezerwowane
            free_shares = portfolio[t]["total_shares"] - reserved
            portfolio[t]["shares_available"] = free_shares if free_shares > 0 else 0

        return portfolio

    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Błąd portfolio summary: {e}")
        except Exception:
            pass
        return {}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_cc_expiry_alerts(days_ahead=7):
    """Pobiera Covered Calls wygasające w najbliższych N dni (as-of dziś)."""
    import sqlite3
    from datetime import date as _date, timedelta as _td

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Okno alertów: [today, today+N]
        today = _date.today()
        if not isinstance(days_ahead, int):
            try:
                days_ahead = int(days_ahead)
            except Exception:
                days_ahead = 7
        end_date = today + _td(days=max(0, days_ahead))  # nie pozwól na ujemne

        today_str = today.isoformat()
        end_str = end_date.isoformat()

        # Tylko faktycznie otwarte CC as-of dziś
        cur.execute("""
            SELECT id, ticker, contracts, strike_usd, expiry_date,
                   CAST(julianday(expiry_date) - julianday(?) AS INTEGER) AS days_to_expiry
            FROM options_cc
            WHERE status = 'open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
              AND expiry_date >= ?
              AND expiry_date <= ?
            ORDER BY expiry_date ASC, id ASC
        """, (today_str, today_str, today_str, today_str, end_str))

        rows = cur.fetchall() or []

        alerts = []
        for r in rows:
            alerts.append({
                'cc_id': int(r['id']),
                'ticker': r['ticker'],
                'contracts': int(r['contracts'] or 0),
                'strike_usd': float(r['strike_usd'] or 0),
                'expiry_date': r['expiry_date'],
                'days_to_expiry': int(r['days_to_expiry'] or 0)
            })

        return alerts

    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Błąd CC expiry alerts: {e}")
        except Exception:
            pass
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

        
def reset_ticker_reservations(ticker):
    """
    FUNKCJA NAPRAWCZA: Resetuje rezerwacje dla konkretnego tickera
    (bez modyfikacji lots.quantity_open).
    Czyści stare rezerwacje i odbudowuje je z FIFO dla wszystkich otwartych CC tego tickera.
    """
    import sqlite3
    from datetime import date as _date, datetime as _dt

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return "Brak połączenia z bazą"

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        t = str(ticker).upper().strip()
        today = _date.today().isoformat()
        print(f"🔄 RESET REZERWACJI dla {t} (as-of {today})")

        # 1) Zbierz OTWARTE CC dla tickera (as-of dziś)
        cur.execute("""
            SELECT id, contracts, open_date
            FROM options_cc
            WHERE UPPER(ticker) = ?
              AND status = 'open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
            ORDER BY open_date, id
        """, (t, today, today))
        open_cc = cur.fetchall() or []
        print(f"   🎯 Otwarte CC: {len(open_cc)}")

        # 2) Wyczyść rezerwacje dla tego tickera (oba stoły)
        try:
            cur.execute("BEGIN")
            cur.execute("""
                DELETE FROM cc_lot_mappings
                WHERE cc_id IN (SELECT id FROM options_cc WHERE UPPER(ticker)=?)
            """, (t,))
            cur.execute("""
                DELETE FROM options_cc_reservations
                WHERE cc_id IN (SELECT id FROM options_cc WHERE UPPER(ticker)=?)
            """, (t,))
            cur.execute("COMMIT")
        except Exception:
            try: cur.execute("ROLLBACK")
            except Exception: pass
            return f"Błąd: nie udało się wyczyścić starych rezerwacji dla {t}"

        # 3) Odbuduj rezerwacje FIFO dla każdego CC
        rebuilt = 0
        failed = []
        ts = _dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        for cc in open_cc:
            cc_id = int(cc["id"])
            contracts = int(cc["contracts"] or 0)
            open_date = cc["open_date"]
            shares_needed = contracts * 100

            coverage = check_cc_coverage_with_chronology(t, contracts, open_date)
            if not coverage or not coverage.get("can_cover"):
                failed.append((cc_id, f"Brak pokrycia: {coverage.get('message') if isinstance(coverage, dict) else 'Nieznany błąd'}"))
                continue

            fifo_preview = coverage.get("fifo_preview") or []
            if sum(int(a.get("qty_to_reserve", 0) or 0) for a in fifo_preview) < shares_needed:
                failed.append((cc_id, "FIFO preview nie pokrywa pełnej rezerwacji"))
                continue

            try:
                cur.execute("BEGIN")
                total_reserved = 0
                for alloc in fifo_preview:
                    lot_id = alloc.get("lot_id")
                    qty = int(alloc.get("qty_to_reserve", 0) or 0)
                    if not lot_id or qty <= 0:
                        continue

                    # Autoratywna tabela rezerwacji
                    cur.execute("""
                        INSERT INTO cc_lot_mappings (cc_id, lot_id, shares_reserved, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (cc_id, lot_id, qty, ts))

                    # Lustrzane odwzorowanie (kompatybilność wstecz)
                    cur.execute("""
                        INSERT INTO options_cc_reservations (cc_id, lot_id, qty_reserved)
                        VALUES (?, ?, ?)
                    """, (cc_id, lot_id, qty))

                    total_reserved += qty

                if total_reserved < shares_needed:
                    cur.execute("ROLLBACK")
                    failed.append((cc_id, f"Zarezerwowano {total_reserved}/{shares_needed}"))
                    continue

                cur.execute("COMMIT")
                rebuilt += 1

            except Exception as txe:
                try: cur.execute("ROLLBACK")
                except Exception: pass
                failed.append((cc_id, f"Błąd transakcji: {txe}"))
                continue

        # 4) Statystyki końcowe (posiadane vs zarezerwowane)
        cur.execute("""
            SELECT COALESCE(SUM(quantity_total),0) AS total_shares
            FROM lots
            WHERE UPPER(ticker)=?
        """, (t,))
        row = cur.fetchone()
        total_shares = int(row["total_shares"] if row and row["total_shares"] is not None else 0)

        cur.execute("""
            SELECT COALESCE(SUM(m.shares_reserved),0) AS reserved
            FROM cc_lot_mappings m
            JOIN options_cc cc ON cc.id = m.cc_id
            WHERE UPPER(cc.ticker)=?
              AND cc.status='open'
              AND cc.open_date <= ?
              AND (cc.close_date IS NULL OR cc.close_date > ?)
        """, (t, today, today))
        row = cur.fetchone()
        reserved = int(row["reserved"] if row and row["reserved"] is not None else 0)

        # fallback do starej tabeli, jeśli mappings puste
        if reserved == 0:
            cur.execute("""
                SELECT COALESCE(SUM(r.qty_reserved),0) AS reserved
                FROM options_cc_reservations r
                JOIN options_cc cc ON cc.id = r.cc_id
                WHERE UPPER(cc.ticker)=?
                  AND cc.status='open'
                  AND cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
            """, (t, today, today))
            row = cur.fetchone()
            reserved = int(row["reserved"] if row and row["reserved"] is not None else 0)

        free = total_shares - reserved
        if free < 0:
            free = 0

        msg = f"Reset {t}: wolne {free}/{total_shares}, zarezerwowane {reserved}. Odbudowano {rebuilt}/{len(open_cc)} CC"
        if failed:
            fails = "; ".join([f"CC#{cid}: {why}" for cid, why in failed])
            msg += f"; Problemy: {fails}"

        return msg

    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        print(f"❌ Błąd resetu: {e}")
        return f"Błąd: {e}"
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def delete_covered_call(cc_id: int, confirm_delete: bool = False):
    """
    Usuwa CC:
      - zwalnia rezerwacje (usuwa wpisy w cc_lot_mappings oraz options_cc_reservations),
      - usuwa powiązane cashflow (ref_table='options_cc', ref_id=cc_id),
      - usuwa rekord z options_cc.
    NIE modyfikuje lots.quantity_open.
    """
    import sqlite3

    if not confirm_delete:
        return {'success': False, 'message': 'Brak potwierdzenia usunięcia'}

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Pobierz bazowe info (do komunikatu)
        cur.execute("SELECT ticker, contracts, status FROM options_cc WHERE id = ?", (cc_id,))
        row = cur.fetchone()
        if not row:
            try: conn.close()
            except Exception: pass
            return {'success': False, 'message': f'CC #{cc_id} nie istnieje'}

        ticker = row['ticker']
        contracts = int(row['contracts'] or 0)
        status = row['status']

        # Policz ile faktycznie jest zarezerwowane (dla raportu)
        cur.execute("SELECT COALESCE(SUM(shares_reserved),0) AS s FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
        r1 = cur.fetchone()
        shares_released = int(r1['s'] if r1 and r1['s'] is not None else 0)

        if shares_released == 0:
            cur.execute("SELECT COALESCE(SUM(qty_reserved),0) AS s FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))
            r2 = cur.fetchone()
            shares_released = int(r2['s'] if r2 and r2['s'] is not None else 0)

        # Usuwanie w transakcji
        try:
            cur.execute("BEGIN")

            # 1) Usuń rezerwacje (obie tabele — na wypadek, gdyby były wpisy w obu)
            cur.execute("DELETE FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
            cur.execute("DELETE FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))

            # 2) Usuń powiązane cashflow
            cur.execute("""
                DELETE FROM cashflows
                WHERE ref_table = 'options_cc' AND ref_id = ?
            """, (cc_id,))

            # 3) Usuń CC
            cur.execute("DELETE FROM options_cc WHERE id = ?", (cc_id,))

            cur.execute("COMMIT")
        except Exception as txe:
            try: cur.execute("ROLLBACK")
            except Exception: pass
            return {'success': False, 'message': f'Błąd usuwania (transakcja): {txe}'}

        try: conn.close()
        except Exception: pass

        return {
            'success': True,
            'message': f'Usunięto CC #{cc_id} ({ticker}); zwolniono {shares_released} akcji',
            'details': {
                'ticker': ticker,
                'shares_released': shares_released,
                'status_prev': status,
                'cashflows_deleted': True
            }
        }

    except Exception as e:
        if conn:
            try: conn.rollback()
            except Exception: pass
            try: conn.close()
            except Exception: pass
        return {'success': False, 'message': f'Błąd usuwania CC #{cc_id}: {str(e)}'}

def get_deletable_cc_list():
    """
    Pobiera listę CC które można usunąć (z informacjami o ryzyku).
    shares_reserved liczone realnie z cc_lot_mappings (fallback: options_cc_reservations).
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Subzapytania: suma rezerwacji per CC w obu tabelach
        query = """
        SELECT
            cc.id,
            cc.ticker,
            cc.contracts,
            cc.status,
            cc.premium_sell_usd,
            cc.premium_sell_pln,
            cc.open_date,
            cc.expiry_date,
            cc.close_date,
            CASE 
                WHEN cc.status = 'open' THEN 'UWAGA - zwolni rezerwacje'
                WHEN cc.status = 'expired' THEN 'Bezpieczne - już zamknięte'
                WHEN cc.status = 'bought_back' THEN 'Bezpieczne - już zamknięte'
                ELSE 'Sprawdź status'
            END AS delete_risk,
            COALESCE(m.reserved, 0) AS reserved_mappings,
            COALESCE(r.reserved, 0) AS reserved_simple
        FROM options_cc cc
        LEFT JOIN (
            SELECT cc_id, SUM(shares_reserved) AS reserved
            FROM cc_lot_mappings
            GROUP BY cc_id
        ) m ON m.cc_id = cc.id
        LEFT JOIN (
            SELECT cc_id, SUM(qty_reserved) AS reserved
            FROM options_cc_reservations
            GROUP BY cc_id
        ) r ON r.cc_id = cc.id
        ORDER BY cc.status, cc.open_date DESC, cc.id DESC
        """
        cur.execute(query)
        rows = cur.fetchall() or []

        cc_list = []
        for row in rows:
            reserved = int(row["reserved_mappings"] or 0)
            if reserved == 0:
                reserved = int(row["reserved_simple"] or 0)
            # jeśli nadal 0 (np. historyczne wpisy bez rezerwacji), pokaż nominalne contracts*100
            if reserved == 0:
                reserved = int(row["contracts"] or 0) * 100

            cc_list.append({
                'id': row['id'],
                'ticker': row['ticker'],
                'contracts': row['contracts'],
                'status': row['status'],
                'premium_sell_usd': row['premium_sell_usd'],
                'premium_sell_pln': row['premium_sell_pln'],
                'open_date': row['open_date'],
                'expiry_date': row['expiry_date'],
                'close_date': row['close_date'],
                'delete_risk': row['delete_risk'],
                'shares_reserved': reserved
            })

        return cc_list

    except Exception as e:
        print(f"Błąd pobierania listy CC: {e}")
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass



def update_covered_call(cc_id, **kwargs):
    """
    PUNKT 64: Edycja parametrów covered call

    Args:
        cc_id: ID covered call
        **kwargs: Pola do aktualizacji (strike_usd, expiry_date, premium_sell_usd)

    Returns:
        dict: Status operacji
    """
    import sqlite3
    from datetime import date as _date, datetime as _dt

    conn = None
    try:
        if not kwargs:
            return {'success': False, 'message': 'Brak parametrów do aktualizacji'}

        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        # pozwala czytać po nazwach kolumn
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Pobierz aktualne dane (rozszerzone o opłaty pod korektę cashflow)
        cur.execute("""
            SELECT id, ticker, contracts, status, premium_sell_usd, premium_sell_pln,
                   strike_usd, expiry_date, fx_open,
                   COALESCE(broker_fee_sell_usd, 0.0) AS broker_fee_sell_usd,
                   COALESCE(reg_fee_sell_usd, 0.0)     AS reg_fee_sell_usd
            FROM options_cc
            WHERE id = ?
        """, (cc_id,))
        r = cur.fetchone()
        if not r:
            try: conn.close()
            except Exception: pass
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione'}

        current_cc = {
            'id': r['id'],
            'ticker': r['ticker'],
            'contracts': int(r['contracts'] or 0),
            'status': r['status'],
            'premium_sell_usd': float(r['premium_sell_usd'] or 0.0),
            'premium_sell_pln': float(r['premium_sell_pln'] or 0.0) if r['premium_sell_pln'] is not None else None,
            'strike_usd': float(r['strike_usd'] or 0.0),
            'expiry_date': r['expiry_date'],
            'fx_open': float(r['fx_open'] or 0.0),
            'broker_fee_sell_usd': float(r['broker_fee_sell_usd'] or 0.0),
            'reg_fee_sell_usd': float(r['reg_fee_sell_usd'] or 0.0),
        }

        # Walidacja statusu
        if current_cc['status'] != 'open':
            try: conn.close()
            except Exception: pass
            return {'success': False, 'message': f"Nie można edytować zamkniętego CC (status: {current_cc['status']})"}

        # Dozwolone pola do update
        allowed_fields = {
            'strike_usd': 'strike_usd',
            'expiry_date': 'expiry_date',
            'premium_sell_usd': 'premium_sell_usd',
        }

        fields_to_update = []
        values = []
        changes_log = []

        # Normalizacja ewentualnej daty
        if 'expiry_date' in kwargs:
            val = kwargs['expiry_date']
            if hasattr(val, 'strftime'):
                kwargs['expiry_date'] = val.strftime('%Y-%m-%d')
            elif isinstance(val, str):
                # spróbuj sparsować popularne formaty i sprowadzić do ISO
                try:
                    kwargs['expiry_date'] = _dt.strptime(val, '%Y-%m-%d').date().isoformat()
                except Exception:
                    # jeśli nieznany format, zostaw jak jest (DB przyjmie tekst)
                    pass

        # Zbierz zmiany pól głównych
        for field, db_field in allowed_fields.items():
            if field in kwargs:
                new_value = kwargs[field]
                old_value = current_cc[db_field] if db_field in current_cc else None
                fields_to_update.append(f"{db_field} = ?")
                values.append(new_value)
                changes_log.append(f"{field}: {old_value} → {new_value}")

        if not fields_to_update:
            try: conn.close()
            except Exception: pass
            return {'success': False, 'message': 'Brak prawidłowych pól do aktualizacji'}

        # Jeśli zmieniono premium → przelicz premium_sell_pln (GROSS) oraz skoryguj cashflow (NETTO)
        if 'premium_sell_usd' in kwargs:
            new_premium_per_share_usd = float(kwargs['premium_sell_usd'])
            contracts = current_cc['contracts']
            fx_rate = current_cc['fx_open']

            # GROSS premium (całość, wg Twojej konwencji przechowywanej w options_cc)
            gross_premium_usd = new_premium_per_share_usd * contracts * 100.0
            premium_sell_pln = round(gross_premium_usd * fx_rate, 2)

            fields_to_update.append("premium_sell_pln = ?")
            values.append(premium_sell_pln)
            changes_log.append(f"premium_sell_pln: {current_cc['premium_sell_pln']} → {premium_sell_pln}")

            # Korekta cashflow 'option_premium' → NETTO (gross - fees)
            total_fees_usd = (current_cc['broker_fee_sell_usd'] or 0.0) + (current_cc['reg_fee_sell_usd'] or 0.0)
            net_premium_usd = gross_premium_usd - total_fees_usd
            amount_pln = round(net_premium_usd * fx_rate, 2)

            # Zaktualizuj wyłącznie powiązany cashflow premium (nie ruszamy buyback/others)
            cur.execute("""
                UPDATE cashflows
                SET amount_usd = ?, amount_pln = ?, fx_rate = ?
                WHERE ref_table = 'options_cc' AND ref_id = ? AND type = 'option_premium'
            """, (net_premium_usd, amount_pln, fx_rate, cc_id))

        # Dołóż znacznik aktualizacji
        fields_to_update.append("updated_at = CURRENT_TIMESTAMP")
        values.append(cc_id)

        # Wykonaj update w options_cc
        query = f"UPDATE options_cc SET {', '.join(fields_to_update)} WHERE id = ?"
        cur.execute(query, values)

        conn.commit()
        try: conn.close()
        except Exception: pass

        return {
            'success': True,
            'message': f'CC #{cc_id} zaktualizowane pomyślnie',
            'changes': changes_log
        }

    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd aktualizacji CC #{cc_id}: {str(e)}'}



def bulk_delete_covered_calls(cc_ids, confirm_bulk=False):
    """
    PUNKT 64: Masowe usuwanie covered calls
    
    Args:
        cc_ids: Lista ID do usunięcia  
        confirm_bulk: Potwierdzenie operacji masowej
    
    Returns:
        dict: Status operacji z szczegółami
    """
    try:
        if not cc_ids:
            return {'success': False, 'message': 'Brak CC do usunięcia'}
        
        if not confirm_bulk:
            return {'success': False, 'message': 'Operacja wymaga potwierdzenia'}
        
        results = {
            'success': True,
            'total_requested': len(cc_ids),
            'deleted': 0,
            'failed': 0,
            'shares_released': {},
            'errors': []
        }
        
        print(f"🗑️ BULK DELETE: Usuwanie {len(cc_ids)} CC...")
        
        for cc_id in cc_ids:
            delete_result = delete_covered_call(cc_id, confirm_delete=True)
            
            if delete_result['success']:
                results['deleted'] += 1
                details = delete_result['details']
                ticker = details['ticker']
                
                if ticker in results['shares_released']:
                    results['shares_released'][ticker] += details['shares_released']
                else:
                    results['shares_released'][ticker] = details['shares_released']
                
                print(f"   ✅ CC #{cc_id}: {ticker} - OK")
                
            else:
                results['failed'] += 1
                results['errors'].append(f"CC #{cc_id}: {delete_result['message']}")
                print(f"   ❌ CC #{cc_id}: {delete_result['message']}")
        
        if results['failed'] > 0:
            results['success'] = False
            results['message'] = f"Usunięto {results['deleted']}/{results['total_requested']} CC (błędy: {results['failed']})"
        else:
            results['message'] = f"Pomyślnie usunięto wszystkie {results['deleted']} CC"
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Błąd bulk delete: {str(e)}',
            'deleted': 0,
            'failed': len(cc_ids)
        }


def get_cc_edit_candidates():
    """
    Pobiera CC które można edytować (tylko otwarte as-of dziś) wraz z realną liczbą zarezerwowanych akcji.
    """
    import sqlite3
    from datetime import date as _date

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        today = _date.today().isoformat()

        # Tylko faktycznie otwarte CC na dziś (chronologia + status)
        cur.execute("""
            SELECT id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                   expiry_date, open_date, fx_open
            FROM options_cc
            WHERE status = 'open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
            ORDER BY open_date DESC, id DESC
        """, (today, today))
        rows = cur.fetchall() or []

        candidates = []
        for r in rows:
            cc_id = int(r["id"])
            contracts = int(r["contracts"] or 0)

            # Rzeczywiste rezerwacje dla tego CC
            cur.execute("SELECT COALESCE(SUM(shares_reserved),0) AS s FROM cc_lot_mappings WHERE cc_id = ?", (cc_id,))
            rr = cur.fetchone()
            shares_reserved = int(rr["s"] if rr and rr["s"] is not None else 0)

            if shares_reserved == 0:
                cur.execute("SELECT COALESCE(SUM(qty_reserved),0) AS s FROM options_cc_reservations WHERE cc_id = ?", (cc_id,))
                rr2 = cur.fetchone()
                shares_reserved = int(rr2["s"] if rr2 and rr2["s"] is not None else 0)

            if shares_reserved == 0:
                # historyczny fallback — nominalnie kontrakty * 100
                shares_reserved = contracts * 100

            candidates.append({
                'id': cc_id,
                'ticker': r['ticker'],
                'contracts': contracts,
                'strike_usd': float(r['strike_usd'] or 0),
                'premium_sell_usd': float(r['premium_sell_usd'] or 0),
                'premium_sell_pln': float(r['premium_sell_pln'] or 0) if r['premium_sell_pln'] is not None else None,
                'expiry_date': r['expiry_date'],
                'open_date': r['open_date'],
                'fx_open': float(r['fx_open'] or 0),
                'shares_reserved': shares_reserved
            })

        return candidates

    except Exception as e:
        print(f"Błąd pobierania CC do edycji: {e}")
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_cc_coverage_details(cc_id=None):
    """
    PUNKT 66: Pobiera szczegółowe informacje o pokryciu CC przez LOT-y
    - Źródłem prawdy o alokacjach są cc_lot_mappings (fallback: options_cc_reservations).
    - Gdy cc_id=None: bierzemy wszystkie CC faktycznie otwarte as-of dziś.
    """
    import sqlite3
    from datetime import date as _date, datetime as _dt

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        # czytanie po nazwach kolumn
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        today = _date.today().isoformat()

        # 1) Pobierz CC do analizy
        if cc_id:
            cur.execute("""
                SELECT id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                       open_date, expiry_date, fx_open
                FROM options_cc
                WHERE id = ? AND status = 'open'
            """, (cc_id,))
        else:
            cur.execute("""
                SELECT id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                       open_date, expiry_date, fx_open
                FROM options_cc
                WHERE status = 'open'
                  AND open_date <= ?
                  AND (close_date IS NULL OR close_date > ?)
                ORDER BY ticker, open_date, id
            """, (today, today))

        cc_rows = cur.fetchall() or []
        if not cc_rows:
            return []

        coverage_details = []

        for cc in cc_rows:
            _cc_id = int(cc["id"])
            ticker = cc["ticker"]
            contracts = int(cc["contracts"] or 0)
            shares_needed = contracts * 100
            strike_usd = float(cc["strike_usd"] or 0)
            premium_sell_usd = float(cc["premium_sell_usd"] or 0)
            premium_sell_pln = float(cc["premium_sell_pln"] or 0) if cc["premium_sell_pln"] is not None else 0.0
            open_date = cc["open_date"]
            expiry_date = cc["expiry_date"]
            fx_open = float(cc["fx_open"] or 0)

            # 2) Pobierz realne alokacje LOT-ów z cc_lot_mappings (fallback: options_cc_reservations)
            cur.execute("""
                SELECT m.lot_id, m.shares_reserved AS qty
                FROM cc_lot_mappings m
                WHERE m.cc_id = ?
                ORDER BY m.id
            """, (_cc_id,))
            map_rows = cur.fetchall() or []

            if not map_rows:
                cur.execute("""
                    SELECT r.lot_id, r.qty_reserved AS qty
                    FROM options_cc_reservations r
                    WHERE r.cc_id = ?
                    ORDER BY r.id
                """, (_cc_id,))
                map_rows = cur.fetchall() or []

            # 3) Dociągnij dane LOT-ów i policz koszt na akcję
            lot_allocations = []
            total_cost_basis = 0.0

            for mr in map_rows:
                lot_id = int(mr["lot_id"])
                qty = int(mr["qty"] or 0)
                if qty <= 0:
                    continue

                cur.execute("""
                    SELECT id, quantity_total, buy_date, buy_price_usd, fx_rate, cost_pln
                    FROM lots
                    WHERE id = ?
                """, (lot_id,))
                lot = cur.fetchone()
                if not lot:
                    continue

                qty_total = int(lot["quantity_total"] or 0)
                cost_pln = float(lot["cost_pln"] or 0.0) if lot["cost_pln"] is not None else 0.0
                cost_per_share_pln = (cost_pln / qty_total) if qty_total > 0 else 0.0
                total_cost_pln = round(cost_per_share_pln * qty, 2)
                total_cost_basis += total_cost_pln

                lot_allocations.append({
                    'lot_id': int(lot["id"]),
                    'buy_date': lot["buy_date"],
                    'buy_price_usd': float(lot["buy_price_usd"] or 0) if lot["buy_price_usd"] is not None else 0.0,
                    'fx_rate': float(lot["fx_rate"] or 0) if lot["fx_rate"] is not None else 0.0,
                    'cost_per_share_pln': round(cost_per_share_pln, 4),
                    'shares_allocated': qty,
                    'total_cost_pln': total_cost_pln
                })

            # 4) Daty + metryki czasowe
            def _to_date(x):
                if hasattr(x, 'strftime'):
                    return x
                if isinstance(x, str):
                    try:
                        return _dt.strptime(x, '%Y-%m-%d').date()
                    except Exception:
                        return None
                return None

            open_date_obj = _to_date(open_date)
            expiry_date_obj = _to_date(expiry_date)
            today_obj = _date.today()

            days_to_expiry = (expiry_date_obj - today_obj).days if expiry_date_obj else None
            days_held = (today_obj - open_date_obj).days + 1 if open_date_obj else None
            total_days = (expiry_date_obj - open_date_obj).days + 1 if (open_date_obj and expiry_date_obj) else None

            # 5) Yields
            premium_yield_pct = (premium_sell_pln / total_cost_basis * 100.0) if total_cost_basis > 0 else 0.0
            annualized_yield_pct = (premium_yield_pct * 365.0 / total_days) if (total_days and total_days > 0) else 0.0

            coverage_details.append({
                'cc_id': _cc_id,
                'ticker': ticker,
                'contracts': contracts,
                'shares_needed': shares_needed,
                'strike_usd': strike_usd,
                'premium_sell_usd': premium_sell_usd,
                'premium_sell_pln': premium_sell_pln,
                'open_date': open_date,
                'expiry_date': expiry_date,
                'fx_open': fx_open,
                'days_to_expiry': days_to_expiry if days_to_expiry is not None else 0,
                'days_held': days_held if days_held is not None else 0,
                'total_days': total_days if total_days is not None else 0,
                'lot_allocations': lot_allocations,
                'total_cost_basis': round(total_cost_basis, 2),
                'premium_yield_pct': round(premium_yield_pct, 4) if premium_yield_pct else 0.0,
                'annualized_yield_pct': round(annualized_yield_pct, 4) if annualized_yield_pct else 0.0
            })

        return coverage_details

    except Exception as e:
        print(f"Błąd get_cc_coverage_details: {e}")
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass



def get_portfolio_cc_summary():
    """
    PUNKT 66: Podsumowanie całego portfela CC (as-of dziś, z realnymi rezerwacjami).
    """
    import sqlite3
    from datetime import date as _date

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {}

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        today = _date.today().isoformat()

        # --- OPEN / CLOSED counts & sums (OPEN as-of today) ---
        cur.execute("""
            SELECT COUNT(*) AS open_cc_count,
                   COALESCE(SUM(contracts),0) AS total_open_contracts,
                   COALESCE(SUM(premium_sell_pln),0) AS total_open_premium_pln
            FROM options_cc
            WHERE status='open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
        """, (today, today))
        r_open = cur.fetchone()
        open_cc_count = int(r_open["open_cc_count"] or 0)
        total_open_contracts = int(r_open["total_open_contracts"] or 0)
        total_open_premium_pln = float(r_open["total_open_premium_pln"] or 0.0)

        cur.execute("""
            SELECT COUNT(*) AS closed_cc_count,
                   COALESCE(SUM(pl_pln),0) AS total_realized_pl_pln
            FROM options_cc
            WHERE status <> 'open'
        """)
        r_closed = cur.fetchone()
        closed_cc_count = int(r_closed["closed_cc_count"] or 0)
        total_realized_pl_pln = float(r_closed["total_realized_pl_pln"] or 0.0)

        # --- REAL reserved shares for OPEN CC (as-of today) ---
        cur.execute("""
            SELECT UPPER(cc.ticker) AS ticker,
                   COALESCE(SUM(m.shares_reserved),0) AS reserved
            FROM cc_lot_mappings m
            JOIN options_cc cc ON cc.id = m.cc_id
            WHERE cc.status='open'
              AND cc.open_date <= ?
              AND (cc.close_date IS NULL OR cc.close_date > ?)
            GROUP BY UPPER(cc.ticker)
        """, (today, today))
        reserved_map = {row["ticker"]: int(row["reserved"] or 0) for row in (cur.fetchall() or [])}

        # Fallback do options_cc_reservations dla tickerów z 0 w mappings
        need_fallback = []
        if open_cc_count > 0:
            cur.execute("""
                SELECT DISTINCT UPPER(ticker) AS ticker
                FROM options_cc
                WHERE status='open'
                  AND open_date <= ?
                  AND (close_date IS NULL OR close_date > ?)
            """, (today, today))
            open_tickers = [row["ticker"] for row in (cur.fetchall() or [])]
            need_fallback = [t for t in open_tickers if reserved_map.get(t, 0) == 0]

        if need_fallback:
            cur.execute(f"""
                SELECT UPPER(cc.ticker) AS ticker,
                       COALESCE(SUM(r.qty_reserved),0) AS reserved
                FROM options_cc_reservations r
                JOIN options_cc cc ON cc.id = r.cc_id
                WHERE cc.status='open'
                  AND cc.open_date <= ?
                  AND (cc.close_date IS NULL OR cc.close_date > ?)
                  AND UPPER(cc.ticker) IN ({",".join(["?"]*len(need_fallback))})
                GROUP BY UPPER(cc.ticker)
            """, [today, today, *need_fallback])
            for row in (cur.fetchall() or []):
                t = row["ticker"]
                reserved_map[t] = int(row["reserved"] or 0)

        # Suma rezerwacji (jeśli brak — nominalnie 0; nie używamy contracts*100 do sumy globalnej)
        total_shares_reserved = sum(reserved_map.values()) if reserved_map else 0

        # --- Stats per ticker (OPEN as-of today) ---
        cur.execute("""
            SELECT UPPER(ticker) AS ticker,
                   COUNT(*) AS cc_count,
                   COALESCE(SUM(contracts),0) AS total_contracts,
                   COALESCE(SUM(premium_sell_pln),0) AS total_premium_pln
            FROM options_cc
            WHERE status='open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
            GROUP BY UPPER(ticker)
            ORDER BY UPPER(ticker)
        """, (today, today))
        rows = cur.fetchall() or []

        ticker_stats = []
        for row in rows:
            t = row["ticker"]
            contracts = int(row["total_contracts"] or 0)
            real_reserved = int(reserved_map.get(t, 0))
            ticker_stats.append({
                'ticker': t,
                'cc_count': int(row["cc_count"] or 0),
                'total_contracts': contracts,
                'shares_reserved': real_reserved,                # realnie zarezerwowane
                'total_premium_pln': float(row["total_premium_pln"] or 0.0)
            })

        return {
            'open_cc_count': open_cc_count,
            'closed_cc_count': closed_cc_count,
            'total_open_contracts': total_open_contracts,
            'total_shares_reserved': total_shares_reserved,
            'total_open_premium_pln': total_open_premium_pln,
            'total_realized_pl_pln': total_realized_pl_pln,
            'ticker_stats': ticker_stats
        }

    except Exception as e:
        print(f"Błąd get_portfolio_cc_summary: {e}")
        return {}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

        
def get_closed_cc_analysis():
    """
    PUNKT 67: Szczegółowa analiza zamkniętych CC z P/L
    - P/L w PLN: expired → premium_sell_pln; bought_back → premium_sell_pln - premium_buyback_pln
    - Koszt bazowy: suma (cost_pln/quantity_total * qty_alloc) po realnych alokacjach z cc_lot_mappings (fallback: options_cc_reservations)
    - Annualizowanie wg dni od open_date do close_date (lub expiry_date, jeśli close_date brak)
    """
    import sqlite3
    from datetime import datetime as _dt, date as _date

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        # Dostęp kolumnami po nazwach
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Pobierz zamknięte CC
        cur.execute("""
            SELECT id, ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                   premium_buyback_usd, premium_buyback_pln, open_date, close_date, expiry_date,
                   status, fx_open, fx_close, pl_pln, created_at
            FROM options_cc
            WHERE status IN ('bought_back', 'expired')
            ORDER BY close_date DESC, ticker, id DESC
        """)
        rows = cur.fetchall() or []

        out = []

        for r in rows:
            cc_id = int(r["id"])
            ticker = r["ticker"]
            contracts = int(r["contracts"] or 0)
            shares_nominal = contracts * 100
            strike_usd = float(r["strike_usd"] or 0.0)

            premium_sell_usd = float(r["premium_sell_usd"] or 0.0)
            premium_sell_pln = float(r["premium_sell_pln"] or 0.0) if r["premium_sell_pln"] is not None else 0.0
            premium_buyback_usd = float(r["premium_buyback_usd"] or 0.0) if r["premium_buyback_usd"] is not None else 0.0
            premium_buyback_pln = float(r["premium_buyback_pln"] or 0.0) if r["premium_buyback_pln"] is not None else 0.0

            status = r["status"]
            fx_open = float(r["fx_open"] or 0.0)
            fx_close = float(r["fx_close"] or 0.0) if r["fx_close"] is not None else fx_open

            open_date = r["open_date"]
            close_date = r["close_date"]
            expiry_date = r["expiry_date"]

            # Daty -> date
            def _to_date(x):
                if not x:
                    return None
                if hasattr(x, "strftime"):
                    return x
                if isinstance(x, str):
                    try:
                        return _dt.strptime(x, "%Y-%m-%d").date()
                    except Exception:
                        return None
                return None

            od = _to_date(open_date)
            cd = _to_date(close_date) or _to_date(expiry_date)  # na wszelki wypadek
            today = _date.today()
            days_held = (cd - od).days if (od and cd) else 0
            if days_held <= 0:
                days_held = 1  # uniknij dzielenia przez 0

            # Rzeczywiste alokacje dla CC: najpierw cc_lot_mappings, fallback options_cc_reservations
            cur.execute("SELECT lot_id, COALESCE(SUM(shares_reserved),0) AS qty FROM cc_lot_mappings WHERE cc_id=? GROUP BY lot_id", (cc_id,))
            alloc_rows = cur.fetchall() or []

            if not alloc_rows:
                cur.execute("SELECT lot_id, COALESCE(SUM(qty_reserved),0) AS qty FROM options_cc_reservations WHERE cc_id=? GROUP BY lot_id", (cc_id,))
                alloc_rows = cur.fetchall() or []

            # Zbuduj pokrycie per LOT + policz koszt bazowy
            lot_allocations = []
            total_cost_basis_pln = 0.0
            total_alloc_shares = 0

            for ar in alloc_rows:
                lot_id = int(ar["lot_id"])
                qty = int(ar["qty"] or 0)
                if qty <= 0:
                    continue
                # Dane LOT-a
                cur.execute("""SELECT id, quantity_total, buy_date, buy_price_usd, fx_rate, cost_pln
                               FROM lots WHERE id = ?""", (lot_id,))
                lot = cur.fetchone()
                if not lot:
                    continue
                qty_total = int(lot["quantity_total"] or 0)
                cost_pln = float(lot["cost_pln"] or 0.0) if lot["cost_pln"] is not None else 0.0
                cps_pln = (cost_pln / qty_total) if qty_total > 0 else 0.0
                total_cost_pln = round(cps_pln * qty, 2)

                total_cost_basis_pln += total_cost_pln
                total_alloc_shares += qty

                lot_allocations.append({
                    "lot_id": int(lot["id"]),
                    "buy_date": lot["buy_date"],
                    "buy_price_usd": float(lot["buy_price_usd"] or 0.0) if lot["buy_price_usd"] is not None else 0.0,
                    "fx_rate": float(lot["fx_rate"] or 0.0) if lot["fx_rate"] is not None else 0.0,
                    "cost_per_share_pln": round(cps_pln, 4),
                    "shares_allocated": qty,
                    "total_cost_pln": total_cost_pln,
                })

            # Jeśli brak alokacji (historyczne rekordy), załóż nominalne udziały i koszt bazowy ~0 (yield wtedy 0)
            if total_alloc_shares == 0:
                total_alloc_shares = shares_nominal

            # P/L w PLN (jeśli brak – wylicz)
            recorded_pl_pln = float(r["pl_pln"] or 0.0) if r["pl_pln"] is not None else None
            if recorded_pl_pln is None or recorded_pl_pln == 0.0:
                if status == "expired":
                    pl_pln = premium_sell_pln
                else:  # bought_back
                    pl_pln = premium_sell_pln - premium_buyback_pln
            else:
                pl_pln = recorded_pl_pln

            # Net premium (info pomocnicze; w USD/PLN)
            if status == "expired":
                net_premium_usd = premium_sell_usd
                net_premium_pln = premium_sell_pln
                outcome_emoji = "🏆"
                outcome_text = "Expired (Max Profit)"
            else:
                net_premium_usd = premium_sell_usd - premium_buyback_usd
                net_premium_pln = premium_sell_pln - premium_buyback_pln
                outcome_emoji = "🔄"
                outcome_text = "Bought Back"

            # Yields na realnym koszcie bazowym
            premium_yield_pct = (net_premium_pln / total_cost_basis_pln * 100.0) if total_cost_basis_pln > 0 else 0.0
            annualized_yield_pct = (premium_yield_pct * 365.0 / days_held) if days_held > 0 else 0.0

            out.append({
                "cc_id": cc_id,
                "ticker": ticker,
                "contracts": contracts,
                "shares": total_alloc_shares,             # realnie policzone z alokacji (fallback: nominal)
                "strike_usd": strike_usd,
                "premium_sell_usd": premium_sell_usd,
                "premium_sell_pln": premium_sell_pln,
                "premium_buyback_usd": premium_buyback_usd,
                "premium_buyback_pln": premium_buyback_pln,
                "open_date": open_date,
                "close_date": close_date,
                "expiry_date": expiry_date,
                "status": status,
                "fx_open": fx_open,
                "fx_close": fx_close or fx_open,
                "pl_pln": pl_pln,                         # skorygowany/wyliczony P&L w PLN
                "created_at": r["created_at"],
                # metryki
                "days_held": days_held,
                "net_premium_usd": net_premium_usd,
                "net_premium_pln": net_premium_pln,
                "outcome_emoji": outcome_emoji,
                "outcome_text": outcome_text,
                "estimated_total_cost": round(total_cost_basis_pln, 2),  # to już realny koszt bazowy
                "premium_yield_pct": round(premium_yield_pct, 4),
                "annualized_yield_pct": round(annualized_yield_pct, 4),
                "lot_allocations": lot_allocations,
            })

        return out

    except Exception as e:
        print(f"Błąd get_closed_cc_analysis: {e}")
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass



def get_cc_performance_summary():
    """
    PUNKT 67: Podsumowanie performance wszystkich CC (z wyliczanym P/L dla braków).
    - P/L używany do statystyk: IF pl_pln IS NULL THEN
        CASE status WHEN 'expired' THEN premium_sell_pln
                    WHEN 'bought_back' THEN premium_sell_pln - COALESCE(premium_buyback_pln,0)
        END
      ELSE pl_pln END
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {}

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # --- GLOBAL STATS (zamknięte CC) ---
        cur.execute("""
            SELECT
                COUNT(*)                                                   AS total_closed,
                SUM(CASE WHEN status='expired'     THEN 1 ELSE 0 END)      AS expired_count,
                SUM(CASE WHEN status='bought_back' THEN 1 ELSE 0 END)      AS buyback_count,
                SUM(
                    CASE
                        WHEN pl_pln IS NULL THEN
                            CASE status
                                WHEN 'expired'     THEN COALESCE(premium_sell_pln,0)
                                WHEN 'bought_back' THEN COALESCE(premium_sell_pln,0) - COALESCE(premium_buyback_pln,0)
                                ELSE 0
                            END
                        ELSE pl_pln
                    END
                )                                                          AS total_realized_pl,
                AVG(
                    CASE
                        WHEN pl_pln IS NULL THEN
                            CASE status
                                WHEN 'expired'     THEN COALESCE(premium_sell_pln,0)
                                WHEN 'bought_back' THEN COALESCE(premium_sell_pln,0) - COALESCE(premium_buyback_pln,0)
                                ELSE 0
                            END
                        ELSE pl_pln
                    END
                )                                                          AS avg_pl_per_cc,
                MIN(
                    CASE
                        WHEN pl_pln IS NULL THEN
                            CASE status
                                WHEN 'expired'     THEN COALESCE(premium_sell_pln,0)
                                WHEN 'bought_back' THEN COALESCE(premium_sell_pln,0) - COALESCE(premium_buyback_pln,0)
                                ELSE 0
                            END
                        ELSE pl_pln
                    END
                )                                                          AS worst_pl,
                MAX(
                    CASE
                        WHEN pl_pln IS NULL THEN
                            CASE status
                                WHEN 'expired'     THEN COALESCE(premium_sell_pln,0)
                                WHEN 'bought_back' THEN COALESCE(premium_sell_pln,0) - COALESCE(premium_buyback_pln,0)
                                ELSE 0
                            END
                        ELSE pl_pln
                    END
                )                                                          AS best_pl
            FROM options_cc
            WHERE status IN ('bought_back','expired')
        """)
        g = cur.fetchone()

        # --- PER TICKER STATS ---
        cur.execute("""
            SELECT
                UPPER(ticker)                                              AS ticker,
                COUNT(*)                                                   AS cc_count,
                SUM(
                    CASE
                        WHEN pl_pln IS NULL THEN
                            CASE status
                                WHEN 'expired'     THEN COALESCE(premium_sell_pln,0)
                                WHEN 'bought_back' THEN COALESCE(premium_sell_pln,0) - COALESCE(premium_buyback_pln,0)
                                ELSE 0
                            END
                        ELSE pl_pln
                    END
                )                                                          AS total_pl,
                AVG(
                    CASE
                        WHEN pl_pln IS NULL THEN
                            CASE status
                                WHEN 'expired'     THEN COALESCE(premium_sell_pln,0)
                                WHEN 'bought_back' THEN COALESCE(premium_sell_pln,0) - COALESCE(premium_buyback_pln,0)
                                ELSE 0
                            END
                        ELSE pl_pln
                    END
                )                                                          AS avg_pl,
                SUM(CASE WHEN status='expired'     THEN 1 ELSE 0 END)      AS expired_count,
                SUM(CASE WHEN status='bought_back' THEN 1 ELSE 0 END)      AS buyback_count
            FROM options_cc
            WHERE status IN ('bought_back','expired')
            GROUP BY UPPER(ticker)
            ORDER BY total_pl DESC, ticker ASC
        """)
        rows = cur.fetchall() or []

        ticker_performance = []
        for r in rows:
            cc_count = int(r["cc_count"] or 0)
            expired_count = int(r["expired_count"] or 0)
            ticker_performance.append({
                'ticker': r['ticker'],
                'cc_count': cc_count,
                'total_pl': float(r['total_pl'] or 0.0),
                'avg_pl': float(r['avg_pl'] or 0.0),
                'expired_count': expired_count,
                'buyback_count': int(r['buyback_count'] or 0),
                # zachowuję Twój wcześniejszy sposób liczenia „win_rate”
                'win_rate': (expired_count / cc_count * 100.0) if cc_count > 0 else 0.0
            })

        if not g:
            return {
                'total_closed': 0,
                'expired_count': 0,
                'buyback_count': 0,
                'total_realized_pl': 0.0,
                'avg_pl_per_cc': 0.0,
                'worst_pl': 0.0,
                'best_pl': 0.0,
                'ticker_performance': ticker_performance
            }

        summary = {
            'total_closed': int(g['total_closed'] or 0),
            'expired_count': int(g['expired_count'] or 0),
            'buyback_count': int(g['buyback_count'] or 0),
            'total_realized_pl': float(g['total_realized_pl'] or 0.0),
            'avg_pl_per_cc': float(g['avg_pl_per_cc'] or 0.0),
            'worst_pl': float(g['worst_pl'] or 0.0),
            'best_pl': float(g['best_pl'] or 0.0),
            'ticker_performance': ticker_performance
        }
        return summary

    except Exception as e:
        print(f"Błąd get_cc_performance_summary: {e}")
        return {}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_reservations_diagnostics():
    """
    Diagnostyka rezerwacji pod otwarte CC (as-of dziś):
      - per ticker: required_reserved (kontrakty*100) vs actual_reserved (z tabel rezerwacji),
      - per CC: oczekiwana rezerwa vs zmapowana w cc_lot_mappings (fallback: options_cc_reservations).

    Zwraca dict:
      {
        'success': True,
        'has_cc_lot_mappings': bool,
        'has_options_cc_reservations': bool,
        'tickers': [{'ticker','required_reserved','actual_reserved','delta'}...],
        'ccs': [{
            'id','ticker','open_date',
            'expected_reserved',
            'mapped_reserved': int,
            'mapped_details': [{'lot_id','qty_reserved'}...]
        }...]
      }
    """
    import sqlite3
    from datetime import date as _date

    conn = get_connection()
    if not conn:
        return {'success': False, 'message': 'Brak połączenia z bazą',
                'has_cc_lot_mappings': False, 'has_options_cc_reservations': False}

    try:
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        today = _date.today().isoformat()

        # Czy istnieją tabele rezerwacyjne?
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings' LIMIT 1")
        has_cc_map = cur.fetchone() is not None
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='options_cc_reservations' LIMIT 1")
        has_simple_map = cur.fetchone() is not None

        out = {
            'success': True,
            'has_cc_lot_mappings': has_cc_map,
            'has_options_cc_reservations': has_simple_map,
            'tickers': [],
            'ccs': []
        }

        # TICKERY z faktycznie otwartymi CC as-of dziś
        cur.execute("""
            SELECT DISTINCT UPPER(ticker) AS ticker
            FROM options_cc
            WHERE status='open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
            ORDER BY UPPER(ticker)
        """, (today, today))
        tickers = [r['ticker'] for r in (cur.fetchall() or [])]

        # Per-ticker: required (contracts*100) i actual z mapowań
        for t in tickers:
            # required = sum(contracts)*100
            cur.execute("""
                SELECT COALESCE(SUM(contracts),0) * 100 AS required_reserved
                FROM options_cc
                WHERE status='open'
                  AND open_date <= ?
                  AND (close_date IS NULL OR close_date > ?)
                  AND UPPER(ticker)=?
            """, (today, today, t))
            required = int((cur.fetchone() or {}) .get('required_reserved', 0) or 0)

            # actual z cc_lot_mappings
            actual = 0
            if has_cc_map:
                cur.execute("""
                    SELECT COALESCE(SUM(m.shares_reserved),0) AS reserved
                    FROM cc_lot_mappings m
                    JOIN options_cc cc ON cc.id = m.cc_id
                    WHERE cc.status='open'
                      AND cc.open_date <= ?
                      AND (cc.close_date IS NULL OR cc.close_date > ?)
                      AND UPPER(cc.ticker)=?
                """, (today, today, t))
                row = cur.fetchone()
                actual = int(row['reserved'] if row and row['reserved'] is not None else 0)

            # fallback do options_cc_reservations
            if actual == 0 and has_simple_map:
                cur.execute("""
                    SELECT COALESCE(SUM(r.qty_reserved),0) AS reserved
                    FROM options_cc_reservations r
                    JOIN options_cc cc ON cc.id = r.cc_id
                    WHERE cc.status='open'
                      AND cc.open_date <= ?
                      AND (cc.close_date IS NULL OR cc.close_date > ?)
                      AND UPPER(cc.ticker)=?
                """, (today, today, t))
                row = cur.fetchone()
                actual = int(row['reserved'] if row and row['reserved'] is not None else 0)

            out['tickers'].append({
                'ticker': t,
                'required_reserved': required,
                'actual_reserved': actual,
                'delta': actual - required
            })

        # Per-CC: otwarte as-of dziś
        cur.execute("""
            SELECT id, UPPER(ticker) AS ticker, contracts, open_date
            FROM options_cc
            WHERE status='open'
              AND open_date <= ?
              AND (close_date IS NULL OR close_date > ?)
            ORDER BY open_date, id
        """, (today, today))
        cc_rows = cur.fetchall() or []

        for r in cc_rows:
            cid = int(r['id'])
            t = r['ticker']
            expected = int(r['contracts'] or 0) * 100

            mapped = 0
            details = []

            if has_cc_map:
                cur.execute("""
                    SELECT lot_id, COALESCE(SUM(shares_reserved),0) AS qty
                    FROM cc_lot_mappings
                    WHERE cc_id=?
                    GROUP BY lot_id
                    ORDER BY lot_id
                """, (cid,))
                rows = cur.fetchall() or []
                mapped = sum(int(x['qty'] or 0) for x in rows)
                details = [{'lot_id': int(x['lot_id']), 'qty_reserved': int(x['qty'] or 0)} for x in rows]

            if mapped == 0 and has_simple_map:
                cur.execute("""
                    SELECT lot_id, COALESCE(SUM(qty_reserved),0) AS qty
                    FROM options_cc_reservations
                    WHERE cc_id=?
                    GROUP BY lot_id
                    ORDER BY lot_id
                """, (cid,))
                rows = cur.fetchall() or []
                mapped = sum(int(x['qty'] or 0) for x in rows)
                details = [{'lot_id': int(x['lot_id']), 'qty_reserved': int(x['qty'] or 0)} for x in rows]

            out['ccs'].append({
                'id': cid,
                'ticker': t,
                'open_date': r['open_date'],
                'expected_reserved': expected,
                'mapped_reserved': mapped,
                'mapped_details': details
            })

        return out

    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd diagnostyki: {e}',
                'has_cc_lot_mappings': False, 'has_options_cc_reservations': False}
    finally:
        try:
            conn.close()
        except Exception:
            pass


def buyback_covered_call_with_fees(cc_id, buyback_price_usd, buyback_date, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    Buyback CC:
      1) zamyka CC jako 'bought_back' (PL po prowizjach),
      2) zwalnia rezerwacje (cc_lot_mappings / options_cc_reservations) i ZWIĘKSZA lots.quantity_open,
      3) ma FIFO fallback jeśli mapowań brakuje/nie sumują się do pełnej ilości,
      4) tworzy cashflow 'option_buyback'.
    """
    import sqlite3
    from datetime import datetime as _dt

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # — Pobierz CC
        cur.execute("""
            SELECT id, ticker, contracts, premium_sell_usd, premium_sell_pln, open_date, expiry_date,
                   status, fx_open
            FROM options_cc WHERE id = ?
        """, (cc_id,))
        r = cur.fetchone()
        if not r:
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione'}

        if (r['status'] or '') != 'open':
            return {'success': False, 'message': f"CC #{cc_id} już zamknięte (status: {r['status']})"}

        ticker            = r['ticker']
        contracts         = int(r['contracts'] or 0)
        prem_sell_usd     = float(r['premium_sell_usd'] or 0.0)
        prem_sell_pln     = float(r['premium_sell_pln'] or 0.0)
        open_date         = r['open_date']
        expiry_date       = r['expiry_date']
        fx_open           = float(r['fx_open'] or 0.0)

        # — Daty/FX
        if hasattr(buyback_date, 'strftime'):
            buyback_date_str = buyback_date.strftime('%Y-%m-%d')
        elif isinstance(buyback_date, str):
            try:
                buyback_date_str = _dt.strptime(buyback_date, '%Y-%m-%d').date().isoformat()
            except Exception:
                buyback_date_str = buyback_date
        else:
            return {'success': False, 'message': 'Nieprawidłowy typ buyback_date'}

        try:
            import pandas as pd
            fx_close_date = (pd.to_datetime(buyback_date_str) - pd.DateOffset(days=1)).strftime('%Y-%m-%d')
        except Exception:
            fx_close_date = buyback_date_str

        fx_close = get_fx_rate_for_date(fx_close_date) or fx_open
        if not fx_close or fx_close <= 0:
            return {'success': False, 'message': f'Brak kursu NBP (ani fallback) dla {fx_close_date}'}

        # — Kalkulacje finansowe
        shares_to_release   = contracts * 100
        premium_buyback_usd = float(buyback_price_usd) * shares_to_release
        fees_usd            = float(broker_fee_usd or 0.0) + float(reg_fee_usd or 0.0)
        total_buyback_usd   = premium_buyback_usd + fees_usd
        premium_buyback_pln = round(premium_buyback_usd * fx_close, 2)
        buyback_cost_pln    = round(total_buyback_usd * fx_close, 2)
        pl_pln              = round(prem_sell_pln - buyback_cost_pln, 2)

        outer_tx = getattr(conn, 'in_transaction', False)
        cur.execute("SAVEPOINT sp_bb")

        try:
            # 1) Zmień status CC → bought_back
            cur.execute("""
                UPDATE options_cc
                SET status='bought_back',
                    close_date=?,
                    premium_buyback_usd=?,
                    premium_buyback_pln=?,
                    fx_close=?,
                    broker_fee_buyback_usd=?,
                    reg_fee_buyback_usd=?,
                    total_fees_buyback_pln=?,
                    pl_pln=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                buyback_date_str, premium_buyback_usd, premium_buyback_pln, fx_close,
                float(broker_fee_usd or 0.0), float(reg_fee_usd or 0.0), round(fees_usd * fx_close, 2),
                pl_pln, cc_id
            ))

            # 2) ZWOLNIJ AKCJE: mapowania → +lots.quantity_open
            released = 0

            # Priorytet: cc_lot_mappings
            cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'")
            if cur.fetchone():
                cur.execute("""SELECT id, lot_id, shares_reserved
                               FROM cc_lot_mappings
                               WHERE cc_id=? ORDER BY id""", (cc_id,))
                for m in cur.fetchall() or []:
                    if released >= shares_to_release: break
                    mid = int(m['id']); lot_id = int(m['lot_id']); qty = int(m['shares_reserved'] or 0)
                    if qty <= 0: continue
                    take = min(qty, shares_to_release - released)
                    new_qty = qty - take
                    if new_qty > 0:
                        cur.execute("UPDATE cc_lot_mappings SET shares_reserved=? WHERE id=?", (new_qty, mid))
                    else:
                        cur.execute("DELETE FROM cc_lot_mappings WHERE id=?", (mid,))
                    cur.execute("UPDATE lots SET quantity_open = quantity_open + ? WHERE id = ?", (take, lot_id))
                    released += take

            # Fallback: options_cc_reservations
            if released < shares_to_release:
                cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='options_cc_reservations'")
                if cur.fetchone():
                    cur.execute("""SELECT id, lot_id, qty_reserved
                                   FROM options_cc_reservations
                                   WHERE cc_id=? ORDER BY id""", (cc_id,))
                    for rm in cur.fetchall() or []:
                        if released >= shares_to_release: break
                        rid = int(rm['id']); lot_id = int(rm['lot_id']); qty = int(rm['qty_reserved'] or 0)
                        if qty <= 0: continue
                        take = min(qty, shares_to_release - released)
                        new_qty = qty - take
                        if new_qty > 0:
                            cur.execute("UPDATE options_cc_reservations SET qty_reserved=? WHERE id=?", (new_qty, rid))
                        else:
                            cur.execute("DELETE FROM options_cc_reservations WHERE id=?", (rid,))
                        cur.execute("UPDATE lots SET quantity_open = quantity_open + ? WHERE id = ?", (take, lot_id))
                        released += take

            # Ostateczny fallback: FIFO (gdy mapowania nie pokryły wszystkiego)
            if released < shares_to_release:
                need = shares_to_release - released
                cur.execute("""SELECT id, quantity_total, quantity_open
                               FROM lots
                               WHERE UPPER(ticker)=?
                               ORDER BY buy_date ASC, id ASC""", (ticker.upper(),))
                for lot_id, qty_total, qty_open in cur.fetchall() or []:
                    if need <= 0: break
                    potentially_blocked = int(qty_total or 0) - int(qty_open or 0)
                    if potentially_blocked <= 0: continue
                    take = min(potentially_blocked, need)
                    cur.execute("UPDATE lots SET quantity_open = quantity_open + ? WHERE id = ?", (take, lot_id))
                    need -= take
                    released += take

            # 3) Cashflow (wydatek)
            desc = (f"Buyback CC #{cc_id} {contracts}x @{float(buyback_price_usd):.4f} | "
                    f"fees ${fees_usd:.2f} | NBP D-1: {fx_close_date}")
            cur.execute("""
                INSERT INTO cashflows (type, amount_usd, date, fx_rate, amount_pln, description, ref_table, ref_id)
                VALUES ('option_buyback', ?, ?, ?, ?, ?, 'options_cc', ?)
            """, (-total_buyback_usd, buyback_date_str, fx_close, -round(total_buyback_usd * fx_close, 2), desc, cc_id))

            cur.execute("RELEASE SAVEPOINT sp_bb")
            if not outer_tx:
                conn.commit()
            conn.close()

            return {
                'success': True,
                'message': f'Odkupiono {contracts}/{contracts} kontraktów CC #{cc_id}. Rezerwacje zmniejszone o {released} akcji.',
                'shares_released': int(released),     # 🔑 oczekiwane przez UI
                'fx_close': fx_close,
                'fx_close_date': fx_close_date,
                'pl_pln': pl_pln
            }

        except Exception as txe:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT sp_bb")
                cur.execute("RELEASE SAVEPOINT sp_bb")
            except Exception:
                pass
            try:
                if not outer_tx:
                    conn.rollback()
                conn.close()
            except Exception:
                pass
            return {'success': False, 'message': f'Błąd buyback: {txe}'}

    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd buyback: {str(e)}'}


def cleanup_orphaned_cashflow():
    """
    Usuwa cashflow, które wskazują na nieistniejące rekordy w options_cc (ref_table='options_cc').
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Anti-join (bezpieczniej niż NOT IN z możliwymi NULL-ami)
        cur.execute("""
            SELECT c.id, c.description, c.amount_usd, c.date
            FROM cashflows c
            LEFT JOIN options_cc oc ON oc.id = c.ref_id
            WHERE c.ref_table = 'options_cc'
              AND c.ref_id IS NOT NULL
              AND oc.id IS NULL
        """)
        orphaned = cur.fetchall() or []

        if not orphaned:
            return {
                'success': True,
                'message': 'Nie znaleziono orphaned cashflow',
                'deleted_count': 0,
                'deleted_descriptions': []
            }

        deleted_descriptions = []
        try:
            cur.execute("BEGIN")
            for r in orphaned:
                cf_id = r["id"]
                desc = r["description"] if r["description"] is not None else "(brak opisu)"
                amt = r["amount_usd"] if r["amount_usd"] is not None else 0.0
                dt  = r["date"] if r["date"] is not None else "(brak daty)"

                cur.execute("DELETE FROM cashflows WHERE id = ?", (cf_id,))
                try:
                    deleted_descriptions.append(f"{dt}: {desc} (${float(amt):.2f})")
                except Exception:
                    deleted_descriptions.append(f"{dt}: {desc} (kwota n/d)")

            cur.execute("COMMIT")
        except Exception as txe:
            try: cur.execute("ROLLBACK")
            except Exception: pass
            return {'success': False, 'message': f'Błąd transakcji cleanup: {txe}'}

        return {
            'success': True,
            'message': f'Usunięto {len(orphaned)} orphaned cashflow',
            'deleted_count': len(orphaned),
            'deleted_descriptions': deleted_descriptions
        }

    except Exception as e:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd cleanup: {str(e)}'}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

def check_cc_cashflow_integrity():
    """
    Sprawdza integralność między CC a cashflow
    """
    try:
        conn = get_connection()
        if not conn:
            return {'issues': ['Brak połączenia z bazą']}
        
        cursor = conn.cursor()
        issues = []
        
        # 1. CC bez cashflow
        cursor.execute("""
            SELECT id, ticker, status FROM options_cc o
            WHERE NOT EXISTS (
                SELECT 1 FROM cashflows c 
                WHERE c.ref_table = 'options_cc' AND c.ref_id = o.id
            )
        """)
        
        cc_without_cashflow = cursor.fetchall()
        for cc_id, ticker, status in cc_without_cashflow:
            issues.append(f"CC #{cc_id} ({ticker}) nie ma cashflow")
        
        # 2. Cashflow bez CC
        cursor.execute("""
            SELECT c.id, c.description FROM cashflows c
            WHERE c.ref_table = 'options_cc' 
            AND c.ref_id NOT IN (SELECT id FROM options_cc)
        """)
        
        cashflow_without_cc = cursor.fetchall()
        for cf_id, description in cashflow_without_cc:
            issues.append(f"Cashflow #{cf_id} ({description}) nie ma CC")
        
        # 3. Bought back CC bez 2 cashflow
        cursor.execute("""
            SELECT o.id, o.ticker, COUNT(c.id) as cf_count
            FROM options_cc o
            LEFT JOIN cashflows c ON c.ref_table = 'options_cc' AND c.ref_id = o.id
            WHERE o.status = 'bought_back'
            GROUP BY o.id, o.ticker
            HAVING COUNT(c.id) != 2
        """)
        
        bought_back_issues = cursor.fetchall()
        for cc_id, ticker, cf_count in bought_back_issues:
            issues.append(f"CC #{cc_id} ({ticker}) bought_back ma {cf_count} cashflow (powinno być 2)")
        
        conn.close()
        
        return {'issues': issues}
        
    except Exception as e:
        return {'issues': [f'Błąd sprawdzania integralności: {str(e)}']}
        
def partial_buyback_covered_call(cc_id, contracts_to_buyback, buyback_price_usd, buyback_date, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    Częściowy buyback CC:
      - tworzy rekord 'bought_back' na odkupioną część,
      - proporcjonalnie zmniejsza premium w CC-rodzicu,
      - ZMNIEJSZA rezerwacje w mapowaniach i JEDNOCZEŚNIE zwiększa lots.quantity_open,
      - dodaje cashflow 'option_buyback'.
    """
    import sqlite3
    from datetime import datetime as _dt

    conn = None
    try:
        if contracts_to_buyback <= 0:
            return {'success': False, 'message': 'Liczba kontraktów do odkupu musi być > 0'}

        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # ---- pobierz CC
        cur.execute("""SELECT id, ticker, contracts, status, strike_usd, open_date, expiry_date,
                              premium_sell_usd, premium_sell_pln, fx_open
                       FROM options_cc WHERE id=?""", (cc_id,))
        r = cur.fetchone()
        if not r:
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione'}
        if (r['status'] or '') != 'open':
            return {'success': False, 'message': f"CC #{cc_id} nie jest otwarte (status: {r['status']})"}

        total_contracts   = int(r['contracts'] or 0)
        if contracts_to_buyback > total_contracts:
            return {'success': False, 'message': f'Nie można odkupić {contracts_to_buyback} (max {total_contracts})'}

        ticker            = r['ticker']
        strike_usd        = float(r['strike_usd'] or 0.0)
        open_date         = r['open_date']
        expiry_date       = r['expiry_date']
        fx_open           = float(r['fx_open'] or 0.0)
        prem_sell_pln_all = float(r['premium_sell_pln'] or 0.0)
        prem_sell_usd_all = float(r['premium_sell_usd'] or 0.0)

        # ---- data i FX
        if hasattr(buyback_date, 'strftime'):
            buyback_date_str = buyback_date.strftime('%Y-%m-%d')
        elif isinstance(buyback_date, str):
            try:
                buyback_date_str = _dt.strptime(buyback_date, '%Y-%m-%d').date().isoformat()
            except Exception:
                buyback_date_str = buyback_date
        else:
            return {'success': False, 'message': 'Nieprawidłowy typ buyback_date'}

        try:
            import pandas as pd
            fx_close_date = (pd.to_datetime(buyback_date_str) - pd.DateOffset(days=1)).strftime('%Y-%m-%d')
        except Exception:
            fx_close_date = buyback_date_str

        fx_close = get_fx_rate_for_date(fx_close_date)
        if not fx_close or fx_close <= 0:
            fx_close = fx_open if fx_open and fx_open > 0 else None
        if not fx_close:
            return {'success': False, 'message': f'Brak kursu NBP (ani fallback) dla {fx_close_date}'}

        # ---- kalkulacje
        shares_to_buyback     = int(contracts_to_buyback) * 100
        buyback_cost_usd      = float(buyback_price_usd) * shares_to_buyback
        fees_usd              = float(broker_fee_usd or 0.0) + float(reg_fee_usd or 0.0)
        total_buyback_usd     = buyback_cost_usd + fees_usd
        total_buyback_pln     = round(total_buyback_usd * fx_close, 2)

        proportion            = (contracts_to_buyback / total_contracts) if total_contracts > 0 else 0.0
        premium_part_pln      = round(prem_sell_pln_all * proportion, 2)
        pl_pln                = round(premium_part_pln - total_buyback_pln, 2)

        # ---- TRANSAKCJA (savepoint)
        outer_tx = getattr(conn, 'in_transaction', False)
        cur.execute("SAVEPOINT sp_partial_bb")

        try:
            # A) dziecko bought_back
            cur.execute("""
                INSERT INTO options_cc (
                    ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                    open_date, expiry_date, status, fx_open,
                    close_date, premium_buyback_usd, premium_buyback_pln, fx_close,
                    broker_fee_buyback_usd, reg_fee_buyback_usd, total_fees_buyback_pln,
                    pl_pln, created_at, parent_cc_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'bought_back', ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (
                ticker, int(contracts_to_buyback), strike_usd, prem_sell_usd_all, premium_part_pln,
                open_date, expiry_date, fx_open,
                buyback_date_str, buyback_cost_usd, total_buyback_pln, fx_close,
                float(broker_fee_usd or 0.0), float(reg_fee_usd or 0.0), round(fees_usd * fx_close, 2),
                pl_pln, cc_id
            ))
            new_cc_id = cur.lastrowid

            # B) zmniejsz kontrakty + premium w rodzicu
            remaining_contracts = total_contracts - int(contracts_to_buyback)
            remaining_premium_pln = round(prem_sell_pln_all - premium_part_pln, 2)
            cur.execute("""UPDATE options_cc
                           SET contracts=?, premium_sell_pln=?, updated_at=CURRENT_TIMESTAMP
                           WHERE id=?""",
                        (remaining_contracts, remaining_premium_pln, cc_id))

            # C) zwolnij rezerwacje TEGO CC w mapowaniach i jednocześnie zwiększ lots.quantity_open
            released = 0

            # priorytet: cc_lot_mappings
            cur.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'""")
            if cur.fetchone():
                cur.execute("""SELECT id, lot_id, shares_reserved FROM cc_lot_mappings WHERE cc_id=? ORDER BY id""", (cc_id,))
                for m in cur.fetchall() or []:
                    mid = int(m['id']); lot_id = int(m['lot_id']); qty = int(m['shares_reserved'] or 0)
                    if qty <= 0: 
                        continue
                    take = min(qty, shares_to_buyback - released)
                    if take <= 0:
                        break
                    new_qty = qty - take
                    if new_qty > 0:
                        cur.execute("UPDATE cc_lot_mappings SET shares_reserved=? WHERE id=?", (new_qty, mid))
                    else:
                        cur.execute("DELETE FROM cc_lot_mappings WHERE id=?", (mid,))
                    # zwolnij na LOT-cie
                    cur.execute("UPDATE lots SET quantity_open = quantity_open + ? WHERE id = ?", (take, lot_id))
                    released += take

            # fallback: options_cc_reservations
            if released < shares_to_buyback:
                cur.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='options_cc_reservations'""")
                if cur.fetchone():
                    cur.execute("""SELECT id, lot_id, qty_reserved 
                                   FROM options_cc_reservations 
                                   WHERE cc_id=? ORDER BY id""", (cc_id,))
                    for rmap in cur.fetchall() or []:
                        rid = int(rmap['id']); lot_id = int(rmap['lot_id']); qty = int(rmap['qty_reserved'] or 0)
                        if qty <= 0:
                            continue
                        need = shares_to_buyback - released
                        if need <= 0:
                            break
                        take = min(qty, need)
                        new_qty = qty - take
                        if new_qty > 0:
                            cur.execute("UPDATE options_cc_reservations SET qty_reserved=? WHERE id=?", (new_qty, rid))
                        else:
                            cur.execute("DELETE FROM options_cc_reservations WHERE id=?", (rid,))
                        cur.execute("UPDATE lots SET quantity_open = quantity_open + ? WHERE id = ?", (take, lot_id))
                        released += take

            # jeżeli nadal mniej – uzupełnij FIFO (rzadko, ale defensywnie)
            if released < shares_to_buyback:
                need = shares_to_buyback - released
                cur.execute("""SELECT id, quantity_total, quantity_open 
                               FROM lots WHERE UPPER(ticker)=? ORDER BY buy_date, id""", (ticker.upper(),))
                for lot_id, qty_total, qty_open in cur.fetchall() or []:
                    if need <= 0: break
                    potentially_blocked = int(qty_total or 0) - int(qty_open or 0)
                    if potentially_blocked <= 0: 
                        continue
                    take = min(potentially_blocked, need)
                    cur.execute("UPDATE lots SET quantity_open = quantity_open + ? WHERE id = ?", (take, lot_id))
                    need -= take
                    released += take

            # D) cashflow (ujemny)
            desc = (f"Partial buyback CC parent#{cc_id} -> child#{new_cc_id} "
                    f"{contracts_to_buyback}x @{float(buyback_price_usd):.4f} | "
                    f"fees ${fees_usd:.2f} | NBP D-1: {fx_close_date}")
            cur.execute("""
                INSERT INTO cashflows (type, amount_usd, date, fx_rate, amount_pln, description, ref_table, ref_id)
                VALUES ('option_buyback', ?, ?, ?, ?, ?, 'options_cc', ?)
            """, (-total_buyback_usd, buyback_date_str, fx_close, -total_buyback_pln, desc, new_cc_id))

            cur.execute("RELEASE SAVEPOINT sp_partial_bb")
            if not outer_tx:
                conn.commit()
            conn.close()

            return {
                'success': True,
                'message': (f'Odkupiono {contracts_to_buyback}/{total_contracts} kontraktów CC #{cc_id}. '
                            f'Nowy rekord bought_back: #{new_cc_id}. Rezerwacje zmniejszone o {released} akcji.'),
                'parent_cc_id': cc_id,
                'new_cc_id': new_cc_id,
                'contracts_bought_back': int(contracts_to_buyback),
                'contracts_remaining': int(remaining_contracts),
                'shares_released': int(released),                 # 🔑 dla UI
                'shares_released_from_mappings': int(released),   # kompatybilnie
                'fx_close': fx_close,
                'fx_close_date': fx_close_date,
                'pl_pln': pl_pln
            }

        except Exception as txe:
            try:
                cur.execute("ROLLBACK TO SAVEPOINT sp_partial_bb")
                cur.execute("RELEASE SAVEPOINT sp_partial_bb")
            except Exception:
                pass
            try:
                if not outer_tx: conn.rollback()
                conn.close()
            except Exception:
                pass
            return {'success': False, 'message': f'Błąd częściowego buyback: {txe}'}

    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd częściowego buyback: {str(e)}'}
    

def partial_buyback_covered_call_with_mappings(cc_id, contracts_to_buyback, buyback_price_usd, buyback_date, broker_fee_usd=0.0, reg_fee_usd=0.0):
    """
    Częściowy buyback CC z mapowaniami:
      - NBP D-1 via get_fx_rate_for_date (fallback do fx_open),
      - redukcja rezerwacji w cc_lot_mappings (fallback: options_cc_reservations),
      - podział pozycji (dziecko 'bought_back' dla odkupionej części),
      - cashflow 'option_buyback' (ujemny).
    """
    import sqlite3
    from datetime import datetime as _dt

    conn = None
    try:
        if contracts_to_buyback <= 0:
            return {'success': False, 'message': 'Liczba kontraktów do odkupu musi być > 0'}

        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # --- sprawdź tabele rezerwacji
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'")
        has_cc_map = cur.fetchone() is not None
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='options_cc_reservations'")
        has_res_table = cur.fetchone() is not None

        if not has_cc_map and not has_res_table:
            return {'success': False, 'message': 'Brak tabel rezerwacji (cc_lot_mappings / options_cc_reservations).'}

        # --- pobierz CC (musi być open)
        cur.execute("""
            SELECT id, ticker, contracts, status, strike_usd, open_date, expiry_date,
                   COALESCE(premium_sell_usd,0.0)  AS premium_sell_usd,
                   COALESCE(premium_sell_pln,0.0)  AS premium_sell_pln,
                   COALESCE(fx_open,0.0)            AS fx_open
            FROM options_cc
            WHERE id = ? AND status = 'open'
        """, (cc_id,))
        r = cur.fetchone()
        if not r:
            return {'success': False, 'message': f'CC #{cc_id} nie znalezione lub nie jest otwarte'}

        total_contracts = int(r['contracts'] or 0)
        if contracts_to_buyback > total_contracts:
            return {'success': False, 'message': f'Nie można odkupić {contracts_to_buyback} (dostępne: {total_contracts})'}

        ticker       = r['ticker']
        strike_usd   = float(r['strike_usd'] or 0.0)
        open_date    = r['open_date']
        expiry_date  = r['expiry_date']
        fx_open      = float(r['fx_open'] or 0.0)
        prem_sell_usd= float(r['premium_sell_usd'] or 0.0)
        prem_sell_pln= float(r['premium_sell_pln'] or 0.0)

        # --- data + NBP D-1
        if hasattr(buyback_date, 'strftime'):
            buyback_date_str = buyback_date.strftime('%Y-%m-%d')
        elif isinstance(buyback_date, str):
            try:
                buyback_date_str = _dt.strptime(buyback_date, '%Y-%m-%d').date().isoformat()
            except Exception:
                buyback_date_str = buyback_date
        else:
            return {'success': False, 'message': 'Nieprawidłowy typ buyback_date'}

        try:
            import pandas as pd
            fx_close_date = (pd.to_datetime(buyback_date_str) - pd.DateOffset(days=1)).strftime('%Y-%m-%d')
        except Exception:
            fx_close_date = buyback_date_str

        fx_close = get_fx_rate_for_date(fx_close_date)
        if not fx_close or fx_close <= 0:
            fx_close = fx_open if fx_open and fx_open > 0 else None
        if not fx_close:
            return {'success': False, 'message': f'Brak kursu NBP (ani fallback) dla {fx_close_date}'}

        # --- kalkulacje części
        shares_to_buyback = int(contracts_to_buyback) * 100
        shares_total      = total_contracts * 100

        buyback_cost_usd = float(buyback_price_usd) * shares_to_buyback
        fees_usd = float(broker_fee_usd or 0.0) + float(reg_fee_usd or 0.0)
        total_buyback_cost_usd = buyback_cost_usd + fees_usd
        total_buyback_cost_pln = round(total_buyback_cost_usd * fx_close, 2)

        # proporcja premii (PLN) na odkupowaną część
        proportion = (contracts_to_buyback / total_contracts) if total_contracts > 0 else 0.0
        premium_for_buyback_pln = round(prem_sell_pln * proportion, 2)

        # P/L dla odkupowanej części
        pl_pln = round(premium_for_buyback_pln - total_buyback_cost_pln, 2)
        pl_usd = round((prem_sell_usd * shares_to_buyback) - total_buyback_cost_usd, 2)  # informacyjnie

        # --- transakcja
        try:
            cur.execute("BEGIN")

            if contracts_to_buyback < total_contracts:
                # A) utwórz dziecko zamknięte (bought_back)
                cur.execute("""
                    INSERT INTO options_cc (
                        ticker, contracts, strike_usd, premium_sell_usd, premium_sell_pln,
                        open_date, expiry_date, status, fx_open,
                        close_date, premium_buyback_usd, premium_buyback_pln, fx_close,
                        broker_fee_buyback_usd, reg_fee_buyback_usd, total_fees_buyback_pln,
                        pl_pln, created_at, parent_cc_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'bought_back', ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """, (
                    ticker, int(contracts_to_buyback), strike_usd, prem_sell_usd, premium_for_buyback_pln,
                    open_date, expiry_date, fx_open,
                    buyback_date_str, buyback_cost_usd, total_buyback_cost_pln, fx_close,
                    float(broker_fee_usd or 0.0), float(reg_fee_usd or 0.0), round(fees_usd * fx_close, 2),
                    pl_pln, cc_id
                ))
                new_cc_id = cur.lastrowid

                # B) zaktualizuj rodzica (open)
                remaining_contracts   = total_contracts - int(contracts_to_buyback)
                remaining_premium_pln = round(prem_sell_pln - premium_for_buyback_pln, 2)
                cur.execute("""
                    UPDATE options_cc
                    SET contracts = ?, premium_sell_pln = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (remaining_contracts, remaining_premium_pln, cc_id))
            else:
                # pełny buyback na oryginalnym
                new_cc_id = cc_id
                cur.execute("""
                    UPDATE options_cc
                    SET status = 'bought_back',
                        close_date = ?,
                        premium_buyback_usd = ?,
                        premium_buyback_pln = ?,
                        fx_close = ?,
                        broker_fee_buyback_usd = ?,
                        reg_fee_buyback_usd = ?,
                        total_fees_buyback_pln = ?,
                        pl_pln = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (buyback_date_str, buyback_cost_usd, total_buyback_cost_pln, fx_close,
                      float(broker_fee_usd or 0.0), float(reg_fee_usd or 0.0), round(fees_usd * fx_close, 2),
                      pl_pln, cc_id))

            # C) zwolnij rezerwacje Z MAPOWAŃ (bez dotykania lots.quantity_open)
            to_release = shares_to_buyback

            if has_cc_map and to_release > 0:
                # najpierw cc_lot_mappings
                cur.execute("""
                    SELECT id, lot_id, shares_reserved
                    FROM cc_lot_mappings
                    WHERE cc_id = ?
                    ORDER BY id
                """, (cc_id,))
                rows = cur.fetchall() or []
                for m in rows:
                    if to_release <= 0:
                        break
                    mid = int(m['id']); qty = int(m['shares_reserved'] or 0)
                    if qty <= 0:
                        continue
                    take = qty if qty <= to_release else to_release
                    new_qty = qty - take
                    if new_qty > 0:
                        cur.execute("UPDATE cc_lot_mappings SET shares_reserved = ? WHERE id = ?", (new_qty, mid))
                    else:
                        cur.execute("DELETE FROM cc_lot_mappings WHERE id = ?", (mid,))
                    to_release -= take

            if has_res_table and to_release > 0:
                # fallback: options_cc_reservations
                cur.execute("""
                    SELECT id, lot_id, qty_reserved
                    FROM options_cc_reservations
                    WHERE cc_id = ?
                    ORDER BY id
                """, (cc_id,))
                rows = cur.fetchall() or []
                for rmap in rows:
                    if to_release <= 0:
                        break
                    rid = int(rmap['id']); qty = int(rmap['qty_reserved'] or 0)
                    if qty <= 0:
                        continue
                    take = qty if qty <= to_release else to_release
                    new_qty = qty - take
                    if new_qty > 0:
                        cur.execute("UPDATE options_cc_reservations SET qty_reserved = ? WHERE id = ?", (new_qty, rid))
                    else:
                        cur.execute("DELETE FROM options_cc_reservations WHERE id = ?", (rid,))
                    to_release -= take

            # D) cashflow (ujemny) przypięty do rekordu zamkniętego
            description = (f"Partial buyback CC parent#{cc_id}"
                           f"{'' if new_cc_id==cc_id else f' -> child#{new_cc_id}'} "
                           f"{contracts_to_buyback}x @{float(buyback_price_usd):.4f} | "
                           f"fees ${float(broker_fee_usd)+float(reg_fee_usd):.2f} | NBP D-1: {fx_close_date}")
            cur.execute("""
                INSERT INTO cashflows (type, amount_usd, date, fx_rate, amount_pln, description, ref_table, ref_id)
                VALUES ('option_buyback', ?, ?, ?, ?, ?, 'options_cc', ?)
            """, (-total_buyback_cost_usd, buyback_date_str, fx_close, -total_buyback_cost_pln, description, new_cc_id))

            cur.execute("COMMIT")

        except Exception as txe:
            try: cur.execute("ROLLBACK")
            except Exception: pass
            return {'success': False, 'message': f'Błąd transakcji partial buyback: {txe}'}

        # raport
        return {
            'success': True,
            'message': (f'Odkupiono {contracts_to_buyback}/{total_contracts} kontraktów CC #{cc_id}. '
                        f"{'Nowy rekord bought_back: #'+str(new_cc_id)+'. ' if new_cc_id!=cc_id else ''}"
                        f'Rezerwacje zmniejszone o {shares_to_buyback} akcji.'),
            'parent_cc_id': cc_id,
            'new_cc_id': new_cc_id if new_cc_id != cc_id else None,
            'contracts_bought_back': int(contracts_to_buyback),
            'contracts_remaining': int(total_contracts - contracts_to_buyback),
            'shares_released_from_mappings': shares_to_buyback,
            'fx_close': fx_close,
            'fx_close_date': fx_close_date,
            'pl_pln': pl_pln,
            'pl_usd': pl_usd,
            'premium_portion_pln': premium_for_buyback_pln,
            'total_buyback_cost_pln': total_buyback_cost_pln
        }

    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd częściowego buyback: {str(e)}'}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_fx_rate_for_date(target_date):
    """
    🎯 WSPÓLNA FUNKCJA pobierania kursu NBP USD/PLN
    Wykorzystywana we wszystkich buybackach i expiry.

    Args:
        target_date (str | datetime.date): Data w formacie YYYY-MM-DD lub obiekt date

    Returns:
        float: Kurs USD/PLN na ten dzień (NBP D-1)
    """
    try:
        import nbp_api_client

        # Ujednolicenie formatu daty
        if hasattr(target_date, 'strftime'):
            date_for_nbp = target_date
        elif isinstance(target_date, str):
            from datetime import datetime
            date_for_nbp = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            date_for_nbp = target_date

        print(f"🔍 FX_RATE: Pobieranie kursu NBP dla {date_for_nbp}")

        # Pobranie kursu przez klienta NBP
        nbp_result = nbp_api_client.get_usd_rate_for_date(date_for_nbp)

        # Obsługa zwróconego typu
        if isinstance(nbp_result, dict) and 'rate' in nbp_result:
            fx_rate = float(nbp_result['rate'])
            fx_date = nbp_result.get('date', date_for_nbp)
        else:
            fx_rate = float(nbp_result) if nbp_result else None
            fx_date = date_for_nbp

        if fx_rate is None:
            raise Exception("NBP zwrócił None")

        print(f"💱 FX_RATE: {fx_rate:.4f} na {fx_date}")
        return fx_rate

    except Exception as e:
        print(f"❌ FX_RATE: Błąd pobierania kursu: {e}")
        return None


def mass_fix_bought_back_cc_reservations():
    """
    🔓 Naprawa rezerwacji dla CC ze statusem 'bought_back' – BEZ modyfikacji lots.quantity_open.

    Zasady:
      - Źródłem prawdy o rezerwacjach są tabele mapowań.
      - Dla CC o statusie 'bought_back' kasujemy odpowiadające wpisy:
          * cc_lot_mappings (nowa tabela)
          * options_cc_reservations (stara tabela – fallback/legacy)
      - Nie zmieniamy lots.quantity_open.

    Returns:
        dict: {
          'success': bool,
          'message': str,
          'fixed_count': int,                # liczba CC, dla których coś usunięto
          'rows_deleted_cc_lot_mappings': int,
          'rows_deleted_options_cc_reservations': int,
          'shares_released_logical': int     # suma akcji usuniętych z mapowań
        }
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Sprawdź dostępność tabel
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in (cur.fetchall() or [])}
        has_cc_map = 'cc_lot_mappings' in tables
        has_reserv = 'options_cc_reservations' in tables

        if not has_cc_map and not has_reserv:
            return {
                'success': True,
                'message': 'Brak tabel rezerwacji – nie ma czego naprawiać',
                'fixed_count': 0,
                'rows_deleted_cc_lot_mappings': 0,
                'rows_deleted_options_cc_reservations': 0,
                'shares_released_logical': 0
            }

        # Zbierz listę CC w statusie bought_back
        cur.execute("SELECT id FROM options_cc WHERE status='bought_back' ORDER BY id")
        cc_ids = [int(r['id']) for r in (cur.fetchall() or [])]
        if not cc_ids:
            return {
                'success': True,
                'message': 'Brak CC ze statusem bought_back',
                'fixed_count': 0,
                'rows_deleted_cc_lot_mappings': 0,
                'rows_deleted_options_cc_reservations': 0,
                'shares_released_logical': 0
            }

        rows_deleted_new = 0
        rows_deleted_old = 0
        shares_released = 0
        fixed_cc = 0

        try:
            cur.execute("BEGIN")

            for cid in cc_ids:
                per_cc_deleted = 0
                per_cc_shares = 0

                # Nowa tabela mapowań
                if has_cc_map:
                    cur.execute("SELECT COALESCE(SUM(shares_reserved),0) AS s, COUNT(*) AS n FROM cc_lot_mappings WHERE cc_id=?", (cid,))
                    r = cur.fetchone()
                    s = int(r['s'] or 0)
                    n = int(r['n'] or 0)
                    if n > 0:
                        cur.execute("DELETE FROM cc_lot_mappings WHERE cc_id=?", (cid,))
                        rows_deleted_new += n
                        per_cc_deleted += n
                        per_cc_shares += s

                # Stara tabela rezerwacji (fallback)
                if has_reserv:
                    cur.execute("SELECT COALESCE(SUM(qty_reserved),0) AS s, COUNT(*) AS n FROM options_cc_reservations WHERE cc_id=?", (cid,))
                    r = cur.fetchone()
                    s = int(r['s'] or 0)
                    n = int(r['n'] or 0)
                    if n > 0:
                        cur.execute("DELETE FROM options_cc_reservations WHERE cc_id=?", (cid,))
                        rows_deleted_old += n
                        per_cc_deleted += n
                        per_cc_shares += s

                if per_cc_deleted > 0:
                    fixed_cc += 1
                    shares_released += per_cc_shares

            cur.execute("COMMIT")
        except Exception as txe:
            try: cur.execute("ROLLBACK")
            except Exception: pass
            return {'success': False, 'message': f'Błąd transakcji cleanupu: {txe}', 'fixed_count': 0}

        msg_parts = [f"Naprawiono {fixed_cc} CC"]
        if rows_deleted_new:
            msg_parts.append(f"usunięto {rows_deleted_new} wpisów z cc_lot_mappings")
        if rows_deleted_old:
            msg_parts.append(f"usunięto {rows_deleted_old} wpisów z options_cc_reservations")
        if shares_released:
            msg_parts.append(f"łączna „logicznie zwolniona” liczba akcji: {shares_released}")

        return {
            'success': True,
            'message': " | ".join(msg_parts) if msg_parts else "Brak zmian",
            'fixed_count': fixed_cc,
            'rows_deleted_cc_lot_mappings': rows_deleted_new,
            'rows_deleted_options_cc_reservations': rows_deleted_old,
            'shares_released_logical': shares_released
        }

    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd zwalniania rezerwacji: {e}', 'fixed_count': 0}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_blocked_cc_status():
    """
    🔍 SPRAWDZA: ile CC ze statusem 'bought_back' wciąż ma rezerwacje
    w cc_lot_mappings (nowa) i/lub options_cc_reservations (stara).

    Zwraca:
        {
          'blocked_cc_count': int,         # liczba unikalnych CC z blokadami
          'blocked_shares': int,           # suma zarezerwowanych akcji (po zsumowaniu z obu tabel per CC)
          'details': [str, ...],           # opis per tabela
          'has_problems': bool
        }
    """
    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'error': 'Brak połączenia z bazą'}
        cursor = conn.cursor()

        # Sprawdź dostępne tabele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        # Zbierz rezerwacje per CC z obu tabel
        per_cc_from_new = {}  # cc_id -> shares
        per_cc_from_old = {}  # cc_id -> shares

        details = []

        # Nowa tabela mapowań
        if 'cc_lot_mappings' in tables:
            cursor.execute("""
                SELECT m.cc_id, COALESCE(SUM(m.shares_reserved), 0) AS shares_sum
                FROM cc_lot_mappings m
                JOIN options_cc cc ON cc.id = m.cc_id
                WHERE cc.status = 'bought_back'
                GROUP BY m.cc_id
            """)
            rows = cursor.fetchall()
            sum_new = 0
            for cc_id, shares_sum in rows:
                per_cc_from_new[int(cc_id)] = int(shares_sum or 0)
                sum_new += int(shares_sum or 0)
            details.append(f"Nowa tabela: {len(per_cc_from_new)} CC, {sum_new} akcji")

        # Stara tabela rezerwacji
        if 'options_cc_reservations' in tables:
            cursor.execute("""
                SELECT r.cc_id, COALESCE(SUM(r.qty_reserved), 0) AS shares_sum
                FROM options_cc_reservations r
                JOIN options_cc cc ON cc.id = r.cc_id
                WHERE cc.status = 'bought_back'
                GROUP BY r.cc_id
            """)
            rows = cursor.fetchall()
            sum_old = 0
            for cc_id, shares_sum in rows:
                per_cc_from_old[int(cc_id)] = int(shares_sum or 0)
                sum_old += int(shares_sum or 0)
            details.append(f"Stara tabela: {len(per_cc_from_old)} CC, {sum_old} akcji")

        # Połącz wyniki per CC tak, by nie dublować countów; sumujemy akcje z obu tabel
        total_per_cc = {}
        for cc_id, shares in per_cc_from_new.items():
            total_per_cc[cc_id] = total_per_cc.get(cc_id, 0) + shares
        for cc_id, shares in per_cc_from_old.items():
            total_per_cc[cc_id] = total_per_cc.get(cc_id, 0) + shares

        blocked_cc_count = len(total_per_cc)
        blocked_shares = sum(total_per_cc.values())

        return {
            'blocked_cc_count': blocked_cc_count,
            'blocked_shares': blocked_shares,
            'details': details,
            'has_problems': blocked_cc_count > 0
        }

    except Exception as e:
        return {'error': f'Błąd sprawdzania: {str(e)}'}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_lots_for_tax_fifo(ticker: str) -> List[Dict]:
    """
    🎯 KLUCZOWA FUNKCJA: Pobiera LOT-y dla FIFO PODATKOWEGO

    RÓŻNICA od get_lots_by_ticker():
    - NIE filtruje po quantity_open > 0
    - Bierze WSZYSTKIE LOT-y (także częściowo/całkowicie zarezerwowane pod CC)
    - Kolejność: FIFO (buy_date ASC, id ASC)

    Zwracane pola (m.in.):
      - quantity_sold      → faktycznie sprzedane sztuki (ze stock_trade_splits)
      - is_blocked_by_cc   → czy lot ma zarezerwowane akcje pod otwarte CC
      - cost_per_share_pln → koszt jednostkowy w PLN (bezpiecznie 0 gdy qty=0)
    """
    import sqlite3

    conn = get_connection()
    if not conn:
        return []

    try:
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        tkr = (ticker or "").upper().strip()

        # Sprawdź dostępność tabel rezerwacji (nowa i legacy)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {r[0] for r in (cur.fetchall() or [])}
        has_cc_map = 'cc_lot_mappings' in existing_tables
        has_reserv = 'options_cc_reservations' in existing_tables

        # Zbuduj częściowy SELECT dla rezerwacji
        # rezerwacje liczymy tylko dla CC ze statusem 'open'
        reserved_new_sql = ""
        reserved_old_sql = ""
        if has_cc_map:
            reserved_new_sql = """
                COALESCE((
                    SELECT SUM(m.shares_reserved)
                    FROM cc_lot_mappings m
                    JOIN options_cc oc ON oc.id = m.cc_id
                    WHERE m.lot_id = l.id AND oc.status = 'open'
                ), 0)
            """
        else:
            reserved_new_sql = "0"

        if has_reserv:
            reserved_old_sql = """
                COALESCE((
                    SELECT SUM(r.qty_reserved)
                    FROM options_cc_reservations r
                    JOIN options_cc oc2 ON oc2.id = r.cc_id
                    WHERE r.lot_id = l.id AND oc2.status = 'open'
                ), 0)
            """
        else:
            reserved_old_sql = "0"

        # Sprzedaże z realnych splitów
        sold_sql = """
            COALESCE((
                SELECT SUM(sts.qty_from_lot)
                FROM stock_trade_splits sts
                WHERE sts.lot_id = l.id
            ), 0)
        """

        query = f"""
            SELECT
                l.id, l.ticker, l.quantity_total, l.quantity_open, l.buy_price_usd,
                l.broker_fee_usd, l.reg_fee_usd, l.buy_date, l.fx_rate, l.cost_pln,
                l.created_at, l.updated_at,
                ({sold_sql}) AS qty_sold_real,
                ({reserved_new_sql}) AS qty_reserved_new,
                ({reserved_old_sql}) AS qty_reserved_old
            FROM lots l
            WHERE l.ticker = ?
            ORDER BY l.buy_date ASC, l.id ASC
        """

        cur.execute(query, (tkr,))
        rows = cur.fetchall() or []

        lots: List[Dict] = []
        for r in rows:
            qty_total = int(r["quantity_total"] or 0)
            qty_open  = int(r["quantity_open"] or 0)
            qty_sold  = int(r["qty_sold_real"] or 0)

            # Rezerwacje (sumujemy obie tabele, jeśli obie istnieją)
            qty_reserved = int(r["qty_reserved_new"] or 0) + int(r["qty_reserved_old"] or 0)
            is_blocked = qty_reserved > 0

            # Koszt jednostkowy PLN – bezpiecznie obsłuż zero
            cost_pln = float(r["cost_pln"] or 0.0)
            cps_pln = (cost_pln / qty_total) if qty_total > 0 else 0.0

            lots.append({
                'id': r["id"],
                'ticker': r["ticker"],
                'quantity_total': qty_total,
                'quantity_open': qty_open,
                'buy_price_usd': float(r["buy_price_usd"] or 0.0),
                'broker_fee_usd': float(r["broker_fee_usd"] or 0.0),
                'reg_fee_usd': float(r["reg_fee_usd"] or 0.0),
                'buy_date': r["buy_date"],
                'fx_rate': float(r["fx_rate"] or 0.0),
                'cost_pln': cost_pln,
                'created_at': r["created_at"],
                'updated_at': r["updated_at"],

                # Pola podatkowe / pomocnicze
                'quantity_sold': qty_sold,                 # ✅ realne sprzedaże
                'reserved_shares_cc': qty_reserved,        # ile sztuk zarezerwowane pod otwarte CC
                'is_blocked_by_cc': is_blocked,            # ✅ na podstawie mapowań
                'cost_per_share_pln': cps_pln
            })

        return lots

    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def calculate_tax_fifo_allocation(ticker: str, quantity_to_sell: int) -> Dict:
    """
    🎯 FIFO PODATKOWE (ignoruje blokady CC przy wyborze kolejności, ale je raportuje).
    Zwraca alokację kosztu dla PIT-38.
    """
    # Walidacje
    try:
        qty_req = int(quantity_to_sell)
    except Exception:
        return {'success': False, 'error': 'quantity_to_sell musi być liczbą całkowitą', 'allocation': [], 'total_cost_pln': 0.0, 'lots_used': 0}
    if qty_req <= 0:
        return {'success': False, 'error': 'quantity_to_sell musi być > 0', 'allocation': [], 'total_cost_pln': 0.0, 'lots_used': 0}
    if not ticker or not str(ticker).strip():
        return {'success': False, 'error': 'Brak tickera', 'allocation': [], 'total_cost_pln': 0.0, 'lots_used': 0}

    # 1) LOT-y w kolejności FIFO podatkowego (wszystkie, bez filtra blokad)
    tax_lots = get_lots_for_tax_fifo(ticker)
    if not tax_lots:
        return {'success': False, 'error': f'Brak LOT-ów dla {ticker}', 'allocation': [], 'total_cost_pln': 0.0, 'lots_used': 0}

    # 2) Sprawdź dostępność (posiadane - sprzedane)
    total_owned = sum(int(l['quantity_total'] or 0) for l in tax_lots)
    total_already_sold = sum(int(l.get('quantity_sold', 0) or 0) for l in tax_lots)
    total_remaining = total_owned - total_already_sold

    if qty_req > total_remaining:
        return {
            'success': False,
            'error': f'Próba sprzedaży {qty_req} akcji, ale pozostało tylko {total_remaining}',
            'allocation': [],
            'total_cost_pln': 0.0,
            'lots_used': 0
        }

    # 3) Alokacja FIFO (podatkowa)
    allocation: List[Dict] = []
    remaining = qty_req
    total_cost = Decimal('0.00')

    for lot in tax_lots:
        if remaining <= 0:
            break

        qty_total = int(lot['quantity_total'] or 0)
        qty_sold = int(lot.get('quantity_sold', 0) or 0)
        lot_remaining = qty_total - qty_sold
        if lot_remaining <= 0:
            continue

        # koszt jednostkowy PLN – bierzemy z lot['cost_per_share_pln'] jeśli jest; inaczej wyliczamy
        cps = lot.get('cost_per_share_pln', None)
        if cps is None:
            cost_pln = Decimal(str(lot.get('cost_pln', 0.0) or 0.0))
            cps_dec = (cost_pln / Decimal(qty_total)) if qty_total > 0 else Decimal('0')
        else:
            cps_dec = Decimal(str(cps))

        use_qty = min(remaining, lot_remaining)
        cost_from_lot = (cps_dec * Decimal(use_qty)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        allocation.append({
            'lot_id': lot['id'],
            'lot_buy_date': lot['buy_date'],
            'lot_buy_price_usd': float(lot.get('buy_price_usd') or 0.0),
            'lot_fx_rate': float(lot.get('fx_rate') or 0.0),
            'qty_used': use_qty,
            'cost_pln': float(cost_from_lot),
            'cost_per_share_pln': float(cps_dec.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),
            'is_blocked_by_cc': bool(lot.get('is_blocked_by_cc', False)),
            'quantity_open_before': int(lot.get('quantity_open', 0) or 0),
            'tax_note': 'PODATKOWO_SPRZEDANE' if lot.get('is_blocked_by_cc', False) else 'NORMALNIE_SPRZEDANE'
        })

        total_cost += cost_from_lot
        remaining -= use_qty

    # 4) Porównanie z FIFO operacyjnym (opcjonalne)
    comparison = None
    try:
        operational_lots = get_lots_by_ticker(ticker, only_open=True)  # jeśli nie istnieje, złapie except
        comparison = {
            'tax_lots_count': len(tax_lots),
            'operational_lots_count': len(operational_lots) if isinstance(operational_lots, list) else None,
            'tax_uses_blocked': any(a['is_blocked_by_cc'] for a in allocation),
            'difference_detected': (len(tax_lots) != len(operational_lots)) if isinstance(operational_lots, list) else None
        }
    except Exception:
        comparison = {
            'tax_lots_count': len(tax_lots),
            'operational_lots_count': None,
            'tax_uses_blocked': any(a['is_blocked_by_cc'] for a in allocation),
            'difference_detected': None
        }

    return {
        'success': remaining == 0,
        'allocation': allocation,
        'total_cost_pln': float(total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
        'lots_used': len(allocation),
        'comparison': comparison,
        'debug_info': {
            'quantity_requested': qty_req,
            'quantity_allocated': qty_req - remaining,
            'remaining_unallocated': remaining
        }
    }


def get_tax_vs_operational_fifo_comparison(ticker: str, quantity: int) -> Dict:
    """
    🔍 FUNKCJA DIAGNOSTYCZNA: Porównuje FIFO podatkowy vs operacyjny

    FIFO PODATKOWY: calculate_tax_fifo_allocation (wszystkie LOT-y wg buy_date)
    FIFO OPERACYJNY: LOT-y dostępne do sprzedaży teraz = quantity_total - sold - reserved(open CC)
                      (rezerwacje z cc_lot_mappings, fallback: options_cc_reservations)
    """
    try:
        ticker_upper = (ticker or "").upper().strip()

        # 1) FIFO PODATKOWY – zostawiamy Twoją funkcję źródłową
        tax_result = calculate_tax_fifo_allocation(ticker_upper, quantity) or {}
        tax_alloc = tax_result.get('allocation', []) or []
        tax_total_cost = float(tax_result.get('total_cost_pln', 0.0) or 0.0)
        tax_lots_used = [a.get('lot_id') for a in tax_alloc]

        # 2) FIFO OPERACYJNY – policzone na bazie realnych rezerwacji i sprzedaży
        conn = get_connection()
        if not conn:
            return {
                'ticker': ticker_upper,
                'quantity_tested': quantity,
                'tax_fifo': {
                    'success': tax_result.get('success', False),
                    'lots_used': tax_lots_used,
                    'total_cost_pln': tax_total_cost,
                    'allocation_count': len(tax_alloc)
                },
                'operational_fifo': {
                    'success': False,
                    'lots_used': [],
                    'total_cost_pln': 0.0,
                    'allocation_count': 0
                },
                'differences': {
                    'different_lots_used': True,
                    'different_costs': True,
                    'tax_uses_blocked_lots': any(a.get('is_blocked_by_cc', False) for a in tax_alloc),
                    'cost_difference_pln': tax_total_cost - 0.0
                },
                'recommendation': 'USE_TAX_FIFO_FOR_PIT38'
            }

        cur = conn.cursor()

        # 2a) Suma sprzedanych per LOT (cała historia)
        cur.execute("""
            SELECT sts.lot_id, COALESCE(SUM(sts.qty_from_lot), 0) AS qty_sold
            FROM stock_trade_splits sts
            JOIN lots l ON l.id = sts.lot_id
            WHERE UPPER(l.ticker) = ?
            GROUP BY sts.lot_id
        """, (ticker_upper,))
        sold_map = {row[0]: int(row[1] or 0) for row in (cur.fetchall() or [])}

        # 2b) Rezerwacje z cc_lot_mappings dla OTWARTYCH CC
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'")
        has_mappings = cur.fetchone() is not None
        reserved_map = {}

        total_reserved_from_mappings = 0
        if has_mappings:
            cur.execute("""
                SELECT m.lot_id, COALESCE(SUM(m.shares_reserved),0) AS qty_reserved
                FROM cc_lot_mappings m
                JOIN options_cc cc ON cc.id = m.cc_id
                JOIN lots l ON l.id = m.lot_id
                WHERE cc.status='open' AND UPPER(l.ticker)=?
                GROUP BY m.lot_id
            """, (ticker_upper,))
            rows = cur.fetchall() or []
            reserved_map = {r[0]: int(r[1] or 0) for r in rows}
            total_reserved_from_mappings = sum(reserved_map.values())

        # 2c) Fallback: jeśli brak rezerwacji w cc_lot_mappings, użyj options_cc_reservations
        if total_reserved_from_mappings == 0:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='options_cc_reservations'")
            has_old = cur.fetchone() is not None
            if has_old:
                cur.execute("""
                    SELECT r.lot_id, COALESCE(SUM(r.qty_reserved),0) AS qty_reserved
                    FROM options_cc_reservations r
                    JOIN options_cc cc ON cc.id = r.cc_id
                    JOIN lots l ON l.id = r.lot_id
                    WHERE cc.status='open' AND UPPER(l.ticker)=?
                    GROUP BY r.lot_id
                """, (ticker_upper,))
                rows = cur.fetchall() or []
                reserved_map = {r[0]: int(r[1] or 0) for r in rows}

        # 2d) Lista LOT-ów (kolejność FIFO)
        cur.execute("""
            SELECT id, quantity_total, buy_date, cost_pln
            FROM lots
            WHERE UPPER(ticker)=?
            ORDER BY buy_date ASC, id ASC
        """, (ticker_upper,))
        lots_rows = cur.fetchall() or []

        operational_allocation = []
        remaining = int(quantity)
        operational_cost = 0.0

        for row in lots_rows:
            if remaining <= 0:
                break
            lot_id, qty_total, buy_date, cost_pln = row[0], int(row[1] or 0), row[2], float(row[3] or 0.0)
            qty_sold = int(sold_map.get(lot_id, 0))
            qty_res  = int(reserved_map.get(lot_id, 0))
            qty_available = qty_total - qty_sold - qty_res
            if qty_available <= 0:
                continue

            take = qty_available if qty_available < remaining else remaining
            cps_pln = (cost_pln / qty_total) if qty_total > 0 else 0.0
            cost_from_lot = round(take * cps_pln, 2)

            operational_allocation.append({
                'lot_id': lot_id,
                'lot_buy_date': buy_date,
                'qty_used': take,
                'cost_pln': cost_from_lot
            })

            operational_cost += cost_from_lot
            remaining -= take

        # 2e) Czy tax FIFO używa LOT-ów zablokowanych przez CC?
        #     Najpierw spróbuj z flagi w tax_result, a jeśli brak – sprawdź względem reserved_map.
        tax_uses_blocked_flag = any(a.get('is_blocked_by_cc', False) for a in tax_alloc)
        if not tax_uses_blocked_flag and reserved_map and tax_alloc:
            for a in tax_alloc:
                lid = a.get('lot_id')
                if lid is not None and int(reserved_map.get(int(lid), 0)) > 0:
                    tax_uses_blocked_flag = True
                    break

        try:
            conn.close()
        except Exception:
            pass

        operational_lots_used = [a['lot_id'] for a in operational_allocation]

        return {
            'ticker': ticker_upper,
            'quantity_tested': quantity,
            'tax_fifo': {
                'success': tax_result.get('success', False),
                'lots_used': tax_lots_used,
                'total_cost_pln': round(tax_total_cost, 2),
                'allocation_count': len(tax_alloc)
            },
            'operational_fifo': {
                'success': remaining == 0,
                'lots_used': operational_lots_used,
                'total_cost_pln': round(operational_cost, 2),
                'allocation_count': len(operational_allocation)
            },
            'differences': {
                'different_lots_used': tax_lots_used != operational_lots_used,
                'different_costs': abs(tax_total_cost - operational_cost) > 0.01,
                'tax_uses_blocked_lots': tax_uses_blocked_flag,
                'cost_difference_pln': round(tax_total_cost - operational_cost, 2)
            },
            'recommendation': 'USE_TAX_FIFO_FOR_PIT38' if tax_lots_used != operational_lots_used else 'BOTH_SAME'
        }

    except Exception as e:
        return {
            'ticker': (ticker or '').upper(),
            'quantity_tested': quantity,
            'tax_fifo': {'success': False, 'lots_used': [], 'total_cost_pln': 0.0, 'allocation_count': 0},
            'operational_fifo': {'success': False, 'lots_used': [], 'total_cost_pln': 0.0, 'allocation_count': 0},
            'differences': {'different_lots_used': False, 'different_costs': False, 'tax_uses_blocked_lots': False, 'cost_difference_pln': 0.0},
            'recommendation': 'USE_TAX_FIFO_FOR_PIT38',
            'error': str(e)
        }


def migrate_options_cc_add_chain_id():
    """
    🔗 PUNKT 72: Dodanie kolumny chain_id do tabeli options_cc
    - Idempotentne
    - FK do cc_chains(id) ON DELETE SET NULL
    - Tworzy cc_chains, jeśli nie istnieje
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}
        cur = conn.cursor()

        # Włącz weryfikację kluczy obcych (na wszelki wypadek)
        try:
            cur.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass

        # Upewnij się, że istnieje tabela cc_chains (minimalna definicja)
        cur.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='cc_chains'
        """)
        has_chains = cur.fetchone() is not None
        if not has_chains:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cc_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP
                )
            """)

        # Sprawdź czy kolumna już istnieje
        cur.execute("PRAGMA table_info(options_cc)")
        existing_columns = [row[1] for row in (cur.fetchall() or [])]
        if 'chain_id' in existing_columns:
            # Indeks może jeszcze nie istnieć – dołóż idempotentnie
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_options_cc_chain_id 
                ON options_cc(chain_id)
            """)
            conn.commit()
            return {'success': True, 'message': 'Kolumna chain_id już istniała (upewniono się o indeksie)'}

        # Dodaj kolumnę chain_id z FK
        cur.execute("BEGIN")
        cur.execute("""
            ALTER TABLE options_cc 
            ADD COLUMN chain_id INTEGER 
                REFERENCES cc_chains(id) ON DELETE SET NULL
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_options_cc_chain_id 
            ON options_cc(chain_id)
        """)
        cur.execute("COMMIT")

        return {'success': True, 'message': '✅ Kolumna chain_id dodana do options_cc (z FK i indeksem)'}
    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        return {'success': False, 'message': f'❌ Błąd migracji: {e}'}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def check_cc_chains_migration_status():
    """
    🔍 PUNKT 72.1: Sprawdza status migracji CC Chains

    Returns:
        dict: {
            'success': bool,
            'tables_status': {...},
            'anomalies': [str, ...],            # dodatkowe ostrzeżenia (opcjonalne)
            'chains_overview': [{'chain_id': int, 'members': int}, ...]  # opcjonalnie
        }
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'error': 'Brak połączenia z bazą'}

        # Ułatwione czytanie kolumn po nazwach (gdy możliwe)
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        tables_status = {}
        anomalies = []
        chains_overview = []

        # 1) Czy tabela cc_chains istnieje?
        cur.execute("SELECT COUNT(*) AS c FROM sqlite_master WHERE type='table' AND name='cc_chains'")
        tables_status['cc_chains_exists'] = (cur.fetchone()['c'] > 0)

        if tables_status['cc_chains_exists']:
            cur.execute("SELECT COUNT(*) AS c FROM cc_chains")
            tables_status['cc_chains_count'] = int(cur.fetchone()['c'] or 0)
        else:
            tables_status['cc_chains_count'] = 0

        # 2) Czy options_cc ma kolumnę chain_id?
        cur.execute("PRAGMA table_info(options_cc)")
        cols = cur.fetchall() or []
        existing_columns = [row[1] if not isinstance(row, sqlite3.Row) else row['name'] for row in cols]
        tables_status['chain_id_exists'] = ('chain_id' in existing_columns)

        # 2a) Czy istnieje indeks na chain_id?
        index_exists = False
        if tables_status['chain_id_exists']:
            cur.execute("PRAGMA index_list('options_cc')")
            idx_rows = cur.fetchall() or []
            names = []
            for r in idx_rows:
                # PRAGMA index_list daje (seq, name, unique, origin, partial) lub Row
                nm = r[1] if not isinstance(r, sqlite3.Row) else r['name']
                if nm:
                    names.append(nm.lower())
            index_exists = any('idx_options_cc_chain_id' == n for n in names)
        tables_status['chain_id_index_exists'] = index_exists

        # 3) Ile CC ma przypisane chains?
        if tables_status['chain_id_exists']:
            cur.execute("SELECT COUNT(*) AS c FROM options_cc WHERE chain_id IS NOT NULL")
            tables_status['cc_with_chains'] = int(cur.fetchone()['c'] or 0)

            cur.execute("SELECT COUNT(*) AS c FROM options_cc WHERE chain_id IS NULL")
            tables_status['cc_without_chains'] = int(cur.fetchone()['c'] or 0)
        else:
            tables_status['cc_with_chains'] = 0
            tables_status['cc_without_chains'] = 0

        # --- Dodatkowa diagnostyka anomalii, jeśli mamy chain_id lub tabelę chains ---
        if tables_status['chain_id_exists']:
            # CC wskazujące nieistniejący chain_id (orphan FK logiczny – gdy FK OFF)
            if tables_status['cc_chains_exists']:
                cur.execute("""
                    SELECT DISTINCT oc.chain_id
                    FROM options_cc oc
                    LEFT JOIN cc_chains ch ON ch.id = oc.chain_id
                    WHERE oc.chain_id IS NOT NULL AND ch.id IS NULL
                """)
                orphans = [int(r[0]) for r in (cur.fetchall() or [])]
                if orphans:
                    anomalies.append(f"CC wskazują na nieistniejące chain_id: {orphans}")

                # Łańcuchy bez członków
                cur.execute("""
                    SELECT ch.id
                    FROM cc_chains ch
                    LEFT JOIN options_cc oc ON oc.chain_id = ch.id
                    GROUP BY ch.id
                    HAVING COUNT(oc.id) = 0
                """)
                empty_chains = [int(r[0]) for r in (cur.fetchall() or [])]
                if empty_chains:
                    anomalies.append(f"Łańcuchy bez członków: {empty_chains}")

                # Przegląd liczebności per chain
                cur.execute("""
                    SELECT oc.chain_id AS chain_id, COUNT(*) AS members
                    FROM options_cc oc
                    WHERE oc.chain_id IS NOT NULL
                    GROUP BY oc.chain_id
                    ORDER BY oc.chain_id
                """)
                chains_overview = [{'chain_id': int(r['chain_id']), 'members': int(r['members'])}
                                   for r in (cur.fetchall() or [])]
            else:
                # Nie ma cc_chains, ale są CC z chain_id => anomalia
                if tables_status.get('cc_with_chains', 0) > 0:
                    anomalies.append("Istnieją CC z chain_id, ale brak tabeli cc_chains.")

        return {
            'success': True,
            'tables_status': tables_status,
            'anomalies': anomalies,
            'chains_overview': chains_overview
        }

    except Exception as e:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return {'success': False, 'error': f'Błąd sprawdzania: {str(e)}'}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def run_cc_chains_migration():
    """
    🚀 PUNKT 72.2: Kompletna migracja CC Chains

    1) Tworzy tabelę cc_chains (jeśli nie istnieje) – próbuje structure.create_cc_chains_table(conn),
       a gdy brak/nie działa, tworzy inline (fallback).
    2) Dodaje chain_id do options_cc (FK ON DELETE SET NULL + indeks) – przez migrate_options_cc_add_chain_id().
    3) Sprawdza status i dorzuca ewentualne anomalie z check_cc_chains_migration_status().

    Zwraca: dict z kluczami:
      - steps_completed: [str, ...]
      - errors: [str, ...]
      - success: bool
      - final_status: dict (jak z check_cc_chains_migration_status()['tables_status'])
      - anomalies: [str, ...] (opcjonalnie)
      - chains_overview: [ {chain_id, members}, ... ] (opcjonalnie)
    """
    import sqlite3

    migration_report = {
        'steps_completed': [],
        'errors': [],
        'success': True
    }

    conn = None
    try:
        # --- KROK 1: Utwórz tabelę cc_chains (zależność opcjonalna + fallback)
        try:
            from structure import create_cc_chains_table  # opcjonalne
        except Exception:
            create_cc_chains_table = None

        conn = get_connection()
        if not conn:
            migration_report['errors'].append('Brak połączenia z bazą')
            migration_report['success'] = False
            return migration_report

        cur = conn.cursor()
        try:
            cur.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass

        used_structure = False
        if callable(create_cc_chains_table):
            try:
                if create_cc_chains_table(conn):
                    migration_report['steps_completed'].append('✅ Tabela cc_chains utworzona (structure)')
                    used_structure = True
                else:
                    migration_report['errors'].append('❌ structure.create_cc_chains_table zwróciło False')
            except Exception as e:
                migration_report['errors'].append(f'❌ Błąd structure.create_cc_chains_table: {e}')

        # Zweryfikuj istnienie; jeśli brak – utwórz inline (fallback)
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cc_chains'")
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cc_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP
                )
            """)
            migration_report['steps_completed'].append(
                '✅ Tabela cc_chains utworzona (inline fallback)' if not used_structure
                else 'ℹ️ cc_chains potwierdzona/utworzona (inline)'
            )

        conn.commit()
        try:
            conn.close()
        except Exception:
            pass
        conn = None

        # --- KROK 2: Dodaj chain_id do options_cc (idempotentnie)
        chain_id_result = migrate_options_cc_add_chain_id()
        if chain_id_result.get('success'):
            migration_report['steps_completed'].append(f"✅ {chain_id_result.get('message')}")
        else:
            migration_report['errors'].append(f"❌ {chain_id_result.get('message')}")
            migration_report['success'] = False

        # --- KROK 3: Sprawdź status migracji i anomalia
        status_check = check_cc_chains_migration_status()
        if status_check.get('success'):
            migration_report['final_status'] = status_check.get('tables_status', {})
            if status_check.get('anomalies'):
                migration_report['anomalies'] = status_check['anomalies']
                # nie oznaczamy od razu jako fail – traktuj jako ostrzeżenia
                migration_report['steps_completed'].append('⚠️ Wykryto anomalie – sprawdź pole anomalies')
            if status_check.get('chains_overview') is not None:
                migration_report['chains_overview'] = status_check['chains_overview']
            migration_report['steps_completed'].append('✅ Weryfikacja migracji zakończona')
        else:
            migration_report['errors'].append(f"❌ {status_check.get('error')}")
            migration_report['success'] = False

        return migration_report

    except Exception as e:
        migration_report['success'] = False
        return migration_report
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def auto_detect_cc_chains():
    """
    🤖 PUNKT 74: Automatyczne tworzenie/przypisywanie CC Chains
    Zasady:
      - grupowanie po LOT (1 CC -> 1 LOT); CC rozbite na wiele LOT-ów jest pomijane (raportowane),
      - źródło prawdy: cc_lot_mappings; fallback: options_cc_reservations,
      - bez dotykania lots.quantity_open,
      - idempotentne uzupełnienie cc_chains o kolumny: lot_id, ticker, chain_name, start_date, status.
    Zwraca dict z licznikami i diagnostyką.
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia z bazą'}

        # Ułatwione nazwy kolumn (gdy możliwe)
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # --- 0) Przygotuj cc_chains: dołóż kolumny jeśli brakuje (idempotentnie)
        cur.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='cc_chains'""")
        has_chains = cur.fetchone() is not None
        if not has_chains:
            # Pełny schemat (jeśli tablica nie istnieje)
            cur.execute("""
                CREATE TABLE cc_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lot_id INTEGER,
                    ticker TEXT,
                    chain_name TEXT,
                    start_date DATE,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # Dołóż brakujące kolumny
            cur.execute("PRAGMA table_info(cc_chains)")
            cols = [r['name'] if isinstance(r, sqlite3.Row) else r[1] for r in (cur.fetchall() or [])]
            required = ['lot_id', 'ticker', 'chain_name', 'start_date', 'status']
            for col in required:
                if col not in cols:
                    cur.execute(f"ALTER TABLE cc_chains ADD COLUMN {col} {('INTEGER' if col=='lot_id' else ('DATE' if col=='start_date' else 'TEXT'))}")

        # Indeks po lot_id (przyspiesza lookup)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_chains_lot ON cc_chains(lot_id)")

        # --- 1) Ile CC bez chains?
        cur.execute("SELECT COUNT(*) AS c FROM options_cc WHERE chain_id IS NULL")
        cc_without_chains = int((cur.fetchone() or {'c': 0})['c'] or 0)

        # Dla debug: ile mapowań w nowej tabeli
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'")
        has_new_maps = cur.fetchone() is not None
        total_mappings = 0
        if has_new_maps:
            cur.execute("SELECT COUNT(*) AS c FROM cc_lot_mappings")
            total_mappings = int((cur.fetchone() or {'c': 0})['c'] or 0)

        if cc_without_chains == 0:
            return {
                'success': True,
                'chains_created': 0,
                'cc_assigned': 0,
                'skipped_multi_lot': [],
                'used_source': 'cc_lot_mappings' if has_new_maps else 'none',
                'message': f'✅ Wszystkie CC mają chain_id (mapowań: {total_mappings})'
            }

        # --- 2) Zbierz kandydata per CC -> LOT (tylko te CC, które mają dokładnie 1 LOT)
        cc_to_lot = {}           # cc_id -> lot_id (jednoznacznie)
        ambiguous_cc = []        # cc_id z >1 LOT
        used_source = None

        def _collect_from_mappings(table_name, qty_col_name):
            # zwraca (cc_to_lot, ambiguous_cc)
            _cc_to_lot = {}
            _ambiguous = set()

            # policz DISTINCT lotów na cc_id
            cur.execute(f"""
                SELECT cc.id AS cc_id, COUNT(DISTINCT m.lot_id) AS lot_cnt
                FROM options_cc cc
                JOIN {table_name} m ON m.cc_id = cc.id
                WHERE cc.chain_id IS NULL
                GROUP BY cc.id
            """)
            rows = cur.fetchall() or []
            one_lot_cc = set(int(r['cc_id']) for r in rows if int(r['lot_cnt'] or 0) == 1)
            many_lot_cc = set(int(r['cc_id']) for r in rows if int(r['lot_cnt'] or 0) > 1)

            if one_lot_cc:
                cur.execute(f"""
                    SELECT m.cc_id, m.lot_id
                    FROM {table_name} m
                    WHERE m.cc_id IN ({",".join("?"*len(one_lot_cc))})
                    GROUP BY m.cc_id
                """, tuple(one_lot_cc))
                for r in (cur.fetchall() or []):
                    _cc_to_lot[int(r['cc_id'])] = int(r['lot_id'])

            _ambiguous.update(many_lot_cc)
            return _cc_to_lot, sorted(_ambiguous)

        # priorytet: cc_lot_mappings
        if has_new_maps:
            used_source = 'cc_lot_mappings'
            cc_to_lot, ambiguous_cc = _collect_from_mappings('cc_lot_mappings', 'shares_reserved')

        # fallback: options_cc_reservations
        if not cc_to_lot:
            cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='options_cc_reservations'")
            has_old_maps = cur.fetchone() is not None
            if has_old_maps:
                used_source = 'options_cc_reservations'
                cc_to_lot, ambiguous_cc = _collect_from_mappings('options_cc_reservations', 'qty_reserved')

        # jeśli dalej nic nie znaleziono
        if not cc_to_lot:
            return {
                'success': True,
                'chains_created': 0,
                'cc_assigned': 0,
                'skipped_multi_lot': ambiguous_cc,
                'used_source': used_source or 'none',
                'message': f"🔍 {cc_without_chains} CC bez chain_id, ale brak jednoznacznych mapowań (sprawdź mapowania)."
            }

        # --- 3) Zbuduj listę LOT-ów i utwórz/pobierz chain dla każdego
        lot_ids = sorted(set(cc_to_lot.values()))
        lot_chain = {}   # lot_id -> chain_id
        chains_created = 0

        for lot_id in lot_ids:
            # pobierz ticker/buy_date dla nazwy łańcucha
            cur.execute("SELECT ticker, buy_date FROM lots WHERE id = ?", (lot_id,))
            row = cur.fetchone()
            if not row:
                # brak takiego lota – nie blokujemy całej operacji
                continue
            ticker = row['ticker']
            buy_date = row['buy_date']

            # Czy łańcuch już istnieje dla tego LOT-a?
            cur.execute("SELECT id FROM cc_chains WHERE lot_id = ? LIMIT 1", (lot_id,))
            r = cur.fetchone()
            if r:
                chain_id = int(r['id'])
                lot_chain[lot_id] = chain_id
                continue

            # wyznacz start_date = najwcześniejszy open_date CC korzystających z tego LOT-a
            cc_ids_for_lot = [cc for cc, l in cc_to_lot.items() if l == lot_id]
            if cc_ids_for_lot:
                cur.execute(f"""
                    SELECT MIN(open_date) AS start_date
                    FROM options_cc
                    WHERE id IN ({",".join("?"*len(cc_ids_for_lot))})
                """, tuple(cc_ids_for_lot))
                r2 = cur.fetchone()
                start_date = r2['start_date'] if r2 and r2['start_date'] else buy_date
            else:
                start_date = buy_date

            chain_name = f"{ticker} Chain (LOT #{lot_id})"

            cur.execute("""
                INSERT INTO cc_chains (lot_id, ticker, chain_name, start_date, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (lot_id, ticker, chain_name, start_date))
            chain_id = cur.lastrowid
            lot_chain[lot_id] = chain_id
            chains_created += 1

        # --- 4) Przypisz chain_id do CC (tylko jednoznaczne, bez wielo-lotowych)
        cc_assigned = 0
        skipped_multi = []

        try:
            cur.execute("BEGIN")
            # CC z >1 lot – pomijamy i raportujemy
            skipped_multi.extend(ambiguous_cc)

            # Jednoznaczne: przypisz
            for cc_id, lot_id in cc_to_lot.items():
                if cc_id in ambiguous_cc:
                    continue
                chain_id = lot_chain.get(lot_id)
                if not chain_id:
                    continue
                cur.execute("UPDATE options_cc SET chain_id = ? WHERE id = ? AND chain_id IS NULL", (chain_id, cc_id))
                if cur.rowcount:
                    cc_assigned += 1
            cur.execute("COMMIT")
        except Exception as txe:
            try: cur.execute("ROLLBACK")
            except Exception: pass
            return {'success': False, 'message': f'Błąd transakcji przypisywania: {txe}'}

        return {
            'success': True,
            'chains_created': chains_created,
            'cc_assigned': cc_assigned,
            'skipped_multi_lot': sorted(set(skipped_multi)),
            'used_source': used_source or 'none',
            'message': f'✅ Utworzono {chains_created} chains, przypisano {cc_assigned} CC'
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'message': f'❌ Błąd auto-detection: {e}',
            'error_details': traceback.format_exc()
        }
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def get_cc_chains_summary():
    """
    📊 PUNKT 74.1: Pobranie podsumowania wszystkich CC Chains

    Zwraca listę słowników:
      id, lot_id, ticker, chain_name, start_date, end_date, status,
      lot_buy_date, lot_total, lot_open, cc_count, open_cc_count,
      total_pl_pln, total_premium_pln
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return []

        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # Czy istnieje tabela cc_chains?
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cc_chains'")
        if cur.fetchone() is None:
            return []

        # Sprawdź kolumny w cc_chains (end_date może nie istnieć)
        cur.execute("PRAGMA table_info(cc_chains)")
        cc_cols = { (r['name'] if isinstance(r, sqlite3.Row) else r[1]) for r in (cur.fetchall() or []) }
        has_end_date = 'end_date' in cc_cols

        end_date_sql = "ch.end_date" if has_end_date else "NULL AS end_date"

        # Raport: LEFT JOIN na lots (żeby nie tracić chainów bez lota)
        query = f"""
            SELECT 
                ch.id                         AS id,
                ch.lot_id                     AS lot_id,
                COALESCE(ch.ticker, l.ticker) AS ticker,
                ch.chain_name                 AS chain_name,
                ch.start_date                 AS start_date,
                {end_date_sql}                ,
                ch.status                     AS status,
                l.buy_date                    AS lot_buy_date,
                l.quantity_total              AS lot_total,
                l.quantity_open               AS lot_open,
                COUNT(cc.id)                  AS cc_count,
                SUM(CASE WHEN cc.status = 'open' THEN 1 ELSE 0 END)                    AS open_cc_count,
                COALESCE(SUM(CASE WHEN cc.pl_pln IS NOT NULL THEN cc.pl_pln END), 0)   AS total_pl_pln,
                COALESCE(SUM(cc.premium_sell_pln), 0)                                   AS total_premium_pln
            FROM cc_chains ch
            LEFT JOIN lots l      ON l.id = ch.lot_id
            LEFT JOIN options_cc cc ON cc.chain_id = ch.id
            GROUP BY ch.id
            ORDER BY COALESCE(ch.ticker, l.ticker), l.buy_date DESC, ch.id
        """

        cur.execute(query)
        rows = cur.fetchall() or []

        # Konwersja do listy dict
        out = []
        for r in rows:
            # Dla kompatybilności z wcześniejszym formatem kluczy:
            out.append({
                'id':               r['id'],
                'lot_id':           r['lot_id'],
                'ticker':           r['ticker'],
                'chain_name':       r['chain_name'],
                'start_date':       r['start_date'],
                'end_date':         (r['end_date'] if has_end_date else None),
                'status':           r['status'],
                'lot_buy_date':     r['lot_buy_date'],
                'lot_total':        r['lot_total'],
                'lot_open':         r['lot_open'],
                'cc_count':         int(r['cc_count'] or 0),
                'open_cc_count':    int(r['open_cc_count'] or 0),
                'total_pl_pln':     float(r['total_pl_pln'] or 0.0),
                'total_premium_pln':float(r['total_premium_pln'] or 0.0)
            })
        return out

    except Exception:
        # Bez wycieku stacktrace w UI; zwróć pustą listę (funkcja „summary”).
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def update_chain_statistics(chain_id):
    """
    📊 PUNKT 74.2: Aktualizuje statystyki chain na podstawie przypisanych CC
    """
    import sqlite3

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {'success': False, 'message': 'Brak połączenia'}
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        cur = conn.cursor()

        # --- Upewnij się, że tabela cc_chains istnieje
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cc_chains'")
        if cur.fetchone() is None:
            return {'success': False, 'message': 'Brak tabeli cc_chains'}

        # --- Dołóż brakujące kolumny idempotentnie
        cur.execute("PRAGMA table_info(cc_chains)")
        existing_cols = { (r['name'] if isinstance(r, sqlite3.Row) else r[1]) for r in (cur.fetchall() or []) }

        needed = {
            'end_date':            'DATE',
            'updated_at':          'TIMESTAMP',
            'status':              'TEXT',
            'cc_count':            'INTEGER',
            'total_contracts':     'INTEGER',
            'total_premium_pln':   'REAL',
            'total_premium_usd':   'REAL',
            'total_pl_pln':        'REAL',
            'avg_duration_days':   'REAL',
            'success_rate':        'REAL',
            'annualized_return':   'REAL',
        }
        for col, typ in needed.items():
            if col not in existing_cols:
                cur.execute(f"ALTER TABLE cc_chains ADD COLUMN {col} {typ}")

        # --- Statystyki z options_cc dla danego chain_id
        cur.execute("""
            SELECT
                COUNT(*)                                      AS cc_count,
                COALESCE(SUM(contracts), 0)                   AS total_contracts,
                COALESCE(SUM(premium_sell_pln), 0.0)          AS total_premium_pln,
                COALESCE(SUM(pl_pln), 0.0)                    AS total_pl_pln,
                AVG(JULIANDAY(COALESCE(close_date, expiry_date)) - JULIANDAY(open_date)) AS avg_duration_days,
                MAX(COALESCE(close_date, expiry_date))        AS last_activity_date
            FROM options_cc
            WHERE chain_id = ? AND status IN ('open','expired','bought_back')
        """, (chain_id,))
        s = cur.fetchone()
        if not s or (s['cc_count'] or 0) == 0:
            return {'success': False, 'message': 'Brak danych dla chain'}

        cc_count           = int(s['cc_count'] or 0)
        total_contracts    = int(s['total_contracts'] or 0)
        total_premium_pln  = float(s['total_premium_pln'] or 0.0)
        total_pl_pln       = float(s['total_pl_pln'] or 0.0)
        avg_duration_days  = float(s['avg_duration_days'] or 0.0) if s['avg_duration_days'] is not None else 0.0
        last_activity_date = s['last_activity_date']

        # --- Success rate tylko na zamkniętych
        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN pl_pln > 0 THEN 1 ELSE 0 END), 0) AS wins,
                COALESCE(SUM(CASE WHEN status IN ('expired','bought_back') THEN 1 ELSE 0 END), 0) AS closed
            FROM options_cc
            WHERE chain_id = ?
        """, (chain_id,))
        r = cur.fetchone()
        wins   = int(r['wins'] or 0)
        closed = int(r['closed'] or 0)
        success_rate = (wins * 100.0 / closed) if closed > 0 else 0.0

        # --- Jeśli mamy kolumnę total_premium_usd, policz NETTO USD z cashflow (option_premium)
        total_premium_usd_cf = None
        if 'total_premium_usd' in needed and 'total_premium_usd' in existing_cols:
            cur.execute("""
                SELECT COALESCE(SUM(c.amount_usd), 0.0) AS sum_prem_usd
                FROM cashflows c
                JOIN options_cc oc ON oc.id = c.ref_id
                WHERE c.ref_table='options_cc'
                  AND c.type='option_premium'
                  AND oc.chain_id = ?
            """, (chain_id,))
            rp = cur.fetchone()
            total_premium_usd_cf = float(rp['sum_prem_usd'] or 0.0)

        # --- Czy są otwarte CC? (status chain + end_date)
        cur.execute("SELECT COUNT(*) AS open_cnt FROM options_cc WHERE chain_id = ? AND status='open'", (chain_id,))
        open_cnt = int((cur.fetchone() or {'open_cnt': 0})['open_cnt'] or 0)
        chain_status = 'active' if open_cnt > 0 else 'closed'
        end_date = None if open_cnt > 0 else last_activity_date

        # --- Annualized return (ostrożnie)
        # użyj total_premium_pln jako "kapitału pracującego"; jeśli 0 albo avg_duration=0 => 0
        if total_premium_pln > 0.0 and avg_duration_days and avg_duration_days > 0.0:
            annualized_return = (total_pl_pln / total_premium_pln) * (365.0 / avg_duration_days) * 100.0
        else:
            annualized_return = 0.0

        # --- Dynamiczny UPDATE tylko kolumn istniejących
        set_parts = []
        params = []

        # zawsze bezpieczne:
        if 'cc_count' in existing_cols:
            set_parts.append("cc_count = ?");                 params.append(cc_count)
        if 'total_contracts' in existing_cols:
            set_parts.append("total_contracts = ?");          params.append(total_contracts)
        if 'total_premium_pln' in existing_cols:
            set_parts.append("total_premium_pln = ?");        params.append(round(total_premium_pln, 2))
        if 'total_pl_pln' in existing_cols:
            set_parts.append("total_pl_pln = ?");             params.append(round(total_pl_pln, 2))
        if 'avg_duration_days' in existing_cols:
            set_parts.append("avg_duration_days = ?");        params.append(round(avg_duration_days, 2))
        if 'success_rate' in existing_cols:
            set_parts.append("success_rate = ?");             params.append(round(success_rate, 2))
        if 'annualized_return' in existing_cols:
            set_parts.append("annualized_return = ?");        params.append(round(annualized_return, 2))
        if 'end_date' in existing_cols:
            set_parts.append("end_date = ?");                 params.append(end_date)
        if 'status' in existing_cols:
            set_parts.append("status = ?");                   params.append(chain_status)
        if 'updated_at' in existing_cols:
            set_parts.append("updated_at = CURRENT_TIMESTAMP")

        # opcjonalnie USD (z cashflow)
        if 'total_premium_usd' in existing_cols and total_premium_usd_cf is not None:
            set_parts.append("total_premium_usd = ?");        params.append(round(total_premium_usd_cf, 2))

        if not set_parts:
            return {'success': False, 'message': 'Brak kolumn do aktualizacji w cc_chains'}

        params.append(chain_id)
        sql = f"UPDATE cc_chains SET {', '.join(set_parts)} WHERE id = ?"
        cur.execute(sql, tuple(params))

        conn.commit()
        try:
            conn.close()
        except Exception:
            pass

        return {
            'success': True,
            'message': f"✅ Statystyki chain #{chain_id} zaktualizowane",
            'stats': {
                'total_pl': round(total_pl_pln, 2),
                'cc_count': cc_count,
                'status': chain_status
            }
        }

    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return {'success': False, 'message': f'Błąd aktualizacji: {str(e)}'}


# Test na końcu pliku (opcjonalny)
if __name__ == "__main__":
    print("Test funkcji buyback/expiry...")
    results = test_buyback_expiry_operations()
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")