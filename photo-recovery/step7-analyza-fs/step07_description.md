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

Skript automaticky načíta cestu k forenzném obrazu zo súboru `PHOTORECOVERY-2025-01-26-001_verification.json`.

```bash
ptfilesystemanalysis PHOTORECOVERY-2025-01-26-001
```

**2. Analýza partičnej tabuľky (`mmls`):**

Skript detekuje typ tabuľky (DOS/MBR, GPT) a zoznam partícií s ich offsetmi. Ak `mmls` zlyhá, predpokladá sa superfloppy formát – celé médium je jeden súborový systém bez partičnej tabuľky (typické pre USB flash disky a SD karty).

**3. Analýza súborového systému (`fsstat`) a adresárovej štruktúry (`fls`):**

Pre každú partíciu skript extrahuje metadáta súborového systému: typ (FAT32, exFAT, NTFS, ext4...), volume label, UUID, veľkosť sektora a klastra. Následne rekurzívne listuje adresárovú štruktúru vrátane vymazaných súborov (označené `*`) a spočíta aktívne a vymazané obrazové súbory (.jpg, .png, .raw, .cr2, .nef a ďalšie).

**4. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `filesystemAnalysis` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "filesystemAnalysis",
  "properties": {
    "imagePath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd",
    "partitionTable": "DOS/MBR",
    "partitions": [
      {
        "index": 0,
        "offsetSectors": 0,
        "type": "FAT32",
        "status": "recognized",
        "volumeLabel": "SANDISK",
        "uuid": null,
        "sectorSize": 512,
        "clusterSize": 4096
      }
    ],
    "filesystemStatus": "recognized",
    "directoryReadable": true,
    "activeImageFiles": 142,
    "deletedImageFiles": 38,
    "recoveryStrategy": "filesystem_scan",
    "completedAt": "2025-01-26T14:45:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step07-analyza-suboroveho-systemu",
    "action": "Filesystem analysis completed – FAT32 recognized, filesystem_scan strategy selected",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T14:45:00Z",
    "notes": null
  }
}
```

Hodnota `recoveryStrategy` určuje postup v nasledujúcom kroku: `filesystem_scan` (rozpoznaný FS + čitateľná štruktúra), `file_carving` (nerozpoznaný FS), alebo `hybrid` (rozpoznaný FS ale poškodená štruktúra).

## Výsledek

Typ súborového systému identifikovaný, stav a čitateľnosť adresárovej štruktúry overené. Skript uloží `PHOTORECOVERY-2025-01-26-001_filesystem_analysis.json` s kompletným výsledkom analýzy vrátane partition table, FS typu, počtu obrazových súborov a odporúčanej recovery stratégie. Aktualizovaný case JSON súbor s uzlom `filesystemAnalysis` a ďalším záznamom `chainOfCustody`. Workflow pokračuje do nasledujúceho kroku (Rozhodnutie o stratégii obnovy).

## Reference

ISO/IEC 27037:2012 – Section 7 (Analysis of digital evidence)
NIST SP 800-86 – Section 3.1.2 (Examination Phase – Filesystem analysis)
The Sleuth Kit Documentation – mmls, fsstat, fls tools
Brian Carrier: File System Forensic Analysis (2005)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)