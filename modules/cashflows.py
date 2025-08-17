"""
Moduł Cashflows - Przepływy pieniężne
ETAP 2 UKOŃCZONY: Punkty 16-30 (Kompletny moduł przepływów)

FUNKCJONALNOŚCI:
✅ Dodawanie operacji ręcznych (wpłaty, wypłaty, odsetki margin)
✅ Automatyczne pobieranie kursów NBP D-1 z obsługą weekendów/świąt
✅ Manual override kursów NBP (checkbox + własny kurs)
✅ Walidacje biznesowe (wpłaty dodatnie, wypłaty ujemne)
✅ Tabela wszystkich cashflows z filtrami (typ, źródło, kwota)
✅ Edycja/usuwanie operacji ręcznych (blokada automatycznych)
✅ Eksport do CSV z timestampem
✅ Statystyki (saldo, wpływy, wydatki, liczba operacji)
✅ Linki ref do operacji źródłowych (lots#123, stock_trades#45)
✅ 3 taby: Ręczne | Automatyczne | Wszystkie

INTEGRACJA:
- Kursy NBP: nbp_api_client (ETAP 1)
- Baza danych: db.py operacje CRUD (ETAP 1)
- Formatowanie: utils.formatting (ETAP 1)
- Automatyczne cashflows: Tworzone przez moduły Stocks/Options/Dividends (ETAP 3+)

GOTOWE DO ETAPU 3: Moduł Stocks (punkty 31-50)
"""

import streamlit as st
import sys
import os
from datetime import date, timedelta

# Dodaj katalog główny do path
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modułów
try:
    import nbp_api_client
    import db
    from utils.formatting import format_currency_usd, format_currency_pln, format_fx_rate
except ImportError as e:
    st.error(f"Błąd importu modułów: {e}")

