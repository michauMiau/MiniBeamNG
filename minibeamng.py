#!/usr/bin/env python3
"""
minibeamng.py - shrink a BeamNG.drive install by copying only what's needed
into a new folder. The original install is never touched.

Usage:
    python minibeamng.py <source_dir> [dest_dir] [--profile PROFILE] [options]

    source_dir   path to your BeamNG.drive folder (the one with Bin64, content, ...)
    dest_dir     where the mini copy goes (default: <source>_mini next to source)

Profiles:
    full       Keep all levels and vehicles. Remove campaigns, crash reporter,
               EOS, pacenote audio, docs, support.exe, roadArchitect, tech.
               Still ~45GB (won't fit on 32GB USB).
    compact    Keep only pickup, common, unicycle vehicles and garage_v2 level.
               Remove campaigns, crash reporter, EOS, pacenote audio, docs.
               ~14GB (fits on 16GB USB).
    extreme    Like compact but also strip unnecessary UI apps, keep only
               English locale. ~12GB. Add --recompress for ~8-10GB.

To fit on a 32GB USB, use --profile full and manually remove unwanted
levels/vehicles from the source before running, or edit the levels_keep
and vehicles_keep sets in the script.

Options:
    --profile PROFILE     full, compact, or extreme (default: compact)
    --dry-run             Show what would happen without copying
    --estimate            Estimate final size without copying (fast)
    --keep-linux          Keep the BinLinux folder
    --recompress          Re-compress content zip files (deflate, max level).
                          Slower but saves GBs. Only applies in extreme mode.
    --skip-recompress     Override: don't re-compress even in extreme mode
"""

import argparse
import copy
import os
import re
import shutil
import sys
import zipfile

# --- Profile definitions ----------------------------------------------------

PROFILES = {
    "full": {
        "levels_keep": None,           # None = keep all
        "vehicles_keep": None,         # None = keep all
        "skip_dirs": ["campaigns", "flowgraphEditor"],
        "skip_files": {
            "crashrpt.dll",
            "crashrpt_lang.ini",
            "crashsender.exe",
            "crashreporter",
            "eossdk-win64-shipping.dll",
            "libeossdk-linux-shipping.so",
        },
        "strip_ui_apps": False,
        "strip_locales": False,
        "recompress": False,
        "description": "All levels and vehicles, minus campaigns/docs/crash reporter",
    },
    "compact": {
        "levels_keep": {"garage_v2.zip"},
        "vehicles_keep": {"common", "pickup", "unicycle"},
        "skip_dirs": ["campaigns", "flowgraphEditor"],
        "skip_files": {
            "crashrpt.dll",
            "crashrpt_lang.ini",
            "crashsender.exe",
            "crashreporter",
            "eossdk-win64-shipping.dll",
            "libeossdk-linux-shipping.so",
        },
        "strip_ui_apps": False,
        "strip_locales": False,
        "recompress": False,
        "description": "pickup + common + unicycle + garage_v2 only",
    },
    "extreme": {
        "levels_keep": {"garage_v2.zip"},
        "vehicles_keep": {"common", "pickup", "unicycle"},
        "skip_dirs": ["campaigns", "flowgraphEditor"],
        "skip_files": {
            "crashrpt.dll",
            "crashrpt_lang.ini",
            "crashsender.exe",
            "crashreporter",
            "eossdk-win64-shipping.dll",
            "libeossdk-linux-shipping.so",
        },
        "strip_ui_apps": True,
        "strip_locales": True,
        "recompress": False,
        "description": "Minimal install with UI/locale stripping. Add --recompress for <5GB.",
    },
}

# UI apps to strip in extreme mode (radio test, debug tools, etc.).
# Kept lowercase: compared against an already-lowercased path.
STRIP_UI_APPS = {
    "radio",
    "radiotest",
    "soundtest",
    "cameratest",
    "debug",
    "devtools",
    "benchmark",
    "perf",
    "rallyvisualpacenotes",
    "trafficsignaltest",
}

SKIP_DOC_FILES = {
    "EULA.pdf",
    "PrivacyPolicy.pdf",
    "PrivacyPolicy-tech.pdf",
    "licenses.txt",
    "lua/bCDDL-1.1.txt",
}

# The one translation folder extreme mode keeps.
KEEP_LOCALE = "en"

# Files to remove in all profiles
SKIP_FILES_ALL = {
    "support.exe",
}

# Directories to remove in all profiles
SKIP_DIRS_ALWAYS = {
    "roadArchitect",
    "tech",
}

