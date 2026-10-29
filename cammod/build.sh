#!/bin/bash
# Builds the CamMod classes and writes their smali into the decoded camera APK.
# Usage: build.sh <rising source root> <apktool-decoded camera dir>
set -euo pipefail
ROOT=${1:?rising source root}
APK=${2:?decoded camera dir}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

JDK=$ROOT/prebuilts/jdk/jdk21/linux-x86/bin
ANDROID_JAR=$ROOT/prebuilts/sdk/current/public/android.jar
D8=$ROOT/out/host/linux-x86/bin/d8
BAKSMALI=$ROOT/prebuilts/extract-tools/common/smali/baksmali.jar

python3 -I "$HERE/gen_i18n.py"

# Stubs only satisfy javac; the camera provides the real classes at runtime.
mkdir -p "$OUT/stubs" "$OUT/classes" "$OUT/dex"
"$JDK/javac" -nowarn --release 11 -d "$OUT/stubs" -classpath "$ANDROID_JAR" \
    $(find "$HERE/stubs" -name '*.java')
"$JDK/javac" -Xlint:-options --release 11 -d "$OUT/classes" -classpath "$ANDROID_JAR:$OUT/stubs" \
    $(find "$HERE/src" -name '*.java')

"$D8" --release --min-api 29 --lib "$ANDROID_JAR" --classpath "$OUT/stubs" \
    --output "$OUT/dex" $(find "$OUT/classes" -name '*.class')

rm -rf "$APK/smali_classes8"
"$JDK/java" -jar "$BAKSMALI" d -o "$APK/smali_classes8" "$OUT/dex/classes.dex"
find "$APK/smali_classes8" -name '*.smali' | sort
