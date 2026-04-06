# Detaily testu

## Úkol

Extrahovať a analyzovať EXIF metadáta zo všetkých obnovených fotografií.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Áno

## Popis

Skript načíta validné súbory z uzla `integrityValidation` (Krok 10) a voliteľne úspešne opravené súbory z uzla `photoRepair` (Krok 12), dávkovo extrahuje EXIF metadáta pomocou `exiftool` a vykoná analýzu časovej osi, zariadení, GPS súradníc a detekciu upravených fotografií. Poškodené a neopraviteľné súbory sú vynechané. Ak krok opravy prebehol so stratégiou `skip_repair`, uzol `photoRepair` neexistuje – skript to ošetrí bez chyby a spracuje iba validné súbory.

## Jak na to

**1. Príprava vstupného zoznamu:**

Z uzla `integrityValidation` (Krok 10) získajte zoznam validných súborov (adresár `_validation/valid/`). Ak existuje uzol `photoRepair` (Krok 12), doplňte zoznam o súbory z `_repair/repaired/`. Poškodené a neopraviteľné súbory nezahrňujte.

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
BASE="/forenzne/pripady/${CASE_ID}"
EXIF_DIR="${BASE}/${CASE_ID}_exif"
mkdir -p "${EXIF_DIR}/metadata"
```

**2. Dávková extrakcia EXIF:**

```bash
exiftool -j -G -a -s -n \
    "${BASE}/${CASE_ID}_validation/valid/" \
    "${BASE}/${CASE_ID}_repair/repaired/" \
    > "${EXIF_DIR}/${CASE_ID}_exif_database.json"
```
Ak adresár `_repair/repaired/` neexistuje, príkaz ho jednoducho preskočí.

Pre CSV export:
```bash
exiftool -csv -G -a \
    "${BASE}/${CASE_ID}_validation/valid/" \
    > "${EXIF_DIR}/${CASE_ID}_exif_data.csv"
```

Súbory s aspoň jedným zmysluplným poľom (DateTimeOriginal, Make, ISO, GPS, Software) považujte za EXIF-pozitívne.

**3. Analýza času a zariadení:**

Z `_exif_database.json` pre každý záznam skontrolujte:
- `DateTimeOriginal` – zostavte časovú os (zoskupte fotky podľa dátumu)
- `Make` a `Model` – zaznamenajte zoznam unikátnych zariadení

**4. GPS a technické nastavenia:**

Pre každý záznam skontrolujte:
- `GPSLatitude` a `GPSLongitude` → zaznamenajte zoznam GPS súradníc
- `ISO`, `FNumber`, `FocalLength` → zaznamenajte min/max/priemerné hodnoty

**5. Detekcia úprav a anomálií:**

**Editačný softvér** – pole `Software`:
Ak obsahuje hodnoty ako `Adobe Photoshop`, `Lightroom`, `GIMP`, `Instagram`, `Snapseed` a podobne, označte súbor ako upravený.

**Anomálie – skontrolujte manuálne:**
- `DateTimeOriginal` v budúcnosti → pravdepodobne poškodené EXIF alebo manipulácia
- `ISO` > 25 600 → hodnota neobvyklá pre bežné zariadenia
- `ModifyDate` novší ako `DateTimeOriginal` a zároveň chýba `Software` tag → možná tichá úprava

**6. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do uzla `exifAnalysis` v dokumentácii prípadu:
- Celkový počet spracovaných súborov
- Počet EXIF-pozitívnych súborov
- Počet súborov s `DateTimeOriginal`
- Počet súborov s GPS súradnicami
- Počet unikátnych zariadení
- Počet upravených fotografií (Software tag prítomný)
- Počet detekovaných anomálií
- EXIF quality score:
  - excellent – > 90 % súborov má `DateTimeOriginal`
  - good – 70–90 %
  - fair – 50–70 %
  - poor – < 50 %

Pridajte záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T17:30:00Z",
  "analyst": "Meno Analytika",
  "action": "EXIF analýza dokončená – N EXIF-pozitívnych súborov, EXIF quality: good"
}
```

**7. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_exif_database.json` – kompletná EXIF databáza
- `${CASE_ID}_exif_data.csv` – Excel-kompatibilný export
- `${CASE_ID}_EXIF_REPORT.txt` – textový súhrn pre klienta (časová os, zariadenia, anomálie)

---

> **Automatizácia (pripravuje sa):** Skript `ptexifanalysis` bude dávkovú extrakciu, analýzu, zápis uzla `exifAnalysis` a aktualizáciu CoC vykonávať automaticky.

## Výsledek

Kompletná EXIF databáza s per-file metadátami, časovou osou a GPS zoznamom. CSV export pre ďalšie spracovanie. Výsledky zaznamenané v uzle `exifAnalysis`. Workflow pokračuje do Kroku 14 (Záverečná správa).

## Reference

EXIF 2.32 Specification (CIPA DC-008-2019)
ISO 12234-2:2001 – Electronic still-picture imaging
ExifTool Documentation

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)