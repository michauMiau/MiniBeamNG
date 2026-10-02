"""Tests for minibeamng.py - profile filtering, copy behaviour, recompression."""
# pylint: disable=wrong-import-position
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import minibeamng as mb  # noqa: E402


def touch(root, rel):
    """Create a file (and its parent dirs) with a byte of content."""
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(b"x")
    return path


def build_mock(root):
    """Build a small BeamNG-shaped tree covering every filter rule."""
    for rel in [
        "BeamNG.drive.exe",
        "gameengine.zip",
        "Bin64/BeamNG.drive.x64.exe",
        "Bin64/libcef.dll",
        "Bin64/crashrpt.dll",
        "Bin64/CrashSender.exe",
        "Bin64/EOSSDK-Win64-Shipping.dll",
        "Bin64/libbeamng.x64.dll.mine",
        "Bin64/BeamNG.drive.x64.exe.r183766",
        "BinLinux/libbeamng.x64.so",
        "BinLinux/libEOSSDK-Linux-Shipping.so",
        "content/art_shapes.zip",
        "content/levels/garage_v2.zip",
        "content/levels/small_island.zip",
        "content/vehicles/common.zip",
        "content/vehicles/pickup.zip",
        "content/vehicles/unicycle.zip",
        "content/vehicles/gavril_d_series.zip",
        "tech/annotations.json",
        "roadArchitect/groups/one.json",
        "EULA.pdf",
        "PrivacyPolicy.pdf",
        "licenses.txt",
        "support.exe",
        "campaigns/chapter1/campaign_info.json",
        "flowgraphEditor/Tower/tower.png",
        "lua/ge/extensions/gameplay/walk.lua",
        "lua/ge/extensions/gameplay/rally/notebook/pacenote.lua",
        "lua/ge/extensions/gameplay/rally/audio/pacenote_left.ogg",
    ]:
        touch(root, rel)


class ProfileTests(unittest.TestCase):
    """Rules that decide whether a file or folder is kept."""

    def setUp(self):
        self.compact = mb.get_profile("compact")
        self.extreme = mb.get_profile("extreme")

    def test_protected_file_is_always_kept(self):
        self.assertFalse(mb.should_skip_file("content/art_shapes.zip", self.compact))

    def test_compact_keeps_only_listed_vehicle(self):
        for name in ("common", "pickup", "unicycle"):
            self.assertFalse(mb.should_skip_file(f"content/vehicles/{name}.zip", self.compact))
        self.assertTrue(mb.should_skip_file("content/vehicles/gavril_d_series.zip", self.compact))

    def test_compact_keeps_only_listed_level(self):
        self.assertFalse(mb.should_skip_file("content/levels/garage_v2.zip", self.compact))
        self.assertTrue(mb.should_skip_file("content/levels/small_island.zip", self.compact))

    def test_full_profile_keeps_every_level_and_vehicle(self):
        full = mb.get_profile("full")
        self.assertFalse(mb.should_skip_file("content/levels/small_island.zip", full))
        self.assertFalse(mb.should_skip_file("content/vehicles/gavril_d_series.zip", full))

    def test_crash_reporter_and_eos_are_skipped(self):
        for rel in ("Bin64/crashrpt.dll", "Bin64/CrashSender.exe",
                    "Bin64/EOSSDK-Win64-Shipping.dll",
                    "BinLinux/libEOSSDK-Linux-Shipping.so"):
            self.assertTrue(mb.should_skip_file(rel, self.compact), rel)

    def test_pacenote_audio_goes_but_lua_stays(self):
        audio = "lua/ge/extensions/gameplay/rally/audio/pacenote_left.ogg"
        script = "lua/ge/extensions/gameplay/rally/notebook/pacenote.lua"
        self.assertTrue(mb.should_skip_file(audio, self.compact))
        self.assertFalse(mb.should_skip_file(script, self.compact))

    def test_svn_conflict_files_are_skipped(self):
        self.assertTrue(mb.should_skip_file("Bin64/libbeamng.x64.dll.mine", self.compact))
        self.assertTrue(mb.should_skip_file("Bin64/BeamNG.drive.x64.exe.r183766", self.compact))

    def test_docs_and_support_exe_are_skipped(self):
        for rel in ("EULA.pdf", "PrivacyPolicy.pdf", "licenses.txt", "support.exe"):
            self.assertTrue(mb.should_skip_file(rel, self.compact), rel)

    def test_doc_entries_match_regardless_of_case(self):
        # The filter compares a lowercased path, so the entries must be
        # lowercase or they never match. bCDDL-1.1.txt is the real mixed-case
        # name in a BeamNG install.
        self.assertTrue(mb.should_skip_file("lua/bCDDL-1.1.txt", self.compact))
        self.assertTrue(mb.should_skip_file("PrivacyPolicy-tech.pdf", self.compact))

    def test_filter_tables_are_lowercase(self):
        # Import-time guard: uppercase entries silently never match.
        mb._selfcheck()  # pylint: disable=protected-access

    def test_campaigns_and_flowgraph_dirs_are_skipped(self):
        for name in ("campaigns", "flowgraphEditor", "roadArchitect", "tech"):
            self.assertTrue(mb.should_skip_dir(name, self.compact), name)


