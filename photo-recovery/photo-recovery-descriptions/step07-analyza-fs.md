# Detaily testu

## Úkol

Analyzovať forenzný obraz média a určiť typ súborového systému, jeho stav, partície a metadáta.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

10 minút

## Automatický test

Áno

## Popis

Analýza súborového systému je prvý krok forenznej analýzy po vytvorení a overení forenzného obrazu. Výsledok priamo určuje stratégiu obnovy: rozpoznaný súborový systém s čitateľnou adresárovou štruktúrou umožňuje filesystem-based recovery (zachováva pôvodné názvy súborov a metadáta), poškodený alebo nerozpoznaný súborový systém vyžaduje file carving (hľadá súbory podľa signatúr v raw dátach).

Všetky príkazy pracujú výhradne s forenzným obrazom – originálne médium sa v tejto fáze nedotýka.

## Jak na to

**1. Zistenie cesty k obrazu:**

Pozrite sa do výstupu z hash verification a zapíšte si cestu k forenzného obrazu. Typicky:
```
/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd
```

**2. Spustenie analýzy pomocou skriptu:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
IMAGE="/var/forensics/images/${CASE_ID}.dd"

# Iba terminálový výstup
ptfilesystemanalysis ${CASE_ID} ${IMAGE} --analyst "Meno Analytika"

# S JSON výstupom pre case.json
ptfilesystemanalysis ${CASE_ID} ${IMAGE} \
  --analyst "Meno Analytika" \
  --json-out ${CASE_ID}_filesystem_analysis.json
```

Skript automaticky overí existenciu forenzného obrazu a následne vykoná kroky 3–5.

Exit kódy: `0` – úspech, `1` – chyba (obraz nenájdený, chýbajúce nástroje), `130` – prerušené (Ctrl+C).

**3. Analýza partičnej tabuľky (`mmls`):**

```bash
mmls "${IMAGE}"
```

Zaznamenajte typ tabuľky (DOS/MBR, GPT), zoznam partícií s offsetmi a veľkosťami. Ak `mmls` zlyhá alebo nevráti žiadne partície, predpokladá sa superfloppy formát – celé médium je jeden súborový systém bez partičnej tabuľky (typické pre USB flash disky a SD karty). V takom prípade použite offset `0` v nasledujúcich príkazoch.

**4. Analýza súborového systému (`fsstat`):**

Pre každú partíciu (alebo offset `0` pri superfloppy):
```bash
fsstat -o OFFSET "${IMAGE}"
```

Zaznamenajte typ súborového systému (FAT32, exFAT, NTFS, ext4…), volume label, UUID, veľkosť sektora a klastra. Ak `fsstat` zlyhá, súborový systém je nerozpoznaný alebo poškodený.

**5. Kontrola adresárovej štruktúry (`fls`):**

```bash
fls -r -o OFFSET "${IMAGE}" | grep -iE '\.(jpg|jpeg|png|tiff?|bmp|gif|raw|cr2|nef|arw|dng|heic|webp)$'
```

Vymazané súbory sú v liste označené hviezdičkou `*`. Spočítajte aktívne a vymazané obrazové súbory.

**6. Určenie stratégie obnovy:**

Na základe výsledkov zvoľte stratégiu:
- Rozpoznaný FS + čitateľná adresárová štruktúra → `filesystem_scan`
- Nerozpoznaný FS (fsstat zlyhalo) → `file_carving`
- Rozpoznaný FS, ale poškodená štruktúra (fsstat prešlo, fls vrátilo nekonzistentné dáta) → `hybrid`

**7. Zápis výsledkov a aktualizácia CoC:**

Pri použití `--json-out` sa vytvorí JSON s forensic metadata. Analytik manuálne skopíruje oba záznamy do `case.json`.

Pridávaný objekt `filesystemAnalysis`:
```json
"filesystemAnalysis": {
  "version": "1.0.0",
  "compliance": ["NIST SP 800-86", "ISO/IEC 27042:2015"],
  "caseId": "PHOTORECOVERY-2025-01-26-001",
  "timestamp": "2025-01-26T13:30:00Z",
  "analyst": "Meno Analytika",
  "partitionTable": {
    "tableType": "DOS/MBR",
    "partitionsFound": 1
  },
  "partitions": [
    {
      "partitionNumber": 0,
      "offset": 0,
      "filesystemType": "FAT32",
      "filesystemRecognized": true,
      "volumeLabel": "USB_PHOTOS",
      "directoryReadable": true,
      "imageFiles": {
        "total": 1247,
        "active": 834,
        "deleted": 413
      }
    }
  ],
  "recoveryStrategy": {
    "recommendedMethod": "filesystem_scan",
    "recommendedTool": "fls + icat (The Sleuth Kit)",
    "estimatedTimeMinutes": 15,
    "filesystemRecognized": true,
    "directoryReadable": true,
    "totalImageFiles": 1247
  }
}
```

Nový záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T13:30:00Z",
  "analyst": "Meno Analytika",
  "action": "Analýza súborového systému – stratégia: filesystem_scan",
  "mediaSerial": "SN-XXXXXXXX"
}
```

**8. Archivácia výstupov:**

Uložte textový výstup príkazov `mmls`, `fsstat` a `fls` do súboru `${CASE_ID}_filesystem_analysis.txt` pre audit trail.

## Výsledok

Typ súborového systému identifikovaný, stav a čitateľnosť adresárovej štruktúry overené. Výsledky zaznamenané v JSON súbore vrátane partition table, FS typu, počtu obrazových súborov a zvolenej recovery stratégie.

Ďalší krok závisí od stratégie: `filesystem_scan` → Filesystem Recovery, `file_carving` → File Carving, `hybrid` → obe metódy.

## Reference

ISO/IEC 27042:2015 – Section 5 (Digital evidence analysis)

NIST SP 800-86 – Section 2.2 (Examination)

The Sleuth Kit Documentation – mmls, fsstat, fls tools

Brian Carrier: File System Forensic Analysis (2005)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)