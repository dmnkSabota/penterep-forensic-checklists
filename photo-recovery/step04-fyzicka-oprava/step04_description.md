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

Fyzická oprava je proces, pri ktorom sa pokúšame obnoviť funkčnosť poškodeného úložného média natoľko, aby bolo možné z neho vytvoriť forenzný obraz. Tento krok je aktivovaný iba vtedy, keď test čítateľnosti určí stav média ako UNREADABLE.

Každá oprava mení fyzický stav dôkazu a musí byť kompletne zdokumentovaná pre Chain of Custody. Niektoré zásahy sú nezvratné a úspešnosť nie je garantovaná – pred začatím je nutné získať písomný informovaný súhlas klienta.

## Jak na to

**1. Informovaný súhlas klienta:**

Pripravte súhlasný formulár s jasným popisom rizík: oprava môže nenávratne zničiť zostávajúce dáta, úspech nie je garantovaný, niektoré zásahy sú nezvratné. Nechajte klienta podpísať pred akýmkoľvek fyzickým zásahom. Naskenovanú kópiu nahrajte do záložky **Přílohy** projektu.

**2. Fotodokumentácia PRED opravou:**

Minimálne tri fotografie povinné: celkový záber média s mierkou, detailný záber oblasti plánovanej opravy, fotografia pripravených nástrojov a pracoviska. Tieto fotografie slúžia ako baseline pre porovnanie po oprave. Nahrajte ich do záložky **Přílohy** projektu.

**3. Klasifikácia a vykonanie opravy:**

Zvoľte typ opravy podľa poškodenia:

- **Jednoduchá** – čistenie kontaktov izopropylalkoholom, vyrovnanie ohnutých pinov pinzetou, odstránenie prachu z konektorov
- **Stredná** – výmena USB konektora spájkovaním, odstránenie korózie skalpelom, oprava zlomeného púzdra epoxidovým lepidlom
- **Komplexná** – chip-off technika (odpájanie pamäťového čipu z PCB), oprava prasklej PCB vodivým lepidlom, prenos čipu na donorovú PCB – vyžaduje mikroskop a špecializované vybavenie

Pri každom kroku opravy vytvorte fotografiu dokumentujúcu aktuálny stav. Používajte vhodné nástroje – antištatickú pinzetu, mikroskop pre SMD komponenty, teplotne kontrolovanú spájkovačku (max. 350°C).

**4. Fotodokumentácia PO oprave:**

Odfotografujte médium v rovnakých záberoch ako pred opravou. Táto symetria umožňuje priame before/after porovnanie v dokumentácii. Nahrajte fotografie do záložky **Přílohy** projektu.

**5. Vyplnenie záznamu opravy na Penterep:**

Na uzle zariadenia vyplňte formulár záznamu fyzickej opravy:
- Typ opravy – jednoduchá / stredná / komplexná
- Popis opravy – čo konkrétne bolo vykonané
- Súhlas podpísaný – potvrďte po fyzickom podpise a archivácii v Přílohy
- Použité nástroje – zoznam nástrojov
- Počet fotografií pred opravou – min. 3
- Počet fotografií po oprave – min. 3
- Fotografie archivované – potvrďte po nahratí do Přílohy
- Technik – meno technika

**6. Overenie opravy:**

Po vyplnení formulára pripojte opravené médium cez write-blocker a spustite Krok 3 znova na rovnakom uzle zariadenia. Krok 3 automaticky zapíše výsledok overenia. Na základe výsledku:
- READABLE alebo PARTIAL → workflow pokračuje na vytvorenie obrazu
- UNREADABLE → jeden ďalší pokus inou metódou, alebo kontaktujte klienta s odporúčaním zaslania do špecializovaného cleanroom laboratória, workflow sa zastavuje

## Výsledek

- Before/after fotodokumentácia archivovaná v záložke Přílohy pod Case ID
- Podpísaný súhlasný formulár archivovaný v záložke Přílohy (fyzická kópia + naskenovaná digitálna kópia)
- Vyplnený uzol `physicalRepair` s výsledkom opravy
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