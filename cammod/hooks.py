#!/usr/bin/env python3
"""Applies the CamMod smali hooks to an apktool-decoded MiuiCamera (run with python3 -I).

Every edit names the exact original text and must match exactly once, so a camera
update that moves any of these lines fails loudly instead of patching the wrong place.
"""
import os
import re
import sys

APK = sys.argv[1]
CM = 'Lorg/acerhizm/cammod/CamMod;'

# Obfuscated profile classes, decrypted names in comments (XOR, prefix com.mi.device.).
ZEUS = 'smali_classes4/緹緵緷綴緷緳綴緾緿緬緳緹緿綴緀緿緯緩.smali'    # com.mi.device.Zeus
COMMON = 'smali_classes4/弜弐弒彑弒弖彑弛弚弉弖弜弚彑弼弐弒弒弐弑.smali'  # com.mi.device.Common


def find_class(name):
    for root, _, files in os.walk(APK):
        for f in files:
            if not f.endswith('.smali'):
                continue
            p = os.path.join(root, f)
            with open(p, encoding='utf-8') as h:
                if h.readline().split()[-1] == name:
                    return os.path.relpath(p, APK)
    sys.exit(f'class {name} not found')


def edit(rel, old, new):
    p = os.path.join(APK, rel)
    with open(p, encoding='utf-8') as f:
        t = f.read()
    n = t.count(old)
    if n != 1:
        sys.exit(f'{rel}: expected 1 match, found {n}:\n{old}')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(t.replace(old, new))
    print(f'hooked {rel}')


def add_methods(rel, body):
    p = os.path.join(APK, rel)
    with open(p, encoding='utf-8') as f:
        t = f.read()
    for name in re.findall(r'^\.method public (\w+)\(', body, re.M):
        if re.search(r'^\.method [^\n]* ' + name + r'\(\)', t, re.M):
            sys.exit(f'{rel}: {name} already defined')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(t.rstrip('\n') + '\n' + body)
    print(f'extended {rel}')


def getter(name, ret, helper):
    return (f'\n.method public {name}(){ret}\n    .locals 0\n\n'
            f'    invoke-static {{}}, {CM}->{helper}(){ret}\n\n    move-result p0\n\n'
            f'    return p0\n.end method\n')


# 1. Leica theme on zeus: the values of com.mi.device.Unicorn (Xiaomi 12S Pro) when on,
#    the Common defaults when off. Q6() = k4 && E1 > 0 && Z == 0 picks the Leica (Madrid) theme.
add_methods(ZEUS, getter('E1', 'I', 'leicaThemeCount') + getter('Z', 'I', 'leicaThemeIndex')
            + getter('j4', 'Z', 'leica') + getter('k4', 'Z', 'leica'))

# 2. Colourful More-mode icons by default (pref_more_mode_tab_style 1); stock is !leica.
edit(find_class('Lt0/g;'),
     '    move-result p1\n\n    xor-int/2addr p1, v2\n\n    iput p1, p0, Lt0/g;->z:I\n',
     '    move-result p1\n\n    const/4 p1, 0x1\n\n    iput p1, p0, Lt0/g;->z:I\n')

# 3. SUPER (100) JPEG quality: Common.x8() caps v2.g0() at HIGH; no profile overrides it.
edit(COMMON,
     '.method public x8()Z\n    .locals 0\n\n    const/4 p0, 0x0\n\n    return p0\n.end method',
     f'.method public x8()Z\n    .locals 0\n\n    invoke-static {{}}, {CM}->superJpeg()Z\n\n'
     '    move-result p0\n\n    return p0\n.end method')

# 4. Maximum brightness: the value Camera.hn() restores to, and every resume.
edit('smali/com/android/camera/Camera.smali',
     '    const/high16 v0, -0x40800000    # -1.0f\n\n    :goto_0\n',
     f'    const/high16 v0, -0x40800000    # -1.0f\n\n    :goto_0\n'
     f'    invoke-static {{v0}}, {CM}->brightness(F)F\n\n    move-result v0\n\n')
# After Aj(): p0 is still the activity; the lines below reuse p0 for a log string.
edit('smali/com/android/camera/ActivityBase.smali',
     '    invoke-virtual {p0}, Lcom/android/camera/ActivityBase;->Aj()V\n\n'
     '    const-string p0, "onResume - version: 5.3.001580.0"\n',
     '    invoke-virtual {p0}, Lcom/android/camera/ActivityBase;->Aj()V\n\n'
     f'    invoke-static {{p0}}, {CM}->applyBrightness(Landroid/app/Activity;)V\n\n'
     '    const-string p0, "onResume - version: 5.3.001580.0"\n')

