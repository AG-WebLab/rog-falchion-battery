# rog-falchion-battery

**Read the battery level of the ASUS ROG Falchion wireless keyboard on Linux.**

[Italiano](README.it.md)

The ROG Falchion (wireless, 2.4 GHz receiver) does not tell Linux how charged it is: there is
nothing in UPower, nothing in `/sys/class/power_supply`. The battery has to be *asked* to the
keyboard, in ASUS's own language. This small tool does exactly that, and prints the answer.

```
$ rog-falchion-battery.py
ROG Falchion: 90%

$ rog-falchion-battery.py --json
[{"name": "ROG Falchion", "product": "0b05:193e", "battery": 90, "charging": false}]
```

- Python 3, standard library only: one file, no dependencies.
- It only **asks**: nothing on the keyboard (lighting, settings, firmware) is changed.
- `--json` output, easy to show in a bar (Waybar, Quickshell, eww, …) or to use for low-battery alerts.

## Tested on

| Keyboard | USB ID | Connection | System |
|---|---|---|---|
| ASUS ROG Falchion (wireless) | `0b05:193e` | 2.4 GHz USB receiver | CachyOS (Arch Linux), Hyprland |

The wired-mode product ID `0b05:193c` is included because G-Helper uses the same protocol for it,
but it has **not** been tested. Reports are welcome.

## Install

```sh
git clone https://github.com/AG-WebLab/rog-falchion-battery
cd rog-falchion-battery

# let the logged-in user talk to the keyboard (once)
sudo cp udev/70-rog-falchion-battery.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger --subsystem-match=hidraw

./rog-falchion-battery.py
```

Without the udev rule the tool needs root (`sudo ./rog-falchion-battery.py`).

## Usage

| Command | What it does |
|---|---|
| `rog-falchion-battery.py` | Prints `ROG Falchion: 90%` (and `(charging)` while charging) |
| `rog-falchion-battery.py --json` | Prints a JSON list, one entry per keyboard |
| `rog-falchion-battery.py --udev` | Prints the udev rule |
| `rog-falchion-battery.py --probe` | Tries every ASUS hidraw interface and request and prints the raw replies (useful for other models) |

If the keyboard is off, asleep or out of range, the entry says `no answer`.

## How it works

The keyboard's USB receiver exposes four HID interfaces. On **interface 1** it answers ASUS
vendor requests (64-byte payloads, report ID 0):

| | Bytes |
|---|---|
| Request | `00 12 01 00 …` (65 bytes including report ID 0) |
| Reply | `00 12 01 …`, **battery percentage at byte 11**, **charging flag at byte 9** (byte 6: a 0–10 gauge) |
| Unknown request | `00 ff aa …` |

The battery request used by ROG mice (`12 07`) is answered with `ff aa` ("unknown request") by
this keyboard: that is why tools written for ROG mice don't see its battery.

## Credits

- The request and reply layout come from [G-Helper](https://github.com/seerge/g-helper)
  (`app/Peripherals/Keyboard/Models/Falchion.cs`), the Windows tool for ASUS devices.
  This tool is an independent Linux implementation, written from scratch.
- [rogctl](https://github.com/Humblemonk/rogctl) (ROG mice) and
  [rogdriver](https://github.com/rahulrajaram/rogdriver) (ROG Falchion RX Low Profile) were useful
  references for the ASUS HID protocol on Linux.

## Author

Made by **[AG-WebLab](https://github.com/AG-WebLab)** with
[Claude Code](https://claude.com/claude-code), and tested on my own ROG Falchion.

## License

[MIT](LICENSE)
