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

Fyzická identifikácia média zabezpečuje jeho jednoznačné odlíšenie od ostatných artefaktov v laboratóriu a vytvára základ pre Chain of Custody dokumentáciu v súlade s ISO/IEC 27037:2012. Všetky záznamy z tohto kroku sú priamo prepojené s Case ID z kroku 1.

## Jak na to

**1. Informácie o médiu (podľa klienta):**

Zaznamenajte do formulára základné informácie podľa toho, čo klient uvádza:
- **Typ zariadenia** – SD karta / microSD / USB flash disk / HDD / SSD / iné
- **Odhadovaná kapacita** – podľa vyjadrenia klienta
- **Viditeľné poškodenie** – popis alebo žiadne

Tieto údaje budú overené fyzicky v nasledujúcich krokoch.

**2. Fotodokumentácia:**

Vyhotovte komplexnú fotodokumentáciu média – minimálne 8 záberov:
- Celkový záber s mierkou
- Šesť strán zariadenia: vrch, spodok, predná strana, zadná strana, ľavá, pravá
- Makro detail sériového čísla
- Detail každého viditeľného poškodenia alebo anomálie

Do formulára zadajte **Počet fotografií** a po archivácii aktivujte prepínač **Fotografie archivované**.

**3. Fyzické identifikátory:**

Zaznamenajte do formulára overené fyzické parametre zariadenia: **Výrobca**, **Model**, **Sériové číslo** (úplné), **Farba / materiál**, **Dĺžka (mm)**, **Šírka (mm)**, **Výška (mm)** a **Kapacita (nálepka)** z fyzickej nálepky zariadenia. Typ zariadenia určuje, ktoré diagnostické nástroje budú relevantné v Kroku 3.

**4. Fyzický stav média:**

Vyberte **Stav zariadenia** (nové / mierne použité / intenzívne použité / poškodené) a do poľa **Poznámka k stavu** zaznamenajte viditeľné stopy používania – škrabance, znečistenie, zmeny farby, stav nálepiek.

**5. Fyzické poškodenie:**

Ak je poškodenie prítomné, aktivujte prepínač **Poškodenie prítomné** a vyplňte:
- **Typ poškodenia** – prasklina púzdra / zlomený konektor / deformácia / korózia kontaktov
- **Lokalizácia poškodenia** – presné miesto na zariadení
- **Závažnosť poškodenia:**
  - Malé – kozmetické, funkčnosť neovplyvnená
  - Stredné – čiastočne funkčné, vyžaduje opravu
  - Kritické – znemožňuje pripojenie

**6. Viditeľné indikátory šifrovania:**

Skontrolujte, či médium nenesie viditeľné znaky šifrovania – BitLocker štítok od výrobcu, VeraCrypt bootloader nálepku, alebo firemný bezpečnostný štítok. Ak sú prítomné, aktivujte prepínač **Indikátor šifrovania viditeľný** a informujte klienta, že recovery kľúč alebo heslo bude nevyhnutné. Technická verifikácia šifrovania prebehne v Kroku 3.

**7. Fyzické označenie:**

Nalepte štítok s Case ID na médium – nie na konektor, nie cez sériové číslo, nie cez pôvodné výrobné nálepky. Po nalepení aktivujte prepínač **Štítok nalepený**.

**8. Archivácia fotografií a formulárov:**

Všetky fotografie a formuláre uložte do dokumentácie Case pod príslušným Case ID a potvrďte archiváciu vo formulári scenára.

**9. Aktualizácia záznamu:**

Skontrolujte, že všetky povinné polia formulára sú vyplnené a potvrďte krok.

## Výsledek

Médium je identifikované a zdokumentované. Vytvorené výstupy:
- Fotodokumentácia (minimálne 8 fotografií) archivovaná pod Case ID
- Identifikačný formulár s kompletnými fyzickými parametrami
- Fyzický štítok s Case ID nalepený na médium
- Vyplnený uzol identifikácie média s druhým záznamom `chainOfCustody`

## Reference

ISO/IEC 27037:2012 – Section 5.2 (Identification of digital evidence)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Documentation)
ACPO Good Practice Guide – Principle 2 (Recording and preservation)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)