# Pacenote pattern (audio only, keep lua scripts)
PACENOTE_AUDIO = re.compile(r"^pacenote.*\.ogg$", re.IGNORECASE)
SVN_CONFLICT = re.compile(r"(\.mine$|\.r\d+$)")

# Files that must always be copied
PROTECTED = {
    "content/art_shapes.zip",
}


def get_profile(name):
    """Return a deep copy of the named profile, or exit if it doesn't exist."""
    p = PROFILES.get(name)
    if not p:
        print(f"Unknown profile '{name}'. Options: {', '.join(PROFILES)}")
        sys.exit(1)
    # Deep copy: callers mutate the copy (e.g. toggling "recompress"), and a
    # shallow copy would let that leak into PROFILES for the whole process.
    return copy.deepcopy(p)


def should_skip_file(rel, profile):
    """Return True when a file at rel_path should be left out of the copy."""
    name = os.path.basename(rel)
    name_l = name.lower()
    rl = rel.replace(os.sep, "/").lower()

    # Always protected
    if rl in PROTECTED:
        return False

    # Docs and PDFs
    if rl in SKIP_DOC_FILES:
        return True
    if name_l.endswith(".pdf"):
        return True

    # Files to always skip
    if name_l in SKIP_FILES_ALL:
        return True

    # Profile-specific skip list
    if name_l in profile["skip_files"]:
        return True

    # Pacenote audio
    if PACENOTE_AUDIO.search(name):
        return True

    # SVN conflict leftovers
    if SVN_CONFLICT.search(name):
        return True

    # Levels whitelist
    if rl.startswith("content/levels/") and rl.endswith(".zip"):
        if profile["levels_keep"] is not None:
            return name not in profile["levels_keep"]

    # Vehicles whitelist
    if rl.startswith("content/vehicles/") and rl.endswith(".zip"):
        if profile["vehicles_keep"] is not None:
            return not any(name_l.startswith(v) for v in profile["vehicles_keep"])

    # UI app stripping (extreme mode)
    if profile["strip_ui_apps"] and rl.startswith("ui/modules/apps/"):
        parts = rl.split("/")
        if len(parts) >= 4 and parts[3] in STRIP_UI_APPS:
            return True

    # Locale stripping (extreme mode) - keep only English.
    # Path shape: locales/translations/<lang>/... so the lang is index 2.
    if profile["strip_locales"] and rl.startswith("locales/translations/"):
        parts = rl.split("/")
        if len(parts) >= 3 and parts[2] != KEEP_LOCALE:
            return True

    return False


def should_skip_dir(rel, profile):
    """Return True when a directory at rel should be pruned from the walk."""
    name = os.path.basename(rel)
    if name in profile["skip_dirs"]:
        return True
    if name in SKIP_DIRS_ALWAYS:
        return True
    return False


def rezip_file(path, dry_run):
    """Re-compress a zip file using deflate instead of stored."""
    if dry_run:
        print(f"  [dry-run] Would recompress: {path}")
        return

    tmp_path = path + ".minibeamng.tmp"
    try:
        with zipfile.ZipFile(path, "r") as zin:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
                for item in zin.infolist():
                    zout.writestr(item, zin.read(item.filename),
                                  zipfile.ZIP_DEFLATED, 9)

        os.replace(tmp_path, path)
        new_size = os.path.getsize(path)
        print(f"  Recompressed {os.path.basename(path)} -> {human_size(new_size)}")
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError) as err:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        print(f"  Warning: could not recompress {path}: {err}")


def recompress_content(dest, dry_run):
    """Re-compress all content zip files in the destination."""
    print()
    print("Recompressing content zip files...")
    for dirpath, _dirnames, filenames in os.walk(os.path.join(dest, "content")):
        for f in filenames:
            if f.endswith(".zip"):
                full = os.path.join(dirpath, f)
                rezip_file(full, dry_run)


def is_dest_inside_source(source, dest):
    """Return True if dest sits inside source, or the other way around."""
    s = os.path.abspath(source) + os.sep
    d = os.path.abspath(dest) + os.sep
    return d.startswith(s) or s.startswith(d)


