# Detaily testu

## Úkol

Je médium čitateľné?

## Obtiažnosť

Jednoduchá

## Časová náročnosť

5 minút

## Automatický test

Poloautomatický (vyžaduje potvrdenie write-blockera pred spustením)

## Popis

Tento rozhodovací bod určuje kľúčové vetvenie pracovného postupu. Po potvrdení write-blockera platforma spustí diagnostický skript, ktorý vykoná READ-ONLY kontroly a klasifikuje médium. Na základe výsledkov systém odporučí optimálny postup.

## Jak na to

**1. Overte a pripojte write-blocker:**

Fyzicky pripojte write-blocker a zapojte médium cez neho – nikdy nie priamo. Overte, že LED indikátor svieti. Pri mechanických HDD skontrolujte, či zariadenie nevydáva nezvyčajné zvuky (škrabanie, cvakanie).

⚠️ Ak niektorá podmienka nie je splnená, nepokračujte – existuje riziko poškodenia dôkazu.

**2. Predbežná detekcia:**

Overte, že OS zariadenie vidí a zaznamenajte základné informácie:
```bash
lsblk -d -o NAME,SIZE,TYPE,MODEL,SERIAL,TRAN /dev/sdX
```

Zistite súborový systém a skontrolujte prítomnosť šifrovania (LUKS signature, BitLocker header). Prázdny výsledok pri poškodenom médiu nie je chyba:
```bash
blkid /dev/sdX
```

Pre HDD a SSD skontrolujte SMART zdravotné dáta a zaznamenajte kritické atribúty – Reallocated Sector Count (>50 = kriticky poškodený), Current Pending Sector Count (>0 = aktívne zlyháva), Uncorrectable Sector Count a teplotu (>45°C = riziko). Flash médiá SMART nepodporujú – chyba príkazu je v poriadku:
```bash
smartctl -a /dev/sdX
```

Pre SSD zariadenia zaznamenajte TRIM support status – ak je aktívny, vymazané dáta môžu byť automaticky fyzicky odstránené na pozadí a recovery môže byť neúplná:
```bash
hdparm -I /dev/sdX | grep TRIM
```

Ak `lsblk` zobrazí viac zariadení naraz alebo výstup naznačuje RAID pole, zistite konfiguráciu:
```bash
mdadm --examine /dev/sdX
```

**3. Diagnostické testy:**

Pokúste sa prečítať prvý sektor (512 B) – ak tento príkaz zlyhá, médium je nečitateľné a ďalšie testy nemajú zmysel:
```bash
dd if=/dev/sdX of=/dev/null bs=512 count=1 status=none
```

Skúste sekvenčné čítanie 1 MB:
```bash
dd if=/dev/sdX of=/dev/null bs=512 count=2048 status=none
```

Otestujte čítanie na troch rôznych pozíciách média (začiatok, stred, koniec):
```bash
dd if=/dev/sdX of=/dev/null bs=512 count=1 skip=2048 status=none
dd if=/dev/sdX of=/dev/null bs=512 count=1 skip=$(($(blockdev --getsize64 /dev/sdX) / 1024)) status=none
dd if=/dev/sdX of=/dev/null bs=512 count=1 skip=$(($(blockdev --getsize64 /dev/sdX) / 512 - 20480)) status=none
```

Zmerajte rýchlosť čítania 10 MB – pod 5 MB/s znamená extrémne dlhý imaging alebo zlyhanie počas neho:
```bash
dd if=/dev/sdX of=/dev/null bs=512 count=20480 status=progress
```

**4. Vyhodnotenie a postup:**

Na základe výsledkov klasifikujte médium a vyberte nástroj pre Krok 5:
- Všetky testy prešli → **READABLE** → dc3dd
- Test sekvenčného čítania prešiel, niektoré iné zlyhali → **PARTIAL** → ddrescue
- Test prvého sektora zlyhal → **UNREADABLE** → Krok 4 (fyzická oprava)

Ak boli identifikované kritické nálezy (aktívny TRIM, zlý SMART status, šifrovanie, RAID), informujte klienta o limitáciách recovery pred pokračovaním.

**5. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `readabilityTest` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "readabilityTest",
  "properties": {
    "devicePath": "/dev/sdX",
    "mediaStatus": "READABLE",
    "detectionResults": {
      "lsblk": "detected",
      "blkid": "FAT32",
      "smartctl": "ok",
      "hdparm": "TRIM not supported",
      "mdadm": "not applicable"
    },
    "diagnosticTests": {
      "firstSector": "pass",
      "sequential1MB": "pass",
      "positionStart": "pass",
      "positionMiddle": "pass",
      "positionEnd": "pass",
      "readSpeed": "18.4 MB/s"
    },
    "criticalFindings": [],
    "selectedTool": "dc3dd",
    "reportPath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001_readability_report.json",
    "completedAt": "2025-01-26T12:30:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step03-test-citatelnosti",
    "action": "Readability test completed – media classified as READABLE, dc3dd selected for imaging",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T12:30:00Z",
    "notes": null
  }
}
```

Pre stav PARTIAL nastavte `"mediaStatus": "PARTIAL"` a `"selectedTool": "ddrescue"`. Pre stav UNREADABLE nastavte `"mediaStatus": "UNREADABLE"` a `"selectedTool": null`.

## Výsledek

Stav média je klasifikovaný ako READABLE, PARTIAL alebo UNREADABLE. Výsledky predbežnej detekcie (lsblk, blkid, smartctl, hdparm, mdadm) a všetkých diagnostických testov sú zaznamenané v `PHOTORECOVERY-2025-01-26-001_readability_report.json`. Klient je informovaný o prípadných kritických limitáciách. Aktualizovaný case JSON súbor s uzlom `readabilityTest` a ďalším záznamom `chainOfCustody`. Analytik pokračuje do príslušného kroku.

## Reference

ISO/IEC 27037:2012 – Section 6.3 (Acquisition of digital evidence)
NIST SP 800-86 – Section 3.1.1.3 (Data Collection Methodology)
ACPO Good Practice Guide – Principle 1 (No action should change data)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)