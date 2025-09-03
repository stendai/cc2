# DIAGNOSTYKA I NAPRAWA BŁĘDÓW MODUŁU STOCKS
# ==========================================

# 1. UTWORZ PLIK: diagnostic_stocks.py w głównym katalogu
import sqlite3
from colorama import init, Fore, Style
import db
from datetime import datetime, date

init(autoreset=True)  # Inicjalizacja colorama

def diagnose_stocks_issues(ticker=None):
    """
    Kompleksowa diagnostyka problemów z modułem stocks
    """
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}🔍 DIAGNOSTYKA MODUŁU STOCKS")
    print(f"{Fore.CYAN}{'='*60}")
    
    conn = db.get_connection()
    if not conn:
        print(f"{Fore.RED}❌ Brak połączenia z bazą danych")
        return
    
    cursor = conn.cursor()
    
    # 1. SPRAWDŹ WSZYSTKIE TICKERY LUB KONKRETNY
    if ticker:
        tickers = [ticker.upper()]
        print(f"{Fore.YELLOW}🎯 Analizuję ticker: {ticker}")
    else:
        cursor.execute("SELECT DISTINCT ticker FROM lots ORDER BY ticker")
        tickers = [row[0] for row in cursor.fetchall()]
        print(f"{Fore.YELLOW}📊 Analizuję wszystkie tickery: {', '.join(tickers)}")
    
    print()
    
    for ticker_name in tickers:
        print(f"\n{Fore.BLUE}{'─'*50}")
        print(f"{Fore.BLUE}📈 TICKER: {ticker_name}")
        print(f"{Fore.BLUE}{'─'*50}")
        
        # A. POBIERZ WSZYSTKIE LOT-Y
        cursor.execute("""
            SELECT id, quantity_total, quantity_open, buy_date, buy_price_usd
            FROM lots 
            WHERE ticker = ?
            ORDER BY buy_date ASC, id ASC
        """, (ticker_name,))
        lots = cursor.fetchall()
        
        if not lots:
            print(f"{Fore.YELLOW}⚠️  Brak LOT-ów dla {ticker_name}")
            continue
            
        print(f"🏷️  Znalezionych LOT-ów: {len(lots)}")
        
        # B. POLICZ RZECZYWISTE SUMY
        total_bought = sum(lot[1] for lot in lots)  # quantity_total
        total_open_from_lots = sum(lot[2] for lot in lots)  # quantity_open
        
        print(f"📦 Łącznie kupione: {total_bought}")
        print(f"💼 Quantity_open z LOT-ów: {total_open_from_lots}")
        
        # C. POLICZ RZECZYWISTE SPRZEDAŻE (z stock_trade_splits)
        cursor.execute("""
            SELECT COALESCE(SUM(sts.qty_from_lot), 0) as total_sold
            FROM stock_trade_splits sts
            JOIN stock_trades st ON sts.trade_id = st.id
            WHERE st.ticker = ?
        """, (ticker_name,))
        
        result = cursor.fetchone()
        real_sold = int(result[0]) if result and result[0] else 0
        print(f"📉 Rzeczywiście sprzedane: {real_sold}")
        
        # D. POLICZ REZERWACJE POD CC
        cursor.execute("""
            SELECT COALESCE(SUM(contracts * 100), 0) as total_reserved
            FROM options_cc 
            WHERE ticker = ? AND status = 'open'
        """, (ticker_name,))
        
        result = cursor.fetchone()
        reserved_cc = int(result[0]) if result and result[0] else 0
        print(f"🔒 Zarezerwowane pod CC: {reserved_cc}")
        
        # E. TEORETYCZNE OBLICZENIA
        theoretical_available = total_bought - real_sold - reserved_cc
        print(f"✅ Teoretycznie dostępne: {total_bought} - {real_sold} - {reserved_cc} = {theoretical_available}")
        
        # F. SPRAWDŹ FUNKCJĘ get_total_and_available_shares()
        try:
            total_func, available_func = db.get_total_and_available_shares(ticker_name)
            print(f"🔧 get_total_and_available_shares(): total={total_func}, available={available_func}")
            
            # PORÓWNAJ WYNIKI
            if total_func != total_bought:
                print(f"{Fore.RED}❌ BŁĄD: Funkcja zwraca total={total_func}, powinno być {total_bought}")
            if available_func != theoretical_available:
                print(f"{Fore.RED}❌ BŁĄD: Funkcja zwraca available={available_func}, powinno być {theoretical_available}")
                
            if total_func == total_bought and available_func == theoretical_available:
                print(f"{Fore.GREEN}✅ Funkcja get_total_and_available_shares() działa poprawnie")
                
        except Exception as e:
            print(f"{Fore.RED}❌ BŁĄD w get_total_and_available_shares(): {e}")
        
        # G. SZCZEGÓŁOWA ANALIZA KAŻDEGO LOT-A
        print(f"\n{Fore.CYAN}📋 Szczegóły LOT-ów:")
        
        lot_issues = 0
        for lot in lots:
            lot_id, qty_total, qty_open, buy_date, buy_price = lot
            
            # Ile sprzedano z tego LOT-a?
            cursor.execute("""
                SELECT COALESCE(SUM(qty_from_lot), 0)
                FROM stock_trade_splits
                WHERE lot_id = ?
            """, (lot_id,))
            sold_from_lot = int(cursor.fetchone()[0] or 0)
            
            # Teoretyczne quantity_open
            theoretical_open = qty_total - sold_from_lot
            
            if qty_open != theoretical_open:
                print(f"{Fore.RED}❌ LOT #{lot_id}: quantity_open={qty_open}, powinno być {theoretical_open}")
                lot_issues += 1
            else:
                print(f"{Fore.GREEN}✅ LOT #{lot_id}: quantity_open={qty_open} (OK)")
        
        if lot_issues > 0:
            print(f"\n{Fore.RED}🚨 Znaleziono {lot_issues} błędów w quantity_open!")
            print(f"{Fore.YELLOW}💡 Uruchom fix_quantity_open_issues() aby naprawić")
        
        # H. SPRAWDŹ BLOKADY CC
        print(f"\n{Fore.MAGENTA}🔍 Analiza blokad Covered Calls:")
        
        cursor.execute("""
            SELECT id, contracts, strike_price, expiry_date, status
            FROM options_cc 
            WHERE ticker = ?
            ORDER BY expiry_date ASC
        """, (ticker_name,))
        cc_list = cursor.fetchall()
        
        if cc_list:
            for cc in cc_list:
                cc_id, contracts, strike, expiry, status = cc
                shares_blocked = contracts * 100
                print(f"  CC #{cc_id}: {contracts} kontraktów = {shares_blocked} akcji, {status}")
        else:
            print(f"  Brak Covered Calls")
    
    conn.close()
    print(f"\n{Fore.GREEN}✅ Diagnostyka zakończona")


