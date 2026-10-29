#!/usr/bin/env python3
"""
JioHotstar APK downloader — APKPure API (no Cloudflare bypass needed).

APKMirror now blocks GitHub runner (datacenter) IPs at the redirect stage even
after a successful Cloudflare challenge, which broke the old trawl/cfbs
scraping. APKPure exposes an official app API (tapi.pureapk.com) that returns
version info and direct download URLs without any challenge — so we use that.

Downloaded file is an XAPK (a zip of the base APK + config.* split APKs +
manifest.json). We pick the arm64-v8a variant, then merge it into a single
APK with APKEditor (which fuses the split resources.arsc tables and native
libs — the same merge the old APKMirror path used).

Output:
  jiohotstar.apk  — merged arm64 APK
  version.txt     — version name (e.g. 26.10.12.2)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

PACKAGE_NAME = os.environ.get("PACKAGE_NAME", "in.startv.hotstar")
OUTPUT_APK = os.environ.get("OUTPUT", "jiohotstar.apk")
TARGET_ARCH = os.environ.get("ARCH", "arm64-v8a").lower()
if TARGET_ARCH == "arm-v7a":
    TARGET_ARCH = "armeabi-v7a"
APKEDITOR_JAR = os.environ.get("APKEDITOR_JAR", "/usr/local/bin/apkeditor.jar")

API_URL = "https://tapi.pureapk.com/v3/get_app_his_version"
API_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Pixel 5 Build/TQ3A.230901.001); APKPure/3.20.34 (Aegon)",
    "Ual-Access-Businessid": "projecta",
    "Ual-Access-ProjectA": '{"device_info":{"abis":["x86_64","arm64-v8a","x86","armeabi-v7a","armeabi"],"android_id":"50f838123d9a9c94","brand":"google","country":"United States","country_code":"US","imei":"","language":"en-US","manufacturer":"Google","mode":"Pixel 5","os_ver":"33","os_ver_name":"13","platform":1,"product":"redfin","screen_height":1080,"screen_width":1920},"host_app_info":{"build_no":"468","channel":"","md5":"6756e53158d6f6c013650a40d8f1147b","pkg_name":"com.apkpure.aegon","sdk_ver":"3.20.34","version_code":3203427,"version_name":"3.20.34"}}',
    "Connection": "Keep-Alive",
}


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def err(msg: str) -> None:
    print(f"::error::{msg}", flush=True)


def _http_get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout)


def apkpure_versions(package: str):
    """Return the raw version_list from APKPure's API, or None."""
    params = "?" + "&".join(
        [f"package_name={urllib.request.quote(package)}", "hl=en"]
    )
    req = urllib.request.Request(API_URL + params, headers=API_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        err(f"APKPure API request failed: {e}")
        return None
    versions = data.get("version_list") or []
    if not versions:
        err("APKPure API returned no versions")
        return None
    return versions


def latest_asset_urls(versions, version_name: str):
    """Collect all download URLs for the given version (covers arch variants)."""
    urls = []
    for v in versions:
        if (v.get("version_name") or "").strip() != version_name:
            continue
        asset = v.get("asset") or {}
        for u in asset.get("urls") or []:
            if u:
                urls.append(u)
    return urls


def xapk_has_arch(path: str, arch: str) -> bool:
    """Check whether the XAPK contains a config.<arch>.apk native split."""
    underscore = arch.replace("-", "_")  # arm64-v8a -> arm64_v8a
    want = f"config.{underscore}.apk"
    try:
        with zipfile.ZipFile(path, "r") as z:
            return any(n.endswith(want) for n in z.namelist())
    except Exception:
        return False


def download(url: str, output: str) -> None:
    log(f"Downloading XAPK ({url[:70]}...)")
    try:
        with _http_get(url, timeout=600) as resp, open(output, "wb") as f:
            shutil.copyfileobj(resp, f)
    except Exception as e:
        err(f"download failed: {e}")
        sys.exit(1)
    size = os.path.getsize(output) if os.path.exists(output) else 0
    if size < 1_000_000:
        err(f"download too small ({size} bytes)")
        sys.exit(1)
    log(f"Downloaded {size / 1024 / 1024:.1f} MB")


def merge_via_apkeditor(xapk_path: str) -> None:
    """Merge the XAPK (base + splits) into a single APK via APKEditor."""
    if not os.path.exists(APKEDITOR_JAR):
        err(f"APKEditor jar not found: {APKEDITOR_JAR}")
        sys.exit(1)
    cmd = ["java", "-jar", APKEDITOR_JAR, "m", "-i", xapk_path, "-o", OUTPUT_APK, "-f"]
    log(f"Running APKEditor merge ...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except FileNotFoundError:
        err("java not found")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        err("APKEditor merge timed out")
        sys.exit(1)
    if result.returncode != 0:
        err("APKEditor merge failed")
        log(result.stdout[-4000:] if result.stdout else "")
        log(result.stderr[-4000:] if result.stderr else "")
        sys.exit(1)
    if not os.path.exists(OUTPUT_APK) or os.path.getsize(OUTPUT_APK) < 5_000_000:
        err("merged APK too small or missing")
        sys.exit(1)
    log(f"Ready: {OUTPUT_APK} ({os.path.getsize(OUTPUT_APK) / 1024 / 1024:.1f} MB)")


def main() -> int:
    print("=== JioHotstar APK downloader (APKPure API) ===", flush=True)
    print(f"  Package:     {PACKAGE_NAME}", flush=True)
    print(f"  Target arch: {TARGET_ARCH}", flush=True)

    versions = apkpure_versions(PACKAGE_NAME)
    if versions is None:
        return 1

    version_name = (versions[0].get("version_name") or "").strip()
    if not version_name:
        err("empty latest version")
        return 1
    log(f"Latest version: {version_name}")

    urls = latest_asset_urls(versions, version_name)
    if not urls:
        err(f"no download URLs for {version_name}")
        return 1
    log(f"{len(urls)} variant URL(s) for {version_name}")

    # Download variants until we find one matching the target arch.
    downloaded = "downloaded.xapk"
    chosen = None
    for u in urls:
        download(u, downloaded)
        if xapk_has_arch(downloaded, TARGET_ARCH):
            chosen = downloaded
            log(f"variant has {TARGET_ARCH} native libs")
            break
        log("variant lacks target arch — trying next")
        os.remove(downloaded)

    if chosen is None:
        # Fall back to the last downloaded file if arch detection never matched
        # (single-arch XAPK or arch split named differently).
        if os.path.exists(downloaded):
            log("no arch-specific variant found — using last downloaded file")
            chosen = downloaded
        else:
            err("no usable XAPK downloaded")
            return 1

    merge_via_apkeditor(chosen)

    with open("version.txt", "w") as f:
        f.write(version_name)

    print("\n=== SUCCESS ===", flush=True)
    print(f"  Version: {version_name}", flush=True)
    print(f"  APK:     {OUTPUT_APK} ({os.path.getsize(OUTPUT_APK) / 1024 / 1024:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
