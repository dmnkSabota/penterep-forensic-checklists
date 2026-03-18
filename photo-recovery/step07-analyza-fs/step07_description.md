# Detaily testu

## Úkol

Analyzovať forenzný obraz média a určiť typ súborového systému, jeho stav, partície a metadáta.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

10 minút

## Automatický test

Áno

## Popis

Analýza súborového systému je prvý krok forenznej analýzy po vytvorení a overení forenzného obrazu. Výsledok priamo určuje stratégiu obnovy: rozpoznaný súborový systém s čitateľnou adresárovou štruktúrou umožňuje filesystem-based recovery (zachováva pôvodné názvy súborov a metadáta), poškodený alebo nerozpoznaný súborový systém vyžaduje file carving (hľadá súbory podľa signatúr v raw dátach).

## Jak na to

**1. Spustenie analýzy:**

Skript automaticky načíta cestu k forenzného obrazu z uzla `hashVerification` (Krok 6):

```bash
ptfilesystemanalysis PHOTORECOVERY-2025-01-26-001
```

**2. Analýza partičnej tabuľky (`mmls`):**

Skript detekuje typ tabuľky (DOS/MBR, GPT) a zoznam partícií s ich offsetmi. Ak `mmls` zlyhá, predpokladá sa superfloppy formát – celé médium je jeden súborový systém bez partičnej tabuľky (typické pre USB flash disky a SD karty).

**3. Analýza súborového systému (`fsstat`) a adresárovej štruktúry (`fls`):**

Pre každú partíciu skript extrahuje metadáta súborového systému: typ (FAT32, exFAT, NTFS, ext4...), volume label, UUID, veľkosť sektora a klastra. Následne rekurzívne listuje adresárovú štruktúru vrátane vymazaných súborov (označené `*`) a spočíta aktívne a vymazané obrazové súbory (.jpg, .png, .raw, .cr2, .nef a ďalšie).

**4. Výsledky v uzle filesystemAnalysis:**

Skript automaticky zapíše výsledky do uzla `filesystemAnalysis` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Typ partičnej tabuľky – DOS/MBR / GPT / superfloppy
- Partície – zoznam s offsetmi, typom FS, stavom, volume label, UUID, veľkosťou sektora a klastra
- Stav súborového systému – recognized / unrecognized / damaged
- Čitateľnosť adresárovej štruktúry – áno / nie
- Počet aktívnych obrazových súborov
- Počet vymazaných obrazových súborov
- Stratégia obnovy – `filesystem_scan` / `file_carving` / `hybrid`

Hodnota stratégie obnovy určuje postup v nasledujúcom kroku:
- `filesystem_scan` – rozpoznaný FS + čitateľná štruktúra
- `file_carving` – nerozpoznaný FS
- `hybrid` – rozpoznaný FS ale poškodená štruktúra

**5. Archivácia výstupov:**

Skript automaticky nahrá nasledujúci súbor do záložky **Přílohy** projektu:
- `PHOTORECOVERY-2025-01-26-001_filesystem_analysis.json` – kompletný výsledok analýzy

## Výsledek

Typ súborového systému identifikovaný, stav a čitateľnosť adresárovej štruktúry overené. Výsledky zaznamenané v uzle `filesystemAnalysis` vrátane partition table, FS typu, počtu obrazových súborov a odporúčanej recovery stratégie. Workflow pokračuje do nasledujúceho kroku.

## Reference

ISO/IEC 27037:2012 – Section 7 (Analysis of digital evidence)
NIST SP 800-86 – Section 3.1.2 (Examination Phase – Filesystem analysis)
The Sleuth Kit Documentation – mmls, fsstat, fls tools
Brian Carrier: File System Forensic Analysis (2005)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)