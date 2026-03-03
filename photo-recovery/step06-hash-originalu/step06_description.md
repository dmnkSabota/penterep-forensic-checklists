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

Predchádzajúci krok vypočítal source_hash priamo z originálneho média počas imaging procesu. Tento krok vypočíta image_hash zo súboru forenzného obrazu uloženého na disku a porovná obe hodnoty. Zhoda hashov matematicky dokazuje, že súbor obrazu je bit-for-bit identický s dátami prečítanými z originálneho média.

## Jak na to

**1. Spustenie verifikácie:**

Skript automaticky načíta source_hash zo súboru `PHOTORECOVERY-2025-01-26-001_imaging.json` a vypočíta SHA-256 hash forenzného obrazu:

```bash
ptimageverification PHOTORECOVERY-2025-01-26-001
```

**2. Vyhodnotenie výsledku:**

Skript automaticky porovná source_hash a image_hash:
- **MATCH** – hashe sa zhodujú vo všetkých 64 znakoch → integrita potvrdená → workflow pokračuje nasledujúcim krokom
- **MISMATCH** – hashe sa nezhodujú → kritická chyba → predchádzajúci krok vytvorenia obrazu musí byť zopakovaný, s obrazom sa nesmie ďalej pracovať

**3. Aktualizácia case JSON:**

Otvorte súbor `PHOTORECOVERY-2025-01-26-001.json` a pridajte uzol `hashVerification` a nový záznam `chainOfCustody` do poľa `nodes`:

```json
{
  "type": "hashVerification",
  "properties": {
    "algorithm": "SHA-256",
    "sourceHash": "a3f5...c9d1",
    "imageHash": "a3f5...c9d1",
    "hashMatch": true,
    "imagePath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd",
    "imageSizeBytes": 31914983424,
    "calculationTimeSeconds": 312,
    "verificationStatus": "VERIFIED",
    "completedAt": "2025-01-26T14:15:00Z"
  }
},
{
  "type": "chainOfCustody",
  "properties": {
    "step": "step06-verifikacia-hashu",
    "action": "Hash verification completed – SHA-256 MATCH, image integrity confirmed",
    "analyst": "Dominik Sabota",
    "timestamp": "2025-01-26T14:15:00Z",
    "notes": null
  }
}
```

Pri MISMATCH nastavte `"hashMatch": false`, `"verificationStatus": "MISMATCH"` a zaznamenajte dôvod do `notes` v CoC zázname.

**4. Archivácia výstupov:**

Archivujte do Case dokumentácie:
- `PHOTORECOVERY-2025-01-26-001_verification.json` – výsledok verifikácie s oboma hashmi (generuje skript)
- `PHOTORECOVERY-2025-01-26-001_image.sha256` – image_hash v štandardnom formáte (generuje skript)

## Výsledek

SHA-256 image_hash vypočítaný a porovnaný so source_hash. Aktualizovaný case JSON súbor s uzlom `hashVerification` a ďalším záznamom `chainOfCustody`. Pri MATCH originálne médium môže byť bezpečne odpojené a workflow pokračuje nasledujúcim krokom. Pri MISMATCH analýza zastavená a predchádzajúci krok sa opakuje.

## Reference

NIST SP 800-86 – Section 3.1.2 (Examination Phase – Data Integrity Verification)
ISO/IEC 27037:2012 – Section 7.2 (Verification of integrity of digital evidence)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 algorithm)
RFC 6234 – US Secure Hash Algorithms

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)

