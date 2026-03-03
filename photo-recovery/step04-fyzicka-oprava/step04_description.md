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

Pripravte súhlasný formulár s jasným popisom rizík: oprava môže nenávratne zničiť zostávajúce dáta, úspech nie je garantovaný, niektoré zásahy sú nezvratné. Nechajte klienta podpísať pred akýmkoľvek fyzickým zásahom. Kópiu archivujte do Case dokumentácie.

**2. Fotodokumentácia PRED opravou:**

Minimálne tri fotografie povinné: celkový záber média s mierkou, detailný záber oblasti plánovanej opravy, fotografia pripravených nástrojov a pracoviska. Tieto fotografie slúžia ako baseline pre porovnanie po oprave.

**3. Klasifikácia a vykonanie opravy:**

Zvoľte typ opravy podľa poškodenia:

- **Jednoduchá** – čistenie kontaktov izopropylalkoholom, vyrovnanie ohnutých pinov pinzetou, odstránenie prachu z konektorov
- **Stredná** – výmena USB konektora spájkovaním, odstránenie korózie skalpelom, oprava zlomeného púzdra epoxidovým lepidlom
- **Komplexná** – chip-off technika (odpájanie pamäťového čipu z PCB), oprava prasklej PCB vodivým lepidlom, prenos čipu na donorovú PCB – vyžaduje mikroskop a špecializované vybavenie

Pri každom kroku opravy vytvorte fotografiu dokumentujúcu aktuálny stav. Používajte vhodné nástroje – antištatickú pinzetu, mikroskop pre SMD komponenty, teplotne kontrolovanú spájkovačku (max. 350°C).

**4. Fotodokumentácia PO oprave:**

Odfotografujte médium v rovnakých záberoch ako pred opravou. Táto symetria umožňuje priame before/after porovnanie v dokumentácii.

**5. Overenie opravy:**

Pripojte opravené médium cez write-blocker a spustite Readability Test. Na základe výsledku:
- READABLE alebo PARTIAL → pokračujte na vytvoreni obrazu 
- UNREADABLE → jeden ďalší pokus inou metódou, alebo kontaktujte klienta s odporúčaním zaslania do špecializovaného cleanroom laboratória

**6. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte `physicalRepair` node a nový `chainOfCustody` záznam do poľa `nodes`:

```json
{
  "type": "physicalRepair",
  "properties": {
    "repairType": "stredná",
    "repairDescription": "Výmena USB konektora spájkovaním",
    "consentSigned": true,
    "toolsUsed": ["spájkovačka 350°C", "antištatická pinzeta", "mikroskop"],
    "photosBeforeCount": 3,
    "photosAfterCount": 3,
    "photosArchived": true,
    "outcome": "READABLE",
    "outcomeNotes": "Médium čitateľné po výmene konektora, readability test prešiel",
    "nextStep": 5,
    "technician": "Dominik Sabota",
    "completedAt": "2025-01-26T13:00:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step04-fyzicka-oprava",
    "action": "Physical repair completed – connector replaced, media now READABLE",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T13:00:00Z",
    "notes": null
  }
}
```

Ak oprava nebola úspešná, nastavte `"outcome": "UNREADABLE"` a `"nextStep": null` a zaznamenajte dôvod do `outcomeNotes`.

## Výsledek

Oprava vykonaná a zdokumentovaná. Vytvorené výstupy:
- Before/after fotodokumentácia archivovaná pod Case ID
- Podpísaný súhlasný formulár (fyzická kópia + naskenovaná digitálna kópia)
- Aktualizovaný case JSON súbor s `physicalRepair` nodom a ďalším `chainOfCustody` záznamom
- Pri úspešnej oprave (READABLE alebo PARTIAL) workflow pokračuje Krokom 5
- Pri neúspešnej oprave klient informovaný o možnostiach ďalšieho postupu

## Reference

ISO/IEC 27037:2012 – Section 6.3.3 (Handling damaged devices)
NIST SP 800-86 – Section 3.1.1.4 (Special Considerations)
ACPO Good Practice Guide – Principle 2 (Competence)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)
