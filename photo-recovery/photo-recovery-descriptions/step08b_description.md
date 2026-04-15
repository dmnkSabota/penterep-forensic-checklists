# Detaily testu

## Úkol

Obnoviť obrazové súbory priamym vyhľadávaním byte signatúr v raw dátach forenzného obrazu.

## Obtiažnosť

Stredná

## Časová náročnosť

30 minút – 8 hodín (závisí od veľkosti média)

## Automatický test

Áno

## Popis

File carving vyhľadáva súbory priamo v raw dátach forenzného obrazu podľa ich byte signatúr (magic bytes) – nezávisle od súborového systému. Tento prístup funguje aj vtedy, keď je súborový systém úplne poškodený alebo neexistuje. Nevýhodou je strata pôvodných názvov súborov, adresárovej štruktúry a FS timestamps.

Vykonáva sa pri stratégii `file_carving` alebo `hybrid` (určenej analýzou súborového systému). Pri stratégii `filesystem_scan` tento krok preskočte.

## Jak na to

**1. Overenie stratégie a príprava:**

Z výstupu analýzy súborového systému skontrolujte odporúčanú stratégiu – musí byť `file_carving` alebo `hybrid`. Pri `filesystem_scan` tento krok preskočte.

Overte dostupnosť nástrojov:
```bash
which photorec file identify exiftool
```
Inštalácia (ak chýbajú):
```bash
sudo apt-get install testdisk imagemagick libimage-exiftool-perl
```

Nastavte premenné:
```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
IMAGE="/forenzne/pripady/${CASE_ID}/${CASE_ID}.dd"
OUTPUT_DIR="/forenzne/pripady/${CASE_ID}/${CASE_ID}_carved"
mkdir -p "${OUTPUT_DIR}"
```

**2. Spustenie PhotoRec:**

PhotoRec je interaktívny nástroj – spustite ho a prejdite nastavením:
```bash
photorec "${IMAGE}"
```
V interaktívnom menu:
- Vyberte forenzný obraz ako zdroj
- Nastavte cieľový adresár na `${OUTPUT_DIR}`
- V „File Formats" ponechajte len obrazové formáty: jpg, png, tiff, bmp, gif, raw, cr2, nef, arw, dng
- Spustite sken (5 minút – 8 hodín podľa veľkosti média)

PhotoRec ukladá výsledky do adresárov `recup_dir.*` v cieľovom adresári.

**3. Validácia nájdených súborov:**

Pre každý nájdený súbor v `recup_dir.*` vykonajte kontrolu:

Minimálna veľkosť:
```bash
find "${OUTPUT_DIR}" -name "*.jpg" -empty -delete
```

Typ obsahu:
```bash
file -b subor     # musí vrátiť typ obrazu, nie "data"
```

Čitateľnosť:
```bash
identify subor    # ImageMagick – musí prejsť bez chyby
```

Platné súbory presuňte do `${OUTPUT_DIR}/organized/`, neplatné do `${OUTPUT_DIR}/corrupted/`.

**4. Deduplikácia (SHA-256):**

Pre každý platný súbor vypočítajte hash:
```bash
sha256sum "${OUTPUT_DIR}/organized/"* | sort > /tmp/carved_hashes.txt
```
Duplicitné súbory (rovnaký hash) presuňte do `${OUTPUT_DIR}/duplicates/` – zachovajte pre auditné účely.

**5. Organizácia a premenovanie:**

Platné unikátne súbory usporiadajte do podadresárov podľa formátu a premenujte na systematický formát:
```
${OUTPUT_DIR}/organized/
├── jpg/    →  ${CASE_ID}_jpg_000001.jpg, ...
├── png/    →  ${CASE_ID}_png_000001.png, ...
├── tiff/
├── raw/
└── other/
```

**6. EXIF extrakcia:**

Pre každý platný súbor extrahujte EXIF metadáta:
```bash
exiftool -json subor > "${OUTPUT_DIR}/metadata/nazov_suboru.json"
```

**7. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky file carving do dokumentácie prípadu:
- Metóda obnovy – file_carving / hybrid
- Celkový počet carved súborov (z PhotoRec)
- Počet validných obrazových súborov
- Počet poškodených súborov
- Počet duplikátov
- Miera validácie (%)
- Miera duplikácie (%)
- Extrakcia metadát – áno / nie

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T15:00:00Z",
  "analyst": "Meno Analytika",
  "action": "File carving dokončený – nájdených N platných súborov, M duplikátov"
}
```

**8. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_carving_report.json` – kompletný report obnovy
- `CARVING_REPORT.txt` – textový katalóg súborov a štatistiky

## Výsledek

Obnovené súbory organizované podľa formátu v `${CASE_ID}_carved/organized/` (jpg/, png/, tiff/, raw/, other/), poškodené v `corrupted/`, duplikáty v `duplicates/`. Zachované: EXIF metadáta a obsah fotografií. Stratené: pôvodné názvy súborov, adresárová štruktúra a FS timestamps. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje do konsolidácie fotografií.

## Reference

NIST SP 800-86 – Section 3.1.2.3 (Data Carving)
Brian Carrier: File System Forensic Analysis – Chapter 14
PhotoRec Documentation (https://www.cgsecurity.org/wiki/PhotoRec)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)