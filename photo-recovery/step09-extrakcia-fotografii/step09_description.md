# Detaily testu

## Úkol

Spojiť obnovené fotografie do jedného deduplikovaného datasetu a vytvoriť master katalóg.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Áno

## Popis

Skript zjednotí výstupy z krokov obnovy do jedného organizovaného datasetu pomocou SHA-256 deduplikácie naprieč zdrojmi a vytvorí master katalóg so štatistikami. Krok sa vykonáva vždy — pri `filesystem_scan` spracuje jeden zdroj, pri `hybrid` oba.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptrecoveryconsolidation PHOTORECOVERY-2025-01-26-001
```

Skript overí existenciu `PHOTORECOVERY-2025-01-26-001_recovered/` (filesystem recovery) a `PHOTORECOVERY-2025-01-26-001_carved/organized/` (file carving). Ak žiadny zdroj neexistuje, odmietne pokračovať.

**2. Inventarizácia:**

Pre každý dostupný zdroj skript rekurzívne naskenuje obrazové súbory (`.jpg`, `.png`, `.raw` a ďalšie) a zaznamenáva cestu, veľkosť, príponu a zdroj (`fs_based` / `carved`).

**3. SHA-256 hashovanie a deduplikácia:**

Pre každý súbor sa vypočíta SHA-256 odtlačok. Ak rovnaký hash existuje v oboch zdrojoch, FS-based kópia zostane a carved kópia sa skopíruje do `duplicates/` pre auditný zámer. Typicky 15–25 % súborov pri hybridnom prístupe sú duplikáty.

**4. Kopírovanie a organizácia:**

Unikátne súbory sa skopírujú do `PHOTORECOVERY-2025-01-26-001_consolidated/`. Adresárová štruktúra je dvojúrovňová – súbory sa triedia najprv podľa zdroja, potom podľa formátu:

```
PHOTORECOVERY-2025-01-26-001_consolidated/
├── fs_based/
│   ├── jpg/
│   ├── png/
│   ├── tiff/
│   ├── raw/
│   └── other/
├── carved/
│   ├── jpg/
│   ├── png/
│   ├── tiff/
│   ├── raw/
│   └── other/
└── duplicates/
```

FS-based súbory zachovávajú pôvodný názov (s kolíznou ochranou), carved súbory dostanú systematický názov `PHOTORECOVERY-2025-01-26-001_{typ}_{seq:06d}.ext`.

**5. Master katalóg:**

Skript uloží `PHOTORECOVERY-2025-01-26-001_consolidated/master_catalog.json` s kompletným inventárom (ID, názov, hash, veľkosť, formát, zdroj, cesta) a štatistikami. Textový report `CONSOLIDATION_REPORT.txt` obsahuje prehľad pre klienta.

**6. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `recoveryConsolidation` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "recoveryConsolidation",
  "properties": {
    "sourceFsBased": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_recovered",
    "sourceCarved": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_carved/organized",
    "outputDirectory": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_consolidated",
    "totalFromFsBased": 173,
    "totalFromCarved": 298,
    "duplicatesRemoved": 89,
    "finalUniqueFiles": 382,
    "datasetSizeBytes": 1847392841,
    "masterCatalogPath": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_consolidated/master_catalog.json",
    "completedAt": "2025-01-26T21:00:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step09-recovery-consolidation",
    "action": "Recovery consolidation completed – 382 unique files from 2 sources, 89 duplicates removed",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T21:00:00Z",
    "notes": null
  }
}
```

## Výsledek

Konsolidovaný dataset v `PHOTORECOVERY-2025-01-26-001_consolidated/`: podadresáre `fs_based/{jpg,png,tiff,raw,other}/` a `carved/{jpg,png,tiff,raw,other}/` organizované podľa zdroja aj formátu, `duplicates/` pre auditné kópie. `PHOTORECOVERY-2025-01-26-001_consolidated/master_catalog.json` obsahuje kompletný inventár všetkých súborov. Aktualizovaný case JSON súbor s uzlom `recoveryConsolidation` a ďalším záznamom `chainOfCustody`. Workflow pokračuje do kroku Validácia integrity fotografií.

## Reference

ISO/IEC 27037:2012 – Section 7.3 (Data consolidation)
NIST SP 800-86 – Section 3.1.3 (Analysis)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)