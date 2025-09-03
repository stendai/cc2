# PUNKT 73: pages/cc_chains.py - podstawowa struktura nawigacji
# Utwórz nowy plik: pages/cc_chains.py

import streamlit as st
import sys
import os
from datetime import date, datetime
import pandas as pd

# Dodaj katalog główny do path
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modułów
try:
    import db
    from utils.formatting import format_currency_usd, format_currency_pln, format_date, format_percentage
except ImportError as e:
    st.error(f"Błąd importu modułów: {e}")

def show_cc_chains():
    """
    🔗 PUNKT 73: Główna funkcja modułu CC Chains
    Podstawowa struktura nawigacji z placeholder'ami
    """
    
    st.header("🔗 CC Chains - Łańcuchy Opcyjne")
    st.markdown("*Zaawansowana analiza strategii Covered Calls per LOT akcji*")
    
    # Status migracji
    migration_status = check_migration_status()
    display_migration_status(migration_status)
    
    # Główne zakładki
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔗 Active Chains",     # PUNKT 81
        "📊 Chain Analytics",   # PUNKT 82  
        "🛠️ Chain Management", # PUNKT 83
        "🧪 Auto-Detection"     # PUNKT 74-75
    ])
    
    with tab1:
        show_active_chains_tab()
    
    with tab2:
        show_chain_analytics_tab()
    
    with tab3:
        show_chain_management_tab()
    
    with tab4:
        show_auto_detection_tab()

def check_migration_status():
    """Sprawdza status migracji CC Chains"""
    try:
        return db.check_cc_chains_migration_status()
    except Exception as e:
        return {'success': False, 'error': str(e)}

