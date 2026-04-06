# Detaily testu

## Úkol

Je médium čitateľné?

## Obtiažnosť

Jednoduchá

## Časová náročnosť

5-10 minút

## Automatický test

Automatický

## Popis

Tento rozhodovací bod určuje kľúčové vetvenie pracovného postupu. Analytik pripojí médium cez write-blocker, vykoná sériu READ-ONLY diagnostických príkazov a na základe výsledkov klasifikuje médium ako READABLE, PARTIAL alebo UNREADABLE. Všetky príkazy pracujú výhradne v režime čítania – originálne médium sa nesmie modifikovať.

## Jak na to

**1. Overte a pripojte write-blocker:**

Fyzicky pripojte write-blocker a zapojte médium cez neho – nikdy nie priamo. Overte, že LED indikátor svieti (PROTECTED). Pri mechanických HDD skontrolujte, či zariadenie nevydáva nezvyčajné zvuky (škrabanie, cvakanie).

⚠️ Ak niektorá podmienka nie je splnená, nepokračujte – existuje riziko poškodenia dôkazu.

Identifikujte cestu k zariadeniu (napr. `/dev/sdb`) – použijete ju vo všetkých nasledujúcich príkazoch namiesto `/dev/sdX`.

**2. Predbežná detekcia:**

Overte, že OS zariadenie vidí, a zaznamenajte základné informácie:
```bash
lsblk -d -o NAME,SIZE,TYPE,MODEL,SERIAL,TRAN /dev/sdX
```

Zistite súborový systém a skontrolujte prítomnosť šifrovania (LUKS signature, BitLocker header):
```bash
blkid /dev/sdX
```
Prázdny výsledok pri poškodenom médiu nie je chyba – zaznamenajte ho ako „žiadna odpoveď".

Pre HDD a SSD skontrolujte SMART zdravotné dáta:
```bash
smartctl -a /dev/sdX
```
Sledujte: Reallocated Sector Count (>50 = kriticky poškodený), Current Pending Sector Count (>0 = aktívne zlyháva), Uncorrectable Sector Count a teplotu (>45 °C = riziko). Flash médiá SMART nepodporujú – chyba príkazu je v poriadku.

Pre SSD zariadenia zaznamenajte TRIM support status:
```bash
hdparm -I /dev/sdX | grep TRIM
```
Ak je TRIM aktívny, upozornite klienta – vymazané dáta môžu byť fyzicky odstránené a recovery môže byť neúplná.

Ak `lsblk` naznačuje RAID pole, zistite konfiguráciu:
```bash
mdadm --examine /dev/sdX
```
Ak je médium súčasťou RAID poľa, upozornite klienta, že pre úplnú recovery je potrebný prístup ku všetkým členom poľa.

**3. Diagnostické testy:**

Pokúste sa prečítať prvý sektor (512 B). Ak tento príkaz zlyhá, médium je nečitateľné:
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

Zmerajte rýchlosť čítania 10 MB – pod 5 MB/s znamená extrémne dlhý imaging alebo riziko zlyhania:
```bash
dd if=/dev/sdX of=/dev/null bs=512 count=20480 status=progress
```

**4. Vyhodnotenie a klasifikácia:**

Na základe výsledkov klasifikujte médium:
- Všetky testy prešli → **READABLE** → odporúčaný nástroj: `dc3dd`
- Test sekvenčného čítania prešiel, niektoré iné zlyhali → **PARTIAL** → odporúčaný nástroj: `ddrescue`
- Test prvého sektora zlyhal → **UNREADABLE** → pokračujte Krokom 4 (fyzická oprava)

Ak boli identifikované kritické nálezy (aktívny TRIM, zlý SMART status, šifrovanie, RAID), informujte klienta o limitáciách recovery pred pokračovaním.

**5. Zápis výsledkov a aktualizácia CoC:**

Skript `ptmediareadability` môžete spustiť dvoma spôsobmi:

**Iba terminálový výstup (predvolené):**
```bash
ptmediareadability /dev/sdb PHOTORECOVERY-2025-01-26-001 --analyst "Meno Analytika"
```
Všetky výsledky sa zobrazia na terminále. Žiadny JSON súbor sa nevytvorí.

**S JSON výstupom (pre case.json):**
```bash
ptmediareadability /dev/sdb PHOTORECOVERY-2025-01-26-001 --analyst "Meno Analytika" --output result.json
```
Výsledky sa zobrazia na terminále a zároveň sa vytvorí `result.json` s uzlami `readabilityTest` a `chainOfCustodyEntry` pripravenými na manuálne skopírovanie do `case.json`.

**Obsah JSON výstupu:**
```json
{
  "readabilityTest": {
    "devicePath": "/dev/sdb",
    "timestamp": "2025-01-26T10:00:00Z",
    "mediaStatus": "READABLE",
    "recommendedTool": "dc3dd",
    "nextStep": 5,
    "criticalFindings": [],
    "statistics": {...},
    "detectionResults": {...},
    "diagnosticTests": [...]
  },
  "chainOfCustodyEntry": {
    "timestamp": "2025-01-26T10:00:00Z",
    "analyst": "Meno Analytika",
    "action": "Test čitateľnosti média – výsledok: READABLE",
    "selectedTool": "dc3dd"
  }
}
```

Analytik manuálne skopíruje oba uzly do `case.json`.

## Výsledek

Stav média je klasifikovaný ako READABLE, PARTIAL alebo UNREADABLE. Výsledky predbežnej detekcie a všetkých diagnostických testov sú zobrazené na terminále a voliteľne uložené do JSON súboru. Klient je informovaný o prípadných kritických limitáciách. Analytik pokračuje do príslušného kroku.

## Reference

ISO/IEC 27037:2012 – Section 6.3 (Acquisition of digital evidence)
NIST SP 800-86 – Section 3.1.1.3 (Data Collection Methodology)
ACPO Good Practice Guide – Principle 1 (No action should change data)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)