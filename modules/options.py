import streamlit as st
import sys
import os
from datetime import date, timedelta, datetime
import pandas as pd

# Dodaj katalog główny do path
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modułów
try:
    import db
    import nbp_api_client
    from utils.formatting import format_currency_usd, format_currency_pln, format_date
except ImportError as e:
    st.error(f"Błąd importu modułów: {e}")

def show_options():
    """Główna funkcja modułu Options - PUNKT 67: CLEANUP UI"""
    
    st.header("🎯 Options - Covered Calls")
    st.markdown("*Profesjonalne zarządzanie opcjami pokrytymi z rezerwacjami FIFO*")
    
    # CLEANUP: Usunięto deweloperskie komunikaty success
    # st.success("🚀 **PUNKTY 51-56 UKOŃCZONE** - Sprzedaż, buyback i expiry CC!")
    
    # Status systemu (uproszczony)
    try:
        lots_stats = db.get_lots_stats()
        cc_stats = db.get_cc_reservations_summary()
        
        col_status1, col_status2 = st.columns(2)
        
        with col_status1:
            if lots_stats['open_shares'] > 0:
                st.success(f"✅ **{lots_stats['open_shares']} akcji dostępnych**")
            else:
                st.error("❌ **Brak akcji** - dodaj LOT-y w module Stocks")
        
        with col_status2:
            open_cc_count = cc_stats.get('open_cc_count', 0)
            if open_cc_count > 0:
                st.info(f"🎯 **{open_cc_count} otwartych CC**")
            else:
                st.info("📝 **Brak otwartych CC**")
        
    except Exception as e:
        st.error(f"❌ Błąd systemu: {e}")
    
    # CLEANUP: Zakładki bez zmian (już zrobione w punkcie 65)
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Sprzedaż CC", 
        "💰 Buyback & Expiry", 
        "📊 Otwarte CC", 
        "📋 Historia CC",
        "🛠️ Diagnostyka"
    ])
    
    with tab1:
        show_sell_cc_tab()
    
    with tab2:
        show_buyback_expiry_tab()
    
    with tab3:
        show_open_cc_tab()
    
    with tab4:
        show_cc_history_tab()  # Nowa wersja z PUNKT 67
        
    with tab5:
        show_reservations_diagnostics_tab()

def show_sell_cc_tab():
    
    st.subheader("🎯 Sprzedaż Covered Calls")
    
def show_sell_cc_tab():
    """Tab sprzedaży Covered Calls - ROZSZERZONY O POPRAWIONY PRZYCISK"""
    st.subheader("🎯 Sprzedaż Covered Calls")
    
    # ===== ZAKTUALIZOWANY PRZYCISK ZWALNIANIA =====
    st.markdown("---")
    col_tools1, col_tools2, col_tools3 = st.columns([2, 2, 1])
    
    with col_tools1:
        st.markdown("### 🔓 Narzędzia zarządzania")
        if st.button("🔓 Zwolnij odkupione opcje", key="release_bought_back_cc", 
                     help="Zwalnia akcje z bought_back CC (obie tabele)"):
            with st.spinner("Zwalnianie akcji z odkupionych CC..."):
                try:
                    result = db.mass_fix_bought_back_cc_reservations()
                    
                    if result['success']:
                        fixed_count = result.get('fixed_count', 0)
                        shares_released = result.get('shares_released', 0)
                        
                        if fixed_count > 0:
                            st.success(f"✅ {result['message']}")
                            st.balloons()
                        else:
                            st.info("ℹ️ Wszystkie akcje już są prawidłowo zwolnione")
                    else:
                        st.error(f"❌ Błąd zwalniania: {result.get('message', 'Nieznany błąd')}")
                        
                except Exception as e:
                    st.error(f"❌ Błąd systemu: {str(e)}")
    
    with col_tools2:
        # Zaktualizowany status check
        if st.button("🔍 Sprawdź status CC", key="check_cc_status"):
            try:
                status = db.get_blocked_cc_status()
                
                if 'error' in status:
                    st.error(f"❌ {status['error']}")
                elif status['has_problems']:
                    st.warning(f"⚠️ {status['blocked_cc_count']} CC blokuje {status['blocked_shares']} akcji")
                    for detail in status['details']:
                        st.caption(f"• {detail}")
                else:
                    st.success("✅ Wszystkie odkupione CC są prawidłowo zwolnione")
                    
            except Exception as e:
                st.error(f"❌ Błąd sprawdzania: {str(e)}")
    
    with col_tools3:
        # Zaktualizowany status indicator
        try:
            status = db.get_blocked_cc_status()
            
            if 'error' in status:
                st.error("❌")
                st.caption("Błąd sprawdzania")
            elif status['has_problems']:
                st.error(f"⚠️ {status['blocked_cc_count']}")
                st.caption("Zablokowanych CC")
            else:
                st.success("✅ OK")
                st.caption("Wszystkie zwolnione")
                
        except:
            st.info("❓")
            st.caption("Sprawdź status")
    
    st.markdown("---")
    # ===== KONIEC ZAKTUALIZOWANEGO PRZYCISKU =====
    
    # ... reszta funkcji bez zmian ...
    """Tab sprzedaży Covered Calls - PUNKTY 53-54: Kompletny formularz"""
    st.subheader("🎯 Sprzedaż Covered Calls")
    st.success("✅ **PUNKTY 53-54 UKOŃCZONE** - Formularz sprzedaży CC z zapisem")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📝 Formularz sprzedaży CC")
        
        # Pobierz dostępne tickery do wyboru
        available_tickers = get_available_tickers_for_cc()
        
        if not available_tickers:
            st.error("❌ **Brak akcji dostępnych do pokrycia CC**")
            st.info("💡 Dodaj LOT-y akcji w module Stocks przed sprzedażą CC")
            return
        
        # FORMULARZ SPRZEDAŻY CC
        with st.form("sell_cc_form"):
            st.info("💡 **1 kontrakt CC = 100 akcji pokrycia**")
            
            # Wybór tickera z dropdowna
            ticker_options = [f"{ticker} ({shares} akcji → {shares//100} kontraktów)" 
                            for ticker, shares in available_tickers]
            
            selected_ticker_option = st.selectbox(
                "Ticker akcji:",
                options=ticker_options,
                help="Wybierz akcje do pokrycia covered call"
            )
            
            col_dates1, col_dates2 = st.columns(2)

            with col_dates1:
                sell_date = st.date_input(
                    "Data sprzedaży:",
                    value=date.today() - timedelta(days=30)
                )

            with col_dates2:
                expiry_date = st.date_input(
                    "Data expiry:", 
                    value=date.today() + timedelta(days=30)
                )
            
                
            
            # Wyciągnij ticker z opcji
            # I ZAMIEŃ je NA:
            selected_ticker = selected_ticker_option.split(' ')[0] if selected_ticker_option else None

            # 🔧 NAPRAWKA: Sprawdź dostępność na datę CC
            if selected_ticker and sell_date:
                # Używaj naprawionej funkcji chronologii
                test_coverage = db.check_cc_coverage_with_chronology(selected_ticker, 10, sell_date)
                max_contracts_on_date = test_coverage.get('shares_available', 0) // 100
                
                if max_contracts_on_date > 0:
                    st.success(f"✅ Na {sell_date}: dostępne {test_coverage.get('shares_available')} akcji = max {max_contracts_on_date} kontraktów")
                else:
                    st.error(f"❌ Na {sell_date}: brak dostępnych akcji {selected_ticker}")
                    debug_info = test_coverage.get('debug_info', {})
                    st.error(f"   Posiadane: {debug_info.get('owned_on_date', 0)}")
                    st.error(f"   Sprzedane przed: {debug_info.get('sold_before', 0)}")
                    st.error(f"   Zarezerwowane przed: {debug_info.get('cc_reserved_before', 0)}")
            else:
                max_contracts_on_date = 1

            col_form1, col_form2 = st.columns(2)
            
            with col_form1:
                # 🔧 NAPRAWIONA walidacja kontraktów
                contracts = st.number_input(
                    "Liczba kontraktów CC:",
                    min_value=1,
                    max_value=max(1, max_contracts_on_date) if selected_ticker and sell_date else 10,
                    value=min(3, max_contracts_on_date) if max_contracts_on_date >= 3 else 1,
                    help=f"Na {sell_date}: maksymalnie {max_contracts_on_date} kontraktów" if selected_ticker and sell_date else "Wybierz datę i ticker"
                )
                
                # Strike price (bez zmian)
                strike_price = st.number_input(
                    "Strike price USD:",
                    min_value=0.01,
                    value=60.00,  # 🔧 Ustaw na Twoją wartość
                    step=0.01,
                    format="%.2f"
                )
            
            with col_form2:
                # Premium (bez zmian)
                premium_received = st.number_input(
                    "Premium otrzymana USD:",
                    min_value=0.01,
                    value=5.00,  # 🔧 Ustaw na Twoją wartość
                    step=0.01,
                    format="%.2f"
                )
                        # ✅ DODAJ PROWIZJE W OSOBNEJ SEKCJI:
            st.markdown("**💰 Prowizje brokerskie:**")
            col_fee1, col_fee2 = st.columns(2)

            with col_fee1:
                broker_fee = st.number_input(
                    "Prowizja brokera USD:",
                    min_value=0.00,
                    value=1.00,
                    step=0.01,
                    format="%.2f",
                    help="Prowizja IBKR za sprzedaż opcji"
                )

            with col_fee2:
                reg_fee = st.number_input(
                    "Opłaty regulacyjne USD:",
                    min_value=0.00,
                    value=0.15,
                    step=0.01,
                    format="%.2f", 
                    help="Regulatory fees (SEC, FINRA)"
                )



            
            # Przycisk sprawdzenia pokrycia
            check_coverage = st.form_submit_button("🔍 Sprawdź pokrycie i podgląd", use_container_width=True)
        
        # SPRAWDZENIE POKRYCIA - POZA FORMEM
        if check_coverage and selected_ticker and contracts:
            st.session_state.cc_form_data = {
                'ticker': selected_ticker,
                'contracts': contracts,
                'strike_price': strike_price,
                'premium_received': premium_received,
                'broker_fee': broker_fee,
                'reg_fee': reg_fee,
                'expiry_date': expiry_date,
                'sell_date': sell_date
            }
            st.session_state.show_cc_preview = True
    
    with col2:
        st.markdown("### 📊 Dostępne akcje")
        
        # Pokaż tabelę dostępnych akcji
        if available_tickers:
            ticker_data = []
            for ticker, shares in available_tickers:
                max_cc = shares // 100
                ticker_data.append({
                    'Ticker': ticker,
                    'Akcje': f"{shares:,}",
                    'Max CC': max_cc,
                    'Status': "✅ Dostępne" if max_cc > 0 else "⚠️ Za mało"
                })
            
            st.dataframe(ticker_data, use_container_width=True)
        
        # Statystyki CC
        st.markdown("### 🎯 Statystyki CC")
        cc_stats = db.get_cc_reservations_summary()
        
        if cc_stats.get('open_cc_count', 0) > 0:
            st.write(f"📊 **Otwarte CC**: {cc_stats['open_cc_count']}")
            st.write(f"🎯 **Kontrakty**: {cc_stats['total_contracts']}")
            st.write(f"📦 **Zarezerwowane**: {cc_stats['shares_reserved']} akcji")
        else:
            st.info("💡 Brak otwartych pozycji CC")
    
    # PODGLĄD CC - POZA KOLUMNAMI
    if 'show_cc_preview' in st.session_state and st.session_state.show_cc_preview:
        if 'cc_form_data' in st.session_state:
            st.markdown("---")
            show_cc_sell_preview(st.session_state.cc_form_data)
    
    

