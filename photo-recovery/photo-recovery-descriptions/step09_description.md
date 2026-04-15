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

Tento krok zjednotí výstupy z krokov obnovy (Filesystem Recovery a/alebo File Carving) do jedného organizovaného datasetu pomocou SHA-256 deduplikácie naprieč zdrojmi a vytvorí master katalóg so štatistikami. Vykonáva sa vždy – pri `filesystem_scan` spracuje jeden zdroj, pri `hybrid` oba.

## Jak na to

**1. Overenie dostupných zdrojov:**

Skontrolujte, ktoré výstupy z predchádzajúcich krokov existujú podľa stratégie z analýzy súborového systému:
- `filesystem_scan` → adresár `_recovered/` (Filesystem Recovery)
- `file_carving` → adresár `_carved/` (File Carving)
- `hybrid` → oba adresáre

Ak žiadny zdroj neexistuje, vráťte sa k Filesystem Recovery alebo File Carving.

**2. Nastavenie premenných:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
BASE="/forenzne/pripady/${CASE_ID}"
CONSOL="${BASE}/${CASE_ID}_consolidated"
mkdir -p "${CONSOL}/fs_based/jpg" "${CONSOL}/fs_based/png" "${CONSOL}/fs_based/tiff" \
         "${CONSOL}/fs_based/raw" "${CONSOL}/fs_based/other" \
         "${CONSOL}/carved/jpg"   "${CONSOL}/carved/png"    "${CONSOL}/carved/tiff" \
         "${CONSOL}/carved/raw"   "${CONSOL}/carved/other" \
         "${CONSOL}/duplicates"
```

**3. SHA-256 hashovanie všetkých zdrojov:**

```bash
find "${BASE}/${CASE_ID}_recovered" -type f | xargs sha256sum > /tmp/hashes_fs.txt
find "${BASE}/${CASE_ID}_carved/organized" -type f | xargs sha256sum > /tmp/hashes_carved.txt
```

**4. Deduplikácia naprieč zdrojmi:**

Zlúčte hashes a identifikujte duplicitné hodnoty:
```bash
cat /tmp/hashes_fs.txt /tmp/hashes_carved.txt | sort > /tmp/hashes_all.txt
```
Ak rovnaký hash existuje v oboch zdrojoch, FS-based kópia má prednosť – skopírujte ju do `fs_based/[format]/`, carved kópiu presuňte do `duplicates/`. Typicky 15–25 % súborov pri hybridnom prístupe sú duplikáty.

**5. Kopírovanie a organizácia:**

Unikátne súbory skopírujte do konsolidovaného adresára podľa zdroja a formátu:
- FS-based → `${CONSOL}/fs_based/[jpg|png|tiff|raw|other]/` – zachovajte pôvodný názov (pri kolízii pridajte číselný suffix)
- Carved → `${CONSOL}/carved/[jpg|png|tiff|raw|other]/` – použite systematický názov `${CASE_ID}_{typ}_{seq:06d}.ext`

**6. Vytvorenie master katalógu:**

Vytvorte súbor `master_catalog.json` s inventárom každého súboru:
```json
[
  {
    "id": 1,
    "filename": "IMG_1234.jpg",
    "hash_sha256": "abc123...",
    "size_bytes": 2048576,
    "format": "jpg",
    "source": "fs_based",
    "path": "fs_based/jpg/IMG_1234.jpg"
  }
]
```
Vytvorte aj textový report `CONSOLIDATION_REPORT.txt` s prehľadom štatistík.

**7. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky konsolidácie do dokumentácie prípadu:
- Počet súborov z filesystem recovery
- Počet súborov z file carving
- Počet odstránených duplikátov
- Počet finálnych unikátnych súborov
- Celková veľkosť datasetu (bajty)

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T15:30:00Z",
  "analyst": "Meno Analytika",
  "action": "Konsolidácia dokončená – N unikátnych súborov, M duplikátov odstránených"
}
```

**8. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `master_catalog.json` – kompletný inventár všetkých súborov
- `CONSOLIDATION_REPORT.txt` – textový prehľad pre klienta

## Výsledek

Konsolidovaný dataset v `${CASE_ID}_consolidated/`: podadresáre `fs_based/{jpg,png,tiff,raw,other}/` a `carved/{jpg,png,tiff,raw,other}/`, `duplicates/` pre auditné kópie. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje do validácie integrity fotografií.

## Reference

ISO/IEC 27037:2012 – Section 7.3 (Data consolidation)
NIST SP 800-86 – Section 3.1.3 (Analysis)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)