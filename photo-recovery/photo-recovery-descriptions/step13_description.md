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

Nástroj dostane cestu k adresáru s validnými súbormi z Validácie integrity fotografií a voliteľne cestu k adresáru s opravenými súbormi z Opravy fotografií. Dávkovo extrahuje EXIF metadáta pomocou `exiftool` a vykoná analýzu časovej osi, zariadení, GPS súradníc a detekciu upravených fotografií. Poškodené a neopraviteľné súbory sú vynechané. Ak Oprava fotografií prebehla so stratégiou `skip_repair`, `--repaired-dir` sa jednoducho neuvádza.

## Jak na to

**1. Overenie predchádzajúcich výstupov:**

Poznačte si:
- Cestu k adresáru s validnými súbormi z Validácie integrity fotografií (napr. `{CASE_ID}_validation/valid/`)
- Ak prebehla Oprava fotografií, cestu k opravenému adresáru (napr. `{CASE_ID}_repair/repaired/`)

**2. Inštalácia závislostí:**

```bash
sudo apt-get install libimage-exiftool-perl
```

**3. Spustenie analýzy:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
VALID="/var/forensics/images/${CASE_ID}_validation/valid"
REPAIRED="/var/forensics/images/${CASE_ID}_repair/repaired"

# Iba validné súbory (bez predchádzajúcej opravy)
ptexifanalysis ${CASE_ID} --valid-dir ${VALID}

# Validné aj opravené súbory
ptexifanalysis ${CASE_ID} --valid-dir ${VALID} --repaired-dir ${REPAIRED}

# S JSON výstupom
ptexifanalysis ${CASE_ID} --valid-dir ${VALID} --repaired-dir ${REPAIRED} \
  --analyst "Meno Analytika" --json-out ${CASE_ID}_exif_result.json

# Simulácia bez exiftool
ptexifanalysis ${CASE_ID} --valid-dir ${VALID} --dry-run
```

Nástroj automaticky:
- Overí existenciu vstupných adresárov
- Dávkovo extrahuje EXIF (50 súborov na volanie exiftool)
- Zostaví časovú os, zoznam zariadení, GPS súradnice
- Detekuje editačný softvér a anomálie
- Vygeneruje JSON databázu, CSV export a textový report

Exit kódy:
- `0` – aspoň jeden súbor s EXIF dátami
- `1` – žiadne EXIF dáta nenájdené
- `99` – chyba (chýbajúci vstup, exiftool nedostupný)
- `130` – prerušené užívateľom (Ctrl+C)

**4. Manuálna analýza (záložná metóda):**

Ak automatický nástroj nie je dostupný, použite priame príkazy.

Nastavenie premenných:
```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
VALID="/var/forensics/images/${CASE_ID}_validation/valid"
EXIF_DIR="/var/forensics/images/${CASE_ID}_exif_analysis"
mkdir -p "${EXIF_DIR}"
```

**Dávková extrakcia EXIF do JSON:**
```bash
exiftool -j -G -a -s -n \
    "${VALID}/" \
    > "${EXIF_DIR}/${CASE_ID}_exif_database.json"
```

**CSV export pre tabuľkový editor:**
```bash
exiftool -csv -G -a \
    "${VALID}/" \
    > "${EXIF_DIR}/${CASE_ID}_exif_data.csv"
```

**Analýza časovej osi – zoskupenie podľa dátumu:**
```bash
exiftool -DateTimeOriginal -T -r "${VALID}/" \
    | sort | uniq -c | sort -rn
```

**Zoznam zariadení:**
```bash
exiftool -Make -Model -T -r "${VALID}/" \
    | sort | uniq -c | sort -rn
```

**GPS súradnice:**
```bash
exiftool -GPSLatitude -GPSLongitude -FileName -T -r "${VALID}/" \
    | grep -v "^-"
