# Detaily testu

## Úkol

Overiť fyzickú integritu všetkých obnovených fotografií a rozdeliť ich do kategórií.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Áno

## Popis

Tento krok overuje, či sú obnovené súbory skutočne čitateľné a nepoškodené. Pre každý súbor z konsolidovaného datasetu (Krok 9) sa vykoná viacúrovňová validácia a výsledok sa klasifikuje ako valid, corrupted alebo unrecoverable. Tento výsledok priamo určuje, či je potrebná oprava v Kroku 12.

## Jak na to

**1. Príprava a kontrola nástrojov:**

PIL/Pillow je povinný:
```bash
pip install Pillow
```
Voliteľné nástroje (skript ich využije ak sú dostupné):
```bash
sudo apt-get install libjpeg-progs pngcheck
```

Nastavte premenné:
```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
CONSOL="/forenzne/pripady/${CASE_ID}/${CASE_ID}_consolidated"
VALID_DIR="/forenzne/pripady/${CASE_ID}/${CASE_ID}_validation"
mkdir -p "${VALID_DIR}/valid" "${VALID_DIR}/corrupted" "${VALID_DIR}/unrecoverable"
```

**2. Per-file validácia:**

Pre každý súbor z master katalógu vykonajte nasledujúce kontroly:

**a) Veľkosť súboru** – prázdne súbory sú okamžite neopraviteľné:
```bash
[ -s subor ] && echo "OK" || echo "EMPTY – unrecoverable"
```

**b) PIL verify + load** (Python):
```python
from PIL import Image
try:
    img = Image.open("subor")
    img.verify()
    img.close()
    img = Image.open("subor")
    img.load()
    print("VALID")
except Exception as e:
    print(f"CORRUPTED: {e}")
```

**c) Pre JPEG – jpeginfo** (ak je dostupný):
```bash
jpeginfo -c subor
```

**d) Pre PNG – pngcheck** (ak je dostupný):
```bash
pngcheck -v subor
```

**Rozhodovacia logika:**
- Všetky dostupné nástroje prešli → `valid/`
- Niektoré prešli, niektoré zlyhali → `corrupted/` (potenciálne opraviteľný)
- Všetky zlyhali alebo súbor je prázdny → `unrecoverable/`

**3. Klasifikácia typu poškodenia pre corrupted súbory:**

Pre každý súbor v `corrupted/` zaznamenajte typ a úroveň opraviteľnosti:

| Typ | Úroveň | Popis |
|-----|--------|-------|
| truncated | L1 | Skrátený súbor, chýba EOI marker |
| corrupt_segments | L2 | Poškodené dátové bloky |
| unknown | L3 | Neurčený typ, manuálna inšpekcia |
| corrupt_data | L4 | Poškodené pixelové dáta |
| invalid_header | L5 | Poškodená hlavička – neopraviteľné |

**4. Výpočet Integrity Score:**

```
Integrity Score = (počet valid súborov / celkový počet súborov) × 100 %
```

**5. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do uzla `integrityValidation` v dokumentácii prípadu:
- Celkový počet validovaných súborov
- Počet validných súborov
- Počet poškodených súborov
- Počet neopraviteľných súborov
- Integrity score (%)
- Použité nástroje
- Zoznam `filesNeedingRepair` (corrupted súbory L1–L4 s typom poškodenia)

Pridajte záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T16:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Validácia integrity dokončená – Integrity Score: 87 %, N poškodených súborov"
}
```

**6. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_validation_report.json` – kompletný validačný report
- `${CASE_ID}_VALIDATION_REPORT.txt` – textový prehľad so zoznamom súborov na opravu

---

> **Automatizácia (pripravuje sa):** Skript `ptintegrityvalidation` bude validáciu, klasifikáciu, zápis uzla `integrityValidation` a aktualizáciu CoC vykonávať automaticky.

## Výsledek

Klasifikácia všetkých fotografií do troch kategórií v `${CASE_ID}_validation/`: `valid/`, `corrupted/`, `unrecoverable/`. Integrity score s rozpisom podľa formátu a zdroja. Výsledky zaznamenané v uzle `integrityValidation`. Workflow pokračuje do Kroku 11 (Rozhodnutie o oprave).

## Reference

ISO/IEC 10918-1 – JPEG Standard
PNG Specification – ISO/IEC 15948:2004
NIST SP 800-86 – Section 3.1.3 (Data Validation)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)