def fix_quantity_open_issues():
    """
    Naprawia błędne quantity_open w tabeli lots
    """
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}🔧 NAPRAWKA quantity_open w LOT-ach")
    print(f"{Fore.CYAN}{'='*60}")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Pobierz wszystkie LOT-y
    cursor.execute("""
        SELECT id, ticker, quantity_total, quantity_open
        FROM lots
        ORDER BY ticker, buy_date ASC, id ASC
    """)
    lots = cursor.fetchall()
    
    fixes = 0
    
    for lot in lots:
        lot_id, ticker, qty_total, qty_open = lot
        
        # Policz ile sprzedano z tego LOT-a
        cursor.execute("""
            SELECT COALESCE(SUM(qty_from_lot), 0)
            FROM stock_trade_splits
            WHERE lot_id = ?
        """, (lot_id,))
        sold_from_lot = int(cursor.fetchone()[0] or 0)
        
        # Teoretyczne quantity_open
        correct_open = qty_total - sold_from_lot
        
        if qty_open != correct_open:
            cursor.execute("""
                UPDATE lots 
                SET quantity_open = ?
                WHERE id = ?
            """, (correct_open, lot_id))
            
            print(f"{Fore.GREEN}✅ LOT #{lot_id} ({ticker}): {qty_open} → {correct_open}")
            fixes += 1
        else:
            print(f"  LOT #{lot_id} ({ticker}): {qty_open} (OK)")
    
    conn.commit()
    conn.close()
    
    print(f"\n{Fore.GREEN}🎯 Naprawiono {fixes} LOT-ów")


def test_get_total_and_available_function():
    """
    Testuje funkcję get_total_and_available_shares dla wszystkich tickerów
    """
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}🧪 TEST get_total_and_available_shares()")
    print(f"{Fore.CYAN}{'='*60}")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Pobierz wszystkie tickery
    cursor.execute("SELECT DISTINCT ticker FROM lots")
    tickers = [row[0] for row in cursor.fetchall()]
    
    for ticker in tickers:
        print(f"\n{Fore.BLUE}📈 {ticker}:")
        
        try:
            total, available = db.get_total_and_available_shares(ticker)
            print(f"  🔧 Funkcja: total={total}, available={available}")
            
            # Manualnie policz dla porównania
            cursor.execute("""
                SELECT COALESCE(SUM(quantity_total), 0), COALESCE(SUM(quantity_open), 0)
                FROM lots WHERE ticker = ?
            """, (ticker,))
            manual_total, manual_open = cursor.fetchone()
            
            cursor.execute("""
                SELECT COALESCE(SUM(sts.qty_from_lot), 0)
                FROM stock_trade_splits sts
                JOIN stock_trades st ON sts.trade_id = st.id
                WHERE st.ticker = ?
            """, (ticker,))
            sold = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COALESCE(SUM(contracts * 100), 0)
                FROM options_cc WHERE ticker = ? AND status = 'open'
            """, (ticker,))
            reserved = cursor.fetchone()[0] or 0
            
            manual_available = manual_total - sold - reserved
            
            print(f"  📊 Manualne: total={manual_total}, available={manual_available}")
            
            # Porównaj
            if total == manual_total and available == manual_available:
                print(f"  {Fore.GREEN}✅ ZGODNE")
            else:
                print(f"  {Fore.RED}❌ RÓŻNIĄ SIĘ!")
                
        except Exception as e:
            print(f"  {Fore.RED}❌ BŁĄD: {e}")
    
    conn.close()


if __name__ == "__main__":
    print("🔍 NARZĘDZIE DIAGNOSTYCZNE STOCKS")
    print("================================")
    print("1. diagnose_stocks_issues() - pełna diagnostyka")
    print("2. diagnose_stocks_issues('AAPL') - dla konkretnego tickera")
    print("3. fix_quantity_open_issues() - naprawa quantity_open")
    print("4. test_get_total_and_available_function() - test funkcji")
    print("\nPrzykład użycia:")
    print("python diagnostic_stocks.py")
    
    # Uruchom pełną diagnostykę
    diagnose_stocks_issues()
    
    # Napraw quantity_open
    print(f"\n{Fore.YELLOW}🔧 Czy naprawić quantity_open? (y/n)")
    if input().lower() == 'y':
        fix_quantity_open_issues()
    
    # Test funkcji
    test_get_total_and_available_function()