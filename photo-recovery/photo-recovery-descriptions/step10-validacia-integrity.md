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

Tento krok validuje každý obnovený obrazový súbor pomocou trojstupňovej kontroly: (1) veľkosť súboru, (2) typ obsahu (`file`), (3) technická čitateľnosť (`identify` pre JPEG/PNG/TIFF, format-specific nástroje pre RAW). Klasifikuje súbory do kategórií: VALID (úplne v poriadku), REPAIRABLE (čiastočné poškodenie, možno opraviť), CORRUPTED (vážne poškodenie, pravdepodobne neopraviteľné).

## Jak na to

**1. Nastavenie premenných:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
CONSOL="/forenzne/pripady/${CASE_ID}/${CASE_ID}_consolidated"
OUTPUT="${CONSOL}/validation"
mkdir -p "${OUTPUT}/valid" "${OUTPUT}/repairable" "${OUTPUT}/corrupted"
```

**2. Inštalácia validačných nástrojov:**

```bash
sudo apt-get install imagemagick exiftool jpeginfo pngcheck libtiff-tools
```

**3. Trojstupňová validácia pre každý súbor:**

Pre každý súbor v `${CONSOL}/fs_based/` a `${CONSOL}/carved/`:

**Stupeň 1 – Minimálna veľkosť:**
```bash
SIZE=$(stat -c%s "subor")
if [ $SIZE -lt 100 ]; then
  # → CORRUPTED
fi
```

**Stupeň 2 – Typ obsahu:**
```bash
TYPE=$(file -b "subor")
if [[ ! $TYPE =~ "image" ]]; then
  # → CORRUPTED
fi
```

**Stupeň 3 – Technická čitateľnosť:**

JPEG:
```bash
jpeginfo -c "subor.jpg"
# Exit 0 → VALID
# Exit ≠ 0 → skontrolujte ImageMagick
identify "subor.jpg" 2>&1
# Úspech → REPAIRABLE (drobné chyby)
# Zlyhanie → CORRUPTED
```

PNG:
```bash
pngcheck "subor.png"
# OK → VALID
# Warnings → REPAIRABLE
# Errors → CORRUPTED
```

TIFF:
```bash
tiffinfo "subor.tiff" >/dev/null 2>&1
# Exit 0 → VALID
# Exit ≠ 0 → CORRUPTED
```

RAW (CR2, NEF, ARW, atď.):
```bash
exiftool "subor.cr2" | grep -i "Image Size"
# Rozpoznaný → VALID
# Chyba → CORRUPTED (RAW súbory sú ťažko opraviteľné)
```

**4. Klasifikácia a organizácia:**

- **VALID** → skopírujte do `${OUTPUT}/valid/`
- **REPAIRABLE** → skopírujte do `${OUTPUT}/repairable/` (Step 12 ich skúsi opraviť)
- **CORRUPTED** → skopírujte do `${OUTPUT}/corrupted/` (nepokračuje do opravy)

**5. Generovanie štatistík:**

Vytvorte súbor `VALIDATION_REPORT.txt`:
```
Celkový počet súborov: N
VALID: X (Y%)
REPAIRABLE: A (B%)
CORRUPTED: C (D%)

Formáty (VALID):
  JPG: ...
  PNG: ...
  TIFF: ...
  RAW: ...
```

**6. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky validácie do dokumentácie prípadu:
- Celkový počet validovaných súborov
- Počet VALID súborov
- Počet REPAIRABLE súborov
- Počet CORRUPTED súborov
- Miera úspešnosti (%)
- Štatistiky podľa formátu

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T16:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Validácia integrity dokončená – N VALID, M REPAIRABLE, K CORRUPTED"
}
```

**7. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_validation_report.json` – detailné výsledky validácie
- `VALIDATION_REPORT.txt` – textový prehľad pre klienta

## Výsledek

Validované súbory organizované v `${CASE_ID}_consolidated/validation/`: podadresáre `valid/`, `repairable/`, `corrupted/`. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje do rozhodovania o oprave.

## Reference

NIST SP 800-86 – Section 3.1.3 (Data Analysis)
ISO/IEC 27037:2012 – Section 7.3 (Data quality assessment)
ImageMagick Documentation (https://imagemagick.org/)
LibJPEG / JPEGInfo Documentation

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)