class CopyTests(unittest.TestCase):
    """End-to-end behaviour of run() against a throwaway tree."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source = os.path.join(self.tmp, "src")
        os.makedirs(self.source)
        build_mock(self.source)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy_with(self, **kwargs):
        dest = os.path.join(self.tmp, "dest")
        profile = mb.get_profile(kwargs.pop("profile", "compact"))
        mb.run(self.source, dest, profile,
               kwargs.pop("dry_run", False),
               kwargs.pop("keep_linux", False),
               kwargs.pop("force_recompress", False))
        return dest

    def test_source_folder_is_never_modified(self):
        before = sorted(os.listdir(self.source))
        self.copy_with()
        self.assertEqual(before, sorted(os.listdir(self.source)))
        self.assertTrue(os.path.exists(os.path.join(self.source, "content", "vehicles",
                                                    "gavril_d_series.zip")))

    def test_dry_run_writes_nothing(self):
        dest = self.copy_with(dry_run=True)
        self.assertFalse(os.path.exists(dest))

    def test_keeps_and_drops(self):
        dest = self.copy_with()
        kept = [
            "content/art_shapes.zip",
            "content/vehicles/pickup.zip",
            "content/vehicles/common.zip",
            "content/vehicles/unicycle.zip",
            "Bin64/BeamNG.drive.x64.exe",
            "lua/ge/extensions/gameplay/walk.lua",
        ]
        dropped = [
            "content/vehicles/gavril_d_series.zip",
            "content/levels/small_island.zip",
            "Bin64/crashrpt.dll",
            "Bin64/CrashSender.exe",
            "Bin64/EOSSDK-Win64-Shipping.dll",
            "BinLinux",
            "tech",
            "roadArchitect",
            "EULA.pdf",
            "support.exe",
            "campaigns",
            "flowgraphEditor",
        ]
        for rel in kept:
            self.assertTrue(os.path.exists(os.path.join(dest, rel)), f"missing {rel}")
        for rel in dropped:
            self.assertFalse(os.path.exists(os.path.join(dest, rel)), f"leaked {rel}")

    def test_keep_linux_flag_keeps_binlinux(self):
        dest = self.copy_with(keep_linux=True)
        self.assertTrue(os.path.isdir(os.path.join(dest, "BinLinux")))
        # EOS is stripped even from the Linux folder.
        self.assertFalse(os.path.exists(
            os.path.join(dest, "BinLinux", "libEOSSDK-Linux-Shipping.so")))
        self.assertTrue(os.path.exists(
            os.path.join(dest, "BinLinux", "libbeamng.x64.so")))

    def test_default_drops_binlinux(self):
        dest = self.copy_with()
        self.assertFalse(os.path.exists(os.path.join(dest, "BinLinux")))

    def test_recompression_shrinks_a_stored_zip(self):
        # Build a real stored (uncompressed) zip, like BeamNG ships them.
        source_zip = os.path.join(self.source, "content", "vehicles", "common.zip")
        payload = b"beamng" * 4096
        with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_STORED) as zf:
            zf.writestr("vehicles/common/data.bin", payload)

        dest = self.copy_with(force_recompress=True)
        out = os.path.join(dest, "content", "vehicles", "common.zip")

        self.assertLess(os.path.getsize(out), os.path.getsize(source_zip))
        with zipfile.ZipFile(out) as zf:
            self.assertEqual(zf.read("vehicles/common/data.bin"), payload)

    def test_recompression_keeps_non_zip_files_intact(self):
        dest = self.copy_with(force_recompress=True)
        self.assertTrue(os.path.exists(os.path.join(dest, "gameengine.zip")))

    def test_extreme_strips_ui_apps_and_locales(self):
        touch(self.source, "ui/modules/apps/radioTest/app.json")
        touch(self.source, "locales/translations/de/game.json")
        touch(self.source, "locales/translations/en/game.json")
        dest = self.copy_with(profile="extreme")
        self.assertFalse(os.path.exists(
            os.path.join(dest, "ui", "modules", "apps", "radioTest")))
        self.assertFalse(os.path.exists(
            os.path.join(dest, "locales", "translations", "de")))
        self.assertTrue(os.path.exists(
            os.path.join(dest, "locales", "translations", "en")))

    def test_broken_symlink_does_not_abort_the_copy(self):
        # A real install can hold a dangling link; it must not stop the run.
        link = os.path.join(self.source, "Bin64", "dangling.dll")
        try:
            os.symlink("/nonexistent/target", link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")

        dest = self.copy_with()
        # Everything else still made it across.
        self.assertTrue(os.path.exists(
            os.path.join(dest, "content", "vehicles", "pickup.zip")))
        self.assertTrue(os.path.exists(os.path.join(dest, "Bin64", "libcef.dll")))


class GuardTests(unittest.TestCase):
    """Bad inputs should be refused, not silently half-done."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.source = os.path.join(self.tmp, "src")
        os.makedirs(self.source)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_source_exits(self):
        with self.assertRaises(SystemExit):
            mb.run(os.path.join(self.tmp, "nope"), os.path.join(self.tmp, "d"),
                   mb.get_profile("compact"), False, False, False)

    def test_same_source_and_dest_exits(self):
        with self.assertRaises(SystemExit):
            mb.run(self.source, self.source, mb.get_profile("compact"), False, False, False)

    def test_dest_inside_source_exits(self):
        with self.assertRaises(SystemExit):
            mb.run(self.source, os.path.join(self.source, "inner"),
                   mb.get_profile("compact"), False, False, False)

    def test_is_dest_inside_source_detects_both_directions(self):
        self.assertTrue(mb.is_dest_inside_source("/a/b", "/a/b/c"))
        self.assertTrue(mb.is_dest_inside_source("/a/b/c", "/a/b"))
        self.assertFalse(mb.is_dest_inside_source("/a/b", "/a/c"))


class HelperTests(unittest.TestCase):
    """Small pure functions."""

    def test_human_size(self):
        self.assertEqual(mb.human_size(512), "512.0 B")
        self.assertEqual(mb.human_size(1024), "1.0 KB")
        self.assertEqual(mb.human_size(1024 ** 3), "1.0 GB")

    def test_unknown_profile_exits(self):
        with self.assertRaises(SystemExit):
            mb.get_profile("nope")

    def test_get_profile_returns_a_copy(self):
        profile = mb.get_profile("compact")
        profile["skip_dirs"].append("mutated")
        self.assertNotIn("mutated", mb.PROFILES["compact"]["skip_dirs"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
