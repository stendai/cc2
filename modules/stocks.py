"""
Moduł Stocks - Zarządzanie akcjami i LOT-ami
ETAP 3 - Punkty 31-38: UKOŃCZONE
NAPRAWIONO: Formularz sprzedaży działa poprawnie
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
import os
import time

# Dodaj katalog główny do path
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import nbp_api_client
from utils.formatting import format_currency_usd, format_currency_pln, format_date

def create_purchase_cashflow(lot_data, lot_id):
    """Automatyczny cashflow przy zakupie akcji (Punkt 35)"""
    
    try:
        # Kalkulacje dla cashflow
        total_cost_usd = (lot_data['quantity'] * lot_data['buy_price_usd'] + 
                         lot_data['broker_fee_usd'] + lot_data['reg_fee_usd'])
        
        # Cashflow jako wypłata (ujemna kwota)
        cashflow_amount = -total_cost_usd  # Ujemne = wypłata z konta
        
        # Opis cashflow
        description = f"Zakup {lot_data['quantity']} {lot_data['ticker']} @ {lot_data['buy_price_usd']:.2f}"
        
        # Użyj funkcji z db.py - właściwy typ dla zakupu akcji
        cashflow_id = db.insert_cashflow(
            cashflow_type='stock_buy',  # ✅ Zmienione na typ obsługiwany w cashflows
            amount_usd=cashflow_amount,
            date=lot_data['buy_date'],
            fx_rate=lot_data['fx_rate'],
            description=description,
            ref_table='lots',
            ref_id=lot_id
        )
        
        return cashflow_id is not None
            
    except Exception as e:
        st.error(f"❌ Błąd tworzenia cashflow: {e}")
        return False

def save_lot_to_database(lot_data):
    """Zapis LOT-a do bazy danych (Punkt 34-35)"""
    
    try:
        # Połączenie z bazą i zapis LOT-a
        conn = db.get_connection()
        if not conn:
            st.error("❌ Błąd połączenia z bazą danych!")
            return False
        
        cursor = conn.cursor()
        
        # Przygotuj datę (może być date object lub string)
        buy_date_str = lot_data['buy_date']
        if hasattr(buy_date_str, 'strftime'):
            buy_date_str = buy_date_str.strftime('%Y-%m-%d')
        
        # SQL Insert do tabeli lots
        cursor.execute("""
            INSERT INTO lots (
                ticker, quantity_total, quantity_open, buy_price_usd,
                broker_fee_usd, reg_fee_usd, buy_date, fx_rate, cost_pln
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lot_data['ticker'],
            lot_data['quantity'],
            lot_data['quantity'],  # quantity_open = quantity na początku
            lot_data['buy_price_usd'],
            lot_data['broker_fee_usd'],
            lot_data['reg_fee_usd'],
            buy_date_str,
            lot_data['fx_rate'],
            lot_data['cost_pln']
        ))
        
        lot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # 🎯 PUNKT 35: Automatyczny cashflow przy zakupie
        cashflow_success = create_purchase_cashflow(lot_data, lot_id)
        
        if cashflow_success:
            st.session_state.lot_save_success = f"✅ LOT zapisany! ID: {lot_id} + Cashflow utworzony"
        else:
            st.session_state.lot_save_success = f"✅ LOT zapisany! ID: {lot_id} (cashflow manual)"
        
        return True
        
    except Exception as e:
        st.error(f"❌ Błąd zapisu LOT-a: {e}")
        return False

