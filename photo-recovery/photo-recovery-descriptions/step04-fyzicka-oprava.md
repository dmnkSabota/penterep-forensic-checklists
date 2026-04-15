# Detaily testu

## Úkol

Vykonať fyzickú opravu poškodeného média.

## Obtiažnosť

Stredná až vysoká

## Časová náročnosť

30–180 minút (závisí od typu poškodenia)

## Automatický test

Nie

## Popis

K fyzickej oprave pristupujeme iba vtedy, keď test čitateľnosti klasifikuje médium ako UNREADABLE – prvý sektor je nečitateľný alebo zariadenie nebolo detekované operačným systémom. Oprava mení fyzický stav dôkazu, preto musí byť každý zásah kompletne zdokumentovaný v Chain of Custody v súlade s ISO/IEC 27037:2012. Pred začatím akejkoľvek opravy je povinný písomný informovaný súhlas klienta.

## Jak na to

**1. Informovaný súhlas klienta:**

Pripravte súhlasný formulár obsahujúci:
- Oprava môže nenávratne zničiť zostávajúce dáta
- Úspech nie je garantovaný
- Klient uznáva, že médium je už poškodené

Nechajte podpísať pred fyzickým zásahom. Fyzickú kópiu formulára uložte do dokumentácie prípadu, naskenovanú verziu archivujte digitálne pod Case ID.

**2. Fotodokumentácia pred opravou (min. 3 fotografie):**

- Celkový záber média s mierkou
- Detail oblasti poškodenia (konektor, prasklina, korózia)
- Pracovisko s pripraveným náradím

Pomenujte `CASE-ID_repair_before_01.jpg` a archivujte do dokumentácie prípadu.

**3. Vyhodnotenie a vykonanie opravy:**

Vyhodnoťte typ a rozsah poškodenia na základe vizuálnej inšpekcie z identifikácie média a diagnostických testov z testu čitateľnosti.

⚠️ Ak diagnostika naznačuje softwarový problém namiesto hardwarového poškodenia, fyzická oprava nie je potrebná – pokračujte priamo do forenzného imagingu.

Konkrétny postup závisí od typu poškodenia. Používajte ESD ochranu a zaznamenajte každý vykonaný krok do dokumentácie.

**4. Fotodokumentácia po oprave (min. 3 fotografie):**

Rovnaké zábery ako pred opravou (rovnaký uhol, oblasť, mierka) – umožňuje before/after porovnanie.
Pomenujte `CASE-ID_repair_after_01.jpg` a archivujte.

**5. Zápis záznamu opravy:**

Vytvorte záznam `mediaRepair` v JSON dokumentácii prípadu:

```json
{
  "mediaRepair": {
    "timestamp": "2025-01-26T11:15:00Z",
    "repairType": "hardwarová",
    "repairDescription": "Stručný popis vykonanej opravy alebo diagnostiky",
    "consentSigned": true,
    "toolsUsed": ["zoznam použitých nástrojov alebo diagnostických postupov"],
    "photosBeforeCount": 3,
    "photosAfterCount": 3,
    "photosArchived": true,
    "technician": "Meno Technika",
    "repairSuccessful": true,
    "retestResult": "READABLE",
    "retestTimestamp": "2025-01-26T11:30:00Z",
    "notes": "Poznámky o priebehu opravy a zisteniach"
  }
}
```

Pridajte záznam do `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T11:15:00Z",
  "analyst": "Meno Analytika",
  "action": "Fyzická oprava média dokončená – typ: stredná (výmena USB konektora)"
}
```

**6. Overenie opravy – opakovaný test čitateľnosti:**

Pripojte opravené médium cez write-blocker a zopakujte test čitateľnosti:
```bash
ptmediareadability /dev/sdX CASE-ID --analyst "Meno Analytika" --output repair_verification.json
```

Výsledok zapíšte do `mediaRepair.retestResult` a pokračujte:
- **READABLE** alebo **PARTIAL** → Forenzný imaging
- **UNREADABLE** → Zapíšte neúspešný výsledok do dokumentácie. Informujte klienta o možnostiach (špecializované laboratórium / ukončenie). Aktualizujte status prípadu (`REDIRECTED_TO_SPECIALIST` alebo `TERMINATED_REPAIR_FAILED`) a pridajte záverečný záznam do `chainOfCustody`.

**7. Informovanie klienta:**

Kontaktujte klienta s výsledkom opravy. Zaznamenajte komunikáciu do dokumentácie.

## Výsledek

- Before/after fotodokumentácia (min. 3+3 fotografie) archivovaná pod Case ID
- Podpísaný súhlasný formulár archivovaný (fyzická + digitálna kópia)
- Záznam `mediaRepair` a `chainOfCustody` v JSON dokumentácii prípadu
- Výsledok overovacieho testu po oprave zapísaný do dokumentácie

Pri úspešnej oprave workflow pokračuje do forenzného imagingu. Pri neúspešnej oprave prípad ukončený (`TERMINATED_REPAIR_FAILED`) alebo presmerovaný (`REDIRECTED_TO_SPECIALIST`).

## Reference

ISO/IEC 27037:2012 – Section 6.3.3 (Special considerations for handling damaged devices)
NIST SP 800-86 – Section 3.1.1.4 (Special Considerations – damaged media)
ACPO Good Practice Guide – Principle 2 (Competence and training of personnel)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)