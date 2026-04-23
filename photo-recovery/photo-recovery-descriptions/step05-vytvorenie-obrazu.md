# Detaily testu

## Úkol

Vytvoriť forenzný obraz média a vypočítať SHA-256 hash originálu.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

60–240 minút

## Automatický test

Áno

## Popis

Forenzný imaging vytvára presnú bitovú kópiu úložného média, ktorá zachytáva všetko – aktívne súbory, vymazané dáta, slack space, nealokovaný priestor a metadata. SHA-256 hash sa počíta súčasne s kopírovaním v jednom priechode (dc3dd) alebo po dokončení (ddrescue). Výber nástroja: `dc3dd` pre READABLE médium, `ddrescue` pre PARTIAL médium.

Originálne médium zostáva pripojené cez write-blocker. Všetky analýzy sa vykonávajú na kópii, čím je zabezpečená súdna prípustnosť dôkazu.

Tool `ptforensicimaging` automatizuje proces – write-blocker confirmation, kontrolu predpokladov, imaging, hashovanie a vytvorenie kanonického hash súboru. Generuje standards-compliant JSON výstup.

## Jak na to

**1. Overte a pripojte write-blocker:**

Fyzicky pripojte write-blocker a zapojte médium cez neho – nikdy nie priamo. Overte, že LED indikátor svieti (PROTECTED).

**Write-blocker je VŽDY povinný** – skript vyžaduje potvrdenie pred každým spustením. Ak podmienka nie je splnená, nepokračujte – existuje riziko poškodenia dôkazu.

Identifikujte cestu k zariadeniu:
```bash
lsblk -d -o NAME,SIZE
```

**2. Kontrola dostupného miesta:**

Uistite sa, že cieľové úložisko má dostatočnú rezervu kapacity oproti zdrojovému médiu – odporúča sa minimálne rovnaká kapacita plus rezerva pre log súbory a metadata:
```bash
df -h /var/forensics/images
lsblk -d -o NAME,SIZE /dev/sdX
```
Nedostatok miesta počas imagingu môže spôsobiť stratu dôkazu – vždy počítajte s rezervou.

**3. Poznačte si výsledky testu čitateľnosti:**

Z výsledkov testu čitateľnosti si poznačte:
- `devicePath` – cesta k zariadeniu (napr. `/dev/sdb`)
- `mediaStatus` – READABLE alebo PARTIAL
- `recommendedTool` – `dc3dd` alebo `ddrescue`

Tieto hodnoty použijete ako parametre skriptu.

**4. Spustenie skriptu:**

```bash
# Iba terminálový výstup
ptforensicimaging PHOTORECOVERY-2025-01-26-001 /dev/sdb dc3dd --analyst "Meno Analytika"

# S JSON výstupom pre case.json
ptforensicimaging PHOTORECOVERY-2025-01-26-001 /dev/sdb dc3dd --analyst "Meno Analytika" --json-out ${CASE_ID}_imaging.json

# Pre PARTIAL médium (ddrescue)
ptforensicimaging PHOTORECOVERY-2025-01-26-001 /dev/sdb ddrescue --analyst "Meno Analytika" --json-out ${CASE_ID}_imaging.json
```

Skript vykoná potvrdenie write-blockera, kontrolu predpokladov a následne automaticky vykoná imaging a vytvorí kanonický hash súbor.

**5. Vykonanie imagingu:**

**Pre READABLE médium – dc3dd:**

dc3dd používa minimalistickú syntax (nepodporuje `bs=` ani `progress=` parametre):
```bash
dc3dd if=/dev/sdX \
      of=/var/forensics/images/CASE-ID.dd \
      hash=sha256 \
      log=/var/forensics/images/CASE-ID_imaging.log
```

dc3dd automaticky zobrazuje progress a vypíše SHA-256 hash do konzoly aj do log súboru. Hash (64 hexadecimálnych znakov) sa zaznamenáva ako `source_hash`. Hash sa počíta počas kopírovania – jeden priechod médiom, žiadne dodatočné čítanie.

