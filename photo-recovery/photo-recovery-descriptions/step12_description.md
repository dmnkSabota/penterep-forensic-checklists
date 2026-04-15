# Detaily testu

## Úkol

Opraviť poškodené fotografie pomocou automatizovaných techník zodpovedajúcich typu poškodenia.

## Obtiažnosť

Stredná

## Časová náročnosť

45 minút

## Automatický test

Áno

## Popis

Nástroj dostane cestu k adresáru s poškodenými súbormi a JSON so zoznamom súborov na opravu. Pre každý súbor priradí techniku podľa `corruptionType`, vykoná opravu na pracovnej kópii a následne validuje výsledok (PIL + jpeginfo). Originály zostávajú nedotknuté.

Spúšťa sa iba ak Rozhodnutie o oprave fotografií vrátilo stratégiu `perform_repair`.

## Jak na to

**1. Overenie predchádzajúcich výstupov:**

Skontrolujte výstup Rozhodnutia o oprave fotografií (`{CASE_ID}_repair_decision.json`) – ak je stratégia `skip_repair`, tento nástroj preskočte a pokračujte na EXIF analýzu.

Poznačte si:
- Cestu k adresáru s poškodenými súbormi (napr. `{CASE_ID}_validation/corrupted/`)
- Cestu k `{CASE_ID}_validation_report.json` z Validácie integrity fotografií (obsahuje `filesNeedingRepair`)

**2. Inštalácia závislostí:**

```bash
pip install Pillow --break-system-packages
sudo apt-get install jpeginfo
```

**3. Spustenie opravy:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
CORRUPTED="/var/forensics/images/${CASE_ID}_validation/corrupted"
REPORT="/var/forensics/images/${CASE_ID}_validation_report.json"

# Iba terminálový výstup
ptphotorepair ${CASE_ID} --corrupted-dir ${CORRUPTED} --validation-report ${REPORT}

# S JSON výstupom
ptphotorepair ${CASE_ID} --corrupted-dir ${CORRUPTED} --validation-report ${REPORT} \
  --analyst "Meno Analytika" --json-out ${CASE_ID}_repair_result.json

# Simulácia bez skutočných zmien
ptphotorepair ${CASE_ID} --corrupted-dir ${CORRUPTED} --validation-report ${REPORT} --dry-run
```

Nástroj pre každý súbor zo zoznamu `filesNeedingRepair`:
- Vytvorí pracovnú kópiu (`shutil.copy2`) – originál sa nemení
- Priradí techniku podľa `corruptionType` a vykoná opravu
- Validuje výsledok (PIL + jpeginfo)
- Presunie do `repaired/` (úspech) alebo `failed/` (zlyhanie)

Exit kódy:
- `0` – aspoň jeden súbor úspešne opravený
- `1` – žiadny súbor nebol opravený
- `99` – chyba (chýbajúci vstup, PIL nedostupný)
- `130` – prerušené užívateľom (Ctrl+C)

**4. Manuálna oprava (záložná metóda):**

Ak automatický nástroj nie je dostupný, použite priame techniky podľa typu poškodenia. Vždy pracujte na kópii súboru – originál sa nesmie meniť.

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
CORRUPTED="/var/forensics/images/${CASE_ID}_validation/corrupted"
REPAIRED="/var/forensics/images/${CASE_ID}_repair/repaired"
FAILED="/var/forensics/images/${CASE_ID}_repair/failed"
mkdir -p "${REPAIRED}" "${FAILED}"
```

**Chýbajúci EOI marker (`missing_footer`) – doplnenie FF D9 na koniec súboru:**
```python
import shutil

src  = "/var/forensics/images/CASE-001_validation/corrupted/IMG_001.jpg"
work = "/tmp/working_IMG_001.jpg"
shutil.copy2(src, work)

with open(work, "r+b") as f:
    data = f.read()
    if not data.endswith(b"\xff\xd9"):
        f.seek(0, 2)
        f.write(b"\xff\xd9")
```

**Poškodená hlavička (`invalid_header`) – obnovenie SOI markera (FF D8):**
```python
import shutil

src  = "/var/forensics/images/CASE-001_validation/corrupted/IMG_002.jpg"
work = "/tmp/working_IMG_002.jpg"
shutil.copy2(src, work)

with open(work, "rb") as f:
    data = f.read()
soi_pos = data.find(b"\xff\xd8")
if soi_pos > 0:
    with open(work, "wb") as f:
        f.write(data[soi_pos:])
```

