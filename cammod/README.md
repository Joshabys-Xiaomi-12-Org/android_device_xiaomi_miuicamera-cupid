# Modded by acerhizm (CamMod)

Settings and feature switches added to MIUI Camera: Leica UI, colorful mode icons, eye
tracking focus, super JPEG, max brightness, custom theme color and switch color, device
watermark text, black Leica watermark, live photo, India filters, 1/8000 shutter, 10x zoom
in video modes, Director mode, lab options, and lab switches for subtitles, render engine
v2, 55 ms burst and Dolby Vision video. Strings ship in all 80 camera locales.

`patches/0008-Add-the-Modded-by-acerhizm-camera-mod.patch` is the result of this
directory; extract-files.py applies it like the other patches.

## Regenerating patch 0008

1. Decode the camera APK with patches 0001-0007 applied
   (`apktool d -r MiuiCamera.apk -o apk`) and commit that tree as the base.
2. `python3 -I hooks.py apk` applies the smali hooks; every hook matches its original text
   exactly once and fails loudly otherwise.
3. `./build.sh <rising source root> apk` compiles `src/` against `stubs/` (javac, d8,
   baksmali) into `apk/smali_classes8` and regenerates `I18n.java` from `i18n/`.
4. Diff the smali directories against the base to get the new patch.

Translations: `i18n/en*.json` hold the English strings, the other files the 79 locales.
