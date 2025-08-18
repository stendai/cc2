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
    """Główna funkcja modułu Options"""
    
    st.header("🎯 Options - Covered Calls")
    st.markdown("*ETAP 4: Profesjonalne zarządzanie opcjami pokrytymi z rezerwacjami FIFO*")
    
    # Status ETAPU 4
    st.success("🚀 **PUNKTY 51-56 UKOŃCZONE** - Sprzedaż, buyback i expiry CC!")
    
    # Sprawdzenie gotowości do ETAPU 4
    st.markdown("### 🔍 Status systemu Options")
    
    try:
        # Test 1: Dostępność akcji w portfelu
        lots_stats = db.get_lots_stats()
        
        col_check1, col_check2, col_check3 = st.columns(3)
        
        with col_check1:
            if lots_stats['open_shares'] > 0:
                st.success(f"✅ **Akcje dostępne**: {lots_stats['open_shares']} szt.")
                shares_ready = True
            else:
                st.error("❌ **Brak akcji** - dodaj LOT-y w module Stocks")
                shares_ready = False
        
        with col_check2:
            # Test NBP API
            try:
                test_rate = nbp_api_client.get_usd_rate_for_date(date.today())
                if test_rate:
                    st.success("✅ **NBP API**: Działający")
                    nbp_ready = True
                else:
                    st.warning("⚠️ **NBP API**: Problem")
                    nbp_ready = False
            except:
                st.error("❌ **NBP API**: Błąd")
                nbp_ready = False
        
        with col_check3:
            # Test tabeli options_cc
            try:
                cc_stats = db.get_cc_reservations_summary()
                st.success(f"✅ **CC aktywne**: {cc_stats.get('open_cc_count', 0)}")
                table_ready = True
            except Exception as e:
                st.error(f"❌ **Tabela CC**: {e}")
                table_ready = False
        
        # Podsumowanie gotowości
        readiness_score = sum([shares_ready, nbp_ready, table_ready])
        
        if readiness_score == 3:
            st.success("🎉 **SYSTEM DZIAŁA PERFEKCYJNIE!**")
        elif readiness_score >= 2:
            st.warning("⚠️ **System częściowo gotowy** - można kontynuować")
        else:
            st.error("❌ **System wymaga uwagi**")
            
    except Exception as e:
        st.error(f"❌ Błąd sprawdzania gotowości: {e}")
    
    # Zakładki modułu Options
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Sprzedaż CC", 
        "💰 Buyback & Expiry", 
        "🔄 Rolowanie", 
        "📊 Otwarte CC", 
        "📋 Historia CC"
    ])
    
    with tab1:
        show_sell_cc_tab()
    
    with tab2:
        show_buyback_expiry_tab()
    
    with tab3:
        show_rolling_tab()
    
    with tab4:
        show_open_cc_tab()
    
    with tab5:
        show_cc_history_tab()

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

def show_rolling_tab():
    """Tab rolowania opcji"""
    st.subheader("🔄 Rolowanie opcji")
    st.info("**PUNKT 65**: Roll jako dwie operacje (buyback + nowa sprzedaż)")
    
    st.markdown("""
    **🎯 FUNKCJONALNOŚĆ ROLOWANIA:**
    - ⏳ Kombinacja buyback starej CC + sprzedaż nowej CC
    - ⏳ Automatyczne przeniesienie rezerwacji akcji
    - ⏳ Kalkulacja net credit/debit operacji
    - ⏳ Zapis jako dwie osobne operacje w bazie
    """)

