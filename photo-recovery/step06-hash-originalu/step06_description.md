# Detaily testu

## Úkol

Vypočítať SHA-256 hash vytvoreného forenzného obrazu a porovnať so source_hash.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

45 minút

## Automatický test

Áno

## Popis

Krok 5 vypočítal `source_hash` priamo z originálneho média počas imaging procesu. Tento krok vypočíta `image_hash` zo súboru forenzného obrazu a oba hashe porovná. Zhoda matematicky dokazuje, že súbor obrazu je bit-for-bit identický s dátami prečítanými z originálneho média – počas kopírovania nedošlo k žiadnej zmene ani chybe.

## Jak na to

**1. Prečítanie source_hash z dokumentácie:**

Z uzla `imagingResult` (Krok 5) si zapíšte hodnotu `source_hash` (64 hexadecimálnych znakov).

**2. Výpočet image_hash:**

Vypočítajte SHA-256 hash súboru forenzného obrazu:
```bash
sha256sum /forenzne/pripady/PHOTORECOVERY-2025-01-26-001/PHOTORECOVERY-2025-01-26-001.dd
```
Zaznamenajte výsledok (64 hexadecimálnych znakov) ako `image_hash`.

Alternatívne, ak existuje kanonický hash súbor z Kroku 5:
```bash
sha256sum -c /forenzne/pripady/PHOTORECOVERY-2025-01-26-001/PHOTORECOVERY-2025-01-26-001.dd.sha256
```
Výsledok musí byť `OK`.

**3. Porovnanie hashov:**

Porovnajte `source_hash` a `image_hash` znak po znaku:
- **MATCH** – všetky 64 znakov sa zhodujú → integrita potvrdená → workflow pokračuje
- **MISMATCH** – hashe sa nezhodujú → kritická chyba → Krok 5 musí byť zopakovaný. S obrazom sa nesmie ďalej pracovať.

**4. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do uzla `hashVerification` v dokumentácii prípadu:
- Algoritmus – SHA-256
- Zdrojový hash – prevzatý z uzla `imagingResult`
- Hash obrazu – vypočítaný z forenzného obrazu
- Zhoda hashov – MATCH / MISMATCH
- Stav verifikácie – VERIFIED / MISMATCH
- Čas výpočtu (sekundy)

Pridajte záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T13:00:00Z",
  "analyst": "Meno Analytika",
  "action": "Verifikácia integrity obrazu – výsledok: VERIFIED"
}
```

**5. Archivácia výstupov:**

Archivujte do dokumentácie prípadu:
- `PHOTORECOVERY-2025-01-26-001_verification.json` – JSON s oboma hashmi a výsledkom
- `PHOTORECOVERY-2025-01-26-001_image.sha256` – image_hash v štandardnom formáte

---

> **Automatizácia (pripravuje sa):** Skript `ptimageverification` bude hash vypočítavať, porovnávať, zapisovať uzol `hashVerification` a aktualizovať CoC automaticky.

## Výsledek

SHA-256 `image_hash` vypočítaný a porovnaný so `source_hash`. Výsledok zaznamenaný v uzle `hashVerification`. Pri MATCH workflow pokračuje nasledujúcim krokom. Pri MISMATCH analýza zastavená a Krok 5 sa opakuje.

## Reference

NIST SP 800-86 – Section 3.1.2 (Examination Phase – Data Integrity Verification)
ISO/IEC 27037:2012 – Section 7.2 (Verification of integrity of digital evidence)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 algorithm)
RFC 6234 – US Secure Hash Algorithms

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)