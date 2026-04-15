# Detaily testu

## Úkol

Vytvoriť záverečnú správu konsolidujúcu výstupy všetkých predchádzajúcich krokov.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

10 minút

## Automatický test

Nie

## Popis

Záverečná správa je generovaná platformou z priebežne budovanej dokumentácie prípadu. Každý krok workflowu do nej od začiatku prispieva svojimi výstupmi a CoC záznami – v tomto kroku je dokumentácia kompletná a správa sa z nej vygeneruje bez manuálneho dopĺňania.

## Jak na to

**1. Kontrola úplnosti dokumentácie prípadu:**

Každý krok workflowu mal pridať svoje výstupy do dokumentácie prípadu. Pred generovaním správy overte, že sú prítomné záznamy zo všetkých povinných krokov:

| Krok | Výstupný súbor | Povinné |
|------|----------------|---------|
| Prijatie žiadosti a vytvorenie Case ID | `case.json` (prvý záznam) | Áno |
| Identifikácia média a fotodokumentácia | CoC záznam č. 2 | Áno |
| Test čitateľnosti média | `{CASE_ID}_readability.json` | Áno |
| Forenzný imaging + SHA-256 | `{CASE_ID}_imaging.json` | Áno |
| Verifikácia SHA-256 hashu | `{CASE_ID}_verification.json` | Áno |
| Analýza súborového systému | `{CASE_ID}_filesystem_analysis.json` | Áno |
| Filesystem Recovery / File Carving | `{CASE_ID}_recovery_report.json` | Áno |
| Recovery Consolidation | `{CASE_ID}_consolidation_report.json` | Áno |
| Validácia integrity fotografií | `{CASE_ID}_validation_report.json` | Áno |
| Rozhodnutie o oprave fotografií | `{CASE_ID}_repair_decision.json` | Áno |
| Oprava fotografií | `{CASE_ID}_repair_report.json` | Nie |
| EXIF analýza | `{CASE_ID}_exif_analysis/{CASE_ID}_exif_database.json` | Nie |

**2. Štruktúra záverečnej správy:**

Platforma zostaví správu z akumulovanej dokumentácie. Každá sekcia má presne definovaný zdroj:

**S1 – Executive Summary**
Z `validation_report.json` (počty, integrity score) + `exif_database.json` (EXIF pokrytie) + `repair_report.json` (opravené súbory). Celkový počet obnovených fotografií, quality rating, zoznam čo klient dostáva.

**S2 – Case Information**
Z `case.json` – Case ID, meno analytika, dátum prijatia žiadosti, klasifikácia dokumentu. Vyplnené v Prijatí žiadosti.

**S3 – Evidence Information**
Z `case.json` (fyzická identifikácia) + `readability.json` (stav média) + `imaging.json` (write-blocker, SHA-256). Vyplnené v Identifikácii média a Teste čitateľnosti.

**S4 – Methodology**
Generované automaticky podľa toho, ktoré kroky workflowu prebehli a ktoré nástroje boli použité (dc3dd/ddrescue, fls/icat, PhotoRec, ExifTool, PIL).

**S5 – Timeline**
Z timestampov CoC záznamov všetkých krokov – chronologický priebeh prípadu od prijatia po záverečný report.

**S6 – Results**
Z `validation_report.json` + `repair_report.json` + `exif_database.json` + `consolidation_report.json`. Počty súborov, integrity score, štatistiky opravy, EXIF pokrytie.

**S7 – Technical Details**
Z `filesystem_analysis.json` (FS typ, stratégia) + `validation_report.json` (validačná logika) + `repair_report.json` (techniky opravy) + `exif_database.json` (EXIF parametre).

**S8 – Quality Assurance**
Z `validation_report.json` (integrity score) + `exif_database.json` (EXIF quality score) + `verification.json` (SHA-256 zhoda).

**S9 – Chain of Custody**
Z CoC záznamov všetkých krokov – každý krok pridal svoj záznam do `case.json`. Kompletný neprerušený reťazec od prijatia média po záverečný report.

**S10 – Signatures**
Podpisový blok – `PENDING` do fyzického podpísania oboma stranami.

**3. Peer review:**

Nadriadený analytik skontroluje:
- Konzistentnosť čísel naprieč sekciami S1, S6 a S8
- Neprerušenosť Chain of Custody v S9
- Správnosť technických detailov v S7
- Vhodnosť jazyka pre prípadné súdne použitie

**4. Podpisy:**

Pred odovzdaním klientovi sú povinné podpisy primárneho analytika aj peer reviewera. Kým sú podpisy `PENDING`, správa nie je pripravená na odovzdanie.

**5. Aktualizácia CoC:**

Pridajte záverečný záznam do `case.json`:
```json
{
  "timestamp": "2025-01-26T18:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Záverečná správa vygenerovaná a podpísaná – pripravená na odovzdanie"
}
```

**6. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- Záverečná správa (JSON + PDF)
- Podpísaný odovzdávací protokol
- Kontrolný zoznam s potvrdením všetkých položiek

## Výsledek

Záverečná správa s 10 sekciami podpísaná oboma stranami a pripravená na odovzdanie klientovi. Workflow pokračuje na Odovzdanie zákazníkovi.

## Reference

ISO/IEC 27037:2012 – Section 8 (Documentation and reporting)
NIST SP 800-86 – Section 4 (Reporting Phase)
ACPO Good Practice Guide – Principle 4 (Documentation)
SWGDE Best Practices for Digital and Multimedia Evidence

## Stav

Manuálny proces – netestovateľný automaticky

## Nález

(prázdne – vyplní sa po teste)