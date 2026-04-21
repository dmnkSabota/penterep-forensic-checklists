# Detaily testu

## Úkol

Vykonať fyzickú identifikáciu zariadenia a fotodokumentáciu podľa ISO/IEC 27037:2012.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

15 minút

## Automatický test

Nie

## Popis

Fyzická identifikácia zariadenia zabezpečuje jeho jednoznačné odlíšenie od ostatných artefaktov a vytvára základ pre Chain of Custody dokumentáciu v súlade s ISO/IEC 27037:2012. Identifikácia musí byť natoľko kompletná, aby umožňovala jednoznačné určenie zariadenia aj bez jeho fyzickej prítomnosti – napríklad pri súdnom konaní. Všetky záznamy sú priamo prepojené s Case ID z predchádzajúceho kroku.

## Jak na to

**1. Fyzické identifikátory:**

Zaznamenajte priamo z fyzickej nálepky a tela zariadenia: typ zariadenia (notebook, desktop, telefón, tablet, externý disk, USB, SD karta), výrobcu, presný model, sériové číslo, farbu a materiál. Pre mobilné zariadenia zaznamenajte IMEI (`*#06#`) a MAC adresy sieťových adaptérov.

**2. Fotodokumentácia (minimálne 8 záberov):**

- Celkový záber so referenčnou mierkou
- Šesť strán zariadenia: vrch, spodok, predná strana, zadná strana, ľavá, pravá
- Makro detail sériového čísla a výrobných štítkov
- Detail každého viditeľného poškodenia alebo anomálie

Fotografie pomenujte podľa schémy `COC-2025-01-26-001_photo_01.jpg` a archivujte do dokumentácie prípadu.

**3. Stav zariadenia pri zaistení:**

Zaznamenajte stav napájania (zapnuté / vypnuté / standby / nabíjanie), stav batérie ak aplikovateľné, prítomnosť externých médií (vložená SIM, SD karta, USB) a viditeľné stopy opotrebovania alebo poškodenia.

**4. Súvisiace príslušenstvo:**

Zaznamenajte a zafotografujte všetko príslušenstvo zaistené spolu so zariadením: nabíjačky, káble, puzdro, prípadné fyzické poznámky alebo heslá.

**5. Aktualizácia záznamu prípadu:**

Pridajte záznam do `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T09:30:00Z",
  "analyst": "Meno Analytika",
  "action": "Fyzická identifikácia zariadenia a fotodokumentácia dokončená"
}
```

## Výsledok

Identifikačný formulár s kompletnými fyzickými a technickými parametrami. Fotodokumentácia (minimálne 8 fotografií) archivovaná v dokumentácii prípadu. Záznam `chainOfCustody` zapísaný. Workflow pokračuje do forenzného imagingu.

## Reference

ISO/IEC 27037:2012 – Section 5.2 (Identification of digital evidence)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Documentation)
ACPO Good Practice Guide – Principle 2 (Recording and preservation)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)