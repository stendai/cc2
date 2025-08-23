"""
Moduł Options - Zarządzanie Covered Calls
ETAP 4 - PUNKTY 51-56: UKOŃCZONE

FUNKCJONALNOŚCI ETAPU 4:
- ✅ PUNKT 51: Struktura modułu Options
- ✅ PUNKT 52: Logika rezerwacji akcji FIFO
- ✅ PUNKT 53: Formularz sprzedaży CC z walidacją
- ✅ PUNKT 54: Faktyczny zapis CC do bazy
- ✅ PUNKT 55: Tabela otwartych CC z alertami expiry
- ✅ PUNKT 56: Funkcje buyback i expiry CC
"""

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
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Sprzedaż CC", 
        "💰 Buyback & Expiry", 
        "📊 Otwarte CC", 
        "📋 Historia CC"
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
            
            # Wyciągnij ticker z opcji
            selected_ticker = selected_ticker_option.split(' ')[0] if selected_ticker_option else None
            max_shares = next((shares for ticker, shares in available_tickers if ticker == selected_ticker), 0)
            max_contracts = max_shares // 100
            
            col_form1, col_form2 = st.columns(2)
            
            with col_form1:
                # Liczba kontraktów
                contracts = st.number_input(
                    "Liczba kontraktów CC:",
                    min_value=1,
                    max_value=max(1, max_contracts),
                    value=1,
                    help=f"Maksymalnie {max_contracts} kontraktów dla {selected_ticker}"
                )
                
                # Strike price
                strike_price = st.number_input(
                    "Strike price USD:",
                    min_value=0.01,
                    value=100.00,
                    step=0.01,
                    format="%.2f",
                    help="Cena wykonania opcji"
                )
            
            with col_form2:
                # Premium otrzymana
                premium_received = st.number_input(
                    "Premium otrzymana USD:",
                    min_value=0.01,
                    value=2.50,
                    step=0.01,
                    format="%.2f",
                    help="Premium za sprzedaż CC (za akcję)"
                )
                
                # Data expiry
                expiry_date = st.date_input(
                    "Data expiry:",
                    value=date.today() + timedelta(days=30),
                    min_value=date.today() + timedelta(days=1),
                    help="Data wygaśnięcia opcji"
                )
            
            # Data sprzedaży
            sell_date = st.date_input(
                "Data sprzedaży CC:",
                value=date.today(),
                help="Data transakcji sprzedaży"
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
    """Pobiera tickery z dostępnymi akcjami do pokrycia CC"""
    try:
        conn = db.get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticker, SUM(quantity_open) as available
            FROM lots 
            WHERE quantity_open > 0
            GROUP BY ticker
            HAVING SUM(quantity_open) >= 100
            ORDER BY ticker
        """)
        
        tickers = cursor.fetchall()
        conn.close()
        
        return [(ticker, shares) for ticker, shares in tickers]
        
    except Exception as e:
        st.error(f"Błąd pobierania tickerów: {e}")
        return []

def show_cc_sell_preview(form_data):
    """Podgląd sprzedaży CC z walidacją pokrycia - PUNKTY 53-54"""
    st.markdown("### 🎯 Podgląd sprzedaży Covered Call")
    
    ticker = form_data['ticker']
    contracts = form_data['contracts']
    strike_price = form_data['strike_price']
    premium_received = form_data['premium_received']
    expiry_date = form_data['expiry_date']
    sell_date = form_data['sell_date']
    
    # WALIDACJA DAT - nie można sprzedać CC przed zakupem akcji
    lots = db.get_lots_by_ticker(ticker, only_open=True)
    if lots:
        earliest_buy_date = min([lot['buy_date'] for lot in lots])
        if isinstance(earliest_buy_date, str):
            earliest_buy_date = datetime.strptime(earliest_buy_date, '%Y-%m-%d').date()
        
        if sell_date < earliest_buy_date:
            st.error(f"❌ **BŁĄD DATY**: Nie można sprzedać CC przed zakupem akcji!")
            st.error(f"   Data sprzedaży CC: {sell_date}")
            st.error(f"   Najwcześniejszy zakup {ticker}: {earliest_buy_date}")
            
            if st.button("❌ Popraw datę", key="fix_date"):
                if 'show_cc_preview' in st.session_state:
                    del st.session_state.show_cc_preview
                st.rerun()
            return
    
    # Sprawdź pokrycie FIFO
    coverage = db.check_cc_coverage(ticker, contracts)
    
    if not coverage.get('can_cover'):
        st.error(f"❌ **BRAK POKRYCIA dla {contracts} kontraktów {ticker}**")
        st.error(f"   {coverage.get('message', 'Nieznany błąd')}")
        st.write(f"🎯 Potrzeba: {coverage['shares_needed']} akcji")
        st.write(f"📊 Dostępne: {coverage['shares_available']} akcji")
        
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
    total_premium_usd = premium_received * contracts * 100  # Premium za wszystkie akcje
    shares_covered = contracts * 100
    
    # Pobierz kurs NBP D-1
    try:
        nbp_result = nbp_api_client.get_usd_rate_for_date(sell_date)
        if isinstance(nbp_result, dict):
            fx_rate = nbp_result['rate']
            fx_date = nbp_result.get('date', sell_date)
        else:
            fx_rate = float(nbp_result)
            fx_date = sell_date
        
        total_premium_pln = total_premium_usd * fx_rate
        fx_success = True
        
    except Exception as e:
        st.error(f"❌ Błąd pobierania kursu NBP: {e}")
        fx_rate = 4.0  # Fallback
        fx_date = sell_date
        total_premium_pln = total_premium_usd * fx_rate
        fx_success = False
    
    # Wyświetl szczegóły
    col_preview1, col_preview2, col_preview3 = st.columns(3)
    
    with col_preview1:
        st.markdown("**📊 Szczegóły CC:**")
        st.write(f"🏷️ **Ticker**: {ticker}")
        st.write(f"🎯 **Kontrakty**: {contracts}")
        st.write(f"📦 **Pokrycie**: {shares_covered} akcji")
        st.write(f"💰 **Strike**: ${strike_price:.2f}")
        st.write(f"📅 **Expiry**: {expiry_date}")
    
    with col_preview2:
        st.markdown("**💰 Kalkulacje USD:**")
        st.write(f"💵 **Premium/akcja**: ${premium_received:.2f}")
        st.write(f"🎯 **Premium łączna**: ${total_premium_usd:.2f}")
        st.write(f"📅 **Data sprzedaży**: {sell_date}")
        
        if fx_success:
            st.success(f"💱 **Kurs NBP** ({fx_date}): {fx_rate:.4f}")
        else:
            st.warning(f"⚠️ **Kurs fallback**: {fx_rate:.4f}")
    
    with col_preview3:
        st.markdown("**🇵🇱 Przeliczenie PLN:**")
        st.write(f"💰 **Premium PLN**: {total_premium_pln:.2f} zł")
        st.write(f"📊 **PLN/kontrakt**: {total_premium_pln/contracts:.2f} zł")
        
        # Dni do expiry
        days_to_expiry = (expiry_date - sell_date).days
        st.write(f"📅 **Dni do expiry**: {days_to_expiry}")
        
        if days_to_expiry <= 3:
            st.warning("⚠️ Krótkie expiry!")
    
    # Alokacja FIFO
    st.markdown("---")
    st.markdown("### 🔄 Alokacja pokrycia FIFO")
    
    for i, allocation in enumerate(coverage['fifo_preview']):
        with st.expander(f"LOT #{allocation['lot_id']} - {allocation['qty_to_reserve']} akcji", expanded=i<2):
            col_alloc1, col_alloc2 = st.columns(2)
            
            with col_alloc1:
                st.write(f"📅 **Data zakupu**: {allocation['buy_date']}")
                st.write(f"💰 **Cena zakupu**: ${allocation['buy_price_usd']:.2f}")
                st.write(f"📊 **Dostępne przed**: {allocation['qty_available']} akcji")
            
            with col_alloc2:
                st.write(f"🎯 **Do rezerwacji**: {allocation['qty_to_reserve']} akcji")
                st.write(f"📦 **Pozostanie**: {allocation['qty_remaining_after']} akcji")
                st.write(f"💱 **Kurs zakupu**: {allocation['fx_rate']:.4f}")
    
    # Przygotuj dane do zapisu
    cc_data = {
        'ticker': ticker,
        'contracts': contracts,
        'strike_usd': strike_price,
        'premium_sell_usd': premium_received,
        'open_date': sell_date,
        'expiry_date': expiry_date,
        'fx_open': fx_rate,
        'premium_sell_pln': total_premium_pln,
        'coverage': coverage
    }
    
    st.session_state.cc_to_save = cc_data
    
    # Przyciski akcji
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("💾 ZAPISZ COVERED CALL", type="primary", key="save_cc"):
            # PUNKT 54: Faktyczny zapis CC
            with st.spinner("Zapisywanie CC do bazy..."):
                save_result = db.save_covered_call_to_database(cc_data)
                
                if save_result['success']:
                    st.success(f"✅ **{save_result['message']}**")
                    st.info(f"💰 **Premium**: ${total_premium_usd:.2f} → {total_premium_pln:.2f} zł")
                    st.info(f"🔒 **Zarezerwowano**: {shares_covered} akcji {ticker}")
                    st.info(f"💸 **Cashflow utworzony**: +${total_premium_usd:.2f}")
                    
                    st.balloons()  # Celebracja! 🎈
                    
                    # NIE CZYŚCIMY SESSION STATE - pozwalamy na kolejne CC
                    st.success("✅ **Możesz teraz sprzedać kolejną CC!**")
                    
                else:
                    st.error(f"❌ **Błąd zapisu**: {save_result['message']}")
    
    with col_btn2:
        if st.button("➕ Nowa CC", key="new_cc_btn"):
            # Wyczyść formularz dla nowej CC
            if 'show_cc_preview' in st.session_state:
                del st.session_state.show_cc_preview
            if 'cc_form_data' in st.session_state:
                del st.session_state.cc_form_data
            if 'cc_to_save' in st.session_state:
                del st.session_state.cc_to_save
            st.rerun()
    
    with col_btn3:
        if st.button("❌ Anuluj", key="cancel_cc_preview"):
            if 'show_cc_preview' in st.session_state:
                del st.session_state.show_cc_preview
            if 'cc_form_data' in st.session_state:
                del st.session_state.cc_form_data
            if 'cc_to_save' in st.session_state:
                del st.session_state.cc_to_save
            st.rerun()
    
    # Status punktu
    st.markdown("---")
    st.success("✅ **PUNKTY 53-54 UKOŃCZONE**: Formularz sprzedaży CC z zapisem!")

def show_buyback_expiry_tab():
    """Tab buyback i expiry - PUNKT 56: Z funkcjami buyback/expiry"""
    st.subheader("💰 Buyback & Expiry")
    st.success("✅ **PUNKT 56 UKOŃCZONY** - Funkcje buyback i expiry CC")
    
    # Pobierz otwarte CC
    try:
        open_cc_list = db.get_covered_calls_summary(status='open')
        
        if not open_cc_list:
            st.info("💡 **Brak otwartych CC do zamknięcia**")
            st.markdown("*Sprzedaj CC w zakładce 'Sprzedaż CC'*")
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 💰 Buyback CC")
            st.info("Odkup opcji przed expiry z kalkulacją P/L PLN")
            
            # Wybór CC do buyback
            cc_options = [f"CC #{cc['id']} - {cc['ticker']} ${cc['strike_usd']:.2f} exp {cc['expiry_date']}" 
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
                    # Formularz buyback
                    with st.form("buyback_form"):
                        st.write(f"**Odkup CC #{selected_cc_id}:**")
                        st.write(f"📊 {selected_cc['ticker']} - {selected_cc['contracts']} kontraktów")
                        st.write(f"💰 Sprzedano @ ${selected_cc['premium_sell_usd']:.2f}/akcja")
                        
                        col_buy1, col_buy2 = st.columns(2)
                        
                        with col_buy1:
                            buyback_price = st.number_input(
                                "Cena buyback USD (za akcję):",
                                min_value=0.01,
                                value=max(0.01, selected_cc['premium_sell_usd'] * 0.5),  # 50% premium jako default
                                step=0.01,
                                format="%.2f"
                            )
                        
                        with col_buy2:
                            buyback_date = st.date_input(
                                "Data buyback:",
                                value=date.today()
                            )
                        
                        # Podgląd kalkulacji
                        contracts = selected_cc['contracts']
                        premium_received = selected_cc['premium_sell_usd'] * contracts * 100
                        buyback_cost = buyback_price * contracts * 100
                        pl_usd_preview = premium_received - buyback_cost
                        
                        st.write(f"**Podgląd P/L USD:**")
                        st.write(f"Premium otrzymana: ${premium_received:.2f}")
                        st.write(f"Koszt buyback: ${buyback_cost:.2f}")
                        if pl_usd_preview >= 0:
                            st.success(f"Zysk USD: +${pl_usd_preview:.2f}")
                        else:
                            st.error(f"Strata USD: ${pl_usd_preview:.2f}")
                        
                        submit_buyback = st.form_submit_button("💰 WYKONAJ BUYBACK", use_container_width=True)
                    
                    # Wykonanie buyback
                    if submit_buyback:
                        with st.spinner("Wykonywanie buyback..."):
                            result = db.buyback_covered_call(selected_cc_id, buyback_price, buyback_date)
                            
                            if result['success']:
                                st.success(f"✅ **{result['message']}**")
                                
                                # Pokaż szczegóły
                                pl_pln = result['pl_pln']
                                if pl_pln >= 0:
                                    st.success(f"🟢 **Zysk PLN**: +{pl_pln:.2f} zł")
                                else:
                                    st.error(f"🔴 **Strata PLN**: {pl_pln:.2f} zł")
                                
                                st.info(f"💰 Premium otrzymana: {result['premium_received_pln']:.2f} zł")
                                st.info(f"💸 Koszt buyback: {result['buyback_cost_pln']:.2f} zł")
                                st.info(f"🔓 Zwolniono: {result['shares_released']} akcji {selected_cc['ticker']}")
                                st.info(f"💱 Kurs buyback: {result['fx_close']:.4f} ({result['fx_close_date']})")
                                
                                st.balloons()
                                
                                # WYCZYŚĆ SESSION STATE z zakładki sprzedaż
                                if 'show_cc_preview' in st.session_state:
                                    del st.session_state.show_cc_preview
                                if 'cc_form_data' in st.session_state:
                                    del st.session_state.cc_form_data  
                                if 'cc_to_save' in st.session_state:
                                    del st.session_state.cc_to_save

                                # Krótkie opóźnienie i odświeżenie
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ **Błąd buyback**: {result['message']}")
        
        with col2:
            st.markdown("### 📅 Mark as Expired")
            st.info("Oznacz CC jako wygasłe (pełny zysk z premium)")
            
            # Wybór CC do expiry
            cc_expiry_options = [f"CC #{cc['id']} - {cc['ticker']} ${cc['strike_usd']:.2f} exp {cc['expiry_date']}" 
                               for cc in open_cc_list]
            
            if cc_expiry_options:
                selected_expiry_option = st.selectbox(
                    "Wybierz CC do expiry:",
                    options=cc_expiry_options,
                    key="expiry_select"
                )
                
                # Wyciągnij CC ID
                selected_expiry_id = int(selected_expiry_option.split('#')[1].split(' ')[0])
                selected_expiry_cc = next((cc for cc in open_cc_list if cc['id'] == selected_expiry_id), None)
                
                if selected_expiry_cc:
                    # Formularz expiry
                    with st.form("expiry_form"):
                        st.write(f"**Expiry CC #{selected_expiry_id}:**")
                        st.write(f"📊 {selected_expiry_cc['ticker']} - {selected_expiry_cc['contracts']} kontraktów")
                        st.write(f"💰 Premium: ${selected_expiry_cc['premium_sell_usd']:.2f}/akcja")
                        st.write(f"📅 Expiry: {selected_expiry_cc['expiry_date']}")
                        
                        # Podgląd zysku (pełna premium)
                        full_premium_pln = selected_expiry_cc['premium_sell_pln']
                        st.success(f"🟢 **Zysk przy expiry**: +{full_premium_pln:.2f} zł")
                        st.write("💡 Przy expiry - opcja wygasa bezwartościowo, zatrzymujesz pełną premium")
                        
                        submit_expiry = st.form_submit_button("📅 MARK AS EXPIRED", use_container_width=True)
                    
                    # Wykonanie expiry
                    if submit_expiry:
                        with st.spinner("Oznaczanie jako expired..."):
                            result = db.expire_covered_call(selected_expiry_id)
                            
                            if result['success']:
                                st.success(f"✅ **{result['message']}**")
                                st.success(f"🟢 **Zysk PLN**: +{result['pl_pln']:.2f} zł")
                                st.info(f"🔓 Zwolniono: {result['shares_released']} akcji {selected_expiry_cc['ticker']}")
                                st.info(f"📅 Data expiry: {result['expiry_date']}")
                                
                                st.balloons()
                                
                                # WYCZYŚĆ SESSION STATE z zakładki sprzedaż
                                if 'show_cc_preview' in st.session_state:
                                    del st.session_state.show_cc_preview
                                if 'cc_form_data' in st.session_state:
                                    del st.session_state.cc_form_data
                                if 'cc_to_save' in st.session_state:  
                                    del st.session_state.cc_to_save

                                # Krótkie opóźnienie i odświeżenie
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ **Błąd expiry**: {result['message']}")
        
        # Test funkcji PUNKT 56
        st.markdown("---")
        if st.button("🧪 Test funkcji buyback/expiry (PUNKT 56)"):
            test_results = db.test_buyback_expiry_operations()
            
            col_test1, col_test2, col_test3 = st.columns(3)
            
            with col_test1:
                if test_results.get('buyback_function_test'):
                    st.success("✅ Funkcja buyback")
                else:
                    st.error("❌ Funkcja buyback")
            
            with col_test2:
                if test_results.get('expiry_function_test'):
                    st.success("✅ Funkcja expiry")
                else:
                    st.error("❌ Funkcja expiry")
            
            with col_test3:
                if test_results.get('cc_list_test'):
                    st.success("✅ Lista CC")
                else:
                    st.error("❌ Lista CC")
    
    except Exception as e:
        st.error(f"❌ Błąd w buyback/expiry: {e}")
    
    # Status punktu
    st.markdown("---")
    st.success("✅ **PUNKT 56 UKOŃCZONY** - Funkcje buyback i expiry z kalkulacją P/L PLN!")
    st.info("🔄 **NASTĘPNY KROK**: PUNKT 57-58 - Finalizacja buyback/expiry")


def get_portfolio_cc_summary():
    """
    PUNKT 66: Podsumowanie całego portfela CC
    """
    try:
        conn = get_connection()
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
    PUNKT 66: Zaawansowana tabela otwartych CC z rozbiciami FIFO
    """
    st.subheader("📊 Otwarte pozycje CC")
    st.success("✅ **PUNKT 66 UKOŃCZONY** - Zaawansowane tabele z pokryciem FIFO")
    
    # Podsumowanie portfela
    portfolio_summary = db.get_portfolio_cc_summary()
    
    if portfolio_summary['open_cc_count'] == 0:
        st.info("💡 **Brak otwartych pozycji CC**")
        st.markdown("*Sprzedaj pierwszą opcję w zakładce 'Sprzedaż CC'*")
        return
    
    # METRICS OVERVIEW
    st.markdown("### 📈 Podsumowanie portfela CC")
    
    col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
    
    with col_metric1:
        st.metric(
            "🎯 Otwarte CC",
            f"{portfolio_summary['open_cc_count']}",
            help="Liczba otwartych pozycji"
        )
    
    with col_metric2:
        st.metric(
            "📦 Kontrakty",
            f"{portfolio_summary['total_open_contracts']}",
            help="Suma wszystkich kontraktów"
        )
    
    with col_metric3:
        st.metric(
            "🔒 Akcje zarezerwowane",
            f"{portfolio_summary['total_shares_reserved']}",
            help="Akcje pod pokryciem CC"
        )
    
    with col_metric4:
        st.metric(
            "💰 Premium PLN",
            f"{portfolio_summary['total_open_premium_pln']:,.0f} zł",
            help="Łączna otrzymana premium"
        )
    
    # BREAKDOWN PER TICKER
    if portfolio_summary['ticker_stats']:
        st.markdown("### 📊 Rozkład per ticker")
        
        ticker_data = []
        for stat in portfolio_summary['ticker_stats']:
            ticker_data.append({
                'Ticker': stat['ticker'],
                'CC Count': stat['cc_count'],
                'Kontrakty': stat['total_contracts'],
                'Akcje': stat['shares_reserved'],
                'Premium PLN': f"{stat['total_premium_pln']:,.0f} zł"
            })
        
        st.dataframe(ticker_data, use_container_width=True)
    
    # SZCZEGÓŁOWE TABELE CC
    st.markdown("### 🔍 Szczegółowe pozycje CC")
    
    coverage_details = db.get_cc_coverage_details()
    
    if not coverage_details:
        st.error("❌ Błąd pobierania szczegółów pokrycia")
        return
    
    # Sprawdź alerty expiry
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
        
        # Expander per CC
        with st.expander(
            f"{alert_color} CC #{cc_detail['cc_id']} - {cc_detail['ticker']} @ ${cc_detail['strike_usd']} ({alert_text})",
            expanded=(days_to_expiry <= 3)
        ):
            
            col_cc1, col_cc2, col_cc3 = st.columns(3)
            
            with col_cc1:
                st.markdown("**📊 Parametry CC:**")
                st.write(f"🎯 **Strike**: ${cc_detail['strike_usd']:.2f}")
                st.write(f"📦 **Kontrakty**: {cc_detail['contracts']} = {cc_detail['shares_needed']} akcji")
                st.write(f"💰 **Premium**: ${cc_detail['premium_sell_usd']:.2f} = {cc_detail['premium_sell_pln']:.0f} PLN")
                st.write(f"💱 **FX Open**: {cc_detail['fx_open']:.4f}")
            
            with col_cc2:
                st.markdown("**📅 Harmonogram:**")
                st.write(f"📅 **Otwarte**: {cc_detail['open_date']}")
                st.write(f"📅 **Expiry**: {cc_detail['expiry_date']}")
                st.write(f"⏱️ **Dni do expiry**: {cc_detail['days_to_expiry']}")
                st.write(f"📈 **Dni trzymane**: {cc_detail['days_held']}")
            
            with col_cc3:
                st.markdown("**💹 Yield Analysis:**")
                st.write(f"🏦 **Koszt bazowy**: {cc_detail['total_cost_basis']:,.0f} PLN")
                st.write(f"📊 **Premium yield**: {cc_detail['premium_yield_pct']:.2f}%")
                st.write(f"📈 **Annualized yield**: {cc_detail['annualized_yield_pct']:.1f}%")
                
                # Yield quality indicator
                if cc_detail['annualized_yield_pct'] >= 20:
                    st.success("🚀 Excellent yield")
                elif cc_detail['annualized_yield_pct'] >= 12:
                    st.info("✅ Good yield")
                elif cc_detail['annualized_yield_pct'] >= 8:
                    st.warning("⚠️ Moderate yield")
                else:
                    st.error("❌ Low yield")
            
            # FIFO COVERAGE TABLE
            if cc_detail['lot_allocations']:
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
                        'Koszt pokrycia': f"{alloc['total_cost_pln']:.0f} zł"
                    })
                
                st.dataframe(fifo_data, use_container_width=True)
                
                # Podsumowanie pokrycia
                total_covered = sum([alloc['shares_allocated'] for alloc in cc_detail['lot_allocations']])
                if total_covered == cc_detail['shares_needed']:
                    st.success(f"✅ Pełne pokrycie: {total_covered}/{cc_detail['shares_needed']} akcji")
                else:
                    st.warning(f"⚠️ Niepełne pokrycie: {total_covered}/{cc_detail['shares_needed']} akcji")
            else:
                st.error("❌ Brak informacji o pokryciu FIFO!")
    
    # Quick Actions
    st.markdown("---")
    st.markdown("### ⚡ Szybkie akcje")
    
    col_action1, col_action2, col_action3 = st.columns(3)
    
    with col_action1:
        if st.button("🔄 Odśwież dane", key="refresh_open_cc"):
            st.rerun()
    
    with col_action2:
        if st.button("💸 Buyback CC", key="quick_buyback"):
            st.info("💡 Przejdź do zakładki 'Buyback & Expiry'")
    
    with col_action3:
        if st.button("📈 Sprzedaj kolejne CC", key="quick_sell_more"):
            st.info("💡 Przejdź do zakładki 'Sprzedaż CC'")

