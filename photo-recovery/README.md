<div align="center">
  <img src="PHOTORECOVERY_SCENARIO_DIAGRAM.svg" alt="Photo Recovery Process" width="800">
</div>

# Photo Recovery – Prehľad parametrov (Kroky 1–15)

---

## Krok 1 – Prijatie žiadosti
*Manuálny krok. Analytik vypĺňa formulár scenára na Penterep.*

### Case Identification
| Pole | Popis | Povinné |
|---|---|---|
| Case ID | Manuálne vytvorené ID vo formáte `PHOTORECOVERY-YYYY-MM-DD-XXX` | áno |
| Vytvorené | Dátum a čas vytvorenia prípadu | áno |
| Analytik | Meno analytika | áno |

### Client Data
| Pole | Popis | Povinné |
|---|---|---|
| Meno / názov firmy | Meno klienta alebo názov firmy | áno |
| Email | Emailová adresa | áno |
| Telefón | Telefónne číslo | áno |
| Fakturačná adresa | | nie |

### Urgency & SLA
| Pole | Popis | Povinné | Hodnoty |
|---|---|---|---|
| Urgentnosť | Dohodnutá urgentnosť | áno | standard / high / critical |
| SLA (dni) | Počet pracovných dní | áno | 5-7 / 2-3 / <1 |

### GDPR
| Pole | Popis | Povinné | Hodnoty |
|---|---|---|---|
| Právny základ | Právny základ spracovania osobných údajov | áno | plnenie zmluvy / právna povinnosť |

### Protocol
| Pole | Popis | Povinné |
|---|---|---|
| Príjmový protokol podpísaný | Potvrdenie fyzického podpisu príjmového protokolu | áno |

---

## Krok 2 – Identifikácia média
*Manuálny krok. Analytik vypĺňa formulár scenára na Penterep + fyzická práca s médiom.*

### Client-reported Device Info
| Pole | Popis | Povinné | Hodnoty |
|---|---|---|---|
| Typ zariadenia | Typ zariadenia podľa klienta | áno | SD karta / microSD / USB flash disk / HDD / SSD / iné |
| Odhadovaná kapacita | Podľa klienta | áno | napr. 32GB |
| Viditeľné poškodenie | Popis poškodenia podľa klienta | nie | popis alebo žiadne |

### Photo Documentation
| Pole | Popis | Povinné |
|---|---|---|
| Počet fotografií | Min. 8 | áno |
| Fotografie archivované | Potvrdenie archivácie fotografií v Přílohy | áno |

### Physical Identifiers
| Pole | Popis | Povinné |
|---|---|---|
| Výrobca | | áno |
| Model | | áno |
| Sériové číslo | Úplné sériové číslo | áno |
| Farba / materiál | | áno |
| Dĺžka (mm) | | áno |
| Šírka (mm) | | áno |
| Výška (mm) | | áno |
| Kapacita (nálepka) | Z fyzickej nálepky zariadenia | áno |

### Physical Condition
| Pole | Popis | Povinné | Hodnoty |
|---|---|---|---|
| Stav zariadenia | Celkový fyzický stav | áno | nové / mierne použité / intenzívne použité / poškodené |
| Poznámka k stavu | Škrabance, znečistenie, stav nálepiek | nie | voľný text |

### Physical Damage *(podmienečné)*
| Pole | Popis | Povinné | Hodnoty |
|---|---|---|---|
| Poškodenie prítomné | | áno | toggle |
| Typ poškodenia | | podmienečne | prasklina púzdra / zlomený konektor / deformácia / korózia kontaktov |
| Lokalizácia poškodenia | | podmienečne | voľný text |
| Závažnosť poškodenia | | podmienečne | malé / stredné / kritické |

### Encryption & Labeling
| Pole | Popis | Povinné |
|---|---|---|
| Indikátor šifrovania viditeľný | BitLocker, VeraCrypt, firemný štítok | áno |
| Štítok nalepený | Potvrdenie nalepenia štítku s Case ID | áno |