def get_available_tickers_for_cc():
    """Pobiera tickery z dostępnymi akcjami do pokrycia CC - NAPRAWIONE: uwzględnia datę CC"""
    try:
        conn = db.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # 🔧 NAPRAWKA: Pobierz wszystkie tickery, nie filtruj po quantity_open
        cursor.execute("""
            SELECT ticker, SUM(quantity_total) as total_owned
            FROM lots 
            GROUP BY ticker
            HAVING SUM(quantity_total) >= 100
            ORDER BY ticker
        """)
        
        tickers = cursor.fetchall()
        conn.close()
        
        return [(ticker, shares) for ticker, shares in tickers]
        
    except Exception as e:
        st.error(f"Błąd pobierania tickerów: {e}")
        return []

# DODAJ DO OPCJI DEBUG w show_cc_sell_preview (zamiast skomplikowanego debug)

# DODAJ DO OPCJI DEBUG w show_cc_sell_preview (zamiast skomplikowanego debug)

def show_cc_sell_preview(form_data):
    import streamlit as st  # 🔧 NAPRAWKA importu
    
    st.markdown("### 🎯 Podgląd sprzedaży Covered Call")
    
    ticker = form_data['ticker']
    contracts = form_data['contracts']
    sell_date = form_data['sell_date']
    
    # 🔍 PROSTY DEBUG - sprawdź bezpośrednio w bazie
    st.markdown("### 🚨 DEBUG: Sprawdzenie bazy danych")
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 🔧 ZDEFINIUJ WSZYSTKIE ZMIENNE NA POCZĄTKU
        total_reserved = 0
        total_sold_before = 0
        total_on_date = 0
        
        # 1. Wszystkie LOT-y tego tickera
        cursor.execute("""
            SELECT id, buy_date, quantity_total, quantity_open, buy_price_usd
            FROM lots 
            WHERE ticker = ? 
            ORDER BY buy_date, id
        """, (ticker,))
        
        all_lots = cursor.fetchall()
        st.write(f"**🔍 Wszystkie LOT-y {ticker}:**")
        for lot in all_lots:
            lot_id, buy_date, qty_total, qty_open, buy_price = lot
            st.write(f"- LOT #{lot_id}: kup {buy_date}, total={qty_total}, open={qty_open}, cena=${buy_price}")
        
        # 2. Sprawdź które LOT-y były dostępne na 1 sierpnia
        cursor.execute("""
            SELECT id, buy_date, quantity_total, quantity_open 
            FROM lots 
            WHERE ticker = ? AND buy_date <= ?
            ORDER BY buy_date, id
        """, (ticker, sell_date))
        
        lots_on_date = cursor.fetchall()
        st.write(f"**📅 LOT-y dostępne na {sell_date}:**")
        for lot in lots_on_date:
            lot_id, buy_date, qty_total, qty_open = lot
            total_on_date += qty_total  # 🔧 UŻYWAJ JUŻ ZDEFINIOWANEJ ZMIENNEJ
            st.write(f"- LOT #{lot_id}: {buy_date} → {qty_total} akcji")
        
        st.success(f"✅ **RAZEM na {sell_date}: {total_on_date} akcji**")
        
        # 3. Sprawdź sprzedaże PRZED datą CC
        cursor.execute("""
            SELECT st.sell_date, sts.qty_from_lot, sts.lot_id
            FROM stock_trades st
            JOIN stock_trade_splits sts ON st.id = sts.trade_id
            JOIN lots l ON sts.lot_id = l.id
            WHERE l.ticker = ? AND st.sell_date < ?
            ORDER BY st.sell_date
        """, (ticker, sell_date))
        
        sells_before = cursor.fetchall()
        st.write(f"**💸 Sprzedaże przed {sell_date}:**")
        for sell in sells_before:
            sell_date_db, qty_sold, lot_id = sell
            total_sold_before += qty_sold  # 🔧 UŻYWAJ JUŻ ZDEFINIOWANEJ ZMIENNEJ
            st.write(f"- {sell_date_db}: sprzedano {qty_sold} z LOT #{lot_id}")
        
        # 4. Sprawdź WSZYSTKIE CC (nie tylko przed datą)
        cursor.execute("""
            SELECT id, open_date, contracts, expiry_date, status
            FROM options_cc 
            WHERE ticker = ?
            ORDER BY open_date
        """, (ticker,))
        
        cc_before = cursor.fetchall()
        st.write(f"**🎯 WSZYSTKIE CC {ticker}:**")
        total_cc_shares_before = 0
        for cc in cc_before:
            cc_id, open_date, contracts, expiry_date, status = cc
            cc_shares = contracts * 100
            total_cc_shares_before += cc_shares
            st.write(f"- CC #{cc_id}: {open_date} → {contracts} kontr. ({cc_shares} akcji), status={status}")
        
        # PODSUMOWANIE
        available_on_date = total_on_date - total_sold_before - total_reserved  # Używaj total_reserved
        
        st.markdown("---")
        st.markdown("### 📊 PODSUMOWANIE:")
        st.write(f"🏪 **Posiadane na {sell_date}**: {total_on_date} akcji")
        st.write(f"💸 **Sprzedane przed**: {total_sold_before} akcji") 
        st.write(f"📦 **FAKTYCZNIE zarezerwowane**: {total_reserved} akcji")
        st.write(f"🔢 **quantity_open w LOT-ie**: {all_lots[0][3] if all_lots else 0}")
        st.write(f"✅ **DOSTĘPNE**: {available_on_date} akcji")
        st.write(f"🎯 **POTRZEBNE**: {contracts * 100} akcji")
        
        if available_on_date >= contracts * 100:
            st.success(f"✅ **WYSTARCZY!** Można wystawić {contracts} CC")
        else:
            st.error(f"❌ **BRAKUJE** {contracts * 100 - available_on_date} akcji")
        
        # 🚨 PRZYCISK NAPRAWCZY
        st.markdown("---")
        if st.button("🔧 NAPRAW bought_back CC - zwolnij zablokowane akcje", key="fix_bought_back"):
            with st.spinner("Naprawianie bought_back CC..."):
                try:
                    # Znajdź wszystkie bought_back CC które nadal mają rezerwacje
                    cursor.execute("""
                        SELECT DISTINCT ocr.cc_id
                        FROM options_cc_reservations ocr
                        JOIN options_cc oc ON ocr.cc_id = oc.id
                        WHERE oc.status IN ('bought_back', 'expired')
                    """)
                    
                    bad_cc_ids = [row[0] for row in cursor.fetchall()]
                    fixed_count = 0
                    
                    for cc_id in bad_cc_ids:
                        # Pobierz rezerwacje dla tego CC
                        cursor.execute("""
                            SELECT lot_id, qty_reserved
                            FROM options_cc_reservations
                            WHERE cc_id = ?
                        """, (cc_id,))
                        
                        reservations_to_fix = cursor.fetchall()
                        
                        for lot_id, qty_reserved in reservations_to_fix:
                            # Zwolnij akcje w LOT-ie
                            cursor.execute("""
                                UPDATE lots 
                                SET quantity_open = quantity_open + ?
                                WHERE id = ?
                            """, (qty_reserved, lot_id))
                        
                        # Usuń rezerwacje
                        cursor.execute("""
                            DELETE FROM options_cc_reservations
                            WHERE cc_id = ?
                        """, (cc_id,))
                        
                        fixed_count += 1
                    
                    conn.commit()
                    st.success(f"✅ Naprawiono {fixed_count} bought_back/expired CC!")
                    st.info("🔄 Odśwież stronę aby zobaczyć zmiany")
                    
                except Exception as e:
                    conn.rollback()
                    st.error(f"Błąd naprawki: {e}")
        # DODAJ TO w debug sekcji ZARAZ PO "🚨 PRZYCISK NAPRAWCZY" 

        # 🔍 DODATKOWA DIAGNOSTYKA - dlaczego quantity_open=0?
        st.markdown("### 🔍 DLACZEGO quantity_open=0?")
        
        # Sprawdź czy istnieje inna tabela mapowań
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%mapping%' OR name LIKE '%reservation%'
        """)
        mapping_tables = cursor.fetchall()
        st.write("**Tabele mapowań w bazie:**", [t[0] for t in mapping_tables])
        
        # Sprawdź historię quantity_open tego LOT-a
        lot_id = all_lots[0][0] if all_lots else None
        if lot_id:
            st.write(f"**Historia LOT #{lot_id}:**")
            st.write(f"- quantity_total: {all_lots[0][2]}")
            st.write(f"- quantity_open: {all_lots[0][3]}")
            
            # Sprawdź sprzedaże z tego LOT-a
            cursor.execute("""
                SELECT sts.trade_id, sts.qty_from_lot, st.sell_date
                FROM stock_trade_splits sts
                JOIN stock_trades st ON sts.trade_id = st.id
                WHERE sts.lot_id = ?
                ORDER BY st.sell_date
            """, (lot_id,))
            
            lot_sales = cursor.fetchall()
            total_sold_from_lot = sum(sale[1] for sale in lot_sales)
            st.write(f"**Sprzedaże z LOT #{lot_id}:**")
            for sale in lot_sales:
                st.write(f"- Trade #{sale[0]}: sprzedano {sale[1]} na {sale[2]}")
            st.write(f"- **RAZEM sprzedane**: {total_sold_from_lot}")
            
            # OBLICZ co POWINNO być w quantity_open
            expected_open = all_lots[0][2] - total_sold_from_lot  # total - sprzedane
            actual_open = all_lots[0][3]
            difference = expected_open - actual_open
            
            st.write(f"**ANALIZA:**")
            st.write(f"- Powinno być quantity_open: {expected_open}")  
            st.write(f"- Faktycznie jest: {actual_open}")
            st.write(f"- **RÓŻNICA: {difference}** ← To jest zablokowane pod CC!")
            
            if difference > 0:
                st.error(f"❌ **{difference} akcji jest gdzieś zablokowane ale nie widać gdzie!**")
                

                
        # Sprawdź czy są jakieś inne dziwne tabele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [t[0] for t in cursor.fetchall()]
        st.write("**Wszystkie tabele:**", all_tables)
        # DODAJ TO w debug sekcji ZARAZ PO "Wszystkie tabele:"

        # 🔍 SPRAWDŹ cc_lot_mappings
        st.markdown("### 🔍 Sprawdzenie tabeli cc_lot_mappings")
        cursor.execute("""
            SELECT clm.cc_id, clm.lot_id, clm.shares_reserved, oc.status, oc.ticker
            FROM cc_lot_mappings clm
            JOIN options_cc oc ON clm.cc_id = oc.id
            WHERE oc.ticker = ?
            ORDER BY clm.cc_id
        """, (ticker,))
        
        cc_mappings = cursor.fetchall()
        if cc_mappings:
            st.write("**🔍 Mapowania w cc_lot_mappings:**")
            total_in_mappings = 0
            for mapping in cc_mappings:
                cc_id, lot_id, shares_reserved, cc_status, cc_ticker = mapping
                total_in_mappings += shares_reserved
                status_icon = "🟢" if cc_status == 'open' else "🔴"
                st.write(f"- {status_icon} CC #{cc_id} → LOT #{lot_id}: {shares_reserved} akcji (status: {cc_status})")
            
            st.write(f"**RAZEM w cc_lot_mappings: {total_in_mappings} akcji**")
            
            # NAPRAWA - usuń mapowania dla bought_back CC
            if st.button("🔧 USUŃ mapowania dla bought_back CC", key="clean_mappings"):
                cursor.execute("""
                    DELETE FROM cc_lot_mappings 
                    WHERE cc_id IN (
                        SELECT id FROM options_cc 
                        WHERE status IN ('bought_back', 'expired')
                    )
                """)
                
                deleted_rows = cursor.rowcount
                conn.commit()
                st.success(f"✅ Usunięto {deleted_rows} mapowań dla bought_back/expired CC")
                st.info("🔄 Teraz kliknij przycisk RESET quantity_open")
                
        else:
            st.write("- Tabela cc_lot_mappings jest pusta")
            
        # 🔧 PRZYCISK RESET (zawsze dostępny)
# ZAMIEŃ PRZYCISK RESET NA TEN BEZPIECZNY:

        # 🔧 BEZPIECZNY PRZYCISK RESET 
        if st.button("🔧 BEZPIECZNY RESET quantity_open", key="safe_reset_qty_open"):
            # 1. Oblicz ile faktycznie sprzedano
            cursor.execute("""
                SELECT COALESCE(SUM(sts.qty_from_lot), 0)
                FROM stock_trade_splits sts
                WHERE sts.lot_id = ?
            """, (lot_id,))
            total_sold = cursor.fetchone()[0]
            
            # 2. Oblicz ile jest zarezerwowane pod OTWARTE CC
            cursor.execute("""
                SELECT COALESCE(SUM(oc.contracts * 100), 0)
                FROM options_cc oc
                WHERE oc.ticker = ? AND oc.status = 'open'
            """, (ticker,))
            total_reserved_open_cc = cursor.fetchone()[0]
            
            # 3. PRAWIDŁOWA FORMUŁA: total - sprzedane - otwarte_cc
            correct_quantity_open = all_lots[0][2] - total_sold - total_reserved_open_cc
            
            # 4. Zabezpieczenie - nie może być ujemne
            if correct_quantity_open < 0:
                st.error(f"❌ BŁĄD: Masz więcej CC ({total_reserved_open_cc}) niż dostępnych akcji!")
                st.error(f"Total: {all_lots[0][2]}, Sprzedane: {total_sold}, CC: {total_reserved_open_cc}")
                st.error("Musisz najpierw odkupić część CC!")
            else:
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = ? 
                    WHERE id = ?
                """, (correct_quantity_open, lot_id))
                
                conn.commit()
                st.success(f"✅ BEZPIECZNIE zresetowano quantity_open LOT #{lot_id} na {correct_quantity_open}")
                st.info(f"📊 Formuła: {all_lots[0][2]} (total) - {total_sold} (sprzedane) - {total_reserved_open_cc} (otwarte CC) = {correct_quantity_open}")
                
                if correct_quantity_open > 0:
                    st.success(f"✅ Możesz wystawić maksymalnie {correct_quantity_open // 100} nowych CC")
                else:
                    st.warning("⚠️ Brak wolnych akcji - wszystkie są sprzedane lub pod CC")
        conn.close()
        
    except Exception as e:
        st.error(f"Błąd debug: {e}")
    
    # ... reszta oryginalnej funkcji ...
    
    # ... reszta oryginalnej funkcji ...
    """🔧 NAPRAWIONA: Podgląd sprzedaży CC z walidacją pokrycia"""
    st.markdown("### 🎯 Podgląd sprzedaży Covered Call")
    
    ticker = form_data['ticker']
    contracts = form_data['contracts']
    strike_price = form_data['strike_price']
    premium_received = form_data['premium_received']
    expiry_date = form_data['expiry_date']
    sell_date = form_data['sell_date']
    
    # WALIDACJA DAT - nie można sprzedać CC przed zakupem akcji
    # 🔧 NAPRAWKA: Używaj nowej funkcji chronologii zamiast get_lots_by_ticker
    earliest_lot_check = db.check_cc_coverage_with_chronology(ticker, 1, sell_date)
    
    if earliest_lot_check.get('debug_info', {}).get('owned_on_date', 0) == 0:
        st.error(f"❌ **BŁĄD DATY**: Nie można sprzedać CC przed zakupem akcji!")
        st.error(f"   Data sprzedaży CC: {sell_date}")
        st.error(f"   Brak akcji {ticker} na {sell_date}")
        
        if st.button("❌ Popraw datę", key="fix_date"):
            if 'show_cc_preview' in st.session_state:
                del st.session_state.show_cc_preview
            st.rerun()
        return
    
    # 🔧 NAPRAWKA: Sprawdź pokrycie używając naprawionej funkcji
    coverage = db.check_cc_coverage_with_chronology(ticker, contracts, sell_date)
    
    if not coverage.get('can_cover'):
        st.error(f"❌ **BRAK POKRYCIA dla {contracts} kontraktów {ticker}**")
        st.error(f"   {coverage.get('message', 'Nieznany błąd')}")
        
        # 🔧 NAPRAWKA: Używaj debug_info zamiast niezdefiniowanych pól
        debug = coverage.get('debug_info', {})
        st.write(f"🎯 Potrzeba: {coverage.get('shares_needed', contracts * 100)} akcji")
        st.write(f"📊 Dostępne na {sell_date}: {debug.get('available_calculated', 0)} akcji")
        st.write(f"📦 Posiadane na {sell_date}: {debug.get('owned_on_date', 0)} akcji") 
        st.write(f"💰 Sprzedane przed {sell_date}: {debug.get('sold_before', 0)} akcji")
        st.write(f"🎯 Zarezerwowane przed {sell_date}: {debug.get('cc_reserved_before', 0)} akcji")
        
        # Przycisk anulowania
        if st.button("❌ Anuluj", key="cancel_cc"):
            if 'show_cc_preview' in st.session_state:
                del st.session_state.show_cc_preview
            if 'cc_form_data' in st.session_state:
                del st.session_state.cc_form_data
            st.rerun()
        return
    
    # ✅ POKRYCIE OK - POKAŻ SZCZEGÓŁY
    st.success(f"✅ **POKRYCIE OK dla {contracts} kontraktów {ticker}**")
    
    # Podstawowe kalkulacje
    total_premium_usd = premium_received * contracts * 100
    shares_covered = contracts * 100
    
    # Pobierz kurs NBP D-1
    try:
        from nbp_api_client import get_usd_rate_for_date
        nbp_result = get_usd_rate_for_date(sell_date)
        
        if isinstance(nbp_result, dict) and 'rate' in nbp_result:
            fx_rate = nbp_result['rate']
            fx_date = nbp_result.get('date', sell_date)
            fx_success = True
        else:
            fx_rate = float(nbp_result) if nbp_result else 4.0
            fx_date = sell_date
            fx_success = True
            
    except Exception as e:
        st.warning(f"⚠️ Błąd NBP API: {e}")
        fx_rate = 4.0  # Fallback
        fx_date = sell_date
        fx_success = False
    
    # Prowizje (opcjonalne)
    broker_fee = form_data.get('broker_fee', 1.0)
    reg_fee = form_data.get('reg_fee', 0.1)
    total_fees = broker_fee + reg_fee
    net_premium_usd = total_premium_usd - total_fees
    
    # PLN calculations
    total_premium_pln = total_premium_usd * fx_rate
    net_premium_pln = net_premium_usd * fx_rate
    
    # Podgląd podstawowy
    col_preview1, col_preview2, col_preview3 = st.columns(3)
    
    with col_preview1:
        st.markdown("**💰 Podstawowe dane:**")
        st.write(f"🎯 **Ticker**: {ticker}")
        st.write(f"📊 **Kontrakty**: {contracts}")
        st.write(f"🔒 **Pokrycie**: {shares_covered} akcji")
        st.write(f"💲 **Strike**: ${strike_price:.2f}")
        st.write(f"📅 **Expiry**: {expiry_date}")
    
    with col_preview2:
        st.markdown("**💵 Premium USD:**")
        st.write(f"💰 **Premium brutto**: ${total_premium_usd:.2f}")
        st.write(f"💸 **Broker fee**: ${broker_fee:.2f}")
        st.write(f"💸 **Reg fee**: ${reg_fee:.2f}")
        st.write(f"💰 **Razem prowizje**: ${total_fees:.2f}")
        st.success(f"**💚 Premium NETTO: ${net_premium_usd:.2f}**")
        st.write(f"📅 **Data sprzedaży**: {sell_date}")
    
    with col_preview3:
        st.markdown("**🇵🇱 Przeliczenie PLN:**")
        fees_pln = total_fees * fx_rate
        
        if fx_success:
            st.success(f"💱 **Kurs NBP** ({fx_date}): {fx_rate:.4f}")
        else:
            st.warning(f"⚠️ **Kurs fallback**: {fx_rate:.4f}")
        
        st.write(f"💰 **Premium brutto PLN**: {total_premium_pln:.2f} zł")
        st.write(f"💸 **Prowizje PLN**: {fees_pln:.2f} zł")
        st.success(f"**💚 Premium NETTO PLN: {net_premium_pln:.2f} zł**")
    
    # 🔧 NAPRAWKA: Alokacja FIFO z właściwymi kluczami
    st.markdown("---")
    st.markdown("### 🔄 Alokacja pokrycia FIFO")
    
    fifo_preview = coverage.get('fifo_preview', [])
    if fifo_preview:
        for i, allocation in enumerate(fifo_preview):
            with st.expander(f"LOT #{allocation['lot_id']} - {allocation.get('qty_to_reserve', 0)} akcji", expanded=i<2):
                col_alloc1, col_alloc2 = st.columns(2)
                
                with col_alloc1:
                    st.write(f"📅 **Data zakupu**: {allocation.get('buy_date', 'N/A')}")
                    st.write(f"💰 **Cena zakupu**: ${allocation.get('buy_price_usd', 0):.2f}")
                    # 🔧 NAPRAWKA: Używaj właściwego klucza
                    available_qty = allocation.get('qty_available_on_date', allocation.get('qty_total', 0))
                    st.write(f"📊 **Dostępne**: {available_qty} akcji")
                
                with col_alloc2:
                    st.write(f"🎯 **Do rezerwacji**: {allocation.get('qty_to_reserve', 0)} akcji")
                    remaining = allocation.get('qty_remaining_after', available_qty - allocation.get('qty_to_reserve', 0))
                    st.write(f"📦 **Pozostanie**: {remaining} akcji")
                    st.write(f"💱 **Kurs zakupu**: {allocation.get('fx_rate', 0):.4f}")
    else:
        st.warning("⚠️ Brak szczegółów alokacji FIFO")
    
    # Przygotuj dane do zapisu
    cc_data = {
        'ticker': ticker,
        'contracts': contracts,
        'strike_usd': strike_price,
        'premium_sell_usd': premium_received,
        'open_date': sell_date,
        'expiry_date': expiry_date,
        'fx_open': fx_rate,
        'fx_open_date': fx_date, 
        'premium_sell_pln': net_premium_pln,
        'broker_fee': broker_fee,
        'reg_fee': reg_fee,
        'coverage': coverage
    }
    
    st.session_state.cc_to_save = cc_data
    
    # Przyciski akcji
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("💾 ZAPISZ COVERED CALL", type="primary", key="save_cc"):
            with st.spinner("Zapisywanie CC do bazy..."):
                save_result = db.save_covered_call_to_database(cc_data)
                
                if save_result['success']:
                    st.success(f"✅ **{save_result['message']}**")
                    st.info(f"💰 **Premium**: ${total_premium_usd:.2f} → {total_premium_pln:.2f} zł")
                    st.info(f"🔒 **Zarezerwowano**: {shares_covered} akcji {ticker}")
                    st.balloons()
                else:
                    st.error(f"❌ **Błąd zapisu**: {save_result['message']}")
    
    with col_btn2:
        if st.button("➕ Nowa CC", key="new_cc_btn"):
            # Wyczyść formularz
            keys_to_clear = ['show_cc_preview', 'cc_form_data', 'cc_to_save']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    with col_btn3:
        if st.button("❌ Anuluj", key="cancel_cc_preview"):
            keys_to_clear = ['show_cc_preview', 'cc_form_data', 'cc_to_save']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st