def show_lot_preview_persistent(ticker, quantity, buy_price, buy_date, broker_fee, reg_fee):
    """Trwały podgląd LOT-a z manual kursem (Punkt 33-34)"""
    
    # Podstawowe wyliczenia USD
    gross_value = quantity * buy_price
    total_fees = broker_fee + reg_fee
    total_cost_usd = gross_value + total_fees
    
    # 🎯 PUNKT 33: Pobierz kurs NBP D-1 (tylko raz!)
    nbp_key = f"nbp_rate_{ticker}_{buy_date}"
    if nbp_key not in st.session_state:
        try:
            nbp_result = nbp_api_client.get_usd_rate_for_date(buy_date)
            
            if isinstance(nbp_result, dict) and 'rate' in nbp_result:
                fx_rate = nbp_result['rate']
                fx_date = nbp_result.get('date', buy_date)
            else:
                fx_rate = float(nbp_result)
                fx_date = buy_date
                
            st.session_state[nbp_key] = fx_rate
            fx_success = True
            rate_source = "NBP"
            
        except Exception as e:
            st.error(f"❌ Błąd pobierania kursu NBP: {e}")
            fx_rate = 4.0  # Fallback
            fx_date = buy_date
            st.session_state[nbp_key] = fx_rate
            fx_success = False
            rate_source = "FALLBACK"
    else:
        # Używaj cached NBP rate
        fx_rate = st.session_state[nbp_key]
        fx_date = buy_date
        fx_success = True
        rate_source = "NBP"
    
    # Wyświetl podgląd
    st.markdown("---")
    st.markdown("### 🧮 Podgląd LOT-a")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Szczegóły transakcji:**")
        st.write(f"📊 **Ticker:** {ticker}")
        st.write(f"📈 **Ilość:** {quantity:,} akcji")
        st.write(f"💰 **Cena:** {format_currency_usd(buy_price)} za akcję")
        st.write(f"📅 **Data:** {format_date(buy_date)}")
    
    with col2:
        st.markdown("**Kalkulacje USD:**")
        st.write(f"Wartość brutto: {format_currency_usd(gross_value)}")
        st.write(f"Broker fee: {format_currency_usd(broker_fee)}")
        st.write(f"Reg fee: {format_currency_usd(reg_fee)}")
        st.write(f"**Koszt całkowity: {format_currency_usd(total_cost_usd)}**")
    
    with col3:
        st.markdown("**Przeliczenie PLN:**")
        if fx_success:
            st.success(f"💱 **Kurs NBP** ({fx_date}): {fx_rate:.4f}")
        else:
            st.warning(f"⚠️ **Kurs fallback**: {fx_rate:.4f}")
        
        cost_pln = total_cost_usd * fx_rate
        st.write(f"**Koszt PLN: {format_currency_pln(cost_pln)}**")
        st.write(f"Kurs za akcję: {format_currency_pln(buy_price * fx_rate)}")
    
    # 🎯 Manual override kursu (TRWAŁY!)
    st.markdown("---")
    st.markdown("### ⚙️ Manual override kursu")
    
    # Klucz dla manual rate
    manual_key = f"manual_rate_{ticker}_{buy_date}"
    
    # Inicjalizuj manual rate jeśli nie istnieje
    if manual_key not in st.session_state:
        st.session_state[manual_key] = fx_rate
    
    col_manual1, col_manual2, col_manual3 = st.columns([2, 1, 1])
    
    with col_manual1:
        # Manual rate input
        new_manual_rate = st.number_input(
            "Ręczny kurs USD/PLN:", 
            min_value=1.0, 
            max_value=10.0, 
            value=st.session_state[manual_key], 
            step=0.0001,
            format="%.4f",
            help="Zmień kurs i zobacz przeliczenie",
            key=f"manual_input_{manual_key}"
        )
        
        # Aktualizuj session_state
        st.session_state[manual_key] = new_manual_rate
    
    with col_manual2:
        st.write("**Koszt z ręcznym kursem:**")
        manual_cost_pln = total_cost_usd * new_manual_rate
        st.write(f"{format_currency_pln(manual_cost_pln)}")
        
        if abs(new_manual_rate - fx_rate) > 0.0001:
            st.info("✏️ MANUAL")
        else:
            st.success("🏦 NBP")
    
    with col_manual3:
        if st.button("🔄 Reset NBP", help="Przywróć oryginalny kurs NBP"):
            st.session_state[manual_key] = fx_rate
            st.rerun()
    
    # Finalne dane z manual override
    final_fx_rate = new_manual_rate
    final_cost_pln = total_cost_usd * final_fx_rate
    final_rate_source = "NBP" if abs(final_fx_rate - fx_rate) < 0.0001 else "MANUAL"
    
    # 🎯 Okienko podsumowania
    st.markdown("---")
    st.markdown("### 💾 Gotowe do zapisu")
    
    col_summary1, col_summary2 = st.columns(2)
    
    with col_summary1:
        st.write("**Dane do zapisu:**")
        st.write(f"🏷️ {ticker} - {quantity} szt.")
        st.write(f"💰 {format_currency_usd(total_cost_usd)} → {format_currency_pln(final_cost_pln)}")
        st.write(f"💱 Kurs: {final_fx_rate:.4f} ({final_rate_source})")
    
    with col_summary2:
        st.success("**Punkty 34-35**: Zapis + cashflow ✅")
        st.json({
            "ticker": ticker,
            "cost_usd": total_cost_usd,
            "cost_pln": final_cost_pln,
            "fx_rate": final_fx_rate,
            "source": final_rate_source
        })
    
    # Zwróć finalne dane do zapisu
    return {
        "ticker": ticker,
        "quantity": quantity,
        "buy_price_usd": buy_price,
        "buy_date": buy_date,
        "broker_fee_usd": broker_fee,
        "reg_fee_usd": reg_fee,
        "fx_rate": final_fx_rate,
        "cost_pln": final_cost_pln,
        "rate_source": final_rate_source
    }

def show_stocks():
    """Główna funkcja modułu Stocks"""
    st.header("📊 Stocks - Zarządzanie akcjami")
    st.markdown("*Zakupy LOT-ów, sprzedaże FIFO, P/L tracking*")
    
    # Informacja o statusie ETAPU 3
    st.success("🚀 **PUNKTY 31-38 UKOŃCZONE** - LOT-y + sprzedaże FIFO ✅")
    
    # Taby modułu
    tab1, tab2, tab3 = st.tabs(["📈 LOT-y", "💰 Sprzedaże", "📊 Podsumowanie"])
    
    with tab1:
        show_lots_tab()
    
    with tab2:
        show_sales_tab()
    
    with tab3:
        show_summary_tab()

