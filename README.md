# MiniBeamNG

A script that builds a small copy of BeamNG.drive from your existing install. It copies only the files needed to run the game into a new folder; your original install stays untouched, so nothing gets deleted by mistake.

Three size profiles target different drive sizes: full (~20GB), compact (~6GB), and extreme (~5GB, or <5GB with recompression).

## Profiles

- **full** - All levels and vehicles. Removes campaigns, crash reporter, EOS, pacenote audio, and docs.
- **compact** - Keeps only `pickup`, `common`, and `unicycle` vehicles plus `garage_v2` level.
- **extreme** - Like compact, plus strips debug UI apps (radio test, camera test, etc.) and all non-English locales.

## Usage

Double-click `run.bat`, or from a terminal:

```
python minibeamng.py <source_dir> [dest_dir] [--profile PROFILE] [options]
```

Options:
- `--profile full|compact|extreme` - size profile (default: compact)
- `--dry-run` - show what would happen without copying
- `--estimate` - estimate final size without copying (fast)
- `--keep-linux` - keep the `BinLinux` folder
- `--recompress` - re-compress content zip files (saves GBs, takes time)
- `--skip-recompress` - skip recompression even in extreme mode

Example for a 32GB drive:
```
python minibeamng.py "C:\BeamNG" --profile compact
```

Example for a 16GB drive:
```
python minibeamng.py "C:\BeamNG" --profile extreme
```

Example for under 5GB (BYO modded game):
```
python minibeamng.py "C:\BeamNG" --profile extreme --recompress
```

## What it keeps

- Game core: `Bin64`, `gameengine.zip`, `tech`, `lua`, `shaders`, `ui`, `settings`, `locales`
- `content/art_shapes.zip` (the main menu won't launch without it)
- Other content assets, audio, and cache
- Levels and vehicles per the selected profile
- Chromium Embedded Framework files

## What it drops

- Crash reporter (`crashrpt.dll`, `CrashSender.exe`, etc.)
- Epic Online Services DLL and .so files
- Pacenote audio (`pacenote_*.ogg`) - the Lua scripts stay
- `campaigns` (they reference maps and vehicles that are being removed)
- `flowgraphEditor`
- SVN conflict leftovers (`*.mine`, `*.r12345`)
- Docs: `EULA.pdf`, `PrivacyPolicy*.pdf`, `licenses.txt`

Extreme mode additionally drops debug UI apps and non-English locales.

## Notes

- The copy is safe to delete if you don't like it, your original install is not modified.
- If the game complains about missing files, add them back by copying them from your original install into the mini folder.
- Steam may still see the full install size; only the mini folder is smaller.
- Recompression works because BeamNG's content zips are stored uncompressed. Deflate saves ~35% on them.

---

This project does not support illegally obtained copies of BeamNG.drive, nor illegally redistributing them. Use it with your own legal copy at your own risk.
