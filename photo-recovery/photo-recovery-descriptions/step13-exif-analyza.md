# Detaily testu

## Úkol

Extrahovať a analyzovať EXIF metadáta zo všetkých obnovených fotografií.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Áno

## Popis

Nástroj dávkovo extrahuje EXIF metadáta pomocou `exiftool` zo všetkých obrazových súborov v konsolidovanom adresári (výstup kroku 9). Vykoná analýzu časovej osi, zoznam zariadení, GPS súradnice a detekciu anomálií (budúci dátum záznamu, neobvyklé ISO, zmena po vytvorení). Poškodené a neopraviteľné súbory sú vynechané.

## Jak na to

**1. Overenie predchádzajúcich výstupov:**

Poznačte si cestu ku konsolidovanému adresáru – štandardne `{CASE_ID}_consolidated/` v output adresári. Ak prebehla oprava fotografií, opravené súbory v `{CASE_ID}_repaired/` sú umiestnené oddelene a je potrebné ich zahrnúť cez `--source-dir`.

**2. Inštalácia závislostí:**

```bash
sudo apt-get install libimage-exiftool-perl
```

**3. Spustenie analýzy:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"

# Štandardné spustenie – číta z {CASE_ID}_consolidated/
ptexifanalysis ${CASE_ID}

# S JSON výstupom
ptexifanalysis ${CASE_ID} --analyst "Meno Analytika" --json-out ${CASE_ID}_exif_result.json

# Explicitná cesta k adresáru (napr. ak opravené súbory sú v inom adresári)
ptexifanalysis ${CASE_ID} \
  --source-dir /var/forensics/images/${CASE_ID}_consolidated \
  --analyst "Meno Analytika" --json-out ${CASE_ID}_exif_result.json

# Simulácia bez exiftool
ptexifanalysis ${CASE_ID} --dry-run
```

Nástroj automaticky prehľadáva rekurzívne zadaný adresár. Spracovanie prebieha v dávkach po 50 súborov na jedno volanie `exiftool` pre efektivitu.

**4. Manuálna analýza (záložná metóda):**

Ak automatický nástroj nie je dostupný, použite priame príkazy.

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
SOURCE="/var/forensics/images/${CASE_ID}_consolidated"
EXIF_DIR="/var/forensics/images/${CASE_ID}_exif_analysis"
mkdir -p "${EXIF_DIR}"
```

**Dávková extrakcia EXIF do JSON:**
```bash
exiftool -j -G -a -s -n \
    "${SOURCE}/" \
    > "${EXIF_DIR}/${CASE_ID}_exif_database.json"
```

**CSV export pre tabuľkový editor:**
```bash
exiftool -csv -G -a \
    "${SOURCE}/" \
    > "${EXIF_DIR}/${CASE_ID}_exif_data.csv"
```

**Analýza časovej osi – zoskupenie podľa dátumu:**
```bash
exiftool -DateTimeOriginal -T -r "${SOURCE}/" \
    | sort | uniq -c | sort -rn
```

**Zoznam zariadení:**
```bash
exiftool -Make -Model -T -r "${SOURCE}/" \
    | sort | uniq -c | sort -rn
```

**GPS súradnice:**
```bash
exiftool -GPSLatitude -GPSLongitude -FileName -T -r "${SOURCE}/" \
    | grep -v "^-"
```

**Detekcia editačného softvéru:**
```bash
exiftool -Software -FileName -T -r "${SOURCE}/" \
    | grep -iv "^-" \
    | grep -i "photoshop\|lightroom\|gimp\|affinity\|instagram\|snapseed\|vsco\|facetune"
```

**5. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do dokumentácie prípadu:
- Celkový počet spracovaných súborov
- Počet EXIF-pozitívnych súborov
- Počet súborov s `DateTimeOriginal`
- Počet súborov s GPS súradnicami
- Počet unikátnych zariadení
- Počet detekovaných anomálií (future_date, unusual_iso, modify_after_original)

Pridajte záznam do Chain of Custody:
```json
{
  "timestamp": "2025-01-26T17:30:00Z",
  "analyst": "Meno Analytika",
  "action": "EXIF analýza dokončená – N EXIF-pozitívnych súborov, M anomálií"
}
```

**6. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_exif_analysis.json` – kompletná EXIF databáza s per-file metadátami a anomáliami

## Výsledek

Kompletná EXIF databáza s per-file metadátami, časovou osou, GPS zoznamom a detekovanými anomáliami. Výsledky zaznamenané v dokumentácii prípadu. Workflow pokračuje na záverečný forenzný report.

## Reference

EXIF 2.32 Specification (CIPA DC-008-2019)
ISO 12234-2:2001 – Electronic still-picture imaging
Farid, H. (2016). Photo Forensics. MIT Press, Ch. 3–4.
Casey, E. (2011). Digital Evidence and Computer Crime (3rd ed.), Elsevier, Ch. 14.
ExifTool Documentation (https://exiftool.org)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)