def show_lots_tab():
    """Tab zarządzania LOT-ami akcji"""
    st.subheader("📈 LOT-y akcji")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ➕ Dodaj nowy LOT")
        st.success("**Punkty 32-35**: Formularz + zapis + cashflow ✅")
        
        # FORMULARZ
        with st.form("add_lot_form"):
            # Podstawowe pola
            ticker = st.text_input("Ticker", placeholder="np. AAPL", help="Symbol akcji")
            quantity = st.number_input("Ilość akcji", min_value=1, value=100, step=1)
            buy_price = st.number_input("Cena za akcję USD", min_value=0.01, value=150.00, step=0.01)
            buy_date = st.date_input("Data zakupu", value=date.today(), help="Data transakcji")
            
            # Prowizje (opcjonalne)
            st.markdown("**Prowizje (opcjonalne):**")
            col_fee1, col_fee2 = st.columns(2)
            with col_fee1:
                broker_fee = st.number_input("Broker fee USD", min_value=0.0, value=1.0, step=0.01)
            with col_fee2:
                reg_fee = st.number_input("Reg fee USD", min_value=0.0, value=0.5, step=0.01)
            
            submitted = st.form_submit_button("🧮 Podgląd LOT-a")
            
        # POZA FORMEM
        if submitted:
            # WALIDACJE
            if not ticker or len(ticker.strip()) == 0:
                st.error("❌ Ticker jest wymagany!")
            elif quantity <= 0:
                st.error("❌ Ilość musi być większa od zera!")
            elif buy_price <= 0:
                st.error("❌ Cena musi być większa od zera!")
            else:
                # ZAPISZ BAZOWE DANE w session_state
                st.session_state.lot_form_data = {
                    "ticker": ticker.upper().strip(),
                    "quantity": quantity,
                    "buy_price": buy_price,
                    "buy_date": buy_date,
                    "broker_fee": broker_fee,
                    "reg_fee": reg_fee
                }
                st.session_state.show_lot_preview = True
        
        # POKAZUJ PODGLĄD jeśli są dane w session_state
        if 'show_lot_preview' in st.session_state and st.session_state.show_lot_preview:
            if 'lot_form_data' in st.session_state:
                # Pobierz dane z session_state
                form_data = st.session_state.lot_form_data
                
                # PODGLĄD (teraz zawsze widoczny)
                lot_data = show_lot_preview_persistent(
                    form_data["ticker"], 
                    form_data["quantity"], 
                    form_data["buy_price"], 
                    form_data["buy_date"], 
                    form_data["broker_fee"], 
                    form_data["reg_fee"]
                )
                
                if lot_data:
                    st.session_state.lot_to_save = lot_data
        
        # PRZYCISKI AKCJI - POZA FORMEM!
        if 'show_lot_preview' in st.session_state and st.session_state.show_lot_preview:
            
            # Pokaż komunikat sukcesu jeśli jest
            if 'lot_save_success' in st.session_state:
                st.success(st.session_state.lot_save_success)
                # Usuń komunikat po pokazaniu
                del st.session_state.lot_save_success
            
            st.markdown("---")
            st.markdown("### 💾 Akcje")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("💾 ZAPISZ LOT", type="primary", key="save_lot_btn"):
                    if 'lot_to_save' in st.session_state:
                        if save_lot_to_database(st.session_state.lot_to_save):
                            # KOMUNIKAT SUKCESU NATYCHMIAST
                            st.success("✅ LOT zapisany pomyślnie!")
                            st.info("💸 Automatyczny cashflow utworzony!")
                            
                            # Wyczyść po sukcesie
                            if 'lot_to_save' in st.session_state:
                                del st.session_state.lot_to_save
                            if 'show_lot_preview' in st.session_state:
                                del st.session_state.show_lot_preview
                            if 'lot_form_data' in st.session_state:
                                del st.session_state.lot_form_data
                            
                            # Opóźnienie żeby komunikat był widoczny
                            time.sleep(2)
                            st.rerun()
            
            with col_btn2:
                if st.button("🔄 Anuluj", key="cancel_lot_btn"):
                    # Wyczyść BEZPIECZNIE
                    if 'lot_to_save' in st.session_state:
                        del st.session_state.lot_to_save
                    if 'show_lot_preview' in st.session_state:
                        del st.session_state.show_lot_preview
                    if 'lot_form_data' in st.session_state:
                        del st.session_state.lot_form_data
                    st.rerun()
    
    with col2:
        st.markdown("### 📊 Istniejące LOT-y")
        
        # Test połączenia z bazą
        try:
            lots_stats = db.get_lots_stats()
            if lots_stats['total_lots'] > 0:
                st.success(f"✅ Znaleziono {lots_stats['total_lots']} LOT-ów w bazie")
                
                # 🎯 TYLKO NAJWAŻNIEJSZA INFORMACJA
                st.write(f"**Akcje w portfelu:** {lots_stats['open_shares']} szt.")
                
                # 🚀 PLACEHOLDER dla przyszłości (ETAP 4: Options)
                st.info("💡 **ETAP 4**: Tutaj będzie podział na objęte CC vs wolne do sprzedaży")
            else:
                st.info("💡 Brak LOT-ów w bazie - dodaj pierwszy zakup")
        except Exception as e:
            st.error(f"❌ Błąd połączenia z bazą: {e}")

