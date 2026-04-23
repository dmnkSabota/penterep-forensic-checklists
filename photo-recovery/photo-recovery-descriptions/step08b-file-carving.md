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

Skript `ptfilecarving` spúšťa PhotoRec v neinteraktívnom dávkovom režime – bez nutnosti manuálneho prechádzania menu. Filtrovanie obrazových formátov prebieha post-carving počas validácie, nie v samotnom PhotoRec príkaze.

## Jak na to

**1. Overenie stratégie a príprava:**

Z výstupu analýzy súborového systému skontrolujte odporúčanú stratégiu – musí byť `file_carving` alebo `hybrid`. Pri `filesystem_scan` tento krok preskočte.

Overte dostupnosť nástrojov:
```bash
which photorec file identify
```
Inštalácia (ak chýbajú):
```bash
sudo apt-get install testdisk imagemagick
```

**2. Spustenie skriptu:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"

# Iba terminálový výstup
ptfilecarving ${CASE_ID}

# S JSON výstupom pre case.json
ptfilecarving ${CASE_ID} --analyst "Meno Analytika" --json-out ${CASE_ID}_carving.json

# Explicitné zadanie cesty k obrazu (ak analysis file nie je dostupný)
ptfilecarving ${CASE_ID} --image /var/forensics/images/${CASE_ID}.dd --json-out ${CASE_ID}_carving.json

# Simulácia bez spustenia PhotoRec
ptfilecarving ${CASE_ID} --dry-run
```

Skript automaticky načíta cestu k forenzného obrazu z `{CASE_ID}_filesystem_analysis.json` vytvoreného v predchádzajúcom kroku.

**3. Priebeh file carving:**

PhotoRec beží v neinteraktívnom dávkovom režime – spúšťa sa automaticky bez nutnosti manuálneho výberu v menu:
```bash
photorec /log /d <pracovny_adresar> /cmd <forenzny_obraz> search
```

Ak automatický nástroj nie je dostupný, spustite PhotoRec priamo týmto príkazom. Výstup postupu sa priebežne zobrazuje na terminál a zaznamenáva do log súboru `{CASE_ID}_photorec.log`. Čas behu závisí od veľkosti média.

**4. Validácia a deduplikácia:**

Skript automaticky prefiltruje, deduplikuje a validuje výsledky. Ak skript nie je dostupný, vykonajte kroky manuálne:

Prefiltrujte na obrazové prípony:
```bash
find <pracovny_adresar> -type f | grep -iE '\.(jpg|jpeg|png|tiff?|bmp|gif|raw|cr2|nef|arw|dng|heic|webp)$'
```

SHA-256 deduplikácia – identifikujte duplicitné súbory:
```bash
find <pracovny_adresar> -type f | xargs sha256sum | sort | uniq -d -w 64
```

Validácia každého súboru:
```bash
file -b subor
identify subor 2>&1
```

Platné súbory presuňte do `valid/<format>/`, poškodené do `corrupted/`, duplicitné do `duplicates/`.

**5. Zápis výsledkov a aktualizácia CoC:**

Pri použití `--json-out` sa vytvorí JSON s výsledkami. Analytik manuálne skopíruje oba záznamy do `case.json`.

Pridávaný objekt `fileCarvingResult`:
```json
"fileCarvingResult": {
  "timestamp": "2025-01-26T15:00:00Z",
  "analyst": "Meno Analytika",
  "recoveryMethod": "file_carving",
  "totalCarved": 2341,
  "validImageFiles": 1876,
  "corrupted": 312,
  "duplicates": 153,
  "validationRate": 80.1,
  "deduplicationRate": 6.5,
  "outputPath": "/forenzne/pripady/PHOTORECOVERY-2025-01-26-001/PHOTORECOVERY-2025-01-26-001_carved/",
  "photorec_log": "PHOTORECOVERY-2025-01-26-001_photorec.log"
}
```

Nový záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T15:00:00Z",
  "analyst": "Meno Analytika",
  "action": "File carving dokončený – nájdených 1876 platných súborov, 153 duplikátov",
  "mediaSerial": "SN-XXXXXXXX"
}
```

**6. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_carving_report.json` – kompletný report obnovy
- `${CASE_ID}_photorec.log` – log PhotoRec behu
- Adresár `${CASE_ID}_carved/` s organizovanými súbormi

## Výsledek

Obnovené súbory organizované podľa formátu v `${CASE_ID}_carved/valid/<format>/` (jpg/, png/, tiff/, raw/, other/), poškodené v `corrupted/`, duplikáty v `duplicates/`. Zachované: obsah fotografií. Stratené: pôvodné názvy súborov, adresárová štruktúra a FS timestamps. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje do konsolidácie fotografií.

## Reference

ISO/IEC 27042:2015 – Section 5 (Digital evidence analysis)

NIST SP 800-86 – Section 2.2 (Examination)

Brian Carrier: File System Forensic Analysis – Chapter 14

PhotoRec Documentation (https://www.cgsecurity.org/wiki/PhotoRec)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)