r"""
scan_jpegs.py — JPEG Disk Health Scanner & Repair Tool
========================================================
Scans a folder (and subfolders) on an external drive for JPEG files that are
corrupted or unreadable due to disk problems.  By default the script is
READ-ONLY — it never modifies the external drive unless you explicitly pass
--repair.

General workflow
----------------
  Step 1 — Install dependencies (one time only):

    pip install Pillow psutil piexif numpy

    Pillow   : required for image decoding and pixel-level checks.
    psutil   : required for reliable process-tree killing when the drive
               hangs on a bad sector.  Strongly recommended.
    piexif   : used to read and correct EXIF metadata.  Optional but
               improves EXIF mismatch detection and raw-copy repair.
    numpy    : used for pixel anomaly detection.  Optional.

  Step 2 — Run a read-only scan first to assess the damage:

    python scan_jpegs.py "E:\Photos" --report "C:\scan_report.txt"

    This is completely safe — nothing on the drive is touched.  A text
    report and a CSV log (scan_log.csv) are written to your current
    directory.  The CSV is updated after every file so partial results
    are preserved even if the scan is interrupted.

  Step 3 — Review the report, then run with --repair if needed:

    python scan_jpegs.py "E:\Photos" --repair --output "C:\Recovered" ^
        --report "C:\scan_report.txt"

    Repaired and raw copies are written to C:\Recovered.  The external
    drive is never modified.

  Step 4 — Verify the recovered copies:

    Open a sample of the repaired files in an image viewer to confirm the
    intact regions look correct.  Partially-damaged files will show
    solid-colour blocks where data was unrecoverable — this is expected.

  Timeouts and bad sectors:
    If the drive is actively failing, reads can hang indefinitely at the
    OS level.  The script spawns each file read in a separate process so
    it can forcibly kill a stuck read after --timeout seconds (default 10).
    If many files are timing out, the drive I/O queue may be in a degraded
    state — consider a shorter timeout (--timeout 5) to keep the scan
    moving, and use the report to identify which files need attention.
    Files that time out cannot be repaired; the data did not reach the OS.

  If the PowerShell window hangs after Ctrl+C:
    A stuck kernel I/O call on a bad sector can prevent even a killed
    process from releasing its handles.  The most reliable recovery is to
    physically unplug the USB cable — this breaks the kernel wait
    immediately and frees the window.  Running taskkill /F /IM python.exe
    from a second elevated PowerShell also works once the drive I/O
    completes or times out at the hardware level.

Arguments
---------
  target
    Path to the folder or single JPEG file to scan.
    Examples:  E:\Photos          (scan entire folder)
               E:\Photos\0386.jpg  (scan one file)

  --repair
    Enable repair mode.  Salvageable files are copied to --output.
    The external drive is never written to.  Two strategies are used
    automatically — see "Repair modes" below.

  --output PATH
    Destination folder for repaired/recovered copies.
    Default: ./repaired_jpegs  (created in the current directory).
    Use a path on a healthy local drive, not the external drive.

  --report PATH
    Write a full text report to this path at the end of the scan.
    A CSV log with the same base name is also written incrementally.
    Example: --report "C:\scan_report.txt"  →  also writes scan_report.csv

  --timeout SECONDS
    How long to wait for a single file read before killing the worker
    process and marking the file as TIMEOUT.  Default: 10 seconds.
    Increase for very large files or very slow drives (--timeout 60).
    Decrease if the drive is actively failing and you want to keep moving
    (--timeout 5).

  --slow-threshold SECONDS
    Successful reads that take longer than this are flagged as SLOW_READ.
    Default: 2.0 seconds.  Adjust based on the normal speed of your drive.

  --max-depth N
    Limit folder recursion to N levels deep.  Default: unlimited.

  --verbose
    Print a line for every file, not just problems.

Usage examples
--------------
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

  # Full run: scan, repair, save report, verbose output:
  python scan_jpegs.py "E:\Photos" --repair --output "C:\Recovered" ^
      --report "C:\scan_report.txt" --timeout 10 --verbose

Requirements
------------
  pip install Pillow          # image validation
  pip install psutil          # process tree killing (strongly recommended)
  pip install piexif          # EXIF repair helper (optional)

  Windows users: run as Administrator for the best low-level error information.

Keyboard interrupt (Ctrl+C)
---------------------------
  Press Ctrl+C once to stop after the current file finishes.
  Press Ctrl+C twice quickly to terminate immediately.
  Either way the partial results and report are saved automatically.

Repair modes
------------
  Pass --repair to copy salvageable files to a local folder (the external
  drive is NEVER modified).  Two repair strategies are used automatically
  depending on the type of problem detected:

  Structural repair (MISSING_EOI, BAD_HEADER, PIL_DECODE_FAIL):
    Used when the JPEG container is broken but the pixel data region is
    intact.  The script patches the byte stream (appends a missing EOI
    marker, strips a corrupt EXIF/APP1 block if needed), verifies the
    result with Pillow, then writes the fixed file to the output folder.

  Raw copy (SLOW_READ, pixel anomalies, EXIF dimension mismatches):
    Used when the file decoded but shows signs of partial sector loss —
    slow reads, error-concealment blocks, or a mismatch between the
    EXIF-reported dimensions and the actual decoded image size.  In this
    case the script writes the EXACT bytes that came off the disk without
    any re-encoding.  Re-encoding through Pillow would reconstruct the
    image only from what Pillow managed to decode, discarding original
    compressed data and potentially losing partially-intact scan lines.
    The raw copy preserves every recoverable byte.  If piexif is installed
    the EXIF dimension tags are corrected to match the decoded size so
    image viewers allocate the right amount of memory and open the file
    more gracefully.

  What to expect in repaired copies:
    - Structurally repaired files should open normally and look correct.
    - Raw copies of partially-damaged files will open without errors but
      will show the intact region normally and the damaged region as
      solid-colour blocks (grey, green, or black) — this is JPEG
      error-concealment filling in the missing scan data.  The intact
      portion of the image is preserved exactly as it came off the disk.
    - Files that timed out cannot be repaired — the data could not be
      read from the drive at all.

Status codes
------------
  OK              File is healthy and reads cleanly.
  SLOW_READ       File decoded correctly but the read took longer than
                  --slow-threshold seconds.  Leading indicator of sector
                  degradation even before data loss occurs.
  MISSING_EOI     JPEG End-of-Image marker absent — file is likely truncated.
  BAD_HEADER      File does not start with the JPEG SOI marker (FF D8).
  PIL_DECODE_FAIL Pillow cannot decode the image data.
  PIL_TRUNCATED   Pillow detected a truncated image during full decode.
  UNSTABLE_READ   Two successive reads returned different bytes — strong
                  indicator of a physically failing sector.
  EXIF_MISMATCH   EXIF dimensions differ from decoded dimensions (advisory,
                  shown as [WARN] rather than a hard failure).
  PIXEL_ANOMALY   Decoded image contains an abnormal proportion of solid-
                  colour tiles consistent with error-concealment (advisory).
  IO_ERROR        OS-level read error (permissions, missing device, etc.).
  TIMEOUT         Read did not complete within --timeout seconds.
  REPAIRED        A repaired or raw copy was written to the output folder.
  REPAIR_FAILED   Repair was attempted but could not produce a usable file.
"""

