# MiniBeamNG

A script that builds a small copy of BeamNG.drive from your existing install. It copies only the files needed to run the game into a new folder; your original install stays untouched, so nothing gets deleted by mistake.

The goal is a working install under 3GB with one car (Gavril D-Series), one map (Garage V2), walking mode, and the full game UI.

## What it keeps

- Game core: `Bin64`, `gameengine.zip`, `tech`, `lua`, `shaders`, `ui`, `settings`, `locales`
- `content/art_shapes.zip` (the main menu won't launch without it)
- Other content assets, audio, and cache
- Garage V2 map only
- Vehicles whose name starts with `gavril` (edit the list at the top of `minibeamng.py` to change this)
- Chromium Embedded Framework files

## What it drops

- `BinLinux` (Linux binaries)
- Crash reporter (`crashrpt.dll`, `CrashSender.exe`, etc.)
- Epic Online Services DLLs
- Pacenote audio (`pacenote_*.ogg`) - the Lua scripts stay, only the voice files go
- `campaigns` (they reference maps and vehicles that are being removed)
- SVN conflict leftovers (`*.mine`, `*.r12345`)

## Usage

Double-click `run.bat`, or from a terminal:

```
python minibeamng.py <source_dir> [dest_dir] [--dry-run]
```

- `source_dir` - your BeamNG.drive folder (the one with `Bin64` and `content`)
- `dest_dir` - where the mini copy goes, defaults to `<source>_mini` next to the original
- `--dry-run` - prints what would be copied or skipped without writing anything

Example:

```
python minibeamng.py "C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive"
```

That creates `BeamNG.drive_mini` next to it. Launch the game from there with `Bin64\BeamNG.drive.x64.exe`.

## Notes

- The copy is safe to delete if you don't like it, your original install is not modified.
- If the game complains about missing files, add them back by copying them from your original install into the mini folder, or adjust the filter lists in `minibeamng.py` and run again.
- Steam may still see the full install size; only the mini folder is smaller.

---

This project does not support illegally obtained copies of BeamNG.drive, nor illegally redistributing them. Use it with your own legal copy at your own risk.
