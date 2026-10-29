#!/usr/bin/env python3
"""
Check the latest JioHotstar version available on APKPure.

Uses APKPure's official app API (tapi.pureapk.com), which returns direct
version info and download links WITHOUT any Cloudflare bypass. This replaces
the old APKMirror + trawl/cfbs scraping, which broke when APKMirror started
blocking datacenter (GitHub runner) IPs.

Output: prints the latest version string (e.g. "26.10.12.2") to stdout.
        On failure, prints nothing and exits with code 1.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

PACKAGE_NAME = os.environ.get("PACKAGE_NAME", "in.startv.hotstar")

API_URL = "https://tapi.pureapk.com/v3/get_app_his_version"
API_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Pixel 5 Build/TQ3A.230901.001); APKPure/3.20.34 (Aegon)",
    "Ual-Access-Businessid": "projecta",
    "Ual-Access-ProjectA": '{"device_info":{"abis":["x86_64","arm64-v8a","x86","armeabi-v7a","armeabi"],"android_id":"50f838123d9a9c94","brand":"google","country":"United States","country_code":"US","imei":"","language":"en-US","manufacturer":"Google","mode":"Pixel 5","os_ver":"33","os_ver_name":"13","platform":1,"product":"redfin","screen_height":1080,"screen_width":1920},"host_app_info":{"build_no":"468","channel":"","md5":"6756e53158d6f6c013650a40d8f1147b","pkg_name":"com.apkpure.aegon","sdk_ver":"3.20.34","version_code":3203427,"version_name":"3.20.34"}}',
    "Connection": "Keep-Alive",
}


def latest_version(package: str):
    """Return the latest version_name for the package, or None."""
    params = "?" + "&".join(
        [f"package_name={urllib.request.quote(package)}", "hl=en"]
    )
    req = urllib.request.Request(API_URL + params, headers=API_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

    versions = data.get("version_list") or []
    if not versions:
        return None
    name = (versions[0].get("version_name") or "").strip()
    return name or None


def main() -> int:
    version = latest_version(PACKAGE_NAME)
    if version:
        print(version)
        return 0
    print(f"ERROR: could not fetch latest version from APKPure for {PACKAGE_NAME}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
