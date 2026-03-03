# Detaily testu

## Úkol

Oprava identifikovaných poškodených fotografií pomocou automatizovaných techník.

## Obtiažnosť

Stredná

## Časová náročnosť

45 minút

## Automatický test

Áno

## Popis

Skript sa pokúsi opraviť každý súbor z `filesNeedingRepair` pomocou techniky zodpovedajúcej typu poškodenia. Zdrojové súbory v `corrupted/` zostávajú nedotknuté – oprava prebieha na pracovnej kópii.

## Jak na to

**1. Overenie rozhodnutia o oprave:**

Skript ako prvý krok načíta `PHOTORECOVERY-2025-01-26-001_repair_decision.json` a overí, že stratégia je `perform_repair`. Ak súbor neexistuje alebo stratégia je `skip_repair`, skript odmietne pokračovať

**2. Spustenie skriptu:**

```bash
ptphotorepair PHOTORECOVERY-2025-01-26-001
```

Skript načíta `PHOTORECOVERY-2025-01-26-001_validation_report.json` a extrahuje `filesNeedingRepair` – zoznam súborov s typom poškodenia a odporúčanou technikou.

**3. Kontrola nástrojov:**

PIL/Pillow je povinný (`LOAD_TRUNCATED_IMAGES = True`). Voliteľné: `jpeginfo`.

**4. Smerovanie a oprava:**

Pre každý súbor skript vytvorí pracovnú kópiu a aplikuje príslušnú techniku. Výsledok opravy je validovaný pomocou PIL a jpeginfo.

**5. Organizácia výstupov:**

Úspešne opravené súbory sa presunú do `PHOTORECOVERY-2025-01-26-001_repair/repaired/`, neúspešné do `failed/`. Originál v `corrupted/` zostáva nedotknutý.

**6. Report:**

Skript uloží `PHOTORECOVERY-2025-01-26-001_repair_report.json` a `PHOTORECOVERY-2025-01-26-001_REPAIR_REPORT.txt` so štatistikami podľa typu poškodenia a detailom každej opravy.

**7. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `photoRepair` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "photoRepair",
  "properties": {
    "sourceDirectory": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_validation/corrupted",
    "outputDirectory": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_repair",
    "totalAttempted": 29,
    "successfulRepairs": 22,
    "failedRepairs": 7,
    "successRate": 75.9,
    "repairReportPath": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_repair_report.json",
    "completedAt": "2025-01-26T23:00:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step12-photo-repair",
    "action": "Photo repair completed – 22/29 successful (75.9% success rate)",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T23:00:00Z",
    "notes": null
  }
}
```

## Výsledek

Opravené súbory v `PHOTORECOVERY-2025-01-26-001_repair/repaired/` (pripravené na EXIF analýzu), neopraviteľné v `failed/`. `PHOTORECOVERY-2025-01-26-001_repair_report.json` a `PHOTORECOVERY-2025-01-26-001_REPAIR_REPORT.txt` so štatistikami a detailom každej opravy. Aktualizovaný case JSON súbor s uzlom `photoRepair` a ďalším záznamom `chainOfCustody`. Workflow pokračuje do kroku EXIF analýza.

## Reference

ISO/IEC 10918-1 – JPEG Standard (ITU-T T.81)
JFIF Specification v1.02
NIST SP 800-86 – Section 3.1.4 (Data Recovery and Repair)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)