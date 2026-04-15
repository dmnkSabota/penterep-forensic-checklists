# 🎯 ULTIMATE TESTING PLAN
## Kompletný Plán Testovania Celého Photo Recovery Scenára

---

## 📋 OBSAH - Čo všetko pokrýva tento návod

```
ČASŤ I: PRÍPRAVA (4 hodiny)
├─ 1. VirtualBox Setup
├─ 2. Ubuntu 22.04 Inštalácia
├─ 3. Forensic Tools Inštalácia
└─ 4. Simulované Zariadenia Vytvorenie (8 devices)

ČASŤ II: TESTOVANIE V LINUXE - SIMULOVANÉ (10 hodín)
├─ 5. Scenár S1: SD karta (Happy Path)
├─ 6. Scenár S2: USB flash (Partial)
├─ 7. Scenár S3: HDD degraded
└─ 8. Scenár S4: SSD encrypted

ČASŤ III: TESTOVANIE V LINUXE - REÁLNE (7 hodín)
├─ 9. Scenár S5: Real USB
├─ 10. Scenár S6: Real HDD
└─ 11. Scenár S7: Real SSD

ČASŤ IV: TESTOVANIE VO WINDOWS (6 hodín)
├─ 12. Windows Setup
├─ 13. Real USB Testing (Windows)
├─ 14. Real HDD Testing (Windows)
└─ 15. Real SSD Testing (Windows)

ČASŤ V: DOKUMENTÁCIA (3 hodiny)
├─ 16. Screenshots Organizácia
├─ 17. Test Reports Písanie
└─ 18. Thesis Kapitola Kompletácia

CELKOM: 30 hodín = KOMPLETNÉ TESTOVANIE
```

---

# ČASŤ I: PRÍPRAVA TESTOVACIEHO PROSTREDIA

## 🖥️ Krok 1: VirtualBox Inštalácia (30 minút)

### 1.1 Download Requirements

```
Potrebuješ stiahnuť:

1. VirtualBox 7.0.x
   URL: https://www.virtualbox.org/wiki/Downloads
   File: VirtualBox-7.0.x-Win.exe (~110 MB)
   
2. VirtualBox Extension Pack 7.0.x
   URL: Rovnaká stránka
   File: Oracle_VM_VirtualBox_Extension_Pack-7.0.x.vbox-extpack (~11 MB)
   ⚠️ KRITICKÉ pre USB 3.0 support!
   
3. Ubuntu 22.04.3 LTS ISO
   URL: https://ubuntu.com/download/desktop
   File: ubuntu-22.04.3-desktop-amd64.iso (~4.7 GB)
   ⏱️ Download trvá 10-30 minút

TOTAL: ~4.8 GB downloads
```

---

### 1.2 VirtualBox Inštalácia

```
1. Spusti VirtualBox-7.0.x-Win.exe

2. Wizard:
   → Next
   → Next (všetky features enabled)
   → Yes (Network Interfaces warning)
   → Install
   → Finish

3. Spusti VirtualBox Manager

4. Extension Pack inštalácia:
   File → Preferences → Extensions
   → [+] icon
   → Browse → Oracle_VM_VirtualBox_Extension_Pack-7.0.x.vbox-extpack
   → Install → Scroll down → I Agree
   → Zadaj Windows admin heslo
   → OK

5. Verifikácia:
   Preferences → Extensions
   Musíš vidieť: Oracle VM VirtualBox Extension Pack (Active)
   
   ✓ Ak vidíš → USB 3.0 READY
   ✗ Ak nevidíš → Repeat step 4

6. → OK (zatvor Preferences)
```

---

### 1.3 VM Vytvorenie

```
1. VirtualBox Manager → New

2. Name and Operating System:
   Name: Forensic-Testing-VM
   Folder: C:\VMs\Forensic-Testing-VM
   ISO Image: → Other → Browse → ubuntu-22.04.3-desktop-amd64.iso
   Type: Linux
   Version: Ubuntu (64-bit)
   ☑ Skip Unattended Installation ← ZAŠKRTNI!
   → Next

3. Hardware:
   Base Memory: 8192 MB (8 GB) ← Viac = lepšie
   Processors: 4 CPUs ← Viac = rýchlejšie
   
   Minimum pre testing:
   - 4 GB RAM (bude pomalé)
   - 2 CPUs
   
   → Next

4. Virtual Hard Disk:
   Disk Size: 80 GB ← Potrebuješ priestor pre images
   → Next

5. Summary:
   Skontroluj:
   - RAM: 8 GB
   - CPUs: 4
   - Disk: 80 GB
   → Finish
```