def show_cc_history_tab():
    """
    PUNKT 67: Historia CC z zaawansowaną analizą P/L (CLEANUP UI)
    """
    st.subheader("📋 Historia Covered Calls")
    
    # CLEANUP: Usunięto deweloperskie komunikaty
    # st.success("✅ **PUNKT 57 UKOŃCZONY** - Historia CC z filtrami i eksportem CSV")
    
    # Performance Summary
    performance = db.get_cc_performance_summary()
    
    if performance and performance.get('total_closed', 0) > 0:
        st.markdown("### 📊 Performance Summary")
        
        col_perf1, col_perf2, col_perf3, col_perf4 = st.columns(4)
        
        with col_perf1:
            st.metric(
                "💰 Total P/L",
                f"{performance['total_realized_pl']:,.0f} PLN",
                help="Łączny zrealizowany P/L"
            )
        
        with col_perf2:
            st.metric(
                "📈 Avg per CC",
                f"{performance['avg_pl_per_cc']:,.0f} PLN",
                help="Średni P/L na pozycję"
            )
        
        with col_perf3:
            win_rate = (performance['expired_count'] / performance['total_closed'] * 100) if performance['total_closed'] > 0 else 0
            st.metric(
                "🏆 Win Rate",
                f"{win_rate:.1f}%",
                help="% opcji które wygasły (max profit)"
            )
        
        with col_perf4:
            st.metric(
                "📝 Total Closed",
                f"{performance['total_closed']}",
                help=f"Expired: {performance['expired_count']}, Bought back: {performance['buyback_count']}"
            )
        
        # Performance per ticker
        if performance['ticker_performance']:
            st.markdown("### 🎯 Performance per ticker")
            
            ticker_data = []
            for ticker_perf in performance['ticker_performance']:
                ticker_data.append({
                    'Ticker': ticker_perf['ticker'],
                    'CC Count': ticker_perf['cc_count'],
                    'Total P/L': f"{ticker_perf['total_pl']:,.0f} PLN",
                    'Avg P/L': f"{ticker_perf['avg_pl']:,.0f} PLN",
                    'Win Rate': f"{ticker_perf['win_rate']:.1f}%",
                    'Expired': ticker_perf['expired_count'],
                    'Bought Back': ticker_perf['buyback_count']
                })
            
            st.dataframe(ticker_data, use_container_width=True)
    
    # Szczegółowa historia
    st.markdown("### 📋 Detailed History")
    
    closed_cc_analysis = db.get_closed_cc_analysis()
    
    if not closed_cc_analysis:
        st.info("📝 **Brak zamkniętych CC**")
        st.markdown("*Historia pojawi się po buyback lub expiry pierwszych opcji*")
        return
    
    # CLEANUP: Uproszczone filtry (bez zbędnych expander-ów)
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        all_tickers = sorted(list(set([cc['ticker'] for cc in closed_cc_analysis])))
        selected_tickers = st.multiselect(
            "Filtry - Tickery:",
            options=all_tickers,
            default=all_tickers,
            key="history_ticker_filter"
        )
    
    with col_filter2:
        status_filter = st.selectbox(
            "Status:",
            options=["Wszystkie", "Expired", "Bought back"],
            key="history_status_filter"
        )
    
    with col_filter3:
        sort_options = ["Date ↓", "P/L ↓", "Yield ↓", "Ticker A-Z"]
        sort_by = st.selectbox(
            "Sortowanie:",
            options=sort_options,
            key="history_sort_filter"
        )
    
    # Aplikuj filtry
    filtered_cc = []
    for cc in closed_cc_analysis:
        # Filtr ticker
        if cc['ticker'] not in selected_tickers:
            continue
        
        # Filtr status
        if status_filter != "Wszystkie":
            if status_filter == "Expired" and cc['status'] != 'expired':
                continue
            elif status_filter == "Bought back" and cc['status'] != 'bought_back':
                continue
        
        filtered_cc.append(cc)
    
    # Sortowanie
    if sort_by == "Date ↓":
        filtered_cc.sort(key=lambda x: x['close_date'], reverse=True)
    elif sort_by == "P/L ↓":
        filtered_cc.sort(key=lambda x: x['pl_pln'], reverse=True)
    elif sort_by == "Yield ↓":
        filtered_cc.sort(key=lambda x: x['annualized_yield_pct'], reverse=True)
    elif sort_by == "Ticker A-Z":
        filtered_cc.sort(key=lambda x: x['ticker'])
    
    if not filtered_cc:
        st.warning("⚠️ Brak CC po zastosowaniu filtrów")
        return
    
    # Tabela szczegółowa
    st.write(f"**Wyniki:** {len(filtered_cc)} z {len(closed_cc_analysis)} CC")
    
    for cc in filtered_cc:
        # Color coding based on P/L
        if cc['pl_pln'] > 0:
            pl_emoji = "💚"
            pl_color = "success"
        elif cc['pl_pln'] < 0:
            pl_emoji = "❤️"
            pl_color = "error"
        else:
            pl_emoji = "⚪"
            pl_color = "info"
        
        with st.expander(
            f"{cc['outcome_emoji']} {pl_emoji} CC #{cc['cc_id']} - {cc['ticker']} - {cc['pl_pln']:+,.0f} PLN ({cc['annualized_yield_pct']:+.1f}% p.a.)",
            expanded=False
        ):
            
            col_detail1, col_detail2, col_detail3 = st.columns(3)
            
            with col_detail1:
                st.markdown("**📊 Podstawowe info:**")
                st.write(f"🎯 **Ticker**: {cc['ticker']} ({cc['contracts']} kontr.)")
                st.write(f"💰 **Strike**: ${cc['strike_usd']:.2f}")
                st.write(f"📅 **Opened**: {cc['open_date']}")
                st.write(f"📅 **Closed**: {cc['close_date']}")
                st.write(f"⏱️ **Days held**: {cc['days_held']}")
                st.write(f"🏷️ **Status**: {cc['outcome_text']}")
            
            with col_detail2:
                st.markdown("**💸 Premium Analysis:**")
                st.write(f"📈 **Sell Premium**: ${cc['premium_sell_usd']:.2f} = {cc['premium_sell_pln']:.0f} PLN")
                if cc['premium_buyback_usd'] > 0:
                    st.write(f"📉 **Buyback Premium**: ${cc['premium_buyback_usd']:.2f} = {cc['premium_buyback_pln']:.0f} PLN")
                st.write(f"💰 **Net Premium**: ${cc['net_premium_usd']:.2f} = {cc['net_premium_pln']:.0f} PLN")
                st.write(f"💱 **FX Open**: {cc['fx_open']:.4f}")
                if cc['fx_close'] != cc['fx_open']:
                    st.write(f"💱 **FX Close**: {cc['fx_close']:.4f}")
            
            with col_detail3:
                st.markdown("**📈 Performance:**")
                
                # P/L display with color
                if cc['pl_pln'] > 0:
                    st.success(f"💚 **P/L**: +{cc['pl_pln']:.0f} PLN")
                elif cc['pl_pln'] < 0:
                    st.error(f"❤️ **P/L**: {cc['pl_pln']:.0f} PLN")
                else:
                    st.info(f"⚪ **P/L**: {cc['pl_pln']:.0f} PLN")
                
                st.write(f"📊 **Premium Yield**: {cc['premium_yield_pct']:.2f}%")
                st.write(f"📅 **Annualized**: {cc['annualized_yield_pct']:.1f}% p.a.")
                
                # Performance rating
                if cc['annualized_yield_pct'] >= 20:
                    st.success("🚀 Excellent")
                elif cc['annualized_yield_pct'] >= 12:
                    st.info("✅ Good")
                elif cc['annualized_yield_pct'] >= 8:
                    st.warning("⚠️ OK")
                else:
                    st.error("❌ Poor")
    
    # Export functionality
    st.markdown("---")
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        if st.button("📊 Export do CSV", key="export_history"):
            # Przygotuj dane do eksportu
            export_data = []
            for cc in filtered_cc:
                export_data.append({
                    'CC_ID': cc['cc_id'],
                    'Ticker': cc['ticker'],
                    'Contracts': cc['contracts'],
                    'Strike_USD': cc['strike_usd'],
                    'Premium_Sell_USD': cc['premium_sell_usd'],
                    'Premium_Sell_PLN': cc['premium_sell_pln'],
                    'Premium_Buyback_USD': cc['premium_buyback_usd'],
                    'Premium_Buyback_PLN': cc['premium_buyback_pln'],
                    'Net_Premium_PLN': cc['net_premium_pln'],
                    'P/L_PLN': cc['pl_pln'],
                    'Open_Date': cc['open_date'],
                    'Close_Date': cc['close_date'],
                    'Days_Held': cc['days_held'],
                    'Status': cc['status'],
                    'Premium_Yield_%': round(cc['premium_yield_pct'], 2),
                    'Annualized_Yield_%': round(cc['annualized_yield_pct'], 1),
                    'FX_Open': cc['fx_open'],
                    'FX_Close': cc['fx_close']
                })
            
            import pandas as pd
            df = pd.DataFrame(export_data)
            csv = df.to_csv(index=False)
            
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            st.download_button(
                label="💾 Pobierz CSV",
                data=csv,
                file_name=f"cc_history_{timestamp}.csv",
                mime="text/csv",
                key="download_history_csv"
            )
    
    with col_export2:
        st.info(f"📋 **{len(filtered_cc)} CC** ready to export")

    

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

if __name__ == "__main__":
    show_options()  