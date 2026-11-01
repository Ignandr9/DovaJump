#!/usr/bin/env python3
"""
DovaJump Release Packager
Generates the installable mod manager archive (Vortex / Mod Organizer 2) for the DovaJump DLL patch.

The original mod's ESP, scripts and animations (Nexus 125550) are not packaged: its permissions
forbid redistribution. Users install the original mod first.

Zero external dependencies (uses standard Python 3.8+ libraries).
"""

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

VERSION = "1.1.0"
VERSION_STR = "1.1.0.0"

META_INI_NG = f"""[General]
gameName=SkyrimSE
modid=190782
version={VERSION_STR}
newestVersion={VERSION_STR}
category=34
notes=Dova Jump NG Patch ported and verified for Skyrim AE 1.7.104
author=BlessingS91 & Ignandr9
installedFiles\\size=0
"""


def sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_dll(repo_root: Path, explicit_path: str = None) -> Path:
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            return p
        raise FileNotFoundError(f"Specified DLL does not exist: {explicit_path}")

    candidates = [
        repo_root / "build" / "DovaJump.dll",
        repo_root / "build" / "Release" / "DovaJump.dll",
        repo_root / "out" / "build" / "x64-Release" / "DovaJump.dll",
        repo_root / "cmake-build-release" / "DovaJump.dll",
    ]
    for c in candidates:
        if c.is_file():
            return c

    raise FileNotFoundError(
        "Could not find DovaJump.dll in standard build locations. "
        "Build the project first or provide --dll path."
    )


def package_ng(dll_path: Path, ini_path: Path, license_path: Path, dist_dir: Path) -> Path:
    archive_name = f"DovaJump-NG-Patch-v{VERSION}-AE17104.zip"
    archive_path = dist_dir / archive_name

    with tempfile.TemporaryDirectory() as tmpdir:
        stage = Path(tmpdir)
        plugins_dir = stage / "SKSE" / "Plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(dll_path, plugins_dir / "DovaJump.dll")
        if ini_path.is_file():
            shutil.copy2(ini_path, plugins_dir / "JumpRequirements.ini")
        # MIT requires the copyright notice to ship with copies of the software.
        shutil.copy2(license_path, plugins_dir / "DovaJump-LICENSE.txt")

        with open(stage / "meta.ini", "w", encoding="utf-8") as f:
            f.write(META_INI_NG)

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(stage):
                for file in sorted(files):
                    abs_file = Path(root) / file
                    arcname = abs_file.relative_to(stage)
                    zf.write(abs_file, arcname)

    return archive_path


def main():
    parser = argparse.ArgumentParser(description="Package DovaJump releases for mod managers")
    parser.add_argument("--dll", help="Path to compiled DovaJump.dll")
    parser.add_argument("--ini", help="Path to JumpRequirements.ini")
    parser.add_argument("--dist", help="Output directory for packaged archives", default="dist")
    # Accepted for older CI/wrapper calls; the NG patch is the only archive.
    parser.add_argument("--ng-only", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    dist_dir = (repo_root / args.dist).resolve()
    dist_dir.mkdir(parents=True, exist_ok=True)

    dll_path = find_dll(repo_root, args.dll)
    print(f"Found DLL: {dll_path} ({dll_path.stat().st_size} bytes)")

    ini_path = Path(args.ini) if args.ini else (repo_root / "assets" / "SKSE" / "Plugins" / "JumpRequirements.ini")
    if not ini_path.is_file():
        # Fallback to sibling NG patch directory if running in development workspace
        sibling_ini = repo_root.parent / "Dova Jump NG patch" / "SKSE" / "Plugins" / "JumpRequirements.ini"
        if sibling_ini.is_file():
            ini_path = sibling_ini

    license_path = repo_root / "LICENSE"
    if not license_path.is_file():
        sys.exit(f"LICENSE not found at {license_path}; refusing to package without the MIT notice.")

    print("==================================================")
    print("DovaJump Mod Manager Release Packager")
    print("==================================================")

    print("Packaging NG Patch archive...")
    ng_zip = package_ng(dll_path, ini_path, license_path, dist_dir)
    created_archives = [ng_zip]
    print(f"      Created: {ng_zip.name}")

    print("\nRelease Archives Summary:")
    print("--------------------------------------------------")
    for arc in created_archives:
        checksum = sha256_file(arc)
        size_kb = arc.stat().st_size / 1024
        print(f"Archive:  {arc.name} ({size_kb:.1f} KB)")
        print(f"SHA-256:  {checksum}")
        print("Contents:")
        with zipfile.ZipFile(arc, "r") as zf:
            for info in zf.infolist()[:10]:
                print(f"  - {info.filename}")
            if len(zf.infolist()) > 10:
                print(f"  ... ({len(zf.infolist()) - 10} more files)")
        print("--------------------------------------------------")

    print("Packaging complete.")


if __name__ == "__main__":
    main()
