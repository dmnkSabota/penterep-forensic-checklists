# Detaily testu

## Úkol

Spojiť obnovené fotografie do jedného deduplikovaného datasetu a vytvoriť master katalóg.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Áno

## Popis

Skript zjednotí výstupy z krokov obnovy do jedného organizovaného datasetu pomocou SHA-256 deduplikácie naprieč zdrojmi a vytvorí master katalóg so štatistikami. Krok sa vykonáva vždy — pri `filesystem_scan` spracuje jeden zdroj, pri `hybrid` oba.

## Jak na to

**1. Spustenie skriptu:**

```bash
ptrecoveryconsolidation PHOTORECOVERY-2025-01-26-001
```

Skript overí existenciu výstupov z uzlov `filesystemRecovery` (Krok 8a) a `fileCarvingRecovery` (Krok 8b). Ak žiadny zdroj neexistuje, odmietne pokračovať.

**2. Inventarizácia:**

Pre každý dostupný zdroj skript rekurzívne naskenuje obrazové súbory (`.jpg`, `.png`, `.raw` a ďalšie) a zaznamenáva cestu, veľkosť, príponu a zdroj (`fs_based` / `carved`).

**3. SHA-256 hashovanie a deduplikácia:**

Pre každý súbor sa vypočíta SHA-256 odtlačok. Ak rovnaký hash existuje v oboch zdrojoch, FS-based kópia zostane a carved kópia sa skopíruje do `duplicates/` pre auditný zámer. Typicky 15–25 % súborov pri hybridnom prístupe sú duplikáty.

**4. Kopírovanie a organizácia:**

Unikátne súbory sa skopírujú do `PHOTORECOVERY-2025-01-26-001_consolidated/`. Adresárová štruktúra je dvojúrovňová – súbory sa triedia najprv podľa zdroja, potom podľa formátu:

```
PHOTORECOVERY-2025-01-26-001_consolidated/
├── fs_based/
│   ├── jpg/
│   ├── png/
│   ├── tiff/
│   ├── raw/
│   └── other/
├── carved/
│   ├── jpg/
│   ├── png/
│   ├── tiff/
│   ├── raw/
│   └── other/
└── duplicates/
```

FS-based súbory zachovávajú pôvodný názov (s kolíznou ochranou), carved súbory dostanú systematický názov `PHOTORECOVERY-2025-01-26-001_{typ}_{seq:06d}.ext`.

**5. Master katalóg:**

Skript uloží `master_catalog.json` s kompletným inventárom (ID, názov, hash, veľkosť, formát, zdroj, cesta) a štatistikami. Textový report `CONSOLIDATION_REPORT.txt` obsahuje prehľad pre klienta.

**6. Výsledky v uzle recoveryConsolidation:**

Skript automaticky zapíše výsledky do uzla `recoveryConsolidation` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Počet súborov z filesystem recovery
- Počet súborov z file carving
- Počet odstránených duplikátov
- Počet finálnych unikátnych súborov
- Celková veľkosť datasetu (bajty)

**7. Archivácia výstupov:**

Skript automaticky nahrá nasledujúce súbory do záložky **Přílohy** projektu:
- `master_catalog.json` – kompletný inventár všetkých súborov
- `CONSOLIDATION_REPORT.txt` – textový prehľad pre klienta

## Výsledek

Konsolidovaný dataset v `PHOTORECOVERY-2025-01-26-001_consolidated/`: podadresáre `fs_based/{jpg,png,tiff,raw,other}/` a `carved/{jpg,png,tiff,raw,other}/` organizované podľa zdroja aj formátu, `duplicates/` pre auditné kópie. Výsledky zaznamenané v uzle `recoveryConsolidation`. Workflow pokračuje do kroku Validácia integrity fotografií.

## Reference

ISO/IEC 27037:2012 – Section 7.3 (Data consolidation)
NIST SP 800-86 – Section 3.1.3 (Analysis)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)