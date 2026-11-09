package org.acerhizm.cammod;

import android.content.Context;

import androidx.preference.CheckBoxPreference;

/**
 * The camera's BasePreferenceFragment.Ai() sets the fragment as change listener on every
 * preference of the screen, again whenever ti() rebuilds its listeners; ignore those.
 */
final class OwnedCheckBox extends CheckBoxPreference {
    private boolean owned;

    OwnedCheckBox(Context ctx) {
        super(ctx);
    }

    void own(OnPreferenceChangeListener listener) {
        super.setOnPreferenceChangeListener(listener);
        owned = true;
    }

    @Override
    public void setOnPreferenceChangeListener(OnPreferenceChangeListener listener) {
        if (!owned) super.setOnPreferenceChangeListener(listener);
    }
}