**Poškodené segmenty (`corrupt_segments`) – zachovanie kritických markerov SOF0/DQT/DHT:**
```python
import shutil

src  = "/var/forensics/images/CASE-001_validation/corrupted/IMG_003.jpg"
work = "/tmp/working_IMG_003.jpg"
shutil.copy2(src, work)

SOI          = b"\xff\xd8"
SOS          = b"\xff\xda"
JFIF_APP0    = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
KEEP_MARKERS = {b"\xff\xc0", b"\xff\xdb", b"\xff\xc4"}  # SOF0, DQT, DHT

with open(work, "rb") as f:
    data = f.read()

sos_pos  = data.find(SOS)
critical = b""
i = 2
while i < sos_pos - 1:
    if data[i:i+1] != b"\xff":
        i += 1
        continue
    marker  = data[i:i+2]
    seg_len = int.from_bytes(data[i+2:i+4], "big")
    seg_end = i + 2 + seg_len
    if marker in KEEP_MARKERS:
        critical += data[i:seg_end]
    i = seg_end

with open(work, "wb") as f:
    f.write(SOI + JFIF_APP0 + critical + data[sos_pos:])
```

**Skrátený súbor (`truncated`) – čiastočná obnova cez PIL:**
```python
from PIL import Image, ImageFile
import shutil

ImageFile.LOAD_TRUNCATED_IMAGES = True

src  = "/var/forensics/images/CASE-001_validation/corrupted/IMG_004.jpg"
work = "/tmp/working_IMG_004.jpg"
shutil.copy2(src, work)

img = Image.open(work)
img.load()
img.save(work, "JPEG", quality=95, optimize=True)
```

Po každej oprave validujte výsledok a presuňte súbor:
```bash
# Validácia
jpeginfo -c /tmp/working_IMG_001.jpg
identify /tmp/working_IMG_001.jpg 2>&1

# Presun podľa výsledku
mv /tmp/working_IMG_001.jpg "${REPAIRED}/IMG_001.jpg"   # úspech
mv /tmp/working_IMG_001.jpg "${FAILED}/IMG_001.jpg"     # zlyhanie
```

**5. JSON výstup:**

Pri použití `--json-out` nástroj vytvorí štruktúrovaný report:

```json
{
  "result": {
    "properties": {
      "caseId": "PHOTORECOVERY-2025-01-26-001",
      "analyst": "Meno Analytika",
      "timestamp": "2025-01-26T17:00:00Z",
      "compliance": ["NIST SP 800-86", "ISO/IEC 10918-1", "JFIF 1.02"],
      "totalAttempted": 29,
      "successfulRepairs": 21,
      "failedRepairs": 8,
      "skippedFiles": 0,
      "successRate": 72.41,
      "byCorruptionType": {
        "missing_footer":   {"attempted": 10, "successful": 9,  "failed": 1},
        "invalid_header":   {"attempted": 8,  "successful": 7,  "failed": 1},
        "corrupt_segments": {"attempted": 7,  "successful": 4,  "failed": 3},
        "truncated":        {"attempted": 4,  "successful": 1,  "failed": 3}
      }
    }
  },
  "repairResults": [
    {
      "filename": "IMG_0042.jpg",
      "corruptionType": "missing_footer",
      "attempted": true,
      "repairTechnique": "repair_missing_footer",
      "expectedSuccess": "85–95 %",
      "repairMessage": "Appended missing EOI marker",
      "finalStatus": "fully_repaired",
      "validation": {
        "pil": true,
        "width": 4032,
        "height": 3024,
        "mode": "RGB",
        "jpeginfo": true,
        "toolsPassed": 2,
        "toolsTotal": 2,
        "valid": true
      }
    },
    {
      "filename": "IMG_0087.jpg",
      "corruptionType": "truncated",
      "attempted": true,
      "repairTechnique": "repair_truncated_file",
      "expectedSuccess": "50–70 %",
      "repairMessage": "Zero dimensions after truncated load",
      "finalStatus": "repair_failed",
      "validation": {}
    }
  ]
}
```

**6. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do dokumentácie prípadu:
- Celkový počet pokusov o opravu
- Počet úspešne opravených súborov
- Počet neúspešných opráv
- Miera úspešnosti (%)
- Pre každý súbor: typ poškodenia, použitá technika, výsledok (`fully_repaired` / `repair_failed`)

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T17:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Oprava fotografií dokončená – 21 úspešných, 8 neúspešných"
}
```

**7. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_repair_report.json` – detailné výsledky vrátane techniky a validácie pre každý súbor
- `${CASE_ID}_REPAIR_REPORT.txt` – textový prehľad štatistík a zoznam opravených súborov

## Výsledek

Opravené súbory v `${CASE_ID}_repair/repaired/`, neopraviteľné v `failed/`. Originály v `corrupted/` zostávajú nedotknuté. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje na EXIF analýzu.

## Reference

ISO/IEC 10918-1 – JPEG Standard (ITU-T T.81)
JFIF Specification v1.02
NIST SP 800-86 – Section 3.1.4 (Data Recovery and Repair)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)