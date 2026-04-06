# Detaily testu

## Úkol

Vytvoriť forenzný obraz média a vypočítať SHA-256 hash počas procesu imaging.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

120 minút

## Automatický test

Poloautomatický (vyžaduje potvrdenie write-blockera pred spustením)

## Popis

Forenzný imaging je proces vytvárania presnej bitovej kópie úložného média. Na rozdiel od bežného kopírovania súborov, forenzný obraz zachytáva absolútne všetko – aktívne súbory, vymazané súbory, slack space, nealokovaný priestor a metadata súborového systému, pričom je bit-for-bit identický s originálom.

SHA-256 hash sa vypočítava súčasne s kopírovaním dát v jednom priechode – eliminuje potrebu opätovného čítania média a poskytuje matematický dôkaz integrity. Výber nástroja vychádza z výsledku Kroku 3: `dc3dd` pre READABLE médium, `ddrescue` pre PARTIAL médium.

Originálne médium zostáva po celý čas pripojené výhradne cez write-blocker. Všetky budúce analýzy sa vykonávajú na vytvorenej kópii, čím je zabezpečená súdna prípustnosť dôkazu.

## Jak na to

**1. Overte a pripojte write-blocker:**

Pred spustením imagingu overte fyzický stav write-blockera – LED indikátor musí svietiť (PROTECTED) a médium musí byť zapojené výlučne cez write-blocker.

⚠️ Ak podmienka nie je splnená, nepokračujte. Riziko poškodenia dôkazu.

**2. Kontrola dostupného miesta:**

Uistite sa, že cieľové úložisko má dostatok voľného miesta – minimálne 110 % kapacity zdrojového média:
```bash
df -h /cesta/k/cielovemu/uloziku
lsblk -d -o NAME,SIZE /dev/sdX
```

**3. Prečítanie výsledkov Kroku 3:**

Z uzla `readabilityTest` v dokumentácii prípadu si zaznamenajte:
- `devicePath` – cesta k zariadeniu (napr. `/dev/sdb`)
- `mediaStatus` – READABLE alebo PARTIAL
- `selectedTool` – `dc3dd` alebo `ddrescue`

**4. Nastavenie premenných a spustenie imagingu:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
SOURCE="/dev/sdX"
OUTPUT_DIR="/forenzne/pripady/${CASE_ID}"
mkdir -p "${OUTPUT_DIR}"
```

**Pre READABLE médium – dc3dd** (rýchle, s integrovaným SHA-256 hashovaním):
```bash
dc3dd if=${SOURCE} \
      of=${OUTPUT_DIR}/${CASE_ID}.dd \
      hash=sha256 \
      log=${OUTPUT_DIR}/${CASE_ID}_imaging.log \
      bs=1M \
      progress=on
```

**Pre PARTIAL médium – ddrescue** (recovery režim s mapovaním chybných sektorov):
```bash
ddrescue -f -v \
    ${SOURCE} \
    ${OUTPUT_DIR}/${CASE_ID}.dd \
    ${OUTPUT_DIR}/${CASE_ID}.mapfile
```
Po dokončení ddrescue vypočítajte SHA-256 hash samostatne:
```bash
sha256sum ${OUTPUT_DIR}/${CASE_ID}.dd | tee ${OUTPUT_DIR}/${CASE_ID}.dd.sha256
```

**5. Zaznamenanie source_hash:**

Po dokončení dc3dd automaticky vypíše SHA-256 hash do konzoly aj do log súboru. Pre ddrescue hash prevezmite z výstupu sha256sum. Zaznamenajte hash (64 hexadecimálnych znakov) – toto je `source_hash`, referenčná hodnota pre všetky náslebné verifikácie.

Kanonický hash súbor `${CASE_ID}.dd.sha256` uložte v cieľovom adresári vo formáte kompatibilnom s `sha256sum -c`.

**6. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do uzla `imagingResult` v dokumentácii prípadu:
- Nástroj – dc3dd / ddrescue
- Stav média – READABLE / PARTIAL
- Cesta k obrazu
- Formát obrazu – `.dd`
- Veľkosť zdroja (bajty)
- Zdrojový hash – SHA-256, 64 znakov (`source_hash`)
- Trvanie (sekundy)
- Priemerná rýchlosť (MB/s)
- Počet chybných sektorov
- Pre ddrescue: cesta k mapfile

Pridajte záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T12:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Forenzný imaging dokončený – dc3dd, SHA-256: abc123..."
}
```

**7. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `${CASE_ID}_imaging.log` – detailný log procesu
- `${CASE_ID}.dd.sha256` – hash vo formáte `sha256sum -c`
- `${CASE_ID}.mapfile` – len pre ddrescue

---

> **Automatizácia (pripravuje sa):** Skript `ptforensicimaging` bude výber nástroja, spustenie imagingu, zápis uzla `imagingResult` a aktualizáciu CoC vykonávať automaticky.

## Výsledek

Forenzný obraz vytvorený vo formáte `.dd`. SHA-256 `source_hash` vypočítaný a zaznamenaný v uzle `imagingResult`. Kanonický hash súbor vytvorený pre archiváciu a následnú verifikáciu. Originálne médium zostáva neporušené.

## Reference

ISO/IEC 27037:2012 – Section 6.3 (Acquisition of digital evidence)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Forensic Imaging)
ACPO Good Practice Guide – Principle 1 & 2 (Evidence preservation)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 specification)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)