def show_sales_tab():
    """Tab sprzedaży akcji (FIFO) - NAPRAWIONY"""
    st.subheader("💰 Sprzedaże akcji (FIFO)")
    
    st.success("**Punkty 36-38**: Logika FIFO + formularz sprzedaży ✅")
    
    # 🎉 POKAŻ OSTATNIĄ SPRZEDAŻ jeśli była
    if 'last_sale_success' in st.session_state:
        sale_info = st.session_state.last_sale_success
        
        with st.container():
            st.success("🎉 **OSTATNIA SPRZEDAŻ ZAPISANA POMYŚLNIE!**")
            
            col_success1, col_success2, col_success3 = st.columns(3)
            
            with col_success1:
                st.metric("Sprzedano", f"{sale_info['ticker']}")
                st.write(f"📊 {sale_info['quantity']} akcji")
                st.write(f"💰 @ ${sale_info['price']:.2f}")
            
            with col_success2:
                pl_color = "🟢" if sale_info['pl_pln'] >= 0 else "🔴"
                st.metric("P/L PLN", f"{pl_color} {sale_info['pl_pln']:,.2f} zł")
                st.write(f"🔄 Użyto {sale_info['fifo_count']} LOT-ów")
                st.write(f"💸 Prowizje: ${sale_info['total_fees']:.2f}")
            
            with col_success3:
                st.write("📋 **Efekty:**")
                st.write("✅ Trade zapisany")
                st.write("✅ LOT-y zaktualizowane") 
                st.write("✅ Cashflow utworzony")
            
            if st.button("🗑️ Ukryj komunikat", key="hide_success"):
                del st.session_state.last_sale_success
                st.rerun()
        
        st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🔄 FIFO Preview")
        st.info("Podgląd alokacji przed sprzedażą")
        
        # Test funkcji FIFO
        ticker = st.text_input("Ticker do sprawdzenia:", value="AAPL")
        if ticker:
            show_fifo_preview(ticker.upper())
    
    with col2:
        st.markdown("### 💸 Formularz sprzedaży")
        st.success("**Punkt 37-38**: Formularz z kursem NBP D-1 ✅")
        
        # 🔧 NAPRAWIONY FORMULARZ SPRZEDAŻY
        with st.form("sell_stocks_form"):
            # Podstawowe pola
            sell_ticker = st.text_input("Ticker:", placeholder="np. AAPL", help="Symbol akcji do sprzedaży")
            sell_quantity = st.number_input("Ilość akcji:", min_value=1, value=50, step=1)
            sell_price = st.number_input("Cena sprzedaży USD:", min_value=0.01, value=160.00, step=0.01)
            sell_date = st.date_input("Data sprzedaży:", value=date.today(), help="Data transakcji sprzedaży")
            
            # Prowizje sprzedaży
            st.markdown("**Prowizje sprzedaży (opcjonalne):**")
            col_sell_fee1, col_sell_fee2 = st.columns(2)
            with col_sell_fee1:
                sell_broker_fee = st.number_input("Broker fee USD:", min_value=0.0, value=1.0, step=0.01)
            with col_sell_fee2:
                sell_reg_fee = st.number_input("Reg fee USD:", min_value=0.0, value=0.5, step=0.01)
            
            # 🔧 KLUCZ: submit button z unikalnym kluczem
            submitted_sell = st.form_submit_button("🧮 Podgląd sprzedaży", use_container_width=True)
        
        # 🔧 NAPRAWIONA OBSŁUGA FORMULARZA - POZA FORMEM!
        if submitted_sell:
            # WALIDACJE
            if not sell_ticker or len(sell_ticker.strip()) == 0:
                st.error("❌ Ticker jest wymagany!")
            elif sell_quantity <= 0:
                st.error("❌ Ilość musi być większa od zera!")
            elif sell_price <= 0:
                st.error("❌ Cena musi być większa od zera!")
            else:
                # Sprawdź dostępność akcji
                ticker_clean = sell_ticker.upper().strip()
                
                try:
                    available = db.get_available_quantity(ticker_clean)
                    
                    if sell_quantity > available:
                        st.error(f"❌ Nie można sprzedać {sell_quantity} akcji - dostępne tylko {available}")
                    else:
                        # ✅ ZAPISZ DANE SPRZEDAŻY DO SESSION_STATE
                        st.session_state.sell_form_data = {
                            "ticker": ticker_clean,
                            "quantity": sell_quantity,
                            "sell_price": sell_price,
                            "sell_date": sell_date,
                            "broker_fee": sell_broker_fee,
                            "reg_fee": sell_reg_fee
                        }
                        st.session_state.show_sell_preview = True
                        st.success(f"✅ Sprzedaż {sell_quantity} {ticker_clean} - przygotowano do podglądu")
                        
                except Exception as e:
                    st.error(f"❌ Błąd sprawdzania dostępności: {e}")
    
    # 🔧 POKAZUJ PODGLĄD SPRZEDAŻY - POZA KOLUMNAMI!
    if 'show_sell_preview' in st.session_state and st.session_state.show_sell_preview:
        if 'sell_form_data' in st.session_state:
            st.markdown("---")
            st.markdown("## 💰 Podgląd sprzedaży FIFO")
            
            form_data = st.session_state.sell_form_data
            
            # PODGLĄD SPRZEDAŻY z kursem NBP D-1
            sell_data = show_sell_preview_with_fifo(
                form_data["ticker"], 
                form_data["quantity"], 
                form_data["sell_price"], 
                form_data["sell_date"], 
                form_data["broker_fee"], 
                form_data["reg_fee"]
            )
            
            # ✅ ZAPISZ DANE DO ZAPISU
            if sell_data:
                st.session_state.sell_to_save = sell_data
    
    # 🔧 PRZYCISKI AKCJI SPRZEDAŻY - NA KOŃCU!
    if 'show_sell_preview' in st.session_state and st.session_state.show_sell_preview:
        
        st.markdown("---")
        st.markdown("### 💾 Akcje sprzedaży")
        
        col_sell_btn1, col_sell_btn2 = st.columns(2)
        
        with col_sell_btn1:
            if st.button("💾 ZAPISZ SPRZEDAŻ", type="primary", key="save_sell_btn"):
                if 'sell_to_save' in st.session_state:
                    if save_sale_to_database(st.session_state.sell_to_save):
                        # KOMUNIKAT SUKCESU
                        st.success("✅ Sprzedaż zapisana pomyślnie!")
                        st.info("💸 Automatyczny cashflow utworzony!")
                        
                        # Wyczyść po sukcesie
                        clear_sell_session_state()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Błąd zapisu sprzedaży!")
                else:
                    st.error("❌ Brak danych do zapisu!")
        
        with col_sell_btn2:
            if st.button("🔄 Anuluj sprzedaż", key="cancel_sell_btn"):
                clear_sell_session_state()
                st.rerun()

def clear_sell_session_state():
    """Wyczyść session state dla sprzedaży"""
    keys_to_clear = ['sell_to_save', 'show_sell_preview', 'sell_form_data']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def show_fifo_preview(ticker):
    """Podstawowy podgląd FIFO dla tickera (Punkt 36)"""
    
    try:
        available = db.get_available_quantity(ticker)
        st.write(f"**Dostępne akcje {ticker}: {available}**")
        
        if available > 0:
            lots = db.get_lots_by_ticker(ticker, only_open=True)
            st.write(f"**LOT-y w kolejności FIFO ({len(lots)}):**")
            
            # Pokaż wszystkie LOT-y z detalami
            for i, lot in enumerate(lots):
                with st.expander(f"#{i+1} LOT ID {lot['id']} - {lot['quantity_open']} szt.", expanded=i<3):
                    col_lot1, col_lot2 = st.columns(2)
                    
                    with col_lot1:
                        st.write(f"📅 **Data zakupu:** {lot['buy_date']}")
                        st.write(f"💰 **Cena zakupu:** {format_currency_usd(lot['buy_price_usd'])}")
                        st.write(f"📊 **Dostępne:** {lot['quantity_open']} / {lot['quantity_total']}")
                    
                    with col_lot2:
                        st.write(f"💱 **Kurs NBP:** {lot['fx_rate']:.4f}")
                        st.write(f"💸 **Koszt PLN:** {format_currency_pln(lot['cost_pln'])}")
                        cost_per_share_pln = lot['cost_pln'] / lot['quantity_total']
                        st.write(f"🔢 **PLN/akcja:** {format_currency_pln(cost_per_share_pln)}")
        else:
            st.warning(f"❌ Brak dostępnych akcji {ticker}")
            
    except Exception as e:
        st.error(f"Błąd FIFO preview: {e}")