---

### 1.4 VM Configuration (pred prvým spustením)

```
VirtualBox Manager:
→ Select "Forensic-Testing-VM"
→ Settings

1. System:
   Motherboard:
   - Boot Order: Hard Disk (1st), Optical (2nd)
   - Extended Features:
     ☑ Enable I/O APIC
     ☑ Enable EFI
   
   Processor:
   - Processors: 4 CPUs
   - Extended Features:
     ☑ Enable PAE/NX

2. Display:
   Screen:
   - Video Memory: 128 MB
   - Graphics Controller: VMSVGA
   - ☑ Enable 3D Acceleration

3. Storage:
   Controller: IDE
   - [CD icon] → Disk icon → ubuntu-22.04.3-desktop-amd64.iso
   ✓ Verify ISO is attached

4. USB: ⚠️ KRITICKÉ
   ● USB 3.0 (xHCI) Controller
   
   Ak nemáš túto možnosť:
   → Extension Pack nie je nainštalovaný!
   → Vráť sa na krok 1.2

5. Network:
   Adapter 1:
   ☑ Enable Network Adapter
   Attached to: NAT

6. Shared Folders:
   → [+] icon
   Folder Path: C:\Forensic_Testing
   Folder Name: Forensic_Testing
   ☑ Auto-mount
   ☑ Make Permanent
   → OK

7. → OK (save settings)
```

---

## 🐧 Krok 2: Ubuntu Inštalácia (30 minút)

### 2.1 Prvé Spustenie

```
1. VirtualBox Manager
   → Select "Forensic-Testing-VM"
   → Start (zelená šípka)

2. Ubuntu Boot Menu:
   → Try or Install Ubuntu (default)
   → Wait 30 seconds

3. Welcome Screen:
   Language: English
   → Install Ubuntu

4. Keyboard Layout:
   English (US)
   → Continue

5. Updates and Other Software:
   ● Normal installation
   ☑ Download updates while installing Ubuntu
   ☑ Install third-party software for graphics and Wi-Fi hardware
   → Continue

6. Installation Type:
   ● Erase disk and install Ubuntu
   ⚠️ Toto je virtuálny disk, nie Windows!
   → Install Now
   → Continue

7. Where Are You?
   Bratislava / Brno (auto-detected)
   → Continue

8. Who Are You?
   Your name: Forensic Analyst
   Computer name: forensic-vm
   Username: forensic
   Password: forensic123
   Confirm: forensic123
   ○ Log in automatically
   → Continue

9. Installation (15-20 minút):
   ☕ Čas na kávu!

10. Installation Complete:
    → Restart Now
    → Press Enter (ISO auto-ejects)

11. Login:
    Username: forensic
    Password: forensic123

12. First-time Setup:
    → Skip všetky kroky

13. Desktop READY! ✓
```

---

### 2.2 Guest Additions Inštalácia ⚠️ KRITICKÉ

```
1. V Ubuntu VM:
   VirtualBox Menu → Devices → Insert Guest Additions CD image

2. Ubuntu notification:
   "VBox_GAs_7.0.x" medium contains software...
   → Run

3. Terminal window:
   [sudo] password for forensic: forensic123

4. Inštalácia (2-3 min):
   Building modules...
   VirtualBox Guest Additions: Starting.
   → Press Return to close

5. Reboot:
   sudo reboot

6. Po reboote verifikuj:
   - Resize VirtualBox okno → Desktop sa prispôsobí ✓
   - View → Clipboard → Bidirectional
   - Copy text Windows → Paste Ubuntu ✓
   - View → Drag and Drop → Bidirectional
   - Drag file Windows → Ubuntu desktop ✓

7. Shared Folder:
   cd /media/sf_Forensic_Testing
   ls
   → Mali by si vidieť súbory z C:\Forensic_Testing

   Ak nefunguje:
   sudo adduser forensic vboxsf
   sudo reboot
```

---

