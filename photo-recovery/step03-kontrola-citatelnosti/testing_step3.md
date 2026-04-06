# Testing Guide: ptmediareadability.py

Quick step-by-step guide for testing all scenarios on Ubuntu 22.04 LTS

---

## Prerequisites
```bash
# Install required tools
sudo apt install -y smartmontools mdadm hdparm cryptsetup

# Verify Python and ptlibs
python3 --version
python3 -c "import ptlibs; print('ptlibs OK')"

# Navigate to script directory
cd ~/Desktop/penterep-forensic-checklists/photo-recovery/step03-kontrola-citatelnosti
```

---

## Test 1: READABLE Scenario (Perfect Media)

### Setup
```bash
# Create perfect ext4 image
dd if=/dev/zero of=~/test_readable.img bs=1M count=512
mkfs.ext4 ~/test_readable.img

# Mount as loop device
sudo losetup /dev/loop10 ~/test_readable.img
sudo chmod 666 /dev/loop10

# Verify device exists
lsblk | grep loop10
```

### Execute Test
```bash
python3 ptmediareadability.py /dev/loop10 TEST-READABLE-001 \
  --analyst "Dominik Sabota" \
  --output test_readable.json
```

### Expected Results
- Write-blocker prompt: Enter `y`
- All 5 pre-detection checks: ✓ PASS
- All 4 diagnostic tests: ✓ PASS
- **Media Status: READABLE**
- **Recommended Tool: dc3dd**
- Exit code: 0

### Verify JSON
```bash
cat test_readable.json | python3 -m json.tool | head -20
```

### Cleanup
```bash
sudo losetup -d /dev/loop10
rm ~/test_readable.img test_readable.json
```

---

## Test 2: LUKS Encryption Detection

### Setup
```bash
# Create LUKS encrypted image
dd if=/dev/zero of=~/test_luks.img bs=1M count=512
echo "testpassword" | sudo cryptsetup luksFormat ~/test_luks.img --batch-mode

# Mount encrypted container (without opening)
sudo losetup /dev/loop11 ~/test_luks.img
sudo chmod 666 /dev/loop11
```

### Execute Test
```bash
python3 ptmediareadability.py /dev/loop11 TEST-LUKS-001 \
  --analyst "Dominik Sabota" \
  --output test_luks.json
```

### Expected Results
- Write-blocker prompt: Enter `y`
- **blkid: ⚠️ ENCRYPTION: LUKS detected!**
- **Critical Findings: ["Encryption detected: LUKS - recovery key required"]**
- Media Status: READABLE (encrypted bytes are readable)
- Exit code: 0

### Cleanup
```bash
sudo losetup -d /dev/loop11
rm ~/test_luks.img test_luks.json
```

---

## Test 3: Permission Denied (Simulated UNREADABLE)

### Setup
```bash
# Create image but keep root-only permissions
dd if=/dev/zero of=~/test_unreadable.img bs=1M count=512
sudo losetup /dev/loop12 ~/test_unreadable.img
# Don't chmod - leave as root-only
```

### Execute Test
```bash
# Run WITHOUT sudo to trigger permission error
python3 ptmediareadability.py /dev/loop12 TEST-UNREADABLE-001 \
  --analyst "Dominik Sabota"
```

### Expected Results
- Write-blocker prompt: Enter `y`
- **Test 1/4: First Sector: ✗ FAIL**
- **Media Status: UNREADABLE**
- **Recommended Tool: Physical repair required**
- Exit code: 2

### Cleanup
```bash
sudo losetup -d /dev/loop12
rm ~/test_unreadable.img
```

---

## Test 4: Device Not Found

### Execute Test
```bash
python3 ptmediareadability.py /dev/nonexistent TEST-NOTFOUND-001 \
  --analyst "Dominik Sabota"
```

### Expected Results
- **Error: Device not found: /dev/nonexistent**
- Exit code: 1 or 99

---

## Test 5: Invalid Device Path

### Execute Test
```bash
python3 ptmediareadability.py /invalid/path TEST-INVALID-001 \
  --analyst "Dominik Sabota"
```

### Expected Results
- **Error: Invalid device path: /invalid/path**
- Exit code: 1 or 99

---

## Test 6: Write-Blocker Declined

### Setup
```bash
dd if=/dev/zero of=~/test_wb.img bs=1M count=512
sudo losetup /dev/loop13 ~/test_wb.img
sudo chmod 666 /dev/loop13
```

### Execute Test
```bash
python3 ptmediareadability.py /dev/loop13 TEST-WB-NO-001 \
  --analyst "Dominik Sabota"
```

### Expected Results
- Write-blocker prompt: Enter `n` or just press Enter
- **NOT CONFIRMED - test ABORTED**
- Exit code: 99

### Cleanup
```bash
sudo losetup -d /dev/loop13
rm ~/test_wb.img
```

---

## Test 7: Keyboard Interrupt

### Setup
```bash
dd if=/dev/zero of=~/test_interrupt.img bs=1M count=512
mkfs.ext4 ~/test_interrupt.img
sudo losetup /dev/loop14 ~/test_interrupt.img
sudo chmod 666 /dev/loop14
```

### Execute Test
```bash
python3 ptmediareadability.py /dev/loop14 TEST-INTERRUPT-001 \
  --analyst "Dominik Sabota"
```

### During Execution
- Write-blocker prompt: Enter `y`
- **During tests: Press Ctrl+C**

### Expected Results
- **Message: Interrupted by user**
- Exit code: 130

### Cleanup
```bash
sudo losetup -d /dev/loop14
rm ~/test_interrupt.img
```

---

## Test 8: Terminal Output Only (No JSON)

### Setup
```bash
dd if=/dev/zero of=~/test_terminal.img bs=1M count=512
mkfs.ext4 ~/test_terminal.img
sudo losetup /dev/loop15 ~/test_terminal.img
sudo chmod 666 /dev/loop15
```

### Execute Test
```bash
python3 ptmediareadability.py /dev/loop15 TEST-TERMINAL-001 \
  --analyst "Dominik Sabota"
# Note: NO --output flag
```

### Expected Results
- Complete terminal output displayed
- **No JSON file created**
- Verify: `ls test_terminal*.json` (should not exist)

### Cleanup
```bash
sudo losetup -d /dev/loop15
rm ~/test_terminal.img
```

---

## Exit Codes Reference

| Code | Status | Meaning |
|------|--------|---------|
| 0 | ✅ READABLE | All tests passed |
| 1 | ⚠️ PARTIAL | Sequential OK, some failed |
| 2 | ❌ UNREADABLE | First sector failed |
| 99 | ⚠️ ERROR | Write-blocker declined or error |
| 130 | 🛑 INTERRUPTED | Ctrl+C pressed |

---

## Cleanup All Test Devices
```bash
# Detach all loop devices
for i in {10..15}; do
    sudo losetup -d /dev/loop$i 2>/dev/null
done

# Remove all test images
rm -f ~/test_*.img ~/t*.img

# Remove all test JSON files
rm -f test_*.json t*.json

echo "✓ All test devices cleaned up"
```