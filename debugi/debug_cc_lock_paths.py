# debug_cc_lock_paths.py
# Cel: Zdiagnozować DLACZEGO lot nie wraca do quantity_open po buybacku.
# Tryb: READ-ONLY (nie zmienia danych).

import argparse, sqlite3
from typing import Dict, List, Optional

def conn_open(path:str)->sqlite3.Connection:
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    # tryb tylko do odczytu (o ile Python/OS pozwala) – nie wymagany, ale bezpieczny
    return c

def q_all(c, sql, params=()):
    return [dict(r) for r in c.execute(sql, params).fetchall()]

def q_one(c, sql, params=()):
    r = c.execute(sql, params).fetchone()
    return dict(r) if r else None

def banner(t:str):
    line = "="*max(60, len(t)+4)
    print(f"\n{line}\n  {t}\n{line}")

def print_table(rows:List[Dict], limit:int=100):
    if not rows: 
        print("(brak wierszy)"); 
        return
    cols = list(rows[0].keys())
    widths = {k: max(len(k), *(len(str(r.get(k,''))) for r in rows[:limit])) for k in cols}
    head = " | ".join(k.ljust(widths[k]) for k in cols)
    sep  = "-+-".join("-"*widths[k] for k in cols)
    print(head); print(sep)
    for r in rows[:limit]:
        print(" | ".join(str(r.get(k,'')).ljust(widths[k]) for k in cols))
    if len(rows)>limit:
        print(f"... ({len(rows)-limit} więcej)")

def table_exists(c, name:str)->bool:
    return q_one(c, "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", (name,)) is not None

def scan_one(c, ticker:Optional[str], cc_id:Optional[int]):
    # 0) sanity schema
    for t in ("lots","options_cc","options_cc_reservations","cc_lot_mappings"):
        print(f"{t:<26} {'TAK' if table_exists(c,t) else 'NIE'}")
    if not table_exists(c,"lots"):
        print("Brak lots – przerywam.")
        return

    # 1) wyznaczenie lotów i CC do analizy
    lots = []
    if ticker:
        lots = q_all(c, "SELECT * FROM lots WHERE ticker=? ORDER BY id;", (ticker,))
    elif cc_id is not None:
        # spróbuj od CC przejść do tickera
        cc = q_one(c, "SELECT * FROM options_cc WHERE id=?;", (cc_id,))
        if cc:
            ticker = cc.get("ticker")
            lots = q_all(c, "SELECT * FROM lots WHERE ticker=? ORDER BY id;", (ticker,))
        else:
            print("Nie znaleziono CC o podanym id.")
            return
    else:
        print("Podaj --ticker lub --cc-id.")
        return

    banner("LOTS (wejście)")
    print_table(lots)

    # 2) powiązane CC
    cc_rows = q_all(c, "SELECT * FROM options_cc WHERE ticker=? ORDER BY id DESC;", (ticker,))
    banner("OPTIONS_CC (powiązane z tickerem)")
    print_table(cc_rows)

    # 3) rezerwacje & mapowania
    res_rows = q_all(c, """
        SELECT r.*
        FROM options_cc_reservations r 
        JOIN lots l ON l.id=r.lot_id
        WHERE l.ticker=?
        ORDER BY r.id DESC;
    """, (ticker,)) if table_exists(c,"options_cc_reservations") else []
    banner("OPTIONS_CC_RESERVATIONS (dla tickera)")
    print_table(res_rows)

    map_rows = q_all(c, """
        SELECT m.*
        FROM cc_lot_mappings m
        JOIN lots l ON l.id=m.lot_id
        WHERE l.ticker=?
        ORDER BY m.id DESC;
    """, (ticker,)) if table_exists(c,"cc_lot_mappings") else []
    banner("CC_LOT_MAPPINGS (dla tickera)")
    print_table(map_rows)

    # 4) podsumowanie per lot: rezerwy/mappingi vs open
    banner("PODSUMOWANIE PER LOT (rezerwy/mappingi vs open)")
    for lot in lots:
        lot_id = lot["id"]
        total  = int(lot["quantity_total"])
        openq  = int(lot["quantity_open"])
        res_sum = q_one(c, "SELECT COALESCE(SUM(qty_reserved),0) s FROM options_cc_reservations WHERE lot_id=?;", (lot_id,))["s"] if table_exists(c,"options_cc_reservations") else 0
        map_sum = q_one(c, "SELECT COALESCE(SUM(shares_reserved),0) s FROM cc_lot_mappings WHERE lot_id=?;", (lot_id,))["s"] if table_exists(c,"cc_lot_mappings") else 0
        expected_open = max(total - res_sum - map_sum, 0)
        unexplained = (total - openq) - (res_sum + map_sum)
        print(f"LOT {lot_id:>4}  {lot['ticker']:<8} total={total:>4} open={openq:>4}  res={res_sum:>4} map={map_sum:>4}  expected_open={expected_open:>4}  "
              f"UNEXPLAINED_LOCK={unexplained:>4}")

    # 5) heurystyka błędów:
    banner("HEURYSTYKA DIAGNOZY")
    hints = []
    # a) lot_linked_id puste w CC zamkniętych — UI może nie wiedzieć, który lot odblokować (jeśli logika opierała się na tym polu)
    ll = q_all(c, """
        SELECT id, ticker, status, lot_linked_id, contracts, open_date, close_date
        FROM options_cc 
        WHERE ticker=? AND status IN ('bought_back','closed','expired','assigned','cancelled')
        ORDER BY id DESC;
    """, (ticker,))
    if ll and any(r["lot_linked_id"] is None for r in ll):
        hints.append("Zamknięte CC z NULL lot_linked_id → jeśli pipeline odblokowania opiera się na tym polu, to nie wie którego lotu dotyczy.")

    # b) brak rezerwacji i mapowań, a open < total → ghost lock (coś kiedyś zdekrementowało lots.quantity_open i nikt nie inkrementuje)
    for lot in lots:
        lot_id = lot["id"]
        total  = int(lot["quantity_total"]); openq=int(lot["quantity_open"])
        res_sum = q_one(c, "SELECT COALESCE(SUM(qty_reserved),0) s FROM options_cc_reservations WHERE lot_id=?;", (lot_id,))["s"] if table_exists(c,"options_cc_reservations") else 0
        map_sum = q_one(c, "SELECT COALESCE(SUM(shares_reserved),0) s FROM cc_lot_mappings WHERE lot_id=?;", (lot_id,))["s"] if table_exists(c,"cc_lot_mappings") else 0
        if res_sum==0 and map_sum==0 and openq < total:
            hints.append(f"LOT {lot_id}: brak aktywnych blokad (0), a open<{total}. Ktoś zdekrementował lots.quantity_open i nie cofa po buybacku.")

    if not hints:
        print("Brak oczywistych anomalii w danych – patrz sekcja TRIGGERY/SQL niżej (czy w ogóle istnieje ścieżka odblokowania).")
    else:
        for h in hints:
            print("•", h)

    # 6) TRIGGERY i definicje SQL dotykające quantity_open / rezerwacje / mappingi
    banner("TRIGGERY / DEFINICJE SQL zawierające 'lots' i 'quantity_open'")
    tr_lots = q_all(c, "SELECT name, type, tbl_name, sql FROM sqlite_master WHERE sql LIKE '%lots%' AND sql LIKE '%quantity_open%';")
    print_table(tr_lots, limit=50)

    banner("TRIGGERY zawierające 'options_cc_reservations' lub 'cc_lot_mappings'")
    tr_res = q_all(c, "SELECT name, type, tbl_name, sql FROM sqlite_master WHERE sql LIKE '%options_cc_reservations%';")
    tr_map = q_all(c, "SELECT name, type, tbl_name, sql FROM sqlite_master WHERE sql LIKE '%cc_lot_mappings%';")
    print_table(tr_res, limit=50)
    print_table(tr_map, limit=50)

    banner("WSZYSTKIE TRIGGERY w bazie")
    all_tr = q_all(c, "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger';")
    print_table(all_tr, limit=200)

    # 7) Czy istnieje VIEW/indeks/trigger z logiką 'po buybacku'
    banner("DEFINICJE SQL zawierające słowa kluczowe 'bought_back'/'close_date'")
    by_kw = q_all(c, "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE sql LIKE '%bought_back%' OR sql LIKE '%close_date%';")
    print_table(by_kw, limit=200)

