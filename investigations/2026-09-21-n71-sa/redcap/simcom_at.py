#!/usr/bin/env python3
"""Minimal AT client for the SIMCom SDX module over raw USB (macOS has no driver for its vendor-class ports).
Usage: at.py 'ATI' 'AT+CPSI?' ...   (interface 2 = 'CDEV Serial' AT port)"""
import sys, time, usb.core, usb.util

d = usb.core.find(idVendor=0x1E0E, idProduct=0x9071)
if d is None:
    sys.exit("SIMCom module not found")
IF = 2
if d.is_kernel_driver_active(IF) if hasattr(d, "is_kernel_driver_active") else False:
    d.detach_kernel_driver(IF)
usb.util.claim_interface(d, IF)
intf = d.get_active_configuration()[(IF, 0)]
ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
                                 and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK)

def drain(timeout_s):
    buf, end = b"", time.time() + timeout_s
    while time.time() < end:
        try:
            buf += bytes(ep_in.read(4096, timeout=200))
            if buf.rstrip().endswith((b"OK", b"ERROR")) or b"+CME ERROR" in buf:
                break
        except usb.core.USBTimeoutError:
            pass
    return buf.decode(errors="replace")

drain(0.3)  # flush unsolicited output
for cmd in sys.argv[1:]:
    ep_out.write((cmd + "\r").encode())
    tmo = 180 if cmd.upper().startswith("AT+COPS=?") else 5
    out = drain(tmo).replace("\r", "").strip()
    print(f">>> {cmd}\n{out}\n")
usb.util.release_interface(d, IF)
