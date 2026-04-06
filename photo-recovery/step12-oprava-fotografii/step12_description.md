# Detaily testu

## Úkol

Oprava identifikovaných poškodených fotografií pomocou automatizovaných techník.

## Obtiažnosť

Stredná

## Časová náročnosť

45 minút

## Automatický test

Áno

## Popis

Skript sa pokúsi opraviť každý súbor zo zoznamu `filesNeedingRepair` (Krok 10) technikou zodpovedajúcou typu poškodenia. Zdrojové súbory v adresári `corrupted/` zostávajú nedotknuté – oprava prebieha výhradne na pracovnej kópii. Krok sa aktivuje iba ak Krok 11 vrátil stratégiu `perform_repair`.

## Jak na to

**1. Overenie rozhodnutia o oprave:**

Skontrolujte uzol `repairDecision` (Krok 11). Ak stratégia je `skip_repair`, tento krok preskočte a pokračujte Krokom 13 (EXIF analýza).

**2. Príprava pracovného prostredia:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
VALID_DIR="/forenzne/pripady/${CASE_ID}/${CASE_ID}_validation"
REPAIR_DIR="/forenzne/pripady/${CASE_ID}/${CASE_ID}_repair"
mkdir -p "${REPAIR_DIR}/repaired" "${REPAIR_DIR}/failed"
```

Overte dostupnosť nástrojov:
```bash
pip install Pillow
which jpeginfo
```

**3. Vytvorenie pracovnej kópie:**

Pre každý súbor zo zoznamu `filesNeedingRepair` vytvorte pracovnú kópiu – originál v `corrupted/` sa nesmie meniť:
```bash
cp "${VALID_DIR}/corrupted/subor.jpg" "${REPAIR_DIR}/working_subor.jpg"
```

**4. Aplikácia opravných techník podľa typu poškodenia:**

**Truncated JPEG** – doplnenie chýbajúceho EOI markera:
```python
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
try:
    img = Image.open("working_subor.jpg")
    img.save("repaired_subor.jpg")
    print("Opravené")
except Exception as e:
    print(f"Neúspešné: {e}")
```

**Corrupt segments** – opätovné uloženie cez PIL:
```python
from PIL import Image
try:
    img = Image.open("working_subor.jpg")
    img.save("repaired_subor.jpg", quality=95, optimize=True)
except Exception as e:
    print(f"Neúspešné: {e}")
```

**Invalid header** – pokus o obnovu JPEG SOI markera (0xFF 0xD8):
```python
with open("working_subor.jpg", "r+b") as f:
    data = f.read()
    if data[:2] != b'\xff\xd8':
        idx = data.find(b'\xff\xd8')
        if idx > 0:
            f.seek(0)
            f.write(data[idx:])
```

**5. Validácia opraveného súboru:**

Po každej oprave overte výsledok:
```bash
jpeginfo -c repaired_subor.jpg
```
```python
from PIL import Image
try:
    img = Image.open("repaired_subor.jpg")
    img.load()
    print("Validný")
except:
    print("Stále poškodený")
```

Pri úspechu presuňte do `${REPAIR_DIR}/repaired/`, pri neúspechu do `${REPAIR_DIR}/failed/`.

**6. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do uzla `photoRepair` v dokumentácii prípadu:
- Celkový počet pokusov o opravu
- Počet úspešných opráv
- Počet neúspešných opráv
- Úspešnosť opravy (%)
- Pre každý súbor: použitá technika, výsledok (success/failed), prípadná chyba

Pridajte záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T17:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Oprava fotografií dokončená – N úspešných, M neúspešných"
}
```

**7. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_repair_report.json` – štatistiky a detail každej opravy
- `${CASE_ID}_REPAIR_REPORT.txt` – textový prehľad

---

> **Automatizácia (pripravuje sa):** Skript `ptphotorepair` bude smerovanie, opravu, validáciu, zápis uzla `photoRepair` a aktualizáciu CoC vykonávať automaticky.

## Výsledek

Opravené súbory v `${CASE_ID}_repair/repaired/`, neopraviteľné v `failed/`. Originály v `corrupted/` zostávajú nedotknuté. Výsledky zaznamenané v uzle `photoRepair`. Workflow pokračuje do Kroku 13 (EXIF analýza).

## Reference

ISO/IEC 10918-1 – JPEG Standard (ITU-T T.81)
JFIF Specification v1.02
NIST SP 800-86 – Section 3.1.4 (Data Recovery and Repair)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)