## 🛠️ Krok 3: Forensic Tools Inštalácia (1 hodina)

### 3.1 System Update

```bash
# Open Terminal (Ctrl+Alt+T)

sudo apt update
sudo apt upgrade -y

# Toto trvá 10-15 minút
# Reboot po upgrade
sudo reboot
```

---

### 3.2 Core Forensic Utilities

```bash
sudo apt update

sudo apt install -y \
    util-linux \
    smartmontools \
    hdparm \
    mdadm \
    parted \
    e2fsprogs \
    dosfstools \
    exfat-fuse \
    exfat-utils \
    ntfs-3g \
    cryptsetup \
    lvm2

# Verifikácia
lsblk --version      # Expected: 2.37.2
smartctl --version   # Expected: 7.2
hdparm -V            # Expected: 9.60
mdadm --version      # Expected: 4.2
cryptsetup --version # Expected: 2.4.3
```

---

### 3.3 Photo & Media Tools

```bash
sudo apt install -y \
    imagemagick \
    exiftool \
    jpeginfo \
    pngcheck \
    testdisk \
    gddrescue

# Verifikácia
exiftool -ver       # Expected: 12.x
jpeginfo --version  # Expected: 1.6.x
photorec --version  # Expected: 7.x
ddrescue --version  # Expected: 1.26
```

---

### 3.4 Python & ptlibs

```bash
# Python (už nainštalovaný)
python3 --version
# Expected: Python 3.10.x

# pip
sudo apt install -y python3-pip python3-venv

# ptlibs
pip3 install ptlibs Pillow reportlab

# Verifikácia
python3 -c "import ptlibs; print('ptlibs:', ptlibs.__version__)"
python3 -c "import PIL; print('Pillow:', PIL.__version__)"
python3 -c "import reportlab; print('reportlab OK')"

# Expected:
# ptlibs: 1.0.25+
# Pillow: 9.x.x
# reportlab OK
```

---

### 3.5 Forensic Scripts Setup

```bash
# Vytvor pracovný adresár
mkdir -p ~/forensic_tools
cd ~/forensic_tools

# Skopíruj skripty z shared folder
# (predpokladá, že máš skripty v C:\Forensic_Testing\scripts\)

cp /media/sf_Forensic_Testing/scripts/ptmediareadability.py ./
cp /media/sf_Forensic_Testing/scripts/ptforensicimaging.py ./
cp /media/sf_Forensic_Testing/scripts/ptimageverification.py ./
# ... (všetky ostatné skripty)

# Alebo ak máš Git repo:
# git clone https://github.com/your-repo/forensic-tools.git
# cd forensic-tools

# Make executable
chmod +x *.py

# Verifikácia
python3 ptmediareadability.py --version
# Expected: Version: 1.0.0

# Vytvor symlink pre globálny prístup (optional)
sudo ln -s ~/forensic_tools/ptmediareadability.py /usr/local/bin/ptmediareadability
```

---

## 💾 Krok 4: Vytvorenie Simulovaných Zariadení (2 hodiny)

### 4.1 Adresárová Štruktúra

```bash
# Hlavný adresár pre všetky testy
mkdir -p ~/forensic_testing
cd ~/forensic_testing

# Podadresáre pre scenáre
mkdir -p scenario1_sd_happy
mkdir -p scenario2_usb_partial
mkdir -p scenario3_hdd_degraded
mkdir -p scenario4_ssd_encrypted
mkdir -p scenario5_usb_real
mkdir -p scenario6_hdd_real
mkdir -p scenario7_ssd_real

# Adresár pre test images
mkdir -p test_images

# Adresár pre výsledky
mkdir -p test_results
```

---

### 4.2 Vytvorenie 8 Simulovaných Zariadení

#### Device 1: SD Karta - Happy Path (512 MB)