def show_buyback_expiry_tab():
    """Tab buyback i expiry - Z PRAWDZIWYM CZĘŚCIOWYM BUYBACK"""
    st.subheader("💰 Buyback & Expiry")
    
    # SPRAWDŹ CZY SYSTEM OBSŁUGUJE CZĘŚCIOWY BUYBACK
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'")
        has_mappings_table = cursor.fetchone() is not None
        conn.close()
    except:
        has_mappings_table = False
    
    # Alert o braku tabeli mapowań
    if not has_mappings_table:
        st.warning("""
        ⚠️ **CZĘŚCIOWY BUYBACK NIEDOSTĘPNY** 
        
        Brak tabeli mapowań LOT-ów. System obsługuje tylko pełny buyback.
        
        **Aby włączyć częściowy buyback:**
        1. Przejdź do zakładki 🛠️ Diagnostyka  
        2. Kliknij "🔧 Utwórz tabelę mapowań"
        3. Kliknij "🔄 Odbuduj mapowania"
        """)
    
    # Pobierz otwarte CC
    try:
        open_cc_list = db.get_covered_calls_summary(status='open')
        
        if not open_cc_list:
            st.info("💡 **Brak otwartych CC do zamknięcia**")
            st.markdown("*Sprzedaj CC w zakładce 'Sprzedaż CC'*")
            return
        
        col1, col2 = st.columns([1, 1])
        
        # ===== BUYBACK SEKCJA =====
        with col1:
            st.markdown("### 💰 Buyback CC")
            
            if has_mappings_table:
                st.success("✅ Częściowy buyback dostępny")
            else:
                st.info("ℹ️ Tylko pełny buyback")
            
            # Wybór CC do buyback
            cc_options = [f"CC #{cc['id']} - {cc['ticker']} ${cc['strike_usd']:.2f} exp {cc['expiry_date']} ({cc['contracts']} kontr.)" 
                         for cc in open_cc_list]
            
            if cc_options:
                selected_cc_option = st.selectbox(
                    "Wybierz CC do odkupu:",
                    options=cc_options,
                    key="buyback_select"
                )
                
                # Wyciągnij CC ID
                selected_cc_id = int(selected_cc_option.split('#')[1].split(' ')[0])
                selected_cc = next((cc for cc in open_cc_list if cc['id'] == selected_cc_id), None)
                
                if selected_cc:
                    # FORMULARZ BUYBACK - WARUNKOWO CZĘŚCIOWY
                    with st.form("buyback_form"):
                        st.write(f"**Odkup CC #{selected_cc_id}:**")
                        st.write(f"📊 {selected_cc['ticker']} - ${selected_cc['strike_usd']:.2f}")
                        st.write(f"💰 Sprzedano @ ${selected_cc['premium_sell_usd']:.2f}/akcja")
                        st.write(f"🎯 **Dostępne kontrakty: {selected_cc['contracts']}**")
                        
                        # KONTROLA LICZBY KONTRAKTÓW - TYLKO JEŚLI MAPOWANIA ISTNIEJĄ
                        if has_mappings_table:
                            col_contr, col_price = st.columns(2)
                            
                            with col_contr:
                                contracts_to_buyback = st.number_input(
                                    "Kontrakty do odkupu:",
                                    min_value=1,
                                    max_value=selected_cc['contracts'],
                                    value=selected_cc['contracts'],  # Domyślnie wszystkie
                                    step=1,
                                    help=f"Możesz odkupić od 1 do {selected_cc['contracts']} kontraktów"
                                )
                            
                            with col_price:
                                buyback_price = st.number_input(
                                    "Cena buyback USD (za akcję):",
                                    min_value=0.01,
                                    value=max(0.01, selected_cc['premium_sell_usd'] * 0.5),
                                    step=0.01,
                                    format="%.2f"
                                )
                        else:
                            # TYLKO PEŁNY BUYBACK
                            contracts_to_buyback = selected_cc['contracts']
                            st.info(f"🔒 **Pełny buyback**: {contracts_to_buyback} kontraktów (częściowy niedostępny)")
                            
                            buyback_price = st.number_input(
                                "Cena buyback USD (za akcję):",
                                min_value=0.01,
                                value=max(0.01, selected_cc['premium_sell_usd'] * 0.5),
                                step=0.01,
                                format="%.2f"
                            )
                        
                        # DATA I PROWIZJE
                        col_date, col_fees = st.columns(2)
                        
                        with col_date:
                            buyback_date = st.date_input(
                                "Data buyback:",
                                value=date.today(),
                                max_value=date.today()
                            )
                        
                        with col_fees:
                            st.markdown("**Prowizje:**")
                            broker_fee = st.number_input("Broker fee USD:", min_value=0.0, value=1.0, step=0.1, format="%.2f")
                            reg_fee = st.number_input("Reg fee USD:", min_value=0.0, value=0.1, step=0.01, format="%.2f")
                        
                        # PODGLĄD SZYBKI
                        if has_mappings_table and contracts_to_buyback < selected_cc['contracts']:
                            st.info(f"ℹ️ **Częściowy buyback**: Zostanie {selected_cc['contracts'] - contracts_to_buyback} kontraktów w otwartej pozycji")
                        
                        st.markdown("---")
                        
                        # PRZYCISKI
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            check_preview = st.form_submit_button("🔍 Sprawdź podgląd buyback", use_container_width=True)
                        
                        with col_btn2:
                            execute_buyback = st.form_submit_button("💰 Wykonaj Buyback", type="primary", use_container_width=True)
                        
                        # OBSŁUGA PODGLĄDU
                        if check_preview:
                            st.session_state.buyback_form_data = {
                                'cc_id': selected_cc_id,
                                'cc_data': selected_cc,
                                'contracts_to_buyback': contracts_to_buyback,
                                'buyback_price': buyback_price,
                                'buyback_date': buyback_date,
                                'broker_fee': broker_fee,
                                'reg_fee': reg_fee,
                                'has_mappings': has_mappings_table
                            }
                            st.session_state.show_buyback_preview = True
                        
                        # OBSŁUGA WYKONANIA
                        if execute_buyback:
                            if has_mappings_table:
                                # UŻYJ FUNKCJI CZĘŚCIOWEGO BUYBACK
                                result = db.partial_buyback_covered_call_with_mappings(
                                    cc_id=selected_cc_id,
                                    contracts_to_buyback=contracts_to_buyback,
                                    buyback_price_usd=buyback_price,
                                    buyback_date=buyback_date,
                                    broker_fee_usd=broker_fee,
                                    reg_fee_usd=reg_fee
                                )
                            else:
                                # UŻYJ PROSTEJ FUNKCJI (TYLKO PEŁNY)
                                result = db.simple_buyback_covered_call(
                                    cc_id=selected_cc_id,
                                    buyback_price_usd=buyback_price,
                                    buyback_date=buyback_date,
                                    broker_fee_usd=broker_fee,
                                    reg_fee_usd=reg_fee
                                )
                            
                            if result['success']:
                                st.success(f"✅ {result['message']}")
                                
                                # Szczegóły wyników
                                with st.expander("📊 Szczegóły buyback:", expanded=True):
                                    col_res1, col_res2 = st.columns(2)
                                    
                                    with col_res1:
                                        st.write(f"**Kontrakty odkupione:** {result['contracts_bought_back']}")
                                        if result.get('contracts_remaining', 0) > 0:
                                            st.write(f"**Kontrakty pozostałe:** {result['contracts_remaining']}")
                                        st.write(f"**Akcje zwolnione:** {result['shares_released']}")
                                        st.write(f"**LOT-y zaktualizowane:** {result.get('lots_updated', 0)}")
                                    
                                    with col_res2:
                                        st.write(f"**Premium otrzymana (PLN):** {format_currency_pln(result['premium_received_pln'])}")
                                        st.write(f"**Koszt buyback (PLN):** {format_currency_pln(result['buyback_cost_pln'])}")
                                        st.write(f"**Prowizje (USD):** ${result['total_fees_usd']:.2f}")
                                        
                                        # P/L z kolorami
                                        pl_pln = result['pl_pln']
                                        if pl_pln >= 0:
                                            st.success(f"**P/L (PLN): +{format_currency_pln(abs(pl_pln))}**")
                                        else:
                                            st.error(f"**P/L (PLN): -{format_currency_pln(abs(pl_pln))}**")
                                        
                                        # Informacja o typie buyback
                                        if result.get('is_partial'):
                                            st.info("🔄 **Częściowy buyback** - pozycja podzielona")
                                        else:
                                            st.success("✅ **Pełny buyback** - pozycja zamknięta")
                                
                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
        
        # ===== EXPIRY SEKCJA (bez zmian) =====
        with col2:
            st.markdown("### 📅 Expiry CC")
            st.info("Oznacz opcje jako wygasłe w dniu expiry")
            
            # Znajdź CC które mogą być expired
            today = date.today()
            expirable_cc = [cc for cc in open_cc_list 
                           if datetime.strptime(cc['expiry_date'], '%Y-%m-%d').date() <= today]
            
            if expirable_cc:
                expiry_options = [f"CC #{cc['id']} - {cc['ticker']} exp {cc['expiry_date']}" 
                                for cc in expirable_cc]
                
                selected_expiry_option = st.selectbox(
                    "Wybierz CC do expiry:",
                    options=expiry_options,
                    key="expiry_select"
                )
                
                selected_expiry_id = int(selected_expiry_option.split('#')[1].split(' ')[0])
                selected_expiry_cc = next((cc for cc in expirable_cc if cc['id'] == selected_expiry_id), None)
                
                if selected_expiry_cc:
                    with st.form("expiry_form"):
                        st.write(f"**Expiry CC #{selected_expiry_id}:**")
                        st.write(f"📊 {selected_expiry_cc['ticker']} - {selected_expiry_cc['contracts']} kontraktów")
                        st.write(f"💰 Premium: ${selected_expiry_cc['premium_sell_usd']:.2f}/akcja")
                        st.write(f"📅 Data expiry: {selected_expiry_cc['expiry_date']}")
                        
                        st.info("✅ **Expiry = 100% zysk** (całe premium pozostaje)")
                        
                        if st.form_submit_button("📅 Oznacz jako Expired", type="primary", use_container_width=True):
                            
                            result = db.expire_covered_call(selected_expiry_id)
                            
                            if result['success']:
                                st.success(f"✅ {result['message']}")
                                
                                with st.expander("📊 Szczegóły expiry:", expanded=True):
                                    st.write(f"**Premium zachowana (PLN):** {format_currency_pln(result.get('premium_kept_pln', result.get('pl_pln', 0)))}")
                                    st.write(f"**Akcje zwolnione:** {result['shares_released']}")
                                    st.success(f"**P/L (PLN): +{format_currency_pln(result.get('pl_pln', 0))}**")
                                
                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
            else:
                st.warning("⏳ **Brak CC gotowych do expiry**")
    
    except Exception as e:
        st.error(f"❌ Błąd ładowania buyback/expiry: {e}")
    
    # ===== PODGLĄD BUYBACK - PRZYWRÓCONY Z OBSŁUGĄ CZĘŚCIOWEGO! =====
    if 'show_buyback_preview' in st.session_state and st.session_state.show_buyback_preview:
        if 'buyback_form_data' in st.session_state:
            st.markdown("---")
            show_buyback_cc_preview(st.session_state.buyback_form_data)