### Přílohy – manuálne nahratie
| Príloha | Popis | Povinné |
|---|---|---|
| Fotodokumentácia média | Min. 8 fotografií (6 strán, mierka, sériové číslo, poškodenie) | áno |

### Otvorená otázka – na prejednanie
- Pomenovanie polí: Kroky 1–2 používajú technické camelCase názvy (`caseId`, `client.name`, `damagePresent`...). Kroky 4–6 používajú plain labels (Typ opravy, Nástroj, Zdrojový hash...). Treba zjednotiť — buď všetko camelCase, alebo všetko plain labels podľa toho, čo Penterep skutočne zobrazuje v UI.

---

## Krok 3 – Test čitateľnosti média
*Poloautomatický krok. Vyžaduje fyzické potvrdenie write-blockera pred spustením. Skript beží na uzle zariadenia z Kroku 2 a zapisuje výsledky do uzla `readabilityTest`. Žiadne formuláre.*

### readabilityTest – výstup skriptu
| Parameter | Popis | Hodnoty |
|---|---|---|
| `devicePath` | Cesta k zariadeniu | napr. `/dev/sdX` |
| `mediaStatus` | Výsledná klasifikácia média | `READABLE` / `PARTIAL` / `UNREADABLE` |
| `detectionResults.lsblk` | Detekcia zariadenia | `detected` / `not detected` |
| `detectionResults.blkid` | Typ súborového systému | FAT32 / exFAT / NTFS / ext4 / iné / prázdny |
| `detectionResults.smartctl` | SMART stav | `ok` / kritické atribúty / `not supported` |
| `detectionResults.hdparm` | TRIM podpora (SSD) | `TRIM supported` / `TRIM not supported` / `not applicable` |
| `detectionResults.mdadm` | RAID konfigurácia | konfigurácia / `not applicable` |
| `diagnosticTests.firstSector` | Čítanie prvého sektora (512 B) | `pass` / `fail` |
| `diagnosticTests.sequential1MB` | Sekvenčné čítanie 1 MB | `pass` / `fail` |
| `diagnosticTests.positionStart` | Čítanie – začiatok média | `pass` / `fail` |
| `diagnosticTests.positionMiddle` | Čítanie – stred média | `pass` / `fail` |
| `diagnosticTests.positionEnd` | Čítanie – koniec média | `pass` / `fail` |
| `diagnosticTests.readSpeed` | Rýchlosť čítania 10 MB | napr. `18.4 MB/s` (< 5 MB/s = riziko) |
| `criticalFindings` | Zoznam kritických nálezov | TRIM / SMART / šifrovanie / RAID / prázdny |
| `selectedTool` | Nástroj pre imaging | `dc3dd` / `ddrescue` / `null` |

---

## Krok 4 – Fyzická oprava média
*Manuálny krok. Aktivuje sa iba ak Krok 3 vrátil `UNREADABLE`. Po oprave sa Krok 3 spúšťa znova na rovnakom uzle zariadenia. Ak oprava neuspeje, workflow sa zastavuje. Ak krok 3 vrátil `READABLE` alebo `PARTIAL`, tento krok sa preskakuje úplne.*

### Poduzol fyzickej opravy – formulár
| Pole | Popis | Povinné | Hodnoty |
|---|---|---|---|
| Typ opravy | Klasifikácia vykonaného zásahu | áno | jednoduchá / stredná / komplexná |
| Popis opravy | Čo konkrétne bolo vykonané | áno | voľný text |
| Súhlas podpísaný | Potvrdenie podpisu a archivácie súhlasu | áno | toggle |
| Použité nástroje | Zoznam nástrojov | áno | voľný text |
| Počet fotografií pred opravou | Min. 3 | áno | číslo |
| Počet fotografií po oprave | Min. 3 | áno | číslo |
| Fotografie archivované | Potvrdenie nahrania do Přílohy | áno | toggle |
| Technik | Meno technika | áno | |

> Výsledok overenia opravy zapisuje automaticky Krok 3 pri opätovnom spustení.