```bash
cd ~/forensic_testing/test_images

# Vytvor image
dd if=/dev/zero of=sd_happy_512mb.img bs=1M count=512 status=progress
echo "✓ SD card image created (512 MB)"

# Pripoj ako loop device
sudo losetup /dev/loop10 sd_happy_512mb.img

# Formátuj ako FAT32
sudo mkfs.vfat -n "HAPPY_SD" /dev/loop10

# Mount a pridaj fotografie
sudo mkdir -p /mnt/test_media
sudo mount /dev/loop10 /mnt/test_media
sudo mkdir -p /mnt/test_media/DCIM/100CANON

# Vytvor 10 test JPEG fotografií
for i in {1..10}; do
    convert -size 1920x1080 plasma: \
        -pointsize 72 -fill white -gravity center \
        -annotate +0+0 "IMG_$(printf '%04d' $i)" \
        /tmp/img_$(printf '%04d' $i).jpg
    
    # Pridaj EXIF metadata
    exiftool -overwrite_original \
        -Make="Canon" \
        -Model="EOS 80D" \
        -DateTimeOriginal="2025:01:15 14:$(printf '%02d' $i):00" \
        -GPSLatitude=48.1486 \
        -GPSLongitude=17.1077 \
        -ISO=400 \
        -FNumber=5.6 \
        -FocalLength=50 \
        /tmp/img_$(printf '%04d' $i).jpg
    
    sudo cp /tmp/img_$(printf '%04d' $i).jpg /mnt/test_media/DCIM/100CANON/
done

# Verifikácia
ls -lh /mnt/test_media/DCIM/100CANON/
# Expected: 10 JPEG files, ~1-2 MB each

du -sh /mnt/test_media/DCIM/100CANON/
# Expected: 10-20 MB total

# Unmount
sudo umount /mnt/test_media

echo "✓ Device 1: SD Happy Path READY"
echo "   - 10 intact JPEG photos"
echo "   - Full EXIF metadata"
echo "   - Expected recovery: 100%"
```

---

#### Device 2: USB Flash - Partial Corruption (1 GB)

```bash
# Vytvor image
dd if=/dev/zero of=usb_partial_1gb.img bs=1M count=1024 status=progress
echo "✓ USB flash image created (1 GB)"

# Pripoj
sudo losetup /dev/loop11 usb_partial_1gb.img

# Formátuj
sudo mkfs.vfat -n "PARTIAL_USB" /dev/loop11

# Mount
sudo mount /dev/loop11 /mnt/test_media
sudo mkdir -p /mnt/test_media/DCIM/100NIKON

# Vytvor 10 fotografií
for i in {1..10}; do
    convert -size 1920x1080 gradient:blue-green \
        -pointsize 72 -fill white -gravity center \
        -annotate +0+0 "DSC_$(printf '%04d' $i)" \
        /tmp/dsc_$(printf '%04d' $i).jpg
    
    exiftool -overwrite_original \
        -Make="Nikon" \
        -Model="D7500" \
        -DateTimeOriginal="2025:01:20 10:$(printf '%02d' $i):00" \
        /tmp/dsc_$(printf '%04d' $i).jpg
    
    sudo cp /tmp/dsc_$(printf '%04d' $i).jpg /mnt/test_media/DCIM/100NIKON/
done

# SIMULUJ POŠKODENIE:

# 1. Corrupted header (DSC_0003)
sudo dd if=/dev/urandom \
    of=/mnt/test_media/DCIM/100NIKON/dsc_0003.jpg \
    bs=512 count=1 conv=notrunc
echo "   ✓ dsc_0003.jpg - header corrupted"

# 2. Corrupted data in middle (DSC_0005)
sudo dd if=/dev/urandom \
    of=/mnt/test_media/DCIM/100NIKON/dsc_0005.jpg \
    bs=1024 count=10 seek=100 conv=notrunc
echo "   ✓ dsc_0005.jpg - data corrupted"

# 3. Truncated file (DSC_0008)
sudo truncate -s 30% /mnt/test_media/DCIM/100NIKON/dsc_0008.jpg
echo "   ✓ dsc_0008.jpg - truncated"

# 4. Delete 2 files
sudo rm /mnt/test_media/DCIM/100NIKON/dsc_0002.jpg
sudo rm /mnt/test_media/DCIM/100NIKON/dsc_0007.jpg
echo "   ✓ 2 files deleted (dsc_0002, dsc_0007)"

# Sync
sudo sync
sudo umount /mnt/test_media

# Poškodenie FAT table
sudo dd if=/dev/urandom of=/dev/loop11 \
    bs=512 count=5 seek=32 conv=notrunc
echo "   ✓ FAT table damaged"

echo "✓ Device 2: USB Partial READY"
echo "   - 5 intact photos"
echo "   - 3 corrupted photos"
echo "   - 2 deleted photos"
echo "   - Expected recovery: 50-60%"
```

