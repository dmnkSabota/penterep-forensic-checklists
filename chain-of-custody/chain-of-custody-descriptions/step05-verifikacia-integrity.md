# Detaily testu

## Úkol

Vypočítať SHA-256 hash forenzného obrazu a porovnať so source_hash pre matematické overenie integrity.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

30–120 minút (závisí od veľkosti obrazu)

## Automatický test

Áno

## Popis

Forenzný imaging vypočítal `source_hash` priamo z originálneho média počas kopírovania. Verifikácia integrity vypočíta `image_hash` zo súboru forenzného obrazu na disku a oba hashe porovná. Zhoda matematicky dokazuje, že obraz je bit-for-bit identický s dátami prečítanými z originálneho média. Pri nezhode je imaging opakovaný s diagnostikou príčiny – maximálne trikrát; po prekročení limitu je prípad eskalovaný.

## Jak na to

**1. Spustenie verifikácie:**

```bash
CASE_ID="COC-2025-01-26-001"
IMAGE="/var/forensics/images/${CASE_ID}.dd"
SOURCE_HASH="a3f5e8c9..."   # z imaging_result.json

# Iba terminálový výstup
ptimageverification ${CASE_ID} ${IMAGE} ${SOURCE_HASH} --analyst "Meno Analytika"

# S JSON výstupom
ptimageverification ${CASE_ID} ${IMAGE} ${SOURCE_HASH} \
  --analyst "Meno Analytika" \
  --output ${CASE_ID}_verification.json
```

Nástroj overí formát `source_hash`, vypočíta `image_hash` v 4 MB blokoch s priebežným zobrazovaním postupu a porovná obe hodnoty.

**2. Výsledok MATCH:**

Všetky 64 znakov hashov sa zhodujú. Obraz je bit-for-bit identický so zdrojovým médiom. Originálne médium možno bezpečne odpojiť od write-blockera. Workflow pokračuje do dokumentácie a fyzického zabezpečenia dôkazu.

**3. Výsledok MISMATCH:**

Hashe sa nezhodujú. Vykonajte diagnostiku pred opakovaním imagingu:
- Skontrolujte fyzický stav káblov a write-blockera (LED indikátor)
- Skontrolujte I/O chyby: `dmesg | grep -i error | tail -50`
- Overte dostupné miesto: `df -h /var/forensics/images`
- Skontrolujte veľkosť obrazu: `ls -lh ${CASE_ID}.dd`
- Odstráňte neplatný obraz: `shred -u ${CASE_ID}.dd`

Zaznamenajte zistenú príčinu do dokumentácie a opakujte forenzný imaging (predchádzajúci krok). Po treťom neúspešnom pokuse nastavte stav prípadu na `CRITICAL_HASH_MISMATCH` a eskalujte nadriadenému.

## Výsledok

MATCH: `image_hash` zhodný s `source_hash`, obraz verifikovaný. Kanonický hash súbor `.sha256` vytvorený. Záznam `chainOfCustody` zapísaný. Originálne médium odpojené od write-blockera. Workflow pokračuje do dokumentácie a fyzického zabezpečenia dôkazu.
MISMATCH: Diagnostika vykonaná, forenzný imaging sa opakuje. Pri treťom zlyhaní prípad eskalovaný so stavom `CRITICAL_HASH_MISMATCH`.

## Reference

NIST SP 800-86 – Section 3.1.2 (Examination Phase – Data Integrity Verification)
ISO/IEC 27037:2012 – Section 7.2 (Verification of integrity of digital evidence)
NIST FIPS 180-4 – Secure Hash Standard (SHA-256 algorithm)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)