# ---------------------------------------------------------------------------
# Windows multiprocessing requires freeze_support() before anything else.
# ---------------------------------------------------------------------------
import multiprocessing
multiprocessing.freeze_support()

import os
import sys
import struct
import hashlib
import argparse
import logging
import csv
import signal
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------
try:
    from PIL import Image, UnidentifiedImageError
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[WARNING] Pillow not installed.  Install with: pip install Pillow")
    print("          Image-level validation will be skipped.\n")

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[WARNING] psutil not installed.  Install with: pip install psutil")
    print("          Process-tree killing will be less reliable on bad sectors.\n")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
JPEG_SOI      = b'\xff\xd8'
JPEG_EOI      = b'\xff\xd9'
JPEG_EXTS     = {'.jpg', '.jpeg', '.jpe', '.jfif'}
MIN_JPEG_SIZE = 4

# ---------------------------------------------------------------------------
# Result codes
# ---------------------------------------------------------------------------
OK              = 'OK'
EMPTY           = 'EMPTY'
TOO_SMALL       = 'TOO_SMALL'
BAD_HEADER      = 'BAD_HEADER'
MISSING_EOI     = 'MISSING_EOI'
IO_ERROR        = 'IO_ERROR'
TIMEOUT         = 'TIMEOUT'
PIL_DECODE_FAIL = 'PIL_DECODE_FAIL'
PIL_TRUNCATED   = 'PIL_TRUNCATED'
PIXEL_ANOMALY   = 'PIXEL_ANOMALY'   # decoded but contains suspicious pixel regions
UNSTABLE_READ   = 'UNSTABLE_READ'   # two reads returned different bytes (bad sector)
EXIF_MISMATCH   = 'EXIF_MISMATCH'   # EXIF dimensions differ from decoded dimensions
SLOW_READ       = 'SLOW_READ'       # read succeeded but took suspiciously long
REPAIRED        = 'REPAIRED'
REPAIR_FAILED   = 'REPAIR_FAILED'
SKIPPED         = 'SKIPPED'

# Files that read back in more than this many seconds get flagged SLOW_READ
# even when their content looks healthy.  Override with --slow-threshold.
DEFAULT_SLOW_THRESHOLD = 2.0   # seconds

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ScanResult
# ---------------------------------------------------------------------------
class ScanResult:
    __slots__ = ('path', 'size', 'status', 'detail', 'duration', 'repaired_path', 'md5', 'warnings', 'read_secs')

    def __init__(self, path, size=0, status=OK, detail='', duration=0.0,
                 repaired_path=None, md5=None, warnings=None, read_secs=None):
        self.path          = path
        self.size          = size
        self.status        = status
        self.detail        = detail
        self.duration      = duration
        self.repaired_path = repaired_path
        self.md5           = md5
        self.warnings      = warnings or []   # non-fatal advisory notes
        self.read_secs     = read_secs        # wall-clock seconds for first read

    @property
    def is_corrupt(self):
        return self.status not in (OK, REPAIRED, SKIPPED, SLOW_READ)

    def __str__(self):
        tag  = f'[{self.status}]'
        line = f'{tag:<20} {self.path}'
        if self.read_secs is not None:
            line += f'  ({self.read_secs:.2f}s read)'
        if self.detail:
            line += f'\n  -> {self.detail}'
        for w in (self.warnings or []):
            line += f'\n  [WARN] {w}'
        if self.repaired_path:
            line += f'\n  -> Repaired copy: {self.repaired_path}'
        return line


