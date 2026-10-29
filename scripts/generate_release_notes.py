#!/usr/bin/env python3
"""
Generate minimal release notes (markdown) for the current build.

Reads environment variables (set by the workflow):
  NEXT_VER_CODE   — sequential build number (e.g. "260001")
  APK_VERSION     — JioHotstar version name (e.g. "26.07.20.3")
  FINAL_NAME      — final APK filename
  ARCH            — target architecture (e.g. "arm64-v8a")

Output: writes markdown to stdout.

NOTE: the line "JioHotstar version: <x.y.z>" is parsed by ci.yml's update
checker to detect the last released version — keep that exact format.
"""
from __future__ import annotations

import os
import sys
import urllib.parse
from datetime import datetime, timezone


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default) or default


def main() -> int:
    next_ver_code = env("NEXT_VER_CODE")
    apk_version = env("APK_VERSION", "unknown")
    final_name = env("FINAL_NAME", "JioHotstar-Premium.apk")
    arch = env("ARCH", "arm64-v8a")
    repo = os.environ.get("GITHUB_REPOSITORY", "gramnaters/patcher-build")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    asset_url = f"{server}/{repo}/releases/download/{next_ver_code}/{urllib.parse.quote(final_name)}"

    lines = [
        f"## JioHotstar Premium v{apk_version}",
        "",
        f"**Build**: `{next_ver_code}`  •  **Built**: {now}",
        "",
        f"[**Download {final_name}**]({asset_url})",
        "",
        f"JioHotstar version: {apk_version}  •  Architecture: `{arch}`",
        "",
        "Unofficial patched build for personal use.",
    ]

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