# 5. Theme colour: n0/f.k is fixed once in <clinit> and overrides pref_tint_color.
edit('smali/n0/f.smali',
     '    :goto_0\n    sput v0, Ln0/f;->k:I\n',
     f'    :goto_0\n    invoke-static {{v0}}, {CM}->themeColor(I)I\n\n    move-result v0\n\n'
     '    sput v0, Ln0/f;->k:I\n')

# 6. Device watermark text from the zeus profile ("Xiaomi" / "12 PRO").
edit(ZEUS,
     '    invoke-virtual {p0, v3, v1}, Landroid/util/SparseArray;->put(ILjava/lang/Object;)V\n\n'
     '    return-object p0\n',
     '    invoke-virtual {p0, v3, v1}, Landroid/util/SparseArray;->put(ILjava/lang/Object;)V\n\n'
     f'    invoke-static {{p0}}, {CM}->watermark(Landroid/util/SparseArray;)Landroid/util/SparseArray;\n\n'
     '    move-result-object p0\n\n    return-object p0\n')

# 7. Lab options: w3() returns camera.lab.options, read once in mb/b's static init, which can
#    run before any context exists. Ask CamMod at each call instead.
edit('smali_classes3/mb/b.smali',
     '.method public w3()Z\n    .locals 0\n\n    sget-boolean p0, Lmb/b;->s:Z\n\n    return p0\n',
     '.method public w3()Z\n    .locals 0\n\n    sget-boolean p0, Lmb/b;->s:Z\n\n'
     f'    invoke-static {{p0}}, {CM}->labOr(Z)Z\n\n    move-result p0\n\n    return p0\n')
#    The lab section's hint toast only exists in 5 locales; show ours.
edit('smali/com/android/camera/fragment/settings/CameraPreferenceFragment.smali',
     '    const v2, 0x7f140268\n\n'
     '    invoke-static {v0, v2, v1}, Lcom/android/camera/q5;->d(Landroid/content/Context;IZ)V\n',
     '    const v2, 0x7f140268\n\n'
     f'    invoke-static {{v0, v2, v1}}, {CM}->labHint(Landroid/content/Context;IZ)V\n')

# 8. Black Leica watermark: the app's own black-background mode, read only by Leica.smali.
edit('smali_classes2/com/android/camera2/compat/theme/custom/cv/cvwatermark/CvWatermarkParam.smali',
     '    iget-boolean p0, p0, Lcom/android/camera2/compat/theme/custom/cv/cvwatermark/CvWatermarkParam;'
     '->isWhiteBackground:Z\n\n    return p0\n',
     '    iget-boolean p0, p0, Lcom/android/camera2/compat/theme/custom/cv/cvwatermark/CvWatermarkParam;'
     '->isWhiteBackground:Z\n\n    if-eqz p0, :cm_ret\n\n'
     f'    invoke-static {{}}, {CM}->blackLeica()Z\n\n    move-result p0\n\n'
     '    xor-int/lit8 p0, p0, 0x1\n\n    :cm_ret\n    return p0\n')

# 9. Live photo (Dynamic shots): G6() hides it on global builds; patch 0002 makes every build global.
edit('smali_classes3/mb/b.smali',
     '.method public G6()Z\n    .locals 1\n\n    invoke-static {}, Lmb/c;->e()Z\n\n    move-result v0\n',
     '.method public G6()Z\n    .locals 1\n\n    invoke-static {}, Lmb/c;->e()Z\n\n    move-result v0\n\n'
     f'    invoke-static {{v0}}, {CM}->livePhotoGlobal(Z)Z\n\n    move-result v0\n')

# 11. Switch colour: every miuix SlidingButton tints its "on" bar with slidingBarColor (sp/b.d,
#     blue by default) in sp/b.x(), after loading it; replace that colour.
edit('smali_classes5/sp/b.smali',
     '    invoke-virtual {p2, v0, p1}, Landroid/content/res/TypedArray;->getColor(II)I\n\n'
     '    move-result p1\n\n    iput p1, p0, Lsp/b;->d:I\n',
     '    invoke-virtual {p2, v0, p1}, Landroid/content/res/TypedArray;->getColor(II)I\n\n'
     '    move-result p1\n\n'
     f'    invoke-static {{p1}}, {CM}->switchBarColor(I)I\n\n    move-result p1\n\n'
     '    iput p1, p0, Lsp/b;->d:I\n')

