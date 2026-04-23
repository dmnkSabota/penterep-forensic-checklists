# Detaily testu

## Úkol

Odovzdať všetky výsledky klientovi, uzavrieť Chain of Custody a finalizovať prípad.

## Obtiažnosť

Stredná

## Časová náročnosť

90 minút

## Automatický test

Nie

## Popis

Odovzdanie klientovi je záverečný krok celého procesu obnovy fotografií. Zahŕňa prípravu záverečného balíka, kontaktovanie klienta, samotné odovzdanie, uzavretie Chain of Custody a archiváciu prípadu.

Fyzické odovzdanie dôkazového materiálu s overením totožnosti, získanie podpisov a uzavretie Chain of Custody sú právne úkony vyžadujúce ľudskú zodpovednosť – nie je ich možné nahradiť softvérom.

## Jak na to

**1. Príprava záverečného balíka:**

Skompletizujte nasledujúce súbory z dokumentácie prípadu:

| Obsah | Zdroj |
|-------|-------|
| Obnovené fotografie | `{CASE_ID}_validation/valid/` |
| Opravené fotografie (ak prebehla oprava) | `{CASE_ID}_repair/repaired/` |
| Záverečná správa | `{CASE_ID}_final_report/FINAL_REPORT.json` + `.pdf` |
| Pokyny pre klienta | `{CASE_ID}_final_report/README.txt` |
| Kontrolný zoznam | `{CASE_ID}_final_report/delivery_checklist.json` |

Ručne vytvorte `MANIFEST.json` so zoznamom všetkých odovzdávaných súborov a ich SHA-256 kontrolnými súčtami – klient ním môže kedykoľvek overiť integritu prijatých dát.

**2. Kontaktovanie klienta:**

Informujte klienta o výsledkoch: počet obnovených fotografií, hodnotenie kvality obnovy a dohodnutý spôsob odovzdania. Pri nedostatočnej odpovedi kontaktujte znova po 3 dňoch.

**3. Samotné odovzdanie:**

**Osobné odovzdanie:**
- Overte totožnosť klienta (občiansky preukaz)
- Odovzdajte záverečný balík aj pôvodné médium
- Vysvetlite obsah záverečnej správy a `README.txt`
- Získajte podpis odovzdávacieho protokolu

**Kuriérska preprava:**
- Dvojité balenie, poistenie zásielky
- Zaznamenajte číslo sledovania
- Potvrďte prevzatie podpisom pri doručení

**Elektronické odovzdanie:**
- Zabezpečený odkaz s heslom zaslaným samostatnou cestou
- Platnosť odkazu 7 dní
- Klient overí integritu pomocou `MANIFEST.json`
- Pôvodné médium odovzdajte kuriérom

**4. Uzavretie Chain of Custody:**

Pridajte záverečný záznam do `case.json`:
```json
{
  "timestamp": "2025-01-26T18:30:00Z",
  "analyst": "Meno Analytika",
  "action": "Prípad uzavretý – balík odovzdaný klientovi, pôvodné médium vrátené, stav: CLOSED",
  "mediaSerial": "SN-XXXXXXXX"
}
```

Overte úplnosť záznamu – nesmú existovať časové medzery bez zodpovednej osoby. Nastavte stav prípadu na `CLOSED`.

**5. Archivácia prípadu:**

Archivujte všetky súbory prípadu v súlade s platnými právnymi predpismi o uchovávaní záznamov. Archivácia zahŕňa:
- Forenzný obraz média (`{CASE_ID}.dd` + `.sha256`)
- Všetky JSON výstupy jednotlivých krokov
- Záverečnú správu a podpísaný odovzdávací protokol
- `MANIFEST.json` s kontrolnými súčtami odovzdaného balíka

**6. Záverečná kontrola:**

Pred uzavretím overte:
- Odovzdávací protokol podpísaný oboma stranami
- Pôvodné médium vrátené klientovi
- Chain of Custody bez medzier, stav `CLOSED`
- Všetky súbory archivované
- `MANIFEST.json` uložený v dokumentácii prípadu

## Výsledek

Záverečný balík odovzdaný klientovi. Obsah: obnovené fotografie, záverečná technická správa, `README.txt` a `MANIFEST.json` so SHA-256 kontrolnými súčtami. Chain of Custody uzavretá so stavom `CLOSED`. Všetky súbory archivované v súlade s platnými právnymi predpismi.

## Reference

ISO/IEC 27037:2012 – Section 5.5 (Preservation)

NIST SP 800-86 – Section 2.4 (Reporting)

ACPO Good Practice Guide – Principle 4 (Overall responsibility for compliance)

GDPR (Nariadenie EÚ 2016/679) – Článok 30 (Záznamy o spracovateľských činnostiach)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po odovzdaní)