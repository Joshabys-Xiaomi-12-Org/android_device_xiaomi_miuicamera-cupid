package org.acerhizm.cammod;

import android.content.Context;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.text.Editable;
import android.text.InputFilter;
import android.text.InputType;
import android.text.TextWatcher;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.TextView;

import java.util.Locale;

/** HSV colour picker with presets and a hex field, shown in the camera's miuix dialog. */
final class ColorPicker {
    interface Callback { void onColor(int color); }

    /** HyperCeiler default, Leica red, Xiaomi camera yellow, then a spread of hues. */
    private static final int[] PRESETS = {
            CamMod.DEFAULT_THEME_COLOR, 0xFFE11B1B, 0xFFFFCE16, 0xFFFF8A00,
            0xFF34C759, 0xFF00B8D9, 0xFF3482FF, 0xFF9895FF, 0xFFFF5FA2, 0xFFFFFFFF,
    };

    private ColorPicker() {}

    static String hex(int color) {
        return String.format(Locale.ROOT, "#%06X", color & 0xFFFFFF);
    }

    static void show(Context ctx, int current, final int def, final Callback cb) {
        final float[] hsv = new float[3];
        Color.colorToHSV(current, hsv);
        final int pad = dp(ctx, 20);

        LinearLayout root = new LinearLayout(ctx);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, dp(ctx, 8), pad, 0);

        final View preview = new View(ctx);
        final GradientDrawable swatch = new GradientDrawable();
        swatch.setCornerRadius(dp(ctx, 14));
        preview.setBackground(swatch);
        root.addView(preview, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(ctx, 56)));

        LinearLayout presets = new LinearLayout(ctx);
        presets.setOrientation(LinearLayout.HORIZONTAL);
        presets.setGravity(Gravity.CENTER_HORIZONTAL);
        LinearLayout.LayoutParams presetRow = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        presetRow.topMargin = dp(ctx, 14);
        root.addView(presets, presetRow);

        final SeekBar hue = slider(ctx, root, I18n.get(ctx, "hue"), 360);
        final SeekBar sat = slider(ctx, root, I18n.get(ctx, "saturation"), 100);
        final SeekBar val = slider(ctx, root, I18n.get(ctx, "value"), 100);

        final EditText hexField = new EditText(ctx);
        hexField.setHint(I18n.get(ctx, "hex"));
        hexField.setSingleLine(true);
        hexField.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);
        hexField.setFilters(new InputFilter[] { new InputFilter.LengthFilter(7) });
        LinearLayout.LayoutParams hexLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        hexLp.topMargin = dp(ctx, 8);
        root.addView(hexField, hexLp);

        // Guards against the hex watcher and the sliders updating each other in a loop.
        final boolean[] syncing = { false };
        final Runnable fromHsv = () -> {
            int c = Color.HSVToColor(hsv);
            swatch.setColor(c);
            syncing[0] = true;
            hexField.setText(hex(c));
            hexField.setSelection(hexField.length());
            syncing[0] = false;
        };
        final Runnable toSliders = () -> {
            syncing[0] = true;
            hue.setProgress(Math.round(hsv[0]));
            sat.setProgress(Math.round(hsv[1] * 100));
            val.setProgress(Math.round(hsv[2] * 100));
            syncing[0] = false;
        };

        SeekBar.OnSeekBarChangeListener onSlide = new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar s, int p, boolean user) {
                if (syncing[0]) return;
                hsv[0] = hue.getProgress();
                hsv[1] = sat.getProgress() / 100f;
                hsv[2] = val.getProgress() / 100f;
                fromHsv.run();
            }
            @Override public void onStartTrackingTouch(SeekBar s) {}
            @Override public void onStopTrackingTouch(SeekBar s) {}
        };
        hue.setOnSeekBarChangeListener(onSlide);
        sat.setOnSeekBarChangeListener(onSlide);
        val.setOnSeekBarChangeListener(onSlide);

        hexField.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int a, int b, int c) {}
            @Override public void onTextChanged(CharSequence s, int a, int b, int c) {}
            @Override public void afterTextChanged(Editable e) {
                if (syncing[0]) return;
                Integer c = parse(e.toString());
                if (c == null) return;
                Color.colorToHSV(c, hsv);
                swatch.setColor(c);
                toSliders.run();
            }
        });

        int size = dp(ctx, 26);
        int gap = dp(ctx, 4);
        for (final int preset : PRESETS) {
            View dot = new View(ctx);
            GradientDrawable d = new GradientDrawable();
            d.setShape(GradientDrawable.OVAL);
            d.setColor(preset);
            d.setStroke(dp(ctx, 1), 0x33000000);
            dot.setBackground(d);
            dot.setContentDescription(hex(preset));
            dot.setOnClickListener(v -> {
                Color.colorToHSV(preset, hsv);
                toSliders.run();
                fromHsv.run();
            });
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(size, size);
            lp.setMargins(gap, 0, gap, 0);
            presets.addView(dot, lp);
        }

        toSliders.run();
        fromHsv.run();

        new miuix.appcompat.app.AlertDialog.a(ctx)
                .Y(I18n.get(ctx, "theme_color_pick"))
                .b0(root)
                .Q(ctx.getString(android.R.string.ok), (dlg, w) -> cb.onColor(Color.HSVToColor(hsv)))
                .E(ctx.getString(android.R.string.cancel), null)
                .G(I18n.get(ctx, "reset"), (dlg, w) -> cb.onColor(def))
                .c0();
    }

    static Integer parse(String s) {
        String t = s.trim();
        if (!t.startsWith("#")) t = "#" + t;
        if (t.length() != 7) return null;
        try {
            return Color.parseColor(t);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private static SeekBar slider(Context ctx, LinearLayout root, String label, int max) {
        TextView title = new TextView(ctx);
        title.setText(label);
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        LinearLayout.LayoutParams tlp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        tlp.topMargin = dp(ctx, 12);
        root.addView(title, tlp);
        SeekBar bar = new SeekBar(ctx);
        bar.setMax(max);
        root.addView(bar, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        return bar;
    }

    static int dp(Context ctx, int v) {
        return Math.round(v * ctx.getResources().getDisplayMetrics().density);
    }
}
