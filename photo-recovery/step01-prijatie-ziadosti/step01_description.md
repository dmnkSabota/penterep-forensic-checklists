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

Prvý krok procesu obnovy fotografií začína formálnym prijatím žiadosti od klienta. Analytik manuálne zozbiera všetky potrebné informácie, vytvorí unikátny identifikátor prípadu (Case ID) a inicializuje Chain of Custody log. Proces prebieha v súlade s ISO/IEC 27037:2012.

## Jak na to

**1. Vytvorenie Case ID:**

Vytvorte Case ID podľa formátu `PHOTORECOVERY-YYYY-MM-DD-XXX` a vyplňte ho do formulára scenára:
- `PHOTORECOVERY` – fixný prefix identifikujúci typ scenára
- `YYYY-MM-DD` – aktuálny dátum (rok-mesiac-deň), napr. `2025-01-26`
- `XXX` – trojciferné poradové číslo prípadu v daný deň, začína od `001`

Príklad prvého prípadu dňa 26. januára 2025: `PHOTORECOVERY-2025-01-26-001`

Overte, že prípad s týmto ID ešte neexistuje v archíve.

**2. Údaje klienta:**

Zaznamenajte kontaktné údaje klienta do formulára scenára:
- Meno alebo názov firmy
- Email
- Telefónne číslo
- Fakturačná adresa (ak je dostupná)

**3. Urgentnosť a SLA:**

Dohodnite s klientom urgentnosť prípadu a vyberte príslušnú možnosť vo formulári:
- Štandardná (5–7 pracovných dní)
- Vysoká (2–3 pracovné dni)
- Kritická (do 24 hodín)

**4. GDPR súlad:**

Zvoľte právny základ spracovania osobných údajov vo formulári:
- Pre komerčnú obnovu: "plnenie zmluvy"
- Pre súdne prípady: "právna povinnosť"

**5. Príjmový protokol:**

Manuálne vyplňte príjmový protokol (použite pripravený formulár alebo šablónu). Vytlačte ho, nechajte klienta podpísať a naskenovanú verziu archivujte do fyzickej a digitálnej dokumentácie prípadu. Po podpise aktivujte prepínač **Príjmový protokol podpísaný** vo formulári.

**6. Finalizácia:**

Skontrolujte, že formulár scenára obsahuje správne vyplnené všetky povinné polia. Potvrdzovací email s číslom prípadu a ďalšími krokmi odošlite klientovi manuálne.


## Výsledek

Po dokončení kroku existujú tieto výstupy:
- Vyplnený uzol prijatia žiadosti so stavom `INITIATED` a prvým `chainOfCustody` záznamom
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