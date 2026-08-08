# GNOME Startup Applications (snapshot)

Reference copies of `~/.config/autostart/*.desktop`.  
**Not** applied by `install.py` — keep them here so you remember what auto-starts at login.

Live location:

```bash
ls ~/.config/autostart/
gnome-session-properties   # GUI: Startup Applications
```

Restore a file manually:

```bash
cp config/autostart/<name>.desktop ~/.config/autostart/
```

## Current entries

| File | Name | Exec |
|------|------|------|
| `clash-verge.desktop` | clash-verge | Clash Verge AppImage under `~/Applications/` |
| `clashcn.com_…AppImage.desktop` | clash | Same AppImage (duplicate; safe to keep only one) |
| `ipgw.desktop` | ipgw | `tools/net/neu_ipgw.py` |
| `utools.desktop` | utools | `/usr/bin/utools` |

After changing Startup Applications in the GUI, re-copy into this folder if you want the snapshot updated.