def show_buyback_cc_preview(form_data):
    """🔍 PODGLĄD BUYBACK z obsługą częściowego buyback"""
    st.markdown("### 🔍 Podgląd buyback Covered Call")
    
    cc_id = form_data['cc_id']
    cc_data = form_data['cc_data']
    contracts_to_buyback = form_data['contracts_to_buyback']
    buyback_price = form_data['buyback_price']
    buyback_date = form_data['buyback_date']
    broker_fee = form_data['broker_fee']
    reg_fee = form_data['reg_fee']
    has_mappings = form_data.get('has_mappings', False)
    
    # Podstawowe dane CC
    ticker = cc_data['ticker']
    total_contracts = cc_data['contracts']
    premium_sell_usd = cc_data['premium_sell_usd']
    premium_sell_pln = cc_data.get('premium_sell_pln', 0)
    fx_open = cc_data.get('fx_open', 4.0)
    
    # TYP BUYBACK
    is_partial = contracts_to_buyback < total_contracts
    
    if is_partial and has_mappings:
        st.warning(f"⚠️ **CZĘŚCIOWY BUYBACK**: {contracts_to_buyback}/{total_contracts} kontraktów")
        st.info(f"ℹ️ Zostanie {total_contracts - contracts_to_buyback} kontraktów w otwartej pozycji CC #{cc_id}")
    elif is_partial and not has_mappings:
        st.error("❌ **CZĘŚCIOWY BUYBACK NIEMOŻLIWY** - brak tabeli mapowań. Zmień na pełny buyback.")
        return
    else:
        st.success(f"✅ **PEŁNY BUYBACK**: {contracts_to_buyback} kontraktów")
    
    # KALKULACJE (dla wybranej liczby kontraktów)
    shares_to_buyback = contracts_to_buyback * 100
    premium_proportion = contracts_to_buyback / total_contracts
    
    premium_for_contracts_usd = premium_sell_usd * shares_to_buyback
    premium_for_contracts_pln = premium_for_contracts_usd * fx_open
    
    buyback_cost_usd = buyback_price * shares_to_buyback
    total_fees_usd = broker_fee + reg_fee
    total_buyback_cost_usd = buyback_cost_usd + total_fees_usd
    
    # POBIERZ KURS NBP
    try:
        nbp_result = nbp_api_client.get_usd_rate_for_date(buyback_date)
        if isinstance(nbp_result, dict) and 'rate' in nbp_result:
            fx_close = nbp_result['rate']
            fx_close_date = nbp_result.get('date', buyback_date)
        else:
            fx_close = float(nbp_result)
            fx_close_date = buyback_date
        fx_success = True
    except Exception as e:
        st.error(f"❌ Błąd kursu NBP: {e}")
        fx_close = 4.0
        fx_close_date = buyback_date
        fx_success = False
    
    buyback_cost_pln = total_buyback_cost_usd * fx_close
    pl_pln = premium_for_contracts_pln - buyback_cost_pln
    
    # TABELA WYNIKÓW
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💰 Rozliczenie finansowe:**")
        
        data = {
            "Pozycja": [
                f"Premium otrzymana ({contracts_to_buyback} kontr.)",
                "Koszt buyback",
                "Prowizje",
                "**P/L RAZEM**"
            ],
            "USD": [
                f"${premium_for_contracts_usd:.2f}",
                f"-${buyback_cost_usd:.2f}",
                f"-${total_fees_usd:.2f}",
                f"**${premium_for_contracts_usd - total_buyback_cost_usd:.2f}**"
            ],
            "Kurs NBP": [
                f"{fx_open:.4f} (open)",
                f"{fx_close:.4f} (close)",
                f"{fx_close:.4f}",
                "-"
            ],
            "PLN": [
                f"{format_currency_pln(premium_for_contracts_pln)}",
                f"-{format_currency_pln(abs(buyback_cost_pln))}",
                f"-{format_currency_pln(total_fees_usd * fx_close)}",
                f"**{format_currency_pln(pl_pln) if pl_pln >= 0 else '-' + format_currency_pln(abs(pl_pln))}**"
            ]
        }
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("**📊 Podsumowanie operacji:**")
        
        st.info(f"🎯 **CC #{cc_id}** - {ticker}")
        st.write(f"📅 Data buyback: {buyback_date}")
        st.write(f"💼 Kontrakty: {contracts_to_buyback} (z {total_contracts})")
        st.write(f"📈 Akcje: {shares_to_buyback} zwolnionych")
        
        if is_partial:
            st.write(f"🔄 **Pozostaje**: {total_contracts - contracts_to_buyback} kontraktów")
        
        # P/L podsumowanie
        if pl_pln >= 0:
            st.success(f"✅ **Zysk: +{format_currency_pln(pl_pln)}**")
        else:
            st.error(f"❌ **Strata: -{format_currency_pln(abs(pl_pln))}**")
        
        if not fx_success:
            st.warning("⚠️ Użyty fallback kurs NBP")
    
    # PRZYCISKI AKCJI
    col_action1, col_action2 = st.columns(2)
    
    with col_action1:
        if st.button("🔄 Ukryj podgląd", key="hide_buyback_preview"):
            if 'show_buyback_preview' in st.session_state:
                del st.session_state.show_buyback_preview
            if 'buyback_form_data' in st.session_state:
                del st.session_state.buyback_form_data
            st.rerun()
    
    with col_action2:
        if st.button("💰 Wykonaj ten buyback", key="execute_from_preview", type="primary"):
            # WYKONAJ BUYBACK Z PODGLĄDU
            if has_mappings:
                # CZĘŚCIOWY BUYBACK
                result = db.partial_buyback_covered_call_with_mappings(
                    cc_id=cc_id,
                    contracts_to_buyback=contracts_to_buyback,
                    buyback_price_usd=buyback_price,
                    buyback_date=buyback_date,
                    broker_fee_usd=broker_fee,
                    reg_fee_usd=reg_fee
                )
            else:
                # PEŁNY BUYBACK
                result = db.simple_buyback_covered_call(
                    cc_id=cc_id,
                    buyback_price_usd=buyback_price,
                    buyback_date=buyback_date,
                    broker_fee_usd=broker_fee,
                    reg_fee_usd=reg_fee
                )
            
            if result['success']:
                st.success(f"✅ {result['message']}")
                
                # Wyczyść podgląd
                if 'show_buyback_preview' in st.session_state:
                    del st.session_state.show_buyback_preview
                if 'buyback_form_data' in st.session_state:
                    del st.session_state.buyback_form_data
                
                st.rerun()
            else:
                st.error(f"❌ {result['message']}")

