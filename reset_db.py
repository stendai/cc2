#!/usr/bin/env python3
"""
🗑️ PEŁNY RESET BAZY DANYCH PORTFOLIO.DB
Usuwa wszystkie rekordy z zachowaniem struktury tabel i resetem AUTO_INCREMENT

UŻYCIE: python reset_database.py
"""

import sqlite3
import os
from datetime import datetime

# Konfiguracja
DB_PATH = "portfolio.db"

def get_all_tables(conn):
    """Pobiera wszystkie tabele z bazy danych (z wyjątkiem systemowych)"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [row[0] for row in cursor.fetchall()]

def reset_database():
    """
    Pełny reset bazy danych:
    1. Usuwa wszystkie rekordy ze wszystkich tabel
    2. Resetuje AUTO_INCREMENT (sekwencje ID)
    3. Zachowuje strukturę tabel
    """
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Baza danych {DB_PATH} nie istnieje!")
        return False
    
    # Backup nazwy pliku z timestampem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"portfolio_backup_{timestamp}.db"
    
    try:
        # 1. KOPIA ZAPASOWA
        print(f"📋 Tworzę kopię zapasową: {backup_path}")
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Kopia zapasowa utworzona pomyślnie")
        
        # 2. POŁĄCZENIE Z BAZĄ
        print(f"🔌 Łączę z bazą danych: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 3. POBRANIE LISTY TABEL
        tables = get_all_tables(conn)
        print(f"📊 Znalezione tabele ({len(tables)}): {', '.join(tables)}")
        
        if not tables:
            print("⚠️  Brak tabel do wyczyszczenia")
            conn.close()
            return True
        
        # 4. WYŁĄCZENIE FOREIGN KEY CONSTRAINTS (na czas czyszczenia)
        print("🔓 Wyłączam Foreign Key constraints...")
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # 5. ROZPOCZĘCIE TRANSAKCJI
        cursor.execute("BEGIN TRANSACTION")
        
        deleted_records = {}
        
        # 6. USUNIĘCIE REKORDÓW Z KAŻDEJ TABELI
        print("\n🗑️  USUWANIE REKORDÓW:")
        for table in tables:
            try:
                # Sprawdź ile rekordów przed usunięciem
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_before = cursor.fetchone()[0]
                
                # Usuń wszystkie rekordy
                cursor.execute(f"DELETE FROM {table}")
                deleted_count = cursor.rowcount
                
                deleted_records[table] = count_before
                print(f"   ✅ {table}: usunięto {count_before} rekordów")
                
            except Exception as e:
                print(f"   ❌ Błąd usuwania z tabeli {table}: {e}")
                cursor.execute("ROLLBACK")
                conn.close()
                return False
        
        # 7. RESET AUTO_INCREMENT SEQUENCES
        print("\n🔄 RESETOWANIE AUTO_INCREMENT:")
        for table in tables:
            try:
                # Resetuj sekwencję ID dla każdej tabeli
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name=?", (table,))
                print(f"   ✅ {table}: sekwencja ID zresetowana")
                
            except Exception as e:
                # Może nie być sqlite_sequence dla niektórych tabel - to OK
                print(f"   ⚠️  {table}: {e}")
        
        # 8. ZATWIERDZENIE TRANSAKCJI
        cursor.execute("COMMIT")
        
        # 9. VAKUUM - optymalizacja bazy po usunięciu (PO transakcji)
        print("\n🧹 Optymalizacja bazy danych (VACUUM)...")
        cursor.execute("VACUUM")
        
        # 10. WŁĄCZENIE Z POWROTEM FOREIGN KEY CONSTRAINTS
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # 11. WERYFIKACJA - sprawdź czy wszystko puste
        print("\n✅ WERYFIKACJA RESETU:")
        total_records_after = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_records_after += count
            if count > 0:
                print(f"   ⚠️  {table}: {count} rekordów (NIEPEŁNY RESET!)")
            else:
                print(f"   ✅ {table}: 0 rekordów")
        
        conn.close()
        
        # 12. PODSUMOWANIE
        total_deleted = sum(deleted_records.values())
        print(f"\n🎯 PODSUMOWANIE RESETU:")
        print(f"   📊 Usunięto łącznie: {total_deleted} rekordów")
        print(f"   📊 Pozostało łącznie: {total_records_after} rekordów")
        print(f"   📋 Kopia zapasowa: {backup_path}")
        
        if total_records_after == 0:
            print(f"   🏆 RESET KOMPLETNY - baza całkowicie wyczyszczona!")
            return True
        else:
            print(f"   ⚠️  RESET NIEPEŁNY - sprawdź logi błędów")
            return False
            
    except Exception as e:
        print(f"❌ KRYTYCZNY BŁĄD: {e}")
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

def verify_reset():
    """Weryfikuje czy reset się powiódł"""
    try:
        conn = sqlite3.connect(DB_PATH)
        tables = get_all_tables(conn)
        
        print(f"\n🔍 WERYFIKACJA PO RESECIE:")
        total_records = 0
        
        for table in tables:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_records += count
            print(f"   {table}: {count} rekordów")
        
        conn.close()
        
        if total_records == 0:
            print(f"✅ WERYFIKACJA PRZESZŁA - baza jest pusta!")
        else:
            print(f"❌ WERYFIKACJA NIE PRZESZŁA - {total_records} rekordów pozostało")
        
        return total_records == 0
        
    except Exception as e:
        print(f"❌ Błąd weryfikacji: {e}")
        return False

def main():
    """Główna funkcja resetu"""
    print("="*60)
    print("🗑️  PEŁNY RESET BAZY DANYCH PORTFOLIO.DB")
    print("="*60)
    
    # Potwierdzenie użytkownika
    print(f"\n⚠️  UWAGA: Ta operacja:")
    print(f"   • Usuwa WSZYSTKIE rekordy ze WSZYSTKICH tabel")
    print(f"   • Resetuje numery ID (AUTO_INCREMENT)")
    print(f"   • Zachowuje strukturę tabel")
    print(f"   • Tworzy automatyczną kopię zapasową")
    
    response = input(f"\n❓ Czy na pewno chcesz zresetować bazę {DB_PATH}? (tak/nie): ").lower().strip()
    
    if response not in ['tak', 'yes', 'y']:
        print("❌ Reset anulowany przez użytkownika")
        return
    
    # Wykonanie resetu
    print(f"\n🚀 Rozpoczynam reset bazy danych...")
    success = reset_database()
    
    if success:
        print(f"\n🎉 RESET ZAKOŃCZONY POMYŚLNIE!")
        
        # Dodatkowa weryfikacja
        verify_reset()
        
        print(f"\n💡 NASTĘPNE KROKI:")
        print(f"   1. Uruchom aplikację: streamlit run app.py")
        print(f"   2. Sprawdź czy ID-ki rozpoczynają się od 1")
        print(f"   3. Dodaj pierwsze rekordy testowe")
        
    else:
        print(f"\n💥 RESET NIE POWIÓDŁ SIĘ!")
        print(f"   • Sprawdź logi błędów powyżej")
        print(f"   • Przywróć z kopii zapasowej jeśli potrzeba")
    
    print("="*60)

if __name__ == "__main__":
    main()