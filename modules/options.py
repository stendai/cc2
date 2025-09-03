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
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Sprzedaż CC", 
        "💰 Buyback & Expiry", 
        "📊 Otwarte CC", 
        "📋 Historia CC",
    ])
    
    with tab1:
        show_sell_cc_tab()
    
    with tab2:
        show_buyback_expiry_tab()
    
    with tab3:
        show_open_cc_tab()
    
    with tab4:
        show_cc_history_tab()  # Nowa wersja z PUNKT 67
        
def show_sell_cc_tab():
    
    st.subheader("🎯 Sprzedaż Covered Calls")

def get_available_lots_for_cc():
    """Pobiera LOT-y z quantity_open >= 100 (min 1 kontrakt CC)"""
    try:
        conn = db.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, ticker, quantity_open, buy_date, buy_price_usd
            FROM lots 
            WHERE quantity_open >= 100
            ORDER BY ticker, buy_date, id
        """)
        
        lots = cursor.fetchall()
        conn.close()
        
        # Format: [(lot_id, display_text, ticker, quantity_open)]
        lot_options = []
        for lot in lots:
            lot_id, ticker, qty_open, buy_date, buy_price = lot
            max_contracts = qty_open // 100
            
            display_text = (f"LOT #{lot_id}: {ticker} - {qty_open} akcji "
                          f"({max_contracts} CC) @ ${buy_price:.2f} [{buy_date}]")
            
            lot_options.append((lot_id, display_text, ticker, qty_open))
        
        return lot_options
        
    except Exception as e:
        st.error(f"Błąd pobierania LOT-ów: {e}")
        return []


def show_sell_cc_tab():
    """Tab sprzedaży Covered Calls - POPRAWIONE BŁĘDY"""
    st.subheader("🎯 Sprzedaż Covered Calls")
    

    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📝 Formularz sprzedaży CC")
        
        # Pobierz dostępne LOT-y do wyboru
        available_lots = get_available_lots_for_cc()
        
        if not available_lots:
            st.error("❌ **Brak LOT-ów dostępnych do pokrycia CC**")
            st.info("💡 Potrzebujesz co najmniej 100 wolnych akcji w jednym LOT-cie")
            return
        
        # FORMULARZ SPRZEDAŻY CC
        with st.form("sell_cc_form"):
            st.info("💡 **1 kontrakt CC = 100 akcji pokrycia**")
            
            # 🆕 Wybór LOT-a z dropdowna
            lot_options = [lot[1] for lot in available_lots]  # display_text
            
            selected_lot_option = st.selectbox(
                "🎯 Wybierz LOT do pokrycia:",
                options=lot_options,
                help="Wybierz konkretny LOT akcji do rezerwacji pod CC"
            )
            
            col_dates1, col_dates2 = st.columns(2)

            with col_dates1:
                sell_date = st.date_input(
                    "Data sprzedaży:",
                    value=date.today(),
                    key="cc_sell_date"
                )

            with col_dates2:
                expiry_date = st.date_input(
                    "Data expiry:", 
                    value=date.today() + timedelta(days=30)
                )
            
            # 🔧 POPRAWKA: Wyciągnij dane wybranego LOT-a
            selected_lot_data = None
            ticker = None  # 🔧 INICJALIZACJA
            lot_id = None  # 🔧 INICJALIZACJA
            max_contracts = 1  # 🔧 DOMYŚLNA WARTOŚĆ
            
            if selected_lot_option:
                selected_lot_data = next(
                    (lot for lot in available_lots if lot[1] == selected_lot_option), 
                    None
                )
            
            if selected_lot_data:
                lot_id, _, ticker, qty_open = selected_lot_data
                max_contracts = qty_open // 100
                
                # Pokazuj info o wybranym LOT-cie
                st.info(f"📊 **LOT #{lot_id}**: {ticker} - {qty_open} akcji (max {max_contracts} CC)")

            # 🔧 POPRAWKA: Sprawdź dostępność na datę CC (tylko jeśli ticker istnieje)
            max_contracts_on_date = max_contracts  # 🔧 UŻYJ WARTOŚCI Z LOT-A
            
            if ticker and sell_date:  # 🔧 ZMIENIONE Z selected_ticker NA ticker
                try:
                    # Używaj naprawionej funkcji chronologii
                    test_coverage = db.check_cc_coverage_with_chronology(ticker, 10, sell_date)
                    max_contracts_on_date = test_coverage.get('shares_available', 0) // 100
                    
                    if max_contracts_on_date > 0:
                        st.success(f"✅ Na {sell_date}: dostępne {test_coverage.get('shares_available')} akcji = max {max_contracts_on_date} kontraktów")
                    else:
                        st.error(f"❌ Na {sell_date}: brak dostępnych akcji {ticker}")
                        debug_info = test_coverage.get('debug_info', {})
                        st.error(f"   Posiadane: {debug_info.get('owned_on_date', 0)}")
                        st.error(f"   Sprzedane przed: {debug_info.get('sold_before', 0)}")
                        st.error(f"   Zarezerwowane przed: {debug_info.get('cc_reserved_before', 0)}")
                except Exception as e:
                    st.warning(f"⚠️ Nie można sprawdzić pokrycia: {e}")
                    max_contracts_on_date = max_contracts

            col_form1, col_form2 = st.columns(2)
            
            with col_form1:
                # 🔧 NAPRAWIONA walidacja kontraktów - BEZPIECZNE WARTOŚCI
                safe_max_value = max(1, min(max_contracts, max_contracts_on_date)) if ticker else 10
                safe_value = min(1, safe_max_value) if ticker else 1
                
                contracts = st.number_input(
                    "Liczba kontraktów CC:",
                    min_value=1,
                    max_value=safe_max_value,
                    value=safe_value,
                    help=f"LOT #{lot_id}: max {max_contracts}, na {sell_date}: max {max_contracts_on_date}" if ticker else "Wybierz LOT"
                )
                
                # Strike price
                strike_price = st.number_input(
                    "Strike price USD:",
                    min_value=0.01,
                    value=60.00,
                    step=0.01,
                    format="%.2f"
                )
            
            with col_form2:
                # Premium
                premium_received = st.number_input(
                    "Premium otrzymana USD:",
                    min_value=0.01,
                    value=5.00,
                    step=0.01,
                    format="%.2f"
                )
            
            # ✅ PROWIZJE
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

            # 🔧 SUBMIT BUTTON - KONIECZNIE W FORMULARZU!
            submitted_cc = st.form_submit_button(
                "🔍 Sprawdź pokrycie i podgląd", 
                type="primary",
                use_container_width=True
            )
        
        # 🔧 SPRAWDZENIE POKRYCIA - POZA FORMEM (poprawione warunki)
        if submitted_cc and ticker and contracts:  # 🔧 ZMIENIONE NAZWĘ ZMIENNEJ
            st.session_state.cc_form_data = {
                'lot_id': lot_id,  # 🔧 TERAZ JEST ZDEFINIOWANE
                'ticker': ticker,
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
        st.markdown("### 📊 Dostępne LOT-y")
        
        # 🔧 POPRAWKA: Pokaż tabelę LOT-ów (nie tickerów)
        if available_lots:
            lot_data = []
            for lot_id, display_text, ticker, qty_open in available_lots:
                max_cc = qty_open // 100
                lot_data.append({
                    'LOT ID': lot_id,
                    'Ticker': ticker,
                    'Akcje': f"{qty_open:,}",
                    'Max CC': max_cc,
                    'Status': "✅ Dostępne" if max_cc > 0 else "⚠️ Za mało"
                })
            
            st.dataframe(lot_data, use_container_width=True)
        
        # Statystyki CC
        st.markdown("### 🎯 Statystyki CC")
        try:
            cc_stats = db.get_cc_reservations_summary()
            
            if cc_stats.get('open_cc_count', 0) > 0:
                st.write(f"📊 **Otwarte CC**: {cc_stats['open_cc_count']}")
                st.write(f"🎯 **Kontrakty**: {cc_stats['total_contracts']}")
                st.write(f"📦 **Zarezerwowane**: {cc_stats['shares_reserved']} akcji")
            else:
                st.info("💡 Brak otwartych pozycji CC")
        except Exception as e:
            st.error(f"❌ Błąd statystyk: {e}")
    
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


def show_cc_sell_preview(form_data):
    """Podgląd sprzedaży Covered Call z walidacją pokrycia"""
    import streamlit as st
    
    st.markdown("### 🎯 Podgląd sprzedaży Covered Call")
    
    ticker = form_data['ticker']
    contracts = form_data['contracts']
    strike_price = form_data['strike_price']
    premium_received = form_data['premium_received']
    expiry_date = form_data['expiry_date']
    sell_date = form_data['sell_date']
    
    # WALIDACJA DAT - nie można sprzedać CC przed zakupem akcji
    earliest_lot_check = db.check_cc_coverage_with_chronology(ticker, 1, sell_date)
    
    if earliest_lot_check.get('debug_info', {}).get('owned_on_date', 0) == 0:
        st.error(f"❌ Nie można sprzedać opcji przed zakupem akcji")
        st.error(f"Data sprzedaży CC: {sell_date}")
        st.error(f"Brak akcji {ticker} na {sell_date}")
        
        if st.button("❌ Popraw datę", key="fix_date"):
            if 'show_cc_preview' in st.session_state:
                del st.session_state.show_cc_preview
            st.rerun()
        return
    
    # Sprawdź pokrycie używając funkcji chronologii
    coverage = db.check_cc_coverage_with_chronology(ticker, contracts, sell_date)
    
    if not coverage.get('can_cover'):
        st.error(f"❌ Brak pokrycia dla {contracts} kontraktów {ticker}")
        st.error(f"{coverage.get('message', 'Nieznany błąd')}")
        
        debug = coverage.get('debug_info', {})
        st.write(f"🎯 Potrzeba: {coverage.get('shares_needed', contracts * 100)} akcji")
        st.write(f"📊 Dostępne na {sell_date}: {debug.get('available_calculated', 0)} akcji")
        st.write(f"📦 Posiadane na {sell_date}: {debug.get('owned_on_date', 0)} akcji") 
        st.write(f"💰 Sprzedane przed {sell_date}: {debug.get('sold_before', 0)} akcji")
        st.write(f"🎯 Zarezerwowane przed {sell_date}: {debug.get('cc_reserved_before', 0)} akcji")
        
        if st.button("❌ Anuluj", key="cancel_cc"):
            if 'show_cc_preview' in st.session_state:
                del st.session_state.show_cc_preview
            if 'cc_form_data' in st.session_state:
                del st.session_state.cc_form_data
            st.rerun()
        return
    
    # POKRYCIE OK - POKAŻ SZCZEGÓŁY
    st.success(f"✅ Pokrycie OK dla {contracts} kontraktów {ticker}")
    
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
        st.write(f"🎯 Ticker: {ticker}")
        st.write(f"📊 Kontrakty: {contracts}")
        st.write(f"🔒 Pokrycie: {shares_covered} akcji")
        st.write(f"💲 Strike: ${strike_price:.2f}")
        st.write(f"📅 Expiry: {expiry_date}")
    
    with col_preview2:
        st.markdown("**💵 Premium USD:**")
        st.write(f"💰 Premium brutto: ${total_premium_usd:.2f}")
        st.write(f"💸 Broker fee: ${broker_fee:.2f}")
        st.write(f"💸 Reg fee: ${reg_fee:.2f}")
        st.write(f"💰 Razem prowizje: ${total_fees:.2f}")
        st.success(f"💚 Premium NETTO: ${net_premium_usd:.2f}")
        st.write(f"📅 Data sprzedaży: {sell_date}")
    
    with col_preview3:
        st.markdown("**🇵🇱 Przeliczenie PLN:**")
        fees_pln = total_fees * fx_rate
        
        if fx_success:
            st.success(f"💱 Kurs NBP ({fx_date}): {fx_rate:.4f}")
        else:
            st.warning(f"⚠️ Kurs fallback: {fx_rate:.4f}")
        
        st.write(f"💰 Premium brutto PLN: {total_premium_pln:.2f} zł")
        st.write(f"💸 Prowizje PLN: {fees_pln:.2f} zł")
        st.success(f"💚 Premium NETTO PLN: {net_premium_pln:.2f} zł")
    
    # Alokacja FIFO
    st.markdown("---")
    st.markdown("### 🔄 Alokacja pokrycia FIFO")
    
    fifo_preview = coverage.get('fifo_preview', [])
    if fifo_preview:
        for i, allocation in enumerate(fifo_preview):
            with st.expander(f"LOT #{allocation['lot_id']} - {allocation.get('qty_to_reserve', 0)} akcji", expanded=i<2):
                col_alloc1, col_alloc2 = st.columns(2)
                
                with col_alloc1:
                    st.write(f"📅 Data zakupu: {allocation.get('buy_date', 'N/A')}")
                    st.write(f"💰 Cena zakupu: ${allocation.get('buy_price_usd', 0):.2f}")
                    available_qty = allocation.get('qty_available_on_date', allocation.get('qty_total', 0))
                    st.write(f"📊 Dostępne: {available_qty} akcji")
                
                with col_alloc2:
                    st.write(f"🎯 Do rezerwacji: {allocation.get('qty_to_reserve', 0)} akcji")
                    remaining = allocation.get('qty_remaining_after', available_qty - allocation.get('qty_to_reserve', 0))
                    st.write(f"📦 Pozostanie: {remaining} akcji")
                    st.write(f"💱 Kurs zakupu: {allocation.get('fx_rate', 0):.4f}")
    else:
        st.warning("⚠️ Brak szczegółów alokacji FIFO")
    
    # Przygotuj dane do zapisu
    cc_data = {
        'lot_id': form_data.get('lot_id'),
        'ticker': ticker,
        'contracts': contracts,
        'strike_usd': strike_price,
        'premium_sell_usd': total_premium_usd,
        'open_date': sell_date,
        'expiry_date': expiry_date,
        'fx_open': fx_rate,
        'fx_open_date': fx_date, 
        'premium_sell_pln': total_premium_pln,
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
                    st.success(f"✅ {save_result['message']}")
                    st.info(f"💰 Premium: ${total_premium_usd:.2f} → {total_premium_pln:.2f} zł")
                    st.info(f"🔒 Zarezerwowano: {shares_covered} akcji {ticker}")
                    st.balloons()
                else:
                    st.error(f"❌ Błąd zapisu: {save_result['message']}")
    
    with col_btn2:
        if st.button("➕ Nowa CC", key="new_cc_btn"):
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
                    del st.session_state[key]
            st.rerun()

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
                                        st.write(f"**Koszt buyback (PLN):** {result.get('total_buyback_cost_pln', 0):,.2f} zł")
                                        st.write(f"**P/L (PLN):** {result.get('pl_pln', 0):+,.2f} zł")  # + pokazuje znak
                                        st.write(f"**Akcje zwolnione:** {result.get('shares_released_from_mappings', 0)}")
                                        st.write(f"**Kontrakty odkupione:** {result.get('contracts_bought_back', 0)}")
                                    
                                        
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
                                
                                
                            else:
                                st.error(f"❌ {result['message']}")
        
        # ===== EXPIRY SEKCJA (bez zmian) =====
        with col2:
            st.markdown("### 📅 Expiry/Assignment CC")
            st.info("Dwa scenariusze: opcja wygasa lub zostaje wykonana")
            
            # Znajdź CC które mogą być expired/assigned
            today = date.today()
            expirable_cc = [cc for cc in open_cc_list 
                           if datetime.strptime(cc['expiry_date'], '%Y-%m-%d').date() <= today]
            
            if expirable_cc:
                expiry_options = [f"CC #{cc['id']} - {cc['ticker']} exp {cc['expiry_date']}" 
                                for cc in expirable_cc]
                
                selected_expiry_option = st.selectbox(
                    "Wybierz CC:",
                    options=expiry_options,
                    key="expiry_select"
                )
                
                selected_expiry_id = int(selected_expiry_option.split('#')[1].split(' ')[0])
                selected_expiry_cc = next((cc for cc in expirable_cc if cc['id'] == selected_expiry_id), None)
                
                if selected_expiry_cc:
                    st.write(f"**📊 {selected_expiry_cc['ticker']} - {selected_expiry_cc['contracts']} kontraktów**")
                    st.write(f"💰 Strike: ${selected_expiry_cc['strike_usd']:.2f}")
                    st.write(f"📅 Expiry: {selected_expiry_cc['expiry_date']}")
                    
                    # DWA SCENARIUSZE
                    col_expire, col_assign = st.columns(2)
                    
                    with col_expire:
                        st.markdown("**✅ EXPIRE**")
                        st.caption("Opcja wygasła bezwartościowo")
                        st.caption("Cena < Strike")
                        st.success("🎉 Yield: 100% premium")
                        
                        if st.button("✅ EXPIRE", key=f"expire_btn_{selected_expiry_id}", 
                                   use_container_width=True, type="primary"):
                            
                            result = db.expire_covered_call(selected_expiry_id)
                            
                            if result['success']:
                                st.success(f"✅ {result['message']}")
                                st.success("🎉 **100% yield** - premia została, akcje zostały!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
                    
                    with col_assign:
                        st.markdown("**📞 ASSIGN**")
                        st.caption("Opcja została wykonana")
                        st.caption("Cena > Strike")
                        st.info("💼 Akcje sprzedane po strike")
                        
                        if st.button("📞 ASSIGN", key=f"assign_btn_{selected_expiry_id}", 
                                   use_container_width=True):
                            
                            result = db.assign_covered_call(selected_expiry_id)
                            
                            if result['success']:
                                st.success(f"✅ {result['message']}")
                                st.info(f"💰 P/L total: {result.get('pl_pln', 0):.2f} PLN")
                                st.warning("⚠️ Akcje sprzedane - quantity_open = 0")
                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
                                
                    # Pomoc dla użytkownika
                    st.markdown("---")
                    st.markdown("**💡 Która opcja?**")
                    st.markdown("• **EXPIRE** - jeśli cena akcji < strike na expiry")
                    st.markdown("• **ASSIGN** - jeśli cena akcji > strike na expiry")
                    
            else:
                st.warning("⏳ **Brak CC gotowych do expiry/assignment**")
    
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
    
    # ✅ POPRAWNIE: proporcja premii
    premium_proportion = contracts_to_buyback / total_contracts
    premium_for_contracts_usd = premium_sell_usd * premium_proportion
    premium_for_contracts_pln = premium_sell_pln * premium_proportion
    
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
                
                # ZACHOWAJ WYNIK W SESSION STATE
                st.session_state.last_buyback_success = result
                
                # Wyczyść podgląd FORM ale NIE WYNIK
                if 'buyback_form_data' in st.session_state:
                    del st.session_state.buyback_form_data
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
                                    result = db.update_covered_call(cc_detail['cc_id'], **changes)
                                    
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


# =============================================================================
# AKTUALIZACJA show_cc_history_tab() dla statusu 'assigned'
# =============================================================================

def show_cc_history_tab():
    """Historia CC - centrum analityczne strategii opcyjnej"""
    
    try:
        closed_cc_analysis = db.get_closed_cc_analysis()
    except Exception as e:
        st.error(f"Błąd pobierania historii CC: {e}")
        return
    
    if not closed_cc_analysis:
        st.info("Brak zamkniętych pozycji CC. Sprzedaj i zamknij CC aby zobaczyć analizy.")
        return
    
    # === STRATEGICZNE KPI ===
    performance = db.get_cc_performance_summary()
    
    if performance and performance.get('total_closed', 0) > 0:
        st.markdown("### 📊 Strategic Performance Dashboard")
        
        # Główne metryki
        col1, col2, col3, col4 = st.columns(4)
        
        total_pl = performance.get('total_realized_pl', 0) or 0
        total_closed = performance.get('total_closed', 0) or 0
        expired_count = performance.get('expired_count', 0) or 0
        buyback_count = performance.get('buyback_count', 0) or 0
        # DODANE: assigned_count
        assigned_count = performance.get('assigned_count', 0) or 0
        
        # Oblicz dodatkowe metryki
        wins = sum(1 for cc in closed_cc_analysis if cc.get('pl_pln', 0) > 0)
        losses = total_closed - wins
        
        if wins > 0:
            avg_win = sum(cc.get('pl_pln', 0) for cc in closed_cc_analysis if cc.get('pl_pln', 0) > 0) / wins
        else:
            avg_win = 0
            
        if losses > 0:
            avg_loss = sum(cc.get('pl_pln', 0) for cc in closed_cc_analysis if cc.get('pl_pln', 0) < 0) / losses
        else:
            avg_loss = 0
        
        with col1:
            st.metric(
                "💰 Total P/L",
                f"{total_pl:+,.0f} PLN",
                delta=f"Per trade: {total_pl/total_closed:+,.0f}" if total_closed > 0 else None
            )
        
        with col2:
            success_rate = (wins / total_closed * 100) if total_closed > 0 else 0
            st.metric(
                "🎯 Success Rate",
                f"{success_rate:.1f}%",
                delta=f"{wins}W / {losses}L"
            )
        
        with col3:
            if avg_loss != 0:
                profit_factor = abs(avg_win / avg_loss) if avg_loss < 0 else 0
                st.metric(
                    "⚖️ Risk/Reward", 
                    f"1:{profit_factor:.1f}",
                    delta="Win vs Loss size"
                )
            else:
                st.metric("⚖️ Risk/Reward", "N/A")
        
        with col4:
            expire_rate = (expired_count / total_closed * 100) if total_closed > 0 else 0
            st.metric(
                "🏆 Max Profit Rate",
                f"{expire_rate:.1f}%", 
                delta=f"{expired_count} expired"
            )
        
        # === DODATKOWA SEKCJA: Breakdown po typach zamknięcia ===
        st.markdown("### 📈 Outcome Breakdown")
        col_outcome1, col_outcome2, col_outcome3 = st.columns(3)
        
        with col_outcome1:
            st.metric(
                "✅ Expired",
                f"{expired_count}",
                delta=f"{(expired_count/total_closed*100):.1f}%" if total_closed > 0 else None
            )
        
        with col_outcome2:
            st.metric(
                "🔴 Bought Back", 
                f"{buyback_count}",
                delta=f"{(buyback_count/total_closed*100):.1f}%" if total_closed > 0 else None
            )
        
        with col_outcome3:
            st.metric(
                "📞 Assigned",  # NOWE
                f"{assigned_count}",
                delta=f"{(assigned_count/total_closed*100):.1f}%" if total_closed > 0 else None
            )
        
        # === STRATEGICZNE INSIGHTS ===
        st.markdown("### 🧠 Strategy Insights")
        
        col_insight1, col_insight2 = st.columns(2)
        
        with col_insight1:
            st.markdown("**💡 Performance Breakdown:**")
            
            if avg_win > 0 and avg_loss < 0:
                st.success(f"Average Win: +{avg_win:,.0f} PLN")
                st.error(f"Average Loss: {avg_loss:,.0f} PLN")
                
                if profit_factor > 2:
                    st.info("🎯 Excellent risk management - losses well controlled")
                elif profit_factor > 1:
                    st.warning("⚠️ Acceptable risk profile - monitor position sizing")
                else:
                    st.error("❌ Poor risk/reward - consider tighter stops or better entries")
        
        with col_insight2:
            st.markdown("**📈 Strategy Recommendations:**")
            
            # ZAKTUALIZOWANA LOGIKA: expire + assigned = "max profit outcomes"
            max_profit_outcomes = expired_count + assigned_count
            max_profit_rate = (max_profit_outcomes / total_closed * 100) if total_closed > 0 else 0
            
            if max_profit_rate > 70:
                st.success(f"✅ Great outcomes - {max_profit_rate:.1f}% expired/assigned")
            elif max_profit_rate > 50:
                st.info(f"📊 Good outcomes - {max_profit_rate:.1f}% expired/assigned")
            else:
                st.warning(f"⚠️ Too many buybacks - only {max_profit_rate:.1f}% expired/assigned")
            
            # NOWE: Assigned analysis
            if assigned_count > 0:
                assigned_rate = (assigned_count / total_closed * 100)
                if assigned_rate > 30:
                    st.warning("⚠️ High assignment rate - consider further OTM strikes")
                elif assigned_rate > 10:
                    st.info("📊 Moderate assignments - good strike selection")
                else:
                    st.success("✅ Low assignments - strikes well positioned")
                
            # Seasonality hint
            import datetime
            current_month = datetime.date.today().month
            if 3 <= current_month <= 5:
                st.info("🌱 Q1 earnings season - watch IV expansion opportunities")
            elif current_month in [10, 11]:
                st.info("🍂 Q3 earnings + volatility season ahead")
    
    # === TICKER PERFORMANCE MATRIX ===
    ticker_performance = performance.get('ticker_performance', [])
    if ticker_performance:
        st.markdown("### 🎯 Ticker Performance Matrix")
        
        # Sortuj według P/L
        ticker_performance.sort(key=lambda x: x.get('total_pl', 0), reverse=True)
        
        for i, ticker_perf in enumerate(ticker_performance):
            ticker = ticker_perf.get('ticker', 'N/A')
            total_pl = ticker_perf.get('total_pl', 0)
            cc_count = ticker_perf.get('cc_count', 0)
            win_rate = ticker_perf.get('win_rate', 0)
            
            # Status icon
            if i == 0:
                icon = "🥇"  # Best performer
            elif total_pl > 0:
                icon = "✅" 
            else:
                icon = "❌"
            
            # Performance label
            if total_pl > 5000:
                label = "STAR PERFORMER"
                color = "success"
            elif total_pl > 0:
                label = "PROFITABLE"
                color = "info"
            elif total_pl > -10000:
                label = "UNDERPERFORMING"
                color = "warning"
            else:
                label = "AVOID"
                color = "error"
            
            col_ticker, col_metrics = st.columns([1, 3])
            
            with col_ticker:
                if color == "success":
                    st.success(f"{icon} **{ticker}**")
                elif color == "info": 
                    st.info(f"{icon} **{ticker}**")
                elif color == "warning":
                    st.warning(f"{icon} **{ticker}**")
                else:
                    st.error(f"{icon} **{ticker}**")
            
            with col_metrics:
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric("P/L", f"{total_pl:+,.0f}")
                with col_m2:
                    st.metric("Trades", f"{cc_count}")
                with col_m3:
                    st.metric("Win Rate", f"{win_rate:.0f}%")
                with col_m4:
                    avg_per_trade = total_pl / cc_count if cc_count > 0 else 0
                    st.metric("Per Trade", f"{avg_per_trade:+,.0f}")
    
    # === SMART FILTERS ===
    st.markdown("### 🔍 Analysis Filters")
    
    with st.expander("Filter & Sort Options", expanded=False):
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            all_tickers = list(set([cc['ticker'] for cc in closed_cc_analysis]))
            selected_tickers = st.multiselect(
                "Select Tickers:",
                options=all_tickers,
                default=all_tickers[:3] if len(all_tickers) > 3 else all_tickers,  # Limit default
                key="history_ticker_filter"
            )
        
        with col_f2:
            # ZAKTUALIZOWANE: Dodano "Assigned"
            outcome_filter = st.selectbox(
                "Outcome:",
                ["All", "Profitable Only", "Losses Only", "Expired", "Assigned", "Bought Back"],
                key="outcome_filter"
            )
        
        with col_f3:
            sort_options = {
                "Recent First": lambda x: x.get('close_date', ''),
                "Highest P/L": lambda x: x.get('pl_pln', 0),
                "Lowest P/L": lambda x: x.get('pl_pln', 0),
                "Best Yield": lambda x: x.get('yield_pct', 0),
                "Ticker A-Z": lambda x: x.get('ticker', '')
            }
            sort_by = st.selectbox("Sort by:", list(sort_options.keys()))
    
    # Apply filters
    filtered_cc = []
    for cc in closed_cc_analysis:
        if selected_tickers and cc['ticker'] not in selected_tickers:
            continue
        
        pl = cc.get('pl_pln', 0)
        status = cc.get('status', '')
        
        if outcome_filter == "Profitable Only" and pl <= 0:
            continue
        elif outcome_filter == "Losses Only" and pl >= 0:
            continue
        elif outcome_filter == "Expired" and status != 'expired':
            continue
        elif outcome_filter == "Assigned" and status != 'assigned':  # NOWE
            continue
        elif outcome_filter == "Bought Back" and status != 'bought_back':
            continue
            
        filtered_cc.append(cc)
    
    # Sort results
    reverse_sort = sort_by in ["Recent First", "Highest P/L", "Best Yield"]
    filtered_cc.sort(key=sort_options[sort_by], reverse=reverse_sort)
    
    if not filtered_cc:
        st.warning("No CC match your filters")
        return
    
    st.write(f"**Showing:** {len(filtered_cc)} of {len(closed_cc_analysis)} closed positions")
    
    # === DETAILED RESULTS ===
    st.markdown("### 📋 Trade Details")
    
    # FUNKCJA POMOCNICZA: Status display
    def get_status_display(status):
        """Zwróć ładny display dla statusu CC"""
        status_displays = {
            'open': '🟢 OPEN',
            'expired': '✅ EXPIRED',
            'assigned': '📞 ASSIGNED',  # NOWE
            'bought_back': '🔴 BOUGHT BACK'
        }
        return status_displays.get(status, f'❓ {status.upper()}')
    
    for cc in filtered_cc[:10]:  # Limit to top 10 for performance
        pl_pln = cc.get('pl_pln', 0)
        status = cc.get('status', 'unknown')
        
        # Visual indicators
        if pl_pln > 1000:
            pl_color = "🟢"
            pl_label = "BIG WIN"
        elif pl_pln > 0:
            pl_color = "🔵" 
            pl_label = "WIN"
        elif pl_pln > -1000:
            pl_color = "🟡"
            pl_label = "SMALL LOSS"
        else:
            pl_color = "🔴"
            pl_label = "BIG LOSS"
        
        # ZAKTUALIZOWANE: Używaj get_status_display
        outcome = get_status_display(status)
        ticker = cc.get('ticker', 'N/A')
        cc_id = cc.get('cc_id', cc.get('id', 'N/A'))
        
        with st.expander(
            f"{pl_color} {ticker} • {pl_label} • {pl_pln:+,.0f} PLN • {outcome}",
            expanded=False
        ):
            col_d1, col_d2, col_d3 = st.columns(3)
            
            with col_d1:
                st.markdown("**Trade Summary:**")
                st.write(f"CC #{cc_id} • {cc.get('contracts', 1)} contracts")
                st.write(f"Strike: ${cc.get('strike_usd', 0):.2f}")
                st.write(f"Period: {cc.get('open_date', 'N/A')} → {cc.get('close_date', 'N/A')}")
                
            with col_d2:
                st.markdown("**Financial:**")
                premium = cc.get('premium_sell_usd', 0)
                st.write(f"Premium: ${premium:.2f}")
                if cc.get('premium_buyback_usd', 0) > 0:
                    buyback = cc.get('premium_buyback_usd', 0)
                    st.write(f"Buyback: ${buyback:.2f}")
                st.write(f"Net P/L: {pl_pln:+,.0f} PLN")
                
            with col_d3:
                st.markdown("**Analysis:**")
                days_held = cc.get('days_held', 1)
                st.write(f"Days held: {days_held}")
                
                # Calculate yield properly
                premium_pln = cc.get('premium_sell_pln', 0)
                if premium_pln > 0:
                    yield_pct = (pl_pln / premium_pln) * 100
                    st.write(f"Return: {yield_pct:+.1f}%")
                    
                    # Annualized only if meaningful
                    if days_held >= 7:  # At least a week
                        annual_yield = yield_pct * (365 / days_held)
                        st.write(f"Annualized: {annual_yield:+.0f}%")
                else:
                    st.write("Return: N/A")
                
                # NOWE: Dodatkowe info dla assigned
                if status == 'assigned':
                    st.info("📞 **ASSIGNED**: Opcja wykonana przez kupującego")
                    st.write(f"💰 Strike: ${cc.get('strike_usd', 0):.2f}")
                    st.write("✅ Premia zachowana + akcje sprzedane")
    
    if len(filtered_cc) > 10:
        st.info(f"Showing top 10 results. {len(filtered_cc) - 10} more available.")
    
    # === EXPORT ===
    if st.button("📥 Export Analysis (CSV)", key="export_analysis"):
        st.info("CSV export will be available in the next version")

            
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
                current_total_premium = float(cc['premium_sell_usd'])  # np. 500
                contracts = int(cc['contracts'])                       # np. 5
                current_premium_per_share = current_total_premium / (contracts * 100)  # 500/(5*100) = 1.0

                new_premium_per_share = st.number_input(
                    "Premium USD per share:",
                    min_value=0.001,
                    value=current_premium_per_share,  # np. 1.0 per share
                    step=0.001,
                    format="%.3f",  # 3 miejsca po przecinku
                    key=f"{edit_key_base}_premium",
                    help=f"Obecna: ${current_premium_per_share:.3f}/akcja (${current_total_premium:.2f} total)"
                )
                new_total_premium = new_premium_per_share * contracts * 100
                if new_premium_per_share != current_premium_per_share:
                    col_calc1, col_calc2 = st.columns(2)
                    with col_calc1:
                        st.info(f"💰 **Stara**: ${current_total_premium:.2f} total")
                        st.caption(f"${current_premium_per_share:.3f} × {contracts} × 100")
                    with col_calc2:
                        st.success(f"💰 **Nowa**: ${new_total_premium:.2f} total")
                        st.caption(f"${new_premium_per_share:.3f} × {contracts} × 100")               
                
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
                    if new_premium_per_share != current_premium_per_share:
                        changes['premium_sell_usd'] = new_total_premium  # Do bazy idzie total
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
    

if __name__ == "__main__":
    show_options()  