def get_portfolio_cc_summary():
    """
    PUNKT 66: Podsumowanie całego portfela CC
    """
    try:
        conn = db.get_connection()  # ← POPRAWKA: było get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        # Podstawowe statystyki
        cursor.execute("SELECT COUNT(*) FROM options_cc WHERE status = 'open'")
        open_cc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM options_cc WHERE status != 'open'")
        closed_cc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(contracts) FROM options_cc WHERE status = 'open'")
        total_open_contracts = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(premium_sell_pln) FROM options_cc WHERE status = 'open'")
        total_open_premium_pln = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(pl_pln) FROM options_cc WHERE status != 'open' AND pl_pln IS NOT NULL")
        total_realized_pl_pln = cursor.fetchone()[0] or 0
        
        # Statystyki per ticker
        cursor.execute("""
            SELECT ticker, 
                   COUNT(*) as cc_count,
                   SUM(contracts) as total_contracts,
                   SUM(premium_sell_pln) as total_premium_pln
            FROM options_cc 
            WHERE status = 'open'
            GROUP BY ticker
            ORDER BY ticker
        """)
        
        ticker_stats = []
        for row in cursor.fetchall():
            ticker_stats.append({
                'ticker': row[0],
                'cc_count': row[1],
                'total_contracts': row[2],
                'shares_reserved': row[2] * 100,
                'total_premium_pln': row[3]
            })
        
        conn.close()
        
        return {
            'open_cc_count': open_cc_count,
            'closed_cc_count': closed_cc_count,
            'total_open_contracts': total_open_contracts,
            'total_shares_reserved': total_open_contracts * 100,
            'total_open_premium_pln': total_open_premium_pln,
            'total_realized_pl_pln': total_realized_pl_pln,
            'ticker_stats': ticker_stats
        }
        
    except Exception as e:
        print(f"Błąd get_portfolio_cc_summary: {e}")
        return {}


# PUNKT 66: Ulepszona funkcja show_open_cc_tab() w modules/options.py

