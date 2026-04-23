# Detaily testu

## Úkol

Validovať integritu obnovených fotografií a identifikovať poškodené súbory.

## Obtiažnosť

Stredná

## Časová náročnosť

30 minút – 2 hodiny (závisí od počtu súborov)

## Automatický test

Áno

## Popis

Tento krok validuje každý obnovený obrazový súbor pomocou trojstupňovej kontroly: (1) veľkosť a rozpoznanie typu obsahu (`file` + `identify`), (2) štruktúrna validácia nástrojom špecifickým pre formát (jpeginfo, pngcheck, tiffinfo), (3) klasifikácia typu poškodenia pre REPAIRABLE súbory.

Validácia prebieha IN-PLACE – súbory zostávajú na svojom mieste v konsolidovanom adresári z predchádzajúceho kroku. Nevytvára sa žiadna ďalšia kópia súborov. Výstupom je JSON klasifikácia s cestou a stavom každého súboru.

## Jak na to

**1. Inštalácia validačných nástrojov:**

```bash
sudo apt-get install imagemagick jpeginfo pngcheck libtiff-tools libimage-exiftool-perl
```

Nástroje `jpeginfo`, `pngcheck` a `tiffinfo` sú voliteľné – pri ich absencii skript použije PIL/Pillow ako záložnú metódu.

**2. Spustenie validácie:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"

# Iba terminálový výstup
ptintegrityvalidation ${CASE_ID}

# S JSON výstupom pre case.json
ptintegrityvalidation ${CASE_ID} --analyst "Meno Analytika" --json-out ${CASE_ID}_validation.json

# Simulácia bez čítania súborov
ptintegrityvalidation ${CASE_ID} --dry-run
```

Skript automaticky načíta súbory z `{CASE_ID}_consolidated/` vytvoreného v predchádzajúcom kroku.

**3. Priebeh validácie:**

Pre každý súbor v konsolidovanom adresári skript vykoná trojstupňovú kontrolu:

Stupeň 1 – základná validácia (`file` + `identify`): veľkosť súboru musí byť aspoň 100 B, `file -b` musí identifikovať typ ako obraz, `identify` musí súbor prečítať bez chyby.

Stupeň 2 – štruktúrna validácia špecifická pre formát: JPEG → `jpeginfo -c`, PNG → `pngcheck -v`, TIFF → `tiffinfo`, RAW → `exiftool`. Pri absencii nástroja sa použije PIL/Pillow.

Stupeň 3 – klasifikácia: súbory, ktoré neprejdú štruktúrnou validáciou, sú zatriedené podľa typu poškodenia (`missing_footer`, `invalid_header`, `corrupt_segments`, `truncated`, `corrupt_data`, `unknown`).

Klasifikácia výsledku:
- **VALID** – prejde obidvomi stupňami bez chyby
- **REPAIRABLE** – prejde základnou validáciou, štruktúrna validácia odhalí opraviteľné poškodenie
- **CORRUPTED** – závažné poškodenie, pravdepodobne neopraviteľné

Ak automatický nástroj nie je dostupný, vykonajte validáciu manuálne pre každý súbor:
```bash
# Stupeň 1
file -b subor.jpg
identify subor.jpg 2>&1

# Stupeň 2 – JPEG
jpeginfo -c subor.jpg

# Stupeň 2 – PNG
pngcheck -v subor.png

# Stupeň 2 – TIFF
tiffinfo subor.tiff
```

Výsledok zaznamenajte ručne do `{CASE_ID}_integrity_validation.json` s poliami `path`, `status` a `corruptionType`.

Súbory sa fyzicky nepresúvajú. Stav každého súboru sa zaznamenáva iba v JSON výstupe.

**4. Zápis výsledkov a aktualizácia CoC:**

Pri použití `--json-out` sa vytvorí JSON s výsledkami. Analytik manuálne skopíruje oba záznamy do `case.json`.

Pridávaný objekt `integrityValidation`:
```json
"integrityValidation": {
  "timestamp": "2025-01-26T16:00:00Z",
  "analyst": "Meno Analytika",
  "totalValidated": 2612,
  "valid": 2341,
  "repairable": 198,
  "corrupted": 73,
  "successRate": 89.6,
  "corruptionTypes": {
    "missing_footer": 87,
    "truncated": 64,
    "corrupt_segments": 31,
    "invalid_header": 16,
    "unknown": 0
  },
  "validationCatalog": "PHOTORECOVERY-2025-01-26-001_integrity_validation.json"
}
```

Nový záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T16:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Validácia integrity dokončená – 2341 VALID, 198 REPAIRABLE, 73 CORRUPTED (in-place, bez kópií)",
  "mediaSerial": "SN-XXXXXXXX"
}
```

**5. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_integrity_validation.json` – klasifikácia každého súboru s cestou, stavom a typom poškodenia

## Výsledek

Každý súbor v konsolidovanom adresári je klasifikovaný ako VALID, REPAIRABLE alebo CORRUPTED. Výsledky uložené v `{CASE_ID}_integrity_validation.json` s per-file záznamy (path, status, corruptionType). Súbory zostávajú na pôvodnom mieste – žiadne kopírovanie. Workflow pokračuje do rozhodnutia o oprave.

## Reference

ISO/IEC 27042:2015 – Section 5 (Digital evidence analysis)

NIST SP 800-86 – Section 2.3 (Analysis)

ImageMagick Documentation (https://imagemagick.org/)

LibJPEG / JPEGInfo Documentation

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)