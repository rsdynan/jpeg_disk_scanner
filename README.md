# JPEG Disk Health Scanner & Repair Tool

Scans a folder (and subfolders) on an external drive for JPEG files that are corrupted or unreadable due to disk problems. By default the script is **READ-ONLY** — it never modifies the external drive unless you explicitly pass `--repair`.

## Usage

```bash
# Scan a single file (safe, no changes made):
python scan_jpegs.py "E:\Photos\IMG_001.jpg"

# Scan an entire folder:
python scan_jpegs.py "E:\Photos"

# Scan and attempt repairs (copies repaired files to a local output folder):
python scan_jpegs.py "E:\Photos" --repair --output "C:\Repaired"

# Single file with a longer timeout (useful for drives with bad sectors):
python scan_jpegs.py "E:\Photos\IMG_001.jpg" --timeout 60

# Limit scan depth and set a longer I/O timeout:
python scan_jpegs.py "E:\Photos" --max-depth 2 --timeout 15

# Save a detailed report:
python scan_jpegs.py "E:\Photos" --report "C:\scan_report.txt"
```

## Requirements

```bash
pip install Pillow          # image validation
pip install psutil          # process tree killing (strongly recommended)
pip install piexif          # EXIF repair helper (optional)
```

**Windows users:** run as Administrator for the best low-level error information.

## Keyboard Interrupt (Ctrl+C)

- Press **Ctrl+C once** to stop after the current file finishes.
- Press **Ctrl+C twice quickly** to terminate immediately.
- Either way the partial results and report are saved automatically.

## Repair Modes

Pass `--repair` to copy salvageable files to a local folder (the external drive is **NEVER** modified). Two repair strategies are used automatically depending on the type of problem detected:

### Structural Repair (MISSING_EOI, BAD_HEADER, PIL_DECODE_FAIL)
Used when the JPEG container is broken but the pixel data region is intact. The script patches the byte stream (appends a missing EOI marker, strips a corrupt EXIF/APP1 block if needed), verifies the result with Pillow, then writes the fixed file to the output folder.

### Raw Copy (SLOW_READ, pixel anomalies, EXIF dimension mismatches)
Used when the file decoded but shows signs of partial sector loss — slow reads, error-concealment blocks, or a mismatch between the EXIF-reported dimensions and the actual decoded image size. In this case the script writes the **EXACT bytes** that came off the disk without any re-encoding. Re-encoding through Pillow would reconstruct the image only from what Pillow managed to decode, discarding original compressed data and potentially losing partially-intact scan lines. The raw copy preserves every recoverable byte. If piexif is installed the EXIF dimension tags are corrected to match the decoded size so image viewers allocate the right amount of memory and open the file more gracefully.

### What to Expect in Repaired Copies
- Structurally repaired files should open normally and look correct.
- Raw copies of partially-damaged files will open without errors but will show the intact region normally and the damaged region as solid-colour blocks (grey, green, or black) — this is JPEG error-concealment filling in the missing scan data. The intact portion of the image is preserved exactly as it came off the disk.
- Files that timed out cannot be repaired — the data could not be read from the drive at all.

## Status Codes

| Code | Description |
|------|-------------|
| `OK` | File is healthy and reads cleanly. |
| `SLOW_READ` | File decoded correctly but the read took longer than `--slow-threshold` seconds. Leading indicator of sector degradation even before data loss occurs. |
| `MISSING_EOI` | JPEG End-of-Image marker absent — file is likely truncated. |
| `BAD_HEADER` | File does not start with the JPEG SOI marker (FF D8). |
| `PIL_DECODE_FAIL` | Pillow cannot decode the image data. |
| `PIL_TRUNCATED` | Pillow detected a truncated image during full decode. |
| `UNSTABLE_READ` | Two successive reads returned different bytes — strong indicator of a physically failing sector. |
| `EXIF_MISMATCH` | EXIF dimensions differ from decoded dimensions (advisory, shown as [WARN] rather than a hard failure). |
| `PIXEL_ANOMALY` | Decoded image contains an abnormal proportion of solid-colour tiles consistent with error-concealment (advisory). |
| `IO_ERROR` | OS-level read error (permissions, missing device, etc.). |
| `TIMEOUT` | Read did not complete within `--timeout` seconds. |
| `REPAIRED` | A repaired or raw copy was written to the output folder. |
| `REPAIR_FAILED` | Repair was attempted but could not produce a usable file. |
