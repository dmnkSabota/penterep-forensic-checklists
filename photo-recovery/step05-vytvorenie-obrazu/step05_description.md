# Detaily testu

## Úkol

Vytvoriť forenzný obraz média a automaticky vypočítať SHA-256 hash počas procesu imaging.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

120 minút

## Automatický test

Poloautomatický (vyžaduje potvrdenie write-blockera pred spustením)

## Popis

Forenzný imaging je proces vytvárania presnej bitovej kópie úložného média. Na rozdiel od bežného kopírovania súborov, forenzný obraz zachytáva absolútne všetko – aktívne súbory, vymazané súbory, slack space, nealokovaný priestor a metadata súborového systému, pričom je bit-for-bit identický s originálom.

SHA-256 hash sa vypočítava súčasne s kopírovaním dát v jednom priechode – eliminuje potrebu opätovného čítania média a poskytuje matematický dôkaz integrity. Výber nástroja je automatický: skript načíta výsledok testu čítateľnosti z uzla `readabilityTest` a podľa klasifikácie média zvolí dc3dd (READABLE) alebo ddrescue (PARTIAL).

Originálne médium zostáva po celý čas pripojené výhradne cez write-blocker. Všetky budúce analýzy sa vykonávajú na vytvorenej kópii, čím je zabezpečená súdna prípustnosť dôkazu.

## Jak na to

**1. Overte a pripojte write-blocker:**

Pred spustením imagingu overte fyzický stav write-blockera – LED indikátor musí svietiť (PROTECTED) a médium musí byť zapojené výlučne cez write-blocker.

⚠️ Systém vyžiada explicitné potvrdenie pred pokračovaním. Ak podmienka nie je splnená, nepokračujte.

**2. Kontrola dostupného miesta:**

Uistite sa, že cieľové úložisko má dostatok miesta – minimálne 110% kapacity zdrojového média (rezerva pre metadata, logy a mapfile). Systém toto overí automaticky.

**3. Spustenie imagingu:**

Skript automaticky načíta `devicePath` a `selectedTool` z uzla `readabilityTest`:

```bash
ptforensicimaging PHOTORECOVERY-2025-01-26-001
```

Na základe `selectedTool` skript automaticky zvolí:
- **READABLE → dc3dd** (rýchle, s integrovaným SHA-256 hashovaním):
```bash
dc3dd if=/dev/sdX of=PHOTORECOVERY-2025-01-26-001.dd hash=sha256 log=imaging.log bs=1M progress=on
```

- **PARTIAL → ddrescue** (recovery režim s mapovaním chybných sektorov; SHA-256 sa vypočíta samostatne po dokončení cez bezpečné Popen reťazenie bez shell=True):
```bash
ddrescue -f -v /dev/sdX PHOTORECOVERY-2025-01-26-001.dd PHOTORECOVERY-2025-01-26-001.mapfile
```

**4. Zaznamenanie source_hash:**

Po dokončení dc3dd automaticky vypíše SHA-256 hash do konzoly aj do log súboru. Tento hash je source_hash – referenčná hodnota pre následnú verifikáciu. Zaznamenajte ho presne (64 hexadecimálnych znakov).

Kanonický hash súbor `PHOTORECOVERY-2025-01-26-001.dd.sha256` sa vytvorí automaticky vo formáte kompatibilnom s `sha256sum -c`. Následujúci krok načíta source_hash z uzla `imagingResult` (pole Zdrojový hash), nie priamo z hash súboru.

**5. Výsledky v uzle imagingResult:**

Skript automaticky zapíše výsledky do uzla `imagingResult` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Nástroj – dc3dd / ddrescue
- Stav média – READABLE / PARTIAL
- Cesta k obrazu
- Formát obrazu
- Veľkosť zdroja (bajty)
- Zdrojový hash (SHA-256, 64 znakov)
- Trvanie (sekundy)
- Priemerná rýchlosť (MB/s)
- Počet chybných sektorov
- Pre ddrescue: cesta k mapfile

**6. Archivácia výstupov:**

Skript automaticky nahrá nasledujúce súbory do záložky **Přílohy** projektu:
- `PHOTORECOVERY-2025-01-26-001_imaging.log` – detailný log procesu
- `PHOTORECOVERY-2025-01-26-001.dd.sha256` – hash vo formáte `sha256sum -c` (ľudsky čitateľná záloha hash hodnoty)
- `PHOTORECOVERY-2025-01-26-001.mapfile` – len pre ddrescue, mapa chybných sektorov

## Výsledek

Forenzný obraz vytvorený vo formáte `.dd`. SHA-256 source_hash vypočítaný a zaznamenaný v uzle `imagingResult`. Kanonický hash súbor vytvorený pre archiváciu. Imaging log obsahuje kompletné detaily – nástroj, trvanie, priemernú rýchlosť, počet chybných sektorov a source_hash. Originálne médium zostáva neporušené a pripojené pre následnú verifikáciu.

## Reference

ISO/IEC 27037:2012 – Section 6.3 (Acquisition of digital evidence)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Forensic Imaging)
ACPO Good Practice Guide – Principle 1 & 2 (Evidence preservation)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 specification)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)