# 10. Settings: our category at the end of BasePreferenceFragment.xi(). It must come after
#     Bi() (sets the fragment as listener of every preference) and Di() (loads checked
#     states from the camera's prefs), or both would overwrite our preferences.
#     CamMod.addSettings() only acts on CameraPreferenceFragment.
edit('smali/com/android/camera/fragment/settings/BasePreferenceFragment.smali',
     '    invoke-virtual {p0, v0, v1}, Lcom/android/camera/fragment/settings/BasePreferenceFragment;'
     '->Di(Landroidx/preference/PreferenceGroup;Landroid/content/SharedPreferences;)V\n\n'
     '    :goto_1\n    return-void\n',
     '    invoke-virtual {p0, v0, v1}, Lcom/android/camera/fragment/settings/BasePreferenceFragment;'
     '->Di(Landroidx/preference/PreferenceGroup;Landroid/content/SharedPreferences;)V\n\n'
     f'    invoke-static {{p0}}, {CM}->addSettings(Landroidx/preference/PreferenceFragmentCompat;)V\n\n'
     '    :goto_1\n    return-void\n')

# 12. India filters appended to the normal and beauty lists (the stock India flag replaces
#     them and also swaps AI/beauty LUTs). p0 is still `this` right after super.initialize().
edit('smali_classes2/com/android/camera2/compat/theme/custom/cv/filter/EffectControllerCv.smali',
     '    invoke-super {p0}, Lcom/android/camera/effect/b;->initialize()V\n',
     '    invoke-super {p0}, Lcom/android/camera/effect/b;->initialize()V\n\n'
     f'    invoke-static {{p0}}, {CM}->indiaFilters(Lcom/android/camera/effect/b;)V\n')

# 13. File pickers: the teleprompter text and Log LUT imports target the Mi file manager,
#     which is not in the ROM, so the uncaught ActivityNotFoundException crashed the camera.
PROMPTER = 'smali/com/android/camera/fragment/videoprompter/FragmentVideoPrompterEdit.smali'
edit(PROMPTER,
     '    const v1, 0x8c36\n\n'
     '    invoke-virtual {p0, v0, v1}, Landroidx/fragment/app/Fragment;->startActivityForResult(Landroid/content/Intent;I)V\n',
     '    const v1, 0x8c36\n\n'
     f'    invoke-static {{p0, v0, v1}}, {CM}->pickFile(Landroidx/fragment/app/Fragment;Landroid/content/Intent;I)V\n')
edit('smali_classes2/com/android/camera2/compat/theme/custom/mm/beauty/FragmentMasterFilterMM2.smali',
     '    const v1, 0x8c37\n\n'
     '    invoke-virtual {p0, v0, v1}, Landroidx/activity/ComponentActivity;->startActivityForResult(Landroid/content/Intent;I)V\n',
     '    const v1, 0x8c37\n\n'
     f'    invoke-static {{p0, v0, v1}}, {CM}->pickFile(Landroid/app/Activity;Landroid/content/Intent;I)V\n')
#     Picker URIs (Downloads, Recent) carry no file name: take it from the display name.
edit(PROMPTER,
     '    invoke-virtual {v0, v1}, Ljava/lang/String;->substring(I)Ljava/lang/String;\n\n'
     '    move-result-object v0\n\n    const v1, 0x7f140cb8\n',
     '    invoke-virtual {v0, v1}, Ljava/lang/String;->substring(I)Ljava/lang/String;\n\n'
     '    move-result-object v0\n\n'
     f'    invoke-static {{p1, v0}}, {CM}->pickedExt(Landroid/net/Uri;Ljava/lang/String;)Ljava/lang/String;\n\n'
     '    move-result-object v0\n\n    const v1, 0x7f140cb8\n')
edit('smali_classes2/o6/c0.smali',
     '    invoke-virtual {p1}, Landroid/net/Uri;->getPath()Ljava/lang/String;\n\n    move-result-object v3\n',
     '    invoke-virtual {p1}, Landroid/net/Uri;->getPath()Ljava/lang/String;\n\n    move-result-object v3\n\n'
     f'    invoke-static {{p1, v3}}, {CM}->pickedPath(Landroid/net/Uri;Ljava/lang/String;)Ljava/lang/String;\n\n'
     '    move-result-object v3\n')

# 14. Video subtitles: S7() hides them on global builds; only this check is relaxed.
edit('smali_classes3/mb/b.smali',
     '.method public S7()Z\n    .locals 1\n\n    invoke-static {}, Lmb/c;->e()Z\n\n    move-result v0\n',
     '.method public S7()Z\n    .locals 1\n\n    invoke-static {}, Lmb/c;->e()Z\n\n    move-result v0\n\n'
     f'    invoke-static {{v0}}, {CM}->subtitlesGlobal(Z)Z\n\n    move-result v0\n')

