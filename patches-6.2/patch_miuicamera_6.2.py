#!/usr/bin/env python3
"""
Reproducible DEX patcher for HyperOS Leica Camera 6.2 (1+6.2.000360.1)
on Xiaomi SM8450 / SM8475 / SM7475 devices (cupid, zeus, mayfly, unicorn, thor).

Input APK: MiuiCamera.apk from zeus-hyperos-leica-camera v1.0
(already includes base beautify/zoom/vendor-tag/portrait patches for SM8450).

Applies:
  1. classes3.dex: Ultra-wide minimum zoom 0.5f -> 0.625f (cupid, mayfly) / 0.65625f (unicorn)
     in i1(), n1(), q0() so 0.6x matches HAL zoom limits.
  2. classes3.dex: device_common.l3() -> return true (was: this instanceof fuxi)
     so EffectController enables CvStyleFilterRender + CvShadingRender.
  3. classes2.dex: pb.d0.a1() default pb_leica_key true -> false
     so GPU Leica Authentic LUT + vignette runs by default on non-Leica HALs (cupid).
  4. classes5.dex: Gb.c.i() when focal <= 0 (HAL lacks com.xiaomi.sensor.info.focalLength35mm)
     fall back to 23mm instead of clearing the entire EXIF watermark line.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
import zipfile
import zlib

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
]


def fix_dex_header(data: bytearray) -> None:
    data[12:32] = hashlib.sha1(data[32:]).digest()
    data[8:12] = zlib.adler32(bytes(data[12:])).to_bytes(4, "little")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_apk", required=True, help="Input MiuiCamera.apk (zeus-hyperos-leica-camera v1.0)")
    ap.add_argument("--out", dest="out_apk", required=True, help="Output patched MiuiCamera.apk")
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
