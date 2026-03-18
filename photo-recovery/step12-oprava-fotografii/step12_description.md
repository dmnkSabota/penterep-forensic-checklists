# Detaily testu

## Úkol

Oprava identifikovaných poškodených fotografií pomocou automatizovaných techník.

## Obtiažnosť

Stredná

## Časová náročnosť

45 minút

## Automatický test

Áno

## Popis

Skript sa pokúsi opraviť každý súbor z `filesNeedingRepair` pomocou techniky zodpovedajúcej typu poškodenia. Zdrojové súbory v `corrupted/` zostávajú nedotknuté – oprava prebieha na pracovnej kópii. Krok sa aktivuje iba ak Krok 11 vrátil stratégiu `perform_repair`.

## Jak na to

**1. Overenie rozhodnutia o oprave:**

Skript ako prvý krok overí stratégiu v uzle `repairDecision` (Krok 11). Ak stratégia je `skip_repair`, skript odmietne pokračovať.

**2. Spustenie skriptu:**

```bash
ptphotorepair PHOTORECOVERY-2025-01-26-001
```

Skript načíta zoznam súborov na opravu z uzla `integrityValidation` (Krok 10) – pole `filesNeedingRepair` s typom poškodenia a odporúčanou technikou.

**3. Kontrola nástrojov:**

PIL/Pillow je povinný (`LOAD_TRUNCATED_IMAGES = True`). Voliteľné: `jpeginfo`.

**4. Smerovanie a oprava:**

Pre každý súbor skript vytvorí pracovnú kópiu a aplikuje príslušnú techniku. Výsledok opravy je validovaný pomocou PIL a jpeginfo.

**5. Organizácia výstupov:**

Úspešne opravené súbory sa presunú do `PHOTORECOVERY-2025-01-26-001_repair/repaired/`, neúspešné do `failed/`. Originál v `corrupted/` zostáva nedotknutý.

**6. Výsledky v uzle photoRepair:**

Skript automaticky zapíše výsledky do uzla `photoRepair` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Celkový počet pokusov o opravu
- Počet úspešných opráv
- Počet neúspešných opráv
- Úspešnosť opravy (%)

**7. Archivácia výstupov:**

Skript automaticky nahrá nasledujúce súbory do záložky **Přílohy** projektu:
- `PHOTORECOVERY-2025-01-26-001_repair_report.json` – štatistiky a detail každej opravy
- `PHOTORECOVERY-2025-01-26-001_REPAIR_REPORT.txt` – textový prehľad

## Výsledek

Opravené súbory v `PHOTORECOVERY-2025-01-26-001_repair/repaired/` (pripravené na EXIF analýzu), neopraviteľné v `failed/`. Výsledky zaznamenané v uzle `photoRepair`. Workflow pokračuje do kroku EXIF analýza.

## Reference

ISO/IEC 10918-1 – JPEG Standard (ITU-T T.81)
JFIF Specification v1.02
NIST SP 800-86 – Section 3.1.4 (Data Recovery and Repair)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)