# Detaily testu

## Úkol

Vytvoriť bit-presnú forenznú kópiu originálneho média a vypočítať SHA-256 source_hash v jedinom priechode.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

60–240 minút 

## Automatický test

Áno

## Popis

Forenzný imaging vytvára bit-presnú kópiu celého originálneho média vrátane aktívnych súborov, zmazaných dát, nealokovaného priestoru, slack space a metadát súborového systému. SHA-256 `source_hash` sa vypočítava súčasne s kopírovaním v jedinom priechode – nástroj dc3dd má integrované hashovanie (`hash=sha256`), čím médium sa číta práve raz.

Skript vyžaduje manuálne potvrdenie aktívneho write-blockera pred každým spustením – bez potvrdenia sa imaging nespustí. Ak podmienka nie je splnená, nepokračujte – existuje riziko poškodenia dôkazu. Originálne médium zostáva po celý čas pripojené výhradne cez write-blocker.

## Jak na to

**1. Pripojenie write-blockera:**

Fyzicky pripojte write-blocker a zapojte médium cez neho – nikdy nie priamo. Overte, že LED indikátor svieti (PROTECTED). Identifikujte cestu k zariadeniu:
```bash
lsblk -d -o NAME,SIZE,TYPE,MODEL,SERIAL,TRAN
```
Dokumentujte write-blocker v CoC logu: typ, model, sériové číslo, firmware verzia.

**2. Spustenie skriptu:**

```bash
# Iba terminálový výstup
ptforensicimaging COC-2025-01-26-001 /dev/sdb dc3dd --analyst "Meno Analytika"

# S JSON výstupom pre case.json
ptforensicimaging COC-2025-01-26-001 /dev/sdb dc3dd --analyst "Meno Analytika" --json-out imaging_result.json
```

Skript vykoná potvrdenie write-blockera (manuálna výzva), kontrolu dostupného miesta (min. 110 % kapacity média) a následne automaticky vykoná imaging s integrovaným hashovaním.

**3. Vykonanie imagingu:**

dc3dd automaticky vypočíta SHA-256 hash počas kopírovania:
```bash
dc3dd if=/dev/sdX \
      of=/var/forensics/images/COC-2025-01-26-001.dd \
      hash=sha256 \
      log=/var/forensics/images/COC-2025-01-26-001_imaging.log
```
Hash (64 hexadecimálnych znakov) sa zaznamenáva ako `source_hash`. Zaznamenajte ho aj manuálne do CoC dokumentácie – vizuálna kontrola posledných 8 znakov eliminuje chyby kopírovania.

**4. Archivácia výstupov:**

Vytvorené súbory:
- `COC-2025-01-26-001.dd` – forenzný obraz (raw formát)
- `COC-2025-01-26-001.dd.sha256` – kanonický hash súbor
- `COC-2025-01-26-001_imaging.log` – detailný log procesu
- `COC-2025-01-26-001_imaging_result.json` – JSON report so `source_hash`

## Výsledok

Forenzný obraz `COC-2025-01-26-001.dd` vytvorený. SHA-256 `source_hash` vypočítaný a uložený v JSON reporte. Kanonický hash súbor vytvorený pre verifikáciu. Záznam `chainOfCustody` automaticky zapísaný. Workflow pokračuje do verifikácie integrity obrazu.

## Reference

ISO/IEC 27037:2012 – Section 6.3 (Acquisition of digital evidence)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Forensic Imaging)
ACPO Good Practice Guide – Principle 1 & 2 (Evidence preservation)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 specification)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)