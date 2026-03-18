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

Záverečná správa konsoliduje výstupy všetkých predchádzajúcich krokov do jedného dokumentu. Načíta výsledky z uzlov `integrityValidation` (Krok 10), `exifAnalysis` (Krok 13) a voliteľne `photoRepair` (Krok 12), a zostaví 10-sekčnú správu. Výstupom je `FINAL_REPORT.json`, voliteľný `FINAL_REPORT.pdf` a `README.txt` pre klienta.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptfinalreport PHOTORECOVERY-2025-01-26-001
```

Skript načíta nasledujúce vstupy:
- Uzol `integrityValidation` (Krok 10) – povinné
- Uzol `exifAnalysis` (Krok 13) – voliteľné
- Uzol `photoRepair` (Krok 12) – voliteľné

Absencia voliteľných uzlov nespôsobí chybu – príslušné sekcie reportu sa jednoducho vynechajú.

**2. Zostavenie 10-sekčnej správy:**

Každá sekcia má dedikovanú metódu: zhrnutie pre klienta, informácie o prípade, informácie o dôkaze, metodológia, časový priebeh, výsledky, technické detaily, zabezpečenie kvality, reťazec úschovy, podpisy.

**3. PDF správa (voliteľná):**

Ak je nainštalovaný `reportlab`, vygeneruje dokument formátu A4 s titulnou stranou, tabuľkami a blokom podpisov. Bez `reportlab` sa krok preskočí.

**4. Klientská dokumentácia:**

`README.txt` s inštrukciami pre klienta a `delivery_checklist.json` so statusom položiek (peer review a podpisy sú PENDING).

**5. Výsledky v uzle finalReport:**

Skript automaticky zapíše výsledky do uzla `finalReport` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Celkový počet obnovených fotografií
- Integrity score
- Hodnotenie kvality – Very Good / Good / Fair / Poor
- Počet vygenerovaných sekcií
- PDF vygenerované – áno / nie

**6. Archivácia výstupov:**

Skript automaticky nahrá nasledujúce súbory do záložky **Přílohy** projektu:
- `FINAL_REPORT.json` – kompletná záverečná správa (10 sekcií)
- `FINAL_REPORT.pdf` – voliteľný, len ak je nainštalovaný reportlab
- `README.txt` – inštrukcie pre klienta
- `delivery_checklist.json` – zoznam položiek pred odovzdaním

## Výsledek

Záverečná správa vygenerovaná a zaznamenaná v uzle `finalReport`. Kontrola nadriadeným analytikom a podpisy sú povinné pred odovzdaním. Workflow pokračuje do kroku Odovzdanie klientovi.

## Reference

ISO/IEC 27037:2012 – Digital evidence handling
NIST SP 800-86 – Forensic Techniques
ACPO Good Practice Guide
SWGDE Best Practices

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)