# Detaily testu

## Úkol

Je médium čitateľné?

## Obtiažnosť

Jednoduchá

## Časová náročnosť

5-10 minút

## Automatický test

Áno

## Popis

Tento rozhodovací bod určuje kľúčové vetvenie pracovného postupu. Analytik pripojí médium cez write-blocker, vykoná sériu READ-ONLY diagnostických príkazov a na základe výsledkov klasifikuje médium ako READABLE, PARTIAL alebo UNREADABLE. Všetky príkazy pracujú výhradne v režime čítania – originálne médium sa nesmie modifikovať.

## Jak na to

**1. Overte a pripojte write-blocker:**

Fyzicky pripojte write-blocker a zapojte médium cez neho – nikdy nie priamo. Overte, že LED indikátor svieti (PROTECTED). Pri mechanických HDD skontrolujte, či zariadenie nevydáva nezvyčajné zvuky (škrabanie, cvakanie).

Ak niektorá podmienka nie je splnená, nepokračujte – existuje riziko poškodenia dôkazu.

Identifikujte cestu k zariadeniu (napr. `/dev/sdb`) – použijete ju vo všetkých nasledujúcich príkazoch namiesto `/dev/sdX`.

**2. Spustenie testu pomocou skriptu:**

```bash
# Iba terminálový výstup
ptmediareadability /dev/sdb PHOTORECOVERY-2025-01-26-001 --analyst "Meno Analytika"

# S JSON výstupom pre case.json
ptmediareadability /dev/sdb PHOTORECOVERY-2025-01-26-001 --analyst "Meno Analytika" --json-out ${CASE_ID}_readability.json
```

Skript vykoná potvrdenie write-blockera (manuálna výzva) a následne automaticky predbežnú detekciu a diagnostické testy.

**3. Predbežná detekcia:**

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
Sledujte: Reallocated Sector Count (vyššie hodnoty naznačujú poškodenie), Current Pending Sector Count (>0 = aktívne zlyháva), Uncorrectable Sector Count a teplotu (zvýšená teplota predstavuje riziko – referenčné hodnoty sa líšia podľa výrobcu). Flash médiá SMART nepodporujú – chyba príkazu je v poriadku.

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

**4. Diagnostické testy:**

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

Zmerajte rýchlosť čítania 10 MB – výrazne nízka rýchlosť môže naznačovať extrémne dlhý imaging alebo riziko zlyhania počas procesu:
```bash
dd if=/dev/sdX of=/dev/null bs=512 count=20480 status=progress
```

**5. Vyhodnotenie a klasifikácia:**

Na základe výsledkov klasifikujte médium:
- Všetky testy prešli → **READABLE** → odporúčaný nástroj: `dc3dd`
- Test sekvenčného čítania prešiel, niektoré iné zlyhali → **PARTIAL** → odporúčaný nástroj: `ddrescue`
- Test prvého sektora zlyhal → **UNREADABLE** → pokračuje fyzická oprava média

Ak boli identifikované kritické nálezy (aktívny TRIM, zlý SMART status, šifrovanie, RAID), informujte klienta o limitáciách recovery pred pokračovaním.

**6. Zápis výsledkov a aktualizácia CoC:**

Pri použití `--json-out` skript vytvorí JSON s forensic metadata. Analytik manuálne skopíruje oba záznamy do `case.json`.

Pridávaný objekt `readabilityTest`:
```json
"readabilityTest": {
  "version": "1.0.0",
  "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
  "caseId": "PHOTORECOVERY-2025-01-26-001",
  "timestamp": "2025-01-26T10:00:00Z",
  "analyst": "Meno Analytika",
  "device": {
    "devicePath": "/dev/sdb",
    "mediaStatus": "READABLE",
    "recommendedTool": "dc3dd"
  },
  "criticalFindings": [],
  "statistics": {
    "testsRun": 4,
    "testsPassed": 4,
    "testsFailed": 0
  }
}
```

Nový záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T10:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Test čitateľnosti média – výsledok: READABLE, nástroj: dc3dd",
  "mediaSerial": "SN-XXXXXXXX"
}
```

## Výsledek

Stav média je klasifikovaný ako READABLE, PARTIAL alebo UNREADABLE. Výsledky predbežnej detekcie a všetkých diagnostických testov sú zobrazené na terminále a voliteľne uložené do JSON súboru. Klient je informovaný o prípadných kritických limitáciách. Analytik pokračuje do príslušného kroku.

## Reference

ISO/IEC 27037:2012 – Section 5.3 (Collection)

NIST SP 800-86 – Section 2.1 (Collection)

ACPO Good Practice Guide – Principle 1 (No action should change data)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)