# Detaily testu

## Úkol
Prijať žiadosť o obnovu fotografií a vytvoriť Case ID.

## Obtiažnosť
Jednoduchá

## Časová náročnosť
15 minút

## Automatický test
Nie

## Popis
Prvý krok procesu obnovy fotografií začína formálnym prijatím žiadosti od klienta. Analytik manuálne zozbiera všetky potrebné informácie, vytvorí unikátny identifikátor prípadu (Case ID) a inicializuje Chain of Custody log. Postup vychádza z ISO/IEC 27037:2012, ktorý zostáva platným medzinárodným štandardom pre zaobchádzanie s digitálnymi dôkazmi. Case ID slúži ako primárny kľúč, pod ktorým sú ukladané výsledky všetkých následných technických krokov vrátane forenzného obrazu média a výsledkov obnovy súborov.

## Jak na to

**1. Vytvorenie Case ID:**
Vytvorte Case ID podľa formátu `PHOTORECOVERY-YYYY-MM-DD-XXX` a vyplňte ho do formulára scenára:
- `PHOTORECOVERY` – fixný prefix identifikujúci typ scenára
- `YYYY-MM-DD` – aktuálny dátum (rok-mesiac-deň), napr. `2025-01-26`
- `XXX` – trojciferné poradové číslo prípadu v daný deň, začína od `001`

Príklad prvého prípadu dňa 26. januára 2025: `PHOTORECOVERY-2025-01-26-001`

Skontrolujte archív existujúcich prípadov a overte, že toto ID ešte nebolo použité.

**2. Údaje klienta:**
Zaznamenajte kontaktné údaje klienta do formulára scenára:
- Meno alebo názov firmy
- Email
- Telefónne číslo
- Fakturačná adresa (ak je dostupná)

**3. Urgentnosť a SLA:**
Dohodnite s klientom urgentnosť prípadu a zaznamenajte zvolenú možnosť:
- Štandardná (5–7 pracovných dní)
- Vysoká (2–3 pracovné dni)
- Kritická (do 24 hodín)

**4. GDPR súlad:**
Zvoľte právny základ spracovania osobných údajov podľa čl. 6 nariadenia EÚ 2016/679 a zaznamenajte ho:
- Pre komerčnú obnovu: čl. 6 ods. 1 písm. b) – plnenie zmluvy
- Pre súdne prípady: čl. 6 ods. 1 písm. c) – právna povinnosť

**5. Príjmový protokol:**
Manuálne vyplňte príjmový protokol. Protokol musí obsahovať minimálne tieto polia:
- Case ID a dátum prijatia
- Meno a kontaktné údaje klienta
- Popis a fyzický stav odovzdaného média
- Podpis klienta a analytika

Vytlačte ho, nechajte klienta podpísať a naskenovanú verziu archivujte do fyzickej aj digitálnej dokumentácie prípadu. Fyzickú kópiu uložte na príslušné miesto.

**6. Inicializácia záznamu prípadu:**
Vytvorte JSON záznam prípadu a uložte ho pod príslušným Case ID. Záznam musí obsahovať stav `INITIATED`, kontaktné údaje klienta, zvolenú urgentnosť, zaznamenaný právny základ a prvý zápis do poľa `chainOfCustody`.
 
Príklad záznamu:
```json
{
  "caseId": "PHOTORECOVERY-2025-01-26-001",
  "status": "INITIATED",
  "client": {
    "name": "Meno Klienta",
    "email": "klient@example.com",
    "phone": "+421 900 000 000",
    "address": "Ulica 1, 000 00 Mesto"
  },
  "urgency": "standard",
  "gdprBasis": "Art. 6(1)(b) - performance of contract",
  "chainOfCustody": [
    {
      "timestamp": "2025-01-26T09:00:00Z",
      "analyst": "Meno Analytika",
      "action": "Prijatá žiadosť o obnovu fotografií"
    }
  ]
}
```
 
**7. Finalizácia:**
Skontrolujte, že záznam prípadu obsahuje všetky povinné polia: `caseId`, `status`, `client`, prvý záznam v poli `chainOfCustody`. Potvrdzovací email s číslom prípadu a ďalšími krokmi odošlite klientovi manuálne.
 
## Výsledek
Po dokončení kroku existujú tieto výstupy:
- Vyplnený záznam prípadu so stavom `INITIATED` a prvým `chainOfCustody` záznamom
- Vyplnený a podpísaný príjmový protokol (fyzická kópia + naskenovaná digitálna kópia)
- Odoslaný potvrdzovací email klientovi

## Reference
 
ISO/IEC 27037:2012 – Section 5 (Guidelines for identification)
 
GDPR (Nariadenie EÚ 2016/679) – Článok 6 (Právny základ spracovania)
 
NIST SP 800-86 – Section 2.1 (Collection)
 
## Stav
K otestovaniu
 
## Nález
(prázdne – vyplní sa po teste)