**Pre PARTIAL médium – ddrescue:**
```bash
ddrescue -f -v \
    /dev/sdX \
    /var/forensics/images/CASE-ID.dd \
    /var/forensics/images/CASE-ID.mapfile
```

ddrescue použije stratégiu minimalizácie stresu na médium – číta zdravé oblasti najprv, problematické sektory opakovane s menšími blokmi. Vytvorí mapfile, ktorý zaznamenáva pozície chybných sektorov. Po dokončení sa vypočíta SHA-256 hash:
```bash
sha256sum /var/forensics/images/CASE-ID.dd
```

Výstup ddrescue sa automaticky zapisuje do imaging log súboru spolu s command, timestamps a exit code.

**6. Vytvorenie kanonického hash súboru:**

Skript automaticky vytvorí `.sha256` súbor vo formáte kompatibilnom s `sha256sum -c`. Formát je: `HASH  FILENAME` (dve medzery medzi hashom a názvom súboru).

Verifikácia integrity obrazu:
```bash
sha256sum -c CASE-ID.dd.sha256
```

**7. Zápis výsledkov a aktualizácia CoC:**

Pri použití `--json-out` skript vytvorí JSON s forensic metadata. Analytik manuálne skopíruje oba záznamy do `case.json`.

Pridávaný objekt `forensicImaging`:
```json
"forensicImaging": {
  "version": "1.0.0",
  "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
  "caseId": "PHOTORECOVERY-2025-01-26-001",
  "timestamp": "2025-01-26T12:00:00Z",
  "analyst": "Meno Analytika",
  "source": {
    "devicePath": "/dev/sdb",
    "mediaStatus": "READABLE",
    "sizeBytes": 32017047552
  },
  "acquisition": {
    "tool": "dc3dd",
    "toolVersion": "7.2.646",
    "method": "single-pass with integrated hashing",
    "durationSeconds": 1847.5,
    "averageSpeedMBps": 16.5
  },
  "output": {
    "imagePath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd",
    "imageFormat": "raw (.dd)",
    "imageSizeBytes": 32017047552,
    "imagingLog": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001_imaging.log",
    "hashFile": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd.sha256"
  },
  "integrity": {
    "writeBlockerConfirmed": true,
    "errorSectors": 0,
    "hashAlgorithm": "SHA-256",
    "sourceHash": "a3f5e8c9d2b1a7f4e6c8d9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2",
    "verified": true
  }
}
```

Nový záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T12:30:00Z",
  "analyst": "Meno Analytika",
  "action": "Forenzný imaging dokončený – nástroj: dc3dd, výsledok: SUCCESS",
  "mediaSerial": "SN-XXXXXXXX"
}
```

**8. Archivácia výstupov:**

Vytvorené súbory:
- `{CASE-ID}.dd` – forenzný obraz (raw format, bitová kópia)
- `{CASE-ID}.dd.sha256` – kanonický hash súbor pre verifikáciu
- `{CASE-ID}_imaging.log` – detailný log procesu (timestamps, rýchlosť, chyby)
- `{CASE-ID}.mapfile` – len pre ddrescue (mapa zdravých/chybných oblastí)

Archivujte tieto súbory do dokumentácie prípadu.

## Výsledek

Forenzný obraz vytvorený vo formáte `.dd`. SHA-256 `source_hash` vypočítaný a zaznamenaný. Kanonický hash súbor vytvorený pre verifikáciu. Standards-compliant JSON vygenerovaný s compliance metadata. Záznamy pripravené na integráciu do dokumentácie. Originálne médium zostáva neporušené.

Workflow pokračuje do verifikácie integrity obrazu.

## Reference

ISO/IEC 27037:2012 – Section 5.4 (Acquisition of digital evidence)

NIST SP 800-86 – Section 2.1 (Collection)

ACPO Good Practice Guide – Principle 1 (No action should change data) & Principle 2 (Competence of personnel performing acquisition)

NIST FIPS 180-4 – Secure Hash Standard (SHA-256 specification)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)