# Detaily testu

## Úkol

Overiť fyzickú integritu všetkých obnovených fotografií a rozdeliť ich do kategórií.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Áno

## Popis

Skript načíta master katalóg z predošlého kroku a pre každý súbor vykoná validáciu pomocou dostupných nástrojov. Výsledkom je klasifikácia fotografií do troch kategórií s integrity score a reportom poškodených súborov.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptintegrityvalidation PHOTORECOVERY-2025-01-26-001
```

Skript načíta `PHOTORECOVERY-2025-01-26-001_consolidated/master_catalog.json` a získa zoznam všetkých konsolidovaných súborov na validáciu.

**2. Kontrola nástrojov:**

PIL/Pillow je povinný (`pip install Pillow`). Voliteľné: `jpeginfo`, `pngcheck` – skript použije ak sú dostupné.

**3. Per-file validácia:**

Pre každý súbor skript overí: veľkosť (prázdne súbory = neopraviteľné), čitateľnosť pixelov cez PIL `verify()` + `load()`, a pre JPEG/PNG aj `jpeginfo -c` / `pngcheck -v`. Rozhodovacia logika: ak všetky nástroje prešli → validný, ak niektoré prešli a niektoré zlyhali → poškodený (potenciálne opraviteľný), ak všetky zlyhali → neopraviteľný.

**4. Organizácia výstupov:**

Súbory sa skopírujú do `PHOTORECOVERY-2025-01-26-001_validation/valid/`, `corrupted/` alebo `unrecoverable/`. Zdrojové súbory v konsolidovanom adresári zostávajú nedotknuté.

**5. Analýza poškodení a report:**

Pre každý poškodený súbor skript určí typ chyby (truncated, invalid_header, corrupt_segments, corrupt_data, unknown) a úroveň opraviteľnosti (L1–L5). Ak typ chyby nie je možné určiť, súbor sa klasifikuje ako unknown (L3, vyžaduje manuálnu inšpekciu). Výstupom sú `PHOTORECOVERY-2025-01-26-001_validation_report.json` a `PHOTORECOVERY-2025-01-26-001_VALIDATION_REPORT.txt`.

**6. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `integrityValidation` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "integrityValidation",
  "properties": {
    "sourceDirectory": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_consolidated",
    "outputDirectory": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_validation",
    "totalFilesValidated": 382,
    "valid": 341,
    "corrupted": 29,
    "unrecoverable": 12,
    "integrityScore": 89.3,
    "toolsUsed": ["PIL", "jpeginfo", "pngcheck"],
    "reportPath": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_validation_report.json",
    "completedAt": "2025-01-26T22:00:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step10-integrity-validation",
    "action": "Integrity validation completed – 341 valid, 29 corrupted, 12 unrecoverable (integrity score: 89.3%)",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T22:00:00Z",
    "notes": null
  }
}
```

## Výsledek

Klasifikácia všetkých fotografií do troch kategórií v `PHOTORECOVERY-2025-01-26-001_validation/`: `valid/`, `corrupted/`, `unrecoverable/`. Integrity score (% validných súborov) s rozpisom podľa formátu a zdroja (fs_based vs carved). `PHOTORECOVERY-2025-01-26-001_validation_report.json` a `PHOTORECOVERY-2025-01-26-001_VALIDATION_REPORT.txt` so štatistikami a zoznamom súborov odporúčaných na opravu. Aktualizovaný case JSON súbor s uzlom `integrityValidation` a ďalším záznamom `chainOfCustody`. Workflow pokračuje do kroku Rozhodnutie o oprave fotografií.

## Reference

ISO/IEC 10918-1 – JPEG Standard
PNG Specification – ISO/IEC 15948:2004
NIST SP 800-86 – Section 3.1.3 (Data Validation)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)