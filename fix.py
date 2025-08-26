import sqlite3

conn = sqlite3.connect('portfolio.db')
cursor = conn.cursor()

# Wylicz poprawne pl_pln dla CC #5
cursor.execute("UPDATE options_cc SET pl_pln = premium_sell_pln - premium_buyback_pln WHERE id = 4")
conn.commit()
conn.close()
print("✅ CC #5 naprawione!")