# Detaily testu

## Úkol

Overiť fyzickú dostupnosť dôkazu a riešiť prípad nedostupnosti.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

5 minút (pri dostupnom dôkaze) / 30+ minút (pri riešení nedostupnosti)

## Automatický test

Nie

## Popis

Tento rozhodovací bod verifikuje fyzickú dostupnosť zariadenia alebo média určeného na forenzné spracovanie. Ak dôkaz nie je dostupný, workflow sa vetví do alternatívnej cesty zahŕňajúcej dokumentáciu problému a kontaktovanie zodpovednej osoby. Po vyriešení sa proces vracia k verifikácii dostupnosti.

## Jak na to

**Vetva ÁNO – dôkaz dostupný:**

Overte fyzickú prítomnosť zariadenia s odkazom na kontextový záznam z predchádzajúceho kroku. Skontrolujte, že zariadenie zodpovedá popisu v príkaze, dodacom liste alebo klientskej dokumentácii (typ, sériové číslo, stav obalu). Potvrďte dostupnosť zápisom do dokumentácie a pokračujte do identifikácie zariadenia.

**Vetva NIE – dôkaz nedostupný:**

**1. Dokumentácia problému:**
Zaznamenajte dôvod nedostupnosti: zariadenie neodovzdané / nesprávne zariadenie / poškodené v transporte / prístup zamietnutý / iné. Fotografujte miesto kde mal byť dôkaz umiestnený. Zaznamenajte čas a okolnosti zistenia.

**2. Kontaktovanie zodpovednej osoby:**
Identifikujte zodpovednú osobu (nadriadený dôstojník, kurierská spoločnosť, klient). Zaznamenajte čas kontaktu, meno osoby a dohodnuté riešenie.

**3. Čakanie a eskalácia:**
Proces sa pozastaví do vyriešenia. Každé opakovanie musí byť zaznamenané v CoC logu s časovou pečiatkou. Ak problém nie je vyriešiteľný v rozumnom čase, nastavte stav prípadu na `PENDING_EVIDENCE` a eskalujte nadriadenému.

## Výsledok

Pri ÁNO: potvrdenie dostupnosti zaznamenané v CoC logu, workflow pokračuje do identifikácie zariadenia. Pri NIE: dokumentácia problému archivovaná, zodpovedná osoba kontaktovaná, workflow pozastavený do vyriešenia.

## Reference

ISO/IEC 27037:2012 – Section 5.2 (Identification – Evidence availability)
NIST SP 800-86 – Section 3.1.1 (Collection Phase)
ACPO Good Practice Guide – Principle 1 (No action should change data)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)