# ---------------------------------------------------------------------------
# Process-tree killer
# Uses psutil when available for a thorough walk-and-kill of every
# descendant.  Falls back to plain terminate()/kill() otherwise.
# ---------------------------------------------------------------------------
def kill_process_tree(proc: multiprocessing.Process) -> None:
    """Forcibly kill proc and every child it spawned."""
    pid = proc.pid
    if pid is None:
        return

    if PSUTIL_AVAILABLE:
        try:
            parent = psutil.Process(pid)
            # Collect the whole subtree before killing anything,
            # so we don't miss grandchildren.
            children = parent.children(recursive=True)
            # Kill leaves first, then the root.
            for child in reversed(children):
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            try:
                parent.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            # Give the OS a moment to clean up handles.
            gone, still_alive = psutil.wait_procs([parent] + children, timeout=3)
            for p in still_alive:
                try:
                    p.kill()   # second attempt for anything that survived
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass  # already gone — that's fine
    else:
        # Fallback: plain multiprocessing signals
        try:
            proc.terminate()
        except Exception:
            pass
        proc.join(2)
        if proc.is_alive():
            try:
                proc.kill()
            except Exception:
                pass
            proc.join(1)


# ---------------------------------------------------------------------------
# Worker function — runs in a child PROCESS (not a thread) so it can be
# hard-killed when stuck on a bad-sector I/O wait.
#
# Results are returned via a multiprocessing.Queue instead of Manager().dict()
# so no extra manager server process is spawned (one less thing to get stuck).
#
# MUST be a module-level function — Windows spawn pickles the target and
# can only pickle module-level callables.
# ---------------------------------------------------------------------------
def _proc_target(path_str: str, repair: bool, output_dir_str: Optional[str],
                 queue: multiprocessing.Queue,
                 slow_threshold: float = DEFAULT_SLOW_THRESHOLD) -> None:
    """Entry point for the child process. Puts one result dict onto queue."""
    result = _worker_scan(path_str, repair, output_dir_str, slow_threshold)
    queue.put(result)


