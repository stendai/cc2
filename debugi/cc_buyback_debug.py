# cc_buyback_debug.py
# READ-ONLY diagnostyka post-buyback dla jednego CC:
#  - sprawdza lot_linked_id, rezerwacje, mapowania, stan lots (open vs total),
#  - wykrywa brakujący krok "increment lots.quantity_open",
#  - podaje JEDNOZNACZNĄ PRZYCZYNĘ awarii (root cause) i dowód z danych.
#
# Użycie:
#   python cc_buyback_debug.py --db portfolio.db --cc-id 8

import argparse
import sqlite3

def conn(db):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    return c

def one(c, sql, params=()):
    r = c.execute(sql, params).fetchone()
    return dict(r) if r else None

def all_rows(c, sql, params=()):
    return [dict(r) for r in c.execute(sql, params).fetchall()]

def banner(t):
    line = "="*max(60, len(t)+4)
    print(f"\n{line}\n  {t}\n{line}")

def table_exists(c, name):
    return one(c, "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", (name,)) is not None

def print_kv(k, v):
    print(f"{k:<30} {v}")

def main():
    ap = argparse.ArgumentParser(description="Debug post-buyback dla jednego CC (bez modyfikacji danych).")
    ap.add_argument("--db", default="portfolio.db")
    ap.add_argument("--cc-id", type=int, required=True)
    args = ap.parse_args()

    c = conn(args.db)

    # sanity
    for t in ("options_cc","options_cc_reservations","cc_lot_mappings","lots"):
        print_kv(f"TABLE {t}", "TAK" if table_exists(c,t) else "NIE")

    cc = one(c, "SELECT * FROM options_cc WHERE id=?;", (args.cc_id,))
    if not cc:
        print("\nCC nie znaleziony.")
        return

    banner("CC (wybrany)")
    for k in cc.keys():
        print_kv(k, cc[k])

    ticker = cc["ticker"]
    lot_linked_id = cc["lot_linked_id"]
    contracts = int(cc["contracts"])
    status = cc["status"]

    # stan rezerwacji i mapowań powiązanych z CC
    res_sum_cc = one(c, "SELECT COALESCE(SUM(qty_reserved),0) s FROM options_cc_reservations WHERE cc_id=?;", (args.cc_id,))["s"]
    maps_rows = all_rows(c, "SELECT * FROM cc_lot_mappings WHERE cc_id=?;", (args.cc_id,))
    map_sum_cc = sum(int(r["shares_reserved"]) for r in maps_rows) if maps_rows else 0

    banner("REZERWACJE / MAPOWANIA CC")
    print_kv("reservations_sum_for_cc", res_sum_cc)
    print_kv("mappings_rows_for_cc", len(maps_rows))
    print_kv("mappings_shares_sum_for_cc", map_sum_cc)

    # jeśli lot_linked_id jest znane, policz stan tego lota
    if lot_linked_id is not None:
        lot = one(c, "SELECT * FROM lots WHERE id=?;", (lot_linked_id,))
    else:
        lot = None

    banner("LOT LINKED")
    print_kv("lot_linked_id", lot_linked_id if lot_linked_id is not None else "NULL")
    if lot:
        for k in ("id","ticker","quantity_total","quantity_open"):
            print_kv(k, lot[k])
    else:
        print("(brak powiązanego lota po id)")

    # policz oczekiwane OPEN oraz UNEXPLAINED_LOCK dla wszystkich lotów TICKERA (gdy brak lot_linked_id)
    lots_same_ticker = all_rows(c, "SELECT * FROM lots WHERE ticker=? ORDER BY id;", (ticker,))
    banner("PODSUMOWANIE LOTÓW TICKERA")
    for L in lots_same_ticker:
        total = int(L["quantity_total"]); openq = int(L["quantity_open"])
        res_sum = one(c, "SELECT COALESCE(SUM(qty_reserved),0) s FROM options_cc_reservations WHERE lot_id=?;", (L["id"],))["s"]
        map_sum = one(c, "SELECT COALESCE(SUM(shares_reserved),0) s FROM cc_lot_mappings WHERE lot_id=?;", (L["id"],))["s"]
        unexplained = (total - openq) - (res_sum + map_sum)
        print_kv(f"LOT {L['id']} total={total} open={openq} res={res_sum} map={map_sum}", f"UNEXPLAINED_LOCK={unexplained}")

    # WNIOSKI (deterministyczne)
    banner("WNIOSKI (root cause)")

    # 1) status powinien być 'bought_back' (lub inny zamykający), a rezerwacje dla CC wyzerowane
    closing_statuses = {"bought_back","expired","assigned","closed","cancelled"}
    if status not in closing_statuses:
        print("❌ CC nie ma statusu zamkniętego → buyback nie został poprawnie domknięty.")
        return
    if int(res_sum_cc) != 0:
        print("❌ Rezerwacje dla tego CC nie zostały zwolnione (sum(qty_reserved) > 0).")
        return
    print("✅ Rezerwacje dla CC wyzerowane po buybacku.")

    # 2) brak jakiegokolwiek mechanizmu podbijającego lots.quantity_open
    #    (wiemy z wcześniejszego uruchomienia probe, ale tu dowodzimy danymi)
    #    Szukamy "ghost locków" w lotach tego tickera.
    ghost_locks = []
    for L in lots_same_ticker:
        total = int(L["quantity_total"]); openq = int(L["quantity_open"])
        res_sum = one(c, "SELECT COALESCE(SUM(qty_reserved),0) s FROM options_cc_reservations WHERE lot_id=?;", (L["id"],))["s"]
        map_sum = one(c, "SELECT COALESCE(SUM(shares_reserved),0) s FROM cc_lot_mappings WHERE lot_id=?;", (L["id"],))["s"]
        if int(res_sum)==0 and int(map_sum)==0 and openq < total:
            ghost_locks.append(L["id"])

    if ghost_locks:
        print(f"❗ Wykryto GHOST-LOCK na lotach: {ghost_locks} — open < total przy zerowych blokadach (rezerwacje/mapowania=0).")
        if lot_linked_id is None:
            print("⛔ root cause A: lot_linked_id = NULL → aplikacyjna ścieżka 'release' najpewniej jest pomijana.")
        else:
            print("⛔ root cause B: brak kroku, który inkrementuje lots.quantity_open po zwolnieniu rezerwacji.")
    else:
        print("✅ Brak ghost-locków na lotach tego tickera (open==expected_open).")

    # 3) jeżeli lot_linked_id jest NULL, wskaż najbardziej prawdopodobny lot kandydujący (heurystyka)
    if lot_linked_id is None:
        # heurystyka: weź najmłodszy lot z tickerem (albo jedyny) – tu po prostu pokażemy listę
        print("\n🔍 lot_linked_id = NULL ⇒ brak kotwicy. Kandydaci (wg ticker):")
        for L in lots_same_ticker:
            total = int(L["quantity_total"]); openq = int(L["quantity_open"])
            print(f"  • lot_id={L['id']} total={total} open={openq} buy_date={L['buy_date']}")

    # 4) sprawdź, czy w bazie istnieje *jakikolwiek* trigger dotykający lots.quantity_open
    trig = all_rows(c, "SELECT name, tbl_name FROM sqlite_master WHERE type='trigger' AND sql LIKE '%lots%' AND sql LIKE '%quantity_open%';")
    if not trig:
        print("\nℹ️ W DB brak mechanizmu, który mógłby zaktualizować lots.quantity_open (zero triggerów dotykających tego pola).")
        print("   To potwierdza, że krok 'release → increment open' musi być wykonany w kodzie aplikacji.")
    else:
        print("\nℹ️ W DB istnieją triggery dotykające quantity_open (sprawdź kolejność/warunki):")
        for t in trig:
            print(f"   - {t['name']} ON {t['tbl_name']}")

    # 5) krótkie podsumowanie przyczyn w 1-linii
    print("\n=== SUMMARY ===")
    if lot_linked_id is None:
        print("ROOT CAUSE: lot_linked_id=NULL oraz brak triggera/ścieżki aplikacyjnej podbijającej lots.quantity_open po buybacku.")
    else:
        print("ROOT CAUSE: brak kroku (trigger/kod) podbijającego lots.quantity_open po buybacku, mimo zwolnienia rezerwacji.")

if __name__ == "__main__":
    main()