### Přílohy – manuálne nahratie
| Príloha | Popis | Povinné |
|---|---|---|
| Súhlasný formulár | Naskenovaný podpísaný súhlas klienta | áno |
| Fotografie pred opravou | Min. 3 (celok, detail, pracovisko) | áno |
| Fotografie po oprave | Min. 3 v rovnakých záberoch | áno |

---

## Krok 5 – Vytvorenie forenzného obrazu
*Poloautomatický krok. Vyžaduje fyzické potvrdenie write-blockera pred spustením. Skript číta `devicePath` a `selectedTool` z uzla `readabilityTest` (Krok 3) a zapisuje výsledky do uzla `imagingResult`. Žiadne formuláre.*

### imagingResult – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Nástroj | Použitý imaging nástroj | `dc3dd` / `ddrescue` |
| Stav média | Prevzaté z Kroku 3 | `READABLE` / `PARTIAL` |
| Cesta k obrazu | Absolútna cesta k `.dd` súboru na forenznom úložisku | |
| Formát obrazu | | `raw (.dd)` |
| Veľkosť zdroja | Veľkosť zdrojového média v bajtoch | |
| Zdrojový hash | SHA-256, 64 hexadecimálnych znakov | |
| Trvanie | Čas imagingu v sekundách | |
| Priemerná rýchlosť | MB/s | |
| Počet chybných sektorov | 0 pre dc3dd, nenulové pre ddrescue | |
| Cesta k mapfile | Len pre ddrescue | |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Imaging log | `PHOTORECOVERY-YYYY-MM-DD-XXX_imaging.log` | áno |
| Hash súbor | `PHOTORECOVERY-YYYY-MM-DD-XXX.dd.sha256` | áno |
| Mapfile | `PHOTORECOVERY-YYYY-MM-DD-XXX.mapfile` – len pre ddrescue | podmienečne |

### Otvorená otázka – na prejednanie
- Kde sa ukladá samotný forenzný obraz `.dd`? Cez Přílohy na Penterep, alebo na externé forenzné úložisko mimo platformy? Toto ovplyvňuje pole „Cesta k obrazu" v uzle `imagingResult` a čo skript po dokončení imagingu robí s výstupným súborom.

---

## Krok 6 – Verifikácia hash hodnoty
*Automatický krok. Skript číta source_hash z uzla `imagingResult` (Krok 5), vypočíta image_hash a zapisuje výsledok do uzla `hashVerification`. Pri MISMATCH sa Krok 5 opakuje. Žiadne formuláre.*

### hashVerification – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Algoritmus | | SHA-256 |
| Zdrojový hash | Prevzatý z uzla `imagingResult` | 64 hex znakov |
| Hash obrazu | Vypočítaný z forenzného obrazu | 64 hex znakov |
| Zhoda hashov | | MATCH / MISMATCH |
| Stav verifikácie | | VERIFIED / MISMATCH |
| Čas výpočtu | V sekundách | |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Verification JSON | `PHOTORECOVERY-YYYY-MM-DD-XXX_verification.json` | áno |
| Image hash súbor | `PHOTORECOVERY-YYYY-MM-DD-XXX_image.sha256` | áno |

---

## Krok 7 – Analýza súborového systému
*Automatický krok. Skript číta cestu k obrazu z uzla `hashVerification` (Krok 6) a zapisuje výsledky do uzla `filesystemAnalysis`. Žiadne formuláre.*

### filesystemAnalysis – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Typ partičnej tabuľky | | DOS/MBR / GPT / superfloppy |
| Partície | Zoznam – offset, typ FS, stav, volume label, UUID, sektor, klaster | |
| Stav súborového systému | | recognized / unrecognized / damaged |
| Čitateľnosť adresárovej štruktúry | | áno / nie |
| Počet aktívnych obrazových súborov | | |
| Počet vymazaných obrazových súborov | | |
| Stratégia obnovy | Určuje postup v Kroku 8 | `filesystem_scan` / `file_carving` / `hybrid` |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Filesystem analysis JSON | `PHOTORECOVERY-YYYY-MM-DD-XXX_filesystem_analysis.json` | áno |

