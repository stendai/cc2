#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 DEBUG & FIX NARZĘDZIE
Diagnostyka i naprawa problemów z rezerwacjami CC
Uruchom: python debug_fix_cc.py
"""

import sqlite3
import pandas as pd
from datetime import datetime
from colorama import init, Fore, Back, Style

# Inicjalizacja kolorów
init(autoreset=True)

DB_PATH = "portfolio.db"

def get_connection():
    """Połączenie z bazą"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"{Fore.RED}Błąd połączenia: {e}")
        return None

def print_header(text):
    """Drukuj nagłówek"""
    print(f"\n{Back.BLUE}{Fore.WHITE}{'='*60}")
    print(f"{Back.BLUE}{Fore.WHITE} {text.center(58)} ")
    print(f"{Back.BLUE}{Fore.WHITE}{'='*60}{Style.RESET_ALL}\n")

def print_section(text):
    """Drukuj sekcję"""
    print(f"\n{Fore.CYAN}{'─'*40}")
    print(f"{Fore.CYAN}📍 {text}")
    print(f"{Fore.CYAN}{'─'*40}{Style.RESET_ALL}")

def diagnose_all():
    """KOMPLETNA DIAGNOSTYKA SYSTEMU"""
    
    print_header("DIAGNOSTYKA SYSTEMU CC")
    
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # 1. SPRAWDŹ JAKIE TABELE ISTNIEJĄ
    print_section("TABELE W BAZIE")
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Znalezione tabele ({len(tables)}):")
    for table in tables:
        if 'reservation' in table.lower() or 'mapping' in table.lower() or 'cc' in table.lower():
            print(f"  {Fore.YELLOW}⚠️  {table}")
        else:
            print(f"  ✓ {table}")
    
    # 2. SPRAWDŹ STAN LOT-ów
    print_section("STAN LOT-ów")
    
    cursor.execute("""
        SELECT ticker, COUNT(*) as lot_count, 
               SUM(quantity_total) as total_shares,
               SUM(quantity_open) as open_shares,
               SUM(quantity_total - quantity_open) as blocked_shares
        FROM lots
        GROUP BY ticker
        ORDER BY ticker
    """)
    
    lots_summary = cursor.fetchall()
    
    print(f"\n{Fore.GREEN}Podsumowanie LOT-ów:")
    print(f"{'Ticker':<10} {'LOT-y':<8} {'Total':<10} {'Open':<10} {'Blocked':<10}")
    print("─" * 50)
    
    for row in lots_summary:
        ticker = row[0]
        lot_count = row[1]
        total = row[2] or 0
        open_shares = row[3] or 0
        blocked = row[4] or 0
        
        if blocked > 0:
            print(f"{Fore.YELLOW}{ticker:<10} {lot_count:<8} {total:<10} {open_shares:<10} {blocked:<10} ⚠️")
        else:
            print(f"{ticker:<10} {lot_count:<8} {total:<10} {open_shares:<10} {blocked:<10}")
    
    # 3. SZCZEGÓŁY KAŻDEGO LOT-a
    print_section("SZCZEGÓŁY LOT-ów Z PROBLEMAMI")
    
    cursor.execute("""
        SELECT id, ticker, buy_date, quantity_total, quantity_open,
               (quantity_total - quantity_open) as blocked
        FROM lots
        WHERE quantity_open < quantity_total
        ORDER BY ticker, id
    """)
    
    problem_lots = cursor.fetchall()
    
    if problem_lots:
        print(f"\n{Fore.RED}LOT-y z zablokowanymi akcjami:")
        for lot in problem_lots:
            print(f"\n  LOT #{lot[0]} ({lot[1]}):")
            print(f"    Data zakupu: {lot[2]}")
            print(f"    Total: {lot[3]}, Open: {lot[4]}, {Fore.RED}Blocked: {lot[5]}")
            
            # Sprawdź co blokuje ten LOT
            lot_id = lot[0]
            ticker = lot[1]
            
            # Sprawdź sprzedaże
            cursor.execute("""
                SELECT COALESCE(SUM(qty_from_lot), 0)
                FROM stock_trade_splits
                WHERE lot_id = ?
            """, (lot_id,))
            sold = cursor.fetchone()[0]
            
            print(f"    Sprzedane: {sold}")
            
            # Sprawdź rezerwacje w options_cc_reservations
            cursor.execute("""
                SELECT cc_id, qty_reserved
                FROM options_cc_reservations
                WHERE lot_id = ?
            """, (lot_id,))
            
            old_reservations = cursor.fetchall()
            if old_reservations:
                print(f"    {Fore.YELLOW}Rezerwacje (options_cc_reservations):")
                for cc_id, qty in old_reservations:
                    # Sprawdź status CC
                    cursor.execute("SELECT status FROM options_cc WHERE id = ?", (cc_id,))
                    cc_status = cursor.fetchone()
                    cc_status = cc_status[0] if cc_status else "NIEZNANY"
                    
                    if cc_status != 'open':
                        print(f"      {Fore.RED}CC #{cc_id}: {qty} akcji (status: {cc_status}) ❌ BŁĄD!")
                    else:
                        print(f"      CC #{cc_id}: {qty} akcji (status: {cc_status})")
            
            # Sprawdź mapowania w cc_lot_mappings
            cursor.execute("""
                SELECT cc_id, shares_reserved
                FROM cc_lot_mappings
                WHERE lot_id = ?
            """, (lot_id,))
            
            new_mappings = cursor.fetchall()
            if new_mappings:
                print(f"    {Fore.YELLOW}Mapowania (cc_lot_mappings):")
                for cc_id, shares in new_mappings:
                    cursor.execute("SELECT status FROM options_cc WHERE id = ?", (cc_id,))
                    cc_status = cursor.fetchone()
                    cc_status = cc_status[0] if cc_status else "NIEZNANY"
                    
                    if cc_status != 'open':
                        print(f"      {Fore.RED}CC #{cc_id}: {shares} akcji (status: {cc_status}) ❌ BŁĄD!")
                    else:
                        print(f"      CC #{cc_id}: {shares} akcji (status: {cc_status})")
    
    # 4. SPRAWDŹ CC
    print_section("STATUS COVERED CALLS")
    
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM options_cc
        GROUP BY status
    """)
    
    cc_stats = cursor.fetchall()
    print(f"\nStatystyki CC:")
    for status, count in cc_stats:
        if status == 'open':
            print(f"  {Fore.GREEN}{status}: {count}")
        elif status == 'bought_back':
            print(f"  {Fore.YELLOW}{status}: {count}")
        else:
            print(f"  {status}: {count}")
    
    # 5. ZNAJDŹ PROBLEMY
    print_section("🔍 ZNALEZIONE PROBLEMY")
    
    problems_found = []
    
    # Problem 1: Bought_back CC z rezerwacjami w options_cc_reservations
    cursor.execute("""
        SELECT oc.id, oc.ticker, oc.contracts, COUNT(ocr.lot_id) as reservations
        FROM options_cc oc
        JOIN options_cc_reservations ocr ON oc.id = ocr.cc_id
        WHERE oc.status = 'bought_back'
        GROUP BY oc.id
    """)
    
    bad_old_reservations = cursor.fetchall()
    if bad_old_reservations:
        for cc_id, ticker, contracts, reservations in bad_old_reservations:
            problem = f"CC #{cc_id} ({ticker}) jest bought_back ale ma {reservations} rezerwacji w options_cc_reservations"
            problems_found.append(problem)
            print(f"{Fore.RED}❌ {problem}")
    
    # Problem 2: Bought_back CC z mapowaniami w cc_lot_mappings
    cursor.execute("""
        SELECT oc.id, oc.ticker, oc.contracts, COUNT(clm.lot_id) as mappings
        FROM options_cc oc
        JOIN cc_lot_mappings clm ON oc.id = clm.cc_id
        WHERE oc.status = 'bought_back'
        GROUP BY oc.id
    """)
    
    bad_new_mappings = cursor.fetchall()
    if bad_new_mappings:
        for cc_id, ticker, contracts, mappings in bad_new_mappings:
            problem = f"CC #{cc_id} ({ticker}) jest bought_back ale ma {mappings} mapowań w cc_lot_mappings"
            problems_found.append(problem)
            print(f"{Fore.RED}❌ {problem}")
    
    # Problem 3: LOT-y z quantity_open = 0 bez powodu
    cursor.execute("""
        SELECT l.id, l.ticker, l.quantity_total
        FROM lots l
        WHERE l.quantity_open = 0
        AND NOT EXISTS (
            SELECT 1 FROM stock_trade_splits sts 
            WHERE sts.lot_id = l.id 
            HAVING SUM(sts.qty_from_lot) >= l.quantity_total
        )
    """)
    
    zero_lots = cursor.fetchall()
    if zero_lots:
        for lot_id, ticker, total in zero_lots:
            problem = f"LOT #{lot_id} ({ticker}) ma quantity_open=0 ale nie jest w pełni sprzedany"
            problems_found.append(problem)
            print(f"{Fore.RED}❌ {problem}")
    
    if not problems_found:
        print(f"{Fore.GREEN}✅ Nie znaleziono problemów!")
    
    conn.close()
    
    return problems_found

def fix_all_problems():
    """NAPRAW WSZYSTKIE ZNALEZIONE PROBLEMY"""
    
    print_header("NAPRAWA PROBLEMÓW")
    
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    fixes_applied = 0
    
    # 1. USUŃ REZERWACJE DLA BOUGHT_BACK CC
    print_section("Usuwanie rezerwacji dla bought_back CC")
    
    # Stara tabela
    cursor.execute("""
        DELETE FROM options_cc_reservations 
        WHERE cc_id IN (
            SELECT id FROM options_cc 
            WHERE status IN ('bought_back', 'expired', 'exercised')
        )
    """)
    
    old_deleted = cursor.rowcount
    if old_deleted > 0:
        print(f"{Fore.GREEN}✅ Usunięto {old_deleted} rezerwacji ze starej tabeli")
        fixes_applied += old_deleted
    
    # Nowa tabela
    cursor.execute("""
        DELETE FROM cc_lot_mappings 
        WHERE cc_id IN (
            SELECT id FROM options_cc 
            WHERE status IN ('bought_back', 'expired', 'exercised')
        )
    """)
    
    new_deleted = cursor.rowcount
    if new_deleted > 0:
        print(f"{Fore.GREEN}✅ Usunięto {new_deleted} mapowań z nowej tabeli")
        fixes_applied += new_deleted
    
    # 2. NAPRAW QUANTITY_OPEN DLA KAŻDEGO TICKERA
    print_section("Naprawa quantity_open metodą BEZPIECZNEGO RESETU")
    
    cursor.execute("SELECT DISTINCT ticker FROM lots")
    all_tickers = [row[0] for row in cursor.fetchall()]
    
    for ticker in all_tickers:
        print(f"\n{Fore.CYAN}Naprawiam ticker: {ticker}")
        
        # Pobierz wszystkie LOT-y tickera
        cursor.execute("""
            SELECT id, quantity_total, quantity_open
            FROM lots 
            WHERE ticker = ?
            ORDER BY buy_date ASC, id ASC
        """, (ticker,))
        
        lots = cursor.fetchall()
        
        for lot_id, quantity_total, current_open in lots:
            
            # FORMUŁA BEZPIECZNEGO RESETU
            # quantity_open = total - sprzedane - otwarte_CC
            
            # A. Ile sprzedano z tego LOT-a
            cursor.execute("""
                SELECT COALESCE(SUM(sts.qty_from_lot), 0)
                FROM stock_trade_splits sts
                WHERE sts.lot_id = ?
            """, (lot_id,))
            total_sold = cursor.fetchone()[0]
            
            # B. Ile powinno być zarezerwowane pod OTWARTE CC
            # To jest bardziej skomplikowane - musimy użyć FIFO per ticker
            
            # Prostsze podejście - policz dla całego tickera i podziel proporcjonalnie
            cursor.execute("""
                SELECT COALESCE(SUM(contracts * 100), 0)
                FROM options_cc 
                WHERE ticker = ? AND status = 'open'
            """, (ticker,))
            total_cc_shares = cursor.fetchone()[0]
            
            # Dla pierwszego LOT-a przypisz maksymalnie co może
            if lot_id == lots[0][0]:  # Pierwszy LOT (FIFO)
                available_in_lot = quantity_total - total_sold
                reserved_for_cc = min(available_in_lot, total_cc_shares)
                correct_open = quantity_total - total_sold - reserved_for_cc
            else:
                # Dla kolejnych LOT-ów - zobacz ile już zarezerwowano w poprzednich
                already_reserved = 0
                for prev_lot_id, prev_total, _ in lots:
                    if prev_lot_id >= lot_id:
                        break
                    cursor.execute("""
                        SELECT COALESCE(SUM(qty_from_lot), 0)
                        FROM stock_trade_splits
                        WHERE lot_id = ?
                    """, (prev_lot_id,))
                    prev_sold = cursor.fetchone()[0]
                    prev_available = prev_total - prev_sold
                    already_reserved += min(prev_available, total_cc_shares - already_reserved)
                
                remaining_cc = max(0, total_cc_shares - already_reserved)
                available_in_lot = quantity_total - total_sold
                reserved_for_cc = min(available_in_lot, remaining_cc)
                correct_open = quantity_total - total_sold - reserved_for_cc
            
            # Upewnij się że nie jest ujemne
            correct_open = max(0, correct_open)
            
            # ZASTOSUJ POPRAWKĘ
            if correct_open != current_open:
                cursor.execute("""
                    UPDATE lots 
                    SET quantity_open = ?
                    WHERE id = ?
                """, (correct_open, lot_id))
                
                print(f"  LOT #{lot_id}: {current_open} → {correct_open} {Fore.GREEN}✅")
                fixes_applied += 1
            else:
                print(f"  LOT #{lot_id}: {current_open} (OK)")
    
    # 3. COMMIT ZMIAN
    conn.commit()
    conn.close()
    
    print(f"\n{Back.GREEN}{Fore.WHITE} PODSUMOWANIE: Zastosowano {fixes_applied} poprawek {Style.RESET_ALL}")
    
    return fixes_applied

def verify_fix():
    """WERYFIKUJ CZY NAPRAWA ZADZIAŁAŁA"""
    
    print_header("WERYFIKACJA PO NAPRAWIE")
    
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Sprawdź czy są jeszcze zablokowane LOT-y
    cursor.execute("""
        SELECT COUNT(*) 
        FROM lots 
        WHERE quantity_open < quantity_total
    """)
    
    blocked_lots = cursor.fetchone()[0]
    
    # Sprawdź ile jest otwartych CC
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(contracts * 100), 0)
        FROM options_cc 
        WHERE status = 'open'
    """)
    
    open_cc_count, total_cc_shares = cursor.fetchone()
    
    # Sprawdź dostępne akcje
    cursor.execute("""
        SELECT ticker, SUM(quantity_open) as available
        FROM lots
        GROUP BY ticker
        HAVING SUM(quantity_open) > 0
    """)
    
    available_shares = cursor.fetchall()
    
    print(f"\n{Fore.GREEN}Status po naprawie:")
    print(f"  • Zablokowane LOT-y: {blocked_lots}")
    print(f"  • Otwarte CC: {open_cc_count} (rezerwują {total_cc_shares} akcji)")
    print(f"\n  Dostępne akcje:")
    for ticker, available in available_shares:
        print(f"    {ticker}: {available} akcji")
    
    conn.close()

