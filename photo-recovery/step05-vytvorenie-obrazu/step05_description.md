# Detaily testu

## Úkol

Vytvoriť forenzný obraz média a automaticky vypočítať SHA-256 hash počas procesu imaging.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

120 minút

## Automatický test

Áno

## Popis

Forenzný imaging je proces vytvárania presnej bitovej kópie úložného média. Na rozdiel od bežného kopírovania súborov, forenzný obraz zachytáva absolútne všetko – aktívne súbory, vymazané súbory, slack space, nealokovaný priestor a metadata súborového systému, pričom je bit-for-bit identický s originálom.

SHA-256 hash sa vypočítava súčasne s kopírovaním dát v jednom priechode – eliminuje potrebu opätovného čítania média a poskytuje matematický dôkaz integrity. Výber nástroja je automatický: skript načíta výsledok testu čítateľnosti z predchádzajúceho kroku a podľa klasifikácie média zvolí dc3dd (READABLE) alebo ddrescue (PARTIAL).

Originálne médium zostáva po celý čas pripojené výhradne cez write-blocker. Všetky budúce analýzy sa vykonávajú na vytvorenej kópii, čím je zabezpečená súdna prípustnosť dôkazu.

## Jak na to

**1. Overenie write-blockera:**

Pred spustením imagingu overte fyzický stav write-blockera – LED indikátor musí svietiť (PROTECTED) a médium musí byť zapojené výlučne cez write-blocker. Systém vyžiada explicitné interaktívne potvrdenie pred pokračovaním.

**2. Kontrola dostupného miesta:**

Uistite sa, že cieľové úložisko má dostatok miesta – minimálne 110% kapacity zdrojového média (rezerva pre metadata, logy a mapfile). Systém toto overí automaticky.

**3. Spustenie imagingu:**

Skript automaticky načíta `devicePath` a `selectedTool` zo súboru `PHOTORECOVERY-2025-01-26-001_readability_report.json` (výstup predchádzajúceho kroku):

```bash
ptforensicimaging PHOTORECOVERY-2025-01-26-001
```

Na základe `selectedTool` z readability reportu skript automaticky zvolí:
- **READABLE → dc3dd** (rýchle, s integrovaným SHA-256 hashovaním):
```bash
dc3dd if=/dev/sdX of=PHOTORECOVERY-2025-01-26-001.dd hash=sha256 log=imaging.log bs=1M progress=on
```

- **PARTIAL → ddrescue** (recovery režim s mapovaním chybných sektorov; SHA-256 sa vypočíta samostatne po dokončení cez bezpečné Popen reťazenie bez shell=True):
```bash
ddrescue -f -v /dev/sdX PHOTORECOVERY-2025-01-26-001.dd PHOTORECOVERY-2025-01-26-001.mapfile
```

**4. Zaznamenanie source_hash:**

Po dokončení dc3dd automaticky vypíše SHA-256 hash do konzoly aj do log súboru. Tento hash je source_hash – referenčná hodnota pre následnú verifikáciu v Kroku 6. Zaznamenajte ho presne (64 hexadecimálnych znakov).

Kanonický hash súbor je `PHOTORECOVERY-2025-01-26-001.dd.sha256` – skript ho vytvorí automaticky vo formáte kompatibilnom s `sha256sum -c`. Krok 6 načíta source_hash z `PHOTORECOVERY-2025-01-26-001_imaging.json` (pole `sourceHash`), nie priamo z hash súboru.

**5. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte `imagingResult` node a nový `chainOfCustody` záznam do poľa `nodes`:

```json
{
  "type": "imagingResult",
  "properties": {
    "tool": "dc3dd",
    "mediaStatus": "READABLE",
    "imagePath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd",
    "imageFormat": "raw (.dd)",
    "sourceSizeBytes": 31914983424,
    "sourceHash": "a3f5...c9d1",
    "durationSeconds": 1847,
    "averageSpeedMBps": 16.4,
    "errorSectors": 0,
    "imagingLog": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001_imaging.log",
    "completedAt": "2025-01-26T13:30:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step05-vytvorenie-obrazu",
    "action": "Forensic image created – dc3dd, SHA-256 source hash recorded",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T13:30:00Z",
    "notes": null
  }
}
```

Pre ddrescue pridajte aj `"errorSectors"` s počtom chybných sektorov a `"mapfile"` s cestou k mapfile.

**6. Archivácia výstupov:**

Archivujte do Case dokumentácie:
- `PHOTORECOVERY-2025-01-26-001.dd` – forenzný obraz
- `PHOTORECOVERY-2025-01-26-001_imaging.json` – source_hash a metadata (generuje skript, kanonický zdroj pre Krok 6)
- `PHOTORECOVERY-2025-01-26-001_imaging.log` – detailný log procesu
- `PHOTORECOVERY-2025-01-26-001.dd.sha256` – hash vo formáte `sha256sum -c` (ľudsky čitateľná záloha hash hodnoty)
- `PHOTORECOVERY-2025-01-26-001.mapfile` – len pre ddrescue, mapa chybných sektorov

## Výsledek

Forenzný obraz vytvorený vo formáte `.dd`. SHA-256 source_hash vypočítaný a zaznamenaný v `PHOTORECOVERY-2025-01-26-001_imaging.json`. Kanonický hash súbor `PHOTORECOVERY-2025-01-26-001.dd.sha256` vytvorený pre archiváciu. Imaging log obsahuje kompletné detaily – nástroj, trvanie, priemernú rýchlosť, počet chybných sektorov a source_hash. Aktualizovaný case JSON súbor s `imagingResult` nodom a ďalším `chainOfCustody` záznamom. Originálne médium zostáva neporušené a pripojené pre následnú verifikáciu.

## Reference

ISO/IEC 27037:2012 – Section 6.3 (Acquisition of digital evidence)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Forensic Imaging)
ACPO Good Practice Guide – Principle 1 & 2 (Evidence preservation)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 specification)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)