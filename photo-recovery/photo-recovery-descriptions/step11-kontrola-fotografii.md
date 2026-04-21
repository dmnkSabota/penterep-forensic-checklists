# Detaily testu

## Úkol

Rozhodnúť pre každý REPAIRABLE súbor, či a ako pristúpiť k oprave.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

5 minút

## Automatický test

Áno

## Popis

Tento krok načíta výsledky validácie integrity a pre každý REPAIRABLE súbor určí rozhodnutie na základe empiricky odhadovanej miery úspešnosti opravy podľa typu poškodenia. Výsledok je čisto analytický – žiadne súbory sa v tomto kroku nemenia.

Rozhodnutia: `ATTEMPT_REPAIR` (postúpi do opravy fotografií), `MANUAL_REVIEW` (príznak pre analytika, automatická oprava sa nevykoná), `SKIP` (súbor je považovaný za neopraviteľný).

Miery úspešnosti vychádzajú z empirického testovania autora (50 syntetických testovacích prípadov na typ poškodenia) a sú podporené odkazmi v literatúre: Kessler (2016), Garfinkel et al. (2009), NIST SP 800-86 §4.1.

## Jak na to

**1. Spustenie rozhodovacieho kroku:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"

# Iba terminálový výstup
ptrepairdecision ${CASE_ID}

# S JSON výstupom pre case.json
ptrepairdecision ${CASE_ID} --analyst "Meno Analytika" --json-out ${CASE_ID}_decisions.json

# Explicitná cesta k validation reportu
ptrepairdecision ${CASE_ID} --validation-file /var/forensics/images/${CASE_ID}_integrity_validation.json
```

Skript automaticky načíta `{CASE_ID}_integrity_validation.json` z výstupného adresára.

**2. Rozhodovacia logika:**

Pre každý REPAIRABLE súbor skript priradí odhadovanú mieru úspešnosti opravy podľa typu poškodenia:

| Typ poškodenia | Odhadovaná úspešnosť | Zdroj odhadu |
|---|---|---|
| `missing_footer` | 90 % | Autor; doplnenie EOI/IEND je takmer vždy spoľahlivé ak sú dáta kompletné |
| `invalid_header` | 85 % | Autor; rekonštrukcia SOI + APP0 – závisí od integrity SOS segmentu |
| `corrupt_segments` | 60 % | Autor; vysoká variabilita podľa toho, ktorý segment je poškodený |
| `truncated` | 85 % | Autor; PIL LOAD_TRUNCATED_IMAGES – efektívne pri čiastočnej strate konca súboru |
| `corrupt_data` | 40 % | Kessler (2016); poškodenie v dátovom regióne produkuje viditeľné artefakty |
| `fragmented` | 15 % | Garfinkel et al. (2009); viacfragmentové skladanie zriedka vedie k plne dekódovateľnému obrazu |
| `unknown` | 30 % | Konzervatívny odhad pre neklasifikované prípady |

Na základe miery úspešnosti sa aplikujú pravidlá R1–R5 v poradí, prvé platné pravidlo rozhoduje:

| Pravidlo | Podmienka | Rozhodnutie |
|---|---|---|
| R1 | Úspešnosť ≥ 85 % | `ATTEMPT_REPAIR` |
| R2 | 50 % ≤ úspešnosť < 85 % | `ATTEMPT_REPAIR` |
| R3 | 30 % ≤ úspešnosť < 50 % | `MANUAL_REVIEW` |
| R4 | 15 % ≤ úspešnosť < 30 % | `SKIP` |
| R5 | Úspešnosť < 15 % | `SKIP` |

**3. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky rozhodnutia do dokumentácie prípadu:
- Celkový počet REPAIRABLE súborov
- Počet `ATTEMPT_REPAIR`
- Počet `MANUAL_REVIEW`
- Počet `SKIP`
- Rozloženie podľa typu poškodenia a použitého pravidla

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T16:05:00Z",
  "analyst": "Meno Analytika",
  "action": "Rozhodnutie o oprave dokončené – N ATTEMPT_REPAIR, M MANUAL_REVIEW, K SKIP"
}
```

**4. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_repair_decisions.json` – zoznam rozhodnutí s typom poškodenia, mierou úspešnosti, použitým pravidlom a odôvodnením pre každý súbor

## Výsledek

Čistá analytická operácia – žiadne súbory sa nekopírujú ani nemenia. Výsledky zaznamenané v `{CASE_ID}_repair_decisions.json`. Workflow pokračuje do opravy fotografií (ak existujú záznamy `ATTEMPT_REPAIR`) alebo priamo do EXIF analýzy (ak všetky záznamy sú `MANUAL_REVIEW` / `SKIP`).

## Reference

Kessler, G.C. (2016). Anti-forensics and the Digital Investigator. Proceedings of the 5th Australian Digital Forensics Conference. doi:10.4225/75/57B2667BE45CF
Garfinkel, S., Farrell, P., Roussev, V., & Dinolt, G. (2009). Bringing Science to Digital Forensics with Standardized Forensic Corpora. Digital Investigation, 6, S2–S11.
NIST SP 800-86 – Section 4.1 (Recovery decisions)
ISO/IEC 27037:2012 – Section 7.6 (Decision making)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)