def scan_all(c):
    banner("SKAN GLOBALNY: UNEXPLAINED_LOCK dla wszystkich lotów")
    lots = q_all(c, "SELECT * FROM lots ORDER BY ticker, id;")
    rows=[]
    for lot in lots:
        lot_id=lot["id"]; total=int(lot["quantity_total"]); openq=int(lot["quantity_open"])
        res_sum = q_one(c,"SELECT COALESCE(SUM(qty_reserved),0) s FROM options_cc_reservations WHERE lot_id=?;",(lot_id,))["s"] if table_exists(c,"options_cc_reservations") else 0
        map_sum = q_one(c,"SELECT COALESCE(SUM(shares_reserved),0) s FROM cc_lot_mappings WHERE lot_id=?;",(lot_id,))["s"] if table_exists(c,"cc_lot_mappings") else 0
        unexplained = (total-openq) - (res_sum+map_sum)
        rows.append({
            "lot_id": lot_id, "ticker": lot["ticker"],
            "total": total, "open": openq, "res": res_sum, "map": map_sum,
            "UNEXPLAINED_LOCK": unexplained
        })
    print_table(rows, limit=500)

def main():
    ap = argparse.ArgumentParser(description="Debug ścieżek blokady/odblokowania akcji po buybacku (bez zmian w DB).")
    ap.add_argument("--db", default="portfolio.db")
    ap.add_argument("--ticker", help="Ticker do wglądu")
    ap.add_argument("--cc-id", type=int, help="Konkretny CC-ID (alternatywa dla --ticker)")
    ap.add_argument("--scan-all", action="store_true", help="Pokaż UNEXPLAINED_LOCK dla wszystkich lotów")
    args = ap.parse_args()

    c = conn_open(args.db)

    banner("📋 PODSUMOWANIE TABEL")
    for t in ("lots","options_cc","options_cc_reservations","cc_lot_mappings"):
        print(f"{t:<26} {'TAK' if table_exists(c,t) else 'NIE'}")

    if args.scan_all:
        scan_all(c)

    if args.ticker or (args.cc-id if False else False):
        pass  # tylko by nie mylił edytor ;)
    if args.ticker or (args.cc_id is not None):
        banner("🔎 DIAGNOZA DLA WYBRANEGO OBIEKTU")
        scan_one(c, args.ticker, args.cc_id)
    elif not args.scan_all:
        banner("Jak używać")
        print("  python debug_cc_lock_paths.py --db portfolio.db --ticker BASIA")
        print("  python debug_cc_lock_paths.py --db portfolio.db --cc-id 6")
        print("  python debug_cc_lock_paths.py --db portfolio.db --scan-all")

if __name__ == "__main__":
    main()