def _worker_scan(path_str: str, repair: bool,
                 output_dir_str: Optional[str],
                 slow_threshold: float = DEFAULT_SLOW_THRESHOLD) -> dict:
    """All scanning/repair logic runs here, inside the child process."""
    import hashlib, time
    from pathlib import Path

    path       = Path(path_str)
    output_dir = Path(output_dir_str) if output_dir_str else None
    t0         = time.perf_counter()
    warnings   = []

    def make(status, detail='', size=0, md5=None, repaired_path=None,
             read_secs=None):
        return dict(
            path=path_str, size=size, status=status, detail=detail,
            duration=time.perf_counter() - t0,
            repaired_path=str(repaired_path) if repaired_path else None,
            md5=md5, warnings=warnings, read_secs=read_secs,
        )

    # ------------------------------------------------------------------ #
    # Check 1 — Timed first read                                          #
    # ------------------------------------------------------------------ #
    t_read = time.perf_counter()
    try:
        data = path.read_bytes()
    except OSError as e:
        return make(IO_ERROR, str(e))
    read_secs = time.perf_counter() - t_read

    size = len(data)
    md5  = hashlib.md5(data).hexdigest()

    # ------------------------------------------------------------------ #
    # Check 2 — JPEG structural validation                                #
    # ------------------------------------------------------------------ #
    status, detail = _validate_jpeg_bytes(data)
    if status != OK:
        if repair and output_dir:
            dest = output_dir / path.name
            status, detail = _attempt_repair(data, dest)
            return make(status, detail, size, md5,
                        dest if status == REPAIRED else None, read_secs)
        return make(status, detail, size, md5, read_secs=read_secs)

    # ------------------------------------------------------------------ #
    # Check 3 — Pillow full decode                                        #
    # ------------------------------------------------------------------ #
    pil_status, pil_detail = _validate_with_pillow(data)
    if pil_status != OK:
        if repair and output_dir:
            dest = output_dir / path.name
            pil_status, pil_detail = _attempt_repair(data, dest)
            return make(pil_status, pil_detail, size, md5,
                        dest if pil_status == REPAIRED else None, read_secs)
        return make(pil_status, pil_detail, size, md5, read_secs=read_secs)

    # ------------------------------------------------------------------ #
    # Check 4 — Verify-read: read again and compare checksums.           #
    # Different bytes on two reads = marginal/failing sector.            #
    # ------------------------------------------------------------------ #
    try:
        data2 = path.read_bytes()
        md5_2 = hashlib.md5(data2).hexdigest()
        if md5_2 != md5:
            detail = (
                "File returned DIFFERENT data on two successive reads — "
                "strong indicator of a failing disk sector. "
                f"Read-1 MD5: {md5}  Read-2 MD5: {md5_2}"
            )
            if repair and output_dir:
                dest = output_dir / path.name
                r_status, r_detail = _attempt_repair(data, dest, raw=True)
                return make(r_status, r_detail, size, md5,
                            dest if r_status == REPAIRED else None, read_secs)
            return make(UNSTABLE_READ, detail, size, md5, read_secs=read_secs)
    except OSError as e:
        warnings.append(f"Verify-read failed (could not read file a second time): {e}")

    # ------------------------------------------------------------------ #
    # Check 5 — EXIF dimension vs decoded dimension consistency           #
    # ------------------------------------------------------------------ #
    exif_warn = _check_exif_dimensions(data)
    if exif_warn:
        warnings.append(exif_warn)

    # ------------------------------------------------------------------ #
    # Check 6 — Pixel-level anomaly detection                            #
    # Looks for large solid-colour blocks that JPEG error-concealment    #
    # fills in when scan data is missing or corrupted.                   #
    # ------------------------------------------------------------------ #
    pixel_status, pixel_detail = _check_pixel_anomalies(data)
    if pixel_status != OK:
        warnings.append(pixel_detail)

    # ------------------------------------------------------------------ #
    # Check 7 — Slow read flag                                           #
    # A healthy file that takes a long time to read is a leading         #
    # indicator of sector problems even before data loss occurs.         #
    # ------------------------------------------------------------------ #
    has_anomaly = bool(warnings)   # pixel anomaly or EXIF mismatch detected
    is_slow     = read_secs >= slow_threshold

    final_status = OK
    final_detail = 'File reads cleanly'

    if is_slow or has_anomaly:
        final_status = SLOW_READ if is_slow else OK
        parts = []
        if is_slow:
            parts.append(
                f"Read took {read_secs:.2f}s — slower than the {slow_threshold}s "
                "threshold. Sector may be degrading."
            )
        if has_anomaly:
            parts.append(
                "Pixel/EXIF anomalies detected — file likely contains "
                "error-concealment blocks from partially unreadable sectors."
            )
        parts.append("Consider backing up this file.")
        final_detail = " ".join(parts)

        # Raw repair: copy exactly what came off the disk so we preserve
        # every recoverable byte without re-encoding through Pillow.
        if repair and output_dir:
            dest = output_dir / path.name
            r_status, r_detail = _attempt_repair(data, dest, raw=True)
            return make(r_status, r_detail, size, md5,
                        dest if r_status == REPAIRED else None, read_secs)

        return make(final_status, final_detail, size, md5, read_secs=read_secs)

    # File passed all checks.  If repair mode is active, still write a
    # verified clean copy — the user explicitly requested it (common when
    # scanning a single file or wanting to migrate healthy files off a
    # failing drive alongside the damaged ones).
    if repair and output_dir:
        dest = output_dir / path.name
        r_status, r_detail = _attempt_repair(data, dest, raw=True)
        r_detail = "File is healthy; " + r_detail
        return make(r_status, r_detail, size, md5,
                    dest if r_status == REPAIRED else None, read_secs)

    return make(OK, 'File reads cleanly', size, md5, read_secs=read_secs)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def _validate_jpeg_bytes(data: bytes):
    if len(data) == 0:
        return EMPTY, "File is completely empty (0 bytes)"
    if len(data) < MIN_JPEG_SIZE:
        return TOO_SMALL, f"File is only {len(data)} bytes — too small to be a JPEG"
    if not data.startswith(JPEG_SOI):
        got = data[:2].hex().upper()
        return BAD_HEADER, f"Missing JPEG SOI marker (FF D8) — found {got} instead"
    if not data.endswith(JPEG_EOI):
        stripped = data.rstrip(b'\x00')
        if not stripped.endswith(JPEG_EOI):
            tail = data[-4:].hex().upper()
            return MISSING_EOI, (
                f"Missing JPEG EOI marker (FF D9) — last 4 bytes are {tail}. "
                "File is likely truncated."
            )
    return OK, "Basic JPEG structure intact"


def _check_exif_dimensions(data: bytes) -> str:
    """
    Returns a warning string if EXIF-reported dimensions differ from the
    actual decoded image size, or an empty string if everything is consistent.
    """
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(data)) as img:
            decoded_w, decoded_h = img.size
            exif_raw = img.info.get('exif', b'')

        if not exif_raw:
            return ''   # no EXIF to compare against

        try:
            import piexif
            exif = piexif.load(exif_raw)
            ifd  = exif.get('Exif', {})
            px_x = ifd.get(piexif.ExifIFD.PixelXDimension)
            px_y = ifd.get(piexif.ExifIFD.PixelYDimension)
            if px_x and px_y:
                if int(px_x) != decoded_w or int(px_y) != decoded_h:
                    return (
                        f"EXIF reports {px_x}x{px_y} but decoded image is "
                        f"{decoded_w}x{decoded_h} — possible partial overwrite"
                    )
        except Exception:
            pass   # piexif unavailable or EXIF unreadable — skip silently

    except Exception:
        pass   # Pillow unavailable or image unreadable — already caught elsewhere

    return ''


