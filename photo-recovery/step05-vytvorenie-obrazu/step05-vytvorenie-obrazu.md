# Detaily testu

## Úkol

Vytvoriť forenzný obraz média a vypočítať SHA-256 hash originálu.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

60–240 minút

## Automatický test

Automatický

## Popis

Forenzný imaging vytvára presnú bitovú kópiu úložného média, ktorá zachytáva všetko – aktívne súbory, vymazané dáta, slack space, nealokovaný priestor a metadata. SHA-256 hash sa počíta súčasne s kopírovaním v jednom priechode, čím sa eliminuje opätovné čítanie média. Výber nástroja: `dc3dd` pre READABLE médium, `ddrescue` pre PARTIAL médium.

Originálne médium zostáva pripojené cez write-blocker. Všetky analýzy sa vykonávajú na kópii, čím je zabezpečená súdna prípustnosť dôkazu.

## Jak na to

**1. Overte a pripojte write-blocker:**

Fyzicky pripojte write-blocker a zapojte médium cez neho – nikdy nie priamo. Overte, že LED indikátor svieti (PROTECTED).

⚠️ Ak podmienka nie je splnená, nepokračujte – existuje riziko poškodenia dôkazu.

Identifikujte cestu k zariadeniu:
```bash
lsblk -d -o NAME,SIZE
```

**2. Kontrola dostupného miesta:**

Uistite sa, že cieľové úložisko má minimálne 110 % kapacity zdrojového média:
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
ptforensicimaging PHOTORECOVERY-2025-01-26-001 /dev/sdb dc3dd --analyst "Meno Analytika" --json-out imaging_result.json
```

Skript vykoná potvrdenie write-blockera, kontrolu predpokladov a následne automaticky vykoná imaging a vytvorí kanonický hash súbor.

**5. Vykonanie imagingu:**

**Pre READABLE médium – dc3dd:**
```bash
dc3dd if=/dev/sdX \
      of=/var/forensics/images/CASE-ID.dd \
      hash=sha256 \
      log=/var/forensics/images/CASE-ID_imaging.log \
      bs=1M \
      progress=on
```

dc3dd automaticky vypíše SHA-256 hash do konzoly aj do log súboru. Hash (64 hexadecimálnych znakov) sa zaznamenáva ako `source_hash`. Hash sa počíta počas kopírovania – jeden priechod médiom, žiadne dodatočné čítanie.

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

**6. Vytvorenie kanonického hash súboru:**

Skript automaticky vytvorí `.sha256` súbor vo formáte kompatibilnom s `sha256sum -c`. Formát je: `HASH  FILENAME` (dve medzery medzi hashom a názvom súboru).

Verifikácia integrity obrazu:
```bash
sha256sum -c CASE-ID.dd.sha256
```

**7. Zápis výsledkov a aktualizácia CoC:**

Pri použití `--json-out` sa vytvorí JSON s dvoma záznamami:

```json
{
  "imagingResult": {
    "devicePath": "/dev/sdb",
    "timestamp": "2025-01-26T12:00:00Z",
    "tool": "dc3dd",
    "mediaStatus": "READABLE",
    "imagePath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd",
    "imageFormat": "raw (.dd)",
    "sourceSizeBytes": 32017047552,
    "sourceHash": "a3f5e8c9d2b1a7f4e6c8d9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2",
    "durationSeconds": 1847.5,
    "averageSpeedMBps": 16.5,
    "errorSectors": 0,
    "imagingLog": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001_imaging.log",
    "mapfile": null
  },
  "chainOfCustodyEntry": {
    "timestamp": "2025-01-26T12:30:00Z",
    "analyst": "Meno Analytika",
    "action": "Forenzný imaging dokončený – dc3dd, SHA-256: a3f5e8c9d2b1a7f4..."
  }
}
```

Analytik manuálne skopíruje oba záznamy do `case.json`.

**8. Archivácia výstupov:**

Vytvorené súbory:
- `{CASE-ID}.dd` – forenzný obraz (raw format, bitová kópia)
- `{CASE-ID}.dd.sha256` – kanonický hash súbor pre verifikáciu
- `{CASE-ID}_imaging.log` – detailný log procesu (timestamps, rýchlosť, chyby)
- `{CASE-ID}.mapfile` – len pre ddrescue (mapa zdravých/chybných oblastí)

Archivujte tieto súbory do dokumentácie prípadu.

## Výsledek

Forenzný obraz vytvorený vo formáte `.dd`. SHA-256 `source_hash` vypočítaný a zaznamenaný v `imagingResult`. Kanonický hash súbor vytvorený pre verifikáciu. Záznamy pripravené na integráciu do dokumentácie. Originálne médium zostáva neporušené.

Workflow pokračuje do verifikácie integrity obrazu.

## Reference

ISO/IEC 27037:2012 – Section 6.3 (Acquisition of digital evidence)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Forensic Imaging)
ACPO Good Practice Guide – Principle 1 & 2 (Evidence preservation)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 specification)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)