---

#### Device 3: HDD - Degraded with Bad Sectors (2 GB)

```bash
# Vytvor image
dd if=/dev/zero of=hdd_degraded_2gb.img bs=1M count=2048 status=progress
echo "✓ HDD image created (2 GB)"

# Pripoj
sudo losetup /dev/loop12 hdd_degraded_2gb.img

# Vytvor partition table
sudo parted /dev/loop12 mklabel msdos
sudo parted /dev/loop12 mkpart primary fat32 1MiB 100%
sudo partprobe /dev/loop12

# Formátuj
sudo mkfs.vfat -n "HDD_PHOTO" /dev/loop12

# Mount
sudo mount /dev/loop12 /mnt/test_media
sudo mkdir -p /mnt/test_media/DCIM/100CANON

# Vytvor 12 fotografií
for i in {1..12}; do
    convert -size 2560x1920 gradient:red-yellow \
        -pointsize 100 -fill white -gravity center \
        -annotate +0+0 "IMG_HDD_$(printf '%04d' $i)" \
        /tmp/img_hdd_$(printf '%04d' $i).jpg
    
    sudo cp /tmp/img_hdd_$(printf '%04d' $i).jpg \
        /mnt/test_media/DCIM/100CANON/
done

sudo umount /mnt/test_media

# SIMULUJ BAD SECTORS (500 bad sectors)
echo "   Simulating 500 bad sectors..."
for j in {1..50}; do
    RANDOM_SEEK=$((RANDOM % 2000000))
    sudo dd if=/dev/urandom of=/dev/loop12 \
        bs=512 count=10 seek=$RANDOM_SEEK conv=notrunc 2>/dev/null
    echo -n "."
done
echo ""
echo "   ✓ 500 bad sectors simulated"

# Poškodenie FAT table navyše
sudo dd if=/dev/urandom of=/dev/loop12 \
    bs=512 count=20 seek=32 conv=notrunc
echo "   ✓ FAT table damaged"

echo "✓ Device 3: HDD Degraded READY"
echo "   - 12 photos total"
echo "   - 500 bad sectors"
echo "   - Expected recovery: 58-67%"
```

---

#### Device 4: SSD - LUKS Encrypted (256 MB)

```bash
# Vytvor image
dd if=/dev/zero of=ssd_encrypted_256mb.img bs=1M count=256 status=progress
echo "✓ SSD image created (256 MB)"

# Pripoj
sudo losetup /dev/loop13 ssd_encrypted_256mb.img

# LUKS encryption
echo "forensic_test_2025" | \
    sudo cryptsetup luksFormat /dev/loop13 --batch-mode -
echo "   ✓ LUKS encryption created"
echo "   Password: forensic_test_2025"

# Otvor LUKS
echo "forensic_test_2025" | \
    sudo cryptsetup luksOpen /dev/loop13 encrypted_ssd

# Formátuj vnútorný volume
sudo mkfs.ext4 -L "ENC_PHOTOS" /dev/mapper/encrypted_ssd

# Mount
sudo mount /dev/mapper/encrypted_ssd /mnt/test_media
sudo mkdir -p /mnt/test_media/photos

# Vytvor 8 fotografií
for i in {1..8}; do
    convert -size 1600x1200 plasma:fractal \
        -pointsize 60 -fill white -gravity center \
        -annotate +0+0 "ENCRYPTED_$(printf '%03d' $i)" \
        /tmp/enc_$(printf '%03d' $i).jpg
    
    sudo cp /tmp/enc_$(printf '%03d' $i).jpg \
        /mnt/test_media/photos/
done

sudo umount /mnt/test_media

# Zavri LUKS
sudo cryptsetup luksClose encrypted_ssd

echo "✓ Device 4: SSD Encrypted READY"
echo "   - 8 photos (encrypted)"
echo "   - Password: forensic_test_2025"
echo "   - Expected recovery: 0% (bez hesla), 100% (s heslom)"
```

---

#### Device 5-8: Dodatočné Test Devices