def _check_pixel_anomalies(data: bytes) -> tuple:
    """
    Loads the image as a numpy array and looks for telltale signs of JPEG
    error-concealment: large contiguous regions of a single solid colour
    (typically solid black or green blocks) that the decoder fills in when
    scan data is missing.

    Returns (status_code, detail_string).
    """
    try:
        import io
        import numpy as np
        from PIL import Image, ImageFilter

        with Image.open(io.BytesIO(data)) as img:
            # Convert to RGB so we always have three channels regardless of
            # source mode (grayscale, CMYK, etc.)
            rgb = img.convert('RGB')

        arr = np.array(rgb, dtype=np.float32)   # shape: H x W x 3

        h, w = arr.shape[:2]
        total_pixels = h * w

        # ---- Strategy A: tile-based solid-colour detection ----
        # Divide the image into 16x16 tiles and flag tiles where every
        # pixel is within ±2 of the tile mean (i.e. essentially flat).
        # JPEG error-concealment nearly always produces tiles that are
        # perfectly uniform (all 0,0,0 or all 0,255,0 etc.).
        tile_size   = 16
        flat_tiles  = 0
        total_tiles = 0
        for y in range(0, h - tile_size + 1, tile_size):
            for x in range(0, w - tile_size + 1, tile_size):
                tile = arr[y:y+tile_size, x:x+tile_size]
                std  = float(tile.std())
                total_tiles += 1
                if std < 2.0:
                    flat_tiles += 1

        if total_tiles > 0:
            flat_ratio = flat_tiles / total_tiles
            # More than 10% flat tiles is suspicious in a natural photo.
            if flat_ratio > 0.10:
                return (
                    PIXEL_ANOMALY,
                    f"{flat_ratio*100:.1f}% of image tiles are uniform solid colour "
                    f"({flat_tiles}/{total_tiles} tiles) — possible JPEG "
                    "error-concealment blocks from corrupt scan data"
                )

        # ---- Strategy B: channel statistics ----
        # A channel with near-zero standard deviation across the whole image
        # suggests the decoder filled it with a constant (e.g. green channel
        # all-255 is the classic Pillow error-concealment artefact).
        channel_names = ('Red', 'Green', 'Blue')
        for c, name in enumerate(channel_names):
            ch_std = float(arr[:, :, c].std())
            if ch_std < 1.0 and total_pixels > 1000:
                return (
                    PIXEL_ANOMALY,
                    f"{name} channel has near-zero variance (std={ch_std:.3f}) "
                    "across the whole image — possible decoder fill artefact"
                )

    except ImportError:
        pass   # numpy not installed — skip pixel checks silently
    except Exception:
        pass   # any other error — don't mask earlier findings

    return OK, ''


def _validate_with_pillow(data: bytes):
    try:
        from PIL import Image, UnidentifiedImageError, ImageFile
    except ImportError:
        return OK, "Pillow not available — skipping deep decode"

    import io
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.load()
        return OK, "Pillow decoded successfully"
    except UnidentifiedImageError:
        return PIL_DECODE_FAIL, "Pillow cannot identify file as a valid image"
    except OSError as e:
        msg = str(e).lower()
        if 'truncated' in msg or 'incomplete' in msg:
            return PIL_TRUNCATED, f"Pillow: image appears truncated — {e}"
        return PIL_DECODE_FAIL, f"Pillow decode error — {e}"
    except Exception as e:
        return PIL_DECODE_FAIL, f"Pillow unexpected error — {e}"


def _attempt_repair(data: bytes, dest_path, raw: bool = False):
    """
    Copy salvageable data to dest_path.

    raw=False (default, used for structural failures):
        Patch the byte stream (append EOI, strip corrupt EXIF) then verify
        with Pillow before writing.  Used when the JPEG structure itself is
        broken but the pixel data region is intact.

    raw=True (used for partial-data / pixel-anomaly / slow-read files):
        Skip re-encoding entirely.  Write the exact bytes that came off the
        disk, with only a minimal EOI fix if needed.  This preserves every
        recoverable byte — re-encoding through Pillow would discard the
        partially-decoded regions and potentially lose more data than it saves.
        The saved file will open in most viewers, showing intact regions
        normally and damaged regions as error-concealment blocks.
    """
    import io
    from pathlib import Path
    dest_path  = Path(dest_path)
    repaired   = bytearray(data)
    repair_log = []

    # Always fix a missing EOI — it's a 2-byte append and never hurts.
    if not bytes(repaired).endswith(JPEG_EOI):
        while repaired and repaired[-1] == 0x00:
            repaired.pop()
        repaired += JPEG_EOI
        repair_log.append("Appended missing EOI marker")

    if raw:
        # Raw mode: write what we have without any re-encoding.
        # Update EXIF dimensions to match what actually decoded so viewers
        # don't get confused by the mismatch.
        repaired = bytearray(_fix_exif_dimensions(bytes(repaired)) or repaired)
        if _fix_exif_dimensions(bytes(repaired)) is not None:
            repair_log.append("Updated EXIF dimensions to match decoded size")
        repair_log.append("Raw copy — original bytes preserved, no re-encoding")
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(bytes(repaired))
            return REPAIRED, "; ".join(repair_log)
        except OSError as e:
            return REPAIR_FAILED, f"Could not write raw copy — {e}"

    # Structural repair mode: try to produce a Pillow-verified clean file.
    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = False
        try:
            with Image.open(io.BytesIO(bytes(repaired))) as img:
                img.load()
        except Exception:
            no_exif = _strip_app1(bytes(repaired))
            if no_exif:
                try:
                    with Image.open(io.BytesIO(no_exif)) as img:
                        img.load()
                    repaired = bytearray(no_exif)
                    repair_log.append("Removed corrupt EXIF/APP1 segment")
                except Exception:
                    pass
    except ImportError:
        pass

    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = False
        with Image.open(io.BytesIO(bytes(repaired))) as img:
            img.load()
    except Exception as e:
        return REPAIR_FAILED, f"Could not repair — {e}"
    except ImportError:
        pass

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(bytes(repaired))
        return REPAIRED, "; ".join(repair_log) or "Repaired (structural)"
    except OSError as e:
        return REPAIR_FAILED, f"Repair ok in memory but could not write — {e}"