def show_open_cc_tab():
    """Tab otwartych pozycji CC - PUNKT 55: Pokazanie faktycznych danych"""
    st.subheader("📊 Otwarte pozycje CC")
    st.success("✅ **PUNKT 55 UKOŃCZONY** - Finalizacja sprzedaży CC z alertami expiry")
    
    # Pobierz otwarte CC z bazy
    try:
        open_cc_list = db.get_covered_calls_summary(status='open')
        
        if not open_cc_list:
            st.info("💡 **Brak otwartych pozycji CC**")
            st.markdown("*Sprzedaj pierwszą opcję w zakładce 'Sprzedaż CC'*")
            return
        
        st.write(f"🎯 **Otwarte pozycje CC**: {len(open_cc_list)}")
        
        # Sprawdź alerty expiry ≤ 3 dni
        today = date.today()
        alert_threshold = today + timedelta(days=3)
        
        expiry_alerts = []
        for cc in open_cc_list:
            expiry_date = cc['expiry_date']
            if isinstance(expiry_date, str):
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            
            if expiry_date <= alert_threshold:
                days_left = (expiry_date - today).days
                expiry_alerts.append({
                    'cc': cc,
                    'days_left': days_left,
                    'expiry_date': expiry_date
                })
        
        # ALERTY EXPIRY
        if expiry_alerts:
            st.markdown("### 🚨 Alerty Expiry ≤ 3 dni")
            
            for alert in expiry_alerts:
                cc = alert['cc']
                days_left = alert['days_left']
                
                if days_left <= 0:
                    alert_type = "🔴 **EXPIRED**"
                    alert_color = "error"
                elif days_left <= 1:
                    alert_type = "🟠 **1 DZIEŃ**"
                    alert_color = "warning"
                else:
                    alert_type = f"🟡 **{days_left} DNI**"
                    alert_color = "warning"
                
                with st.container():
                    if alert_color == "error":
                        st.error(f"{alert_type} - CC #{cc['id']} {cc['ticker']} ${cc['strike_usd']:.2f} exp {alert['expiry_date']}")
                    else:
                        st.warning(f"{alert_type} - CC #{cc['id']} {cc['ticker']} ${cc['strike_usd']:.2f} exp {alert['expiry_date']}")
        
        # TABELA OTWARTYCH CC
        st.markdown("### 📋 Wszystkie otwarte pozycje")
        
        # Przygotuj dane do tabeli
        table_data = []
        total_premium_pln = 0
        total_contracts = 0
        
        for cc in open_cc_list:
            # Oblicz dni do expiry
            expiry_date = cc['expiry_date']
            if isinstance(expiry_date, str):
                expiry_date_obj = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            else:
                expiry_date_obj = expiry_date
            
            days_to_expiry = (expiry_date_obj - today).days
            
            # Status expiry
            if days_to_expiry <= 0:
                expiry_status = "🔴 EXPIRED"
            elif days_to_expiry <= 3:
                expiry_status = f"🟠 {days_to_expiry}d"
            elif days_to_expiry <= 7:
                expiry_status = f"🟡 {days_to_expiry}d"
            else:
                expiry_status = f"🟢 {days_to_expiry}d"
            
            table_data.append({
                'ID': cc['id'],
                'Ticker': cc['ticker'],
                'Kontrakty': cc['contracts'],
                'Strike': f"${cc['strike_usd']:.2f}",
                'Premium/akcja': f"${cc['premium_sell_usd']:.2f}",
                'Premium PLN': f"{cc['premium_sell_pln']:.2f} zł",
                'Open Date': cc['open_date'],
                'Expiry': cc['expiry_date'],
                'Status Expiry': expiry_status,
                'Kurs Open': f"{cc['fx_open']:.4f}"
            })
            
            total_premium_pln += cc['premium_sell_pln']
            total_contracts += cc['contracts']
        
        # Wyświetl tabelę
        df_open_cc = pd.DataFrame(table_data)
        
        st.dataframe(
            df_open_cc,
            use_container_width=True,
            height=400,
            column_config={
                'ID': st.column_config.NumberColumn('ID', width=60),
                'Ticker': st.column_config.TextColumn('Ticker', width=80),
                'Kontrakty': st.column_config.NumberColumn('Kontrakty', width=80),
                'Strike': st.column_config.TextColumn('Strike', width=90),
                'Premium/akcja': st.column_config.TextColumn('Premium/akcja', width=100),
                'Premium PLN': st.column_config.TextColumn('Premium PLN', width=120),
                'Open Date': st.column_config.DateColumn('Open Date', width=110),
                'Expiry': st.column_config.DateColumn('Expiry', width=110),
                'Status Expiry': st.column_config.TextColumn('Status Expiry', width=100),
                'Kurs Open': st.column_config.TextColumn('Kurs Open', width=90)
            }
        )
        
        # PODSUMOWANIE
        st.markdown("### 📊 Podsumowanie otwartych CC")
        
        col_summary1, col_summary2, col_summary3, col_summary4 = st.columns(4)
        
        with col_summary1:
            st.metric("🎯 Pozycje CC", len(open_cc_list))
        
        with col_summary2:
            st.metric("📊 Kontrakty", total_contracts)
            st.caption(f"{total_contracts * 100} akcji zarezerwowane")
        
        with col_summary3:
            st.metric("💰 Premium łączna", f"{total_premium_pln:.2f} zł")
        
        with col_summary4:
            alert_count = len(expiry_alerts)
            if alert_count > 0:
                st.metric("🚨 Alerty expiry", alert_count, delta_color="inverse")
            else:
                st.metric("✅ Alerty expiry", "0", delta_color="normal")
        
        # SPRAWDZENIE REZERWACJI AKCJI
        st.markdown("### 🔒 Sprawdzenie rezerwacji akcji")
        
        if st.button("📊 Pokaż wpływ na portfel akcji"):
            # Sprawdź quantity_open przed i po CC
            for cc in open_cc_list:
                ticker = cc['ticker']
                contracts = cc['contracts']
                
                st.write(f"**CC #{cc['id']} - {ticker}**: {contracts} kontraktów = {contracts * 100} akcji zarezerwowane")
                
                # Pokaż dostępne akcje teraz
                available_now = db.get_available_quantity(ticker)
                st.write(f"   → Dostępne teraz: {available_now} akcji")
                
                if available_now < 100:
                    st.warning(f"   ⚠️ Za mało akcji na kolejne CC")
                else:
                    max_new_cc = available_now // 100
                    st.info(f"   ✅ Można sprzedać jeszcze {max_new_cc} CC")
                
    except Exception as e:
        st.error(f"❌ Błąd pobierania otwartych CC: {e}")

