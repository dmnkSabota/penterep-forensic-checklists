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

Skript načíta stratégiu obnovy z uzla `filesystemAnalysis` (Krok 7) a overí odporúčanú metódu. Pri `hybrid` pokračuje normálne a na konci upozorní na nutnosť spustiť aj krok File Carving.

**2. Overenie nástrojov:**

Skript overí dostupnosť `fls` a `icat` (The Sleuth Kit), `file` (detekcia typu), `identify` (ImageMagick), `exiftool` (EXIF metadáta). Inštalácia: `sudo apt-get install sleuthkit imagemagick libimage-exiftool-perl`.

**3. Skenovanie súborového systému (`fls`):**

Skript rekurzívne vypíše všetky záznamy vrátane vymazaných (označené `*`). Výsledok sa prefiltruje na obrazové prípony (.jpg, .png, .tiff, .raw, .cr2, .nef, .arw, .dng a ďalšie) a rozdelí na aktívne a vymazané súbory.

**4. Extrakcia (`icat`) a validácia:**

Pre každý súbor skript spustí `icat` a uloží výstup so zachovaním pôvodnej adresárovej cesty. Každý extrahovaný súbor sa validuje v troch fázach: nenulová veľkosť → `file -b` potvrdí typ obrazu → `identify` potvrdí čitateľnú štruktúru. Výsledok je zatriedený do `active/`, `deleted/`, alebo `corrupted/`.

**5. Extrakcia metadát:**

Pre každý validný súbor skript extrahuje FS timestamps (mtime, atime, ctime) a EXIF metadáta (`exiftool -json`). Metadáta sa uložia ako individuálny JSON súbor do `metadata/`.

**6. Výsledky v uzle filesystemRecovery:**

Skript automaticky zapíše výsledky do uzla `filesystemRecovery` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Metóda obnovy – filesystem_scan / hybrid
- Počet prehľadaných súborov
- Počet obnovených aktívnych súborov
- Počet obnovených vymazaných súborov
- Počet poškodených súborov
- Úspešnosť obnovy aktívnych súborov (%)
- Úspešnosť obnovy vymazaných súborov (%)
- Extrakcia metadát – áno / nie
- Nutnosť následného File Carving – áno / nie (pri `hybrid`)

**7. Archivácia výstupov:**

Skript automaticky nahrá nasledujúci súbor do záložky **Přílohy** projektu:
- `PHOTORECOVERY-2025-01-26-001_recovery_report.json` – kompletný report obnovy

## Výsledek

Obnovené súbory uložené v `PHOTORECOVERY-2025-01-26-001_recovered/`: aktívne v `active/`, vymazané v `deleted/`, čiastočne poškodené v `corrupted/`. Výsledky zaznamenané v uzle `filesystemRecovery`. Workflow pokračuje do kroku File Carving (ak `hybrid`) alebo priamo do kroku Katalogizácia fotografií.

## Reference

ISO/IEC 27037:2012 – Section 7.3 (Data Extraction)
NIST SP 800-86 – Section 3.1.2.2 (File System Recovery)
The Sleuth Kit Documentation (fls, icat)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)