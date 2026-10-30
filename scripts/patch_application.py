#!/usr/bin/env python3
"""Patch the Application class to call CookieSeeder via reflection.

Replacing a direct ``invoke-static CookieSeeder.seedIfNeeded`` with reflection
because newer Zeo builds push classes.dex to Android's 64K method-index
limit. A direct call adds one more method_id and overflows it:

    Unsigned short value out of range: 65536

Reflection references CookieSeeder only as a string constant (Class.forName),
and uses Class.forName / Class.getMethod / Method.invoke which the app already
references in classes.dex — so zero new method_ids are introduced.

Usage: python3 patch_application.py <decompiled_dir>
"""
import os
import re
import sys

CLASS_NAME = "com.hotstar.patch.CookieSeeder"
METHOD_NAME = "seedIfNeeded"

# NOTE: v1 is left untouched — the original onCreate() uses v1 as a boolean
# (const/4 v1, 0x1 ... iput-boolean v1) *after* the injection point, and
# clobbering it trips the dex verifier. We use v0,v2..v7 instead (all of
# which the original code reassigns right after this block).
REFLECT_BLOCK = """    const-string v0, "com.hotstar.patch.CookieSeeder"

    invoke-static {v0}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v2

    const-string v3, "seedIfNeeded"

    const/4 v4, 0x1

    new-array v5, v4, [Ljava/lang/Class;

    const-class v6, Landroid/content/Context;

    const/4 v7, 0x0

    aput-object v6, v5, v7

    invoke-virtual {v2, v3, v5}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v2

    const/4 v3, 0x1

    new-array v4, v3, [Ljava/lang/Object;

    const/4 v5, 0x0

    aput-object p0, v4, v5

    const/4 v6, 0x0

    invoke-virtual {v2, v6, v4}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v2
"""

# Reflection block uses locals v0..v4 -> 5 registers minimum.
MIN_LOCALS = 5


def read_manifest_app_class(root: str) -> str:
    """Extract android:name from the decompiled AndroidManifest.xml."""
    manifest = os.path.join(root, "AndroidManifest.xml")
    with open(manifest, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    m = re.search(r"<application[^>]*android:name=\"([^\"]+)\"", text)
    if m:
        return m.group(1)
    return ""


def find_app_smali(root: str, app_class: str) -> str | None:
    """Locate the smali file for the Application class."""
    rel = app_class.replace(".", "/") + ".smali"
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        path = os.path.join(root, d, rel)
        if os.path.isfile(path):
            return path
    # Fallback: search by simple class name
    simple = app_class.split(".")[-1] + ".smali"
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        for dirpath, _dirs, files in os.walk(os.path.join(root, d)):
            if simple in files:
                return os.path.join(dirpath, simple)
    return None


def bump_locals(lines: list[str], method_start: int, needed: int) -> list[str]:
    """Ensure the method has at least `needed` locals; bump .locals if not."""
    for i in range(method_start, min(method_start + 8, len(lines))):
        m = re.match(r"^(\s*)\.locals\s+(\d+)", lines[i])
        if m:
            cur = int(m.group(2))
            if cur < needed:
                lines[i] = f"{m.group(1)}.locals {needed}"
            return lines
    # No .locals found (uses .registers) — leave as-is; caller checks separately
    return lines


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: patch_application.py <decompiled_dir>", file=sys.stderr)
        return 2
    root = sys.argv[1]

    app_class = read_manifest_app_class(root)
    if not app_class:
        print("::error::Application android:name not found in manifest")
        return 1
    print(f"Application class: {app_class}")

    smali_path = find_app_smali(root, app_class)
    if not smali_path:
        print(f"::error::Application smali not found for {app_class}")
        return 1
    print(f"Smali file: {smali_path}")

    with open(smali_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().split("\n")

    if "CookieSeeder" in "\n".join(lines):
        print("CookieSeeder already injected — skipping")
        return 0

    # Find onCreate (preferred) or fall back to <init>
    method_start = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s == ".method public final onCreate()V" or s.endswith(" onCreate()V"):
            method_start = i
            break
    if method_start is None:
        for i, ln in enumerate(lines):
            if ".method public constructor <init>()V" in ln:
                method_start = i
                break
    if method_start is None:
        print("::error::no onCreate()V or <init>()V found")
        return 1

    # Find invoke-super within this method body
    inject_at = None
    for i in range(method_start, len(lines)):
        if lines[i].strip() == ".end method":
            break
        if "invoke-super" in lines[i]:
            inject_at = i
            break
    if inject_at is None:
        print("::error::invoke-super not found in target method")
        return 1

    # Ensure enough locals (v0..v4 needed)
    if MIN_LOCALS > 0:
        bump_locals(lines, method_start, MIN_LOCALS)

    block_lines = REFLECT_BLOCK.rstrip("\n").split("\n")
    new_lines = lines[: inject_at + 1] + block_lines + lines[inject_at + 1 :]

    with open(smali_path, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(new_lines))

    print(f"Injected reflection block after line {inject_at + 1} ({lines[inject_at].strip()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
