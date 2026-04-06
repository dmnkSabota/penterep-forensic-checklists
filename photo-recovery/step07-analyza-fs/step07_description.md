# Detaily testu

## Úkol

Analyzovať forenzný obraz média a určiť typ súborového systému, jeho stav, partície a metadáta.

## Obtiažnosť

Jednoduchá

## Časová náročnosť

10 minút

## Automatický test

Áno

## Popis

Analýza súborového systému je prvý krok forenznej analýzy po vytvorení a overení forenzného obrazu. Výsledok priamo určuje stratégiu obnovy: rozpoznaný súborový systém s čitateľnou adresárovou štruktúrou umožňuje filesystem-based recovery (zachováva pôvodné názvy súborov a metadáta), poškodený alebo nerozpoznaný súborový systém vyžaduje file carving (hľadá súbory podľa signatúr v raw dátach).

Všetky príkazy pracujú výhradne s forenzným obrazom – originálne médium sa v tejto fáze nedotýka.

## Jak na to

**1. Nastavenie premenných:**

```bash
CASE_ID="PHOTORECOVERY-2025-01-26-001"
IMAGE="/forenzne/pripady/${CASE_ID}/${CASE_ID}.dd"
```

**2. Analýza partičnej tabuľky (`mmls`):**

```bash
mmls "${IMAGE}"
```
Zaznamenajte: typ tabuľky (DOS/MBR, GPT), zoznam partícií s ich offsetmi a veľkosťami. Ak `mmls` zlyhá alebo nevráti žiadne partície, predpokladá sa superfloppy formát – celé médium je jeden súborový systém bez partičnej tabuľky (typické pre USB flash disky a SD karty). V takom prípade použite offset `0` v nasledujúcich príkazoch.

**3. Analýza súborového systému (`fsstat`):**

Pre každú partíciu (alebo offset `0` pri superfloppy):
```bash
fsstat -o OFFSET "${IMAGE}"
```
Zaznamenajte: typ súborového systému (FAT32, exFAT, NTFS, ext4…), volume label, UUID, veľkosť sektora a klastra. Ak `fsstat` zlyhá, súborový systém je nerozpoznaný alebo poškodený.

**4. Rekurzívny listing adresárovej štruktúry (`fls`):**

```bash
fls -r -o OFFSET "${IMAGE}"
```
Prefiltrujte na obrazové prípony a spočítajte aktívne a vymazané súbory:
```bash
fls -r -o OFFSET "${IMAGE}" | grep -iE '\.(jpg|jpeg|png|tiff?|bmp|gif|raw|cr2|nef|arw|dng|heic|webp)$'
```
Vymazané súbory sú v liste označené hviezdičkou `*`.

**5. Určenie stratégie obnovy:**

Na základe výsledkov zvoľte stratégiu:
- Rozpoznaný FS + čitateľná adresárová štruktúra → `filesystem_scan` → Krok 8a
- Nerozpoznaný FS (fsstat zlyhalo) → `file_carving` → Krok 8b
- Rozpoznaný FS, ale poškodená štruktúra (fsstat prešlo, fls vrátilo nekonzistentné dáta) → `hybrid` → Krok 8a aj 8b

**6. Zápis výsledkov a aktualizácia CoC:**

Zapíšte výsledky do uzla `filesystemAnalysis` v dokumentácii prípadu:
- Typ partičnej tabuľky – DOS/MBR / GPT / superfloppy
- Partície – zoznam s offsetmi, typom FS, stavom, volume label, UUID, veľkosťou sektora a klastra
- Stav súborového systému – recognized / unrecognized / damaged
- Čitateľnosť adresárovej štruktúry – áno / nie
- Počet aktívnych obrazových súborov
- Počet vymazaných obrazových súborov
- Stratégia obnovy – `filesystem_scan` / `file_carving` / `hybrid`

Pridajte záznam do poľa `chainOfCustody`:
```json
{
  "timestamp": "2025-01-26T13:30:00Z",
  "analyst": "Meno Analytika",
  "action": "Analýza súborového systému – stratégia: filesystem_scan"
}
```

**7. Archivácia výstupov:**

Uložte textový výstup príkazov mmls, fsstat a fls do súboru `${CASE_ID}_filesystem_analysis.txt` a archivujte ho v dokumentácii prípadu.

---

> **Automatizácia (pripravuje sa):** Skript `ptfilesystemanalysis` bude všetky príkazy spúšťať automaticky, zapisovať uzol `filesystemAnalysis` a aktualizovať CoC.

## Výsledek

Typ súborového systému identifikovaný, stav a čitateľnosť adresárovej štruktúry overené. Výsledky zaznamenané v uzle `filesystemAnalysis` vrátane partition table, FS typu, počtu obrazových súborov a zvolenej recovery stratégie. Workflow pokračuje do Kroku 8a, 8b alebo oboch.

## Reference

ISO/IEC 27037:2012 – Section 7 (Analysis of digital evidence)
NIST SP 800-86 – Section 3.1.2 (Examination Phase – Filesystem analysis)
The Sleuth Kit Documentation – mmls, fsstat, fls tools
Brian Carrier: File System Forensic Analysis (2005)

## Stav

K otestovaniu

## Nález

(prázdne – vyplní sa po teste)