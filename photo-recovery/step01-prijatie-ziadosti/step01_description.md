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

Prvý krok procesu obnovy fotografií začína formálnym prijatím žiadosti od klienta. Analytik manuálne zozbiera všetky potrebné informácie, vytvorí unikátny identifikátor prípadu (Case ID), inicializuje Chain of Custody log a vytvorí centrálny case JSON súbor. Tento súbor slúži ako vstup pre všetky nasledujúce kroky – každý ďalší krok do neho pridáva svoje výsledky. Proces prebieha v súlade s ISO/IEC 27037:2012.

## Jak na to

**1. Vytvorenie Case ID:**

Vytvorte Case ID podľa formátu `PHOTORECOVERY-YYYY-MM-DD-XXX`, kde `YYYY-MM-DD` je aktuálny dátum a `XXX` je poradové číslo prípadu v daný deň. Napríklad prvý prípad dňa 26. januára 2025 dostane ID `PHOTORECOVERY-2025-01-26-001`. Overte, že prípad s týmto ID ešte neexistuje v archíve.

**2. Údaje klienta:**

Zaznamenajte kontaktné údaje klienta:
- Meno alebo názov firmy
- Email
- Telefónne číslo
- Fakturačná adresa (ak je dostupná)

**3. Informácie o médiu:**

Zaznamenajte základné informácie podľa toho, čo klient uvádza:
- Typ zariadenia: SD karta / microSD / USB flash disk / HDD / SSD / iné
- Odhadovaná kapacita
- Popis prípadného viditeľného poškodenia

Tieto údaje budú overené fyzicky v nasledujúcom kroku.

**4. Urgentnosť a SLA:**

Dohodnite s klientom urgentnosť prípadu:
- Štandardná (5–7 pracovných dní)
- Vysoká (2–3 pracovné dni)
- Kritická (do 24 hodín)

**5. GDPR súlad:**

Zvoľte právny základ spracovania osobných údajov:
- Pre komerčnú obnovu: "plnenie zmluvy"
- Pre súdne prípady: "právna povinnosť"

**6. Príjmový protokol:**

Manuálne vyplňte príjmový protokol (použite pripravený formulár alebo šablónu). Vytlačte ho, nechajte klienta podpísať a naskenovanú verziu archivujte do fyzickej a digitálnej dokumentácie prípadu.

**7. Vytvorenie centrálneho case JSON súboru:**

Manuálne vytvorte súbor `PHOTORECOVERY-2025-01-26-001.json` s nasledujúcou štruktúrou. Tento súbor bude každý ďalší krok načítať a dopĺňať o svoje výsledky:

```json
{
  "result": {
    "properties": {
      "caseId": "PHOTORECOVERY-2025-01-26-001",
      "status": "INITIATED",
      "createdAt": "2025-01-26T10:30:00Z",
      "analyst": "Dominik Sabota",
      "urgency": "standard",
      "gdprBasis": "plnenie zmluvy",
      "deviceType": "SD karta"
    },
    "nodes": [
      {
        "type": "caseInit",
        "properties": {
          "client": {
            "name": "Jan Novak",
            "email": "jan.novak@email.com",
            "phone": "+421 900 000 000",
            "address": null
          },
          "device": {
            "type": "SD karta",
            "estimatedCapacity": "32GB",
            "visibleDamage": "žiadne"
          },
          "urgency": "standard",
          "slaDays": "5-7",
          "gdprBasis": "plnenie zmluvy",
          "protocolSigned": false,
          "completedAt": "2025-01-26T10:30:00Z"
        }
      },
      {
        "type": "chainOfCustody",
        "properties": {
          "step": "step01-prijatie-ziadosti",
          "action": "Case initiated – client request accepted",
          "analyst": "Dominik Sabota",
          "timestamp": "2025-01-26T10:30:00Z",
          "notes": null
        }
      }
    ]
  }
}
```

**8. Finalizácia:**

Skontrolujte, že case JSON súbor obsahuje správne vyplnené všetky povinné polia. Po fyzickom podpise príjmového protokolu klientom aktualizujte pole `protocolSigned` na `true`. Potvrdzovací email s číslom prípadu a ďalšími krokmi odošlite klientovi manuálne.

## Výsledek

Po dokončení kroku existujú tieto výstupy:
- Centrálny case JSON súbor (`PHOTORECOVERY-2025-01-26-001.json`) so stavom `INITIATED`, `caseInit` nodom a prvým `chainOfCustody` záznamom
- Vyplnený a podpísaný príjmový protokol (fyzická kópia + naskenovaná digitálna kópia)
- Odoslaný potvrdzovací email klientovi

## Reference

ISO/IEC 27037:2012 – Section 5 (Guidelines for identification)
GDPR (Nariadenie EÚ 2016/679) – Článok 6 (Právny základ spracovania)
NIST SP 800-86 – Section 3.1.1 (Collection Phase)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)