def show_open_cc_tab():
    """
    PUNKT 66: Zaawansowana tabela otwartych CC + NAPRAWKA: Przycisk usuń/edytuj
    """
    st.subheader("📊 Otwarte pozycje CC")
    
    # Podsumowanie portfela (bez zmian)
    portfolio_summary = db.get_portfolio_cc_summary()
    
    if portfolio_summary['open_cc_count'] == 0:
        st.info("💡 **Brak otwartych pozycji CC**")
        st.markdown("*Sprzedaj pierwszą opcję w zakładce 'Sprzedaż CC'*")
        return
    
    # METRICS OVERVIEW (bez zmian)
    st.markdown("### 📈 Podsumowanie portfela CC")
    
    col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
    
    with col_metric1:
        st.metric("🎯 Otwarte CC", f"{portfolio_summary['open_cc_count']}")
    
    with col_metric2:
        st.metric("📦 Kontrakty", f"{portfolio_summary['total_open_contracts']}")
    
    with col_metric3:
        st.metric("🔒 Akcje zarezerwowane", f"{portfolio_summary['total_shares_reserved']}")
    
    with col_metric4:
        st.metric("💰 Premium PLN", f"{portfolio_summary['total_open_premium_pln']:,.2f} zł")
    
    # SZCZEGÓŁOWE TABELE CC + PRZYCISK USUŃ/EDYTUJ
    st.markdown("### 🔍 Szczegółowe pozycje CC")
    
    coverage_details = db.get_cc_coverage_details()
    
    if not coverage_details:
        st.error("❌ Błąd pobierania szczegółów pokrycia")
        return
    
    from datetime import date
    today = date.today()
    
    for cc_detail in coverage_details:
        days_to_expiry = cc_detail['days_to_expiry']
        
        # Alert styling
        if days_to_expiry <= 0:
            alert_color = "🔴"
            alert_text = "EXPIRED"
        elif days_to_expiry <= 3:
            alert_color = "🟠"
            alert_text = f"{days_to_expiry}d left"
        elif days_to_expiry <= 7:
            alert_color = "🟡"
            alert_text = f"{days_to_expiry}d left"
        else:
            alert_color = "🟢"
            alert_text = f"{days_to_expiry}d left"
        
        # Expander per CC Z PRZYCISKAMI AKCJI
        with st.expander(
            f"{alert_color} CC #{cc_detail['cc_id']} - {cc_detail['ticker']} @ ${cc_detail['strike_usd']} ({alert_text})",
            expanded=(days_to_expiry <= 3)
        ):
            
            col_cc1, col_cc2, col_cc3 = st.columns(3)
            
            with col_cc1:
                st.markdown("**📊 Parametry CC:**")
                st.write(f"🎯 **Strike**: ${cc_detail['strike_usd']:.2f}")
                st.write(f"📦 **Kontrakty**: {cc_detail['contracts']} = {cc_detail['shares_needed']} akcji")
                st.write(f"💰 **Premium**: ${cc_detail['premium_sell_usd']:.2f} = {cc_detail['premium_sell_pln']:.2f} PLN")
                st.write(f"💱 **FX Open**: {cc_detail['fx_open']:.4f}")
            
            with col_cc2:
                st.markdown("**📅 Harmonogram:**")
                st.write(f"📅 **Otwarte**: {cc_detail['open_date']}")
                st.write(f"📅 **Expiry**: {cc_detail['expiry_date']}")
                st.write(f"⏱️ **Dni do expiry**: {cc_detail['days_to_expiry']}")
                st.write(f"📈 **Dni trzymane**: {cc_detail['days_held']}")
            
            with col_cc3:
                st.markdown("**💹 Yield Analysis:**")
                st.write(f"🏦 **Koszt bazowy**: {cc_detail['total_cost_basis']:,.2f} PLN")
                st.write(f"📊 **Premium yield**: {cc_detail['premium_yield_pct']:.2f}%")
                st.write(f"📈 **Annualized yield**: {cc_detail['annualized_yield_pct']:.1f}%")
                
                if cc_detail['annualized_yield_pct'] >= 20:
                    st.success("🚀 Excellent yield")
                elif cc_detail['annualized_yield_pct'] >= 12:
                    st.info("✅ Good yield")
                elif cc_detail['annualized_yield_pct'] >= 8:
                    st.warning("⚠️ Moderate yield")
                else:
                    st.error("❌ Low yield")
            
            # ✅ DODAJ SEKCJĘ AKCJI (USUŃ/EDYTUJ)
            st.markdown("---")
            st.markdown("**🔧 Akcje:**")
            
            col_action1, col_action2, col_action3, col_action4 = st.columns(4)
            
            # PRZYCISK USUŃ
            with col_action1:
                delete_key = f"delete_cc_{cc_detail['cc_id']}"
                confirm_key = f"confirm_delete_{cc_detail['cc_id']}"
                
                if st.button(f"🗑️ Usuń", key=delete_key, help="Usuń CC + cashflow + zwolnij akcje"):
                    st.session_state[confirm_key] = True
                
                # Potwierdzenie usunięcia
                if st.session_state.get(confirm_key, False):
                    if st.button(f"✅ POTWIERDŹ", key=f"confirm_{cc_detail['cc_id']}", type="primary"):
                        with st.spinner("Usuwanie CC..."):
                            result = db.delete_covered_call(cc_detail['cc_id'], confirm_delete=True)
                            
                            if result['success']:
                                st.success(f"✅ {result['message']}")
                                details = result['details']
                                st.info(f"🔓 Zwolniono {details['shares_released']} akcji {details['ticker']}")
                                if details.get('cashflows_deleted'):
                                    st.info(f"💸 Usunięto powiązane cashflow")
                                
                                # Wyczyść potwierdzenie i odśwież
                                del st.session_state[confirm_key]
                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
            
            # PRZYCISK EDYTUJ DATĘ
            with col_action2:
                edit_key = f"edit_cc_{cc_detail['cc_id']}"
                
                if st.button(f"✏️ Edytuj", key=edit_key, help="Edytuj parametry CC"):
                    st.session_state[f"show_edit_{cc_detail['cc_id']}"] = True
            
            # QUICK BUYBACK
            with col_action3:
                if st.button(f"💰 Buyback", key=f"quick_buyback_{cc_detail['cc_id']}", help="Przejdź do buyback"):
                    st.info("💡 Przejdź do zakładki 'Buyback & Expiry'")
            
            # QUICK EXPIRE
            with col_action4:
                if st.button(f"⏰ Expire", key=f"quick_expire_{cc_detail['cc_id']}", help="Oznacz jako expired"):
                    with st.spinner("Expire CC..."):
                        result = db.expire_covered_call(cc_detail['cc_id'])
                        if result['success']:
                            st.success(f"✅ {result['message']}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
            
            # ✅ FORMULARZ EDYCJI (JEŚLI WŁĄCZONY)
            if st.session_state.get(f"show_edit_{cc_detail['cc_id']}", False):
                st.markdown("---")
                st.markdown("**✏️ Edycja parametrów CC:**")
                
                with st.form(f"edit_form_{cc_detail['cc_id']}"):
                    col_edit1, col_edit2, col_edit3 = st.columns(3)
                    
                    with col_edit1:
                        new_open_date = st.date_input(
                            "Nowa data otwarcia:",
                            value=datetime.strptime(cc_detail['open_date'], '%Y-%m-%d').date(),
                            key=f"new_open_date_{cc_detail['cc_id']}"
                        )
                    
                    with col_edit2:
                        new_premium = st.number_input(
                            "Nowa premium USD:",
                            min_value=0.01,
                            value=float(cc_detail['premium_sell_usd']),
                            step=0.01,
                            format="%.2f",
                            key=f"new_premium_{cc_detail['cc_id']}"
                        )
                    
                    with col_edit3:
                        new_expiry = st.date_input(
                            "Nowa data expiry:",
                            value=datetime.strptime(cc_detail['expiry_date'], '%Y-%m-%d').date(),
                            key=f"new_expiry_{cc_detail['cc_id']}"
                        )
                    
                    # Pokazuj nowy kurs NBP dla nowej daty
                    if new_open_date != datetime.strptime(cc_detail['open_date'], '%Y-%m-%d').date():
                        try:
                            import nbp_api_client
                            new_fx_result = nbp_api_client.get_usd_rate_for_date(new_open_date)
                            if isinstance(new_fx_result, dict):
                                new_fx_rate = new_fx_result['rate']
                            else:
                                new_fx_rate = float(new_fx_result)
                            
                            st.info(f"💱 Nowy kurs NBP ({new_open_date}): {new_fx_rate:.4f}")
                            new_premium_pln = new_premium * cc_detail['contracts'] * 100 * new_fx_rate
                            st.info(f"💰 Nowa premium PLN: {new_premium_pln:.2f} zł")
                            
                        except Exception as e:
                            st.warning(f"⚠️ Błąd pobierania nowego kursu NBP: {e}")
                    
                    col_save, col_cancel = st.columns(2)
                    
                    with col_save:
                        if st.form_submit_button("💾 Zapisz zmiany", type="primary"):
                            # Wywołaj funkcję edycji z nowymi parametrami
                            changes = {}
                            
                            if new_open_date != datetime.strptime(cc_detail['open_date'], '%Y-%m-%d').date():
                                changes['open_date'] = new_open_date.strftime('%Y-%m-%d')
                            
                            if new_premium != cc_detail['premium_sell_usd']:
                                changes['premium_sell_usd'] = new_premium
                            
                            if new_expiry != datetime.strptime(cc_detail['expiry_date'], '%Y-%m-%d').date():
                                changes['expiry_date'] = new_expiry.strftime('%Y-%m-%d')
                            
                            if changes:
                                with st.spinner("Zapisywanie zmian..."):
                                    result = db.update_covered_call_with_recalc(cc_detail['cc_id'], **changes)
                                    
                                    if result['success']:
                                        st.success(f"✅ {result['message']}")
                                        if result.get('changes'):
                                            for change in result['changes']:
                                                st.info(f"📝 {change}")
                                        
                                        # Wyczyść edycję i odśwież
                                        del st.session_state[f"show_edit_{cc_detail['cc_id']}"]
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {result['message']}")
                            else:
                                st.warning("⚠️ Brak zmian do zapisania")
                    
                    with col_cancel:
                        if st.form_submit_button("❌ Anuluj"):
                            del st.session_state[f"show_edit_{cc_detail['cc_id']}"]
                            st.rerun()
            
            # FIFO COVERAGE TABLE (bez zmian)
            if cc_detail.get('lot_allocations'):
                st.markdown("**🔄 Pokrycie FIFO (LOT-y):**")
                
                fifo_data = []
                for alloc in cc_detail['lot_allocations']:
                    fifo_data.append({
                        'LOT ID': f"#{alloc['lot_id']}",
                        'Data zakupu': alloc['buy_date'],
                        'Cena zakupu': f"${alloc['buy_price_usd']:.2f}",
                        'FX Rate': f"{alloc['fx_rate']:.4f}",
                        'Koszt/akcję PLN': f"{alloc['cost_per_share_pln']:.2f} zł",
                        'Akcje pokryte': alloc['shares_allocated'],
                        'Koszt pokrycia': f"{alloc['total_cost_pln']:.2f} zł"
                    })
                
                st.dataframe(fifo_data, use_container_width=True)


def show_cc_history_tab():
    """
    PUNKT 67 + 68: Historia CC z zaawansowaną analizą P/L + zaawansowane filtry
    """
    st.subheader("📋 Historia Covered Calls")
    
    try:
        closed_cc_analysis = db.get_closed_cc_analysis()
    except Exception as e:
        st.error(f"❌ Błąd pobierania historii CC: {e}")
        return
    
    if not closed_cc_analysis:
        st.info("📋 **Brak zamkniętych CC** - sprzedaj i zamknij CC aby zobaczyć historię")
        return
    
    # Performance Summary
    performance = db.get_cc_performance_summary()
    
    if performance and performance.get('total_closed', 0) > 0:
        st.markdown("### 📊 Performance Summary")
        
        col_perf1, col_perf2, col_perf3, col_perf4 = st.columns(4)
        
        with col_perf1:
            total_pl = performance.get('total_realized_pl', 0) or 0
            st.metric(
                "💰 Total P/L",
                f"{total_pl:.2f} PLN",  # PUNKT 68: Dokładne wartości
                help="Łączny zrealizowany P/L"
            )
        
        with col_perf2:
            avg_pl = performance.get('avg_pl_per_cc', 0) or 0
            st.metric(
                "📈 Avg per CC",
                f"{avg_pl:.2f} PLN",  # PUNKT 68: Dokładne wartości
                help="Średni P/L na pozycję"
            )
        
        with col_perf3:
            total_closed = performance.get('total_closed', 0) or 0
            expired_count = performance.get('expired_count', 0) or 0
            win_rate = (expired_count / total_closed * 100) if total_closed > 0 else 0
            st.metric(
                "🏆 Win Rate",
                f"{win_rate:.1f}%",
                help="% opcji które wygasły (max profit)"
            )
        
        with col_perf4:
            buyback_count = performance.get('buyback_count', 0) or 0
            st.metric(
                "📝 Total Closed",
                f"{total_closed}",
                help=f"Expired: {expired_count}, Bought back: {buyback_count}"
            )
 
        # ✅ CLEANUP SECTION - NOWA FUNKCJA!
        st.markdown("---")
        st.markdown("### 🧹 Narzędzia cleanup")
        
        col_cleanup1, col_cleanup2, col_cleanup3 = st.columns(3)
        
        with col_cleanup1:
            if st.button("🧹 Usuń orphaned cashflow", key="cleanup_cashflow", help="Usuwa cashflow bez powiązań z CC"):
                with st.spinner("Szukam orphaned cashflow..."):
                    result = db.cleanup_orphaned_cashflow()
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        if result['deleted_count'] > 0:
                            st.info(f"🗑️ Usunięto {result['deleted_count']} orphaned cashflow")
                            for desc in result['deleted_descriptions']:
                                st.write(f"   • {desc}")
                    else:
                        st.error(f"❌ {result['message']}")
        
        with col_cleanup2:
            if st.button("📊 Sprawdź integralność", key="check_integrity", help="Sprawdza spójność CC vs cashflow"):
                integrity = db.check_cc_cashflow_integrity()
                
                if integrity['issues']:
                    st.warning(f"⚠️ Znaleziono {len(integrity['issues'])} problemów:")
                    for issue in integrity['issues']:
                        st.write(f"   • {issue}")
                else:
                    st.success("✅ Brak problemów z integralnością")
        
        with col_cleanup3:
            if st.button("🔄 Odśwież dane", key="refresh_history"):
                st.rerun()
 
        # Performance per ticker
        ticker_performance = performance.get('ticker_performance', [])
        if ticker_performance:
            st.markdown("### 🎯 Performance per ticker")
            
            ticker_data = []
            for ticker_perf in ticker_performance:
                ticker_data.append({
                    'Ticker': ticker_perf.get('ticker', 'N/A'),
                    'CC Count': ticker_perf.get('cc_count', 0),
                    'Total P/L': f"{ticker_perf.get('total_pl', 0):,.2f} PLN",
                    'Avg P/L': f"{ticker_perf.get('avg_pl', 0):,.2f} PLN", 
                    'Win Rate': f"{ticker_perf.get('win_rate', 0):.1f}%",
                    'Expired': ticker_perf.get('expired_count', 0),
                    'Bought Back': ticker_perf.get('buyback_count', 0)
                })
            
            st.dataframe(ticker_data, use_container_width=True)
    
    # PUNKT 68: FILTRY
    st.markdown("### 🔍 Filtry")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        all_tickers = list(set([cc['ticker'] for cc in closed_cc_analysis]))
        selected_tickers = st.multiselect(
            "Tickery:",
            options=all_tickers,
            default=all_tickers,
            key="history_ticker_filter_68"
        )
    
    with col_f2:
        status_filter = st.selectbox(
            "Status:",
            ["Wszystkie", "Expired", "Bought back"],
            key="history_status_filter_68"
        )
    
    with col_f3:
        sort_options = [
            "Data ↓", "Data ↑", 
            "P/L ↓", "P/L ↑",
            "Yield ↓", "Yield ↑",
            "Premium ↓", "Premium ↑",
            "Ticker A-Z"
        ]
        sort_by = st.selectbox(
            "Sortowanie:",
            options=sort_options,
            key="history_sort_filter_68"
        )
    
    with col_f4:
        if st.button("🔄 Reset", key="reset_filters_68"):
            st.rerun()
    
    # Zaawansowane filtry
    with st.expander("⚙️ Filtry zaawansowane", expanded=False):
        col_af1, col_af2 = st.columns(2)
        
        with col_af1:
            st.markdown("**📅 Zakres dat:**")
            
            from datetime import datetime
            all_dates = []
            for cc in closed_cc_analysis:
                if 'close_date' in cc and cc['close_date']:
                    try:
                        cc_date = datetime.strptime(cc['close_date'], '%Y-%m-%d').date()
                        all_dates.append(cc_date)
                    except:
                        pass
            
            if all_dates:
                min_date = min(all_dates)
                max_date = max(all_dates)
                
                date_from = st.date_input("Od:", value=min_date, key="date_from_68")
                date_to = st.date_input("Do:", value=max_date, key="date_to_68")
            else:
                date_from = None
                date_to = None
                st.info("Brak dat do filtrowania")
        
        with col_af2:
            st.markdown("**💰 Zakresy kwot:**")
            
            all_pl = [cc.get('pl_pln', 0) for cc in closed_cc_analysis if 'pl_pln' in cc]
            if all_pl:
                min_pl = min(all_pl)
                max_pl = max(all_pl)
                
                min_pl_slider = int(min_pl - 1) if min_pl >= 0 else int(min_pl - abs(min_pl * 0.1) - 1)
                max_pl_slider = int(max_pl + 2)
                
                pl_range = st.slider(
                    "P/L PLN:",
                    min_value=min_pl_slider,
                    max_value=max_pl_slider,
                    value=(int(min_pl), int(max_pl) + 1),
                    step=1,
                    key="pl_range_68",
                    help=f"Rzeczywisty zakres: {min_pl:.2f} - {max_pl:.2f} PLN"
                )
                
                st.caption(f"💡 Rzeczywiste P/L: {min_pl:.2f} do {max_pl:.2f} PLN")
            else:
                pl_range = None
                st.info("Brak danych P/L")
    
    # Aplikowanie filtrów
    filtered_cc = []
    for cc in closed_cc_analysis:
        if cc['ticker'] not in selected_tickers:
            continue
        
        if status_filter != "Wszystkie":
            if status_filter == "Expired" and cc.get('status') != 'expired':
                continue
            elif status_filter == "Bought back" and cc.get('status') != 'bought_back':
                continue
        
        if date_from and date_to and 'close_date' in cc:
            try:
                cc_date = datetime.strptime(cc['close_date'], '%Y-%m-%d').date()
                if cc_date < date_from or cc_date > date_to:
                    continue
            except:
                pass
        
        if pl_range and 'pl_pln' in cc:
            if cc['pl_pln'] < pl_range[0] or cc['pl_pln'] > pl_range[1]:
                continue
        
        filtered_cc.append(cc)
    
    # Sortowanie
    if sort_by == "Data ↓":
        filtered_cc.sort(key=lambda x: x.get('close_date', ''), reverse=True)
    elif sort_by == "Data ↑":
        filtered_cc.sort(key=lambda x: x.get('close_date', ''))
    elif sort_by == "P/L ↓":
        filtered_cc.sort(key=lambda x: x.get('pl_pln', 0), reverse=True)
    elif sort_by == "P/L ↑":
        filtered_cc.sort(key=lambda x: x.get('pl_pln', 0))
    elif sort_by == "Yield ↓":
        filtered_cc.sort(key=lambda x: x.get('annualized_yield_pct', 0), reverse=True)
    elif sort_by == "Yield ↑":
        filtered_cc.sort(key=lambda x: x.get('annualized_yield_pct', 0))
    elif sort_by == "Premium ↓":
        filtered_cc.sort(key=lambda x: x.get('premium_sell_usd', 0), reverse=True)
    elif sort_by == "Premium ↑":
        filtered_cc.sort(key=lambda x: x.get('premium_sell_usd', 0))
    elif sort_by == "Ticker A-Z":
        filtered_cc.sort(key=lambda x: x.get('ticker', ''))
    
    if not filtered_cc:
        st.warning("⚠️ Brak CC po zastosowaniu filtrów")
        return
    
    # Wyniki
    st.write(f"**Wyniki:** {len(filtered_cc)} z {len(closed_cc_analysis)} zamkniętych CC")
    
    # Szczegółowa tabela
    for cc in filtered_cc:
        pl_pln = cc.get('pl_pln', 0)
        if pl_pln > 0:
            pl_emoji = "💚"
        elif pl_pln < 0:
            pl_emoji = "❤️"
        else:
            pl_emoji = "⚪"
        
        outcome_emoji = cc.get('outcome_emoji', '📋')
        ticker = cc.get('ticker', 'N/A')
        cc_id = cc.get('id', 'N/A')
        annualized_yield = cc.get('annualized_yield_pct', 0)
        
        with st.expander(
            f"{outcome_emoji} {pl_emoji} CC #{cc_id} - {ticker} - {pl_pln:+,.2f} PLN ({annualized_yield:+.1f}% p.a.)",
            expanded=False
        ):
            
            col_detail1, col_detail2, col_detail3 = st.columns(3)
            
            with col_detail1:
                st.markdown("**📊 Podstawowe info:**")
                st.write(f"🎯 **Ticker**: {ticker} ({cc.get('contracts', 'N/A')} kontr.)")
                st.write(f"💰 **Strike**: ${cc.get('strike_usd', 0):.2f}")
                st.write(f"📅 **Okres**: {cc.get('open_date', 'N/A')} → {cc.get('close_date', 'N/A')}")
            
            with col_detail2:
                st.markdown("**💵 Finansowe:**")
                st.write(f"💲 **Premium sprzedaż**: ${cc.get('premium_sell_usd', 0):.2f}")
                if cc.get('premium_buyback_usd', 0) > 0:
                    st.write(f"💸 **Premium buyback**: ${cc.get('premium_buyback_usd', 0):.2f}")
                st.write(f"💰 **P/L PLN**: {pl_pln:+,.2f}")
            
            with col_detail3:
                st.markdown("**📈 Performance:**")
                st.write(f"📊 **Status**: {cc.get('outcome_text', cc.get('status', 'N/A'))}")
                st.write(f"🎯 **Dni trzymania**: {cc.get('days_held', 0)}")
                st.write(f"📈 **Yield p.a.**: {annualized_yield:.1f}%")
                
    
    # Export CSV
    if st.button("📥 Eksport CSV", key="export_history_csv"):
        st.info("💡 **PUNKT 69** - Eksporty CSV będą dostępne w następnej wersji")

# Test funkcjonalności (opcjonalny)
def test_options_prerequisites():
    """Test wymagań dla modułu Options"""
    
    results = {
        'stocks_available': False,
        'table_exists': False,
        'nbp_working': False,
        'cashflows_working': False
    }
    
    try:
        # Test 1: Akcje w portfelu
        lots_stats = db.get_lots_stats()
        results['stocks_available'] = lots_stats['open_shares'] > 0
        
        # Test 2: Tabela options_cc
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM options_cc")
            cursor.fetchone()
            results['table_exists'] = True
            conn.close()
        
        # Test 3: NBP API
        rate = nbp_api_client.get_usd_rate_for_date(date.today())
        results['nbp_working'] = rate is not None
        
        # Test 4: Cashflows
        cashflow_stats = db.get_cashflows_stats()
        results['cashflows_working'] = cashflow_stats['total_records'] >= 0
        
    except Exception as e:
        pass  # Testy opcjonalne
    
    return results
    
def show_cc_management_section():
    """
    PUNKT 63: Sekcja zarządzania CC (usuwanie, edycja)
    """
    st.markdown("---")
    st.markdown("## 🗑️ Zarządzanie Covered Calls")
    st.markdown("*Usuwanie błędnych operacji i czyszczenie danych*")
    
    # Pobierz listę CC do zarządzania
    cc_list = db.get_deletable_cc_list()
    
    if not cc_list:
        st.info("📝 Brak Covered Calls do zarządzania")
        return
    
    st.markdown(f"### 📋 Lista CC ({len(cc_list)} rekordów)")
    
    # Tabela z przyciskami usuwania
    for i, cc in enumerate(cc_list):
        with st.expander(f"CC #{cc['id']} - {cc['ticker']} ({cc['contracts']} kontr.) - {cc['status']}", expanded=False):
            
            col_info, col_actions = st.columns([2, 1])
            
            with col_info:
                st.markdown("**📊 Szczegóły:**")
                st.write(f"🎯 **Ticker**: {cc['ticker']}")
                st.write(f"📦 **Kontrakty**: {cc['contracts']} = {cc['shares_reserved']} akcji")
                st.write(f"💰 **Premium**: ${cc['premium_sell_usd']:.2f} = {cc['premium_sell_pln']:.2f} PLN")
                st.write(f"📅 **Otwarte**: {cc['open_date']} → **Expiry**: {cc['expiry_date']}")
                st.write(f"🔒 **Status**: {cc['status']}")
                
                if cc['close_date']:
                    st.write(f"❌ **Zamknięte**: {cc['close_date']}")
                
                # Ryzyko usunięcia
                if cc['status'] == 'open':
                    st.warning(f"⚠️ **Ryzyko**: {cc['delete_risk']}")
                else:
                    st.success(f"✅ **Ryzyko**: {cc['delete_risk']}")
            
            with col_actions:
                st.markdown("**🔧 Akcje:**")
                
                # Przycisk usuwania z potwierdzeniem
                delete_key = f"delete_cc_{cc['id']}"
                confirm_key = f"confirm_delete_{cc['id']}"
                
                if st.button(f"🗑️ Usuń CC #{cc['id']}", key=delete_key, type="secondary"):
                    st.session_state[confirm_key] = True
                
                # Potwierdzenie usunięcia
                if st.session_state.get(confirm_key, False):
                    st.warning("⚠️ **POTWIERDŹ USUNIĘCIE**")
                    
                    col_confirm, col_cancel = st.columns(2)
                    
                    with col_confirm:
                        if st.button("✅ TAK, usuń", key=f"yes_delete_{cc['id']}", type="primary"):
                            # Wykonaj usunięcie
                            result = db.delete_covered_call(cc['id'], confirm_delete=True)
                            
                            if result['success']:
                                st.success(f"✅ {result['message']}")
                                details = result['details']
                                st.info(f"🔓 Zwolniono {details['shares_released']} akcji {details['ticker']}")
                                if details['cashflows_deleted'] > 0:
                                    st.info(f"💸 Usunięto {details['cashflows_deleted']} powiązanych cashflow")
                                
                                # Wyczyść potwierdzenie i odśwież
                                del st.session_state[confirm_key]
                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
                    
                    with col_cancel:
                        if st.button("❌ Anuluj", key=f"cancel_delete_{cc['id']}"):
                            del st.session_state[confirm_key]
                            st.rerun()
    
    # Dodatkowe narzędzia
    st.markdown("---")
    st.markdown("### 🧹 Narzędzia dodatkowe")
    
    col_tools1, col_tools2 = st.columns(2)
    
    with col_tools1:
        if st.button("🔄 Odśwież listę", key="refresh_cc_list"):
            st.rerun()
    
    with col_tools2:
        open_count = len([cc for cc in cc_list if cc['status'] == 'open'])
        if open_count > 0:
            st.warning(f"⚠️ {open_count} otwartych CC - usuwanie zwolni rezerwacje!")
        else:
            st.success("✅ Wszystkie CC są zamknięte - bezpieczne usuwanie")
            
def show_cc_edit_section():
    """
    PUNKT 64: Sekcja edycji parametrów CC
    """
    st.markdown("---")
    st.markdown("## ✏️ Edycja Covered Calls")
    st.markdown("*Modyfikacja parametrów otwartych CC*")
    
    # Pobierz CC do edycji (tylko otwarte)
    edit_candidates = db.get_cc_edit_candidates()
    
    if not edit_candidates:
        st.info("📝 Brak otwartych CC do edycji")
        return
    
    st.markdown(f"### 📋 Otwarte CC ({len(edit_candidates)} rekordów)")
    
    for cc in edit_candidates:
        with st.expander(f"✏️ CC #{cc['id']} - {cc['ticker']} @ ${cc['strike_usd']}", expanded=False):
            
            col_current, col_edit = st.columns([1, 1])
            
            with col_current:
                st.markdown("**📊 Aktualne parametry:**")
                st.write(f"🎯 **Ticker**: {cc['ticker']} ({cc['contracts']} kontr.)")
                st.write(f"💰 **Strike**: ${cc['strike_usd']:.2f}")
                st.write(f"💸 **Premium**: ${cc['premium_sell_usd']:.2f} = {cc['premium_sell_pln']:.2f} PLN")
                st.write(f"📅 **Expiry**: {cc['expiry_date']}")
                st.write(f"📅 **Otwarte**: {cc['open_date']}")
                st.write(f"💱 **Kurs otwarcia**: {cc['fx_open']:.4f}")
            
            with col_edit:
                st.markdown("**✏️ Nowe wartości:**")
                
                edit_key_base = f"edit_cc_{cc['id']}"
                
                # Nowy strike
                new_strike = st.number_input(
                    "Strike USD:",
                    min_value=0.01,
                    value=float(cc['strike_usd']),
                    step=0.01,
                    format="%.2f",
                    key=f"{edit_key_base}_strike"
                )
                
                # Nowa premium
                new_premium = st.number_input(
                    "Premium USD:",
                    min_value=0.01,
                    value=float(cc['premium_sell_usd']),
                    step=0.01,
                    format="%.2f", 
                    key=f"{edit_key_base}_premium"
                )
                
                # Nowa data expiry
                from datetime import datetime, date
                current_expiry = datetime.strptime(cc['expiry_date'], '%Y-%m-%d').date()
                
                new_expiry = st.date_input(
                    "Expiry date:",
                    value=current_expiry,
                    min_value=date.today(),
                    key=f"{edit_key_base}_expiry"
                )
                
                # Pokaż przeliczenie premium PLN
                if new_premium != cc['premium_sell_usd']:
                    new_premium_pln = round(new_premium * cc['fx_open'], 2)
                    st.info(f"💱 Nowa premium PLN: {new_premium_pln:.2f} zł")
                
                # Przycisk zapisz
                if st.button(f"💾 Zapisz zmiany", key=f"{edit_key_base}_save", type="primary"):
                    
                    changes = {}
                    if new_strike != cc['strike_usd']:
                        changes['strike_usd'] = new_strike
                    if new_premium != cc['premium_sell_usd']:
                        changes['premium_sell_usd'] = new_premium
                    if new_expiry.strftime('%Y-%m-%d') != cc['expiry_date']:
                        changes['expiry_date'] = new_expiry.strftime('%Y-%m-%d')
                    
                    if changes:
                        result = db.update_covered_call(cc['id'], **changes)
                        
                        if result['success']:
                            st.success(f"✅ {result['message']}")
                            st.info("📝 Zmiany: " + ", ".join(result['changes']))
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
                    else:
                        st.warning("⚠️ Brak zmian do zapisania")


def show_bulk_operations_section():
    """
    PUNKT 64: Sekcja operacji masowych
    """
    st.markdown("---")
    st.markdown("## 🗑️ Operacje masowe")
    st.markdown("*Bulk delete i cleanup danych*")
    
    # Pobierz wszystkie CC
    all_cc = db.get_deletable_cc_list()
    
    if not all_cc:
        st.info("📝 Brak CC do operacji masowych")
        return
    
    # Filtry dla bulk operations
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        # Filtr po statusie
        status_filter = st.selectbox(
            "Filtruj po statusie:",
            ["Wszystkie", "Otwarte", "Zamknięte", "Expired", "Bought back"],
            key="bulk_status_filter"
        )
    
    with col_filter2:
        # Filtr po tickerze
        tickers = list(set([cc['ticker'] for cc in all_cc]))
        ticker_filter = st.selectbox(
            "Filtruj po tickerze:",
            ["Wszystkie"] + tickers,
            key="bulk_ticker_filter"  
        )
    
    # Zastosuj filtry
    filtered_cc = []
    for cc in all_cc:
        # Filtr status
        if status_filter != "Wszystkie":
            if status_filter == "Otwarte" and cc['status'] != 'open':
                continue
            elif status_filter == "Zamknięte" and cc['status'] == 'open':
                continue
            elif status_filter == "Expired" and cc['status'] != 'expired':
                continue
            elif status_filter == "Bought back" and cc['status'] != 'bought_back':
                continue
        
        # Filtr ticker
        if ticker_filter != "Wszystkie" and cc['ticker'] != ticker_filter:
            continue
            
        filtered_cc.append(cc)
    
    if not filtered_cc:
        st.warning("⚠️ Brak CC po zastosowaniu filtrów")
        return
    
    st.markdown(f"### 📋 Filtered CC ({len(filtered_cc)} z {len(all_cc)})")
    
    # Multi-select dla bulk delete
    cc_to_delete = []
    
    for cc in filtered_cc[:10]:  # Pokaż max 10 dla UI
        if st.checkbox(
            f"CC #{cc['id']} - {cc['ticker']} ({cc['status']}) - ${cc['premium_sell_usd']:.2f}",
            key=f"bulk_select_{cc['id']}"
        ):
            cc_to_delete.append(cc['id'])
    
    if len(filtered_cc) > 10:
        st.info(f"📋 Pokazano 10 z {len(filtered_cc)} CC. Użyj filtrów aby zawęzić wybór.")
    
    # Operacje masowe
    if cc_to_delete:
        st.markdown(f"### 🎯 Wybrano {len(cc_to_delete)} CC do usunięcia")
        
        col_bulk1, col_bulk2 = st.columns(2)
        
        with col_bulk1:
            if st.button(f"🗑️ USUŃ {len(cc_to_delete)} CC", key="bulk_delete_btn", type="secondary"):
                st.session_state.bulk_delete_confirm = cc_to_delete
        
        with col_bulk2:
            if st.session_state.get('bulk_delete_confirm'):
                if st.button("✅ POTWIERDŹ BULK DELETE", key="bulk_confirm", type="primary"):
                    result = db.bulk_delete_covered_calls(st.session_state.bulk_delete_confirm, confirm_bulk=True)
                    
                    if result['success']:
                        st.success(f"✅ {result['message']}")
                        if result['shares_released']:
                            st.info(f"🔓 Zwolniono akcje: {result['shares_released']}")
                    else:
                        st.error(f"❌ {result['message']}")
                        if result['errors']:
                            for error in result['errors']:
                                st.error(f"   • {error}")
                    
                    # Wyczyść potwierdzenie
                    del st.session_state.bulk_delete_confirm
                    st.rerun()
    
    else:
        st.info("☑️ Zaznacz CC do operacji masowych")

def show_reservations_diagnostics_tab():
    """
    Diagnostyka rezerwacji CC ↔ LOT (FIFO) + spójność tabeli options_cc_reservations.
    """
    import streamlit as st
    st.subheader("🛠️ Diagnostyka rezerwacji CC ↔ LOT")

    try:
        diag = db.get_reservations_diagnostics()
    except Exception as e:
        st.error(f"❌ Błąd diagnostyki: {e}")
        return

    if not diag.get('success'):
        st.error(f"❌ {diag.get('message','Nieznany błąd')}")
        return

    has_map = diag.get('has_mapping_table', False)
    if has_map:
        st.info("📦 Tabela mapowań: **options_cc_reservations** → ✅ istnieje")
    else:
        st.warning("📦 Tabela mapowań: **options_cc_reservations** → ❌ brak (mapuję tylko na podstawie LOT-ów)\n\n"
                   "Uruchom skrypt `db_fix_cc_reservations.py --apply`, aby ją odbudować.")

    st.markdown("### 📊 Poziom Tickerów")
    rows = []
    for r in diag.get('tickers', []):
        status = "✅ OK" if r['delta'] == 0 else ("🔻 za mało" if r['delta'] < 0 else "🔺 za dużo")
        rows.append({
            "Ticker": r['ticker'],
            "Wymagane (kontr.*100)": r['required_reserved'],
            "Faktycznie z LOT-ów": r['actual_reserved'],
            "Delta": r['delta'],
            "Status": status
        })
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("Brak otwartych CC.")

    st.markdown("### 🔎 Poziom CC (mapowanie LOT-ów)")
    for cc in diag.get('ccs', []):
        expected = cc['expected_reserved']
        mapped = cc.get('mapped_reserved')
        hdr = f"CC #{cc['id']} – {cc['ticker']} – oczekiwane {expected} akcji"
        if mapped is None:
            hdr = "ℹ️ " + hdr + " | brak tabeli mapowań"
        else:
            emoji = "✅" if mapped == expected else "🟠"
            hdr = f"{emoji} {hdr} | zmapowane {mapped}"

        with st.expander(hdr, expanded=(mapped is not None and mapped != expected)):
            st.write(f"📅 Open: {cc['open_date']}")
            if mapped is None:
                st.warning("Brak danych mapowania. Odbuduj `options_cc_reservations` naprawczym skryptem.")
            else:
                lot_rows = [{"LOT ID": d['lot_id'], "Zarezerwowane": d['qty_reserved']} for d in cc.get('mapped_details', [])]
                if lot_rows:
                    st.dataframe(lot_rows, use_container_width=True)
                else:
                    st.info("Brak wpisów mapowania dla tej CC.")
    

if __name__ == "__main__":
    show_options()  