def main():
    """GŁÓWNA FUNKCJA"""
    
    print(f"{Back.YELLOW}{Fore.BLACK} NARZĘDZIE DEBUG & FIX DLA COVERED CALLS {Style.RESET_ALL}")
    print(f"Baza danych: {DB_PATH}\n")
    
    while True:
        print(f"\n{Fore.CYAN}MENU:")
        print("1. 🔍 Diagnostyka (pokaż problemy)")
        print("2. 🔧 Napraw wszystko automatycznie")
        print("3. ✅ Weryfikuj stan po naprawie")
        print("4. 🚀 Pełny proces (diagnostyka → naprawa → weryfikacja)")
        print("0. Wyjście")
        
        choice = input(f"\n{Fore.YELLOW}Wybierz opcję: {Style.RESET_ALL}")
        
        if choice == '1':
            diagnose_all()
        elif choice == '2':
            confirm = input(f"{Fore.RED}Czy na pewno chcesz zastosować naprawy? (tak/nie): {Style.RESET_ALL}")
            if confirm.lower() in ['tak', 'yes', 't', 'y']:
                fix_all_problems()
        elif choice == '3':
            verify_fix()
        elif choice == '4':
            print(f"\n{Back.MAGENTA} PEŁNY PROCES NAPRAWCZY {Style.RESET_ALL}")
            diagnose_all()
            input(f"\n{Fore.YELLOW}Naciśnij Enter aby kontynuować z naprawą...{Style.RESET_ALL}")
            fix_all_problems()
            input(f"\n{Fore.YELLOW}Naciśnij Enter aby zweryfikować...{Style.RESET_ALL}")
            verify_fix()
        elif choice == '0':
            print(f"\n{Fore.GREEN}Do widzenia!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Nieprawidłowy wybór!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()