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

Predchádzajúci krok vypočítal source_hash priamo z originálneho média počas imaging procesu. Tento krok vypočíta image_hash zo súboru forenzného obrazu a porovná obe hodnoty. Zhoda hashov matematicky dokazuje, že súbor obrazu je bit-for-bit identický s dátami prečítanými z originálneho média.

## Jak na to

**1. Spustenie verifikácie:**

Skript automaticky načíta source_hash z uzla `imagingResult` (Krok 5) a vypočíta SHA-256 hash forenzného obrazu:

```bash
ptimageverification PHOTORECOVERY-2025-01-26-001
```

**2. Vyhodnotenie výsledku:**

Skript automaticky porovná source_hash a image_hash:
- **MATCH** – hashe sa zhodujú vo všetkých 64 znakoch → integrita potvrdená → workflow pokračuje nasledujúcim krokom
- **MISMATCH** – hashe sa nezhodujú → kritická chyba → Krok 5 musí byť zopakovaný, s obrazom sa nesmie ďalej pracovať

**3. Výsledky v uzle hashVerification:**

Skript automaticky zapíše výsledky do uzla `hashVerification` na platforme. Skontrolujte, že uzol obsahuje správne hodnoty:
- Algoritmus – SHA-256
- Zdrojový hash – prevzatý z uzla `imagingResult`
- Hash obrazu – vypočítaný z forenzného obrazu
- Zhoda hashov – MATCH / MISMATCH
- Stav verifikácie – VERIFIED / MISMATCH
- Čas výpočtu (sekundy)

**4. Archivácia výstupov:**

Skript automaticky nahrá nasledujúce súbory do záložky **Přílohy** projektu:
- `PHOTORECOVERY-2025-01-26-001_verification.json` – výsledok verifikácie s oboma hashmi
- `PHOTORECOVERY-2025-01-26-001_image.sha256` – image_hash v štandardnom formáte

## Výsledek

SHA-256 image_hash vypočítaný a porovnaný so source_hash. Výsledok zaznamenaný v uzle `hashVerification`. Pri MATCH workflow pokračuje nasledujúcim krokom. Pri MISMATCH analýza zastavená a Krok 5 sa opakuje.

## Reference

NIST SP 800-86 – Section 3.1.2 (Examination Phase – Data Integrity Verification)
ISO/IEC 27037:2012 – Section 7.2 (Verification of integrity of digital evidence)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 algorithm)
RFC 6234 – US Secure Hash Algorithms

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)