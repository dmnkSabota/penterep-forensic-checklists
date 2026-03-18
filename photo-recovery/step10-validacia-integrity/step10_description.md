# Detaily testu

## Úkol

Overiť fyzickú integritu všetkých obnovených fotografií a rozdeliť ich do kategórií.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Áno

## Popis

Skript načíta master katalóg z uzla `recoveryConsolidation` (Krok 9) a pre každý súbor vykoná validáciu pomocou dostupných nástrojov. Výsledkom je klasifikácia fotografií do troch kategórií s integrity score a reportom poškodených súborov.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptintegrityvalidation PHOTORECOVERY-2025-01-26-001
```

Skript načíta `master_catalog.json` z uzla `recoveryConsolidation` (Krok 9) a získa zoznam všetkých konsolidovaných súborov na validáciu.

**2. Kontrola nástrojov:**

PIL/Pillow je povinný (`pip install Pillow`). Voliteľné: `jpeginfo`, `pngcheck` – skript použije ak sú dostupné.

**3. Per-file validácia:**

Pre každý súbor skript overí: veľkosť (prázdne súbory = neopraviteľné), čitateľnosť pixelov cez PIL `verify()` + `load()`, a pre JPEG/PNG aj `jpeginfo -c` / `pngcheck -v`. Rozhodovacia logika: ak všetky nástroje prešli → validný, ak niektoré prešli a niektoré zlyhali → poškodený (potenciálne opraviteľný), ak všetky zlyhali → neopraviteľný.

**4. Organizácia výstupov:**

Súbory sa skopírujú do `PHOTORECOVERY-2025-01-26-001_validation/valid/`, `corrupted/` alebo `unrecoverable/`. Zdrojové súbory v konsolidovanom adresári zostávajú nedotknuté.

**5. Analýza poškodení a report:**

Pre každý poškodený súbor skript určí typ chyby (truncated, invalid_header, corrupt_segments, corrupt_data, unknown) a úroveň opraviteľnosti (L1–L5). Ak typ chyby nie je možné určiť, súbor sa klasifikuje ako unknown (L3, vyžaduje manuálnu inšpekciu).

**6. Výsledky v uzle integrityValidation:**

Skript automaticky zapíše výsledky do uzla `integrityValidation` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Celkový počet validovaných súborov
- Počet validných súborov
- Počet poškodených súborov
- Počet neopraviteľných súborov
- Integrity score (% validných súborov)
- Použité nástroje

**7. Archivácia výstupov:**

Skript automaticky nahrá nasledujúce súbory do záložky **Přílohy** projektu:
- `PHOTORECOVERY-2025-01-26-001_validation_report.json` – kompletný validačný report
- `PHOTORECOVERY-2025-01-26-001_VALIDATION_REPORT.txt` – textový prehľad so zoznamom súborov odporúčaných na opravu

## Výsledek

Klasifikácia všetkých fotografií do troch kategórií v `PHOTORECOVERY-2025-01-26-001_validation/`: `valid/`, `corrupted/`, `unrecoverable/`. Integrity score s rozpisom podľa formátu a zdroja (fs_based vs carved). Výsledky zaznamenané v uzle `integrityValidation`. Workflow pokračuje do kroku Rozhodnutie o oprave fotografií.

## Reference

ISO/IEC 10918-1 – JPEG Standard
PNG Specification – ISO/IEC 15948:2004
NIST SP 800-86 – Section 3.1.3 (Data Validation)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)