def run(source, dest, profile, dry_run, keep_linux, force_recompress):
    """Copy every kept file from source into dest and report the size."""
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    source = os.path.abspath(source)
    dest = os.path.abspath(dest)

    if not os.path.isdir(source):
        print(f"Error: source folder not found: {source}")
        sys.exit(1)

    if os.path.abspath(source) == dest:
        print("Error: destination must be different from source.")
        sys.exit(1)

    if is_dest_inside_source(source, dest):
        print("Error: destination must not be inside source.")
        sys.exit(1)

    if not (os.path.isdir(os.path.join(source, "Bin64"))
            or os.path.isdir(os.path.join(source, "content"))):
        print("Warning: source does not look like a BeamNG.drive install.")

    copied_files = 0
    skipped_files = 0
    copied_bytes = 0
    skipped_bytes = 0
    copied_zip_bytes = 0  # content zips that were copied (for recompression estimate)

    for dirpath, dirnames, filenames in os.walk(source):
        rel_dir = os.path.relpath(dirpath, source)
        rel_dir_slash = "" if rel_dir == "." else rel_dir.replace(os.sep, "/")

        # Prune directories
        keep_dirs = []
        for d in dirnames:
            rel = f"{rel_dir_slash}/{d}" if rel_dir_slash else d
            # BinLinux: only skip if not keep_linux
            if d == "BinLinux" and not keep_linux:
                continue
            if should_skip_dir(rel, profile):
                continue
            keep_dirs.append(d)
        dirnames[:] = keep_dirs

        for f in filenames:
            full = os.path.join(dirpath, f)
            rel = f"{rel_dir_slash}/{f}" if rel_dir_slash else f

            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0

            if should_skip_file(rel, profile):
                skipped_files += 1
                skipped_bytes += size
                continue

            target = os.path.join(dest, rel)
            if not dry_run:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(full, target)

            copied_files += 1
            copied_bytes += size

            # Track content zip bytes for recompression estimate
            if rel.startswith("content/") and f.endswith(".zip"):
                copied_zip_bytes += size

    print()
    verb = "Would copy" if dry_run else "Copied"
    print(f"{verb} {copied_files} files ({human_size(copied_bytes)})")
    print(f"Skipped {skipped_files} files ({human_size(skipped_bytes)})")

    # Estimate recompressed size
    should_recompress = profile["recompress"] or force_recompress
    if should_recompress:
        # Content zips are stored (no compression), deflate gets roughly 65%
        zip_estimate = int(copied_zip_bytes * 0.65)
        total_estimate = copied_bytes - copied_zip_bytes + zip_estimate
        print(f"Estimated size with recompression: {human_size(total_estimate)}")
        print(f"(Zip files: {human_size(copied_zip_bytes)}"
              f" -> est. {human_size(zip_estimate)})")

        if not dry_run:
            recompress_content(dest, dry_run=False)
    elif dry_run and profile.get("recompress"):
        print("(Recompression would run in non-dry-run mode)")

    if not dry_run:
        print(f"\nMini install ready at: {dest}")


def human_size(n):
    """Format a byte count as a human readable size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main():
    """Parse command line arguments and run the copy."""
    parser = argparse.ArgumentParser(
        description="Copy a minimal, working BeamNG.drive install to a new folder.")
    parser.add_argument("source", help="Path to your BeamNG.drive folder")
    parser.add_argument("dest", nargs="?", default=None,
                        help="Output folder (default: <source>_mini)")
    parser.add_argument("--profile", choices=PROFILES.keys(), default="compact",
                        help="Size profile (default: compact)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without copying")
    parser.add_argument("--estimate", action="store_true",
                        help="Just estimate final size, don't copy anything")
    parser.add_argument("--keep-linux", action="store_true",
                        help="Keep the BinLinux folder")
    parser.add_argument("--recompress", action="store_true",
                        help="Re-compress content zip files (slower, saves space)")
    parser.add_argument("--skip-recompress", action="store_true",
                        help="Skip recompression even in extreme mode")
    args = parser.parse_args()

    profile = get_profile(args.profile)

    # Handle recompression flags
    if args.skip_recompress:
        profile["recompress"] = False
    elif args.recompress:
        profile["recompress"] = True

    # --estimate implies --dry-run
    if args.estimate:
        args.dry_run = True

    dest = args.dest
    if dest is None:
        src_abs = os.path.abspath(args.source)
        base, ext = os.path.splitext(src_abs)
        dest = f"{base}_mini_{args.profile}{ext}"

    print(f"Source:   {os.path.abspath(args.source)}")
    print(f"Dest:     {os.path.abspath(dest)}")
    print(f"Profile:  {args.profile} ({profile['description']})")
    if profile["recompress"]:
        print("Note:     Will re-compress content zip files (takes time)")
    if args.dry_run:
        print("Mode:     dry run (nothing will be written)")
    print("Warning:  Any files you have manually added to the source folder")
    print("          will also be copied to the destination.")
    print()

    run(args.source, dest, profile, args.dry_run,
        args.keep_linux, args.recompress)


if __name__ == "__main__":
    main()
