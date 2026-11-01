# rog-falchion-battery

**Legge la batteria della tastiera senza fili ASUS ROG Falchion su Linux.**

[English](README.md)

La ROG Falchion (senza fili, con il ricevitore a 2,4 GHz) non dice a Linux quanto è carica: in
UPower non c'è, in `/sys/class/power_supply` nemmeno. La batteria bisogna *chiederla* alla
tastiera, nel linguaggio di ASUS. Questo piccolo programma fa proprio questo e stampa la risposta.

```
$ rog-falchion-battery.py
ROG Falchion: 90%

$ rog-falchion-battery.py --json
[{"name": "ROG Falchion", "product": "0b05:193e", "battery": 90, "charging": false}]
```

- Python 3, solo la libreria standard: un file solo, niente da installare.
- Fa solo **domande**: sulla tastiera non cambia niente (luci, impostazioni, firmware).
- Uscita `--json`, comoda da mostrare in una barra (Waybar, Quickshell, eww…) o per gli avvisi di batteria scarica.

## Provato su

| Tastiera | ID USB | Collegamento | Sistema |
|---|---|---|---|
| ASUS ROG Falchion (senza fili) | `0b05:193e` | ricevitore USB a 2,4 GHz | CachyOS (Arch Linux), Hyprland |

Il codice prodotto `0b05:193c` (modalità con il filo) è incluso perché G-Helper usa lo stesso
protocollo, ma **non** è stato provato. Le segnalazioni sono benvenute.

## Installazione

```sh
git clone https://github.com/AG-WebLab/rog-falchion-battery
cd rog-falchion-battery

# permette all'utente collegato di parlare con la tastiera (una volta sola)
sudo cp udev/70-rog-falchion-battery.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger --subsystem-match=hidraw

./rog-falchion-battery.py
```

Senza la regola udev il programma va lanciato da amministratore (`sudo ./rog-falchion-battery.py`).

## Uso

| Comando | Cosa fa |
|---|---|
| `rog-falchion-battery.py` | Stampa `ROG Falchion: 90%` (e `(charging)` quando è in carica) |
| `rog-falchion-battery.py --json` | Stampa un elenco JSON, una voce per tastiera |
| `rog-falchion-battery.py --udev` | Stampa la regola udev |
| `rog-falchion-battery.py --probe` | Prova ogni interfaccia ASUS e ogni domanda e stampa le risposte così come arrivano (utile per altri modelli) |

Se la tastiera è spenta, addormentata o troppo lontana, la voce dice `no answer`.

## Come funziona

Il ricevitore USB della tastiera ha quattro interfacce HID. Sull'**interfaccia 1** risponde alle
domande di ASUS (pacchetti da 64 byte, ID del rapporto 0):

| | Byte |
|---|---|
| Domanda | `00 12 01 00 …` (65 byte compreso l'ID 0) |
| Risposta | `00 12 01 …`, **percentuale della batteria al byte 11**, **in carica al byte 9** (byte 6: una scala da 0 a 10) |
| Domanda sconosciuta | `00 ff aa …` |

La domanda della batteria usata dai mouse ROG (`12 07`) riceve da questa tastiera `ff aa`
("domanda sconosciuta"): per questo i programmi scritti per i mouse ROG non vedono la sua batteria.

## Ringraziamenti

- La forma della domanda e della risposta viene da [G-Helper](https://github.com/seerge/g-helper)
  (`app/Peripherals/Keyboard/Models/Falchion.cs`), il programma per Windows dei dispositivi ASUS.
  Questo programma è una versione per Linux indipendente, scritta da zero: non contiene codice di
  G-Helper (GPL-3.0) né di rogctl (AGPL-3.0), solo le informazioni su come comunica la tastiera
  (quali byte mandare e dove sta la risposta). Per questo può avere la licenza MIT.
- [rogctl](https://github.com/Humblemonk/rogctl) (mouse ROG) e
  [rogdriver](https://github.com/rahulrajaram/rogdriver) (ROG Falchion RX Low Profile) sono stati
  utili per capire il protocollo HID di ASUS su Linux.

## Autore

Fatto da **[AG-WebLab](https://github.com/AG-WebLab)** con
[Claude Code](https://claude.com/claude-code), e provato sulla mia ROG Falchion.

## Licenza

[MIT](LICENSE)
