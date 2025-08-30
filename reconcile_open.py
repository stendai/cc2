#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rekonsyliacja lots.quantity_open dla podanego tickera:
  quantity_open = quantity_total - sprzedane_z_lota - zarezerwowane_przez_otwarte_CC

Źródło rezerwacji:
  - preferencyjnie: cc_lot_mappings (per-lot),
  - fallback: options_cc_reservations (per-lot),
  - jeśli obie tabele istnieją i cc_lot_mappings ma dane -> używamy TYLKO cc_lot_mappings (by nie dublować).

Użycie:
  python reconcile_open.py --ticker TICK [--db PATH_DO_SQLITE] [--dry-run] [--verbose]

Jeśli masz w projekcie db.py z get_connection(), możesz pominąć --db.
"""

import argparse
import os
import sys
import sqlite3

def table_exists(cur, name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
    return cur.fetchone() is not None

def get_conn(db_path: str | None):
    """
    1) jeśli jest importowalne db.get_connection() – użyj
    2) w przeciwnym razie wymagane --db
    """
    if db_path:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    # spróbuj importu lokalnego db.py
    try:
        sys.path.insert(0, os.getcwd())
        import db  # type: ignore
        conn = db.get_connection()
        if conn is None:
            raise RuntimeError("db.get_connection() zwróciło None")
        # upewnij się o row_factory
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass
        return conn
    except Exception as e:
        raise RuntimeError(f"Nie mogę uzyskać połączenia. Podaj --db PATH. Szczegóły: {e}")

def load_sold_per_lot(cur, ticker_upper: str) -> dict[int, int]:
    cur.execute("""
        SELECT sts.lot_id, COALESCE(SUM(sts.qty_from_lot),0) AS sold_qty
        FROM stock_trade_splits sts
        JOIN lots l ON l.id = sts.lot_id
        WHERE UPPER(l.ticker) = ?
        GROUP BY sts.lot_id
    """, (ticker_upper,))
    return {int(r[0]): int(r[1] or 0) for r in (cur.fetchall() or [])}

def load_reserved_per_lot(cur, ticker_upper: str) -> dict[int, int]:
    reserved = {}
    has_new = table_exists(cur, 'cc_lot_mappings')
    has_old = table_exists(cur, 'options_cc_reservations')

    # spróbuj nowej tabeli
    if has_new:
        cur.execute("""
            SELECT m.lot_id, COALESCE(SUM(m.shares_reserved),0) AS qty
            FROM cc_lot_mappings m
            JOIN options_cc cc ON cc.id = m.cc_id
            JOIN lots l ON l.id = m.lot_id
            WHERE cc.status='open'
              AND UPPER(cc.ticker)=?
              AND UPPER(l.ticker)=?
            GROUP BY m.lot_id
        """, (ticker_upper, ticker_upper))
        rows = cur.fetchall() or []
        reserved = {int(r[0]): int(r[1] or 0) for r in rows}
        if sum(reserved.values()) > 0:
            return reserved  # używamy wyłącznie nowej mapy, aby nie dublować

    # fallback do starej
    if has_old:
        cur.execute("""
            SELECT r.lot_id, COALESCE(SUM(r.qty_reserved),0) AS qty
            FROM options_cc_reservations r
            JOIN options_cc cc ON cc.id = r.cc_id
            JOIN lots l ON l.id = r.lot_id
            WHERE cc.status='open'
              AND UPPER(cc.ticker)=?
              AND UPPER(l.ticker)=?
            GROUP BY r.lot_id
        """, (ticker_upper, ticker_upper))
        rows = cur.fetchall() or []
        reserved = {int(r[0]): int(r[1] or 0) for r in rows}

    return reserved

def reconcile_ticker(conn: sqlite3.Connection, ticker: str, dry_run: bool, verbose: bool) -> int:
    cur = conn.cursor()
    t = str(ticker).upper().strip()

    # pobierz LOT-y tickera
    cur.execute("""
        SELECT id, quantity_total, quantity_open, buy_date
        FROM lots
        WHERE UPPER(ticker) = ?
        ORDER BY buy_date ASC, id ASC
    """, (t,))
    lots = cur.fetchall() or []
    if not lots:
        print(f"⚠️  Brak LOT-ów dla {t}")
        return 0

    sold_map = load_sold_per_lot(cur, t)
    reserved_map = load_reserved_per_lot(cur, t)

    total_before_open = 0
    total_after_open = 0
    updated_rows = 0

    # transakcja lokalna
    cur.execute("SAVEPOINT sp_reconcile")
    try:
        for r in lots:
            lot_id = int(r["id"])
            qty_total = int(r["quantity_total"] or 0)
            qty_open  = int(r["quantity_open"]  or 0)
            sold      = int(sold_map.get(lot_id, 0))
            reserved  = int(reserved_map.get(lot_id, 0))

            correct_open = qty_total - sold - reserved
            if correct_open < 0:
                correct_open = 0
            if correct_open > qty_total:
                correct_open = qty_total  # na wszelki wypadek

            total_before_open += qty_open
            total_after_open  += correct_open

            if verbose:
                print(f"LOT #{lot_id}: total={qty_total}, open={qty_open} -> calc_open={correct_open}  "
                      f"(sold={sold}, reserved={reserved})")

            if correct_open != qty_open and not dry_run:
                cur.execute(
                    "UPDATE lots SET quantity_open = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (int(correct_open), lot_id)
                )
                updated_rows += 1

        if dry_run:
            cur.execute("ROLLBACK TO SAVEPOINT sp_reconcile")
        cur.execute("RELEASE SAVEPOINT sp_reconcile")

        # podsumowanie
        print("\n📊 Podsumowanie rekonsyliacji")
        print(f"  Ticker:                {t}")
        print(f"  LOT-ów:                {len(lots)}")
        print(f"  SUMA open PRZED:       {total_before_open}")
        print(f"  SUMA open PO:          {total_after_open}")
        print(f"  Zaktualizowane LOT-y:  {updated_rows}" + (" (dry-run)" if dry_run else ""))

        # sanity-check z poziomu tickera: total - sold - reserved vs suma open
        cur.execute("SELECT COALESCE(SUM(quantity_total),0), COALESCE(SUM(quantity_open),0) FROM lots WHERE UPPER(ticker)=?", (t,))
        tot_after, open_after = cur.fetchone()
        sold_sum = sum(sold_map.values())
        reserved_sum = sum(reserved_map.values())
        expected_open = int(tot_after) - int(sold_sum) - int(reserved_sum)
        if expected_open < 0:
            expected_open = 0

        print("\n🧪 Walidacja:")
        print(f"  Suma quantity_total:   {int(tot_after)}")
        print(f"  Sprzedane (per-lot):   {int(sold_sum)}")
        print(f"  Zarezerwowane (open):  {int(reserved_sum)}")
        print(f"  Oczekiwane open:       {expected_open}")
        print(f"  Rzeczywiste open:      {int(open_after)}")
        if expected_open != int(open_after):
            print("  ⚠️  Rozjazd! Jeśli to dry-run, uruchom bez --dry-run. "
                  "Jeśli nie, sprawdź, czy rezerwacje nie występują w obu tabelach równocześnie.")

        return updated_rows

    except Exception as e:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT sp_reconcile")
            cur.execute("RELEASE SAVEPOINT sp_reconcile")
        except Exception:
            pass
        raise

def main():
    ap = argparse.ArgumentParser(description="Rekonsyliacja lots.quantity_open dla tickera")
    ap.add_argument("--ticker", required=True, help="Ticker (np. AAPL)")
    ap.add_argument("--db", help="Ścieżka do pliku SQLite (jeśli nie używasz db.py/get_connection())")
    ap.add_argument("--dry-run", action="store_true", help="Tylko pokaż co zostanie zmienione, bez zapisu")
    ap.add_argument("--verbose", action="store_true", help="Szczegółowe logi per LOT")
    args = ap.parse_args()

    try:
        conn = get_conn(args.db)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    try:
        updated = reconcile_ticker(conn, args.ticker, args.dry_run, args.verbose)
        if not args.dry_run:
            conn.commit()
        conn.close()
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        print(f"❌ Błąd rekonsyliacji: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
