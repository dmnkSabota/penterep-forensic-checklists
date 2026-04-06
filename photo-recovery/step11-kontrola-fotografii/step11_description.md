# Detaily testu

## Úkol

Je potrebná oprava poškodených fotografií?

## Obtiažnosť

Jednoduchá

## Časová náročnosť

5 minút

## Automatický test

Áno

## Popis

Skript rozhodne, či má zmysel pokúsiť sa o opravu poškodených súborov. Načíta výsledky validácie z uzla `integrityValidation` (Krok 10) a na základe piatich prioritných pravidiel určí stratégiu: `perform_repair` alebo `skip_repair`. Výsledok je čisto analytický – žiadne súbory sa v tomto kroku nemenia.

## Jak na to

**1. Prečítanie výsledkov validácie:**

Z uzla `integrityValidation` (Krok 10) si zapíšte:
- Počet validných súborov
- Počet poškodených súborov
- Počet neopraviteľných súborov
- Integrity score (%)
- Zoznam `filesNeedingRepair` s typmi poškodení a úrovňami opraviteľnosti (L1–L5)

**2. Odhad úspešnosti opravy:**

Pre každý súbor v `filesNeedingRepair` priraďte empirickú mieru úspešnosti:

| Typ poškodenia | Odhadovaná úspešnosť |
|----------------|----------------------|
| truncated | 85 % |
| corrupt_segments | 60 % |
| corrupt_data | 40 % |
| fragmented | 15 % |
| unknown / invalid_header | 0 % |

Vypočítajte vážený priemer naprieč všetkými opraviteľnými súbormi (L1–L4). Súbory L5 do výpočtu nezahrňujte.

**3. Aplikácia rozhodovacích pravidiel:**

Prechádzajte pravidlá v poradí a zastavte sa pri prvom, ktoré platí:

| # | Podmienka | Rozhodnutie |
|---|-----------|-------------|
| R1 | Žiadne poškodené súbory (corrupted = 0) | `skip_repair` |
| R2 | Žiadny súbor nie je opraviteľný (všetky L5) | `skip_repair` |
| R3 | Menej ako 50 validných súborov | `perform_repair` |
| R4 | Odhadovaná úspešnosť ≥ 50 % | `perform_repair` |
| R5 | Inak | `skip_repair` |

**4. Výpočet očakávaného výsledku:**

Ak `perform_repair`:
- Počet dodatočných súborov = počet opraviteľných × odhadovaná úspešnosť
- Finálny počet = aktuálne validné + dodatočné

**5. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do uzla `repairDecision` v dokumentácii prípadu:
- Stratégia – `perform_repair` / `skip_repair`
- Použité pravidlo – R1 / R2 / R3 / R4 / R5
- Odôvodnenie
- Počet opraviteľných súborov
- Odhadovaná úspešnosť opravy (%)
- Očakávaný počet dodatočných súborov
- Finálny očakávaný počet validných súborov

Pridajte záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T16:05:00Z",
  "analyst": "Meno Analytika",
  "action": "Rozhodnutie o oprave: perform_repair – pravidlo R4, odhadovaná úspešnosť 72 %"
}
```

**6. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_repair_decision.json` – rozhodnutie so stratégiou, odôvodnením a očakávaným výsledkom

---

> **Automatizácia (pripravuje sa):** Skript `ptrepairdecision` bude odhad úspešnosti, aplikáciu pravidiel, zápis uzla `repairDecision` a aktualizáciu CoC vykonávať automaticky.

## Výsledek

Čistá analytická operácia – žiadne súbory sa nekopírujú ani nemenia. Výsledky zaznamenané v uzle `repairDecision`. Workflow pokračuje do Kroku 12 (ak `perform_repair`) alebo priamo do Kroku 13 (ak `skip_repair`).

## Reference

ISO/IEC 27037:2012 – Section 7.6 (Decision making)
NIST SP 800-86 – Section 3.2 (Analysis decisions)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)