```bash
# Device 5: Clean SD card (pre comparisons)
dd if=/dev/zero of=sd_clean_256mb.img bs=1M count=256 status=progress
sudo losetup /dev/loop14 sd_clean_256mb.img
sudo mkfs.vfat -n "CLEAN_SD" /dev/loop14
echo "✓ Device 5: Clean SD READY"

# Device 6: Corrupted filesystem (no partition table)
dd if=/dev/zero of=corrupted_fs_512mb.img bs=1M count=512 status=progress
sudo losetup /dev/loop15 corrupted_fs_512mb.img
sudo mkfs.ext4 -L "CORRUPT_FS" /dev/loop15
# Zniči superblock
sudo dd if=/dev/urandom of=/dev/loop15 bs=512 count=10 seek=2048 conv=notrunc
echo "✓ Device 6: Corrupted FS READY"

# Device 7: Mixed content (documents + photos)
dd if=/dev/zero of=mixed_content_1gb.img bs=1M count=1024 status=progress
sudo losetup /dev/loop16 mixed_content_1gb.img
sudo mkfs.vfat -n "MIXED" /dev/loop16
sudo mount /dev/loop16 /mnt/test_media
sudo mkdir -p /mnt/test_media/{photos,documents,videos}
# ... (pridaj mixed content)
sudo umount /mnt/test_media
echo "✓ Device 7: Mixed Content READY"

# Device 8: Old FAT16 (legacy format)
dd if=/dev/zero of=old_fat16_64mb.img bs=1M count=64 status=progress
sudo losetup /dev/loop17 old_fat16_64mb.img
sudo mkfs.vfat -F 16 -n "OLD_FAT16" /dev/loop17
echo "✓ Device 8: Old FAT16 READY"
```

---

### 4.3 Verifikácia Všetkých Zariadení

```bash
# Zobraz všetky loop devices
sudo losetup -a | grep loop1

# Expected output:
# /dev/loop10: [xxxx]:xxxxx (/home/forensic/forensic_testing/test_images/sd_happy_512mb.img)
# /dev/loop11: [xxxx]:xxxxx (/home/forensic/forensic_testing/test_images/usb_partial_1gb.img)
# /dev/loop12: [xxxx]:xxxxx (/home/forensic/forensic_testing/test_images/hdd_degraded_2gb.img)
# /dev/loop13: [xxxx]:xxxxx (/home/forensic/forensic_testing/test_images/ssd_encrypted_256mb.img)
# /dev/loop14: [xxxx]:xxxxx (/home/forensic/forensic_testing/test_images/sd_clean_256mb.img)
# /dev/loop15: [xxxx]:xxxxx (/home/forensic/forensic_testing/test_images/corrupted_fs_512mb.img)
# /dev/loop16: [xxxx]:xxxxx (/home/forensic/forensic_testing/test_images/mixed_content_1gb.img)
# /dev/loop17: [xxxx]:xxxxx (/home/forensic/forensic_testing/test_images/old_fat16_64mb.img)

# Zobraz file systémy
sudo blkid | grep loop1

# Vytvor snapshot VM (DÔLEŽITÉ!)
# VirtualBox Manager → Snapshots → Take
# Name: "All 8 Devices Ready"
# Description: "8 loop devices created and formatted, ready for testing"

echo "🎉 PRÍPRAVA KOMPLETNÁ!"
echo ""
echo "Máš vytvorených 8 simulovaných zariadení:"
echo "  ✓ loop10: SD Happy (512 MB, 10 intact photos)"
echo "  ✓ loop11: USB Partial (1 GB, 5 intact + 3 corrupt + 2 deleted)"
echo "  ✓ loop12: HDD Degraded (2 GB, 12 photos, 500 bad sectors)"
echo "  ✓ loop13: SSD Encrypted (256 MB, 8 photos, LUKS)"
echo "  ✓ loop14: SD Clean (256 MB, empty)"
echo "  ✓ loop15: Corrupted FS (512 MB, damaged superblock)"
echo "  ✓ loop16: Mixed Content (1 GB, photos + docs)"
echo "  ✓ loop17: Old FAT16 (64 MB, legacy format)"
echo ""
echo "Ready pre testovanie scenárov!"
```

---

# POKRAČOVANIE NASLEDUJE...

Toto je prvá časť (PRÍPRAVA). Pokračujem hneď s ČASŤOU II (TESTOVANIE V LINUXE)...

