# Detaily testu

## Úkol

Odovzdať všetky výsledky klientovi, uzavrieť reťazec úschovy a finalizovať prípad.

## Obtiažnosť

Stredná

## Časová náročnosť

90 minút

## Automatický test

Nie

## Popis

Odovzdanie klientovi je záverečný krok celého procesu obnovy fotografií. Zahŕňa prípravu záverečného balíka, kontaktovanie klienta, samotné odovzdanie, uzavretie reťazca úschovy a archiváciu prípadu.

Tento krok predstavuje zámerné ukončenie automatizácie. Fyzické odovzdanie dôkazového materiálu s overením totožnosti, získanie podpisov a uzavretie reťazca úschovy sú právne úkony vyžadujúce ľudskú zodpovednosť, ktoré nie je možné nahradiť softvérom.

## Jak na to

**1. Príprava záverečného balíka:**

Skopíruj obnovené fotografie z adresárov `validation/valid/` a `repair/repaired/` (ak prebehla oprava), záverečnú správu `FINAL_REPORT.json`, `FINAL_REPORT.pdf` a `README.txt`. Vytvor súbor `MANIFEST.json` so zoznamom všetkých súborov a ich SHA-256 kontrolnými súčtami. Voliteľne skomprimuj celý balík do ZIP archívu.

**2. Kontaktovanie klienta:**

Informuj klienta o výsledkoch: počet obnovených fotografií, hodnotenie kvality obnovy a možnosti odovzdania. Odpoveď sa očakáva do 24 hodín, opätovný kontakt po 3 dňoch bez reakcie.

**3. Samotné odovzdanie:**

Pri osobnom odovzdaní: over totožnosť klienta, odovzdaj balík aj pôvodné médium, vysvetli obsah záverečnej správy a získaj podpis odovzdávacieho protokolu. Pri kuriérskej preprave: dvojité balenie, poistenie zásielky, sledovanie, podpis pri prevzatí. Pri elektronickom odovzdaní: zabezpečený odkaz s heslom zaslaným samostatnou cestou, platnosť 7 dní, kontrolné súčty pre overenie integrity, pôvodné médium kuriérom.

**4. Uzavretie reťazca úschovy:**

Pridaj záverečný záznam „vrátené klientovi", získaj podpisy všetkých strán, over úplnosť záznamu bez medzier, nastav stav prípadu na `UZAVRETÝ`. Pôvodné médium je vrátené klientovi, forenzná kópia je archivovaná.

**5. Uzavretie prípadu:**

Archivuj všetky súbory s retenčnou lehotou 7 rokov v zmysle GDPR čl. 30. Aktualizuj stav prípadu v databáze na `UZAVRETÝ` a zaznamenaj súhrn priebehu vrátane ponaučení pre budúce prípady.

**6. Aktualizácia case JSON:**

Otvor súbor `PHOTORECOVERY-2025-01-26-001.json`, pridaj uzol `caseDelivery` a záverečný záznam `chainOfCustody` do poľa `nodes`. Súčasne aktualizuj hodnotu `status` v hlavnom objekte `properties` z `"INITIATED"` na `"CLOSED"`:
```json
{
  "type": "caseDelivery",
  "properties": {
    "deliveryMethod": "osobné odovzdanie",
    "deliveredTo": "Jan Novak",
    "identityVerified": true,
    "originalMediaReturned": true,
    "protocolSigned": true,
    "manifestPath": "/var/forensics/delivery/PHOTORECOVERY-2025-01-26-001/MANIFEST.json",
    "totalFilesDelivered": 363,
    "archiveRetentionYears": 7,
    "caseStatus": "CLOSED",
    "completedAt": "2025-01-26T16:00:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step15-odovzdanie-klientovi",
    "action": "Case closed – all materials delivered to client, original media returned, Chain of Custody complete",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T16:00:00Z",
    "notes": "Odovzdávací protokol podpísaný oboma stranami. Prípad archivovaný s retenčnou lehotou 7 rokov."
  }
}
```

Pri elektronickom odovzdaní nastav `"deliveryMethod": "elektronické odovzdanie"` a doplň pole `"secureLink"` s URL a dobou platnosti. Pri kuriérskej preprave nastav `"deliveryMethod": "kuriér"` a doplň pole `"trackingNumber"`.

Po aktualizácii uzlov zmeň tiež hlavný `status` v časti `properties` celého JSON súboru:
```json
"status": "CLOSED"
```

## Výsledek

Záverečný balík pre klienta obsahuje: obnovené fotografie, záverečnú technickú správu, pokyny pre klienta a súbor `MANIFEST.json` s SHA-256 kontrolnými súčtami všetkých odovzdaných súborov.

Dokumentácia: informačný e-mail odoslaný, odovzdávací protokol podpísaný oboma stranami, reťazec úschovy má stav `UZAVRETÝ` bez medzier v zázname.

Archivácia prípadu: všetky súbory archivované s retenčnou lehotou 7 rokov, stav v databáze `UZAVRETÝ`.

Aktualizovaný case JSON súbor s uzlom `caseDelivery`, záverečným záznamom `chainOfCustody` a hodnotou `status: "CLOSED"` — reťazec úschovy je formálne uzavretý.

Fyzické odovzdanie a podpisy: mimo rozsah automatizácie – realizované manuálne analytikom.

## Reference

ISO/IEC 27037:2012 – Uchovávanie digitálnych dôkazov
NIST SP 800-86 – Section 3.4 (Reporting)
ACPO Good Practice Guide – Principle 4 (Documentation)
GDPR čl. 30 – Záznamy o spracovateľských činnostiach

## Stav

Manuálny proces – netestovateľný automaticky

## Nález

(prázdne – vyplní sa po odovzdaní)