```

**Detekcia editačného softvéru:**
```bash
exiftool -Software -FileName -T -r "${VALID}/" \
    | grep -iv "^-" \
    | grep -i "photoshop\|lightroom\|gimp\|instagram\|snapseed"
```

**Anomálie – dátumy v budúcnosti:**
```bash
YEAR=$(date +%Y)
exiftool -DateTimeOriginal -FileName -T -r "${VALID}/" \
    | awk -F'\t' -v yr="$YEAR" '$1 > yr":00:00 00:00:00" {print $0}'
```

**5. JSON výstup:**

Pri použití `--json-out` nástroj vytvorí štruktúrovaný report:

```json
{
  "result": {
    "properties": {
      "caseId": "PHOTORECOVERY-2025-01-26-001",
      "analyst": "Meno Analytika",
      "timestamp": "2025-01-26T17:30:00Z",
      "compliance": ["NIST SP 800-86", "EXIF 2.32", "CIPA DC-008-2019"],
      "totalFiles": 847,
      "filesWithExif": 812,
      "filesWithoutExif": 35,
      "withDatetime": 798,
      "withGps": 423,
      "editedPhotos": 14,
      "anomalies": 3,
      "uniqueCameras": 4,
      "qualityScore": "excellent",
      "qualityPct": 98.2,
      "dateRange": {
        "earliest": "2024-03-15 08:22:11",
        "latest":   "2025-01-20 18:45:03",
        "spanDays": 311
      },
      "byCamera": {
        "Apple iPhone 15 Pro": 541,
        "Samsung Galaxy S24":  198,
        "Canon EOS R6":         63,
        "Unknown":              10
      },
      "settingsRange": {
        "iso":         {"min": 20,   "max": 6400,  "avg": 312.4},
        "aperture":    {"min": 1.8,  "max": 22.0,  "avg": 4.2},
        "focalLength": {"min": 13.0, "max": 200.0, "avg": 38.7}
      }
    }
  },
  "exifData": [
    {
      "fileId": 1,
      "filename": "IMG_0042.jpg",
      "make": "Apple",
      "model": "iPhone 15 Pro",
      "datetimeOriginal": "2025:01:15 14:32:07",
      "iso": 64,
      "fNumber": 1.78,
      "focalLength": 6.86,
      "gpsLatitude": 48.1482,
      "gpsLongitude": 17.1067,
      "software": null,
      "edited": false
    }
  ],
  "editedPhotos": [
    {
      "filename": "IMG_0731.jpg",
      "software": "Adobe Lightroom 7.0"
    }
  ],
  "anomalies": [
    {
      "filename": "IMG_0099.jpg",
      "type": "future_date",
      "detail": "DateTimeOriginal in future: 2027-03-01"
    }
  ]
}
```

**6. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do dokumentácie prípadu:
- Celkový počet spracovaných súborov
- Počet EXIF-pozitívnych súborov
- Počet súborov s `DateTimeOriginal`
- Počet súborov s GPS súradnicami
- Počet unikátnych zariadení
- Počet upravených fotografií
- Počet detekovaných anomálií
- EXIF quality score (excellent / good / fair / poor)

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T17:30:00Z",
  "analyst": "Meno Analytika",
  "action": "EXIF analýza dokončená – 812 EXIF-pozitívnych súborov, quality: excellent"
}
```

**7. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_exif_database.json` – kompletná EXIF databáza s per-file metadátami
- `${CASE_ID}_exif_data.csv` – Excel-kompatibilný export
- `${CASE_ID}_EXIF_REPORT.txt` – textový súhrn (časová os, zariadenia, GPS, anomálie)

## Výsledek

Kompletná EXIF databáza s per-file metadátami, časovou osou a GPS zoznamom. CSV export pre ďalšie spracovanie. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje na Záverečný report.

## Reference

EXIF 2.32 Specification (CIPA DC-008-2019)
ISO 12234-2:2001 – Electronic still-picture imaging
ExifTool Documentation (https://exiftool.org)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)