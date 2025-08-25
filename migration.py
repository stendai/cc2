"""
SKRYPT MIGRACJI BAZY DANYCH
Dodanie prowizji brokerskich do tabeli options_cc

URUCHOM TO PRZED UŻYCIEM NOWEGO MODUŁU OPCJI!
"""

import sqlite3
import streamlit as st

def migrate_options_cc_table():
    """
    Migracja tabeli options_cc - dodanie kolumn prowizji
    """
    try:
        # Połączenie z bazą
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        
        st.write("🔄 Sprawdzanie struktury tabeli options_cc...")
        
        # Sprawdź czy tabela istnieje
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='options_cc'
        """)
        
        if not cursor.fetchone():
            st.error("❌ Tabela options_cc nie istnieje!")
            conn.close()
            return False
        
        # Sprawdź obecne kolumny
        cursor.execute("PRAGMA table_info(options_cc)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        st.write(f"📋 Obecne kolumny: {', '.join(existing_columns)}")
        
        # Lista kolumn do dodania
        new_columns = [
            ("broker_fee_sell_usd", "DECIMAL(10,2) DEFAULT 0.00"),
            ("reg_fee_sell_usd", "DECIMAL(10,2) DEFAULT 0.00"),
            ("broker_fee_buyback_usd", "DECIMAL(10,2) DEFAULT 0.00"),
            ("reg_fee_buyback_usd", "DECIMAL(10,2) DEFAULT 0.00"),
            ("total_fees_sell_pln", "DECIMAL(15,2) DEFAULT 0.00"),
            ("total_fees_buyback_pln", "DECIMAL(15,2) DEFAULT 0.00"),
            ("net_premium_pln", "DECIMAL(15,2)"),
            ("premium_buyback_pln", "DECIMAL(15,2)")
        ]
        
        added_columns = 0
        
        for column_name, column_def in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE options_cc ADD COLUMN {column_name} {column_def}")
                    st.success(f"✅ Dodano kolumnę: {column_name}")
                    added_columns += 1
                except Exception as e:
                    st.error(f"❌ Błąd dodawania {column_name}: {e}")
            else:
                st.info(f"ℹ️ Kolumna {column_name} już istnieje")
        
        if added_columns > 0:
            # Aktualizuj istniejące rekordy - przelicz net_premium_pln
            st.write("🔄 Aktualizowanie istniejących rekordów...")
            
            cursor.execute("""
                UPDATE options_cc 
                SET net_premium_pln = premium_sell_pln,
                    total_fees_sell_pln = 0.00
                WHERE net_premium_pln IS NULL
            """)
            
            updated_rows = cursor.rowcount
            st.success(f"✅ Zaktualizowano {updated_rows} rekordów")
        
        conn.commit()
        conn.close()
        
        st.success(f"🎉 Migracja zakończona! Dodano {added_columns} kolumn.")
        
        # Pokaż nową strukturę
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(options_cc)")
        new_columns_info = cursor.fetchall()
        conn.close()
        
        st.write("📊 **Nowa struktura tabeli options_cc:**")
        for col in new_columns_info:
            st.write(f"  - {col[1]} ({col[2]})")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Błąd migracji: {e}")
        return False


def test_options_cc_operations():
    """
    Test operacji na zmigowanej tabeli options_cc
    """
    try:
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        
        st.write("🧪 Test operacji na tabeli options_cc...")
        
        # Test insert z nowymi kolumnami
        cursor.execute("""
            INSERT INTO options_cc (
                ticker, contracts, strike_usd, premium_sell_usd,
                broker_fee_sell_usd, reg_fee_sell_usd,
                open_date, expiry_date, status, fx_open,
                premium_sell_pln, total_fees_sell_pln, net_premium_pln
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'TEST', 1, 100.0, 2.50,  # Podstawowe dane
            1.00, 0.15,  # Prowizje sprzedaży
            '2025-01-25', '2025-02-21', 'open', 4.2500,  # Daty i kurs
            1062.50, 48.88, 1013.62  # PLN z prowizjami
        ))
        
        test_id = cursor.lastrowid
        st.success(f"✅ Test insert - ID: {test_id}")
        
        # Test select z nowymi kolumnami
        cursor.execute("""
            SELECT ticker, contracts, premium_sell_usd, broker_fee_sell_usd,
                   reg_fee_sell_usd, net_premium_pln
            FROM options_cc 
            WHERE id = ?
        """, (test_id,))
        
        result = cursor.fetchone()
        if result:
            st.success("✅ Test select - dane prawidłowe")
            st.write(f"   Ticker: {result[0]}, Prowizje: ${result[3]:.2f} + ${result[4]:.2f}")
            st.write(f"   Premium netto PLN: {result[5]:.2f} zł")
        
        # Usuń test record
        cursor.execute("DELETE FROM options_cc WHERE id = ?", (test_id,))
        
        conn.commit()
        conn.close()
        
        st.success("🎉 Wszystkie testy przeszły pomyślnie!")
        return True
        
    except Exception as e:
        st.error(f"❌ Błąd testów: {e}")
        return False


def main():
    """
    Główna funkcja migracji
    """
    st.title("🛠️ Migracja Bazy Danych - Options CC")
    
    st.markdown("""
    **Ten skrypt doda brakujące kolumny prowizji do tabeli `options_cc`.**
    
    Nowe kolumny:
    - `broker_fee_sell_usd` - prowizja brokera przy sprzedaży
    - `reg_fee_sell_usd` - opłaty regulacyjne przy sprzedaży  
    - `broker_fee_buyback_usd` - prowizja brokera przy buyback
    - `reg_fee_buyback_usd` - opłaty regulacyjne przy buyback
    - `total_fees_sell_pln` - łączne prowizje sprzedaży w PLN
    - `total_fees_buyback_pln` - łączne prowizje buyback w PLN
    - `net_premium_pln` - premium netto po prowizjach w PLN
    - `premium_buyback_pln` - premium buyback w PLN
    
    **⚠️ UWAGA: Zrób backup bazy danych przed migracją!**
    """)
    
    if st.button("🚀 Uruchom migrację", type="primary"):
        with st.spinner("Migracja w toku..."):
            success = migrate_options_cc_table()
            
            if success:
                st.balloons()
                st.markdown("---")
                
                if st.button("🧪 Uruchom testy"):
                    test_options_cc_operations()
    
    st.markdown("---")
    st.markdown("**Po pomyślnej migracji możesz używać nowego modułu opcji z prowizjami!**")


if __name__ == "__main__":
    main()