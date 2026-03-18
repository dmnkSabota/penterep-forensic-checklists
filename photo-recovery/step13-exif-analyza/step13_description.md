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

**1. Spustenie skriptu:**

```bash
ptexifanalysis PHOTORECOVERY-2025-01-26-001
```

Skript načíta zoznam validných súborov z uzla `integrityValidation` (Krok 10) a voliteľne zoznam úspešne opravených súborov z uzla `photoRepair` (Krok 12). Ak uzol `photoRepair` neexistuje alebo stratégia bola `skip_repair`, skript zaloguje varovanie a pokračuje len s validnými súbormi.

**2. Dávková extrakcia EXIF:**

Pre každú dávku 50 súborov skript spustí `exiftool -j -G -a -s -n`. Súbory s aspoň jedným zmysluplným poľom (DateTimeOriginal, Make, ISO, GPS, Software) sa považujú za EXIF-pozitívne.

**3. Analýza času a zariadení:**

Skript parsuje `DateTimeOriginal`, buduje časovú os (fotky zoskupené podľa dátumu) a identifikuje unikátne zariadenia podľa polí `Make` a `Model` (výrobca a model fotoaparátu alebo telefónu).

**4. GPS a nastavenia:**

Pre každý záznam skript extrahuje GPS súradnice a číselné hodnoty ISO, FNumber a FocalLength pre štatistiku (min/max/avg).

**5. Detekcia úprav a anomálií:**

Každá fotografia môže mať v EXIF poli `Software` informáciu o programe, ktorý ju spracoval (napr. `"Adobe Photoshop"`, `"Instagram"`). Skript porovná túto hodnotu so zoznamom známeho editačného softvéru a označí súbor ako upravený.

Paralelne sa vykonávajú tri kontroly anomálií: ak je `DateTimeOriginal` v budúcnosti, pravdepodobne ide o poškodené EXIF alebo manipuláciu s metadátami. Ak je ISO vyššie ako 25 600, hodnota je pre bežné zariadenia neobvyklá. Ak je `ModifyDate` novší ako `DateTimeOriginal` a pritom chýba `Software` tag, súbor mohol byť potichu upravený bez zanechania stopy v metadátach.

**6. Výsledky v uzle exifAnalysis:**

Skript automaticky zapíše výsledky do uzla `exifAnalysis` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Celkový počet spracovaných súborov
- Počet EXIF-pozitívnych súborov
- Počet súborov s DateTimeOriginal
- Počet súborov s GPS
- Počet unikátnych zariadení
- Počet upravených fotografií (Software tag)
- Počet detekovaných anomálií
- EXIF quality score – excellent (>90 % DateTimeOriginal) / good (70–90 %) / fair (50–70 %) / poor (<50 %)

**7. Archivácia výstupov:**

Skript automaticky nahrá nasledujúce súbory do záložky **Přílohy** projektu:
- `PHOTORECOVERY-2025-01-26-001_exif_database.json` – kompletná EXIF databáza
- `PHOTORECOVERY-2025-01-26-001_exif_data.csv` – Excel-kompatibilný export
- `PHOTORECOVERY-2025-01-26-001_EXIF_REPORT.txt` – textový report pre klienta

## Výsledek

Kompletná EXIF databáza s per-file metadátami, časovou osou a GPS zoznamom. CSV export pre ďalšie spracovanie. Výsledky zaznamenané v uzle `exifAnalysis`. Workflow pokračuje do kroku Finálny report.

## Reference

EXIF 2.32 Specification (CIPA DC-008-2019)
ISO 12234-2:2001 – Electronic still-picture imaging
ExifTool Documentation

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)