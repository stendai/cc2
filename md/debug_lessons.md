# 📓 Debug Lessons Learned (Covered Call System)

## 1. Świadomość instalacji triggerów
- Logi (`debug_log`) pojawiają się **tylko dla zdarzeń po instalacji triggerów**.
- Jeśli buyback był **przed instalacją** → logów nie będzie.
- ✅ Nauka: zawsze instalować triggery przed testem.

---

## 2. Custom logger w bazie (`cc_unlock_probe`)
- Stworzyliśmy mechanizm **diagnostycznych triggerów**:
  - `dbg_cc_status_update` – loguje zmianę statusu CC.
  - `dbg_res_insert` / `dbg_res_delete` – logują tworzenie i kasowanie rezerwacji.
  - `dbg_lots_open_update` – śledzi zmiany w `lots.quantity_open`.
- ✅ Nauka: taki logger pozwala zobaczyć, które kroki faktycznie wykonuje baza.

---

## 3. Rozszerzenie argparse
- Dodaliśmy brakujący argument `--ticker` w `cc_unlock_probe.py`.
- ✅ Nauka: czasem debugowanie nie działa tylko dlatego, że brakuje opcji w CLI.

---

## 4. Analiza ghost-locków
- `lot.quantity_open=0`, ale rezerwacje=0 i mapowania=0.
- To znaczy: ktoś zdekrementował OPEN przy rezerwacji, ale nie podbił go przy zwolnieniu.
- ✅ Nauka: zawsze sprawdzaj różnicę „decrement vs release”.

---

## 5. Trigger gap analysis
- W bazie istnieje trigger kasujący rezerwacje (`trg_cc_release_reservations_on_status_update`).
- ❌ Brak triggera zwiększającego `lots.quantity_open`.
- ✅ Nauka: sprawdzanie wszystkich triggerów SQL pozwala wykryć brakujące kroki.

---

## 6. Problem `lot_linked_id=NULL`
- CC miało `lot_linked_id=NULL`.
- Ścieżka aplikacyjna release oparta na tym polu **nie wykonała się**.
- ✅ Nauka: nie polegać na polach linkujących, tylko na faktycznych rezerwacjach.

---

## 7. Biznesowy wniosek – wybór lota przez użytkownika
- Użytkownik powinien wskazać **konkretne loty** przy SELL CC i BUYBACK.
- ✅ Wtedy rezerwacje są jawne i odblokowanie jest jednoznaczne.

---

## 8. Nowe triggery spójności
- Dodaliśmy propozycję:
  - `trg_lots_open_on_reserve` – zmniejsza `quantity_open` przy INSERT rezerwacji.
  - `trg_lots_open_on_release` – zwiększa `quantity_open` przy DELETE rezerwacji.
- ✅ Problem ghost-locków znika, nawet jeśli `lot_linked_id=NULL`.

---

## 9. Heurystyka w debugach
- Debug wypisywał:
  - `reservations_sum_for_cc`
  - `mappings_rows_for_cc`
  - `quantity_open vs expected_open`
- ✅ Nauka: to daje natychmiastową diagnozę czy lock jest „uzasadniony” czy „ghost”.

---

## 10. UI i status „Nieznany”
- Status w UI pojawiał się, bo JOIN był po `lot_linked_id` i zostawały NULL-e.
- ✅ Nauka: UI powinno liczyć blokady **na podstawie sumy rezerwacji**, a nie statusów CC.

---

# 🧩 Proces debugowania krok po kroku
1. Zauważenie „Nieznany” w UI.
2. Uruchomienie skanów (reservations, orphan mappings, lots).
3. Instalacja triggerów logujących.
4. Ponowny buyback → logi pokazują sekwencję (insert reserve → status update → delete reserve).
5. Brak update `lots.quantity_open` → root cause.
6. Wykrycie `lot_linked_id=NULL`.
7. Wniosek: potrzebny wybór lota przez użytkownika.
8. Dodanie triggerów open_on_reserve/release.
9. Refleksja: UI powinno bazować na rezerwacjach.

---

# 💡 Summary
- Zamiast ręcznych poprawek, znaleźliśmy **root cause**: brak jawnego przypięcia lota i brak triggerów zwiększających `quantity_open`.
- Teraz system jest jednoznaczny: **rezerwacje są źródłem prawdy**, a loty podnoszą się i opuszczają automatycznie.
- To podejście to już nie poziom juniora, a **junior+ / mid**, bo obejmuje myślenie systemowe i architekturę bazy.

