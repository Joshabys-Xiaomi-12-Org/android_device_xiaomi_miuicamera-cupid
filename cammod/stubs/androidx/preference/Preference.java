package androidx.preference;
import android.content.Context;
public class Preference {
    public interface OnPreferenceChangeListener { boolean onPreferenceChange(Preference p, Object v); }
    public interface OnPreferenceClickListener { boolean onPreferenceClick(Preference p); }
    public Preference(Context c) {}
    public Context getContext() { return null; }
    public void setKey(String k) {}
    public void setTitle(CharSequence t) {}
    public void setTitle(int t) {}
    public void setSummary(CharSequence s) {}
    public void setSummary(int s) {}
    public void setEnabled(boolean e) {}
    public void setPersistent(boolean p) {}
    public void setIconSpaceReserved(boolean b) {}
    public void setOnPreferenceChangeListener(OnPreferenceChangeListener l) {}
    public void setOnPreferenceClickListener(OnPreferenceClickListener l) {}
}
