# reconcile_lots_open.py
# Autor: ChatGPT (dla Erwin/Mati)
# Wersja: 1.1 (solidniejsze wykrywanie kolumn; brak twardych domyślnych nazw)

import argparse
import sqlite3
from typing import List, Dict, Optional

def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", (name,)
    ).fetchone() is not None

def cols(conn, table: str) -> List[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table});").fetchall()]

def first_existing(all_cols: List[str], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in all_cols:
            return c
    return None  # <— żadnych domyślnych nazw, żeby nie walić w nieistniejące kolumny

def banner(t: str):
    line = "=" * max(50, len(t)+4)
    print(f"\n{line}\n  {t}\n{line}")

def print_rows(rows: List[Dict], limit: int = 200):
    if not rows:
        print("(brak wierszy)")
        return
    headers = list(rows[0].keys())
    widths = {h: max(len(h), *(len(str(r.get(h,""))) for r in rows[:limit])) for h in headers}
    head = " | ".join(h.ljust(widths[h]) for h in headers)
    sep  = "-+-".join("-"*widths[h] for h in headers)
    print(head); print(sep)
    for r in rows[:limit]:
        print(" | ".join(str(r.get(h,"")).ljust(widths[h]) for h in headers))
    if len(rows) > limit:
        print(f"... ({len(rows)-limit} więcej)")

class Hints:
    def __init__(self, conn: sqlite3.Connection, verbose: bool=False):
        self.has_lots  = table_exists(conn, "lots")
        self.has_res   = table_exists(conn, "options_cc_reservations")
        self.has_map   = table_exists(conn, "cc_lot_mappings")
        if not self.has_lots:
            raise RuntimeError("Brak tabeli 'lots' — nie ma czego rekoncyliować.")

        self.lots_cols = cols(conn, "lots")
        self.res_cols  = cols(conn, "options_cc_reservations") if self.has_res else []
        self.map_cols  = cols(conn, "cc_lot_mappings") if self.has_map else []

        # lots
        self.lot_id     = first_existing(self.lots_cols, ["id","lot_id"])
        self.lot_ticker = first_existing(self.lots_cols, ["ticker","symbol"])
        self.lot_total  = first_existing(self.lots_cols, ["quantity_total","qty_total","qty"])
        self.lot_open   = first_existing(self.lots_cols, ["quantity_open","qty_open","open_qty"])

        # reservations (aktywnosc + ilość)
        self.res_lot_id = first_existing(self.res_cols, ["lot_id","lotid"])
        self.res_qty    = first_existing(self.res_cols, ["quantity","qty","shares","quantity_reserved"])
        self.res_is_active = first_existing(self.res_cols, ["is_active","active"])
        self.res_released  = first_existing(self.res_cols, ["released","is_released"])
        self.res_rel_at    = first_existing(self.res_cols, ["released_at","unreserved_at","unlock_time"])

        # mappings (aktywnosc + ilość)
        self.map_lot_id    = first_existing(self.map_cols, ["lot_id","lotid"])
        self.map_qty       = first_existing(self.map_cols, ["shares","shares_reserved","qty","quantity"])
        self.map_is_active = first_existing(self.map_cols, ["is_active","active","enabled"])
        self.map_released  = first_existing(self.map_cols, ["released","is_released"])
        self.map_rel_at    = first_existing(self.map_cols, ["released_at","unreserved_at","unlock_time"])

        self.verbose = verbose

        # minimalne sanity-checki
        for name, val in [
            ("lots.lot_id", self.lot_id),
            ("lots.ticker", self.lot_ticker),
            ("lots.quantity_total", self.lot_total),
            ("lots.quantity_open", self.lot_open),
        ]:
            if not val:
                raise RuntimeError(f"Brak wymaganej kolumny: {name} (sprawdź schemat).")

    def res_active_pred(self) -> Optional[str]:
        terms = []
        if self.res_is_active: terms.append(f"{self.res_is_active}=1")
        if self.res_released:  terms.append(f"{self.res_released}=0")
        if self.res_rel_at:    terms.append(f"{self.res_rel_at} IS NULL")
        if terms:
            return " AND ".join(terms)
        # brak jakichkolwiek flag — przyjmijmy, że WSZYSTKIE wpisy są aktywne (ostrożnie)
        return "1=1"

    def map_active_pred(self) -> Optional[str]:
        terms = []
        if self.map_is_active: terms.append(f"{self.map_is_active}=1")
        if self.map_released:  terms.append(f"{self.map_released}=0")
        if self.map_rel_at:    terms.append(f"{self.map_rel_at} IS NULL")
        if terms:
            return " AND ".join(terms)
        return "1=1"

    def dump(self):
        print("DETEKCJA KOLUMN:")
        print("  lots:", self.lots_cols)
        print("    lot_id:", self.lot_id, " ticker:", self.lot_ticker, " total:", self.lot_total, " open:", self.lot_open)
        print("  options_cc_reservations:", self.res_cols if self.has_res else "(brak tabeli)")
        print("    lot_id:", self.res_lot_id, " qty:", self.res_qty, " flags:", [self.res_is_active, self.res_released, self.res_rel_at])
        print("  cc_lot_mappings:", self.map_cols if self.has_map else "(brak tabeli)")
        print("    lot_id:", self.map_lot_id, " qty:", self.map_qty, " flags:", [self.map_is_active, self.map_released, self.map_rel_at])

def load_lots(conn, h: Hints, ticker: Optional[str]=None) -> List[Dict]:
    if ticker:
        sql = f"SELECT * FROM lots WHERE {h.lot_ticker}=? ORDER BY {h.lot_id};"
        return [dict(r) for r in conn.execute(sql, (ticker,)).fetchall()]
    else:
        sql = f"SELECT * FROM lots ORDER BY {h.lot_ticker}, {h.lot_id};"
        return [dict(r) for r in conn.execute(sql).fetchall()]

def active_reserved_sum(conn, h: Hints, lot_id: int) -> int:
    # jeśli brak tabeli lub brak wymaganych kolumn — traktujemy jako 0
    if not h.has_res or not h.res_lot_id or not h.res_qty:
        return 0
    pred = h.res_active_pred() or "1=1"
    sql = f"""
        SELECT COALESCE(SUM(COALESCE({h.res_qty},0)),0) AS s
        FROM options_cc_reservations
        WHERE {h.res_lot_id}=?
          AND {pred}
    """
    return int(conn.execute(sql, (lot_id,)).fetchone()["s"])

def active_mapped_sum(conn, h: Hints, lot_id: int) -> int:
    if not h.has_map or not h.map_lot_id or not h.map_qty:
        return 0
    pred = h.map_active_pred() or "1=1"
    sql = f"""
        SELECT COALESCE(SUM(COALESCE({h.map_qty},0)),0) AS s
        FROM cc_lot_mappings
        WHERE {h.map_lot_id}=?
          AND {pred}
    """
    return int(conn.execute(sql, (lot_id,)).fetchone()["s"])

def scan(conn, h: Hints, ticker: Optional[str]) -> Dict[str, List[Dict]]:
    out = {
        "ok": [],
        "off_by": [],          # expected_open != quantity_open
        "ghost_lock": [],      # brak blokad, a open < total
    }
    rows = load_lots(conn, h, ticker)
    for r in rows:
        lot_id = r[h.lot_id]
        qty_total = int(r.get(h.lot_total, 0) or 0)
        qty_open  = int(r.get(h.lot_open, 0) or 0)
        res = active_reserved_sum(conn, h, lot_id)
        mp  = active_mapped_sum(conn, h, lot_id)
        expected_open = max(qty_total - res - mp, 0)

        rec = {
            "lot_id": lot_id,
            "ticker": r.get(h.lot_ticker),
            "quantity_total": qty_total,
            "quantity_open": qty_open,
            "reserved_active": res,
            "mapped_active": mp,
            "expected_open": expected_open,
            "delta_open": expected_open - qty_open,
        }

        if expected_open != qty_open:
            out["off_by"].append(rec)
            if res == 0 and mp == 0 and qty_open < qty_total:
                out["ghost_lock"].append(rec)
        else:
            out["ok"].append(rec)
    return out

def do_fix(conn, h: Hints, rows: List[Dict], dry_run: bool):
    if not rows:
        print("Brak rozjazdów do poprawy.")
        return
    banner("PLAN ZMIAN")
    for r in rows:
        print(f"LOT {r['lot_id']} {r['ticker']}: open {_]()
