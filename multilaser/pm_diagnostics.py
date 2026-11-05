"""
Power meter enumeration diagnostics.

Builds a plain-text report for working out why a Thorlabs meter appears
more than once in the scan, or which entry is the real one. It covers:

* Python / PyVISA / pyvisa-py / pyusb versions
* Every VISA backend that loads (the default, NI/IVI and pyvisa-py) and
  every resource each lists, so backend-specific duplicates stand out
* Each Thorlabs entry parsed into VID / PID / serial / USB interface, and
  probed with ``*IDN?`` and ``SYST:SENS:IDN?`` (meter and sensor head)
* Raw USB devices with Thorlabs' vendor ID (pyusb), with interface classes
  (USBTMC vs DFU etc.)
* On Windows, Device Manager entries for VID_1313 **including devices not
  currently present** (stale "ghost" entries) and their drivers

Run from the GUI (Settings tab -> Diagnose...) or from a terminal::

    python -m multilaser.pm_diagnostics            # probe every entry
    python -m multilaser.pm_diagnostics --no-probe # list only
"""

import argparse
import datetime
import platform
import subprocess
import sys
from typing import Callable, Dict, Iterable, List, Optional

from multilaser._version import __version__
from multilaser.power_meter_controller import (
    RSRC_NFOUND_HINT,
    THORLABS_VID,
    MeterCandidate,
)

# Interface classes worth naming in the USB section
_USB_CLASSES = {
    (0xFE, 0x01): "DFU (firmware update)",
    (0xFE, 0x03): "USBTMC (test & measurement)",
    (0xFF, None): "vendor-specific",
}


def _version_of(module_name: str) -> str:
    try:
        module = __import__(module_name)
        return str(getattr(module, "__version__", "installed (version unknown)"))
    except Exception as e:
        return f"not available ({type(e).__name__}: {e})"


def _resource_managers() -> List[tuple]:
    """(label, ResourceManager or error string) for each backend that loads."""
    try:
        import pyvisa
    except ImportError as e:
        return [("pyvisa", f"PyVISA not installed: {e}")]
    out = []
    for label, spec in (
        ("default (what the app uses)", None),
        ("@ivi (NI-VISA / vendor VISA)", "@ivi"),
        ("@py (pyvisa-py)", "@py"),
    ):
        try:
            rm = pyvisa.ResourceManager() if spec is None else pyvisa.ResourceManager(spec)
            out.append((label, rm))
        except Exception as e:
            out.append((label, f"{type(e).__name__}: {e}"))
    return out


def _describe_backend(rm) -> str:
    lib = getattr(rm, "visalib", None)
    path = getattr(lib, "library_path", "")
    return f"{lib!r}" + (f" ({path})" if path else "")


def _probe(rm, resource: str, timeout_ms: int) -> List[str]:
    """Open resource, query meter and sensor identity, close. Never raises."""
    import time
    lines = []
    start = time.monotonic()
    inst = None
    try:
        inst = rm.open_resource(resource, open_timeout=timeout_ms)
        inst.timeout = timeout_ms
        lines.append(f"      open:      OK ({time.monotonic() - start:.2f} s)")
        for cmd in ("*IDN?", "SYST:SENS:IDN?"):
            try:
                lines.append(f"      {cmd:<15}{inst.query(cmd).strip()}")
            except Exception as e:
                lines.append(f"      {cmd:<15}FAILED {type(e).__name__}: {e}")
    except Exception as e:
        lines.append(
            f"      open:      FAILED after {time.monotonic() - start:.2f} s "
            f"- {type(e).__name__}: {e}"
        )
        if "RSRC_NFOUND" in str(e):
            lines.append(f"      hint:      {RSRC_NFOUND_HINT}")
    finally:
        if inst is not None:
            try:
                inst.close()
            except Exception:
                pass
    return lines


def _visa_section(
    probe: bool, in_use: Dict[str, str], names: Callable[[str], str], timeout_ms: int
) -> List[str]:
    lines = ["== VISA backends =="]
    seen_backends = set()
    for label, rm in _resource_managers():
        lines.append("")
        if isinstance(rm, str):
            lines.append(f"-- {label}: unavailable ({rm})")
            continue
        backend = _describe_backend(rm)
        duplicate_backend = backend in seen_backends
        seen_backends.add(backend)
        lines.append(f"-- {label}: {backend}")
        try:
            resources = list(rm.list_resources("?*::INSTR"))
        except Exception as e:
            lines.append(f"   list_resources failed: {type(e).__name__}: {e}")
            continue
        lines.append(f"   {len(resources)} INSTR resource(s):")
        for r in resources:
            lines.append(f"     {r}")
        thorlabs = [
            MeterCandidate.from_resource(r)
            for r in resources
            if MeterCandidate.from_resource(r).vid == THORLABS_VID
        ]
        if not thorlabs:
            continue
        lines.append(f"   Thorlabs (VID 0x{THORLABS_VID:04X}) entries:")
        serials = [c.serial for c in thorlabs]
        for c in thorlabs:
            notes = []
            if serials.count(c.serial) > 1:
                notes.append("SAME SERIAL AS ANOTHER ENTRY")
            name = names(c.serial)
            if name:
                notes.append(f'named "{name}"')
            lines.append(
                f"   * {c.resource}\n"
                f"      PID {c.pid_text}  serial {c.serial or '?'}  "
                f"interface {c.interface if c.interface is not None else '-'}"
                + (f"  [{'; '.join(notes)}]" if notes else "")
            )
            if c.resource in in_use:
                lines.append(f"      (connected in the app - not probed) {in_use[c.resource]}")
            elif probe and not duplicate_backend:
                lines.extend(_probe(rm, c.resource, timeout_ms))
        if duplicate_backend:
            lines.append("   (same library as above - not probed again)")
    return lines