---

## Krok 8a – Filesystem Recovery
*Automatický krok. Aktivuje sa ak Krok 7 vrátil `filesystem_scan` alebo `hybrid`. Skript číta stratégiu z uzla `filesystemAnalysis` (Krok 7) a zapisuje výsledky do uzla `filesystemRecovery`. Žiadne formuláre.*

### filesystemRecovery – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Metóda obnovy | Prevzatá z Kroku 7 | `filesystem_scan` / `hybrid` |
| Počet prehľadaných súborov | | |
| Počet obnovených aktívnych súborov | | |
| Počet obnovených vymazaných súborov | | |
| Počet poškodených súborov | | |
| Úspešnosť obnovy aktívnych (%) | | |
| Úspešnosť obnovy vymazaných (%) | | |
| Extrakcia metadát | | áno / nie |
| Nutnosť File Carving | Len pri `hybrid` | áno / nie |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Recovery report | `PHOTORECOVERY-YYYY-MM-DD-XXX_recovery_report.json` | áno |

---

## Krok 8b – File Carving
*Automatický krok. Aktivuje sa ak Krok 7 vrátil `file_carving` alebo `hybrid`. Pri `filesystem_scan` odmietne pokračovať. Skript číta stratégiu z uzla `filesystemAnalysis` (Krok 7) a zapisuje výsledky do uzla `fileCarvingRecovery`. Žiadne formuláre.*

### fileCarvingRecovery – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Metóda obnovy | Prevzatá z Kroku 7 | `file_carving` / `hybrid` |
| Celkový počet carved súborov | | |
| Počet validných obrazových súborov | | |
| Počet poškodených súborov | | |
| Počet duplikátov | | |
| Počet súborov v karanténe | | |
| Miera validácie (%) | Typicky 50–65 % | |
| Miera duplikácie (%) | Typicky 20–30 % | |
| Extrakcia metadát | | áno / nie |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Carving report JSON | `PHOTORECOVERY-YYYY-MM-DD-XXX_carving_report.json` | áno |
| Carving report TXT | `CARVING_REPORT.txt` | áno |

---

## Krok 9 – Recovery Consolidation
*Automatický krok. Vždy sa vykonáva po Krokoch 8a/8b. Skript číta výstupy z uzlov `filesystemRecovery` a/alebo `fileCarvingRecovery` a zapisuje výsledky do uzla `recoveryConsolidation`. Žiadne formuláre.*

### recoveryConsolidation – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Počet súborov z filesystem recovery | Z Kroku 8a | |
| Počet súborov z file carving | Z Kroku 8b | |
| Počet odstránených duplikátov | SHA-256 deduplikácia naprieč zdrojmi | typicky 15–25 % pri hybrid |
| Počet finálnych unikátnych súborov | | |
| Celková veľkosť datasetu | V bajtoch | |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Master katalóg | `master_catalog.json` | áno |
| Consolidation report | `CONSOLIDATION_REPORT.txt` | áno |

---

## Krok 10 – Integrity Validation
*Automatický krok. Skript číta master katalóg z uzla `recoveryConsolidation` (Krok 9) a zapisuje výsledky do uzla `integrityValidation`. Žiadne formuláre.*

### integrityValidation – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Celkový počet validovaných súborov | Z master katalógu Kroku 9 | |
| Počet validných súborov | | |
| Počet poškodených súborov | Potenciálne opraviteľné | |
| Počet neopraviteľných súborov | | |
| Integrity score | % validných súborov | |
| Použité nástroje | | PIL / jpeginfo / pngcheck |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Validation report JSON | `PHOTORECOVERY-YYYY-MM-DD-XXX_validation_report.json` | áno |
| Validation report TXT | `PHOTORECOVERY-YYYY-MM-DD-XXX_VALIDATION_REPORT.txt` | áno |

---

