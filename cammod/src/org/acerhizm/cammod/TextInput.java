package org.acerhizm.cammod;

import android.content.Context;
import android.text.InputFilter;
import android.widget.EditText;
import android.widget.FrameLayout;

/** Single-line text dialog for the watermark fields. */
final class TextInput {
    interface Callback { void onText(String text); }

    /** Watermark text is drawn on one line; keep it to a sane length. */
    private static final int MAX_LENGTH = 40;

    private TextInput() {}

    static void show(Context ctx, String title, String current, final Callback cb) {
        final EditText field = new EditText(ctx);
        field.setSingleLine(true);
        field.setFilters(new InputFilter[] { new InputFilter.LengthFilter(MAX_LENGTH) });
        field.setText(current);
        field.setSelection(field.length());

        FrameLayout box = new FrameLayout(ctx);
        int pad = ColorPicker.dp(ctx, 20);
        box.setPadding(pad, ColorPicker.dp(ctx, 8), pad, 0);
        box.addView(field);

        new miuix.appcompat.app.AlertDialog.a(ctx)
                .Y(title)
                .b0(box)
                .Q(ctx.getString(android.R.string.ok), (d, w) -> cb.onText(field.getText().toString().trim()))
                .E(ctx.getString(android.R.string.cancel), null)
                .G(I18n.get(ctx, "reset"), (d, w) -> cb.onText(""))
                .c0();
    }
}
