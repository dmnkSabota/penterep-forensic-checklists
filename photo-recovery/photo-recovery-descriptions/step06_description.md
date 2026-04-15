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

Forenzný imaging vypočítal `source_hash` priamo z originálneho média počas kopírovania. Verifikácia integrity vypočíta `image_hash` zo súboru forenzného obrazu a oba hashe porovná. Zhoda matematicky dokazuje, že súbor obrazu je bit-for-bit identický s dátami prečítanými z originálneho média – počas kopírovania nedošlo k žiadnej zmene ani chybe.

## Jak na to

**1. Prečítanie source_hash z dokumentácie:**

Z výstupu forenzného imagingu si zapíšte hodnotu `source_hash` (64 hexadecimálnych znakov). Typicky sa nachádza v:
- Terminal output z `dc3dd` alebo `ddrescue`
- Log súbor `{CASE-ID}_imaging.log`
- JSON súbor (ak bol použitý `--json-out`)
- Kanonický hash súbor `{CASE-ID}.dd.sha256`

Príklad:
```
source_hash: a3f5e8c9d2b1a7f4e6c8d9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2
```

**2. Spustenie verifikácie:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
IMAGE="/var/forensics/images/${CASE_ID}.dd"
SOURCE_HASH="a3f5e8c9d2b1a7f4e6c8d9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2"

# Iba terminálový výstup
ptimageverification ${CASE_ID} ${IMAGE} ${SOURCE_HASH} --analyst "Meno Analytika"

# S JSON výstupom
ptimageverification ${CASE_ID} ${IMAGE} ${SOURCE_HASH} \
  --analyst "Meno Analytika" \
  --output ${CASE_ID}_verification.json
```

Nástroj automaticky:
- Overí formát source_hash (64 hex znakov)
- Nájde a validuje forenzný obraz
- Vypočíta SHA-256 hash obrazu (image_hash)
- Porovná oba hashe
- Vygeneruje JSON report
- Vytvorí kanonický hash súbor `.sha256`
- Aktualizuje Chain of Custody

**3. Výpočet image_hash:**

Pre `.dd` a `.raw` súbory nástroj používa `hashlib` s 4 MB chunks:
```python
sha256 = hashlib.sha256()
with open(image_file, 'rb') as f:
    while chunk := f.read(4 * 1024 * 1024):
        sha256.update(chunk)
image_hash = sha256.hexdigest()
```

Pre `.e01` súbory nástroj používa `ewfverify`:
```bash
ewfverify -d sha256 image.e01
```

Progress sa zobrazuje každých 1 GB s aktuálnou rýchlosťou čítania.

**4. Porovnanie hashov:**

Nástroj porovná `source_hash` a `image_hash` znak po znaku:

**MATCH** – všetky 64 znakov sa zhodujú. Obraz je bit-for-bit identický so zdrojovým médiom. Workflow pokračuje do analýzy súborového systému.

**MISMATCH** – hashe sa nezhodujú. Možné príčiny: I/O chyba počas imagingu, korupcia súboru na disku, modifikácia obrazu po vytvorení, degradácia média počas imagingu. Forenzný imaging musí byť zopakovaný, s obrazom sa nesmie ďalej pracovať.

**5. Vytvorenie kanonického hash súboru:**

Nástroj automaticky vytvorí `.sha256` súbor vo formáte kompatibilnom s `sha256sum -c`:
```
{CASE-ID}.dd.sha256
```

Formát: `HASH  FILENAME` (dve medzery medzi hashom a názvom súboru).

Manuálna verifikácia integrity obrazu kedykoľvek neskôr:
```bash
sha256sum -c /var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd.sha256
```

Výstup by mal byť: `PHOTORECOVERY-2025-01-26-001.dd: OK`

**6. JSON output (voliteľné):**

Pri použití `--output` sa vytvorí JSON s forensic metadata:

```json
{
  "hashVerification": {
    "version": "1.0.0",
    "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
    "caseId": "PHOTORECOVERY-2025-01-26-001",
    "timestamp": "2025-01-26T13:00:00Z",
    "analyst": "Meno Analytika",
    "image": {
      "imagePath": "/var/forensics/images/PHOTORECOVERY-2025-01-26-001.dd",
      "imageFormat": ".dd",
      "imageSizeBytes": 32017047552
    },
    "verification": {
      "algorithm": "SHA-256",
      "sourceHash": "a3f5e8c9d2b1a7f4e6c8d9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2",
      "imageHash": "a3f5e8c9d2b1a7f4e6c8d9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2",
      "hashMatch": true,
      "verificationStatus": "VERIFIED",
      "calculationTimeSeconds": 1847.5
    }
  },
  "chainOfCustodyEntry": {
    "action": "Verifikácia integrity obrazu – výsledok: VERIFIED",
    "result": "SUCCESS",
    "analyst": "Meno Analytika",
    "timestamp": "2025-01-26T13:30:00Z"
  }
}
```

Analytik manuálne skopíruje JSON obsah do dokumentácie prípadu.

## Výsledek

SHA-256 `image_hash` vypočítaný a porovnaný so `source_hash`. Pri MATCH workflow pokračuje do analýzy súborového systému. Pri MISMATCH analýza zastavená a forensic imaging sa opakuje. Kanonický hash súbor `.sha256` vytvorený pre budúcu verifikáciu.

## Reference

- NIST SP 800-86 – Section 3.1.2 (Examination Phase – Data Integrity Verification)
- ISO/IEC 27037:2012 – Section 7.2 (Verification of integrity of digital evidence)
- NIST FIPS 180-4 – Secure Hash Standard (SHA-256 algorithm)
- RFC 6234 – US Secure Hash Algorithms

## Stav

Implementované

## Nález

(prázdne – vyplní sa po teste)