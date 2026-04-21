# Detaily testu

## Úkol

Využiť funkčný súborový systém na identifikáciu a obnovu obrazových súborov.

## Obtiažnosť

Stredná

## Časová náročnosť

60 minút

## Automatický test

Áno

## Popis

Filesystem recovery využíva zachovanú adresárovú štruktúru forenzného obrazu na identifikáciu a extrakciu obrazových súborov pomocou nástrojov `fls` a `icat` z balíka The Sleuth Kit. Pôvodné názvy súborov, adresárová štruktúra a FS timestamps sú zachované. Vykonáva sa pri stratégii `filesystem_scan` alebo `hybrid` (určenej analýzou súborového systému).

## Jak na to

**1. Overenie stratégie a príprava:**

Z výstupu analýzy súborového systému skontrolujte odporúčanú stratégiu – musí byť `filesystem_scan` alebo `hybrid`. Pri `file_carving` tento krok preskočte a pokračujte File Carving.

Overte dostupnosť nástrojov:
```bash
which fls icat file identify exiftool
```
Inštalácia (ak chýbajú):
```bash
sudo apt-get install sleuthkit imagemagick libimage-exiftool-perl
```

Nastavte premenné:
```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
IMAGE="/forenzne/pripady/${CASE_ID}/${CASE_ID}.dd"
OFFSET=0          # z mmls výstupu (analýza súborového systému)
OUTPUT_DIR="/forenzne/pripady/${CASE_ID}/${CASE_ID}_recovered"
mkdir -p "${OUTPUT_DIR}/active" "${OUTPUT_DIR}/deleted" "${OUTPUT_DIR}/corrupted" "${OUTPUT_DIR}/metadata"
```

**2. Skenovanie súborového systému (`fls`):**

Rekurzívne vypíšte všetky záznamy vrátane vymazaných:
```bash
fls -r -o ${OFFSET} "${IMAGE}" > /tmp/fls_all.txt
```
Prefiltrujte na obrazové prípony:
```bash
grep -iE '\.(jpg|jpeg|png|tiff?|bmp|gif|raw|cr2|nef|arw|dng|heic|webp)$' /tmp/fls_all.txt > /tmp/fls_images.txt
```
Spočítajte aktívne súbory (riadky bez `*`) a vymazané (riadky s `*`).

**3. Extrakcia (`icat`) a validácia:**

Pre každý súbor z `/tmp/fls_images.txt` extrahovajte obsah pomocou `icat`. Inóde číslo je číselná hodnota v druhom stĺpci výstupu `fls`:
```bash
icat -o ${OFFSET} "${IMAGE}" INODE_NUMBER > "${OUTPUT_DIR}/active/nazov_suboru.jpg"
```

Pre každý extrahovaný súbor vykonajte trojfázovú validáciu:
1. Nenulová veľkosť: `ls -la subor`
2. Typ obsahu: `file -b subor` – musí vrátiť typ obrazu
3. Čitateľná štruktúra: `identify subor` (ImageMagick) – musí prejsť bez chyby

Podľa výsledku presuňte súbor do `active/`, `deleted/` alebo `corrupted/`.

**4. Extrakcia metadát:**

Pre každý validný súbor extrahujte FS timestamps a EXIF metadáta:
```bash
stat subor
exiftool -json subor > "${OUTPUT_DIR}/metadata/nazov_suboru.json"
```

**5. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky filesystem recovery do dokumentácie prípadu:
- Metóda obnovy – filesystem_scan / hybrid
- Počet prehľadaných súborov
- Počet obnovených aktívnych súborov
- Počet obnovených vymazaných súborov
- Počet poškodených súborov
- Úspešnosť obnovy aktívnych súborov (%)
- Úspešnosť obnovy vymazaných súborov (%)
- Extrakcia metadát – áno / nie
- Nutnosť následného File Carving – áno / nie (pri `hybrid`)

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T14:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Filesystem recovery dokončená – obnovených N súborov (X aktívnych, Y vymazaných)"
}
```

**6. Archivácia výstupov:**

Uložte súhrn výsledkov do `${CASE_ID}_recovery_report.json` a archivujte ho v dokumentácii prípadu.

## Výsledek

Obnovené súbory uložené v `${CASE_ID}_recovered/`: aktívne v `active/`, vymazané v `deleted/`, čiastočne poškodené v `corrupted/`. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje do File Carving (ak `hybrid`) alebo priamo do konsolidácie fotografií.

## Reference

ISO/IEC 27037:2012 – Section 7.3 (Data Extraction)
NIST SP 800-86 – Section 3.1.2.2 (File System Recovery)
The Sleuth Kit Documentation (fls, icat)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)