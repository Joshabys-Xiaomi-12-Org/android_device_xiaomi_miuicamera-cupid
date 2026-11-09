package org.acerhizm.cammod;

import android.app.Activity;
import android.app.AlarmManager;
import android.app.Application;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.util.SparseArray;
import android.view.Window;
import android.view.WindowManager;

import androidx.preference.Preference;
import androidx.preference.PreferenceCategory;
import androidx.preference.PreferenceFragmentCompat;
import androidx.preference.PreferenceScreen;

/**
 * Settings and feature switches added to MIUI Camera. Smali hooks call the static
 * getters below; everything defaults to the camera's stock behaviour except the
 * Leica theme, which this ROM ships enabled.
 */
public final class CamMod {
    static final String PREFS = "cammod";

    static final String LEICA = "leica";
    static final String SUPER_JPEG = "super_jpeg";
    static final String BRIGHTNESS = "brightness";
    static final String THEME_COLOR_ON = "theme_color_on";
    static final String THEME_COLOR = "theme_color";
    static final String WATERMARK_ON = "watermark_on";
    static final String WATERMARK_MAKER = "watermark_maker";
    static final String WATERMARK_DEVICE = "watermark_device";
    static final String LAB = "lab";
    static final String BLACK_LEICA = "black_leica";
    static final String LIVE_PHOTO = "live_photo";
    static final String INDIA = "india_filters";
    static final String SHUTTER_8000 = "shutter_8000";
    static final String ZOOM_10X = "zoom_10x";
    static final String TRUE_COLOR = "lab_true_color";
    static final String DIRECTOR = "director";
    // Experimental features, shown in the camera's own lab category.
    static final String SUBTITLES = "lab_subtitles";
    static final String RENDER_V2 = "lab_render_v2";
    static final String BURST_55 = "lab_burst_55";

    /** HyperCeiler's default for its camera theme color picker. */
    static final int DEFAULT_THEME_COLOR = -2025677;

    // Camera's own strings, already translated in every locale it ships.
    private static final int STR_DIRECTOR = 0x7f1402e2;
    private static final int STR_EYE_TITLE = 0x7f1409c3;
    private static final int STR_EYE_SUMMARY = 0x7f1409c2;
    private static final String KEY_EYE = "pref_camera_track_eye_preferred_key";

    private CamMod() {}

    // ----- context and storage -----

    static Context context() {
        Context c = null;
        try {
            c = com.android.camera.CameraAppImpl.o();
        } catch (Throwable ignored) {
        }
        if (c == null) {
            // Static initialisers can run before the camera stores its context.
            try {
                c = (Application) Class.forName("android.app.ActivityThread")
                        .getMethod("currentApplication").invoke(null);
            } catch (Throwable ignored) {
            }
        }
        return c;
    }

