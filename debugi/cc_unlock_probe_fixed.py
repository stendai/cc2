# cc_unlock_probe_fixed.py
# Instrumentacja DEBUG dla ścieżki buyback→odblokowanie lotów (READ-ONLY poza logowaniem).
# Funkcje:
#   --install   : tworzy tabelę debug_log i triggery logujące zmiany
#   --uninstall : usuwa triggery debugujące (tabela debug_log zostaje)
#   --show      : pokazuje logi (filtr: --cc-id i/lub --ticker)
#
# Przykłady:
#   python cc_unlock_probe_fixed.py --db portfolio.db --install
#   # wykonaj BUYBACK w aplikacji
#   python cc_unlock_probe_fixed.py --db portfolio.db --show --ticker BASIA
#   python cc_unlock_probe_fixed.py --db portfolio.db --show --cc-id 5
#   python cc_unlock_probe_fixed.py --db portfolio.db --uninstall

import argparse
import sqlite3

DDL_TRIGGERS = [
# 1) tabela logów
("""
CREATE TABLE IF NOT EXISTS debug_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT DEFAULT (datetime('now')),
  event TEXT,
  table_name TEXT,
  cc_id INTEGER,
  lot_id INTEGER,
  qty INTEGER,
  old_status TEXT,
  new_status TEXT,
  note TEXT
);
""","create_log_table"),

# 2) log: zmiana statusu CC (np. → bought_back)
("""
CREATE TRIGGER IF NOT EXISTS dbg_cc_status_update
AFTER UPDATE OF status ON options_cc
BEGIN
  INSERT INTO debug_log(event,table_name,cc_id,lot_id,old_status,new_status,note)
  VALUES('cc_status_update','options_cc',NEW.id,NEW.lot_linked_id,OLD.status,NEW.status,'status changed');
END;
""","dbg_cc_status_update"),

# 3) log: INSERT rezerwacji
("""
CREATE TRIGGER IF NOT EXISTS dbg_res_insert
AFTER INSERT ON options_cc_reservations
BEGIN
  INSERT INTO debug_log(event,table_name,cc_id,lot_id,qty,note)
  VALUES('res_insert','options_cc_reservations',NEW.cc_id,NEW.lot_id,NEW.qty_reserved,'reserve');
END;
""","dbg_res_insert"),

# 4) log: DELETE rezerwacji (np. trigger release po buybacku)
("""
CREATE TRIGGER IF NOT EXISTS dbg_res_delete
AFTER DELETE ON options_cc_reservations
BEGIN
  INSERT INTO debug_log(event,table_name,cc_id,lot_id,qty,note)
  VALUES('res_delete','options_cc_reservations',OLD.cc_id,OLD.lot_id,OLD.qty_reserved,'release');
END;
""","dbg_res_delete"),

# 5) log: INSERT mapowania cc_lot_mappings
("""
CREATE TRIGGER IF NOT EXISTS dbg_map_insert
AFTER INSERT ON cc_lot_mappings
BEGIN
  INSERT INTO debug_log(event,table_name,cc_id,lot_id,qty,note)
  VALUES('map_insert','cc_lot_mappings',NEW.cc_id,NEW.lot_id,NEW.shares_reserved,'map');
END;
""","dbg_map_insert"),

# 6) log: DELETE mapowania cc_lot_mappings
("""
CREATE TRIGGER IF NOT EXISTS dbg_map_delete
AFTER DELETE ON cc_lot_mappings
BEGIN
  INSERT INTO debug_log(event,table_name,cc_id,lot_id,qty,note)
  VALUES('map_delete','cc_lot_mappings',OLD.cc_id,OLD.lot_id,OLD.shares_reserved,'unmap');
END;
""","dbg_map_delete"),

# 7) log: UPDATE lots.quantity_open (krytyczne do wykrycia braku inkrementu po buybacku)
("""
CREATE TRIGGER IF NOT EXISTS dbg_lots_open_update
AFTER UPDATE OF quantity_open ON lots
BEGIN
  INSERT INTO debug_log(event,table_name,cc_id,lot_id,qty,note)
  VALUES('lots_open_update','lots',NULL,NEW.id,(NEW.quantity_open-OLD.quantity_open),'open changed');
END;
""","dbg_lots_open_update"),
]

DROP_TRIGGERS = [
  "dbg_cc_status_update",
  "dbg_res_insert",
  "dbg_res_delete",
  "dbg_map_insert",
  "dbg_map_delete",
  "dbg_lots_open_update",
]

def connect(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c

def install(c: sqlite3.Connection):
    cur = c.cursor()
    for sql, _name in DDL_TRIGGERS:
        cur.execute(sql)
    c.commit()
    print("✅ Zainstalowano triggery debugujące i tabelę debug_log.")

def uninstall(c: sqlite3.Connection):
    cur = c.cursor()
    for name in DROP_TRIGGERS:
        cur.execute(f"DROP TRIGGER IF EXISTS {name};")
    c.commit()
    print("🧹 Usunięto triggery debugujące (debug_log pozostaje).")

def fetchall(c: sqlite3.Connection, sql: str, params=()):
    return [dict(r) for r in c.execute(sql, params).fetchall()]

def show(c: sqlite3.Connection, cc_id: int=None, ticker: str=None, limit: int=200):
    where = []
    params = []

    if cc_id is not None:
        where.append("cc_id = ?")
        params.append(cc_id)

    if ticker:
        # dopasuj zdarzenia po lotach danego tickera ORAZ po cc-ach danego tickera
        # (bo log cc_status_update może mieć lot_linked_id = NULL)
        where.append("""
            (
               (lot_id IS NOT NULL AND lot_id IN (SELECT id FROM lots WHERE UPPER(ticker)=UPPER(?)))
               OR
               (cc_id IS NOT NULL  AND cc_id  IN (SELECT id FROM options_cc WHERE UPPER(ticker)=UPPER(?)))
            )
        """)
        params.extend([ticker, ticker])

    sql = "SELECT * FROM debug_log"
    if where:
        sql += " WHERE " + " AND ".join(f"({w})" for w in where)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = fetchall(c, sql, params)
    if not rows:
        print("(brak logów)")
        return

    headers = list(rows[0].keys())
    widths = {h: max(len(h), *(len(str(r.get(h,""))) for r in rows)) for h in headers}
    print(" | ".join(h.ljust(widths[h]) for h in headers))
    print("-+-".join("-"*widths[h] for h in headers))
    for r in rows:
        print(" | ".join(str(r.get(h,"")).ljust(widths[h]) for h in headers))

def main():
    ap = argparse.ArgumentParser(description="DEBUG: ścieżka buyback→release (logi z triggerów).")
    ap.add_argument("--db", default="portfolio.db")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--cc-id", type=int, help="Filtruj logi po konkretnym CC-ID")
    ap.add_argument("--ticker", help="Filtruj logi po tickerze (opiera się na lots/options_cc)")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    c = connect(args.db)

    if args.install:
        install(c)
    if args.uninstall:
        uninstall(c)
    if args.show:
        show(c, cc_id=args.cc_id, ticker=args.ticker, limit=args.limit)

    if not any([args.install, args.uninstall, args.show]):
        print("Użycie:")
        print("  python cc_unlock_probe_fixed.py --db portfolio.db --install")
        print("  # wykonaj BUYBACK w aplikacji")
        print("  python cc_unlock_probe_fixed.py --db portfolio.db --show --ticker BASIA")
        print("  python cc_unlock_probe_fixed.py --db portfolio.db --show --cc-id 5")
        print("  python cc_unlock_probe_fixed.py --db portfolio.db --uninstall")

if __name__ == "__main__":
    main()