## Krok 11 – Repair Decision
*Automatický krok. Skript číta výsledky z uzla `integrityValidation` (Krok 10) a zapisuje rozhodnutie do uzla `repairDecision`. Žiadne formuláre. Pri `skip_repair` sa Krok 12 preskakuje úplne.*

### repairDecision – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Stratégia | Výsledok rozhodovacej logiky | `perform_repair` / `skip_repair` |
| Úroveň istoty | | `high` / `medium` / `low` |
| Odôvodnenie | Pravidlo R1–R5 ktoré rozhodlo | voľný text |
| Počet opraviteľných súborov | | |
| Odhadovaná úspešnosť opravy (%) | Priemer podľa typu poškodenia | |
| Očakávaný počet dodatočných súborov | | |
| Finálny očakávaný počet validných súborov | | |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Repair decision JSON | `PHOTORECOVERY-YYYY-MM-DD-XXX_repair_decision.json` | áno |

---

## Krok 12 – Photo Repair
*Automatický krok. Aktivuje sa iba ak Krok 11 vrátil `perform_repair`. Skript číta z uzlov `repairDecision` (Krok 11) a `integrityValidation` (Krok 10), zapisuje výsledky do uzla `photoRepair`. Žiadne formuláre.*

### photoRepair – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Celkový počet pokusov o opravu | | |
| Počet úspešných opráv | | |
| Počet neúspešných opráv | | |
| Úspešnosť opravy (%) | | |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Repair report JSON | `PHOTORECOVERY-YYYY-MM-DD-XXX_repair_report.json` | áno |
| Repair report TXT | `PHOTORECOVERY-YYYY-MM-DD-XXX_REPAIR_REPORT.txt` | áno |

---

## Krok 13 – EXIF analýza
*Automatický krok. Skript číta z uzla `integrityValidation` (Krok 10) a voliteľne z uzla `photoRepair` (Krok 12) — ak `skip_repair`, pokračuje len s validnými súbormi. Zapisuje výsledky do uzla `exifAnalysis`. Žiadne formuláre.*

### exifAnalysis – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Celkový počet spracovaných súborov | Validné + opravené | |
| Počet EXIF-pozitívnych súborov | | |
| Počet súborov s DateTimeOriginal | | |
| Počet súborov s GPS | | |
| Počet unikátnych zariadení | Podľa Make + Model | |
| Počet upravených fotografií | Software tag zhodný so zoznamom editorov | |
| Počet detekovaných anomálií | Budúci dátum / ISO >25600 / potiché úpravy | |
| EXIF quality score | | excellent / good / fair / poor |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| EXIF databáza JSON | `PHOTORECOVERY-YYYY-MM-DD-XXX_exif_database.json` | áno |
| EXIF CSV export | `PHOTORECOVERY-YYYY-MM-DD-XXX_exif_data.csv` | áno |
| EXIF report TXT | `PHOTORECOVERY-YYYY-MM-DD-XXX_EXIF_REPORT.txt` | áno |

---

## Krok 14 – Záverečná správa
*Automatický krok. Skript číta z uzlov `integrityValidation` (Krok 10), `exifAnalysis` (Krok 13) a voliteľne `photoRepair` (Krok 12). Zapisuje výsledky do uzla `finalReport`. Žiadne formuláre.*

### finalReport – výstup skriptu
| Pole | Popis | Hodnoty |
|---|---|---|
| Celkový počet obnovených fotografií | | |
| Integrity score | | % |
| Hodnotenie kvality | | Very Good / Good / Fair / Poor |
| Počet vygenerovaných sekcií | | 10 |
| PDF vygenerované | Závisí od dostupnosti reportlab | áno / nie |

### Přílohy – automaticky nahrané skriptom
| Príloha | Popis | Povinné |
|---|---|---|
| Final report JSON | `FINAL_REPORT.json` | áno |
| Final report PDF | `FINAL_REPORT.pdf` | podmienečne |
| README | `README.txt` | áno |
| Delivery checklist | `delivery_checklist.json` | áno |

---

