# Detaily testu

## Úkol

Identifikovať médium a vytvoriť fotodokumentáciu.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

15 minút

## Automatický test

Nie

## Popis

Fyzická identifikácia média zabezpečuje jeho jednoznačné odlíšenie od ostatných artefaktov v laboratóriu a vytvára základ pre Chain of Custody dokumentáciu v súlade s ISO/IEC 27037:2012. Všetky záznamy z tohto kroku sú priamo prepojené s Case ID z kroku 1 a pridávajú sa do centrálneho case JSON súboru.

## Jak na to

**1. Fotodokumentácia:**

Vyhotovte komplexnú fotodokumentáciu média – minimálne 8 záberov:
- Celkový záber s mierkou
- Šesť strán zariadenia: vrch, spodok, predná strana, zadná strana, ľavá, pravá
- Makro detail sériového čísla
- Detail každého viditeľného poškodenia alebo anomálie

**2. Fyzické identifikátory:**

Zaznamenajte do formulára: výrobcu, typové označenie modelu, úplné sériové číslo, farbu a materiál púzdra, presné rozmery v mm a kapacitu z nálepky zariadenia. Zaznamenajte aj typ zariadenia (SSD, HDD, USB flash disk, SD karta) – určuje, ktoré diagnostické nástroje budú relevantné v Kroku 3.

**3. Fyzický stav média:**

Zdokumentujte celkový stav zariadenia (nové / mierne použité / intenzívne použité / poškodené), stav nálepiek a štítkov, a viditeľné stopy používania – škrabance, znečistenie, zmeny farby.

**4. Fyzické poškodenie:**

Detailne popíšte typ poškodenia (prasklina púzdra, zlomený konektor, deformácia, korózia kontaktov), presnú lokalizáciu na zariadení a závažnosť:
- Malé – kozmetické, funkčnosť neovplyvnená
- Stredné – čiastočne funkčné, vyžaduje opravu
- Kritické – znemožňuje pripojenie

**5. Viditeľné indikátory šifrovania:**

Skontrolujte, či médium nenesie viditeľné znaky šifrovania – BitLocker štítok od výrobcu, VeraCrypt bootloader nálepku, alebo firemný bezpečnostný štítok. Ak sú prítomné, zaznamenajte ich a informujte klienta, že recovery kľúč alebo heslo bude nevyhnutné. Technická verifikácia šifrovania prebehne v Kroku 3.

**6. Fyzické označenie:**

Nalepte štítok s Case ID na médium – nie na konektor, nie cez sériové číslo, nie cez pôvodné výrobné nálepky.

**7. Archivácia fotografií a formulárov:**

Všetky fotografie a formuláre uložte do dokumentácie Case pod príslušným Case ID.

**8. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `mediaIdentify` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "mediaIdentify",
  "properties": {
    "deviceType": "USB flash disk",
    "manufacturer": "SanDisk",
    "model": "Ultra 32GB",
    "serialNumber": "SN123456789",
    "capacity": "32GB",
    "color": "šedá",
    "dimensions": {
      "lengthMm": 32,
      "widthMm": 24,
      "heightMm": 2
    },
    "condition": "poškodené",
    "conditionNotes": "škrabance na povrchu, nálepka čiastočne odlúpnutá",
    "damagePresent": true,
    "damage": {
      "type": "zlomený konektor",
      "location": "pravá strana",
      "severity": "stredné"
    },
    "encryptionIndicatorVisible": false,
    "labelApplied": true,
    "photosCount": 8,
    "photosArchived": true,
    "completedAt": "2025-01-26T10:50:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step02-identifikacia-media",
    "action": "Physical media identification and photo documentation completed",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T10:50:00Z",
    "notes": null
  }
}
```

Ak médium nie je poškodené, nastavte `"damagePresent": false` a vynechajte objekt `"damage"`.

## Výsledek

M�dium je identifikované a zdokumentované. Vytvorené výstupy:
- Fotodokumentácia (minimálne 8 fotografií) archivovaná pod Case ID
- Identifikačný formulár s kompletnými fyzickými parametrami
- Fyzický štítok s Case ID nalepený na médium
- Aktualizovaný case JSON súbor s uzlom `mediaIdentify` a druhým záznamom `chainOfCustody`

## Reference

ISO/IEC 27037:2012 – Section 5.2 (Identification of digital evidence)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Documentation)
ACPO Good Practice Guide – Principle 2 (Recording and preservation)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)