    static SharedPreferences prefs() {
        Context c = context();
        return c == null ? null : c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static boolean bool(String key, boolean def) {
        SharedPreferences p = prefs();
        return p == null ? def : p.getBoolean(key, def);
    }

    static int integer(String key, int def) {
        SharedPreferences p = prefs();
        return p == null ? def : p.getInt(key, def);
    }

    static String string(String key) {
        SharedPreferences p = prefs();
        return p == null ? "" : p.getString(key, "");
    }

    static void put(String key, Object value) {
        SharedPreferences p = prefs();
        if (p == null) return;
        SharedPreferences.Editor e = p.edit();
        if (value instanceof Boolean) e.putBoolean(key, (Boolean) value);
        else if (value instanceof Integer) e.putInt(key, (Integer) value);
        else e.putString(key, String.valueOf(value));
        // commit(): a restart prompt may kill the process right after this write.
        e.commit();
    }

    // ----- feature getters used by the smali hooks -----

    /** Profile k4/j4: Leica (Madrid) theme support. */
    public static boolean leica() {
        return bool(LEICA, true);
    }

    /** Profile E1: theme count; the Xiaomi 12S Pro profile uses 2, Common 0. */
    public static int leicaThemeCount() {
        return leica() ? 2 : 0;
    }

    /** Profile Z: theme index; the Xiaomi 12S Pro profile uses 0, Common -1. */
    public static int leicaThemeIndex() {
        return leica() ? 0 : -1;
    }

    /** Common x8: lets the JPEG quality reach SUPER (100). */
    public static boolean superJpeg() {
        return bool(SUPER_JPEG, false);
    }

    /** Camera.hn(): brightness the camera restores to, -1 meaning system brightness. */
    public static float brightness(float stock) {
        return bool(BRIGHTNESS, false) ? WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_FULL : stock;
    }

    /** ActivityBase.onResume(). */
    public static void applyBrightness(Activity activity) {
        if (activity == null || !bool(BRIGHTNESS, false)) return;
        Window w = activity.getWindow();
        if (w == null) return;
        WindowManager.LayoutParams lp = w.getAttributes();
        lp.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_FULL;
        w.setAttributes(lp);
    }

    /** n0/f.<clinit>: accent color of the camera UI. */
    public static int themeColor(int stock) {
        return bool(THEME_COLOR_ON, false) ? integer(THEME_COLOR, DEFAULT_THEME_COLOR) : stock;
    }

    /** The camera's own accent while the Leica theme is on (n0/f.<clinit>, 0xFFE11B1B). */
    static final int LEICA_RED = 0xFFE11B1B;

    /**
     * sp/b.x(): slidingBarColor, which every miuix sliding switch tints its "on" bar with.
     * Custom theme colour first, then Leica red, else the stock blue.
     */
    public static int switchBarColor(int stock) {
        if (bool(THEME_COLOR_ON, false)) return integer(THEME_COLOR, DEFAULT_THEME_COLOR);
        return leica() ? LEICA_RED : stock;
    }

    /** Zeus profile d(): manufacturer/device text of the device watermark. */
    public static SparseArray<String[]> watermark(SparseArray<String[]> stock) {
        if (stock == null || !bool(WATERMARK_ON, false)) return stock;
        String maker = string(WATERMARK_MAKER);
        String device = string(WATERMARK_DEVICE);
        SparseArray<String[]> out = new SparseArray<>(stock.size());
        for (int i = 0; i < stock.size(); i++) {
            String[] v = stock.valueAt(i);
            String[] n = v == null ? new String[2] : v.clone();
            if (n.length > 0 && !maker.isEmpty()) n[0] = maker;
            if (n.length > 1 && !device.isEmpty()) n[1] = device;
            out.put(stock.keyAt(i), n);
        }
        return out;
    }

    static boolean lab() {
        return bool(LAB, false);
    }

    /** mb/b.w3(): camera.lab.options, or our switch. */
    public static boolean labOr(boolean stock) {
        return stock || lab();
    }

    /** CameraPreferenceFragment.onResume(): the lab hint toast, translated. */
    public static void labHint(Context ctx, int stockRes, boolean longToast) {
        com.android.camera.q5.h(ctx, I18n.get(ctx, "lab_hint"), longToast);
    }

    // Lab preferences added by CameraPreferenceFragment.Wi(); most titles only exist in
    // English and Chinese (three only in Chinese).
    private static final String[][] LAB_TITLES = {
            { "pref_video_capture_repeating", "lab_video_capture_repeating" },
            { "pref_camera_facedetection_key", "lab_facedetection" },
            { "pref_camera_facedetection_auto_hidden_key", "lab_facedetection_auto_hidden" },
            { "pref_camera_video_show_faceview", "lab_video_show_faceview" },
            { "pref_camera_portrait_with_facebeauty_key", "lab_portrait_with_facebeauty" },
            { "pref_camera_dual_enable_key", "lab_dual_enable" },
            { "pref_camera_dual_sat_enable_key", "lab_dual_sat_enable" },
            { "pref_camera_mfnr_sat_enable_key", "lab_mfnr_sat_enable" },
            { "pref_camera_sr_enable_key", "lab_sr_enable" },
            { "pref_camera_parallel_process_enable_key", "lab_parallel_process_enable" },
            { "pref_camera_quick_shot_anim_enable_key", "lab_quick_shot_anim_enable" },
            { "pref_camera_video_sat_enable_key", "lab_video_sat_enable" },
            { "pref_camera_touch_focus_delay_key", "lab_touch_focus_delay" },
            { "pref_camera_quick_shot_enable_key", "lab_quick_shot_enable" },
    };

    static void translateLab(Context ctx, PreferenceScreen screen) {
        for (String[] t : LAB_TITLES) {
            Preference p = screen.findPreference(t[0]);
            if (p != null) p.setTitle(I18n.get(ctx, t[1]));
        }
    }

    /** CvWatermarkParam.isWhiteBackground(): Leica watermark on a black strip. */
    public static boolean blackLeica() {
        return bool(BLACK_LEICA, false);
    }

    /**
     * mb/b.G6(): Dynamic shots are hidden on global builds, and the camera tree's
     * patch 0002 marks every build global. Returns the flag G6 should use.
     */
    public static boolean livePhotoGlobal(boolean global) {
        return global && !bool(LIVE_PHOTO, true);
    }

    /**
     * EffectControllerCv.initialize(): append the India filter sets to the normal and
     * beauty lists. The stock India flag would replace those lists and also swap the
     * AI-scene and beauty LUTs, so it stays off.
     */
    public static void indiaFilters(com.android.camera.effect.b ec) {
        if (ec == null || !bool(INDIA, false)) return;
        try {
            // Separate instances per list: effect/c carries per-list UI state.
            merge(ec.getFilterInfo(1), ec.initIndiaNormalFilterInfoNew(), ec.initIndiaBeautyFilterInfoBack());
            merge(ec.getFilterInfo(2), ec.initIndiaBeautyFilterInfoFront());
            merge(ec.getFilterInfo(10), ec.initIndiaBeautyFilterInfoBack());
        } catch (Throwable t) {
            android.util.Log.e("CamMod", "indiaFilters failed", t);
        }
    }

    /** Appends items whose id and LUT file are new; 16 of the 21 India LUTs are normal ones. */
    @SafeVarargs
    static void merge(java.util.ArrayList<com.android.camera.effect.c> dst,
            java.util.ArrayList<com.android.camera.effect.c>... srcs) {
        if (dst == null) return;
        java.util.Set<Integer> ids = new java.util.HashSet<>();
        java.util.Set<String> luts = new java.util.HashSet<>();
        for (com.android.camera.effect.c x : dst) {
            ids.add(x.d());
            luts.add(lut(x));
        }
        for (java.util.ArrayList<com.android.camera.effect.c> src : srcs) {
            if (src == null) continue;
            for (com.android.camera.effect.c x : src) {
                String l = lut(x);
                // A null LUT is the "none" item, already in every list.
                if (l == null || ids.contains(x.d()) || luts.contains(l)) continue;
                dst.add(x);
                ids.add(x.d());
                luts.add(l);
            }
        }
    }

    static String lut(com.android.camera.effect.c x) {
        j2.f[] all = j2.f.values();
        int o = com.android.camera.effect.c.i(x.d());
        if (all == null || o < 0 || o >= all.length) return null;
        String[] s = all[o].c();
        return s == null || s.length == 0 ? null : s[0];
    }

    /** The camera targets the Mi file manager, which this ROM does not ship; use the system picker. */
    public static void pickFile(androidx.fragment.app.Fragment f, Intent i, int code) {
        try {
            f.startActivityForResult(picker(i), code);
        } catch (android.content.ActivityNotFoundException e) {
            android.util.Log.w("CamMod", "no file picker", e);
        }
    }

    public static void pickFile(Activity a, Intent i, int code) {
        try {
            a.startActivityForResult(picker(i), code);
        } catch (android.content.ActivityNotFoundException e) {
            android.util.Log.w("CamMod", "no file picker", e);
        }
    }

    static Intent picker(Intent i) {
        i.setAction(Intent.ACTION_GET_CONTENT);
        i.setPackage(null);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        // .cube has no MIME type; the prompter's EXTRA_MIME_TYPES keeps it to doc/docx/txt.
        i.setType("*/*");
        String[] types = i.getStringArrayExtra(Intent.EXTRA_MIME_TYPES);
        java.util.List<String> ok = new java.util.ArrayList<>();
        if (types != null) for (String s : types) if (s != null) ok.add(s);
        if (ok.isEmpty()) i.removeExtra(Intent.EXTRA_MIME_TYPES);
        else i.putExtra(Intent.EXTRA_MIME_TYPES, ok.toArray(new String[0]));
        return i;
    }

    static String displayName(android.net.Uri uri) {
        Context c = context();
        if (c == null || uri == null || !"content".equals(uri.getScheme())) return null;
        try (android.database.Cursor cur = c.getContentResolver().query(uri,
                new String[] { android.provider.OpenableColumns.DISPLAY_NAME }, null, null, null)) {
            return cur != null && cur.moveToFirst() ? cur.getString(0) : null;
        } catch (Throwable t) {
            return null;
        }
    }

    /** FragmentVideoPrompterEdit.ki(): extension it dispatches on; picker URIs often have none. */
    public static String pickedExt(android.net.Uri uri, String stock) {
        String n = displayName(uri);
        int dot = n == null ? -1 : n.lastIndexOf('.');
        return dot < 0 ? stock : n.substring(dot + 1).toLowerCase(java.util.Locale.ROOT);
    }

    /** o6/c0.Gp(): its last segment names the copied LUT, which must end in .cube. */
    public static String pickedPath(android.net.Uri uri, String stock) {
        String n = displayName(uri);
        return n == null || n.isEmpty() || n.contains("/") ? stock : "/" + n;
    }

    /**
     * Common.G1: Pro exposure limits as "mode:minNs:maxNs;...". The colons keep the
     * replacement off the 125000000 upper bounds; 125000 ns = 1/8000 s, above the HAL minimum.
     */
    public static String shutterRange(String stock) {
        return stock != null && bool(SHUTTER_8000, false) ? stock.replace(":250000:", ":125000:") : stock;
    }

    /**
     * e9/w: the 6x zoom cap outside Photo. The callers clamp it to the HAL's
     * maxDigitalZoom; zoomRatioRange tops out at 10 on every zeus camera.
     */
    public static float maxZoom(float stock) {
        return bool(ZOOM_10X, false) ? Math.max(stock, 10f) : stock;
    }

    /** Profile Y6: the Dolby Vision ("true colour") option in Settings → Video; hides HLG. */
    public static boolean trueColor() {
        return lab() && bool(TRUE_COLOR, false);
    }

    /** Common n2: Director mode (module 0xa4). p2/a builds the module list once per process. */
    public static boolean director() {
        return bool(DIRECTOR, false);
    }

    /**
     * Director's multi-device shooting binds Xiaomi MiConnect, which this ROM lacks; without
     * it the setup button, first-use guide and Wi-Fi watch only lead to an error, so hide them.
     */
    public static boolean multicam(boolean stock) {
        if (!stock) return false;
        Context c = context();
        if (c == null) return false;
        try {
            c.getPackageManager().getPackageInfo("com.xiaomi.mi_connect_service", 0);
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    /**
     * t0/g.E(): the saved start mode. A saved Director mode with Director off would make
     * Camera.tl() throw on every launch, so fall back to Photo like the stock 0xa5 migration.
     */
    public static int savedMode(int mode) {
        return mode == 0xa4 && !director() ? 0xa3 : mode;
    }

    /** mb/b.S7(): subtitles are hidden on global builds; patch 0002 makes every build global. */
    public static boolean subtitlesGlobal(boolean global) {
        return global && !(lab() && bool(SUBTITLES, false));
    }

    private static Boolean sRenderV2;

    /** Profile P5. Fixed per process: ActivityBase.li() picks the preview renderer once. */
    public static boolean renderV2() {
        if (sRenderV2 == null) {
            if (prefs() == null) return false; // no context yet: don't cache the default
            sRenderV2 = lab() && bool(RENDER_V2, false);
        }
        return sRenderV2;
    }

    /** Profile O0: fixed burst interval in ms, -1 = stock. 55 is what the 12S Pro uses. */
    public static long burstInterval() {
        return lab() && bool(BURST_55, false) ? 55L : -1L;
    }

    // ----- settings screen -----

    /** End of BasePreferenceFragment.xi(), after the camera has wired its own preferences. */
    public static void addSettings(PreferenceFragmentCompat fragment) {
        // xi() builds every camera settings page; only the main one gets our section.
        if (!fragment.getClass().getName().equals(
                "com.android.camera.fragment.settings.CameraPreferenceFragment")) {
            return;
        }
        try {
            Context ctx = fragment.getContext();
            PreferenceScreen screen = fragment.getPreferenceScreen();
            if (ctx == null || screen == null) return;
            translateLab(ctx, screen);
            new SettingsBuilder(ctx, screen).build();
        } catch (Throwable t) {
            android.util.Log.e("CamMod", "addSettings failed", t);
        }
    }

    static final class SettingsBuilder {
        final Context ctx;
        final PreferenceScreen screen;
        PreferenceCategory cat;

        SettingsBuilder(Context ctx, PreferenceScreen screen) {
            this.ctx = ctx;
            this.screen = screen;
        }

        void build() {
            cat = new PreferenceCategory(ctx);
            cat.setKey("cammod_category");
            cat.setTitle(I18n.get(ctx, "category"));
            screen.addPreference(cat);

            final t0.g store = o0.b.h();

            final OwnedCheckBox leica = check(LEICA, "leica_title", "leica_summary", leica());
            final OwnedCheckBox icons = check("cammod_color_icons", "color_icons_title",
                    "color_icons_summary", store != null && store.Z0());
            icons.setEnabled(leica.isChecked());
            leica.own((p, v) -> {
                put(LEICA, v);
                icons.setEnabled((Boolean) v);
                askRestart();
                return true;
            });
            icons.own((p, v) -> {
                if (store != null) store.R0((Boolean) v ? 1 : 0);
                return true;
            });

            OwnedCheckBox eye = new OwnedCheckBox(ctx);
            eye.setKey("cammod_eye");
            eye.setTitle(ctx.getString(STR_EYE_TITLE));
            eye.setSummary(ctx.getString(STR_EYE_SUMMARY));
            eye.setPersistent(false);
            eye.setChecked(store == null || store.getBoolean(KEY_EYE, true));
            eye.own((p, v) -> {
                if (store != null && store.y() != null) store.y().f((Boolean) v);
                return true;
            });
            cat.addPreference(eye);

            simple(SUPER_JPEG, "super_jpeg_title", "super_jpeg_summary", false, false);
            simple(BRIGHTNESS, "brightness_title", "brightness_summary", false, false);

            final OwnedCheckBox colorOn = check(THEME_COLOR_ON, "theme_color_title",
                    "theme_color_summary", bool(THEME_COLOR_ON, false));
            final Preference color = new Preference(ctx);
            color.setKey("cammod_theme_color_pick");
            color.setTitle(I18n.get(ctx, "theme_color_pick"));
            color.setPersistent(false);
            color.setSummary(ColorPicker.hex(integer(THEME_COLOR, DEFAULT_THEME_COLOR)));
            color.setEnabled(colorOn.isChecked());
            color.setOnPreferenceClickListener(p -> {
                ColorPicker.show(ctx, integer(THEME_COLOR, DEFAULT_THEME_COLOR), DEFAULT_THEME_COLOR, c -> {
                    put(THEME_COLOR, c);
                    color.setSummary(ColorPicker.hex(c));
                    askRestart();
                });
                return true;
            });
            colorOn.own((p, v) -> {
                put(THEME_COLOR_ON, v);
                color.setEnabled((Boolean) v);
                askRestart();
                return true;
            });
            cat.addPreference(color);

            final OwnedCheckBox wmOn = check(WATERMARK_ON, "watermark_title",
                    "watermark_summary", bool(WATERMARK_ON, false));
            final Preference maker = text(WATERMARK_MAKER, "watermark_maker", wmOn.isChecked());
            final Preference device = text(WATERMARK_DEVICE, "watermark_device", wmOn.isChecked());
            wmOn.own((p, v) -> {
                put(WATERMARK_ON, v);
                maker.setEnabled((Boolean) v);
                device.setEnabled((Boolean) v);
                return true;
            });

            simple(LIVE_PHOTO, "live_photo_title", "live_photo_summary", true, true);
            simple(INDIA, "india_title", "india_summary", false, true);
            simple(SHUTTER_8000, "shutter_title", "shutter_summary", false, false);
            simple(ZOOM_10X, "zoom_title", "zoom_summary", false, false);

            OwnedCheckBox director = check(DIRECTOR, "director_summary", "director_summary", director());
            director.setTitle(ctx.getString(STR_DIRECTOR));
            director.own((p, v) -> {
                put(DIRECTOR, v);
                askRestart();
                return true;
            });
            simple(LAB, "lab_title", "lab_summary", false, true);
            simple(BLACK_LEICA, "black_leica_title", "black_leica_summary", false, false);

            // The camera's "Experimental features" category exists only while lab options are on.
            PreferenceCategory lab = screen.findPreference("category_advance_setting");
            if (lab != null) {
                cat = lab;
                simple(SUBTITLES, "subtitles_title", "subtitles_summary", false, false);
                simple(RENDER_V2, "render_v2_title", "render_v2_summary", false, true);
                simple(BURST_55, "burst55_title", "burst55_summary", false, false);
                simple(TRUE_COLOR, "true_color_title", "true_color_summary", false, false);
            }
        }

        OwnedCheckBox check(String key, String title, String summary, boolean checked) {
            OwnedCheckBox p = new OwnedCheckBox(ctx);
            p.setKey("cammod_" + key);
            p.setTitle(I18n.get(ctx, title));
            p.setSummary(I18n.get(ctx, summary));
            p.setPersistent(false);
            p.setChecked(checked);
            cat.addPreference(p);
            return p;
        }

        void simple(final String key, String title, String summary, boolean def, final boolean restart) {
            OwnedCheckBox p = check(key, title, summary, bool(key, def));
            p.own((pref, v) -> {
                put(key, v);
                if (restart) askRestart();
                return true;
            });
        }

        Preference text(final String key, final String titleKey, boolean enabled) {
            final Preference p = new Preference(ctx);
            p.setKey("cammod_" + key);
            p.setTitle(I18n.get(ctx, titleKey));
            p.setPersistent(false);
            p.setEnabled(enabled);
            summarize(p, string(key));
            p.setOnPreferenceClickListener(pref -> {
                TextInput.show(ctx, I18n.get(ctx, titleKey), string(key), v -> {
                    put(key, v);
                    summarize(p, v);
                });
                return true;
            });
            cat.addPreference(p);
            return p;
        }

        void summarize(Preference p, String value) {
            p.setSummary(value == null || value.isEmpty() ? I18n.get(ctx, "not_set") : value);
        }

        void askRestart() {
            new miuix.appcompat.app.AlertDialog.a(ctx)
                    .z(I18n.get(ctx, "restart_message"))
                    .Q(I18n.get(ctx, "restart_now"), (d, w) -> restart(ctx))
                    .E(I18n.get(ctx, "restart_later"), null)
                    .c0();
        }
    }

    /**
     * Values read in static initialisers only change in a new process. The relaunch is
     * scheduled with AlarmManager: an activity started from this process would die with it.
     */
    static void restart(Context ctx) {
        Intent launch = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName());
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            PendingIntent pi = PendingIntent.getActivity(ctx, 0, launch,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_CANCEL_CURRENT);
            AlarmManager am = ctx.getSystemService(AlarmManager.class);
            if (am != null) am.set(AlarmManager.RTC, System.currentTimeMillis() + 500, pi);
        }
        if (ctx instanceof Activity) ((Activity) ctx).finishAffinity();
        android.os.Process.killProcess(android.os.Process.myPid());
    }
}
