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

Skript rozhodne, či má zmysel pokúsiť sa o opravu poškodených súborov. Načíta výsledky validácie z uzla `integrityValidation` (Krok 10) a na základe piatich prioritných pravidiel určí stratégiu: `perform_repair` alebo `skip_repair`.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptrepairdecision PHOTORECOVERY-2025-01-26-001
```

Skript načíta výsledky z uzla `integrityValidation` (Krok 10) a extrahuje štatistiky: počet validných, poškodených a neopraviteľných súborov, integrity score a zoznam súborov odporúčaných na opravu.

**2. Odhad úspešnosti opravy:**

Pre každý opraviteľný súbor skript priradí empirickú mieru úspešnosti podľa typu poškodenia (truncated 85 %, corrupt_segments 60 %, corrupt_data 40 %, fragmented 15 %) a vypočíta priemer naprieč všetkými súbormi.

**3. Aplikácia rozhodovacích pravidiel:**

Skript prejde päť pravidiel v poradí a zastaví sa pri prvom, ktoré platí: R1 – žiadne poškodené súbory → preskočiť, R2 – žiadny súbor nie je opraviteľný → preskočiť, R3 – menej ako 50 validných súborov → opraviť (každá ďalšia fotografia má vysokú hodnotu), R4 – odhadovaná úspešnosť ≥ 50 % → opraviť, R5 – inak → preskočiť.

**4. Výpočet očakávaného výsledku:**

Ak sa rozhodne opravovať, skript vypočíta koľko súborov pravdepodobne pribudne po oprave a aký bude výsledný celkový počet validných fotografií. Ak sa oprava preskočí, počty zostávajú nezmenené.

**5. Výsledky v uzle repairDecision:**

Skript automaticky zapíše výsledky do uzla `repairDecision` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Stratégia – perform_repair / skip_repair
- Úroveň istoty – high / medium / low
- Odôvodnenie
- Počet opraviteľných súborov
- Odhadovaná úspešnosť opravy (%)
- Očakávaný počet dodatočných súborov
- Finálny očakávaný počet validných súborov

**6. Archivácia výstupov:**

Skript automaticky nahrá nasledujúci súbor do záložky **Přílohy** projektu:
- `PHOTORECOVERY-2025-01-26-001_repair_decision.json` – rozhodnutie so stratégiou, odôvodnením a očakávaným výsledkom

## Výsledek

Čistá analytická operácia – žiadne súbory sa nekopírujú ani nemenia. Výsledky zaznamenané v uzle `repairDecision`. Workflow pokračuje do kroku Oprava fotografií (ak `perform_repair`) alebo priamo do kroku EXIF analýza (ak `skip_repair`).

## Reference

ISO/IEC 27037:2012 – Section 7.6 (Decision making)
NIST SP 800-86 – Section 3.2 (Analysis decisions)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)