#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗑️ STOCK DATA CLEANER - Usuń wszystkie dane testowe dla wybranego tickera
Zapisz jako clean_stock_data.py i uruchom: python clean_stock_data.py
"""

import sqlite3
import os
from datetime import datetime

def clean_stock_data():
    """Główna funkcja czyszczenia danych akcji"""
    
    db_path = 'portfolio.db'
    if not os.path.exists(db_path):
        print(f"❌ Nie znaleziono bazy danych: {db_path}")
        print("💡 Sprawdź czy jesteś w katalogu z aplikacją Streamlit")
        return
    
    print("🗑️ STOCK DATA CLEANER")
    print("=" * 50)
    print("⚠️  UWAGA: To trwale usuwa WSZYSTKIE dane dla wybranego tickera!")
    print("   - Zakupy akcji (LOT-y)")
    print("   - Sprzedaże akcji")
    print("   - Covered Calls (CC)")
    print("   - Cashflows")
    print("   - Dywidendy")
    print("   - Mapowania CC")
    print()
    
    # Pokaż dostępne tickery
    show_available_tickers()
    
    while True:
        ticker_input = input("\n📝 Wpisz symbol akcji do usunięcia (lub 'exit' aby wyjść): ").strip().upper()
        
        if ticker_input.lower() == 'exit':
            print("👋 Do widzenia!")
            return
            
        if not ticker_input:
            print("❌ Podaj symbol akcji!")
            continue
            
        # Sprawdź czy ticker istnieje
        if not ticker_exists(ticker_input):
            print(f"❌ Ticker '{ticker_input}' nie znaleziony w bazie!")
            continue
            
        # Pokaż co zostanie usunięte
        data_summary = analyze_ticker_data(ticker_input)
        if not data_summary:
            continue
            
        show_deletion_summary(ticker_input, data_summary)
        
        # Potwierdź usunięcie
        confirmation = input(f"\n⚠️  Wpisz '{ticker_input}' aby potwierdzić TRWAŁE USUNIĘCIE: ")
        
        if confirmation != ticker_input:
            print("❌ Anulowano - brak zmian")
            continue
            
        # Wykonaj usunięcie
        result = delete_ticker_data(ticker_input, data_summary)
        
        if result['success']:
            print(f"\n🎉 Pomyślnie usunięto wszystkie dane dla {ticker_input}!")
            print(f"📊 Usunięto łącznie: {result['total_deleted']} rekordów")
            
            # Pokaż szczegóły
            for table, count in result['deleted_per_table'].items():
                if count > 0:
                    print(f"   - {table}: {count}")
        else:
            print(f"❌ Błąd podczas usuwania: {result['message']}")
        
        # Zapytaj czy usunąć kolejny ticker
        another = input(f"\n❓ Usunąć dane dla kolejnego tickera? (y/n): ")
        if another.lower() != 'y':
            break

def show_available_tickers():
    """Pokaż dostępne tickery w bazie"""
    
    try:
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        
        print("📊 DOSTĘPNE TICKERY W BAZIE:")
        
        # Tickery z lots (akcje)
        cursor.execute("""
            SELECT ticker, COUNT(*) as lot_count, 
                   SUM(quantity_total) as total_shares,
                   SUM(quantity_open) as available_shares
            FROM lots 
            GROUP BY ticker 
            ORDER BY ticker
        """)
        
        lots_data = cursor.fetchall()
        
        if lots_data:
            print("\n   📦 AKCJE (LOT-y):")
            for ticker, lot_count, total_shares, available_shares in lots_data:
                blocked = total_shares - available_shares
                status = f" ({blocked} zablokowane)" if blocked > 0 else ""
                print(f"      {ticker}: {lot_count} LOT-ów, {total_shares} akcji{status}")
        
        # Tickery z CC
        cursor.execute("""
            SELECT ticker, COUNT(*) as cc_count,
                   SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_cc,
                   SUM(CASE WHEN status = 'bought_back' THEN 1 ELSE 0 END) as bought_back,
                   SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired
            FROM options_cc 
            GROUP BY ticker 
            ORDER BY ticker
        """)
        
        cc_data = cursor.fetchall()
        
        if cc_data:
            print("\n   🎯 COVERED CALLS:")
            for ticker, cc_count, open_cc, bought_back, expired in cc_data:
                status_parts = []
                if open_cc > 0: status_parts.append(f"{open_cc} open")
                if bought_back > 0: status_parts.append(f"{bought_back} bought_back")
                if expired > 0: status_parts.append(f"{expired} expired")
                
                status_str = " (" + ", ".join(status_parts) + ")" if status_parts else ""
                print(f"      {ticker}: {cc_count} CC{status_str}")
        
        # Tickery z dywidend (jeśli tabela istnieje)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dividends'")
        if cursor.fetchone():
            cursor.execute("""
                SELECT ticker, COUNT(*) as div_count, SUM(gross_usd) as total_gross
                FROM dividends 
                GROUP BY ticker 
                ORDER BY ticker
            """)
            
            div_data = cursor.fetchall()
            if div_data:
                print("\n   💵 DYWIDENDY:")
                for ticker, div_count, total_gross in div_data:
                    print(f"      {ticker}: {div_count} dywidend, ${total_gross:.2f} brutto")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Błąd pobierania tickerów: {e}")

def ticker_exists(ticker):
    """Sprawdź czy ticker istnieje w bazie"""
    
    try:
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        
        # Sprawdź w lots
        cursor.execute("SELECT COUNT(*) FROM lots WHERE ticker = ?", (ticker,))
        lots_count = cursor.fetchone()[0]
        
        # Sprawdź w options_cc
        cursor.execute("SELECT COUNT(*) FROM options_cc WHERE ticker = ?", (ticker,))
        cc_count = cursor.fetchone()[0]
        
        # Sprawdź w dividends (jeśli tabela istnieje)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dividends'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM dividends WHERE ticker = ?", (ticker,))
            div_count = cursor.fetchone()[0]
        else:
            div_count = 0
        
        conn.close()
        
        return (lots_count + cc_count + div_count) > 0
        
    except Exception as e:
        print(f"❌ Błąd sprawdzania tickera: {e}")
        return False

def analyze_ticker_data(ticker):
    """Analizuj jakie dane zostaną usunięte"""
    
    try:
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        
        analysis = {
            'lots': [],
            'stock_trades': [],
            'options_cc': [],
            'cashflows': [],
            'dividends': [],
            'cc_mappings': []
        }
        
        # 1. LOT-y
        cursor.execute("""
            SELECT id, quantity_total, quantity_open, buy_price_usd, buy_date, cost_pln
            FROM lots WHERE ticker = ?
            ORDER BY buy_date DESC
        """, (ticker,))
        
        analysis['lots'] = cursor.fetchall()
        
        # 2. Sprzedaże akcji
        cursor.execute("""
            SELECT id, quantity, sell_price_usd, sell_date, pl_pln
            FROM stock_trades WHERE ticker = ?
            ORDER BY sell_date DESC
        """, (ticker,))
        
        analysis['stock_trades'] = cursor.fetchall()
        
        # 3. Covered Calls
        cursor.execute("""
            SELECT id, contracts, strike_usd, premium_sell_usd, premium_buyback_usd, 
                   open_date, close_date, status, premium_sell_pln, premium_buyback_pln
            FROM options_cc WHERE ticker = ?
            ORDER BY open_date DESC
        """, (ticker,))
        
        analysis['options_cc'] = cursor.fetchall()
        
        # 4. Cashflows powiązane
        lot_ids = [str(lot[0]) for lot in analysis['lots']] if analysis['lots'] else []
        cc_ids = [str(cc[0]) for cc in analysis['options_cc']] if analysis['options_cc'] else []
        trade_ids = [str(trade[0]) for trade in analysis['stock_trades']] if analysis['stock_trades'] else []
        
        all_ref_ids = lot_ids + cc_ids + trade_ids
        
        if all_ref_ids:
            placeholders = ','.join(['?' for _ in all_ref_ids])
            cursor.execute(f"""
                SELECT id, type, amount_usd, amount_pln, description, ref_table, ref_id
                FROM cashflows 
                WHERE (ref_table = 'lots' AND ref_id IN ({','.join(lot_ids) if lot_ids else '0'}))
                   OR (ref_table = 'options_cc' AND ref_id IN ({','.join(cc_ids) if cc_ids else '0'}))
                   OR (ref_table = 'stock_trades' AND ref_id IN ({','.join(trade_ids) if trade_ids else '0'}))
                ORDER BY date DESC
            """)
            
            analysis['cashflows'] = cursor.fetchall()
        
        # 5. Dywidendy (jeśli tabela istnieje) - POPRAWIONE NAZWY KOLUMN
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dividends'")
        if cursor.fetchone():
            cursor.execute("""
                SELECT id, gross_usd, wht_15_pln, net_pln, date_paid
                FROM dividends WHERE ticker = ?
                ORDER BY date_paid DESC
            """, (ticker,))
            
            analysis['dividends'] = cursor.fetchall()
        
        # 6. Mapowania CC (jeśli tabela istnieje)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cc_lot_mappings'")
        if cursor.fetchone() and cc_ids:
            cursor.execute(f"""
                SELECT cc_id, lot_id, shares_reserved
                FROM cc_lot_mappings 
                WHERE cc_id IN ({','.join(cc_ids) if cc_ids else '0'})
            """)
            
            analysis['cc_mappings'] = cursor.fetchall()
        
        conn.close()
        return analysis
        
    except Exception as e:
        print(f"❌ Błąd analizy danych: {e}")
        return None

def show_deletion_summary(ticker, analysis):
    """Pokaż podsumowanie co zostanie usunięte"""
    
    print(f"\n📋 PODSUMOWANIE USUNIĘCIA DLA: {ticker}")
    print("-" * 40)
    
    total_records = 0
    
    # LOT-y
    if analysis['lots']:
        print(f"📦 AKCJE - LOT-y ({len(analysis['lots'])}):")
        total_cost = 0
        total_shares = 0
        for lot_id, qty_total, qty_open, buy_price_usd, buy_date, cost_pln in analysis['lots']:
            status = f"({qty_open}/{qty_total})" if qty_open != qty_total else f"({qty_total})"
            print(f"   LOT #{lot_id}: {status} @ ${buy_price_usd:.2f} | {buy_date} | {cost_pln:.2f} PLN")
            total_cost += cost_pln
            total_shares += qty_total
        print(f"   💰 RAZEM: {total_shares} akcji za {total_cost:.2f} PLN")
        total_records += len(analysis['lots'])
    
    # Sprzedaże
    if analysis['stock_trades']:
        print(f"\n📊 SPRZEDAŻE AKCJI ({len(analysis['stock_trades'])}):")
        total_pl = 0
        for trade_id, qty, sell_price, sell_date, pl_pln in analysis['stock_trades']:
            print(f"   Trade #{trade_id}: {qty} @ ${sell_price:.2f} | {sell_date} | P/L: {pl_pln:.2f} PLN")
            total_pl += pl_pln or 0
        print(f"   📈 RAZEM P/L: {total_pl:.2f} PLN")
        total_records += len(analysis['stock_trades'])
    
    # Covered Calls
    if analysis['options_cc']:
        print(f"\n🎯 COVERED CALLS ({len(analysis['options_cc'])}):")
        total_premium_received = 0
        total_premium_paid = 0
        for cc_data in analysis['options_cc']:
            cc_id, contracts, strike, prem_sell, prem_buy, open_date, close_date, status, prem_sell_pln, prem_buy_pln = cc_data
            
            close_info = f" → {close_date}" if close_date else ""
            premium_info = f"${prem_sell:.2f}"
            if prem_buy:
                premium_info += f" → ${prem_buy:.2f}"
                
            pl_pln = (prem_sell_pln or 0) - (prem_buy_pln or 0)
            
            print(f"   CC #{cc_id}: {contracts} kontr. @ ${strike:.2f} | {open_date}{close_info}")
            print(f"      Premium: {premium_info} | Status: {status} | P/L: {pl_pln:.2f} PLN")
            
            total_premium_received += prem_sell_pln or 0
            if prem_buy_pln:
                total_premium_paid += prem_buy_pln or 0
        
        net_premium = total_premium_received - total_premium_paid
        print(f"   💰 RAZEM Premium: +{total_premium_received:.2f} -{total_premium_paid:.2f} = {net_premium:.2f} PLN")
        total_records += len(analysis['options_cc'])
    
    # Cashflows
    if analysis['cashflows']:
        print(f"\n💸 CASHFLOWS ({len(analysis['cashflows'])}):")
        total_usd = 0
        for cf_id, cf_type, amount_usd, amount_pln, description, ref_table, ref_id in analysis['cashflows']:
            print(f"   #{cf_id}: {cf_type} | ${amount_usd:.2f} | {description[:50]}...")
            total_usd += amount_usd or 0
        print(f"   💰 RAZEM NET: ${total_usd:.2f} USD")
        total_records += len(analysis['cashflows'])
    
    # Dywidendy
    if analysis['dividends']:
        print(f"\n💵 DYWIDENDY ({len(analysis['dividends'])}):")
        total_div = 0
        for div_id, gross, wht, net, date_paid in analysis['dividends']:
            print(f"   Div #{div_id}: ${gross:.2f} gross - ${wht:.2f} WHT = ${net:.2f} net | {date_paid}")
            total_div += net or 0
        print(f"   💰 RAZEM NETTO: ${total_div:.2f} USD")
        total_records += len(analysis['dividends'])
    
    # Mapowania
    if analysis['cc_mappings']:
        print(f"\n🔗 MAPOWANIA CC ({len(analysis['cc_mappings'])}):")
        for cc_id, lot_id, shares_reserved in analysis['cc_mappings']:
            print(f"   CC #{cc_id} → LOT #{lot_id}: {shares_reserved} akcji")
        total_records += len(analysis['cc_mappings'])
    
    print(f"\n📊 PODSUMOWANIE:")
    print(f"   🗑️ Do usunięcia: {total_records} rekordów")
    print(f"   ⚠️  Operacja jest NIEODWRACALNA!")

def delete_ticker_data(ticker, analysis):
    """Wykonaj usunięcie danych"""
    
    try:
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        
        deleted_counts = {
            'lots': 0,
            'stock_trades': 0,
            'stock_trade_splits': 0,
            'options_cc': 0,
            'cashflows': 0,
            'dividends': 0,
            'cc_lot_mappings': 0
        }
        
        print(f"\n🗑️ USUWANIE DANYCH DLA {ticker}...")
        
        # 1. Usuń mapowania CC (najpierw - foreign keys)
        if analysis['cc_mappings']:
            cc_ids = [str(cc[0]) for cc in analysis['options_cc']]
            if cc_ids:
                cursor.execute(f"DELETE FROM cc_lot_mappings WHERE cc_id IN ({','.join(cc_ids)})")
                deleted_counts['cc_lot_mappings'] = cursor.rowcount
                print(f"   ✅ Mapowania CC: {deleted_counts['cc_lot_mappings']}")
        
        # 2. Usuń cashflows
        if analysis['cashflows']:
            cf_ids = [str(cf[0]) for cf in analysis['cashflows']]
            cursor.execute(f"DELETE FROM cashflows WHERE id IN ({','.join(cf_ids)})")
            deleted_counts['cashflows'] = cursor.rowcount
            print(f"   ✅ Cashflows: {deleted_counts['cashflows']}")
        
        # 3. Usuń stock trade splits
        if analysis['stock_trades']:
            trade_ids = [str(trade[0]) for trade in analysis['stock_trades']]
            if trade_ids:
                cursor.execute(f"DELETE FROM stock_trade_splits WHERE trade_id IN ({','.join(trade_ids)})")
                deleted_counts['stock_trade_splits'] = cursor.rowcount
                print(f"   ✅ Trade splits: {deleted_counts['stock_trade_splits']}")
        
        # 4. Usuń stock trades
        if analysis['stock_trades']:
            cursor.execute("DELETE FROM stock_trades WHERE ticker = ?", (ticker,))
            deleted_counts['stock_trades'] = cursor.rowcount
            print(f"   ✅ Sprzedaże akcji: {deleted_counts['stock_trades']}")
        
        # 5. Usuń options CC
        if analysis['options_cc']:
            cursor.execute("DELETE FROM options_cc WHERE ticker = ?", (ticker,))
            deleted_counts['options_cc'] = cursor.rowcount
            print(f"   ✅ Covered Calls: {deleted_counts['options_cc']}")
        
        # 6. Usuń dywidendy (jeśli tabela istnieje)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dividends'")
        if cursor.fetchone() and analysis['dividends']:
            cursor.execute("DELETE FROM dividends WHERE ticker = ?", (ticker,))
            deleted_counts['dividends'] = cursor.rowcount
            print(f"   ✅ Dywidendy: {deleted_counts['dividends']}")
        
        # 7. Usuń LOT-y (na końcu)
        if analysis['lots']:
            cursor.execute("DELETE FROM lots WHERE ticker = ?", (ticker,))
            deleted_counts['lots'] = cursor.rowcount
            print(f"   ✅ LOT-y akcji: {deleted_counts['lots']}")
        
        # Zapisz zmiany
        conn.commit()
        conn.close()
        
        total_deleted = sum(deleted_counts.values())
        
        return {
            'success': True,
            'total_deleted': total_deleted,
            'deleted_per_table': deleted_counts
        }
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        
        return {
            'success': False,
            'message': str(e)
        }

def bulk_clean_mode():
    """Tryb masowego czyszczenia - usuń wiele tickerów na raz"""
    
    print("\n" + "="*50)
    print("🗑️ TRYB MASOWEGO CZYSZCZENIA")
    print("Usuń dane dla wielu tickerów jednocześnie")
    
    common_tickers = input("\n📝 Wpisz tickery oddzielone przecinkami (np: AAPL,MSFT,NVDA,META): ")
    
    if not common_tickers.strip():
        return
    
    tickers_list = [t.strip().upper() for t in common_tickers.split(',')]
    tickers_list = [t for t in tickers_list if t]  # Usuń puste
    
    if not tickers_list:
        print("❌ Nie podano tickerów!")
        return
    
    print(f"\n📋 Do usunięcia: {', '.join(tickers_list)}")
    
    # Sprawdź które tickery istnieją
    existing_tickers = []
    for ticker in tickers_list:
        if ticker_exists(ticker):
            existing_tickers.append(ticker)
        else:
            print(f"⚠️ {ticker} - nie znaleziony")
    
    if not existing_tickers:
        print("❌ Żaden z tickerów nie istnieje w bazie!")
        return
    
    print(f"\n✅ Znalezione tickery: {', '.join(existing_tickers)}")
    
    confirmation = input(f"\n⚠️ Wpisz 'USUŃ WSZYSTKO' aby potwierdzić masowe usunięcie: ")
    
    if confirmation != 'USUŃ WSZYSTKO':
        print("❌ Anulowano")
        return
    
    # Usuń kolejno każdy ticker
    total_deleted = 0
    for ticker in existing_tickers:
        print(f"\n🗑️ Usuwanie {ticker}...")
        analysis = analyze_ticker_data(ticker)
        if analysis:
            result = delete_ticker_data(ticker, analysis)
            if result['success']:
                total_deleted += result['total_deleted']
                print(f"✅ {ticker}: {result['total_deleted']} rekordów usunięte")
            else:
                print(f"❌ {ticker}: błąd - {result['message']}")
    
    print(f"\n🎉 MASOWE CZYSZCZENIE ZAKOŃCZONE!")
    print(f"📊 Usunięto łącznie: {total_deleted} rekordów")

if __name__ == "__main__":
    print("🗑️ STOCK DATA CLEANER")
    print("1. 🎯 Pojedynczy ticker")
    print("2. 🗑️ Masowe czyszczenie")
    print("3. ❌ Wyjście")
    
    choice = input("\nWybierz opcję (1-3): ")
    
    if choice == "1":
        clean_stock_data()
    elif choice == "2":
        bulk_clean_mode()
    else:
        print("👋 Do widzenia!")