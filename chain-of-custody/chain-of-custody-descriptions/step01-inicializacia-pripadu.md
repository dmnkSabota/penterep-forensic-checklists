# Detaily testu

## Úkol

Inicializovať prípad, vytvoriť Case ID a zaznamenať kontextové informácie z miesta zaistenia dôkazu.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

20 minút

## Automatický test

Nie

## Popis

Prvý krok procesu zabezpečenia digitálnych dôkazov spája administratívnu inicializáciu prípadu so zaznamenaním operatívnych informácií z miesta zaistenia. Analytik vytvorí unikátny identifikátor prípadu (Case ID), zaznamená kontextové informácie a inicializuje Chain of Custody log v súlade s ISO/IEC 27037:2012. Case ID slúži ako primárny kľúč pre všetky dokumenty, hashe a fyzické štítky počas celého procesu.

Krok je navrhnutý duálne – funguje rovnako na mieste zaistenia (domová prehliadka, zadržanie) aj pri príjme kuriérsky doručeného média v laboratóriu. Pri laboratórnom príjme sa kontextové informácie preberajú z dodacieho listu alebo klientskej dokumentácie.

## Jak na to

**1. Vytvorenie Case ID:**

Vytvorte Case ID podľa formátu `COC-YYYY-MM-DD-XXX`, kde `COC` je fixný prefix identifikujúci typ scenára, `YYYY-MM-DD` je aktuálny dátum a `XXX` je trojciferné poradové číslo prípadu v daný deň. Príklad: `COC-2025-01-26-001`. Overte, že toto ID v archíve ešte neexistuje.

**2. Základné údaje prípadu:**

Zaznamenajte: meno a číslo odznaku analytika, pracovisko a laboratórium, právny základ zaistenia (domová prehliadka §83a TŘ / zaistenie §78 TŘ / dobrovoľné odovzdanie / komerčný príjem) a referenčné číslo vyšetrovacieho spisu ak je dostupné.

**3. Záznam kontextu:**

Pri zaistení na mieste: zaznamenajte presnú adresu a lokáciu, mená a funkcie všetkých prítomných osôb, stav zariadenia pri nájdení (zapnuté / vypnuté / standby), okolnosti zaistenia a prípadné vyhlásenia vlastníka.

Pri laboratórnom príjme: zaznamenajte odosielateľa, dátum a čas príjmu, stav obalu pri prevzatí a referenciu na klientsku dokumentáciu alebo dodací list.

**4. Inicializácia záznamu prípadu:**

Vytvorte JSON záznam prípadu so stavom `INITIATED` a prvým záznamom `chainOfCustody`:
```json
{
  "caseId": "COC-2025-01-26-001",
  "status": "INITIATED",
  "chainOfCustody": [
    {
      "timestamp": "2025-01-26T09:00:00Z",
      "analyst": "Meno Analytika",
      "action": "Prípad inicializovaný, záznam kontextu vytvorený"
    }
  ]
}
```
Uložte záznam do dokumentácie prípadu. Vytlačte príjmový lístok s Case ID pre fyzickú evidenciu.

## Výsledok

Case ID dokument (JSON) so stavom `INITIATED` a prvým `chainOfCustody` záznamom uložený v dokumentácii prípadu. Workflow pokračuje do overenia dostupnosti dôkazu.

## Reference

ISO/IEC 27037:2012 – Section 5 (Guidelines for identification)
NIST SP 800-86 – Section 3.1.1 (Collection Phase – Documentation)
ACPO Good Practice Guide – Principle 2 (Recording and preservation)
Zákon č. 141/1961 Sb. (Trestní řád) – §78, §83a

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)