**Chceš, aby som pokračoval s kompletným návodom na všetky scenáre? (ešte ~150 strán) 📖**

# 🎯 ULTIMATE TESTING PLAN - KOMPLETNÝ INDEX
## Celý Photo Recovery Scenár - Všetko na jednom mieste

---

## 📚 ČO MAŤ TERAZ K DISPOZÍCII

### ✅ HOTOVÉ DOKUMENTY:

1. **ULTIMATE_TESTING_PLAN_PART1.md** (PRÍPRAVA)
   - VirtualBox inštalácia
   - Ubuntu setup
   - Forensic tools
   - 8 simulovaných zariadení
   - ⏱️ 4 hodiny
   - ✅ READY TO USE

2. **VALIDACIA_A_VYLEPSENIA.md**
   - Odpovede na tvoje otázky
   - Loop devices validácia
   - Real hardware recommendations
   - Test matrix

3. **Navod1B_VirtualBox_Setup.md**
   - VirtualBox-specific guide
   - Extension Pack setup
   - Guest Additions
   - USB passthrough

4. **README_MASTER_TESTING_GUIDE.md**
   - Master index všetkých návodov
   - Testing stratégie (A/B/C)
   - Troubleshooting

---

## 📋 KOMPLETNÝ TESTING MATRIX

```
10 SCENÁROV CELKOM:

LINUX VM - SIMULOVANÉ (4 scenáre):
  S1: SD Happy Path         512MB    100% recovery    2h
  S2: USB Partial           1GB      50-60% recovery  2.5h
  S3: HDD Degraded          2GB      58-67% recovery  3h
  S4: SSD Encrypted         256MB    0%*/100% recov   1h

LINUX VM - REÁLNE (3 scenáre):
  S5: Real USB              16GB     100% recovery    2h
  S6: Real HDD              160GB    ~70% recovery    3h
  S7: Real SSD              128GB    100% recovery    2h

WINDOWS - REÁLNE (3 scenáre):
  S8: USB Windows           16GB     100% recovery    2h
  S9: HDD Windows           160GB    ~70% recovery    2h
  S10: SSD Windows          128GB    100% recovery    2h

CELKOM: 10 scenárov, 25-30 hodín
```

---

## 🎯 3 VARIANTY TESTOVANIA

### VARIANT A: Minimálny (10h) - STAČÍ PRE PASS
```
✓ PART 1: Príprava (4h)
✓ S1: Happy Path simulated (2h)
✓ S5: Real USB Linux (2h)
✓ Dokumentácia basic (2h)

TOTAL: 10h
VÝSLEDOK: PASS diploma
```

### VARIANT B: Optimálny (24h) - ODPORÚČANÝ ⭐
```
✓ PART 1: Príprava (4h)
✓ S1-S4: Simulované (10h)
✓ S5-S7: Real Linux (7h)
✓ Dokumentácia full (3h)

TOTAL: 24h
VÝSLEDOK: EXCELLENT diploma
```

### VARIANT C: Maximálny (30h) - TOP TIER
```
✓ PART 1: Príprava (4h)
✓ S1-S4: Simulované (10h)
✓ S5-S7: Real Linux (7h)
✓ S8-S10: Windows (6h)
✓ Dokumentácia full (3h)

TOTAL: 30h
VÝSLEDOK: TOP 5% diploma
```

---

## 🚀 QUICK START - ČO UROBIŤ TERAZ

### DNES (30 minút):

```
1. [ ] Rozhodnutie: Variant A / B / C ?

2. [ ] Stiahni:
       • VirtualBox 7.0.x
       • VirtualBox Extension Pack
       • Ubuntu 22.04.3 LTS ISO

3. [ ] Ak Variant B alebo C:
       • Objednaj USB-to-SATA adapter (10 EUR)
       • Nájdi starý HDD (160+ GB)
       • Nájdi starý SSD (64+ GB)
```

---

### TENTO VÍKEND (4 hodiny):

```
Follow: ULTIMATE_TESTING_PLAN_PART1.md

1. [ ] VirtualBox inštalácia (30 min)
2. [ ] Ubuntu inštalácia (30 min)
3. [ ] Forensic tools (1h)
4. [ ] 8 simulovaných zariadení (2h)

VÝSLEDOK:
✓ Funkčná VM
✓ 8 devices ready
✓ Snapshot: "All 8 Devices Ready"
✓ READY pre testovanie scenárov
```

