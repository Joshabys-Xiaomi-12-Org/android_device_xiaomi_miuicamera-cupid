package androidx.preference;
import android.content.Context;
public abstract class PreferenceGroup extends Preference {
    public PreferenceGroup(Context c) { super(c); }
    public boolean addPreference(Preference p) { return true; }
    public <T extends Preference> T findPreference(CharSequence key) { return null; }
}
