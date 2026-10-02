# MiniBeamNG

A script that builds a small copy of BeamNG.drive from your existing install. It copies only the files needed to run the game into a new folder; your original install stays untouched, so nothing gets deleted by mistake.

Three size profiles target different drive sizes: full (~45GB), compact (~14GB), and extreme (~12GB, or ~8-10GB with recompression).

## Profiles

- **full** - All levels and vehicles. Removes campaigns, crash reporter, EOS, pacenote audio, docs, support.exe, roadArchitect, tech. Still ~45GB.
- **compact** - Keeps only `pickup`, `common`, and `unicycle` vehicles plus `garage_v2` level. ~14GB.
- **extreme** - Like compact, plus strips debug UI apps (radio test, camera test, etc.) and all non-English locales. ~12GB.

To fit on a 32GB USB, use --profile full and either manually delete unwanted levels/vehicles from the source before running, or edit the levels_keep and vehicles_keep sets in the script.

## Safety

The original install is never written to. The script refuses to run when the destination resolves to the source, to a folder inside it, or to a symlink pointing into it. It only ever copies files out.

If the destination already has files in it, the script warns instead of pretending the result is clean - files kept by an earlier, more permissive run stay where they are.

A run that cannot read or copy something says so at the end instead of quietly producing a folder with holes in it.

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

Example:
```
python minibeamng.py "C:\BeamNG" --profile compact
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