def _usb_section() -> List[str]:
    lines = ["== Raw USB devices (pyusb) =="]
    try:
        import usb.core
        import usb.util
    except ImportError as e:
        return lines + [f"pyusb not available: {e}"]
    try:
        devices = list(usb.core.find(find_all=True, idVendor=THORLABS_VID))
    except Exception as e:
        return lines + [f"USB enumeration failed (no libusb backend?): {type(e).__name__}: {e}"]
    lines.append(f"{len(devices)} device(s) with VID 0x{THORLABS_VID:04X}")
    for dev in devices:
        try:
            serial = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else ""
        except Exception as e:
            serial = f"(unreadable: {type(e).__name__})"
        try:
            product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else ""
        except Exception:
            product = ""
        lines.append(
            f"* bus {dev.bus} address {dev.address}: PID 0x{dev.idProduct:04X} "
            f"{product} serial {serial}"
        )
        try:
            for cfg in dev:
                for intf in cfg:
                    cls, sub = intf.bInterfaceClass, intf.bInterfaceSubClass
                    desc = _USB_CLASSES.get((cls, sub)) or _USB_CLASSES.get((cls, None), "")
                    lines.append(
                        f"    interface {intf.bInterfaceNumber}: class 0x{cls:02X} "
                        f"subclass 0x{sub:02X} {desc}"
                    )
        except Exception as e:
            lines.append(f"    (interfaces unreadable: {type(e).__name__}: {e})")
    return lines


def _windows_section() -> List[str]:
    lines = ["== Windows Device Manager (VID_1313, including not-present) =="]
    script = (
        "Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_1313' } | "
        "Sort-Object InstanceId | "
        "Format-List Present,Status,Class,FriendlyName,Service,InstanceId | "
        "Out-String -Width 300"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        text = (result.stdout or "").strip() or "(no matching devices)"
        lines.append(text)
        if result.stderr.strip():
            lines.append(f"stderr: {result.stderr.strip()}")
        lines.append(
            "Present=False entries are remembered by Windows but not plugged in.\n"
            "Each PM100USB has two interfaces: MI_00 (TMC, the measurement "
            "interface) and MI_01 (DFU, firmware update only; never a VISA "
            "resource).\nFor this app's NI-VISA backend, the present MI_00 "
            "entries need Service 'Usbtmc' (IVI/VISA driver); 'WINUSB' "
            "(ThorlabsUSBDevice) is Thorlabs' own driver, which NI-VISA "
            "cannot open."
        )
    except Exception as e:
        lines.append(f"PowerShell query failed: {type(e).__name__}: {e}")
    return lines


def collect_report(
    probe: bool = True,
    in_use: Optional[Dict[str, str]] = None,
    names: Optional[Callable[[str], str]] = None,
    timeout_ms: int = 2000,
) -> str:
    """Build the diagnostics report.

    Args:
        probe: Open each Thorlabs entry and query its identity.
        in_use: {resource: description} for meters the app has open; these
            are listed but not probed.
        names: serial -> friendly name lookup (MeterRegistry.name).
        timeout_ms: Open/query timeout per entry.
    """
    in_use = in_use or {}
    names = names or (lambda serial: "")
    sections: List[Iterable[str]] = [
        [
            "Multi-Laser Controller power meter diagnostics",
            f"Generated {datetime.datetime.now().isoformat(timespec='seconds')}",
            f"App {__version__} ({'frozen' if getattr(sys, 'frozen', False) else 'source'})",
            f"Python {sys.version.split()[0]} on {platform.platform()}",
            f"pyvisa {_version_of('pyvisa')}; pyvisa-py {_version_of('pyvisa_py')}; "
            f"pyusb {_version_of('usb')}",
        ],
        _visa_section(probe, in_use, names, timeout_ms),
        _usb_section(),
    ]
    if sys.platform == "win32":
        sections.append(_windows_section())
    return "\n\n".join("\n".join(s) for s in sections) + "\n"


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--no-probe", action="store_true",
                        help="list entries without opening them")
    parser.add_argument("--timeout", type=int, default=2000,
                        help="open/query timeout per entry in ms (default 2000)")
    args = parser.parse_args(argv)
    names = None
    try:
        from PyQt6.QtCore import QSettings
        from multilaser.meter_registry import MeterRegistry
        names = MeterRegistry(QSettings("MultiLaserBox", "LaserController")).name
    except Exception:
        pass
    print(collect_report(probe=not args.no_probe, names=names, timeout_ms=args.timeout))


if __name__ == "__main__":
    main()
