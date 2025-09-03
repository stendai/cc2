# fix_trade_fx.py
# Naprawa kursu NBP (D-1) i przeliczeń dla stock_trades.id = 1
# - pobiera sell_date, quantity, sell_price_usd, broker/reg fee
# - wylicza net_proceeds_usd
# - pobiera kurs NBP D-1 (db.get_fx_rate_for_date -> fallback db.get_latest_fx_rate)
# - aktualizuje fx_rate, proceeds_pln, pl_pln

import sqlite3
from datetime import datetime, timedelta
import db  # Twój moduł z get_connection(), get_fx_rate_for_date(), get_latest_fx_rate()

TRADE_ID = 1  # <<< tylko ten rekord

def _to_iso(d):
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d")
    # spróbuj różne popularne formaty
    s = str(d)
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    # ostatnia próba: obetnij do 10 znaków
    return s[:10]

def _nbp_d_minus_1(date_str: str):
    """Zwraca (rate_float, date_used_str) lub (None, None)."""
    # 1) wspólna funkcja (obsługuje NBP + cache w fx_rates)
    rate = db.get_fx_rate_for_date(date_str)
    if rate:
        d1 = datetime.strptime(date_str, "%Y-%m-%d").date() - timedelta(days=1)
        return float(rate), d1.isoformat()
    # 2) fallback na fx_rates <= D-1
    d1 = datetime.strptime(date_str, "%Y-%m-%d").date() - timedelta(days=1)
    latest = db.get_latest_fx_rate("USD", before_date=d1)
    if latest:
        return float(latest["rate"]), str(latest["date"])
    return None, None

def _nz(x, default=0.0):
    return default if x is None else float(x)

def fix_trade_fx(trade_id: int = TRADE_ID):
    conn = db.get_connection()
    if not conn:
        raise RuntimeError("Brak połączenia z bazą")

    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1) Pobierz rekord
        cur.execute("""
            SELECT id, ticker, quantity, sell_price_usd, sell_date,
                   fx_rate, broker_fee_usd, reg_fee_usd,
                   proceeds_pln, cost_pln, pl_pln
            FROM stock_trades
            WHERE id = ?
        """, (trade_id,))
        row = cur.fetchone()
        if not row:
            print(f"Brak rekordu stock_trades.id={trade_id}")
            return

        before = dict(row)
        sell_date_iso = _to_iso(row["sell_date"])
        quantity = int(row["quantity"] or 0)
        sell_price = _nz(row["sell_price_usd"])
        broker_fee = _nz(row["broker_fee_usd"])
        reg_fee = _nz(row["reg_fee_usd"])
        cost_pln = _nz(row["cost_pln"])

        # 2) Net proceeds USD
        gross_usd = quantity * sell_price
        net_proceeds_usd = gross_usd - broker_fee - reg_fee

        # 3) Kurs NBP D-1
        fx_rate, fx_used_date = _nbp_d_minus_1(sell_date_iso)
        if fx_rate is None:
            raise RuntimeError(f"Brak kursu NBP D-1 dla {sell_date_iso} (ani fallbacku w fx_rates)")

        # 4) PLN przeliczenia
        proceeds_pln = net_proceeds_usd * fx_rate
        pl_pln = proceeds_pln - cost_pln

        # 5) Aktualizacja
        cur.execute("""
            UPDATE stock_trades
               SET fx_rate = ?,
                   proceeds_pln = ?,
                   pl_pln = ?
             WHERE id = ?
        """, (fx_rate, proceeds_pln, pl_pln, trade_id))
        conn.commit()

        # 6) Podgląd po zmianie
        cur.execute("""
            SELECT id, ticker, quantity, sell_price_usd, sell_date,
                   fx_rate, broker_fee_usd, reg_fee_usd,
                   proceeds_pln, cost_pln, pl_pln
            FROM stock_trades
            WHERE id = ?
        """, (trade_id,))
        after = dict(cur.fetchone())

        print("=== stock_trades fix (id={}) ===".format(trade_id))
        print("Before:", before)
        print("After :", after)
        print(f"NBP D-1 użyty: {fx_used_date} @ {fx_rate:.4f}")
        print("OK.")

    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    fix_trade_fx()
