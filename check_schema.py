#!/usr/bin/env python3
"""
🔍 Sprawdź schemat bazy danych - debug tool
"""
import sqlite3

conn = sqlite3.connect('portfolio.db')
cursor = conn.cursor()

# Sprawdź wszystkie tabele
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("📋 SCHEMAT BAZY DANYCH:")
print("=" * 40)

for (table_name,) in tables:
    print(f"\n🗂️ TABELA: {table_name}")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    for col_id, col_name, col_type, not_null, default, primary_key in columns:
        pk = " (PK)" if primary_key else ""
        nn = " NOT NULL" if not_null else ""
        print(f"   {col_name}: {col_type}{nn}{pk}")

conn.close()