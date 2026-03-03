# Detaily testu

## Úkol

Vytvoriť záverečnú správu pre klienta aj technické detaily pre expertov.

## Obtiažnosť

Stredná

## Časová náročnosť

10 minút

## Automatický test

Áno

## Popis

Záverečná správa konsoliduje výstupy všetkých predchádzajúcich krokov do jedného dokumentu. Načíta `validation_report.json` (povinné) a voliteľne `exif_database.json` a `repair_report.json`, a zostaví 10-sekčnú správu. Výstupom je `FINAL_REPORT.json`, voliteľný `FINAL_REPORT.pdf` a `README.txt` pre klienta.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptfinalreport PHOTORECOVERY-2025-01-26-001
```

Skript načíta nasledujúce vstupy:
- `PHOTORECOVERY-2025-01-26-001_validation_report.json` (povinné)
- `PHOTORECOVERY-2025-01-26-001_exif_analysis/PHOTORECOVERY-2025-01-26-001_exif_database.json` (voliteľné)
- `PHOTORECOVERY-2025-01-26-001_repair_report.json` (voliteľné)

Absencia voliteľných súborov nespôsobí chybu – príslušné sekcie reportu sa jednoducho vynechajú.

**2. Zostavenie 10-sekčnej správy:**

Každá sekcia má dedikovanú metódu: zhrnutie pre klienta, informácie o prípade, informácie o dôkaze, metodológia, časový priebeh, výsledky, technické detaily, zabezpečenie kvality, reťazec úschovy, podpisy.

**3. PDF správa (voliteľná):**

Ak je nainštalovaný `reportlab`, vygeneruje dokument formátu A4 s titulnou stranou, tabuľkami a blokom podpisov. Bez `reportlab` sa krok preskočí.

**4. Klientská dokumentácia:**

`README.txt` s inštrukciami pre klienta a `delivery_checklist.json` so statusom položiek (peer review a podpisy sú PENDING).

**5. Záverečné uloženie:**

`FINAL_REPORT.json` s 10 sekciami obsahuje všetky výsledky, reťazec úschovy a technické detaily v jednom súbore.

**6. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `finalReport` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "finalReport",
  "properties": {
    "totalPhotosRecovered": 363,
    "integrityScore": 89.3,
    "qualityRating": "Very Good",
    "sectionsGenerated": 10,
    "pdfGenerated": true,
    "reportPath": "/var/forensics/recovered/PHOTORECOVERY-2025-01-26-001_final_report/FINAL_REPORT.json",
    "completedAt": "2025-01-26T23:30:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step14-final-report",
    "action": "Záverečná správa vygenerovaná – 363 fotografií obnovených, integrita 89.3%, hodnotenie: Very Good",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T23:30:00Z",
    "notes": "Kontrola a podpisy sú povinné pred odovzdaním klientovi"
  }
}
```

## Výsledek

Adresár `PHOTORECOVERY-2025-01-26-001_final_report/` s: `FINAL_REPORT.json` (10 sekcií), `FINAL_REPORT.pdf` (voliteľný), `README.txt`, `delivery_checklist.json`. Kontrola nadriadeným analytikom a podpisy sú povinné pred odovzdaním. Aktualizovaný case JSON súbor s uzlom `finalReport` a ďalším záznamom `chainOfCustody`.

## Reference

ISO/IEC 27037:2012 – Digital evidence handling
NIST SP 800-86 – Forensic Techniques
ACPO Good Practice Guide
SWGDE Best Practices

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)