def _fix_exif_dimensions(data: bytes):
    """
    Rewrite the EXIF PixelXDimension / PixelYDimension tags to match the
    actual decoded image size.  Returns corrected bytes, or None if piexif
    is unavailable or the EXIF block cannot be patched.
    """
    try:
        import io, piexif
        from PIL import Image
        with Image.open(io.BytesIO(data)) as img:
            w, h     = img.size
            exif_raw = img.info.get('exif', b'')
        if not exif_raw:
            return None
        exif = piexif.load(exif_raw)
        ifd  = exif.get('Exif', {})
        ifd[piexif.ExifIFD.PixelXDimension] = w
        ifd[piexif.ExifIFD.PixelYDimension] = h
        exif['Exif'] = ifd
        new_exif = piexif.dumps(exif)
        out = io.BytesIO()
        with Image.open(io.BytesIO(data)) as img:
            piexif.insert(new_exif, data, out)
        return out.getvalue()
    except Exception:
        return None


def _strip_app1(data: bytes) -> Optional[bytes]:
    if len(data) < 4:
        return None
    out = bytearray(data[:2])
    i   = 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            break
        marker = data[i:i+2]
        if marker == JPEG_EOI:
            out += marker
            break
        if i + 4 > len(data):
            break
        seg_len = struct.unpack('>H', data[i+2:i+4])[0]
        seg_end = i + 2 + seg_len
        if marker[1] == 0xE1:
            i = seg_end
            continue
        out += data[i:seg_end]
        i = seg_end
    return bytes(out) if len(out) > 2 else None


# ---------------------------------------------------------------------------
# Folder walker
# ---------------------------------------------------------------------------
def collect_jpegs(root: Path, max_depth: Optional[int]) -> list:
    files      = []
    root_depth = len(root.parts)
    for dirpath, dirs, filenames in os.walk(root):
        depth = len(Path(dirpath).parts) - root_depth
        if max_depth is not None and depth >= max_depth:
            dirs.clear()
        for fname in filenames:
            if Path(fname).suffix.lower() in JPEG_EXTS:
                files.append(Path(dirpath) / fname)
    return files


# ---------------------------------------------------------------------------
# Incremental CSV log — one line per file, written immediately after each
# result so nothing is lost if the scan hangs or is interrupted.
# ---------------------------------------------------------------------------
CSV_FIELDS = ['index', 'filename', 'status', 'read_secs', 'size_bytes',
              'md5', 'detail', 'warnings', 'repaired_path']

def open_csv_log(csv_path: Path):
    """Open (or resume) the CSV log.  Returns (file_handle, csv.DictWriter)."""
    is_new = not csv_path.exists()
    fh = csv_path.open('a', newline='', encoding='utf-8')
    writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
    if is_new:
        writer.writeheader()
        fh.flush()
    return fh, writer


def append_csv_row(writer, fh, index: int, r: 'ScanResult') -> None:
    """Append one result row and flush immediately so the line is on disk."""
    writer.writerow({
        'index':        index,
        'filename':     r.path.name,
        'status':       r.status,
        'read_secs':    f'{r.read_secs:.3f}' if r.read_secs is not None else '',
        'size_bytes':   r.size,
        'md5':          r.md5 or '',
        'detail':       r.detail,
        'warnings':     ' | '.join(r.warnings) if r.warnings else '',
        'repaired_path': str(r.repaired_path) if r.repaired_path else '',
    })
    fh.flush()


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------
def write_report(results: list, report_path: Path, scan_root: Path,
                 elapsed: float, interrupted: bool = False):
    ok       = [r for r in results if r.status == OK]
    corrupt  = [r for r in results if r.is_corrupt]
    repaired = [r for r in results if r.status == REPAIRED]
    errors   = [r for r in results if r.status in (IO_ERROR, TIMEOUT)]

    with report_path.open('w', encoding='utf-8') as f:
        f.write("=" * 72 + "\n")
        f.write("  JPEG DISK SCAN REPORT\n")
        if interrupted:
            f.write("  *** SCAN WAS INTERRUPTED — results are partial ***\n")
        f.write(f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"  Scanned   : {scan_root}\n")
        f.write(f"  Duration  : {elapsed:.1f}s\n")
        f.write("=" * 72 + "\n\n")
        f.write("SUMMARY\n")
        f.write(f"  Total files scanned : {len(results)}\n")
        f.write(f"  OK (healthy)        : {len(ok)}\n")
        f.write(f"  Corrupt / damaged   : {len(corrupt)}\n")
        f.write(f"  Repaired copies     : {len(repaired)}\n")
        f.write(f"  I/O errors / timeout: {len(errors)}\n\n")
        if corrupt or errors:
            f.write("CORRUPT / UNREADABLE FILES\n")
            f.write("-" * 72 + "\n")
            for r in corrupt + errors:
                f.write(f"\n{r}\n")
                f.write(f"  Size : {r.size:,} bytes   MD5 : {r.md5}\n")
        else:
            f.write("No corruption found.\n")

        slow = [r for r in results if r.status == SLOW_READ]
        if slow:
            f.write("\nSLOW READS (content OK but sector may be degrading)\n")
            f.write("-" * 72 + "\n")
            for r in slow:
                f.write(f"\n{r}\n")

        warned = [r for r in results if r.warnings]
        if warned:
            f.write("\nFILES WITH WARNINGS (decoded OK but anomalies detected)\n")
            f.write("-" * 72 + "\n")
            for r in warned:
                f.write(f"\n  {r.path.name}\n")
                for w in r.warnings:
                    f.write(f"    [WARN] {w}\n")
        f.write("\nALL RESULTS\n")
        f.write("-" * 72 + "\n")
        for r in results:
            f.write(f"  [{r.status:<20}] {r.path.name}  ({r.size:,} bytes)\n")

    log.info(f"Report written to: {report_path}")


