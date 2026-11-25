#!/usr/bin/env python3
"""
Reproducible DEX/Smali patcher for HyperOS Leica Camera 6.2 (1+6.2.000360.1)
on Xiaomi SM8450 / SM8475 / SM7475 devices (cupid, zeus, mayfly, unicorn, thor).

Input APK: MiuiCamera.apk from zeus-hyperos-leica-camera v1.0
(already includes base beautify/zoom/vendor-tag/portrait patches for SM8450).

Applies:
  1. classes3.dex: Ultra-wide minimum zoom 0.5f -> 0.625f (cupid, mayfly) / 0.65625f (unicorn)
     in i1(), n1(), q0() so 0.6x matches HAL zoom limits.
  2. classes3.dex & classes2.dex: Enable GPU Leica Authentic engine (CvStyleFilterRender +
     CvShadingRender) on non-Leica HALs (cupid).
  3. classes5.dex: Gb.c.i() fallback to 23mm focal length when HAL lacks focalLength35mm.
  4. classes2.dex: w5.s0.x() fix Ultra HD (50MP) QCFA stream selection when remosaic=false
     while keeping Portrait stream fallback.
  5. classes.dex: Add in-app Monet dynamic color switch ("pref_monet_color_key") and
     disable manual color picker when active.
  6. classes.dex, classes2.dex, classes6.dex: Dynamically tint all camera switches
     (SlidingButton, SlidingSwitch, SlidingSwitchCompat, ToggleSwitch) with Monet when
     active or Leica/Camera color when disabled.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
import zipfile
import zlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BYTE_PATCHES = [
    # --- 1. SM8450/SM8475 ultra-wide min zoom (0.5f -> 0.625f / 0.65625f) ---
    ("classes3.dex", 0x72a636, "1500003f", "1500203f", "cupid.i1(): UW min zoom 0.5f -> 0.625f"),
    ("classes3.dex", 0x72a9ca, "1500003f", "1500203f", "cupid.n1(): UW min zoom 0.5f -> 0.625f"),
    ("classes3.dex", 0x72ab8a, "1500003f", "1500203f", "cupid.q0(): UW min zoom 0.5f -> 0.625f"),
    ("classes3.dex", 0x746142, "1500003f", "1500203f", "mayfly.i1(): UW min zoom 0.5f -> 0.625f"),
    ("classes3.dex", 0x7464d6, "1500003f", "1500203f", "mayfly.n1(): UW min zoom 0.5f -> 0.625f"),
    ("classes3.dex", 0x746696, "1500003f", "1500203f", "mayfly.q0(): UW min zoom 0.5f -> 0.625f"),
    ("classes3.dex", 0x767fa2, "1500003f", "1500283f", "unicorn.i1(): UW min zoom 0.5f -> 0.65625f"),
    ("classes3.dex", 0x768336, "1500003f", "1500283f", "unicorn.n1(): UW min zoom 0.5f -> 0.65625f"),
    ("classes3.dex", 0x7684f6, "1500003f", "1500283f", "unicorn.q0(): UW min zoom 0.5f -> 0.65625f"),

    # --- 2. Enable GPU Leica Authentic engine (CvStyleFilterRender + CvShadingRender) ---
    ("classes3.dex", 0x7303e8, "20003b23", "12100000", "device_common.l3(): instance-of fuxi -> return true"),
    ("classes2.dex", 0x8312b0, "1212", "1202", "pb.d0.a1(): default pb_leica_key true -> false"),

    # --- 3. Leica watermark EXIF fallback when HAL lacks focalLength35mm ---
    ("classes5.dex", 0x3c95da, "5b7402040e00", "1308170028f1", "Gb.c.i(): focal<=0 fallback to 23mm instead of blanking EXIF"),

    # --- 4. Fix Ultra HD (50MP) QCFA stream selection while keeping Portrait fallback ---
    ("classes2.dex", 0x897b6a, "280d000055d2e2e138020300280712526e208fe325000c022805", "39020d0055d2e2e13902090012526e208fe325000c0239020600", "w5.s0.x(): use stream 5 when remosaic=false, fallback to stream 1 only if null"),
]

SMALI_DEX_MAP = {
    "classes.dex": "smali",
    "classes2.dex": "smali_classes2",
    "classes6.dex": "smali_classes6",
}

SMALI_PATCH_FILES = [
    "0005-add-monet-dynamic-color-switch.patch",
    "0006-switches-follow-leica-or-monet.patch",
]


def fix_dex_header(data: bytearray) -> None:
    data[12:32] = hashlib.sha1(data[32:]).digest()
    data[8:12] = zlib.adler32(bytes(data[12:])).to_bytes(4, "little")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_apk", required=True, help="Input MiuiCamera.apk (zeus-hyperos-leica-camera v1.0)")
    ap.add_argument("--out", dest="out_apk", required=True, help="Output patched MiuiCamera.apk")
    ap.add_argument("--baksmali", required=True, help="Path to baksmali.jar")
    ap.add_argument("--smali", required=True, help="Path to smali.jar")
    ap.add_argument("--zipalign", default="zipalign", help="Path to zipalign binary")
    args = ap.parse_args()

    by_dex = {}
    for dex, off, old_hex, new_hex, desc in BYTE_PATCHES:
        by_dex.setdefault(dex, []).append((off, bytes.fromhex(old_hex), bytes.fromhex(new_hex), desc))

    work = tempfile.mkdtemp(prefix="miuicamera_6.2_")
    try:
        patched = {}
        with zipfile.ZipFile(args.in_apk, "r") as zin:
            for dex, items in by_dex.items():
                buf = bytearray(zin.read(dex))
                for off, old, new, desc in items:
                    cur = bytes(buf[off:off + len(old)])
                    if cur != old:
                        raise RuntimeError(f"{dex} @ {hex(off)}: expected {old.hex()}, got {cur.hex()} ({desc})")
                    buf[off:off + len(new)] = new
                    print(f"[OK] {dex} @ {hex(off)}: {desc}")
                fix_dex_header(buf)
                patched[dex] = bytes(buf)

            # Disassemble DEX files touched by smali patches
            smali_root = os.path.join(work, "smali_tree")
            os.makedirs(smali_root, exist_ok=True)
            for dex_name, dir_name in SMALI_DEX_MAP.items():
                dex_bytes = patched.get(dex_name) or zin.read(dex_name)
                dex_path = os.path.join(work, dex_name)
                with open(dex_path, "wb") as f:
                    f.write(dex_bytes)
                subprocess.run(
                    ["java", "-jar", args.baksmali, "d", dex_path, "-o", os.path.join(smali_root, dir_name)],
                    check=True,
                )

            # Apply unified smali patches (0005, 0006)
            for patch_file in SMALI_PATCH_FILES:
                patch_path = os.path.join(SCRIPT_DIR, patch_file)
                with open(patch_path, "rb") as pf:
                    subprocess.run(["patch", "-d", smali_root, "-p1"], stdin=pf, check=True)
                print(f"[OK] Applied {patch_file}")

            # Reassemble patched smali directories back to DEX
            for dex_name, dir_name in SMALI_DEX_MAP.items():
                out_dex = os.path.join(work, f"rebuilt_{dex_name}")
                subprocess.run(
                    ["java", "-jar", args.smali, "a", "-a", "29", os.path.join(smali_root, dir_name), "-o", out_dex],
                    check=True,
                )
                with open(out_dex, "rb") as f:
                    patched[dex_name] = f.read()

            unaligned = os.path.join(work, "unaligned.apk")
            with zipfile.ZipFile(unaligned, "w") as zout:
                for info in zin.infolist():
                    zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                    zi.external_attr = info.external_attr
                    if info.filename in patched:
                        zi.compress_type = zipfile.ZIP_STORED
                        zout.writestr(zi, patched[info.filename])
                    else:
                        zi.compress_type = info.compress_type
                        zout.writestr(zi, zin.read(info.filename))

        subprocess.run([args.zipalign, "-f", "-P", "16", "4", unaligned, args.out_apk], check=True)
        print(f"[DONE] Wrote {args.out_apk}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
