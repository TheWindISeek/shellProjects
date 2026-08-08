# shellProjects

Small personal shell helpers. `install.py` sources `shellrc.sh` from `~/.bashrc`; tools live under `tools/` by category.

## Quick start

```bash
python3 ~/shellProjects/install.py
source ~/.bashrc
```

This writes (or updates) a managed block in `~/.bashrc`:

```bash
# >>> shellProjects >>>
[ -f "$HOME/shellProjects/shellrc.sh" ] && . "$HOME/shellProjects/shellrc.sh"
# <<< shellProjects <<<
```

| Command | What it does |
|---------|----------------|
| `python3 install.py` | Install / update the block |
| `python3 install.py uninstall` | Remove the block |
| `python3 install.py print` | Preview without writing |

Day-to-day: edit scripts and aliases in `shellrc.sh`. You usually do **not** need to rerun `install.py`.

## Layout

```
shellProjects/
├── install.py          # hooks shellrc into ~/.bashrc
├── shellrc.sh          # aliases, sources, prompt
├── tools/
│   ├── app/            # daily: search, keys, rl env, prompt
│   ├── net/            # Wi-Fi, proxy, Clash, campus net
│   └── sys/            # reboot/poweroff guards, process tools
└── vendor/             # third-party (e.g. z)
```

## Common aliases

| Alias | Description |
|-------|-------------|
| `bing` / `bili` / `fanyi` | Search Bing / Bilibili / Baidu Translate |
| `swkey 1\|0` | Toggle xmodmap keymap |
| `swtouch 1\|0` | Disable / enable touchpad |
| `setsound <n>` | Set volume percent |
| `note 1\|0` | Push / pull Obsidian repo |
| `reloadwifi` | Reload Wi-Fi kernel module |
| `reboot` / `poweroff` | Confirm before running |
| `rl` / `rloff` | Enter / leave conda `rl*` env |
| `z <query>` | Jump to frecent directories |

Optional (commented in `shellrc.sh`): `qq`, `wall`, `gitproxy`, `killname`, `ipgw`.

## Prompt

Format: `(env)[LAN-IP]user@host:abs-path$` — colors in `tools/app/prompt.sh`.

- Shows `(env)` when a non-`base` conda / `rl` env is active
- Edit `tools/app/prompt.sh`, then `source ~/.bashrc`

UniLab completion is loaded from `shellrc.sh` when the file exists.

## Clash (optional)

Not wired through bashrc; deploy separately:

```bash
mkdir -p ~/clash ~/.config/clash
cp tools/net/Clash/clash ~/clash/
cp tools/net/Clash/*.yaml ~/.config/clash/
cp tools/net/Clash/*.mmdb ~/.config/clash/
```

Enable system proxy with `wall` after uncommenting it in `shellrc.sh`.

## Third-party

`vendor/z` is [rupa/z](https://github.com/rupa/z). It is gitignored; if missing, `shellrc.sh` prints:

```bash
git clone --depth 1 https://github.com/rupa/z.git vendor/z
```

Optional apt packages:

```bash
sudo apt-get install nload tilix aptitude
```

List key bindings: `xmodmap -pke | less`