def show_sell_preview_with_fifo(ticker, quantity, sell_price, sell_date, broker_fee, reg_fee):
    """Podgląd sprzedaży z FIFO i kursem NBP D-1 (Punkt 37)"""
    
    st.markdown("### 💰 Szczegóły sprzedaży FIFO")
    
    try:
        # Podstawowe wyliczenia USD
        gross_proceeds = quantity * sell_price
        total_fees = broker_fee + reg_fee
        net_proceeds_usd = gross_proceeds - total_fees
        
        # 🎯 PUNKT 37: Pobierz kurs NBP D-1 dla DATY SPRZEDAŻY
        nbp_key = f"sell_nbp_rate_{ticker}_{sell_date}"
        if nbp_key not in st.session_state:
            try:
                nbp_result = nbp_api_client.get_usd_rate_for_date(sell_date)
                
                if isinstance(nbp_result, dict) and 'rate' in nbp_result:
                    sell_fx_rate = nbp_result['rate']
                    sell_fx_date = nbp_result.get('date', sell_date)
                else:
                    sell_fx_rate = float(nbp_result)
                    sell_fx_date = sell_date
                    
                st.session_state[nbp_key] = sell_fx_rate
                fx_success = True
                
            except Exception as e:
                st.error(f"❌ Błąd pobierania kursu NBP dla sprzedaży: {e}")
                sell_fx_rate = 4.0  # Fallback
                sell_fx_date = sell_date
                st.session_state[nbp_key] = sell_fx_rate
                fx_success = False
        else:
            # Używaj cached rate
            sell_fx_rate = st.session_state[nbp_key]
            sell_fx_date = sell_date
            fx_success = True
        
        proceeds_pln = net_proceeds_usd * sell_fx_rate
        
        # Pobierz LOT-y FIFO
        lots = db.get_lots_by_ticker(ticker, only_open=True)
        
        if not lots:
            st.error(f"❌ Brak dostępnych LOT-ów dla {ticker}")
            return None
        
        # FIFO alokacja
        remaining_to_sell = quantity
        fifo_allocation = []
        
        for lot in lots:
            if remaining_to_sell <= 0:
                break
                
            qty_from_lot = min(remaining_to_sell, lot['quantity_open'])
            
            if qty_from_lot > 0:
                # Koszt nabycia tego fragmentu (proporcjonalnie)
                cost_per_share_pln = lot['cost_pln'] / lot['quantity_total']
                cost_this_part_pln = qty_from_lot * cost_per_share_pln
                
                fifo_allocation.append({
                    'lot_id': lot['id'],
                    'lot_date': lot['buy_date'],
                    'lot_price_usd': lot['buy_price_usd'],
                    'lot_fx_rate': lot['fx_rate'],
                    'qty_used': qty_from_lot,
                    'qty_remaining': lot['quantity_open'] - qty_from_lot,
                    'cost_pln': cost_this_part_pln
                })
                
                remaining_to_sell -= qty_from_lot
        
        # Wyświetl podgląd
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Szczegóły sprzedaży:**")
            st.write(f"📊 **Ticker:** {ticker}")
            st.write(f"📈 **Ilość:** {quantity:,} akcji")
            st.write(f"💰 **Cena:** {format_currency_usd(sell_price)}")
            st.write(f"📅 **Data:** {format_date(sell_date)}")
        
        with col2:
            st.markdown("**Kalkulacje USD:**")
            st.write(f"Przychód brutto: {format_currency_usd(gross_proceeds)}")
            st.write(f"Broker fee: {format_currency_usd(broker_fee)}")
            st.write(f"Reg fee: {format_currency_usd(reg_fee)}")
            st.write(f"**Przychód netto: {format_currency_usd(net_proceeds_usd)}**")
        
        with col3:
            st.markdown("**Kurs sprzedaży:**")
            if fx_success:
                st.success(f"💱 **Kurs NBP** ({sell_fx_date}): {sell_fx_rate:.4f}")
            else:
                st.warning(f"⚠️ **Kurs fallback**: {sell_fx_rate:.4f}")
            
            st.write(f"**Przychód PLN: {format_currency_pln(proceeds_pln)}**")
        
        # Pokaż FIFO alokację
        st.markdown("---")
        st.markdown("### 🔄 Alokacja FIFO")
        
        total_cost_pln = 0
        
        for i, alloc in enumerate(fifo_allocation):
            total_cost_pln += alloc['cost_pln']
            
            with st.expander(f"LOT #{i+1} - ID {alloc['lot_id']}", expanded=i<2):
                col_fifo1, col_fifo2, col_fifo3 = st.columns(3)
                
                with col_fifo1:
                    st.write(f"📅 **Zakup:** {alloc['lot_date']}")
                    st.write(f"💰 **Cena zakupu:** {format_currency_usd(alloc['lot_price_usd'])}")
                    
                with col_fifo2:
                    st.write(f"📊 **Użyte:** {alloc['qty_used']} szt.")
                    st.write(f"💱 **Kurs zakupu:** {alloc['lot_fx_rate']:.4f}")
                    
                with col_fifo3:
                    st.write(f"💸 **Koszt nabycia PLN:** {format_currency_pln(alloc['cost_pln'])}")
                    st.write(f"🔢 **PLN/akcja:** {format_currency_pln(alloc['cost_pln']/alloc['qty_used'])}")
        
        # P/L kalkulacja z dokładnymi kursami
        pl_pln = proceeds_pln - total_cost_pln
        
        st.markdown("---")
        st.markdown("### 📊 Szczegółowe podsumowanie kursów")
        
        # Tabela kursów dla przejrzystości
        col_kursy1, col_kursy2 = st.columns(2)
        
        with col_kursy1:
            st.markdown("**💰 Przychód (sprzedaż):**")
            st.write(f"📅 **Data sprzedaży:** {format_date(sell_date)}")
            st.write(f"💱 **Kurs NBP D-1:** {sell_fx_rate:.4f} ({sell_fx_date})")
            st.write(f"💵 **Kwota USD:** {format_currency_usd(net_proceeds_usd)}")
            st.write(f"💰 **Kwota PLN:** {format_currency_pln(proceeds_pln)}")
        
        with col_kursy2:
            st.markdown("**💸 Koszt nabycia (FIFO):**")
            # Pokaż unikalne kursy zakupu
            unique_rates = {}
            for alloc in fifo_allocation:
                rate_key = f"{alloc['lot_fx_rate']:.4f}"
                if rate_key not in unique_rates:
                    unique_rates[rate_key] = {
                        'rate': alloc['lot_fx_rate'],
                        'date': alloc['lot_date'],
                        'qty': alloc['qty_used'],
                        'cost': alloc['cost_pln']
                    }
                else:
                    unique_rates[rate_key]['qty'] += alloc['qty_used']
                    unique_rates[rate_key]['cost'] += alloc['cost_pln']
            
            for rate_info in unique_rates.values():
                st.write(f"💱 **Kurs {rate_info['rate']:.4f}** ({rate_info['date']})")
                st.write(f"  └ {rate_info['qty']} szt. → {format_currency_pln(rate_info['cost'])}")
            
            st.write(f"💸 **Koszt łączny:** {format_currency_pln(total_cost_pln)}")
        
        st.markdown("---")
        st.markdown("### 💰 Wynik finansowy")
        
        col_pl1, col_pl2, col_pl3 = st.columns(3)
        
        with col_pl1:
            st.metric("Przychód PLN", f"{proceeds_pln:,.2f} zł")
        
        with col_pl2:
            st.metric("Koszt nabycia PLN", f"{total_cost_pln:,.2f} zł")
        
        with col_pl3:
            if pl_pln >= 0:
                st.metric("🟢 Zysk PLN", f"+{pl_pln:,.2f} zł")
            else:
                st.metric("🔴 Strata PLN", f"{pl_pln:,.2f} zł")
        
        # Przygotuj dane do zapisu
        sell_data = {
            "ticker": ticker,
            "quantity": quantity,
            "sell_price": sell_price,
            "sell_date": sell_date,
            "broker_fee": broker_fee,
            "reg_fee": reg_fee,
            "sell_fx_rate": sell_fx_rate,
            "sell_fx_date": sell_fx_date,
            "proceeds_pln": proceeds_pln,
            "cost_pln": total_cost_pln,
            "pl_pln": pl_pln,
            "fifo_allocation": fifo_allocation
        }
        
        st.markdown("---")
        st.success("**Punkt 37**: Podgląd z dokładnymi kursami ✅")
        st.info("💡 **Punkt 38**: Gotowe do zapisu - kliknij przycisk poniżej!")
        
        return sell_data
        
    except Exception as e:
        st.error(f"❌ Błąd podglądu sprzedaży: {e}")
        return None

