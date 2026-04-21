# Detaily testu

## Úkol

Exportovať kompletnú dokumentáciu prípadu, odovzdať ju vyšetrovateľovi a formálne uzavrieť prípad.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Nie

## Popis

Záverečný krok konsoliduje export dokumentácie, fyzické odovzdanie vyšetrovateľovi a uzavretie prípadu do jednej reporting fázy. Systém vygeneruje PDF a JSON dokumentáciu z dostupných reportov; analytik ju odovzdá vyšetrovateľovi s podpismi oboch strán, aktualizuje CoC formulár o záznam odovzdania a nastaví stav prípadu na `CLOSED`. Fyzické odovzdanie s overením totožnosti a získaním podpisov je právny úkon vyžadujúci ľudskú zodpovednosť.

## Jak na to

**1. Export dokumentácie:**

Systém automaticky konsoliduje JSON reporty zo všetkých krokov a vygeneruje:
- `COC-2025-01-26-001_documentation.pdf` – pre právne použitie (titulná strana, prehľad prípadu, technická dokumentácia, kryptografická verifikácia, CoC timeline, príloha CoC formulára)
- `COC-2025-01-26-001_documentation.json` – pre automatizované spracovanie platformou Penterep

Po vygenerovaní systém vypočíta SHA-256 hash oboch dokumentov a zaznamená ich do CoC logu – umožňuje overenie nemodifikovanosti kedykoľvek v budúcnosti.

**2. Príprava odovzdávacej sady:**

Skompletizujte: vytlačený PDF dokument, USB nosič s digitálnymi verziami (PDF + JSON), podpísaný CoC formulár a odovzdávací protokol. Vytvorte `MANIFEST.json` so zoznamom všetkých odovzdávaných súborov a ich SHA-256 hashmi – vyšetrovateľ ním môže kedykoľvek overiť integritu prijatých dát.

**3. Fyzické odovzdanie:**

Overte totožnosť vyšetrovateľa. Vyšetrovateľ môže pred podpisom overiť integritu dokumentov:
```bash
sha256sum COC-2025-01-26-001_documentation.pdf
```
Obe strany podpíšu odovzdávací protokol s dátumom a časom – každá strana dostane jednu kópiu.

**4. Uzavretie prípadu:**

Doplňte do CoC formulára sekciu „Záznamy o odovzdaní" (meno preberajúcej osoby, dátum, účel odovzdania) a formulár znovu podpíšte. Nastavte stav prípadu na `CLOSED` a pridajte záverečný záznam do `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T13:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Dokumentácia odovzdaná vyšetrovateľovi, prípad uzavretý – stav: CLOSED"
}
```
Forenzný obraz zostáva archivovaný pre prípadné ďalšie analýzy. Originálne médium zostáva v zabezpečenej úschovni.

## Výsledok

PDF a JSON dokumentácia vygenerovaná s SHA-256 hashmi. Podpísaný odovzdávací protokol (dve kópie). USB nosič s dokumentáciou odovzdaný vyšetrovateľovi. CoC formulár aktualizovaný sekciou odovzdania. Prípad uzavretý so stavom `CLOSED`. Kompletný CoC log archivovaný.

## Reference

ISO/IEC 27037:2012 – Section 5.3.4 & Section 8 (Transfer of custody, Documentation)
NIST SP 800-86 – Section 3.1.3 (Reporting Phase)
ACPO Good Practice Guide – Principle 4 (Documentation)
Zákon č. 141/1961 Sb. (Trestní řád) – §65 (Odovzdanie dôkazov)

## Stav

Manuálny proces – netestovateľný automaticky

## Nález

(prázdne – vyplní sa po odovzdaní)