#!/usr/bin/env python3
"""
minibeamng.py - shrink a BeamNG.drive install by copying only what's needed
into a new folder. The original install is never touched.

Usage:
    python minibeamng.py <source_dir> [dest_dir] [--dry-run]

    source_dir   path to your BeamNG.drive folder (the one with Bin64, content, ...)
    dest_dir     where the mini copy goes (default: <source>_mini next to source)
    --dry-run    print what would be copied/removed without writing anything

What it keeps:
    - Game core (Bin64, gameengine.zip, tech, lua, shaders, ui, settings, locales)
    - content/art_shapes.zip and the rest of content/assets, audio, cache
    - Levels: only garage_v2.zip
    - Vehicles: only anything matching VEHICLE_KEEP_PREFIXES (e.g. gavril_d_series)
    - Full game UI and CEF files

What it removes:
    - BinLinux (Linux binaries)
    - Crash reporter (crashrpt.dll, CrashSender.exe, ...)
    - Epic Online Services DLLs
    - Pacenote audio files (pacenote_*.ogg) - the lua scripts for pacenotes stay
    - Campaigns (they reference levels/vehicles that are being removed)
    - SVN conflict leftovers (*.mine, *.r12345)
"""

import argparse
import os
import re
import shutil
import sys

# --- Configuration ---------------------------------------------------------

LEVELS_KEEP = {
    "garage_v2.zip",
}

VEHICLE_KEEP_PREFIXES = (
    "gavril",  # Gavril D-Series: kept if present in your install
)

SKIP_DIRS = {
    "BinLinux",   # Linux binaries, comment this line if needed
    "campaigns",  # reference removed levels/vehicles
}

SKIP_FILE_EXACT = {
    # Crash reporter
    "crashrpt.dll",
    "crashrpt_lang.ini",
    "crashsender.exe",
    "crashreporter",
    # Epic Online Services
    "eossdk-win64-shipping.dll",
}

# Files matching these patterns are skipped anywhere in the tree.
SKIP_FILE_PATTERNS = (
    re.compile(r"^pacenote.*\.ogg$", re.IGNORECASE),  # pacenote audio only,
                                                      # keeps pacenote*.lua scripts
    re.compile(r"\.mine$"),                            # SVN conflict leftovers
    re.compile(r"\.r\d+$"),                            # SVN conflict leftovers
)

# Files that must always be copied, no matter what (see Required files.md).
PROTECTED = {
    "content/art_shapes.zip",
}

# --- Logic -----------------------------------------------------------------


def rel_lower(path):
    return path.replace(os.sep, "/").lower()


def should_skip_file(rel_path):
    name = os.path.basename(rel_path)
    name_l = name.lower()
    rl = rel_lower(rel_path)

    if rl in PROTECTED:
        return False

    if name_l in SKIP_FILE_EXACT:
        return True

    for pattern in SKIP_FILE_PATTERNS:
        if pattern.search(name):
            return True

    # Levels: whitelist only
    if rel_path.startswith("content/levels/") and rel_path.endswith(".zip"):
        return name not in LEVELS_KEEP

    # Vehicles: prefix whitelist only
    if rel_path.startswith("content/vehicles/") and rel_path.endswith(".zip"):
        return not any(name_l.startswith(p) for p in VEHICLE_KEEP_PREFIXES)

    return False


def should_skip_dir(rel_path):
    return os.path.basename(rel_path) in SKIP_DIRS


def is_dest_inside_source(source, dest):
    s = os.path.abspath(source) + os.sep
    d = os.path.abspath(dest) + os.sep
    return d.startswith(s) or s.startswith(d)


def run(source, dest, dry_run):
    source = os.path.abspath(source)
    dest = os.path.abspath(dest)

    if not os.path.isdir(source):
        print(f"Error: source folder not found: {source}")
        sys.exit(1)

    if os.path.abspath(source) == dest:
        print("Error: destination must be a different folder than source.")
        sys.exit(1)

    if is_dest_inside_source(source, dest):
        print("Error: destination must not be inside the source folder "
              "(the script would try to re-copy its own output).")
        sys.exit(1)

    # Sanity check: does this look like a BeamNG install?
    if not (os.path.isdir(os.path.join(source, "Bin64"))
            or os.path.isdir(os.path.join(source, "content"))):
        print("Warning: source does not look like a BeamNG.drive install "
              "(no Bin64/ or content/ folder found). Continuing anyway.")

    copied_files = 0
    skipped_files = 0
    copied_bytes = 0
    skipped_bytes = 0

    for dirpath, dirnames, filenames in os.walk(source):
        rel_dir = os.path.relpath(dirpath, source)
        rel_dir_l = "" if rel_dir == "." else rel_dir.replace(os.sep, "/")

        # Prune directories in-place so os.walk skips them.
        keep_dirs = []
        for d in dirnames:
            rel = f"{rel_dir_l}/{d}" if rel_dir_l else d
            if should_skip_dir(rel):
                continue
            keep_dirs.append(d)
        dirnames[:] = keep_dirs

        for f in filenames:
            full = os.path.join(dirpath, f)
            rel = f"{rel_dir_l}/{f}" if rel_dir_l else f

            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0

            if should_skip_file(rel):
                skipped_files += 1
                skipped_bytes += size
                continue

            target = os.path.join(dest, rel)
            if not dry_run:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(full, target)

            copied_files += 1
            copied_bytes += size

    print()
    verb = "Would copy" if dry_run else "Copied"
    print(f"{verb} {copied_files} files ({human_size(copied_bytes)})")
    print(f"Skipped {skipped_files} files ({human_size(skipped_bytes)})")
    if not dry_run:
        print(f"Mini install ready at: {dest}")


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024


def main():
    parser = argparse.ArgumentParser(
        description="Copy a minimal, working BeamNG.drive install to a new folder.")
    parser.add_argument("source", help="Path to your BeamNG.drive folder")
    parser.add_argument("dest", nargs="?", default=None,
                        help="Output folder (default: <source>_mini)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without copying")
    args = parser.parse_args()

    dest = args.dest
    if dest is None:
        src_abs = os.path.abspath(args.source)
        base, ext = os.path.splitext(src_abs)
        dest = f"{base}_mini{ext}"

    print(f"Source: {os.path.abspath(args.source)}")
    print(f"Dest:   {os.path.abspath(dest)}")
    if args.dry_run:
        print("Mode:   dry run (nothing will be written)")
    print()

    run(args.source, dest, args.dry_run)


if __name__ == "__main__":
    main()
