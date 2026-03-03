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

Skript načíta validné súbory z kroku integrity validácie a voliteľne úspešne opravené súbory z kroku opravy, dávkovo extrahuje EXIF metadáta pomocou `exiftool` a vykoná analýzu časovej osi, zariadení, GPS súradníc a detekciu upravených fotografií. Poškodené a neopraviteľné súbory sú vynechané. Ak krok opravy prebehol so stratégiou `skip_repair`, `repair_report.json` neexistuje – skript to ošetrí bez chyby a spracuje iba validné súbory.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptexifanalysis PHOTORECOVERY-2025-01-26-001
```

Skript načíta `PHOTORECOVERY-2025-01-26-001_validation_report.json` (povinné – zoznam validných súborov) a `PHOTORECOVERY-2025-01-26-001_repair_report.json` (voliteľné – zoznam úspešne opravených súborov). Ak `repair_report.json` neexistuje alebo je neprístupný, skript zaloguje varovanie a pokračuje len s validnými súbormi.

**2. Dávková extrakcia EXIF:**

Pre každú dávku 50 súborov skript spustí `exiftool -j -G -a -s -n`. Súbory s aspoň jedným zmysluplným poľom (DateTimeOriginal, Make, ISO, GPS, Software) sa považujú za EXIF-pozitívne.

**3. Analýza času a zariadení:**

Skript parsuje `DateTimeOriginal`, buduje časovú os (fotky zoskupené podľa dátumu) a identifikuje unikátne zariadenia podľa polí `Make` a `Model` (výrobca a model fotoaparátu alebo telefónu).

**4. GPS a nastavenia:**

Pre každý záznam skript extrahuje GPS súradnice a číselné hodnoty ISO, FNumber a FocalLength pre štatistiku (min/max/avg).

**5. Detekcia úprav a anomálií:**

Každá fotografia môže mať v EXIF poli `Software` informáciu o programe, ktorý ju spracoval (napr. `"Adobe Photoshop"`, `"Instagram"`). Skript porovná túto hodnotu so zoznamom známeho editačného softvéru a označí súbor ako upravený.

Paralelne sa vykonávajú tri kontroly anomálií: ak je `DateTimeOriginal` v budúcnosti, pravdepodobne ide o poškodené EXIF alebo manipuláciu s metadátami. Ak je ISO vyššie ako 25 600, hodnota je pre bežné zariadenia neobvyklá. Ak je `ModifyDate` novší ako `DateTimeOriginal` a pritom chýba `Software` tag, súbor mohol byť potichu upravený bez zanechania stopy v metadátach.

**6. Export výstupov:**

Skript uloží do adresára `PHOTORECOVERY-2025-01-26-001_exif_analysis/`:
- `PHOTORECOVERY-2025-01-26-001_exif_database.json` – kompletná databáza
- `PHOTORECOVERY-2025-01-26-001_exif_data.csv` – Excel-kompatibilný export
- `PHOTORECOVERY-2025-01-26-001_EXIF_REPORT.txt` – textový report pre klienta

**7. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `exifAnalysis` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "exifAnalysis",
  "properties": {
    "sourcesAnalysed": ["PHOTORECOVERY-2025-01-26-001_validation/valid", "PHOTORECOVERY-2025-01-26-001_repair/repaired"],
    "totalFilesProcessed": 363,
    "exifPositive": 318,
    "withDateTimeOriginal": 298,
    "withGps": 47,
    "uniqueDevices": 3,
    "editedPhotos": 12,
    "anomaliesDetected": 2,
    "qualityScore": "good",
    "exifDatabasePath": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_exif_analysis/PHOTORECOVERY-2025-01-26-001_exif_database.json",
    "completedAt": "2025-01-26T22:30:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step13-exif-analysis",
    "action": "EXIF analysis completed – 363 files processed (341 valid + 22 repaired), quality score: good (87.4% DateTimeOriginal)",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T22:30:00Z",
    "notes": null
  }
}
```

Ak bol krok opravy preskočený (`skip_repair`), pole `sourcesAnalysed` bude obsahovať len `validation/valid` a počet opravených súborov bude 0.

## Výsledek

Kompletná EXIF databáza v adresári `PHOTORECOVERY-2025-01-26-001_exif_analysis/` s per-file metadátami, časovou osou a GPS zoznamom. CSV export pre ďalšie spracovanie. EXIF quality score: excellent (>90 % DateTimeOriginal), good (70–90 %), fair (50–70 %), poor (<50 %). Aktualizovaný case JSON súbor s uzlom `exifAnalysis` a ďalším záznamom `chainOfCustody`. Workflow pokračuje do kroku Finálny report.

## Reference

EXIF 2.32 Specification (CIPA DC-008-2019)
ISO 12234-2:2001 – Electronic still-picture imaging
ExifTool Documentation

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)