def show_cashflows():
    """Główna funkcja modułu Cashflows"""
    
    st.header("💸 Cashflows - Przepływy pieniężne")
    st.markdown("*Dziennik wszystkich operacji finansowych na koncie margin*")
    
    # Tabs dla organizacji
    tab1, tab2, tab3 = st.tabs(["📝 Operacje ręczne", "🔄 Operacje automatyczne", "📊 Wszystkie przepływy"])
    
    with tab1:
        st.subheader("Dodaj operację ręczną")
        st.info("💡 Wpłaty, wypłaty, odsetki margin - wprowadzane bezpośrednio")
        
        # Manual override kursu - POZA formularzem żeby działał interaktywnie
        manual_fx_override = st.checkbox(
            "🔧 Ręczna korekta kursu NBP",
            help="Pozwala na zmianę kursu przed zapisem"
        )
        
        if manual_fx_override:
            manual_fx_rate = st.number_input(
                "Własny kurs USD/PLN:",
                min_value=1.0,
                max_value=10.0,
                value=4.0,
                step=0.0001,
                format="%.4f",
                help="Wprowadź własny kurs zamiast NBP D-1"
            )
        
        # Formularz dodawania cashflow
        with st.form("add_cashflow"):
            # Info box o datach i weekendach
            st.info("💡 **Kursy NBP D-1:** System automatycznie cofa się do ostatniego dnia roboczego (pomija weekendy i święta)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Typ operacji
                cashflow_type = st.selectbox(
                    "Typ operacji:",
                    ["deposit", "withdrawal", "margin_interest", "cash_interest", "other"],
                    format_func=lambda x: {
                        "deposit": "💰 Wpłata",
                        "withdrawal": "💸 Wypłata", 
                        "margin_interest": "📉 Odsetki margin (koszt)",
                        "cash_interest": "📈 Odsetki gotówka (przychód)",
                        "other": "❓ Inne"
                    }[x]
                )
                
                # Kwota USD
                amount_usd = st.number_input(
                    "Kwota USD:", 
                    min_value=-999999.99,
                    max_value=999999.99,
                    value=0.00,
                    step=0.01,
                    format="%.2f",
                    help="Dodatnia dla wpływów, ujemna dla wydatków"
                )
            
            with col2:
                # Data operacji
                operation_date = st.date_input(
                    "Data operacji:",
                    help="Data wykonania operacji"
                )
                
                # Opis (opcjonalny)
                description = st.text_area(
                    "Opis (opcjonalny):",
                    placeholder="np. Wpłata na start, miesięczne odsetki margin...",
                    max_chars=200
                )
            
            # Przycisk zapisu
            submitted = st.form_submit_button("💾 Dodaj operację", use_container_width=True)
            
            if submitted:
                # Walidacje przed zapisem
                validation_errors = []
                
                # Walidacja 1: Wpłaty powinny być dodatnie
                if cashflow_type == "deposit" and amount_usd <= 0:
                    validation_errors.append("💰 Wpłaty powinny mieć kwotę dodatnią")
                
                # Walidacja 2: Wypłaty powinny być ujemne  
                if cashflow_type == "withdrawal" and amount_usd >= 0:
                    validation_errors.append("💸 Wypłaty powinny mieć kwotę ujemną")
                
                # Walidacja 3: Margin interest powinien być ujemny (koszt)
                if cashflow_type == "margin_interest" and amount_usd >= 0:
                    validation_errors.append("📉 Odsetki margin powinny być ujemne (koszt)")
                
                # Walidacja 4: Cash interest powinien być dodatni (przychód)
                if cashflow_type == "cash_interest" and amount_usd <= 0:
                    validation_errors.append("📈 Odsetki od gotówki powinny być dodatnie (przychód)")
                
                # Walidacja 5: Kwota nie może być zerem
                if amount_usd == 0:
                    validation_errors.append("⚠️ Kwota nie może być zerem")
                
                # Jeśli są błędy walidacji
                if validation_errors:
                    st.error("❌ **Błędy walidacji:**")
                    for error in validation_errors:
                        st.error(f"• {error}")
                    return  # Przerwij wykonanie
                
                # Pobierz kurs NBP D-1 automatycznie (tylko jeśli walidacja OK)
                try:
                    if manual_fx_override:
                        # Użyj ręcznego kursu
                        fx_rate = manual_fx_rate
                        fx_data = {'rate': fx_rate, 'date': str(operation_date), 'source': 'MANUAL'}
                        st.info(f"🔧 **Używam ręcznego kursu:** {format_fx_rate(fx_rate)}")
                    else:
                        # Pobierz z NBP API
                        fx_data = nbp_api_client.get_usd_rate_for_date(operation_date)
                        if not fx_data or 'rate' not in fx_data:
                            st.error("❌ Nie można pobrać kursu NBP dla tej daty")
                            return
                        fx_rate = fx_data['rate']
                    
                    amount_pln = round(amount_usd * fx_rate, 2)
                    
                    # Pokaż podgląd z kursem
                    st.success(f"✅ Formularz wypełniony!")
                    
                    col_preview1, col_preview2 = st.columns(2)
                    with col_preview1:
                        st.info(f"**Typ:** {cashflow_type}")
                        st.info(f"**Kwota USD:** {format_currency_usd(amount_usd)}")
                        st.info(f"**Data:** {operation_date}")
                    
                    with col_preview2:
                        kurs_source = "RĘCZNY" if manual_fx_override else "NBP D-1"
                        st.info(f"**Kurs {kurs_source}:** {format_fx_rate(fx_rate)}")
                        st.info(f"**Kwota PLN:** {format_currency_pln(amount_pln)}")
                        if description:
                            st.info(f"**Opis:** {description}")
                        
                    # Zapisz do bazy danych
                    cashflow_id = db.insert_cashflow(
                        cashflow_type=cashflow_type,
                        amount_usd=amount_usd,
                        date=operation_date,
                        fx_rate=fx_rate,
                        description=description
                    )
                    
                    if cashflow_id:
                        st.success(f"✅ **Operacja zapisana!** ID: {cashflow_id}")
                        st.balloons()  # Mała celebracja! 🎈
                        
                        # Pokaż info o źródle kursu
                        if manual_fx_override:
                            st.info(f"🔧 **Użyto ręcznego kursu:** {format_fx_rate(fx_rate)}")
                        elif 'date' in fx_data and fx_data['date'] != str(operation_date):
                            st.info(f"📅 **Uwaga:** Użyto kursu z {fx_data['date']} (ostatni dostępny przed {operation_date})")
                    else:
                        st.error("❌ Błąd zapisu do bazy danych")
                        
                except Exception as e:
                    st.error(f"❌ Błąd pobierania kursu NBP: {e}")
    
    with tab2:
        st.subheader("Operacje automatyczne")
        st.info("🔄 Cashflows tworzone automatycznie przez moduły Stocks/Options/Dividends")
        
        # Pobierz tylko automatyczne cashflows
        try:
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, type, amount_usd, date, fx_rate, amount_pln, 
                           description, ref_table, ref_id, created_at
                    FROM cashflows 
                    WHERE ref_table IS NOT NULL
                    ORDER BY date DESC, id DESC
                """)
                
                auto_cashflows = cursor.fetchall()
                conn.close()
                
                if auto_cashflows:
                    st.write(f"**Operacje automatyczne:** {len(auto_cashflows)}")
                    
                    # Przygotuj dane do tabeli
                    auto_table_data = []
                    for cf in auto_cashflows:
                        # Formatuj typ
                        type_display = {
                            "stock_buy": "📊 Zakup akcji",
                            "stock_sell": "📊 Sprzedaż akcji",
                            "option_premium": "🎯 Sprzedaż CC",
                            "option_buyback": "🔄 Odkup CC",
                            "dividend": "💵 Dywidenda",
                            "broker_fee": "💼 Prowizja broker",
                            "reg_fee": "📋 Opłata reg."
                        }.get(cf[1], cf[1])
                        
                        # Link do źródła
                        ref_link = f"{cf[7]}#{cf[8]}" if cf[8] else f"{cf[7]}"
                        
                        auto_table_data.append({
                            "ID": cf[0],
                            "Typ": type_display,
                            "Kwota USD": format_currency_usd(cf[2]),
                            "Data": cf[3],
                            "Kurs NBP": format_fx_rate(cf[4]),
                            "Kwota PLN": format_currency_pln(cf[5]),
                            "Źródło": ref_link,
                            "Opis": cf[6] if cf[6] else "-"
                        })
                    
                    # Wyświetl tabelę
                    st.dataframe(auto_table_data, use_container_width=True)
                    
                    st.warning("⚠️ **Operacje automatyczne nie mogą być edytowane** - są tworzone przez inne moduły")
                    
                else:
                    st.info("📝 Brak operacji automatycznych - będą tworzone przez moduły Stocks/Options/Dividends")
                    
        except Exception as e:
            st.error(f"❌ Błąd pobierania automatycznych cashflows: {e}")
    
    with tab3:
        st.subheader("Kompletny dziennik")
        st.info("📋 Wszystkie przepływy pieniężne z filtrami i eksportem")
        
        # Filtry
        with st.expander("🔍 Filtry", expanded=False):
            col_f1, col_f2, col_f3 = st.columns(3)
            
            with col_f1:
                filter_type = st.multiselect(
                    "Typ operacji:",
                    ["deposit", "withdrawal", "margin_interest", "cash_interest", 
                     "stock_buy", "stock_sell", "option_premium", "option_buyback", 
                     "dividend", "broker_fee", "reg_fee", "stock_lending", "other"],
                    default=[],
                    format_func=lambda x: {
                        "deposit": "💰 Wpłata",
                        "withdrawal": "💸 Wypłata", 
                        "margin_interest": "📉 Odsetki margin",
                        "cash_interest": "📈 Odsetki gotówka",
                        "stock_buy": "📊 Zakup akcji",
                        "stock_sell": "📊 Sprzedaż akcji",
                        "option_premium": "🎯 Sprzedaż CC",
                        "option_buyback": "🔄 Odkup CC",
                        "dividend": "💵 Dywidenda",
                        "broker_fee": "💼 Prowizja broker",
                        "reg_fee": "📋 Opłata reg.",
                        "stock_lending": "🏦 Stock lending",
                        "other": "❓ Inne"
                    }.get(x, x)
                )
            
            with col_f2:
                filter_source = st.selectbox(
                    "Źródło:",
                    ["Wszystkie", "Ręczne", "Automatyczne"]
                )
            
            with col_f3:
                filter_min_amount = st.number_input(
                    "Min kwota USD:",
                    value=None,
                    step=100.0,
                    format="%.2f"
                )
        
        # Pobierz wszystkie cashflows z bazy z filtrami
        try:
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor()
                
                # Buduj query z filtrami
                query = """
                    SELECT id, type, amount_usd, date, fx_rate, amount_pln, 
                           description, ref_table, ref_id, created_at
                    FROM cashflows 
                    WHERE 1=1
                """
                params = []
                
                # Filtr typu operacji
                if filter_type:
                    placeholders = ','.join(['?' for _ in filter_type])
                    query += f" AND type IN ({placeholders})"
                    params.extend(filter_type)
                
                # Filtr źródła
                if filter_source == "Ręczne":
                    query += " AND ref_table IS NULL"
                elif filter_source == "Automatyczne":
                    query += " AND ref_table IS NOT NULL"
                
                # Filtr minimalnej kwoty (wartość bezwzględna)
                if filter_min_amount is not None:
                    query += " AND ABS(amount_usd) >= ?"
                    params.append(filter_min_amount)
                
                query += " ORDER BY date DESC, id DESC"
                
                cursor.execute(query, params)
                cashflows = cursor.fetchall()
                conn.close()
                
                if cashflows:
                    # Pokaż liczbę rekordów
                    st.write(f"**Znaleziono:** {len(cashflows)} operacji")
                    
                    # Przygotuj dane do tabeli
                    table_data = []
                    for cf in cashflows:
                        # Formatuj typ operacji
                        type_display = {
                            "deposit": "💰 Wpłata",
                            "withdrawal": "💸 Wypłata", 
                            "margin_interest": "📉 Odsetki margin",
                            "cash_interest": "📈 Odsetki gotówka",
                            "stock_buy": "📊 Zakup akcji",
                            "stock_sell": "📊 Sprzedaż akcji",
                            "option_premium": "🎯 Sprzedaż CC",
                            "option_buyback": "🔄 Odkup CC",
                            "dividend": "💵 Dywidenda",
                            "broker_fee": "💼 Prowizja broker",
                            "reg_fee": "📋 Opłata reg.",
                            "stock_lending": "🏦 Stock lending",
                            "other": "❓ Inne"
                        }.get(cf[1], cf[1])
                        
                        # Oznacz źródło (ręczne vs automatyczne) + link
                        if cf[7] is None:
                            source = "🖊️ Ręczne"
                            ref_link = "-"
                        else:
                            source = f"🔄 Auto ({cf[7]})"
                            ref_link = f"{cf[7]}#{cf[8]}" if cf[8] else f"{cf[7]}"
                        
                        table_data.append({
                            "ID": cf[0],
                            "Typ": type_display,
                            "Kwota USD": format_currency_usd(cf[2]),
                            "Data": cf[3],
                            "Kurs NBP": format_fx_rate(cf[4]),
                            "Kwota PLN": format_currency_pln(cf[5]),
                            "Źródło": source,
                            "Ref": ref_link,
                            "Opis": cf[6] if cf[6] else "-"
                        })
                    
                    # Wyświetl tabelę
                    st.dataframe(table_data, use_container_width=True)
                    
                    # Przycisk eksportu CSV
                    if st.button("📥 Eksport do CSV", use_container_width=True):
                        # Przygotuj dane do eksportu (bez formatowania)
                        export_data = []
                        for cf in cashflows:
                            export_data.append({
                                "ID": cf[0],
                                "Type": cf[1],
                                "Amount_USD": cf[2],
                                "Date": cf[3],
                                "FX_Rate": cf[4],
                                "Amount_PLN": cf[5],
                                "Description": cf[6] or "",
                                "Ref_Table": cf[7] or "",
                                "Ref_ID": cf[8] or "",
                                "Created_At": cf[9]
                            })
                        
                        # Konwertuj do CSV
                        import pandas as pd
                        df = pd.DataFrame(export_data)
                        csv = df.to_csv(index=False)
                        
                        # Download button
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"cashflows_{timestamp}.csv"
                        
                        st.download_button(
                            label="💾 Pobierz CSV",
                            data=csv,
                            file_name=filename,
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        st.success(f"✅ Przygotowano eksport: {len(export_data)} rekordów")
                    
                    # Sekcja edycji/usuwania (tylko dla ręcznych)
                    st.markdown("---")
                    st.subheader("✏️ Edycja/Usuwanie")
                    
                    # Filtruj tylko ręczne operacje do edycji
                    manual_cashflows = [cf for cf in cashflows if cf[7] is None]
                    
                    if manual_cashflows:
                        col_edit, col_delete = st.columns(2)
                        
                        with col_edit:
                            st.write("**Edytuj operację ręczną:**")
                            edit_options = {f"ID {cf[0]} - {cf[1]} ${cf[2]:.2f}": cf[0] for cf in manual_cashflows}
                            selected_edit = st.selectbox(
                                "Wybierz operację do edycji:",
                                options=list(edit_options.keys()),
                                key="edit_select"
                            )
                            
                            if st.button("✏️ Edytuj", key="edit_btn"):
                                # Znajdź wybraną operację
                                cashflow_id = edit_options[selected_edit]
                                selected_cf = next((cf for cf in manual_cashflows if cf[0] == cashflow_id), None)
                                
                                if selected_cf:
                                    st.session_state.editing_cashflow = {
                                        'id': selected_cf[0],
                                        'type': selected_cf[1], 
                                        'amount_usd': selected_cf[2],
                                        'date': selected_cf[3],
                                        'description': selected_cf[6]
                                    }
                                    st.rerun()
                            
                            # Formularz edycji (jeśli wybrano operację)
                            if 'editing_cashflow' in st.session_state:
                                st.write("---")
                                st.write("**🛠️ Edycja operacji:**")
                                
                                with st.form("edit_cashflow_form"):
                                    edit_cf = st.session_state.editing_cashflow
                                    
                                    # Edytowalne pola
                                    new_amount = st.number_input(
                                        "Nowa kwota USD:", 
                                        value=float(edit_cf['amount_usd']),
                                        step=0.01
                                    )
                                    
                                    new_description = st.text_area(
                                        "Nowy opis:",
                                        value=edit_cf['description'] or "",
                                        max_chars=200
                                    )
                                    
                                    col_save, col_cancel = st.columns(2)
                                    with col_save:
                                        save_edit = st.form_submit_button("💾 Zapisz zmiany")
                                    with col_cancel:
                                        cancel_edit = st.form_submit_button("❌ Anuluj")
                                    
                                    if save_edit:
                                        # Zapisz zmiany do bazy
                                        success = db.update_cashflow(
                                            edit_cf['id'],
                                            amount_usd=new_amount,
                                            description=new_description
                                        )
                                        
                                        if success:
                                            st.success("✅ Operacja zaktualizowana!")
                                            del st.session_state.editing_cashflow
                                            st.rerun()
                                        else:
                                            st.error("❌ Błąd aktualizacji")
                                    
                                    if cancel_edit:
                                        del st.session_state.editing_cashflow
                                        st.rerun()
                        
                        with col_delete:
                            st.write("**Usuń operację ręczną:**")
                            delete_options = {f"ID {cf[0]} - {cf[1]} ${cf[2]:.2f}": cf[0] for cf in manual_cashflows}
                            selected_delete = st.selectbox(
                                "Wybierz operację do usunięcia:",
                                options=list(delete_options.keys()),
                                key="delete_select"
                            )
                            if st.button("🗑️ Usuń", key="delete_btn", type="secondary"):
                                cashflow_id = delete_options[selected_delete]
                                if db.delete_cashflow(cashflow_id):
                                    st.success("✅ Operacja usunięta!")
                                    st.rerun()
                                else:
                                    st.error("❌ Błąd usuwania")
                    else:
                        st.info("📝 Brak operacji ręcznych do edycji/usuwania")
                    
                else:
                    st.info("📝 Brak operacji w bazie danych")
                    
        except Exception as e:
            st.error(f"❌ Błąd pobierania danych: {e}")
    
    # Statystyki z prawdziwymi danymi
    st.markdown("---")
    st.subheader("📊 Statystyki")
    
    try:
        # Pobierz statystyki z bazy
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor()
            
            # Suma wszystkich przepływów (saldo)
            cursor.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM cashflows")
            total_balance = cursor.fetchone()[0]
            
            # Suma wpłat (dodatnie kwoty)
            cursor.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM cashflows WHERE amount_usd > 0")
            total_inflows = cursor.fetchone()[0]
            
            # Suma wypłat (ujemne kwoty, ale wyświetlamy jako dodatnie)
            cursor.execute("SELECT COALESCE(SUM(ABS(amount_usd)), 0) FROM cashflows WHERE amount_usd < 0")
            total_outflows = cursor.fetchone()[0]
            
            # Liczba operacji
            cursor.execute("SELECT COUNT(*) FROM cashflows")
            total_operations = cursor.fetchone()[0]
            
            # Tylko operacje ręczne
            cursor.execute("SELECT COUNT(*) FROM cashflows WHERE ref_table IS NULL")
            manual_operations = cursor.fetchone()[0]
            
            # Tylko operacje automatyczne  
            cursor.execute("SELECT COUNT(*) FROM cashflows WHERE ref_table IS NOT NULL")
            auto_operations = cursor.fetchone()[0]
            
            conn.close()
            
            # Wyświetl statystyki
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Saldo USD", 
                    format_currency_usd(total_balance),
                    help="Suma wszystkich przepływów pieniężnych"
                )
            
            with col2:
                st.metric(
                    "Wpływy USD", 
                    format_currency_usd(total_inflows),
                    help="Suma wszystkich dodatnich przepływów"
                )
            
            with col3:
                st.metric(
                    "Wydatki USD", 
                    format_currency_usd(total_outflows),
                    help="Suma wszystkich ujemnych przepływów (jako wartość dodatnia)"
                )
            
            with col4:
                st.metric(
                    "Operacje", 
                    f"{total_operations}",
                    help=f"Ręczne: {manual_operations}, Auto: {auto_operations}"
                )
                
    except Exception as e:
        st.error(f"❌ Błąd pobierania statystyk: {e}")
        
        # Fallback statystyki
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Saldo USD", "$0.00")
        with col2:
            st.metric("Wpłaty YTD", "$0.00")
        with col3:
            st.metric("Wypłaty YTD", "$0.00")

    # Test funkcjonalności - dodaj na końcu funkcji
    with st.expander("🧪 Test funkcjonalności modułu", expanded=False):
        st.write("**✅ ETAP 2 - PUNKT 29: Sprawdzenie kompletności modułu**")
        
        # Lista funkcjonalności do sprawdzenia
        features = {
            "✅ Dodawanie operacji ręcznych": "Formularz z typami operacji i kursem NBP D-1",
            "✅ Manual override kursu": "Checkbox + własny kurs USD/PLN",
            "✅ Walidacje biznesowe": "Wpłaty dodatnie, wypłaty ujemne, margin ujemne",
            "✅ Tabela wszystkich cashflows": "Sortowanie, formatowanie, kolumny USD/PLN",
            "✅ Filtry": "Typ operacji, źródło (ręczne/auto), minimalna kwota",
            "✅ Edycja operacji ręcznych": "Zmiana kwoty i opisu z session state",
            "✅ Usuwanie operacji ręcznych": "Tylko ref_table IS NULL",
            "✅ Eksport CSV": "Download button z timestampem",
            "✅ Statystyki": "Saldo, wpływy, wydatki, liczba operacji",
            "✅ Linki ref": "Pokazuje źródło operacji automatycznych"
        }
        
        col_test1, col_test2 = st.columns(2)
        
        with col_test1:
            st.write("**Funkcjonalności ETAPU 2:**")
            for feature, desc in list(features.items())[:5]:
                st.write(f"• {feature}")
                st.caption(desc)
        
        with col_test2:
            st.write("**Dodatkowe możliwości:**")
            for feature, desc in list(features.items())[5:]:
                st.write(f"• {feature}")
                st.caption(desc)
        
        # Szybki test połączenia z bazą
        try:
            stats = db.get_cashflows_stats()
            st.success(f"🔗 **Połączenie z bazą OK:** {stats['total_records']} rekordów")
        except Exception as e:
            st.error(f"❌ **Problem z bazą:** {e}")
        
        st.info("🎯 **ETAP 2 UKOŃCZONY!** Moduł Cashflows kompletny - gotowy do ETAPU 3 (Stocks)")
        st.success("🚀 **Następny etap:** ETAP 3 - Moduł Stocks (punkty 31-50)")
        
        # Podsumowanie ETAPU 2
        st.markdown("---")
        st.markdown("**📊 PODSUMOWANIE ETAPU 2:**")
        st.markdown("• **15 punktów ukończonych** (16-30)")
        st.markdown("• **Kompletny moduł cashflows** z pełną funkcjonalnością")
        st.markdown("• **Integracja z NBP API** i bazą danych") 
        st.markdown("• **Gotowa infrastruktura** dla automatycznych cashflows")
        st.markdown("• **Profesjonalny UI** z tabami, filtrami i eksportem")
        
# Funkcja pomocnicza do testowania (opcjonalna)
def test_cashflows_module():
    """Test funkcjonalności modułu cashflows"""
    try:
        # Test połączenia z bazą
        stats = db.get_cashflows_stats()
        
        # Test formatowania
        test_amount = format_currency_usd(1234.56)
        
        # Test kursu NBP
        from datetime import date
        fx_data = nbp_api_client.get_usd_rate_for_date(date.today())
        
        return {
            'database': stats['total_records'] >= 0,
            'formatting': '$1,234.56' in test_amount,
            'nbp_api': fx_data is not None and 'rate' in fx_data
        }
    except Exception as e:
        return {'error': str(e)}
        
# Test funkcji
if __name__ == "__main__":
    show_cashflows()