# 15. Render engine v2 + Pro video Log LUT (profile P5) and the 55 ms fixed burst (profile O0).
edit(COMMON,
     '.method public P5()Z\n    .locals 0\n\n    const/4 p0, 0x0\n\n    return p0\n.end method',
     f'.method public P5()Z\n    .locals 0\n\n    invoke-static {{}}, {CM}->renderV2()Z\n\n'
     '    move-result p0\n\n    return p0\n.end method')
edit(COMMON,
     '.method public O0()J\n    .locals 2\n\n    const-wide/16 v0, -0x1\n\n    return-wide v0\n.end method',
     f'.method public O0()J\n    .locals 2\n\n    invoke-static {{}}, {CM}->burstInterval()J\n\n'
     '    move-result-wide v0\n\n    return-wide v0\n.end method')

# 16. Pro shutter down to 1/8000: Common.G1 holds "mode:minNs:maxNs;..." (Zeus has no G1).
G1 = ('    const-string p0, "167:250000:30000000000;180:250000:125000000;'
      '164:250000:125000000;169:250000:30000000000"\n\n')
edit(COMMON, G1 + '    return-object p0\n',
     G1 + f'    invoke-static {{p0}}, {CM}->shutterRange(Ljava/lang/String;)Ljava/lang/String;\n\n'
     '    move-result-object p0\n\n    return-object p0\n')

# 17. 10x zoom outside Photo: the 6.0f caps in e9/w (ZoomManager). Left alone on purpose:
#     Sa (4K@120), Oa (slow motion main lens, HFR) and the fixed [1,6] range of multicam etc.
ZOOM = 'smali_classes2/e9/w.smali'
SIX = '0x40c00000    # 6.0f\n'


def cap6(reg, after, before=''):
    six = f'{before}    const/high16 {reg}, {SIX}'
    edit(ZOOM, six + after,
         six + f'\n    invoke-static {{{reg}}}, {CM}->maxZoom(F)F\n\n    move-result {reg}\n' + after)


cap6('p0', '\n    invoke-static {p1}, Lg9/g;->a0(Lg9/f;)F\n\n    move-result p1\n\n'
     '    invoke-static {p0, p1}, Ljava/lang/Math;->min(FF)F\n')                     # A2: video HDR
cap6('v3', '\n    invoke-static {v3, v2}, Ljava/lang/Math;->min(FF)F\n')            # A9: video refresh
cap6('p1', '\n    cmpg-float v0, p0, p1\n')                                          # F2: video default
cap6('v0', '\n    invoke-static {p1}, Lg9/g;->a0(Lg9/f;)F\n',
     before='    if-eqz v0, :cond_0\n\n')                                           # Y4: lightweight video
cap6('v0', '\n    invoke-static {v0, p0}, Ljava/lang/Math;->min(FF)F\n')            # m3: ultra tele
cap6('v2', '\n    invoke-static {v2, v0}, Ljava/lang/Math;->min(FF)F\n')            # t9: video refresh
cap6('p0', '\n    invoke-static {p2}, Lg9/g;->a0(Lg9/f;)F\n')                        # w4: Pro video main

# 18. Pocket mode: Zeus A5 = 0 hides the camera's own "Pocket mode" setting
#     (pref_camera_proximity_lock_key); that setting is the switch.
edit(ZEUS, '.method public A5()Z\n    .locals 0\n\n    const/4 p0, 0x0\n\n    return p0\n.end method',
     '.method public A5()Z\n    .locals 0\n\n    const/4 p0, 0x1\n\n    return p0\n.end method')

# 19. Dolby Vision ("true colour") video: profile Y6 adds it to Settings → Video.
add_methods(ZEUS, getter('Y6', 'Z', 'trueColor'))


# 20. Director mode: Common.n2() = 0 and no profile overrides it. Read once per process
#     (p2/a builds the module registry once), so the setting needs a restart.
add_methods(ZEUS, getter('n2', 'Z', 'director'))