# ---------------------------------------------------------------------------
# Graceful shutdown flag
# ---------------------------------------------------------------------------
class _ShutdownFlag:
    def __init__(self):
        self._count = 0

    def increment(self):
        self._count += 1
        if self._count == 1:
            print("\n\n  [Ctrl+C] Will stop after this file finishes..."
                  "  (Press Ctrl+C again to quit immediately)\n", flush=True)
        else:
            print("\n\n  [Ctrl+C] Hard stop.\n", flush=True)

    @property
    def soft(self):
        return self._count == 1

    @property
    def hard(self):
        return self._count >= 2


_shutdown = _ShutdownFlag()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description=(
            "JPEG Disk Health Scanner & Repair Tool\n"
            "Scans a folder or single file for corrupt or damaged JPEG images.\n"
            "READ-ONLY by default — pass --repair to copy salvageable files locally.\n"
            "Run with --help for full documentation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument('target',
        help=('Path to a folder or single JPEG file to scan.  '              'Examples: E:\\Photos   or   E:\\Photos\\IMG_001.jpg'))
    ap.add_argument('--repair', action='store_true',
        help=('Enable repair mode.  Salvageable files are copied to --output '              'using the best available strategy (structural patch or raw copy). '              'The external drive is NEVER modified.'))
    ap.add_argument('--output', default=None,
        help=('Destination folder for repaired/recovered copies '              '(default: ./repaired_jpegs).  Use a path on a healthy local drive.'))
    ap.add_argument('--report', default=None,
        help=('Write a full text report to this path at the end of the scan. '              'A CSV log with the same base name is also written incrementally '              'after every file.  Example: C:\\scan_report.txt'))
    ap.add_argument('--max-depth', type=int, default=None,
        help='Limit folder recursion to N levels deep (default: unlimited).')
    ap.add_argument('--timeout', type=float, default=10.0,
        help=('Seconds to wait for a single file read before killing the worker '              'and marking the file TIMEOUT (default: 10). '              'Increase for large files or very slow drives; '              'decrease if the drive is actively failing.'))
    ap.add_argument('--slow-threshold', type=float, default=DEFAULT_SLOW_THRESHOLD,
        help=(f'Successful reads slower than this are flagged SLOW_READ '              f'(default: {DEFAULT_SLOW_THRESHOLD}s). '              'Adjust to match the normal speed of your drive.'))
    ap.add_argument('--verbose', action='store_true',
        help='Print a result line for every file, not just problems.')
    args = ap.parse_args()

    target = Path(args.target)
    if not target.exists():
        log.error(f"Path not found: {target}")
        sys.exit(1)

    if target.is_file():
        if target.suffix.lower() not in JPEG_EXTS:
            log.error(f"'{target.name}' does not look like a JPEG file "
                      f"(expected one of: {', '.join(sorted(JPEG_EXTS))})")
            sys.exit(1)
        jpegs     = [target]
        scan_root = target.parent
        log.info(f"Single-file mode: {target}")
    else:
        scan_root = target
        jpegs     = collect_jpegs(scan_root, args.max_depth)
        if not jpegs:
            log.warning("No JPEG files found in that folder.")
            sys.exit(0)
        log.info(f"Folder mode: {scan_root}")

    output_dir = None
    if args.repair:
        output_dir = Path(args.output) if args.output else Path('repaired_jpegs')
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.error(f"Cannot create output folder '{output_dir}': {e}")
            sys.exit(1)
        if target.is_file():
            log.info(f"Repair mode ON — copy will be written to: "
                     f"{output_dir / target.name}")
        else:
            log.info(f"Repair mode ON — repaired copies will go to: {output_dir}")
    else:
        log.info("Read-only scan mode (no files will be modified)")

    log.info(f"Pillow : {'available' if PIL_AVAILABLE else 'NOT installed'}  |  "
             f"psutil: {'available' if PSUTIL_AVAILABLE else 'NOT installed'}  |  "
             f"piexif: {'available' if PIEXIF_AVAILABLE else 'NOT installed'}")
    log.info("Tip: Press Ctrl+C once to stop gracefully, twice to quit immediately.\n")
    log.info(f"Found {len(jpegs)} JPEG file(s) to scan.\n")

    signal.signal(signal.SIGINT, lambda sig, frame: _shutdown.increment())

    results        = []
    interrupted    = False
    t_start        = time.perf_counter()
    output_dir_str = str(output_dir) if output_dir else None
    current_proc   = None

    # Determine the CSV log path — always written, regardless of --report.
    csv_path   = Path(args.report).with_suffix('.csv') if args.report else Path('scan_log.csv')
    csv_fh, csv_writer = open_csv_log(csv_path)
    log.info(f"Incremental CSV log: {csv_path}  (updated after every file)\n")

    try:
        for i, path in enumerate(jpegs, 1):
            if _shutdown.hard:
                log.warning("Hard stop — aborting.")
                interrupted = True
                break
            if _shutdown.soft:
                log.warning("Soft stop — halting after previous file.")
                interrupted = True
                break

            prefix = f"[{i}/{len(jpegs)}]"
            print(f"\r  {prefix} Scanning: {path.name[:70]:<70}", end='', flush=True)

            # Use a Queue instead of Manager().dict() — no extra server process.
            queue = multiprocessing.Queue()
            proc  = multiprocessing.Process(
                target=_proc_target,
                args=(str(path), args.repair, output_dir_str, queue,
                      args.slow_threshold),
                daemon=True,
            )
            current_proc = proc
            proc.start()
            proc.join(args.timeout)

            if proc.is_alive():
                # Worker is stuck (bad sector).  Kill the entire process tree
                # so no orphaned handles remain holding the drive open.
                print(f"\n  {prefix} TIMEOUT — killing worker for {path.name}", flush=True)
                kill_process_tree(proc)
                proc.join(3)   # wait for OS to confirm it's gone
                d = dict(
                    path=str(path), size=0, status=TIMEOUT,
                    detail=f"Read timed out after {args.timeout}s (bad sector?)",
                    duration=args.timeout, repaired_path=None, md5=None,
                    warnings=[], read_secs=None,
                )
            else:
                try:
                    d = queue.get_nowait()
                except Exception:
                    d = dict(
                        path=str(path), size=0, status=IO_ERROR,
                        detail="Worker exited without returning a result",
                        duration=0.0, repaired_path=None, md5=None,
                        warnings=[], read_secs=None,
                    )

            # Explicitly close and join the queue to release its pipe handles
            # before moving to the next file.
            try:
                queue.close()
                queue.join_thread()
            except Exception:
                pass

            current_proc = None

            r = ScanResult(
                path=Path(d['path']),
                size=d['size'],
                status=d['status'],
                detail=d['detail'],
                duration=d['duration'],
                repaired_path=Path(d['repaired_path']) if d['repaired_path'] else None,
                md5=d['md5'],
                warnings=d.get('warnings', []),
                read_secs=d.get('read_secs'),
            )
            results.append(r)
            append_csv_row(csv_writer, csv_fh, i, r)

            if r.is_corrupt or r.status in (IO_ERROR, TIMEOUT, REPAIRED, SLOW_READ) or args.verbose:
                print()
                level = logging.WARNING if r.is_corrupt else logging.INFO
                log.log(level, f"{prefix} {r}")

    except KeyboardInterrupt:
        print()
        log.warning("KeyboardInterrupt — stopping.")
        interrupted = True
    finally:
        if current_proc is not None and current_proc.is_alive():
            log.warning("Cleaning up worker process...")
            kill_process_tree(current_proc)
            current_proc.join(3)
        try:
            csv_fh.close()
        except Exception:
            pass

    elapsed = time.perf_counter() - t_start
    print()

    ok_count       = sum(1 for r in results if r.status == OK)
    corrupt_count  = sum(1 for r in results if r.is_corrupt)
    repaired_count = sum(1 for r in results if r.status == REPAIRED)
    error_count    = sum(1 for r in results if r.status in (IO_ERROR, TIMEOUT))
    slow_count     = sum(1 for r in results if r.status == SLOW_READ)
    warning_count  = sum(1 for r in results if r.warnings)

    banner = "SCAN INTERRUPTED — PARTIAL RESULTS" if interrupted else "SCAN COMPLETE"
    print("\n" + "=" * 60)
    print(f"  {banner}")
    print(f"  Total scanned  : {len(results)}  (of {len(jpegs)} found)")
    print(f"  Healthy (OK)   : {ok_count}")
    print(f"  Corrupt/damaged: {corrupt_count}")
    print(f"  Repaired copies: {repaired_count}")
    print(f"  I/O errors     : {error_count}")
    print(f"  Slow reads     : {slow_count}  (>{args.slow_threshold}s)")
    print(f"  Warnings       : {warning_count}  (EXIF/pixel anomalies)")
    print(f"  Time           : {elapsed:.1f}s")
    print("=" * 60)

    if args.report:
        write_report(results, Path(args.report), scan_root, elapsed, interrupted)
    elif interrupted and results:
        auto_report = Path('scan_partial_report.txt')
        write_report(results, auto_report, scan_root, elapsed, interrupted=True)
        log.info(f"Partial results auto-saved to: {auto_report}")

    sys.exit(0 if (corrupt_count + error_count) == 0 else 1)


if __name__ == '__main__':
    main()