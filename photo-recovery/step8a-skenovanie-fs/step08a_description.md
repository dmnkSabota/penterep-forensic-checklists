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

Skript identifikuje všetky obrazové súbory (aktívne aj vymazané) pomocou `fls` a extrahuje ich pomocou `icat` so zachovaním pôvodnej adresárovej štruktúry, názvov súborov a metadát. Krok sa vykonáva pri stratégii `filesystem_scan` alebo `hybrid`.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptfilesystemrecovery PHOTORECOVERY-2025-01-26-001
```

Skript načíta súbor `PHOTORECOVERY-2025-01-26-001_filesystem_analysis.json` z predošlého kroku a overí odporúčanú metódu. Pri `hybrid` pokračuje normálne a na konci upozorní na nutnosť spustiť aj krok File Carving.

**2. Overenie nástrojov:**

Skript overí dostupnosť `fls` a `icat` (The Sleuth Kit), `file` (detekcia typu), `identify` (ImageMagick), `exiftool` (EXIF metadáta). Inštalácia: `sudo apt-get install sleuthkit imagemagick libimage-exiftool-perl`.

**3. Skenovanie súborového systému (`fls`):**

Skript rekurzívne vypíše všetky záznamy vrátane vymazaných (označené `*`). Výsledok sa prefiltruje na obrazové prípony (.jpg, .png, .tiff, .raw, .cr2, .nef, .arw, .dng a ďalšie) a rozdelí na aktívne a vymazané súbory.

**4. Extrakcia (`icat`) a validácia:**

Pre každý súbor skript spustí `icat` a uloží výstup so zachovaním pôvodnej adresárovej cesty. Každý extrahovaný súbor sa validuje v troch fázach: nenulová veľkosť → `file -b` potvrdí typ obrazu → `identify` potvrdí čitateľnú štruktúru. Výsledok je zatriedený do `active/`, `deleted/`, alebo `corrupted/`.

**5. Extrakcia metadát:**

Pre každý validný súbor skript extrahuje FS timestamps (mtime, atime, ctime) a EXIF metadáta (`exiftool -json`). Metadáta sa uložia ako individuálny JSON súbor do `metadata/`.

**6. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `filesystemRecovery` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "filesystemRecovery",
  "properties": {
    "recoveryMethod": "filesystem_scan",
    "imagePath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd",
    "outputDirectory": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_recovered",
    "filesScanned": 180,
    "activeRecovered": 142,
    "deletedRecovered": 31,
    "corrupted": 7,
    "invalid": 0,
    "successRateActive": 100.0,
    "successRateDeleted": 81.6,
    "metadataExtracted": true,
    "hybridFollowupRequired": false,
    "reportPath": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_recovery_report.json",
    "completedAt": "2025-01-26T15:30:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step08a-filesystem-recovery",
    "action": "Filesystem-based recovery completed – 173 files recovered (142 active, 31 deleted)",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T15:30:00Z",
    "notes": null
  }
}
```

Pri stratégii `hybrid` nastavte `"hybridFollowupRequired": true` – signalizuje, že je potrebné spustiť aj krok File Carving.

## Výsledek

Obnovené súbory uložené v `PHOTORECOVERY-2025-01-26-001_recovered/`: aktívne v `active/`, vymazané v `deleted/`, čiastočne poškodené v `corrupted/`. Aktualizovaný case JSON súbor s uzlom `filesystemRecovery` a ďalším záznamom `chainOfCustody`. Workflow pokračuje do kroku File Carving (ak `hybrid`) alebo priamo do kroku Katalogizácia fotografií.

## Reference

ISO/IEC 27037:2012 – Section 7.3 (Data Extraction)
NIST SP 800-86 – Section 3.1.2.2 (File System Recovery)
The Sleuth Kit Documentation (fls, icat)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)