# 21. Director network callback: u2/s.gq() runs on every camera open of the module
#     (Wj via i0.Oa, also on resume and lens switch) and registered a new Wi-Fi callback each
#     time; only the last one was unregistered (TooManyRequestsException after ~100).
#     Register once per module, and only when multicam (MiConnect) can work at all: the
#     callback only feeds FragmentCinemasterProcess.onWiFiLost and u0/i1.O1 (multicam state).
edit('smali/u2/s.smali',
     '.method public final gq()V\n    .locals 3\n\n'
     '    iget-object v0, p0, Ly5/i0;->q:Lcom/android/camera/Camera;\n',
     '.method public final gq()V\n    .locals 3\n\n'
     '    iget-object v0, p0, Lu2/s;->ja:Landroid/net/ConnectivityManager$NetworkCallback;\n\n'
     '    if-nez v0, :cm_skip\n\n'
     '    const/4 v0, 0x1\n\n'
     f'    invoke-static {{v0}}, {CM}->multicam(Z)Z\n\n'
     '    move-result v0\n\n'
     '    if-nez v0, :cm_reg\n\n'
     '    :cm_skip\n    return-void\n\n'
     '    :cm_reg\n'
     '    iget-object v0, p0, Ly5/i0;->q:Lcom/android/camera/Camera;\n')

# 22. Hide "Multicam setup" (config item 0x91 and top-bar button) without MiConnect.
edit('smali/u2/f.smali',
     '    invoke-virtual {v0}, Lmb/b;->M2()Z\n\n    move-result v0\n\n    if-eqz v0, :cond_5\n',
     '    invoke-virtual {v0}, Lmb/b;->M2()Z\n\n    move-result v0\n\n'
     f'    invoke-static {{v0}}, {CM}->multicam(Z)Z\n\n    move-result v0\n\n'
     '    if-eqz v0, :cond_5\n')
edit('smali/u2/f.smali',
     '    invoke-virtual {v2}, Lmb/b;->M2()Z\n\n    move-result v2\n\n    if-eqz v2, :cond_2\n',
     '    invoke-virtual {v2}, Lmb/b;->M2()Z\n\n    move-result v2\n\n'
     f'    invoke-static {{v2}}, {CM}->multicam(Z)Z\n\n    move-result v2\n\n'
     '    if-eqz v2, :cond_2\n')
#     The first-use guide on entering Director only explains multicam.
edit('smali_classes2/com/android/camera2/compat/theme/custom/mm/cinemaster/FragmentCinemasterProcess.smali',
     '    const-string v1, "pref_camera_first_cine_master_use_hint_shown_key"\n\n'
     '    const/4 v2, 0x1\n\n'
     '    invoke-virtual {v0, v1, v2}, Lcom/android/camera/data/data/g;->getBoolean(Ljava/lang/String;Z)Z\n\n'
     '    move-result v0\n\n    return v0\n',
     '    const-string v1, "pref_camera_first_cine_master_use_hint_shown_key"\n\n'
     '    const/4 v2, 0x1\n\n'
     '    invoke-virtual {v0, v1, v2}, Lcom/android/camera/data/data/g;->getBoolean(Ljava/lang/String;Z)Z\n\n'
     '    move-result v0\n\n'
     f'    invoke-static {{v0}}, {CM}->multicam(Z)Z\n\n    move-result v0\n\n'
     '    return v0\n')

# 23. Log LUT import from Director: the 0x8c37 result is cast to o6/c0 (Pro video module)
#     unconditionally -> ClassCastException when the current module is u2/s. Ignore it there.
edit('smali/com/android/camera/ActivityBase.smali',
     '    iget-object p0, p0, Lcom/android/camera/ActivityBase;->e:Ly5/v4;\n\n'
     '    if-eqz p0, :cond_0\n\n    check-cast p0, Lo6/c0;\n',
     '    iget-object p0, p0, Lcom/android/camera/ActivityBase;->e:Ly5/v4;\n\n'
     '    instance-of v0, p0, Lo6/c0;\n\n'
     '    if-eqz v0, :cond_0\n\n    check-cast p0, Lo6/c0;\n')

# 24. Saved mode 0xa4 after Director is switched off: Camera.tl() throws
#     "invalid module index 164" and SplashProvider.d() NPEs on every start. Map it to
#     Photo (0xa3, the default) where the mode is read, like the stock 0xa5 -> 0xa3 migration below.
edit(find_class('Lt0/g;'),
     '    invoke-virtual {p0, v0, v2}, Lcom/android/camera/data/data/g;->getInt(Ljava/lang/String;I)I\n\n'
     '    move-result v0\n\n    const/16 v2, 0xa5\n',
     '    invoke-virtual {p0, v0, v2}, Lcom/android/camera/data/data/g;->getInt(Ljava/lang/String;I)I\n\n'
     '    move-result v0\n\n'
     f'    invoke-static {{v0}}, {CM}->savedMode(I)I\n\n    move-result v0\n\n'
     '    const/16 v2, 0xa5\n')
