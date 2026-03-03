# Detaily testu

## Úkol

Je potrebná oprava poškodených fotografií ?

## Obtiažnosť

Jednoduchá

## Časová náročnosť

1 minúta

## Automatický test

Áno

## Popis

Skript rozhodne, či má zmysel pokúsiť sa o opravu poškodených súborov. Načíta výsledky validácie a na základe piatich prioritných pravidiel určí stratégiu: `perform_repair` alebo `skip_repair`.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptrepairdecision PHOTORECOVERY-2025-01-26-001
```

Skript načíta `PHOTORECOVERY-2025-01-26-001_validation_report.json` a extrahuje štatistiky: počet validných, poškodených a neopraviteľných súborov, integrity score a zoznam súborov odporúčaných na opravu.

**2. Odhad úspešnosti opravy:**

Pre každý opraviteľný súbor skript priradí empirickú mieru úspešnosti podľa typu poškodenia (truncated 85 %, corrupt_segments 60 %, corrupt_data 40 %, fragmented 15 %) a vypočíta priemer naprieč všetkými súbormi.

**3. Aplikácia rozhodovacích pravidiel:**

Skript prejde päť pravidiel v poradí a zastaví sa pri prvom, ktoré platí: R1 – žiadne poškodené súbory → preskočiť, R2 – žiadny súbor nie je opraviteľný → preskočiť, R3 – menej ako 50 validných súborov → opraviť (každá ďalšia fotografia má vysokú hodnotu), R4 – odhadovaná úspešnosť ≥ 50 % → opraviť, R5 – inak → preskočiť.

**4. Výpočet očakávaného výsledku:**

Ak sa rozhodne opravovať, skript vypočíta koľko súborov pravdepodobne pribudne po oprave a aký bude výsledný celkový počet validných fotografií. Ak sa oprava preskočí, počty zostávajú nezmenené.

**5. Uloženie rozhodnutia:**

Skript uloží `PHOTORECOVERY-2025-01-26-001_repair_decision.json` so stratégiou, odôvodnením, úrovňou istoty a očakávaným výsledkom.

**6. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `repairDecision` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "repairDecision",
  "properties": {
    "strategy": "perform_repair",
    "confidence": "high",
    "reasoning": "Estimated success rate 72.3% ≥ 50% threshold",
    "repairableFiles": 29,
    "estimatedSuccessRate": 72.3,
    "expectedAdditionalFiles": 21,
    "finalExpectedCount": 362,
    "completedAt": "2025-01-26T22:05:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step11-repair-decision",
    "action": "Repair decision: perform_repair – estimated 21 additional files (72.3% success rate)",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T22:05:00Z",
    "notes": null
  }
}
```

## Výsledek

`PHOTORECOVERY-2025-01-26-001_repair_decision.json` so záverom: či sa oprava vykoná alebo preskočí, s akою istotou, prečo a koľko fotografií sa po prípadnej oprave očakáva. Čistá analytická operácia – žiadne súbory sa nekopírujú ani nemenia. Aktualizovaný case JSON súbor s uzlom `repairDecision` a ďalším záznamom `chainOfCustody`. Workflow pokračuje do kroku Oprava fotografií (ak `perform_repair`) alebo priamo do kroku EXIF analýza (ak `skip_repair`).

## Reference

ISO/IEC 27037:2012 – Section 7.6 (Decision making)
NIST SP 800-86 – Section 3.2 (Analysis decisions)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)