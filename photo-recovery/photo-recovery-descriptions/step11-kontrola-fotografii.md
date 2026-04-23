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

Miery úspešnosti vychádzajú z odhadov podporených odkazmi v literatúre: Kessler (2016) a Garfinkel et al. (2009).

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

Na základe miery úspešnosti sa aplikujú pravidlá R1–R3 v poradí, prvé platné pravidlo rozhoduje:

| Pravidlo | Podmienka | Rozhodnutie |
|---|---|---|
| R1 | Úspešnosť ≥ 50 % | `ATTEMPT_REPAIR` |
| R2 | 30 % ≤ úspešnosť < 50 % | `MANUAL_REVIEW` |
| R3 | Úspešnosť < 30 % | `SKIP` |

Ak automatický nástroj nie je dostupný, otvorte `{CASE_ID}_integrity_validation.json`, pre každý súbor so statusom `REPAIRABLE` vyhľadajte `corruptionType` v tabuľke vyššie, aplikujte pravidlá R1–R3 a výsledné rozhodnutie zapíšte ručne do `{CASE_ID}_repair_decisions.json`.

**3. Zápis výsledkov a aktualizácia CoC:**

Pri použití `--json-out` sa vytvorí JSON s výsledkami. Analytik manuálne skopíruje oba záznamy do `case.json`.

Pridávaný objekt `repairDecision`:
```json
"repairDecision": {
  "timestamp": "2025-01-26T16:05:00Z",
  "analyst": "Meno Analytika",
  "totalRepairable": 198,
  "attemptRepair": 156,
  "manualReview": 29,
  "skip": 13,
  "decisionBreakdown": {
    "missing_footer": {"count": 87, "decision": "ATTEMPT_REPAIR", "rule": "R1"},
    "truncated": {"count": 64, "decision": "ATTEMPT_REPAIR", "rule": "R1"},
    "corrupt_segments": {"count": 31, "decision": "ATTEMPT_REPAIR", "rule": "R1"},
    "corrupt_data": {"count": 16, "decision": "MANUAL_REVIEW", "rule": "R2"}
  },
  "decisionFile": "PHOTORECOVERY-2025-01-26-001_repair_decisions.json"
}
```

Nový záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T16:05:00Z",
  "analyst": "Meno Analytika",
  "action": "Rozhodnutie o oprave dokončené – 156 ATTEMPT_REPAIR, 29 MANUAL_REVIEW, 13 SKIP",
  "mediaSerial": "SN-XXXXXXXX"
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

ISO/IEC 27042:2015 – Section 5 (Digital evidence analysis)

NIST SP 800-86 – Section 2.3 (Analysis)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)