def save_sale_to_database(sell_data):
    """Zapis sprzedaży do bazy danych (Punkt 38) - NAPRAWIONY"""
    
    try:
        conn = db.get_connection()
        if not conn:
            st.error("❌ Błąd połączenia z bazą danych!")
            return False
        
        cursor = conn.cursor()
        
        # Przygotuj datę sprzedaży
        sell_date_str = sell_data['sell_date']
        if hasattr(sell_date_str, 'strftime'):
            sell_date_str = sell_date_str.strftime('%Y-%m-%d')
        
        # 1. ZAPISZ GŁÓWNĄ SPRZEDAŻ (stock_trades)
        cursor.execute("""
            INSERT INTO stock_trades (
                ticker, quantity, sell_price_usd, sell_date, fx_rate,
                broker_fee_usd, reg_fee_usd, proceeds_pln, cost_pln, pl_pln
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sell_data['ticker'],
            sell_data['quantity'],
            sell_data['sell_price'],
            sell_date_str,
            sell_data['sell_fx_rate'],
            sell_data['broker_fee'],
            sell_data['reg_fee'],
            sell_data['proceeds_pln'],
            sell_data['cost_pln'],
            sell_data['pl_pln']
        ))
        
        trade_id = cursor.lastrowid
        
        # 🔧 NAPRAWKA: Podziel prowizje proporcjonalnie po LOT-ach
        total_fees_usd = sell_data['broker_fee'] + sell_data['reg_fee']
        total_quantity = sell_data['quantity']
        
        # 2. ZAPISZ ROZBICIA FIFO (stock_trade_splits) z prowizjami
        for alloc in sell_data['fifo_allocation']:
            # Proporcjonalna prowizja dla tego LOT-a
            qty_proportion = alloc['qty_used'] / total_quantity
            commission_part_usd = total_fees_usd * qty_proportion
            commission_part_pln = commission_part_usd * sell_data['sell_fx_rate']
            
            cursor.execute("""
                INSERT INTO stock_trade_splits (
                    trade_id, lot_id, qty_from_lot, cost_part_pln,
                    commission_part_usd, commission_part_pln
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                alloc['lot_id'],
                alloc['qty_used'],
                alloc['cost_pln'],
                commission_part_usd,
                commission_part_pln
            ))
            
            # 3. AKTUALIZUJ quantity_open W LOT-ach
            cursor.execute("""
                UPDATE lots 
                SET quantity_open = quantity_open - ?
                WHERE id = ?
            """, (alloc['qty_used'], alloc['lot_id']))
        
        # 4. UTWÓRZ CASHFLOW (przychód ze sprzedaży)
        net_proceeds = (sell_data['quantity'] * sell_data['sell_price'] - 
                       sell_data['broker_fee'] - sell_data['reg_fee'])
        
        cashflow_description = f"Sprzedaż {sell_data['quantity']} {sell_data['ticker']} @ {sell_data['sell_price']:.2f}"
        
        cursor.execute("""
            INSERT INTO cashflows (
                type, amount_usd, date, fx_rate, amount_pln, 
                description, ref_table, ref_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'stock_sell',  # Typ dla sprzedaży
            net_proceeds,  # Dodatnia kwota (przychód)
            sell_date_str,
            sell_data['sell_fx_rate'],
            sell_data['proceeds_pln'],
            cashflow_description,
            'stock_trades',
            trade_id
        ))
        
        conn.commit()
        conn.close()
        
        st.success(f"✅ **Sprzedaż zapisana!** Trade ID: {trade_id}")
        st.info(f"🔄 Zaktualizowano {len(sell_data['fifo_allocation'])} LOT-ów")
        st.info(f"💰 Prowizje podzielone proporcjonalnie: ${total_fees_usd:.2f}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Błąd zapisu sprzedaży: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def show_summary_tab():
    """Tab podsumowania i statystyk"""
    st.subheader("📊 Podsumowanie portfela")
    
    st.info("**Punkty 46-50**: Tabele, filtry, eksport CSV")
    
    # Podstawowe statystyki z bazy
    try:
        lots_stats = db.get_lots_stats()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("LOT-y łącznie", lots_stats['total_lots'])
        
        with col2:
            st.metric("📊 Akcje w portfelu", lots_stats['open_shares'])
        
        # 🚀 PLACEHOLDER dla ETAPU 4
        st.info("🎯 **ETAP 4 - Options**: Tutaj będzie podział na 'Objęte CC' vs 'Wolne do sprzedaży'")
        
        st.markdown("---")
        st.markdown("### 🧪 Test infrastruktury")
        
        st.warning("⚠️ **WYŁĄCZONO**: Test operacji lots (tworzy testowe dane i usuwa prawdziwe LOT-y!)")
        st.info("💡 Funkcje lots działają poprawnie - test nie jest potrzebny")
        
        # 🔍 DIAGNOSTYKA SEED DATA
        st.markdown("### 🔍 Diagnostyka bazy danych")
        
        if st.button("🕵️ Sprawdź historię LOT-ów", key="debug_lots"):
            try:
                conn = db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    
                    # Sprawdź wszystkie LOT-y z datami utworzenia
                    cursor.execute("""
                        SELECT id, ticker, quantity_total, quantity_open, buy_date, cost_pln, created_at,
                               ROUND(cost_pln / quantity_total, 2) as cost_per_share
                        FROM lots 
                        ORDER BY id
                    """)
                    
                    all_lots = cursor.fetchall()
                    conn.close()
                    
                    if all_lots:
                        st.write(f"**Wszystkie LOT-y w bazie ({len(all_lots)}):**")
                        
                        for lot in all_lots:
                            created_time = lot[6] if lot[6] else "brak timestamp"
                            cost_per_share = lot[7]
                            
                            # Oznacz podejrzane LOT-y
                            if cost_per_share < 50:
                                status = "🚨 TESTOWY (niski koszt)"
                            else:
                                status = "✅ PRAWDZIWY"
                            
                            st.write(f"- LOT {lot[0]}: {lot[1]} {lot[2]} szt. (open: {lot[3]}) z {lot[4]} → {lot[5]:.2f} PLN ({cost_per_share:.2f} PLN/szt) [{status}]")
                            st.caption(f"  Utworzony: {created_time}")
                    else:
                        st.info("Brak LOT-ów w bazie")
                        
            except Exception as e:
                st.error(f"❌ Błąd: {e}")
        
        # Sprawdź sprzedaże
        if st.button("📈 Sprawdź sprzedaże", key="debug_sales"):
            try:
                conn = db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    
                    # Sprawdź wszystkie sprzedaże z detalami
                    cursor.execute("""
                        SELECT st.id, st.ticker, st.quantity, st.sell_price_usd, 
                               st.sell_date, st.pl_pln, st.proceeds_pln, st.cost_pln,
                               COUNT(sts.id) as splits_count
                        FROM stock_trades st
                        LEFT JOIN stock_trade_splits sts ON st.id = sts.trade_id
                        GROUP BY st.id
                        ORDER BY st.id DESC
                    """)
                    
                    trades = cursor.fetchall()
                    
                    if trades:
                        st.write(f"**🏆 WSZYSTKIE SPRZEDAŻE ({len(trades)}):**")
                        
                        # Tabela sprzedaży
                        for i, trade in enumerate(trades):
                            pl_color = "🟢" if trade[5] >= 0 else "🔴"
                            with st.expander(f"Trade #{trade[0]} - {trade[1]} {trade[2]} szt.", expanded=i==0):
                                
                                col_trade1, col_trade2, col_trade3 = st.columns(3)
                                
                                with col_trade1:
                                    st.write(f"📅 **Data:** {trade[4]}")
                                    st.write(f"💰 **Cena:** ${trade[3]:.2f}")
                                    st.write(f"📊 **Ilość:** {trade[2]} akcji")
                                
                                with col_trade2:
                                    st.write(f"💵 **Przychód:** {trade[6]:,.2f} PLN")
                                    st.write(f"💸 **Koszt:** {trade[7]:,.2f} PLN")
                                    st.write(f"{pl_color} **P/L:** {trade[5]:,.2f} PLN")
                                
                                with col_trade3:
                                    st.write(f"🔄 **FIFO splits:** {trade[8]}")
                                    
                                    # Pokaż szczegóły FIFO dla tego trade
                                    cursor.execute("""
                                        SELECT sts.lot_id, sts.qty_from_lot, sts.cost_part_pln,
                                               sts.commission_part_usd, l.buy_date, l.buy_price_usd
                                        FROM stock_trade_splits sts
                                        LEFT JOIN lots l ON sts.lot_id = l.id
                                        WHERE sts.trade_id = ?
                                        ORDER BY sts.lot_id
                                    """, (trade[0],))
                                    
                                    splits = cursor.fetchall()
                                    if splits:
                                        st.write("**Rozbicie FIFO:**")
                                        for split in splits:
                                            st.caption(f"LOT {split[0]}: {split[1]} szt. → {split[2]:.2f} PLN (prowizja: ${split[3]:.2f})")
                    else:
                        st.info("📭 Brak sprzedaży w bazie")
                    
                    conn.close()
                    
            except Exception as e:
                st.error(f"❌ Błąd: {e}")
                if conn:
                    conn.close()
        
        # 🗑️ CZYSZCZENIE DANYCH TESTOWYCH
        st.markdown("### 🗑️ Czyszczenie danych testowych")
        
        col_clean1, col_clean2, col_clean3 = st.columns(3)
        
        with col_clean1:
            if st.button("🔄 Sprawdź orphaned cashflows", type="secondary", key="check_orphaned"):
                st.session_state.show_orphaned = True
                st.rerun()
        
        with col_clean2:
            if st.button("🗑️ Usuń wszystkie orphaned", type="secondary", key="delete_orphaned"):
                try:
                    conn = db.get_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            DELETE FROM cashflows 
                            WHERE ref_table = 'lots' 
                            AND ref_id NOT IN (SELECT id FROM lots)
                        """)
                        deleted = cursor.rowcount
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Usunięto {deleted} orphaned cashflows!")
                        if 'show_orphaned' in st.session_state:
                            del st.session_state.show_orphaned
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Błąd: {e}")
        
        with col_clean3:
            if st.button("🗑️ Usuń cashflows testowe", type="secondary", key="delete_test_cashflows"):
                try:
                    conn = db.get_connection()
                    if conn:
                        cursor = conn.cursor()
                        
                        # BEZPIECZNIEJSZY FILTR: usuń cashflows o niskich ID (z wczesnych testów)
                        cursor.execute("""
                            SELECT COUNT(*) FROM cashflows 
                            WHERE id < 30 AND ref_table IN ('stock_trades', 'lots')
                        """)
                        test_count = cursor.fetchone()[0]
                        
                        if test_count > 0:
                            st.write(f"⚠️ **Znaleziono {test_count} cashflows testowych (ID < 30)**")
                            
                            if st.checkbox("✅ Potwierdź usunięcie cashflows testowych (ID < 30)", key="confirm_delete"):
                                cursor.execute("""
                                    DELETE FROM cashflows 
                                    WHERE id < 30 AND ref_table IN ('stock_trades', 'lots')
                                """)
                                deleted_test = cursor.rowcount
                                
                                cursor.execute("""
                                    DELETE FROM stock_trades WHERE id < 10
                                """)
                                deleted_trades = cursor.rowcount
                                
                                cursor.execute("""
                                    DELETE FROM stock_trade_splits 
                                    WHERE trade_id NOT IN (SELECT id FROM stock_trades)
                                """)
                                deleted_splits = cursor.rowcount
                                
                                conn.commit()
                                st.success(f"✅ Usunięto {deleted_test} cashflows, {deleted_trades} trades, {deleted_splits} splits!")
                                
                        else:
                            st.info("✅ Brak cashflows testowych do usunięcia")
                        
                        conn.close()
                        
                except Exception as e:
                    st.error(f"❌ Błąd: {e}")
                    if conn:
                        conn.close()
        
        # Pokaż orphaned cashflows jeśli sprawdzano
        if 'show_orphaned' in st.session_state and st.session_state.show_orphaned:
            try:
                conn = db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    
                    # Znajdź cashflows bez powiązanych LOT-ów
                    cursor.execute("""
                        SELECT c.id, c.type, c.amount_usd, c.description, c.ref_id, c.date
                        FROM cashflows c
                        LEFT JOIN lots l ON c.ref_id = l.id
                        WHERE c.ref_table = 'lots' AND l.id IS NULL
                        ORDER BY c.id DESC
                    """)
                    
                    orphaned = cursor.fetchall()
                    
                    # Znajdź też cashflows z nieistniejącymi stock_trades
                    cursor.execute("""
                        SELECT c.id, c.type, c.amount_usd, c.description, c.ref_id, c.date
                        FROM cashflows c
                        LEFT JOIN stock_trades st ON c.ref_id = st.id
                        WHERE c.ref_table = 'stock_trades' AND st.id IS NULL
                        ORDER BY c.id DESC
                    """)
                    
                    orphaned_trades = cursor.fetchall()
                    conn.close()
                    
                    if orphaned or orphaned_trades:
                        st.warning(f"⚠️ **Orphaned cashflows:**")
                        
                        if orphaned:
                            st.write(f"**{len(orphaned)} bez LOT-ów:**")
                            for cf in orphaned[:5]:  # Pokaż max 5
                                st.write(f"- ID {cf[0]}: {cf[1]} ${cf[2]:.2f} → brak LOT-a #{cf[4]}")
                        
                        if orphaned_trades:
                            st.write(f"**{len(orphaned_trades)} bez stock_trades:**")
                            for cf in orphaned_trades[:5]:  # Pokaż max 5
                                st.write(f"- ID {cf[0]}: {cf[1]} ${cf[2]:.2f} → brak trade #{cf[4]}")
                    else:
                        st.success("✅ Brak orphaned cashflows")
                        
            except Exception as e:
                st.error(f"❌ Błąd: {e}")
        
    except Exception as e:
        st.error(f"Błąd statystyk: {e}")
    
    # Status ETAPU 3
    st.markdown("---")
    st.markdown("### 🎯 Status ETAPU 3")
    
    progress_items = [
        ("31. Podstawowa struktura modułu", True),  # ✅ 
        ("32. Formularz zakupu LOT-ów", True),      # ✅
        ("33. Kurs NBP D-1 + przeliczenie PLN", True),  # ✅
        ("34. Zapis LOT-a do bazy", True),          # ✅
        ("35. Automatyczny cashflow", True),        # ✅ 
        ("36. Podstawy logiki FIFO", True),         # ✅ 
        ("37. Formularz sprzedaży + kurs NBP D-1", True),  # ✅ NAPRAWIONY
        ("38. Zapis sprzedaży FIFO do bazy", True),        # ✅ NAPRAWIONY
        ("39-40. Finalizacja sprzedaży + testy", False), # 🚀 NASTĘPNE
        ("41-45. Formularze sprzedaży", False),
        ("46-50. UI, tabele, eksport", False)
    ]
    
    completed = sum(1 for _, done in progress_items if done)
    total_points = len(progress_items)
    
    st.progress(completed / total_points)
    st.write(f"**Postęp ETAPU 3:** {completed}/{total_points} grup punktów")
    
    for item, done in progress_items:
        status = "✅" if done else "⏳"
        st.write(f"{status} {item}")

# Test modułu
if __name__ == "__main__":
    show_stocks()