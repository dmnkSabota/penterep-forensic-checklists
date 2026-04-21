# Detaily testu

## Úkol

Vyplniť Chain of Custody formulár, fyzicky označiť zariadenie tamper-evident štítkom a uložiť ho do zabezpečenej úschovne.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30 minút

## Automatický test

Áno

## Popis

Tento krok konsoliduje tri sekvenčné laboratórne úkony do jednej ucelenej dokumentačno-zabezpečovacej fázy: vyplnenie právne záväzného CoC formulára, fyzické označenie zariadenia a jeho uloženie do zabezpečenej úschovne. Všetky tri aktivity prebiehajú bezprostredne po sebe bez prerušenia – ich zlúčenie odráža reálny priebeh laboratórnej praxe. Po uložení média do úschovne sú všetky ďalšie analytické operácie vykonávané výhradne na forenznom obraze.

## Jak na to

**1. Vyplnenie CoC formulára:**

Systém automaticky predvyplní dostupné polia z JSON reportov predchádzajúcich krokov: Case ID a kontext (Krok 1), identifikačné údaje zariadenia (Krok 3), `source_hash` s časovou značkou a metadata imagingu (Krok 4), `image_hash` a výsledok verifikácie (Krok 5).

Sekcie CoC formulára:
- **Identifikačná sekcia:** Case ID, evidenčné číslo, dátum príjmu, lokácia zaistenia, meno analytika, právny základ
- **Popis zariadenia:** typ, výrobca, model, sériové číslo, stav pri zaistení
- **Kryptografické identifikátory:** `source_hash`, `image_hash`, výsledok verifikácie (MATCH), počet pokusov imagingu
- **Technická dokumentácia:** nástroj a verzia, dátum a čas vytvorenia obrazu, write-blocker (typ, model, SN)
- **Záznamy o odovzdaní:** vyplní sa v Kroku 7

Vizuálne overte predvyplnené hash hodnoty – porovnajte posledných 8 znakov s fyzickými zápiskami z Kroku 4. Podpíšte CoC formulár s dátumom a časom.

**2. Fyzické označenie zariadenia:**

Vytlačte tamper-evident štítok obsahujúci: Case ID, evidenčné číslo, dátum označenia, meno a podpis analytika. Nalepte štítok podľa pravidiel:
- Nesmie zakrývať sériové číslo ani identifikačné štítky výrobcu
- Nesmie byť na konektoroch ani pohyblivých častiach
- Musí byť viditeľný bez nutnosti demontáže

Pre malé zariadenia (USB, SD karta) použite štítok na ochrannom antistatickom vaku. Odfotografujte zariadenie s viditeľným štítkom z minimálne troch uhlov a archivujte fotografie do dokumentácie prípadu pod názvom `COC-2025-01-26-001_label_01.jpg`.

**3. Uloženie do úschovne:**

Vložte zariadenie do antistatického vaku a zatavte ho – elektrostatický výboj môže poškodiť flash pamäte a pevné disky. Na vonkajšiu stranu nalepte identifikačný štítok s Case ID. Overte environmentálne podmienky úschovne (teplota 15–25 °C, vlhkosť 40–60 %). Zaznamenajte presnú lokáciu uloženia (miestnosť, regál, polička) do registra úschovne.

**4. Aktualizácia záznamu prípadu:**

Pridajte záznam do `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T12:00:00Z",
  "analyst": "Meno Analytika",
  "action": "CoC formulár podpísaný, zariadenie označené a uložené do úschovne – lokácia: Miestnosť B03, Regál 4"
}
```

## Výsledok

CoC formulár podpísaný a uložený v PDF a JSON formáte. Zariadenie fyzicky označené tamper-evident štítkom s fotodokumentáciou. Originálne médium uložené v zabezpečenej úschovni so zaznamenanou lokáciou. Záznam `chainOfCustody` zapísaný. Workflow pokračuje do exportu a odovzdania dokumentácie.

## Reference

ISO/IEC 27037:2012 – Section 5.2, 5.3, 5.4 (Identification, Chain of Custody, Secure storage)
NIST SP 800-86 – Section 3.1.1 & 3.1.3 (Collection and Reporting)
ACPO Good Practice Guide – Principle 2 & 4 (Preservation and Documentation)
Zákon č. 141/1961 Sb. (Trestní řád) – §89

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)