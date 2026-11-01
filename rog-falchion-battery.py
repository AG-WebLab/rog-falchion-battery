#!/usr/bin/env python3
"""Read the battery level of the ASUS ROG Falchion wireless keyboard on Linux.

The keyboard does not report its battery to the kernel or to UPower: it has to be asked.
This tool asks it over hidraw, the same way G-Helper does on Windows:

  * interface 1 of the USB receiver (0b05:193e), report ID 0, 65-byte packets;
  * request  [0x00, 0x12, 0x01, 0x00 ...];
  * reply    [0x00, 0x12, 0x01, ...] with the battery percentage at byte 11
    and the charging flag at byte 9 (byte 6 holds a 0-10 gauge).

Only questions are sent: nothing on the keyboard is changed.
Python 3 standard library only.

Usage:
  rog-falchion-battery.py            print the battery level ("ROG Falchion: 90%")
  rog-falchion-battery.py --json     print JSON: [{"name", "product", "battery", "charging"}]
  rog-falchion-battery.py --probe    try every ASUS hidraw interface and request, print the raw replies
  rog-falchion-battery.py --udev     print a udev rule that lets the logged-in user read the keyboard
"""

import glob
import json
import os
import select
import sys
import time

ASUS = "0b05"

# Known devices: product ID -> how to ask. Byte indexes count the report ID as byte 0.
MODELS = {
    # ROG Falchion (wireless, 2.4 GHz receiver). Tested.
    "193e": {"name": "ROG Falchion", "interface": 1, "report_id": 0x00, "length": 65,
             "command": 0x01, "percent": 11, "charging": 9},
    # ROG Falchion (wired product ID, same protocol in G-Helper). Not tested.
    "193c": {"name": "ROG Falchion", "interface": 1, "report_id": 0x00, "length": 65,
             "command": 0x01, "percent": 11, "charging": 9},
}


def device_info(node):
    """Vendor, product, USB interface number and name of a /dev/hidrawN node."""
    base = os.path.realpath(f"/sys/class/hidraw/{os.path.basename(node)}/device")
    with open(os.path.join(base, "uevent")) as f:
        uevent = f.read().splitlines()
    hid_id = next((r.split("=", 1)[1] for r in uevent if r.startswith("HID_ID=")), "")
    name = next((r.split("=", 1)[1] for r in uevent if r.startswith("HID_NAME=")), "")
    parts = hid_id.split(":")
    vendor = parts[1][-4:].lower() if len(parts) > 2 else ""
    product = parts[2][-4:].lower() if len(parts) > 2 else ""
    interface = -1
    path = base
    for _ in range(4):
        path = os.path.dirname(path)
        candidate = os.path.join(path, "bInterfaceNumber")
        if os.path.exists(candidate):
            with open(candidate) as f:
                interface = int(f.read().strip(), 16)
            break
    return {"node": node, "vendor": vendor, "product": product, "interface": interface, "name": name}


def asus_nodes():
    nodes = []
    for node in sorted(glob.glob("/dev/hidraw*")):
        try:
            info = device_info(node)
        except OSError:
            continue
        if info["vendor"] == ASUS:
            nodes.append(info)
    return nodes


def ask(node, report_id, length, command, timeout=0.6):
    """Send [report_id, 0x12, command] and return the reply that echoes it (or a rejection), else None."""
    packet = bytes([report_id, 0x12, command]) + bytes(max(0, length - 3))
    fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
    try:
        while select.select([fd], [], [], 0)[0]:      # drop stale input reports
            try:
                os.read(fd, 128)
            except BlockingIOError:
                break
        os.write(fd, packet)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not select.select([fd], [], [], max(0, deadline - time.time()))[0]:
                break
            try:
                reply = os.read(fd, 128)
            except BlockingIOError:
                continue
            if report_id == 0:
                reply = bytes([0]) + reply             # the kernel strips report ID 0: put it back
            if len(reply) >= 12 and reply[1] == 0x12 and reply[2] == command:
                return reply
            if len(reply) >= 3 and reply[1] == 0xFF and reply[2] == 0xAA:
                return reply                           # "unknown request"
        return None
    finally:
        os.close(fd)


def parse(reply, percent, charging):
    if reply is None or (reply[1] == 0xFF and reply[2] == 0xAA) or not any(reply[1:4]):
        return None
    return {"battery": min(100, reply[percent]), "charging": reply[charging] == 1}


def read_all():
    results = []
    for info in asus_nodes():
        model = MODELS.get(info["product"])
        if not model or info["interface"] != model["interface"]:
            continue
        entry = {"name": model["name"], "product": f"{ASUS}:{info['product']}"}
        if not os.access(info["node"], os.R_OK | os.W_OK):
            results.append(dict(entry, error="permission denied (install the udev rule, see --udev)"))
            continue
        try:
            reading = parse(ask(info["node"], model["report_id"], model["length"], model["command"]),
                            model["percent"], model["charging"])
        except OSError as e:
            results.append(dict(entry, error=str(e)))
            continue
        # No answer: the keyboard is off, asleep or out of range.
        results.append(dict(entry, **reading) if reading else dict(entry, error="no answer (keyboard off or asleep?)"))
    return results


def probe():
    report = []
    for info in asus_nodes():
        entry = dict(info, access=os.access(info["node"], os.R_OK | os.W_OK), tries=[])
        if entry["access"]:
            for command, percent, charging in [(0x01, 11, 9), (0x07, 5, 10)]:
                for report_id, length in [(0x00, 65), (0x03, 64), (0x00, 64), (0x02, 64)]:
                    t = {"command": command, "report_id": report_id, "length": length}
                    try:
                        reply = ask(info["node"], report_id, length, command)
                        t.update(reply=reply.hex(" ") if reply else None, parsed=parse(reply, percent, charging))
                    except OSError as e:
                        t["error"] = str(e)
                    entry["tries"].append(t)
        report.append(entry)
    print(json.dumps(report, indent=1))


def udev_rule():
    lines = ["# Let the logged-in user read the battery of ASUS ROG Falchion keyboards (rog-falchion-battery)"]
    for product in sorted(MODELS):
        lines.append(f'KERNEL=="hidraw*", ATTRS{{idVendor}}=="{ASUS}", ATTRS{{idProduct}}=="{product}", TAG+="uaccess"')
    print("\n".join(lines))


def main():
    args = sys.argv[1:]
    if "--probe" in args:
        probe()
    elif "--udev" in args:
        udev_rule()
    elif "-h" in args or "--help" in args:
        print(__doc__)
    else:
        results = read_all()
        if "--json" in args:
            print(json.dumps(results))
        elif not results:
            print("No supported ROG Falchion found.")
            return 1
        else:
            for r in results:
                if "error" in r:
                    print(f"{r['name']}: {r['error']}")
                else:
                    print(f"{r['name']}: {r['battery']}%" + (" (charging)" if r["charging"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
