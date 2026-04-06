# Detaily testu

## Úkol

Vykonať fyzickú opravu poškodeného média.

## Obtiažnosť

Stredná

## Časová náročnosť

30–180 minút (závisí od typu opravy)

## Automatický test

Nie

## Popis

Fyzická oprava je proces, pri ktorom sa pokúšame obnoviť funkčnosť poškodeného úložného média natoľko, aby bolo možné z neho vytvoriť forenzný obraz. Tento krok je aktivovaný iba vtedy, keď test čítateľnosti (Krok 3) určí stav média ako UNREADABLE.

Každá oprava mení fyzický stav dôkazu a musí byť kompletne zdokumentovaná pre Chain of Custody. Niektoré zásahy sú nezvratné a úspešnosť nie je garantovaná – pred začatím je nutné získať písomný informovaný súhlas klienta.

## Jak na to

**1. Informovaný súhlas klienta:**

Pripravte súhlasný formulár s jasným popisom rizík: oprava môže nenávratne zničiť zostávajúce dáta, úspech nie je garantovaný, niektoré zásahy sú nezvratné. Nechajte klienta podpísať pred akýmkoľvek fyzickým zásahom. Fyzickú kópiu uložte do zakladača prípadu, naskenovanú kópiu archivujte v digitálnej dokumentácii prípadu.

**2. Fotodokumentácia PRED opravou:**

Minimálne tri fotografie sú povinné:
- Celkový záber média s mierkou
- Detailný záber oblasti plánovanej opravy
- Fotografia pripravených nástrojov a pracoviska

Tieto fotografie slúžia ako baseline pre porovnanie po oprave. Uložte ich do dokumentácie prípadu pred začatím akéhokoľvek fyzického zásahu.

**3. Klasifikácia a vykonanie opravy:**

Zvoľte typ opravy podľa charakteru poškodenia:

- **Jednoduchá** – čistenie kontaktov izopropylalkoholom, vyrovnanie ohnutých pinov pinzetou, odstránenie prachu z konektorov
- **Stredná** – výmena USB konektora spájkovaním, odstránenie korózie skalpelom, oprava zlomeného púzdra epoxidovým lepidlom
- **Komplexná** – chip-off technika (odpájanie pamäťového čipu z PCB), oprava prasklej PCB vodivým lepidlom, prenos čipu na donorovú PCB – vyžaduje mikroskop a špecializované vybavenie

Pri každom kroku opravy vytvorte fotografiu dokumentujúcu aktuálny stav. Používajte vhodné nástroje – antištatickú pinzetu, mikroskop pre SMD komponenty, teplotne kontrolovanú spájkovačku (max. 350 °C).

**4. Fotodokumentácia PO oprave:**

Odfotografujte médium v rovnakých záberoch ako pred opravou (rovnaký uhol, rovnaká oblasť, rovnaká mierka). Táto symetria umožňuje priame before/after porovnanie v dokumentácii. Archivujte fotografie do dokumentácie prípadu.

**5. Zápis záznamu opravy a aktualizácia CoC:**

Zapíšte uzol `physicalRepair` do dokumentácie prípadu:
- Typ opravy – jednoduchá / stredná / komplexná
- Popis opravy – čo konkrétne bolo vykonané
- Súhlas podpísaný – áno / nie
- Použité nástroje – zoznam nástrojov
- Počet fotografií pred opravou – min. 3
- Počet fotografií po oprave – min. 3
- Fotografie archivované – áno / nie
- Technik – meno technika

Pridajte záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T11:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Fyzická oprava média – typ: stredná, výsledok: médium funkčné"
}
```

**6. Overenie opravy:**

Pripojte opravené médium cez write-blocker a zopakujte Krok 3 (Test čitateľnosti) na rovnakom médiu. Na základe nového výsledku:
- READABLE alebo PARTIAL → workflow pokračuje do Kroku 5 (Forenzný imaging)
- UNREADABLE → zvážte jeden ďalší pokus inou metódou alebo informujte klienta o možnosti zaslania do špecializovaného cleanroom laboratória. Workflow sa zastavuje.

## Výsledek

- Before/after fotodokumentácia archivovaná v dokumentácii prípadu pod Case ID
- Podpísaný súhlasný formulár archivovaný (fyzická kópia + naskenovaná digitálna kópia)
- Uzol `physicalRepair` vyplnený v dokumentácii prípadu
- Pri úspešnej oprave (READABLE alebo PARTIAL) workflow pokračuje do ďalšieho kroku
- Pri neúspešnej oprave klient informovaný o možnostiach ďalšieho postupu

## Reference

ISO/IEC 27037:2012 – Section 6.3.3 (Handling damaged devices)
NIST SP 800-86 – Section 3.1.1.4 (Special Considerations)
ACPO Good Practice Guide – Principle 2 (Competence)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)