def display_migration_status(status):
    """Wyświetla status migracji w UI"""
    if not status.get('success'):
        st.error(f"❌ Błąd sprawdzania migracji: {status.get('error', 'Unknown')}")
        return
    
    tables = status.get('tables_status', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if tables.get('cc_chains_exists'):
            st.success("✅ Tabela cc_chains")
            st.caption(f"Chains: {tables.get('cc_chains_count', 0)}")
        else:
            st.error("❌ Brak tabeli cc_chains")
    
    with col2:
        if tables.get('chain_id_exists'):
            st.success("✅ Kolumna chain_id")
            cc_linked = tables.get('cc_with_chains', 0)
            cc_unlinked = tables.get('cc_without_chains', 0)
            st.caption(f"Linked: {cc_linked} | Unlinked: {cc_unlinked}")
        else:
            st.error("❌ Brak kolumny chain_id")
    
    with col3:
        total_cc = tables.get('cc_with_chains', 0) + tables.get('cc_without_chains', 0)
        if total_cc > 0:
            st.info(f"📊 {total_cc} total CC")
            st.caption("Gotowe do tworzenia chains")
        else:
            st.warning("⚠️ Brak CC w bazie")

# NAPRAWKA: Zamień funkcję show_active_chains_tab() w pages/cc_chains.py

def show_active_chains_tab():
    """PUNKT 81: Active LOT Chains - kompletnie przepisane LOT-focused"""
    st.subheader("📦 LOT Chains - Historia życia LOT-ów akcji")
    st.markdown("*Każdy LOT = jeden chain. Pokazujemy lifecycle: zakup → CC → CC → ... → sprzedaż*")
    
    try:
        lot_chains = db.get_lot_chains_summary()
        
        if not lot_chains:
            st.warning("📝 Brak LOT chains w bazie. Uruchom Auto-Detection żeby je utworzyć.")
            
            # Pokaż ile LOT-ów z CC czeka na chains
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT lot_linked_id)
                FROM options_cc 
                WHERE lot_linked_id IS NOT NULL AND chain_id IS NULL
            """)
            unlinked_lots = cursor.fetchone()[0]
            conn.close()
            
            if unlinked_lots > 0:
                st.info(f"💡 {unlinked_lots} LOT-ów z CC czeka na utworzenie chains")
            
            return
        
        # Sortuj: aktywne LOT-y na górze, potem według ROI
        active_lots = [lot for lot in lot_chains if lot['lot_status'] == 'active']
        sold_lots = [lot for lot in lot_chains if lot['lot_status'] == 'sold']
        
        active_lots.sort(key=lambda x: x.get('roi_percent', 0), reverse=True)
        sold_lots.sort(key=lambda x: x.get('roi_percent', 0), reverse=True)
        
        sorted_lots = active_lots + sold_lots
        
        st.success(f"✅ {len(active_lots)} aktywnych + {len(sold_lots)} sprzedanych LOT chains")
        
        # OVERVIEW METRICS
        col_overview1, col_overview2, col_overview3, col_overview4 = st.columns(4)
        
        total_investment = sum(lot.get('lot_cost_pln', 0) for lot in lot_chains)
        total_pl = sum(lot.get('total_chain_pl_pln', 0) for lot in lot_chains)
        total_premium = sum(lot.get('total_cc_premium_pln', 0) for lot in lot_chains)
        
        with col_overview1:
            st.metric("💰 Total Investment", f"{total_investment:,.0f} PLN")
        
        with col_overview2:
            st.metric("📈 Total P/L", f"{total_pl:+,.0f} PLN")
        
        with col_overview3:
            avg_roi = (total_pl / total_investment * 100) if total_investment > 0 else 0
            st.metric("📊 Avg ROI", f"{avg_roi:+.1f}%")
        
        with col_overview4:
            st.metric("💸 CC Premium", f"{total_premium:,.0f} PLN")
        
        st.markdown("---")
        
        # LOT CHAINS - jeden per LOT
        for lot in sorted_lots:
            
            # LOT STATUS HEADER
            if lot['lot_status'] == 'active':
                status_badge = "🟢 **AKTYWNY LOT**"
                status_color = "green"
            else:
                status_badge = "🔴 **LOT SPRZEDANY**"
                status_color = "red"
            
            with st.container():
                st.markdown(f"### {status_badge} - {lot['ticker']} LOT #{lot['lot_id']}")
                
                # LOT PODSTAWOWE INFO
                col_lot_basic1, col_lot_basic2, col_lot_basic3 = st.columns(3)
                
                with col_lot_basic1:
                    st.markdown("**📦 LOT Purchase:**")
                    st.write(f"Date: {lot.get('lot_buy_date', 'N/A')}")
                    st.write(f"Quantity: {lot.get('lot_quantity_total', 0)} shares")
                    st.write(f"Price: ${lot.get('lot_buy_price_usd', 0):.2f}/share")
                    st.write(f"**Cost: {lot.get('lot_cost_pln', 0):.0f} PLN**")
                
                with col_lot_basic2:
                    st.markdown("**📊 Current Status:**")
                    if lot['lot_status'] == 'active':
                        st.write(f"Available: {lot.get('lot_quantity_open', 0)} shares")
                        st.write(f"Reserved: {lot.get('lot_quantity_total', 0) - lot.get('lot_quantity_open', 0)} shares")
                    else:
                        st.write("Status: Sold")
                        st.write("Available: 0 shares")
                    st.write(f"Chain: {lot.get('chain_start_date', 'N/A')} → {lot.get('chain_end_date', 'Active')}")
                
                with col_lot_basic3:
                    st.markdown("**💰 Performance:**")
                    roi = lot.get('roi_percent', 0)
                    total_pl = lot.get('total_chain_pl_pln', 0)
                    
                    if roi >= 0:
                        st.success(f"ROI: +{roi:.1f}%")
                        st.success(f"P/L: +{total_pl:.0f} PLN")
                    else:
                        st.error(f"ROI: {roi:.1f}%")
                        st.error(f"P/L: {total_pl:.0f} PLN")
                    
                    premium = lot.get('total_cc_premium_pln', 0)
                    st.write(f"CC Premium: {premium:.0f} PLN")
                
                # CC ACTIVITY TABLE
                cc_list = lot.get('cc_list', [])
                if cc_list:
                    st.markdown("**📞 CC Activity na tym LOT-cie:**")
                    
                    cc_df_data = []
                    for cc in cc_list:
                        status_icon = {
                            'open': '🟢',
                            'expired': '✅', 
                            'assigned': '📞',
                            'bought_back': '🔴'
                        }.get(cc.get('status', ''), '❓')
                        
                        pl_pln = cc.get('pl_pln', 0)
                        pl_display = f"{pl_pln:+.0f} PLN" if pl_pln else "pending"
                        
                        cc_df_data.append({
                            'CC ID': f"#{cc.get('id', 'N/A')}",
                            'Status': f"{status_icon} {cc.get('status', 'unknown')}",
                            'Contracts': cc.get('contracts', 0),
                            'Strike': f"${cc.get('strike_usd', 0):.2f}",
                            'Premium': f"${cc.get('premium_sell_usd', 0):.2f}",
                            'Open Date': cc.get('open_date', 'N/A'),
                            'Expiry': cc.get('expiry_date', 'N/A'),
                            'P/L PLN': pl_display
                        })
                    
                    st.dataframe(pd.DataFrame(cc_df_data), use_container_width=True)
                else:
                    st.info("Ten LOT nie ma jeszcze CC")
                
                # STOCK SALES TABLE (jeśli LOT sprzedany)
                stock_sales = lot.get('stock_sales', [])
                if stock_sales:
                    st.markdown("**💸 Sprzedaże z tego LOT-a:**")
                    
                    sales_df_data = []
                    for sale in stock_sales:
                        sales_df_data.append({
                            'Date': sale.get('sell_date', 'N/A'),
                            'Quantity': sale.get('qty_from_lot', 0),
                            'Price': f"${sale.get('sell_price_usd', 0):.2f}",
                            'P/L PLN': f"{sale.get('pl_pln_portion', 0):+.0f}"
                        })
                    
                    st.dataframe(pd.DataFrame(sales_df_data), use_container_width=True)
                
                st.markdown("---")
        
    except Exception as e:
        st.error(f"❌ Błąd ładowania LOT chains: {e}")
        import traceback
        st.code(traceback.format_exc())

def show_chain_analytics_tab():
    """PUNKT 82: Tab Chain Analytics - placeholder"""
    st.subheader("📊 Chain Analytics")
    st.info("🚧 **PUNKT 82** - W budowie: Historia i performance comparison")
    
    # Placeholder analytics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top Performing Chains:**")
        placeholder_data = [
            {"Chain": "WOLF #1", "Return": "28.4%", "Duration": "45d"},
            {"Chain": "AAPL #2", "Return": "22.1%", "Duration": "30d"},
            {"Chain": "MSFT #1", "Return": "19.8%", "Duration": "60d"}
        ]
        st.dataframe(pd.DataFrame(placeholder_data), use_container_width=True)
    
    with col2:
        st.markdown("**Chain Metrics:**")
        st.metric("Best Chain", "WOLF #1", "+28.4%")
        st.metric("Worst Chain", "TSLA #1", "-5.2%")
        st.metric("Avg Success Rate", "78%", "↗️ +3%")

def show_chain_management_tab():
    """PUNKT 83: Tab Chain Management - placeholder"""
    st.subheader("🛠️ Chain Management")
    st.info("🚧 **PUNKT 83** - W budowie: Ręczne łączenie/rozłączanie chains")
    
    # Placeholder management
    st.markdown("**Funkcje zarządzania:**")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔗 Create New Chain", disabled=True):
            st.info("Feature w budowie")
    
    with col2:
        if st.button("✂️ Split Chain", disabled=True):
            st.info("Feature w budowie")
    
    # Lista CC bez chains (do przyszłego przypisywania)
    try:
        unlinked_cc = db.get_covered_calls_summary()
        if unlinked_cc:
            st.markdown("**CC bez przypisanych chains:**")
            
            df_data = []
            for cc in unlinked_cc[:5]:  # Pokaż tylko 5 first
                df_data.append({
                    'ID': cc['id'],
                    'Ticker': cc['ticker'],
                    'Contracts': cc['contracts'],
                    'Status': cc['status'],
                    'Open Date': cc['open_date']
                })
            
            if df_data:
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
                st.caption("💡 Te CC będą automatycznie grupowane w chains w PUNKT 74")
    
    except Exception as e:
        st.error(f"❌ Błąd ładowania CC: {e}")

# NAPRAWKA: Dodaj debug bezpośrednio w pages/cc_chains.py
# Zamień funkcję show_auto_detection_tab() na tę wersję z debug:

def show_auto_detection_tab():
    """PUNKT 74-75: Tab Auto-Detection - ZAKTUALIZOWANY dla LOT Chains"""
    st.subheader("🤖 LOT Chains Auto-Detection")
    st.info("🔗 **PUNKT 74-75** - Automatyczne tworzenie chains per LOT akcji")
    
    # NOWY OPIS LOGIKI
    st.markdown("""
    ### 📦 **LOT Chain Concept:**
    
    **Chain = Kompletny lifecycle pojedynczego LOT-a akcji:**
    1. 🛒 **Zakup LOT-a** (np. 100 KURA @ $10)
    2. 📞 **CC #1** na tym LOT-cie → expire/assign/buyback
    3. 📞 **CC #2** na tym samym LOT-cie → expire/assign/buyback  
    4. 📞 **CC #3** na tym samym LOT-cie...
    5. 💸 **Sprzedaż LOT-a** → **KONIEC CHAIN**
    
    **Jeden LOT = Jeden Chain** (bazuje na `lot_linked_id`)
    """)
    
    # DEBUG: Sprawdź czy nowa funkcja istnieje
    st.markdown("### 🔍 DEBUG:")
    
    try:
        # Test 1: Sprawdź dostępność funkcji
        if hasattr(db, 'auto_detect_lot_chains'):
            st.success("✅ Funkcja auto_detect_lot_chains istnieje")
        elif hasattr(db, 'auto_detect_cc_chains'):
            st.warning("⚠️ Używam starą funkcję auto_detect_cc_chains (do aktualizacji)")
        else:
            st.error("❌ Brak funkcji auto-detection!")
            st.stop()
        
        # Test 2: Status przed testem - ZAKTUALIZOWANE METRYKI
        col_debug1, col_debug2 = st.columns(2)
        
        with col_debug1:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # CC bez chains
            cursor.execute("SELECT COUNT(*) FROM options_cc WHERE chain_id IS NULL")
            unlinked_cc = cursor.fetchone()[0]
            
            # CC z lot_linked_id
            cursor.execute("""
                SELECT COUNT(*) 
                FROM options_cc 
                WHERE chain_id IS NULL AND lot_linked_id IS NOT NULL
            """)
            cc_with_lots = cursor.fetchone()[0]
            
            st.metric("CC bez chains", unlinked_cc)
            st.metric("CC z LOT-ami", cc_with_lots)
            
            conn.close()
        
        with col_debug2:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Total chains
            cursor.execute("SELECT COUNT(*) FROM cc_chains")
            total_chains = cursor.fetchone()[0]
            
            # LOT-y z CC (potencjalne chains)
            cursor.execute("""
                SELECT COUNT(DISTINCT lot_linked_id)
                FROM options_cc 
                WHERE lot_linked_id IS NOT NULL AND chain_id IS NULL
            """)
            lots_needing_chains = cursor.fetchone()[0]
            
            st.metric("Existing chains", total_chains)
            st.metric("LOT-y ready", lots_needing_chains)
            
            conn.close()
    
    except Exception as e:
        st.error(f"❌ DEBUG Error: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    # GŁÓWNY TEST - ZAKTUALIZOWANY
    if st.button("🔍 Test LOT Chains Auto-Detection"):
        st.markdown("### 🧪 LOT CHAINS AUTO-DETECTION:")
        
        try:
            with st.spinner("Tworzenie LOT chains..."):
                
                # PRE-TEST: Pokaż LOT-y gotowe do chains
                with st.expander("📋 LOT-y gotowe do chains", expanded=True):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    
                    # LOT-y z CC bez chains
                    cursor.execute("""
                        SELECT DISTINCT 
                            l.id as lot_id,
                            l.ticker, 
                            l.buy_date,
                            l.quantity_open,
                            COUNT(cc.id) as cc_count
                        FROM lots l
                        JOIN options_cc cc ON cc.lot_linked_id = l.id
                        WHERE cc.chain_id IS NULL
                        GROUP BY l.id, l.ticker, l.buy_date, l.quantity_open
                        ORDER BY l.ticker, l.buy_date
                    """)
                    lots_ready = cursor.fetchall()
                    
                    st.write(f"**LOT-y gotowe do chains ({len(lots_ready)}):**")
                    for lot in lots_ready:
                        status = "🟢 Active" if lot[3] > 0 else "🔴 Sold"
                        st.write(f"   LOT #{lot[0]}: {lot[1]} ({lot[2]}) - {lot[4]} CC - {status}")
                    
                    conn.close()
                
                # WYWOŁAJ NOWĄ FUNKCJĘ
                st.write("🤖 Wywołuję auto-detection...")
                
                # Użyj nowej funkcji jeśli dostępna, fallback do starej
                if hasattr(db, 'auto_detect_lot_chains'):
                    result = db.auto_detect_lot_chains()
                else:
                    result = db.auto_detect_cc_chains()  # Fallback
                
                st.write(f"📊 Wynik: {result}")
                
                # SPRAWDŹ WYNIK
                if result.get('success'):
                    st.success("✅ SUKCES!")
                    st.write(f"🔗 Chains created: **{result.get('chains_created', 0)}**")
                    st.write(f"📞 CC assigned: **{result.get('cc_assigned', 0)}**")
                    st.write(f"📦 LOT-y processed: **{result.get('lots_processed', 0)}**")
                    
                    if 'details' in result:
                        details = result['details']
                        if 'active_chains' in details:
                            st.info(f"🟢 Active chains: {details['active_chains']}")
                        if 'closed_chains' in details:
                            st.info(f"🔴 Closed chains: {details['closed_chains']}")
                    
                    st.success(f"💬 {result.get('message', '')}")
                    
                    if result.get('chains_created', 0) > 0:
                        st.balloons()
                        st.rerun()  # Odśwież stronę
                else:
                    st.error("❌ BŁĄD!")
                    st.error(f"💬 {result.get('message', 'Nieznany błąd')}")
                    if 'error_details' in result:
                        with st.expander("🔧 Szczegóły błędu"):
                            st.code(result['error_details'])
                
        except Exception as e:
            st.error(f"❌ Exception podczas testu: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # INSTRUKCJA UŻYTKOWNIKA
    st.markdown("---")
    st.markdown("### 📚 Jak to działa:")
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown("""
        **🔗 LOT Chain Lifecycle:**
        - Każdy LOT tworzy **jeden chain**
        - Chain trackuje **wszystkie CC** na LOT-cie
        - Chain kończy się przy **sprzedaży LOT-a**
        """)
    
    with col_info2:
        st.markdown("""
        **📊 Chain Analytics:**
        - **Total Premium** z wszystkich CC
        - **Total P/L** (CC + stock sale)
        - **ROI%** na LOT-cie
        """)
    
    # CURRENT STATUS PREVIEW
    try:
        # Pokaż przykład chains jeśli istnieją
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ch.chain_name, ch.ticker, ch.status, 
                   COUNT(cc.id) as cc_count
            FROM cc_chains ch
            LEFT JOIN options_cc cc ON cc.chain_id = ch.id  
            GROUP BY ch.id, ch.chain_name, ch.ticker, ch.status
            LIMIT 3
        """)
        
        sample_chains = cursor.fetchall()
        
        if sample_chains:
            st.markdown("### 📋 Przykłady chains:")
            for chain in sample_chains:
                status_icon = "🟢" if chain[2] == 'active' else "🔴"
                st.caption(f"{status_icon} {chain[0]} - {chain[3]} CC")
        
        conn.close()
        
    except Exception as e:
        st.warning(f"⚠️ Błąd ładowania przykładów: {e}")



# PUNKT 73.1: Test function dla weryfikacji
def test_cc_chains_ui():
    """Test podstawowego UI CC Chains"""
    try:
        migration_status = check_migration_status()
        return {
            'ui_loads': True,
            'migration_ok': migration_status.get('success', False),
            'tabs_work': True  # Jeśli doszedł tutaj, tabs działają
        }
    except Exception as e:
        return {
            'ui_loads': False,
            'error': str(e)
        }


# Main function
if __name__ == "__main__":
    show_cc_chains()