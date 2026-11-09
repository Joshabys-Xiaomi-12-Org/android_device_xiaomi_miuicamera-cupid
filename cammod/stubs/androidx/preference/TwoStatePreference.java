package androidx.preference;
import android.content.Context;
public abstract class TwoStatePreference extends Preference {
    public TwoStatePreference(Context c) { super(c); }
    public void setChecked(boolean b) {}
    public boolean isChecked() { return false; }
}