## Krok 15 – Odovzdanie klientovi
*Manuálny krok. Analytik vypĺňa formulár uzla `caseDelivery` a nahrá prílohy. Prípad sa uzatvára.*

### caseDelivery – formulár uzla
| Pole | Popis | Povinné | Hodnoty |
|---|---|---|---|
| Spôsob odovzdania | | áno | osobné odovzdanie / kuriér / elektronické odovzdanie |
| Odovzdané komu | Meno klienta | áno | |
| Totožnosť overená | | áno | toggle |
| Pôvodné médium vrátené | | áno | toggle |
| Odovzdávací protokol podpísaný | | áno | toggle |
| Počet odovzdaných súborov | | áno | |
| Retenčná lehota archivácie | V rokoch | áno | štandardne 7 |
| Stav prípadu | | áno | CLOSED |
| Zabezpečený odkaz | Len pri elektronickom odovzdaní | podmienečne | |
| Číslo sledovania | Len pri kuriérskej preprave | podmienečne | |

### Přílohy – manuálne nahratie
| Príloha | Popis | Povinné |
|---|---|---|
| MANIFEST.json | Zoznam všetkých odovzdaných súborov so SHA-256 súčtami | áno |
| Odovzdávací protokol | Naskenovaný podpísaný protokol | áno |

---

## Otvorené otázky – na prejednanie

**Krok 5: Uloženie forenzného obrazu `.dd`**
Kde sa ukladá samotný forenzný obraz? Cez Přílohy na Penterep, alebo na externé forenzné úložisko mimo platformy? Toto ovplyvňuje pole „Cesta k obrazu" v uzle `imagingResult` a čo skript po dokončení imagingu robí s výstupným súborom.

**Kroky 3 a 5: Write-blocker potvrdenie**
Oba kroky vyžadujú fyzické potvrdenie write-blockera pred spustením skriptu. Ako to Penterep zobrazí — ako modálne okno, checkbox, alebo iný UI element?

**Krok 4: Poduzol fyzickej opravy**
Fyzická oprava vytvára poduzol pod uzlom zariadenia. Podporuje Penterep hierarchiu uzlov (rodič → dieťa), alebo sa oprava zaznamenáva inak?

**Kroky 8a / 8b: Poradie pri hybrid**
8a a 8b čítajú z rovnakého uzla `filesystemAnalysis` nezávisle a píšu do rôznych uzlov. Krok 9 čaká na oba. Technicky môžu bežať paralelne — je to žiaduce, alebo sekvenčne (8a dokončí → 8b)?

**Krok 14 a 15: MANIFEST.json**
`MANIFEST.json` obsahuje SHA-256 súčty všetkých odovzdávaných súborov. Logicky by ho mal generovať automaticky skript Kroku 14 spolu s ostatnými výstupmi. Ak áno — čo analytik fyzicky uzatvára v Kroku 15 a ako sa prípad formálne ukončí na platforme?

**Krok 14: Peer review a podpisy**
`delivery_checklist.json` obsahuje položky peer review a podpisy so stavom PENDING. Kde sa tieto vykonávajú — mimo Penterep (fyzicky), alebo má platforma miesto kde sa potvrdí kontrola nadriadeným analytikom pred pokračovaním do Kroku 15?

**Krok 14: PDF generovanie**
`FINAL_REPORT.pdf` sa generuje len ak je nainštalovaný `reportlab`. Je to povinná závislosť na serveri, alebo voliteľná?

**Krok 15: Príprava balíka**
Krok 15 opisuje manuálne kopírovanie súborov z adresárov `validation/valid/` a `repair/repaired/`. Má toto robiť analytik ručne, alebo by to mal automatizovať skript spustený z platformy?

**Krok 15: Ponaučenia pre budúce prípady**
Krok 15 hovorí o zaznamenaní súhrnu priebehu vrátane ponaučení. Kde sa toto zaznamenáva — do poľa Poznámka v uzle `caseDelivery`, alebo existuje na Penterep samostatné miesto pre retrospektívu prípadu?