def show_cc_history_tab():
    """Tab historii CC - PUNKT 57: Z filtrami i eksportem CSV"""
    st.subheader("📋 Historia Covered Calls")
    st.success("✅ **PUNKT 57 UKOŃCZONY** - Historia CC z filtrami i eksportem CSV")
    
    # Pobierz wszystkie CC
    try:
        all_cc_list = db.get_covered_calls_summary()  # Wszystkie CC
        
        if not all_cc_list:
            st.info("💡 **Brak historii CC**")
            st.markdown("*Historia pojawi się po sprzedaży pierwszych opcji*")
            return
        
        # FILTRY W EXPANDER
        with st.expander("🔍 Filtry i sortowanie", expanded=False):
            col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
            
            with col_filter1:
                all_tickers = sorted(list(set([cc['ticker'] for cc in all_cc_list])))
                selected_tickers = st.multiselect(
                    "Tickery:",
                    options=all_tickers,
                    default=all_tickers,
                    key="cc_ticker_filter"
                )
            
            with col_filter2:
                status_options = ["Wszystkie", "Otwarte", "Bought back", "Expired"]
                selected_status = st.selectbox(
                    "Status:",
                    options=status_options,
                    index=0,
                    key="cc_status_filter"
                )
            
            with col_filter3:
                pl_options = ["Wszystkie", "Tylko zyski", "Tylko straty", "Bez P/L (otwarte)"]
                selected_pl = st.selectbox(
                    "P/L:",
                    options=pl_options,
                    index=0,
                    key="cc_pl_filter"
                )
            
            with col_filter4:
                sort_options = {
                    "Data otwarcia (najnowsze)": ("open_date", True),
                    "Data otwarcia (najstarsze)": ("open_date", False),
                    "P/L (najwyższy)": ("pl_pln", True),
                    "Premium (najwyższa)": ("premium_sell_pln", True),
                    "Ticker A-Z": ("ticker", False)
                }
                
                selected_sort = st.selectbox(
                    "Sortowanie:",
                    options=list(sort_options.keys()),
                    index=0,
                    key="cc_sort_filter"
                )
        
        # APLIKACJA FILTRÓW
        filtered_cc = []
        
        for cc in all_cc_list:
            # Filtr tickery
            if cc['ticker'] not in selected_tickers:
                continue
            
            # Filtr status
            if selected_status != "Wszystkie":
                if selected_status == "Otwarte" and cc['status'] != 'open':
                    continue
                elif selected_status == "Bought back" and cc['status'] != 'bought_back':
                    continue
                elif selected_status == "Expired" and cc['status'] != 'expired':
                    continue
            
            # Filtr P/L
            if selected_pl != "Wszystkie":
                pl_pln = cc['pl_pln'] or 0
                if selected_pl == "Tylko zyski" and pl_pln <= 0:
                    continue
                elif selected_pl == "Tylko straty" and pl_pln >= 0:
                    continue
                elif selected_pl == "Bez P/L (otwarte)" and cc['status'] != 'open':
                    continue
            
            filtered_cc.append(cc)
        
        # SORTOWANIE
        sort_field, sort_desc = sort_options[selected_sort]
        
        if sort_field == "open_date":
            filtered_cc.sort(key=lambda x: x['open_date'], reverse=sort_desc)
        elif sort_field == "ticker":
            filtered_cc.sort(key=lambda x: x['ticker'], reverse=sort_desc)
        elif sort_field == "pl_pln":
            filtered_cc.sort(key=lambda x: x['pl_pln'] or 0, reverse=sort_desc)
        elif sort_field == "premium_sell_pln":
            filtered_cc.sort(key=lambda x: x['premium_sell_pln'], reverse=sort_desc)
        
        # INFORMACJA O FILTRACH
        if len(filtered_cc) != len(all_cc_list):
            st.info(f"🔍 Pokazano **{len(filtered_cc)}** z **{len(all_cc_list)}** pozycji CC")
        
        if not filtered_cc:
            st.warning("🔍 Brak CC pasujących do filtrów")
            return
        
        st.write(f"📋 **Historia CC**: {len(filtered_cc)} pozycji")
        
        # Przygotuj dane do tabeli
        history_data = []
        total_pl_pln = 0
        total_premium_pln = 0
        open_count = 0
        closed_count = 0
        
        for cc in filtered_cc:
            # Status zamknięcia i ikony
            if cc['status'] == 'open':
                close_status = "🟢 Otwarte"
                close_method = "Aktywne"
                open_count += 1
            elif cc['status'] == 'expired':
                close_status = "📅 Expired"
                close_method = "Wygasła"
                closed_count += 1
            else:
                close_status = "💰 Bought back"
                close_method = "Odkupiona"
                closed_count += 1
            
            pl_pln = cc['pl_pln'] or 0
            premium_pln = cc['premium_sell_pln']
            
            total_pl_pln += pl_pln
            total_premium_pln += premium_pln
            
            # Status P/L z kolorami
            if cc['status'] == 'open':
                pl_status = f"⏳ {premium_pln:.2f} zł"  # Potencjalny zysk
            elif pl_pln >= 0:
                pl_status = f"🟢 +{pl_pln:.2f} zł"
            else:
                pl_status = f"🔴 {pl_pln:.2f} zł"
            
            # Kalkulacja yield (annualized)
            if cc['status'] == 'open':
                # Dni od otwarcia
                open_date_obj = datetime.strptime(cc['open_date'], '%Y-%m-%d').date() if isinstance(cc['open_date'], str) else cc['open_date']
                days_held = (date.today() - open_date_obj).days or 1
            else:
                # Dni całkowite (od open do close)
                open_date_obj = datetime.strptime(cc['open_date'], '%Y-%m-%d').date() if isinstance(cc['open_date'], str) else cc['open_date']
                if cc['status'] == 'expired':
                    expiry_date_obj = datetime.strptime(cc['expiry_date'], '%Y-%m-%d').date() if isinstance(cc['expiry_date'], str) else cc['expiry_date']
                    days_held = (expiry_date_obj - open_date_obj).days or 1
                else:
                    # Bought back - używamy expiry jako przybliżenia
                    expiry_date_obj = datetime.strptime(cc['expiry_date'], '%Y-%m-%d').date() if isinstance(cc['expiry_date'], str) else cc['expiry_date']
                    days_held = (expiry_date_obj - open_date_obj).days or 1
            
            # Yield calculation (premium relative to strike value)
            strike_value_pln = cc['strike_usd'] * cc['contracts'] * 100 * cc['fx_open']
            if strike_value_pln > 0:
                yield_percent = (premium_pln / strike_value_pln) * 100
                annualized_yield = yield_percent * (365 / days_held) if days_held > 0 else 0
                yield_display = f"{annualized_yield:.1f}%"
            else:
                yield_display = "N/A"
            
            history_data.append({
                'ID': cc['id'],
                'Ticker': cc['ticker'],
                'Kontrakty': cc['contracts'],
                'Strike': f"${cc['strike_usd']:.2f}",
                'Premium/akcja': f"${cc['premium_sell_usd']:.2f}",
                'Premium PLN': f"{premium_pln:.2f} zł",
                'Open Date': cc['open_date'],
                'Expiry': cc['expiry_date'],
                'Status': close_status,
                'P/L PLN': pl_status,
                'Yield Ann.': yield_display,
                'Dni': days_held,
                'Kurs Open': f"{cc['fx_open']:.4f}"
            })
        
        # Wyświetl tabelę
        df_history = pd.DataFrame(history_data)
        
        st.dataframe(
            df_history,
            use_container_width=True,
            height=400,
            column_config={
                'ID': st.column_config.NumberColumn('ID', width=50),
                'Ticker': st.column_config.TextColumn('Ticker', width=70),
                'Kontrakty': st.column_config.NumberColumn('Kontrakty', width=70),
                'Strike': st.column_config.TextColumn('Strike', width=80),
                'Premium/akcja': st.column_config.TextColumn('Premium/akcja', width=90),
                'Premium PLN': st.column_config.TextColumn('Premium PLN', width=100),
                'Open Date': st.column_config.DateColumn('Open Date', width=100),
                'Expiry': st.column_config.DateColumn('Expiry', width=100),
                'Status': st.column_config.TextColumn('Status', width=110),
                'P/L PLN': st.column_config.TextColumn('P/L PLN', width=100),
                'Yield Ann.': st.column_config.TextColumn('Yield Ann.', width=80),
                'Dni': st.column_config.NumberColumn('Dni', width=60),
                'Kurs Open': st.column_config.TextColumn('Kurs Open', width=80)
            }
        )
        
        # PODSUMOWANIE SZCZEGÓŁOWE
        st.markdown("### 📊 Szczegółowe podsumowanie")
        
        col_summary1, col_summary2, col_summary3, col_summary4, col_summary5 = st.columns(5)
        
        with col_summary1:
            st.metric("📋 Łączne CC", len(filtered_cc))
            st.caption(f"Otwarte: {open_count}, Zamknięte: {closed_count}")
        
        with col_summary2:
            total_contracts = sum([cc['contracts'] for cc in filtered_cc])
            st.metric("🎯 Kontrakty", total_contracts)
            st.caption(f"{total_contracts * 100} akcji objęte")
        
        with col_summary3:
            st.metric("💰 Premium łączna", f"{total_premium_pln:.2f} zł")
            st.caption("Suma wszystkich premium")
        
        with col_summary4:
            if closed_count > 0:
                profitable = len([cc for cc in filtered_cc if (cc['pl_pln'] or 0) >= 0 and cc['status'] != 'open'])
                win_rate = (profitable / closed_count) * 100 if closed_count > 0 else 0
                st.metric("🎯 Win Rate", f"{win_rate:.1f}%")
                st.caption(f"{profitable}/{closed_count} zyskowne")
            else:
                st.metric("🎯 Win Rate", "N/A")
                st.caption("Brak zamkniętych")
        
        with col_summary5:
            realized_pl = sum([cc['pl_pln'] or 0 for cc in filtered_cc if cc['status'] != 'open'])
            if realized_pl >= 0:
                st.metric("💵 P/L Zrealizowany", f"+{realized_pl:.2f} zł", delta_color="normal")
            else:
                st.metric("💵 P/L Zrealizowany", f"{realized_pl:.2f} zł", delta_color="inverse")
            st.caption("Tylko zamknięte CC")
        
        # EKSPORT CSV - PUNKT 57
        st.markdown("---")
        st.markdown("### 📤 Eksport do CSV")
        
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            # Przygotuj dane do eksportu
            csv_cc_data = []
            for cc in filtered_cc:
                pl_pln = cc['pl_pln'] or 0
                
                # Kalkulacja dni
                open_date_obj = datetime.strptime(cc['open_date'], '%Y-%m-%d').date() if isinstance(cc['open_date'], str) else cc['open_date']
                if cc['status'] == 'open':
                    days_held = (date.today() - open_date_obj).days or 1
                else:
                    expiry_date_obj = datetime.strptime(cc['expiry_date'], '%Y-%m-%d').date() if isinstance(cc['expiry_date'], str) else cc['expiry_date']
                    days_held = (expiry_date_obj - open_date_obj).days or 1
                
                # Yield
                strike_value_pln = cc['strike_usd'] * cc['contracts'] * 100 * cc['fx_open']
                yield_percent = (cc['premium_sell_pln'] / strike_value_pln) * 100 if strike_value_pln > 0 else 0
                annualized_yield = yield_percent * (365 / days_held) if days_held > 0 else 0
                
                csv_cc_data.append({
                    'CC_ID': cc['id'],
                    'Ticker': cc['ticker'],
                    'Contracts': cc['contracts'],
                    'Strike_USD': cc['strike_usd'],
                    'Premium_Per_Share_USD': cc['premium_sell_usd'],
                    'Open_Date': cc['open_date'],
                    'Expiry_Date': cc['expiry_date'],
                    'Status': cc['status'],
                    'FX_Rate_Open': cc['fx_open'],
                    'Premium_Total_PLN': cc['premium_sell_pln'],
                    'Buyback_PLN': cc['premium_buyback_pln'] or 0,
                    'PL_PLN': pl_pln,
                    'Days_Held': days_held,
                    'Yield_Percent': round(yield_percent, 2),
                    'Yield_Annualized': round(annualized_yield, 2),
                    'Created_At': cc['created_at']
                })
            
            # Konwersja do CSV
            import io
            df_csv = pd.DataFrame(csv_cc_data)
            csv_buffer = io.StringIO()
            df_csv.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_data = csv_buffer.getvalue()
            
            # Przycisk download
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"covered_calls_history_{timestamp}.csv"
            
            st.download_button(
                label="📥 Pobierz historię CC CSV",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                help=f"Eksport {len(filtered_cc)} pozycji CC",
                use_container_width=True
            )
            
            st.caption(f"📊 Zawiera {len(filtered_cc)} pozycji CC z filtrów")
        
        with col_export2:
            # Podsumowanie dla księgowości
            st.markdown("**📋 Eksport dla księgowości:**")
            
            if st.button("📊 Generuj raport księgowy"):
                # Przygotuj dane tylko zamkniętych CC dla PIT
                closed_cc = [cc for cc in filtered_cc if cc['status'] != 'open']
                
                if closed_cc:
                    accounting_data = []
                    for cc in closed_cc:
                        pl_pln = cc['pl_pln'] or 0
                        
                        accounting_data.append({
                            'Data_Otwarcia': cc['open_date'],
                            'Data_Zamkniecia': cc['expiry_date'] if cc['status'] == 'expired' else 'BUYBACK',
                            'Ticker': cc['ticker'],
                            'Typ_Operacji': 'COVERED_CALL',
                            'Przychod_PLN': cc['premium_sell_pln'],
                            'Koszt_PLN': cc['premium_buyback_pln'] or 0,
                            'Zysk_Strata_PLN': pl_pln,
                            'Kurs_NBP_Otwarcie': cc['fx_open'],
                            'Kurs_NBP_Zamkniecie': cc.get('fx_close', ''),
                            'Status_PIT': 'PRZYCHOD' if pl_pln >= 0 else 'STRATA'
                        })
                    
                    df_accounting = pd.DataFrame(accounting_data)
                    csv_accounting_buffer = io.StringIO()
                    df_accounting.to_csv(csv_accounting_buffer, index=False, encoding='utf-8')
                    csv_accounting_data = csv_accounting_buffer.getvalue()
                    
                    accounting_filename = f"cc_accounting_report_{timestamp}.csv"
                    
                    st.download_button(
                        label="📋 Pobierz raport księgowy",
                        data=csv_accounting_data,
                        file_name=accounting_filename,
                        mime="text/csv",
                        help="Dane dla PIT-38 (tylko zamknięte CC)",
                        use_container_width=True,
                        key="accounting_download"
                    )
                    
                    st.success(f"✅ Wygenerowano raport księgowy: {len(closed_cc)} zamkniętych CC")
                else:
                    st.warning("⚠️ Brak zamkniętych CC do raportu księgowego")
            
            st.caption("🏛️ Raport zawiera tylko zamknięte CC dla PIT-38")
        
    except Exception as e:
        st.error(f"❌ Błąd pobierania historii CC: {e}")
    
    # Status punktu
    st.markdown("---")
    st.success("✅ **PUNKT 57 UKOŃCZONY** - Historia CC z filtrami, yield i eksportem CSV!")
    st.info("🔄 **NASTĘPNY KROK**: PUNKT 58-60 - Finalizacja modułu Options")

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

if __name__ == "__main__":
    show_options()  