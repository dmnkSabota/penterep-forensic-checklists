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

PhotoRec obnoví všetky typy súborov, ktoré v obraze nájde – filtrovanie na obrazové formáty prebieha v nasledujúcom kroku validácie. Výstup postupu sa priebežne zobrazuje na terminál a zaznamenáva do log súboru `{CASE_ID}_photorec.log`. Čas behu závisí od veľkosti média (5 minút až 8 hodín).

**4. Validácia a deduplikácia:**

Po dokončení PhotoRec skript automaticky:
- Prefiltruje nájdené súbory podľa prípony (len obrazové formáty z `IMAGE_EXTENSIONS`)
- Pre každý kandidát vykoná SHA-256 deduplikáciu (duplicitné súbory presunie do `duplicates/`)
- Validuje každý unikátny súbor: `file -b` → `identify` (ImageMagick)
- Platné súbory presunie do `valid/<format>/` (jpg/, png/, tiff/, raw/, other/)
- Poškodené súbory presunie do `corrupted/`

**5. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky file carving do dokumentácie prípadu:
- Metóda obnovy – file_carving / hybrid
- Celkový počet carved súborov (z PhotoRec)
- Počet validných obrazových súborov
- Počet poškodených súborov
- Počet duplikátov
- Miera validácie (%)
- Miera duplikácie (%)

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T15:00:00Z",
  "analyst": "Meno Analytika",
  "action": "File carving dokončený – nájdených N platných súborov, M duplikátov"
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

NIST SP 800-86 – Section 3.1.2.3 (Data Carving)
Brian Carrier: File System Forensic Analysis – Chapter 14
PhotoRec Documentation (https://www.cgsecurity.org/wiki/PhotoRec)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)