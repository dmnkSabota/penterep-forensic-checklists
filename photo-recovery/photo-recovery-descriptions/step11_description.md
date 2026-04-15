# Detaily testu

## Úkol

Rozhodnúť, či má zmysel pokúsiť sa o opravu poškodených fotografií.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

5 minút

## Automatický test

Áno

## Popis

Tento krok analyzuje výsledky validácie integrity a rozhodne, či je nákladovo efektívne pokúsiť sa o opravu poškodených súborov. Načíta výsledky z validácie integrity a na základe piatich prioritných pravidiel určí stratégiu: `perform_repair` (pokračuje do opravy fotografií) alebo `skip_repair` (preskočí opravu a pokračuje priamo na EXIF analýzu). Výsledok je čisto analytický – žiadne súbory sa v tomto kroku nemenia.

## Jak na to

**1. Prečítanie výsledkov validácie:**

Z výstupu validácie integrity si zapíšte:
- Počet VALID súborov
- Počet REPAIRABLE súborov
- Počet CORRUPTED súborov
- Validation rate (%)
- Typy poškodení pre REPAIRABLE súbory

**2. Odhad úspešnosti opravy:**

Pre každý súbor v kategórii REPAIRABLE priraďte empirickú mieru úspešnosti podľa typu poškodenia:

| Typ poškodenia | Odhadovaná úspešnosť |
|----------------|----------------------|
| truncated | 85 % |
| invalid_header | 85 % |
| corrupt_segments | 60 % |
| corrupt_data | 40 % |
| fragmented | 15 % |
| unknown | 30 % |

Vypočítajte vážený priemer naprieč všetkými REPAIRABLE súbormi.

**3. Aplikácia rozhodovacích pravidiel:**

Prechádzajte pravidlá v poradí a zastavte sa pri prvom, ktoré platí:

| # | Podmienka | Rozhodnutie | Priorita |
|---|-----------|-------------|----------|
| R1 | Žiadne CORRUPTED súbory | `skip_repair` | Vysoká |
| R2 | Žiadne REPAIRABLE súbory | `skip_repair` | Vysoká |
| R3 | Menej ako 50 VALID súborov | `perform_repair` | Stredná |
| R4 | Odhadovaná úspešnosť ≥ 50 % | `perform_repair` | Vysoká |
| R5 | Inak | `skip_repair` | Vysoká |

**4. Výpočet očakávaného výsledku:**

Ak je rozhodnutie `perform_repair`:
```
Dodatočné súbory = počet REPAIRABLE × (odhadovaná úspešnosť / 100)
Finálny počet = aktuálne VALID + dodatočné súbory
Zlepšenie (%) = (dodatočné / VALID) × 100
```

**5. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky rozhodnutia do dokumentácie prípadu:
- Stratégia – `perform_repair` / `skip_repair`
- Použité pravidlo – R1 / R2 / R3 / R4 / R5
- Odôvodnenie
- Počet REPAIRABLE súborov
- Odhadovaná úspešnosť opravy (%)
- Očakávaný počet dodatočných súborov (ak perform_repair)
- Finálny očakávaný počet VALID súborov

Pridajte záznam do Chain of Custody:
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

## Výsledek

Čistá analytická operácia – žiadne súbory sa nekopírujú ani nemenia. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje do opravy fotografií (ak `perform_repair`) alebo priamo do EXIF analýzy (ak `skip_repair`).

## Reference

ISO/IEC 27037:2012 – Section 7.6 (Decision making)
NIST SP 800-86 – Section 3.2 (Analysis decisions)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)