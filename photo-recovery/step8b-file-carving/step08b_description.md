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

Skript spustí PhotoRec na forenznom obraze a vykoná validáciu, deduplikáciu a organizáciu nájdených súborov. Krok sa vykonáva pri stratégii `file_carving` alebo `hybrid` — pri `hybrid` dopĺňa výsledky kroku Filesystem Recovery.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptfilecarving PHOTORECOVERY-2025-01-26-001
```

Skript načíta súbor `PHOTORECOVERY-2025-01-26-001_filesystem_analysis.json` z predošlého kroku a overí odporúčanú metódu. Pri `filesystem_scan` odmietne pokračovať – analytik musí spustiť krok Filesystem Recovery. Pri `hybrid` pokračuje normálne.

**2. Overenie nástrojov:**

Skript overí dostupnosť `photorec` (balíček testdisk), `file`, `identify` (ImageMagick) a `exiftool`. Inštalácia: `sudo apt-get install testdisk imagemagick libimage-exiftool-perl`.

**3. PhotoRec carving:**

Skript vygeneruje konfiguráciu a spustí PhotoRec na forenznom obraze. Čas skenu závisí od veľkosti média – flash médiá (8–64 GB) 5–30 minút, HDD (500 GB+) 2–8 hodín. PhotoRec ukladá výsledky do `recup_dir.*` adresárov.

**4. Validácia a deduplikácia:**

Pre každý carved súbor skript overí minimálnu veľkosť (100 B), typ cez `file -b` a čitateľnosť cez `identify`. Validné súbory prechádzajú SHA-256 deduplikáciou. Výsledky sa triedia do `organized/`, `corrupted/`, `quarantine/` a `duplicates/`.

**5. EXIF extrakcia a organizácia:**

Pre každý unikátny súbor skript extrahuje EXIF metadáta a uloží ich do `metadata/`. Súbory sú presunuté do podadresárov podľa formátu (`jpg/`, `png/`, `tiff/`, `raw/`, `other/`) a premenované na `PHOTORECOVERY-2025-01-26-001_{typ}_{seq:06d}.ext`.

**6. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `fileCarvingRecovery` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "fileCarvingRecovery",
  "properties": {
    "recoveryMethod": "file_carving",
    "imagePath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd",
    "outputDirectory": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_carved",
    "carvedTotal": 520,
    "validImages": 298,
    "corrupted": 41,
    "duplicates": 138,
    "quarantine": 43,
    "validationRate": 57.3,
    "duplicationRate": 26.5,
    "metadataExtracted": true,
    "reportPath": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_carving_report.json",
    "completedAt": "2025-01-26T20:15:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step08b-file-carving",
    "action": "File carving completed – 298 valid images recovered, 138 duplicates removed",
    "analyst": "Jan Novotny",
    "timestamp": "2025-01-26T20:15:00Z",
    "notes": null
  }
}
```

## Výsledek

Obnovené súbory organizované podľa formátu v `PHOTORECOVERY-2025-01-26-001_carved/organized/` (`jpg/`, `png/`, `tiff/`, `raw/`, `other/`), poškodené v `corrupted/`, duplikáty v `duplicates/`. Zachované: EXIF metadáta a obsah fotografií. Stratené: pôvodné názvy súborov, adresárová štruktúra a FS timestamps. Úspešnosť validácie typicky 50–65 %, 20–30 % duplikátov. JSON report `PHOTORECOVERY-2025-01-26-001_carving_report.json` a textový `CARVING_REPORT.txt` obsahujú štatistiky a katalóg súborov. Aktualizovaný case JSON súbor s uzlom `fileCarvingRecovery` a ďalším záznamom `chainOfCustody`. Workflow pokračuje do kroku Katalogizácia fotografií.

## Reference

NIST SP 800-86 – Section 3.1.2.3 (Data Carving)
Brian Carrier: File System Forensic Analysis – Chapter 14
PhotoRec Documentation (https://www.cgsecurity.org/wiki/PhotoRec)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)