---

### BUDÚCI VÍKEND (2-10 hodín):

```
Závisí od variantu:

VARIANT A:
• S1: Happy Path (2h)

VARIANT B:
• S1-S4: Všetky simulované (10h)

VARIANT C:
• S1-S4: Všetky simulované (10h)
```

---

## 📖 AKÉ DOKUMENTY TI CHÝBAJÚ?

### Pre kompletné testovanie potrebuješ ešte:

```
PART 2: LINUX - SIMULOVANÉ SCENÁRE (~80 strán)
  └─ S1: SD Happy Path (Steps 1-15 detailne)
  └─ S2: USB Partial (Steps 1-15)
  └─ S3: HDD Degraded (Steps 1-15)
  └─ S4: SSD Encrypted (Steps 1-4, STOP)

PART 3: LINUX - REÁLNE SCENÁRE (~50 strán)
  └─ S5: Real USB testing
  └─ S6: Real HDD testing
  └─ S7: Real SSD testing

PART 4: WINDOWS TESTING (~40 strán)
  └─ Windows tools setup
  └─ S8: USB na Windows
  └─ S9: HDD na Windows
  └─ S10: SSD na Windows

PART 5: DOKUMENTÁCIA (~30 strán)
  └─ Screenshots organization
  └─ Test reports templates (SK)
  └─ Thesis chapter template
  └─ Test matrix Excel template
```

---

## 💬 TVOJA VOĽBA - POVEDZ MI

**Potrebujem od teba 3 odpovede:**

### 1. Aký variant chceš?
```
[ ] A - Minimálny (10h, iba S1+S5)
[ ] B - Optimálny (24h, S1-S7) ⭐ ODPORÚČAM
[ ] C - Maximálny (30h, S1-S10)
```

### 2. Máš real hardware?
```
[ ] USB flash - áno / nie
[ ] Starý HDD - áno / nie / kúpim
[ ] Starý SSD - áno / nie / kúpim
[ ] USB-to-SATA adapter - áno / nie / kúpim
```

### 3. Čo potrebuješ TERAZ?
```
[ ] A - Začnem s PART 1, potom mi pošli PART 2
[ ] B - Chcem celý balík NARAZ (PART 2-5)
[ ] C - Iba špecifické časti: ___________
```

---

## 🎯 MOJE ODPORÚČANIE

```
Najlepší postup:

1. TERAZ:
   → Začni s PART 1 (už máš!)
   → 4 hodiny setup VM + devices
   → Snapshot

2. PO VÍKENDE:
   → Napíš mi feedback
   → Vytvorím PART 2 (scenáre S1-S4)
   → Adjustujem podľa tvojich potrieb

3. ITERATÍVNE:
   → Postupne testuješ
   → Postupne dostávaš ďalšie časti
   → Flexibilné úpravy

PREČO:
✓ Rýchly start (za 4h máš VM ready)
✓ Feedback loop (môžem upraviť)
✓ Nie overload (200 strán naraz = chaos)
✓ Praktické (testuješ počas písania)
```

---

## ❓ NAPÍŠ MI

**Prosím povedz mi:**

1. **Ktorý variant** chceš: A / B / C ?
2. **Real hardware** máš: USB / HDD / SSD ?
3. **Čo teraz** potrebuješ: PART 1 start / Celý balík / Špecifické ?

**A potom ti vytvorím PRESNE to, čo potrebuješ! 🎯**

---

## 📞 SUMMARY

**Čo MAŤ:**
- ✅ PART 1 ready (príprava, 4h)
- ✅ Validácia dokumentu
- ✅ VirtualBox guide
- ✅ Master index

**Čo CHÝBA:**
- ⏳ PART 2 (simulované scenáre, 10h)
- ⏳ PART 3 (real Linux, 7h)
- ⏳ PART 4 (Windows, 6h)
- ⏳ PART 5 (dokumentácia, 3h)

**Čo urobiť TERAZ:**
1. Prečítaj PART 1
2. Rozhodnúť sa: A/B/C variant
3. Napísať mi odpovede
4. → Vytvorím zvyšok dokumentácie

**LET'S GO! 🚀**