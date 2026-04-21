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

Nástroj načíta zoznam súborov s rozhodnutím `ATTEMPT_REPAIR` z výstupu predchádzajúceho kroku (`{CASE_ID}_repair_decisions.json`). Pre každý súbor priradí techniku podľa `corruptionType`, vykoná opravu na pracovnej kópii a následne validuje výsledok (PIL + jpeginfo). Originály zostávajú nedotknuté.

Spúšťa sa iba ak výstup rozhodovacieho kroku obsahuje záznamy s `ATTEMPT_REPAIR`. Pri absencii takýchto záznamov skript skončí bez vykonania opráv.

Podporované formáty: JPEG (byte-level oprava), PNG (PIL resave). TIFF a RAW nie sú podporované – tieto súbory sú zaznamenané ako `repair_failed`.

## Jak na to

**1. Overenie predchádzajúcich výstupov:**

Skontrolujte výstup rozhodovacieho kroku (`{CASE_ID}_repair_decisions.json`) – ak neobsahuje žiadne záznamy s `ATTEMPT_REPAIR`, tento nástroj preskočte a pokračujte na EXIF analýzu.

Poznačte si:
- Cestu k `{CASE_ID}_repair_decisions.json` (štandardne v output adresári)

**2. Inštalácia závislostí:**

```bash
pip install Pillow --break-system-packages
sudo apt-get install jpeginfo
```

**3. Spustenie opravy:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"

# Iba terminálový výstup
ptphotorepair ${CASE_ID}

# S JSON výstupom
ptphotorepair ${CASE_ID} --analyst "Meno Analytika" --json-out ${CASE_ID}_repair_result.json

# Explicitná cesta k decisions súboru
ptphotorepair ${CASE_ID} \
  --decisions-file /var/forensics/images/${CASE_ID}_repair_decisions.json \
  --analyst "Meno Analytika" --json-out ${CASE_ID}_repair_result.json

# Simulácia bez skutočných zmien
ptphotorepair ${CASE_ID} --dry-run
```

Nástroj pre každý súbor s rozhodnutím `ATTEMPT_REPAIR`:
- Vytvorí pracovnú kópiu (`shutil.copy2`) – originál sa nemení
- Priradí techniku podľa `corruptionType` a vykoná opravu
- Validuje výsledok (PIL + jpeginfo)
- Uloží do `{CASE_ID}_repaired/` (úspech) alebo `{CASE_ID}_repair_failed/` (zlyhanie)

Exit kódy:
- `0` – aspoň jeden súbor úspešne opravený
- `1` – žiadny súbor nebol opravený
- `99` – chyba (chýbajúci vstup, PIL nedostupný)
- `130` – prerušené užívateľom (Ctrl+C)

**4. Manuálna oprava (záložná metóda):**

Ak automatický nástroj nie je dostupný, použite priame techniky podľa typu poškodenia. Vždy pracujte na kópii súboru – originál sa nesmie meniť.

**Chýbajúci EOI marker (`missing_footer`) – doplnenie FF D9 na koniec súboru:**
```python
import shutil
src  = "/cesta/k/originalu/IMG_001.jpg"
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
src  = "/cesta/k/originalu/IMG_002.jpg"
work = "/tmp/working_IMG_002.jpg"
shutil.copy2(src, work)

with open(work, "rb") as f:
    data = f.read()
soi_pos = data.find(b"\xff\xd8")
if soi_pos > 0:
    with open(work, "wb") as f:
        f.write(data[soi_pos:])
```

**Skrátený súbor (`truncated`) – čiastočná obnova cez PIL:**
```python
from PIL import Image, ImageFile
import shutil

ImageFile.LOAD_TRUNCATED_IMAGES = True
src  = "/cesta/k/originalu/IMG_004.jpg"
work = "/tmp/working_IMG_004.jpg"
shutil.copy2(src, work)

img = Image.open(work)
img.load()
img.save(work, "JPEG", quality=95, optimize=True)
```

Po každej oprave validujte výsledok:
```bash
jpeginfo -c /tmp/working_IMG_001.jpg
identify /tmp/working_IMG_001.jpg 2>&1
```

**5. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do dokumentácie prípadu:
- Celkový počet pokusov o opravu
- Počet úspešne opravených súborov
- Počet neúspešných opráv
- Miera úspešnosti (%)
- Pre každý súbor: typ poškodenia, použitá technika, výsledok (`repair_done` / `repair_failed`)

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T17:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Oprava fotografií dokončená – N úspešných, M neúspešných"
}
```

**6. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_repair_report.json` – detailné výsledky vrátane techniky a validácie pre každý súbor

## Výsledek

Opravené súbory v `${CASE_ID}_repaired/`, neopraviteľné v `${CASE_ID}_repair_failed/`. Originály na pôvodných cestách zostávajú nedotknuté. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje na EXIF analýzu.

## Reference

ISO/IEC 10918-1 – JPEG Standard (ITU-T T.81)
JFIF Specification v1.02
NIST SP 800-86 – Section 3.1.4 (Data Recovery and Repair)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)