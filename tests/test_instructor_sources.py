from __future__ import annotations

import hashlib
import json
import struct
import sys
import unittest
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fetch_official_assets import (  # type: ignore[import-not-found]
    MAX_IMAGE_BYTES,
    AssetValidationError,
    fetch_declared_assets,
    inspect_image,
    is_official_bilkent_url,
    validate_local_assets,
)


COURSES = {
    "CTIS151",
    "CTIS163",
    "CTIS164",
    "CTIS166",
    "CTIS255",
    "CTIS256",
    "CTIS259",
    "CTIS262",
    "CTIS264",
    "CTIS359",
    "CTIS411",
    "CTIS465",
    "CTIS474",
}
INSTRUCTOR_NAMES = {
    "Erkan Uçar",
    "Oumout Chousein Oglou",
    "Serkan Genç",
    "Neşe Şahin Özçelik",
    "N. Ceren Serim",
    "Cüneyt Sevgi",
    "Satılmış Topcu",
    "Hamdi Murat Yıldırım",
    "Çağıl Alsaç",
    "Volkan Evrin",
    "Burcu Özdoğru Liman",
    "Leyla Sezer",
}
SPECIALIST_NAMES = {
    "Engin Zafer Kıraçbedel",
    "Berk Önder",
    "Hatice Zehra Yılmaz",
    "Efe Mert Şahinkoç",
}
PERSON_FIELDS = {
    "name",
    "role",
    "courses",
    "evidence_class",
    "official_page",
    "image",
    "image_source",
    "retrieved",
    "example_id",
}
ASSET_FIELDS = {
    "path",
    "source_page",
    "source_url",
    "retrieved",
    "rights_note",
    "sha256",
    "mime",
    "width",
    "height",
}
FORBIDDEN_PRIVATE_STATE_TERMS = {
    "angry",
    "anxious",
    "emotion",
    "feels",
    "hidden thought",
    "personality",
    "secretly",
    "thinks",
    "kızgın",
    "duygu",
    "hissediyor",
    "kişilik",
    "gizlice",
    "düşünüyor",
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def png_fixture(width: int, height: int, padding: int = 0) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    pixels = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"tEXt", b"x" * padding)
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


def jpeg_with_empty_entropy(width: int = 128, height: int = 128) -> bytes:
    frame = (
        b"\x08"
        + struct.pack(">HH", height, width)
        + b"\x01\x01\x11\x00"
    )
    scan = b"\x01\x01\x00\x00\x3f\x00"
    return (
        b"\xff\xd8"
        + b"\xff\xc0"
        + struct.pack(">H", len(frame) + 2)
        + frame
        + b"\xff\xda"
        + struct.pack(">H", len(scan) + 2)
        + scan
        + b"\xff\xd9"
    )


def asset_entry(path: str, payload: bytes) -> dict[str, object]:
    return {
        "path": path,
        "source_page": "https://www.ctis.bilkent.edu.tr/ctis_Logos.php",
        "source_url": "https://www.ctis.bilkent.edu.tr/images/FAS-CTIS-emblem-ENG.png",
        "retrieved": "2026-08-02",
        "rights_note": (
            "Used for identification and source documentation. Copyright remains "
            "with Bilkent University or the applicable rightsholder. "
            "No license or endorsement is implied."
        ),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "mime": "image/png",
        "width": 128,
        "height": 128,
    }


def source_manifest(*entries: dict[str, object]) -> dict[str, object]:
    return {"schema_version": 1, "assets": list(entries)}


class InstructorSourceManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.people = load_json(ROOT / "docs" / "instructors.json")
        cls.sources = load_json(ROOT / "docs" / "assets" / "sources.json")
        cls.instructors = cls.people["instructors"]
        cls.specialists = cls.people["specialists"]
        cls.assets = cls.sources["assets"]

    def test_rosters_are_exact_and_roles_stay_separate(self) -> None:
        self.assertEqual(INSTRUCTOR_NAMES, {person["name"] for person in self.instructors})
        self.assertEqual(SPECIALIST_NAMES, {person["name"] for person in self.specialists})
        self.assertTrue(all(person["role"] != "specialist" for person in self.instructors))
        self.assertTrue(all(person["role"] == "specialist" for person in self.specialists))
        self.assertTrue(all(person["primary"] is False for person in self.specialists))

    def test_person_schema_identifiers_and_urls_are_complete(self) -> None:
        people = [*self.instructors, *self.specialists]
        names = [person["name"] for person in people]
        example_ids = [person["example_id"] for person in people]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(example_ids), len(set(example_ids)))
        for person in people:
            self.assertTrue(PERSON_FIELDS <= person.keys())
            self.assertEqual("2026-08-02", person["retrieved"])
            self.assertTrue(is_official_bilkent_url(person["official_page"]))
            self.assertTrue(is_official_bilkent_url(person["image_source"]))

    def test_course_evidence_is_bounded_and_current_labels_use_profiles(self) -> None:
        people = [*self.instructors, *self.specialists]
        statuses: set[str] = set()
        for person in people:
            for course in person["courses"]:
                self.assertEqual({"course", "basis", "status"}, set(course))
                self.assertIn(course["course"], COURSES)
                self.assertIn(
                    course["status"],
                    {"current", "document-supported/historical"},
                )
                statuses.add(course["status"])
                if course["status"] == "current":
                    self.assertEqual("official-profile", course["basis"])
                else:
                    self.assertEqual("signed-course-material", course["basis"])
        self.assertEqual({"current", "document-supported/historical"}, statuses)
        self.assertEqual([], next(person for person in self.specialists if person["name"] == "Efe Mert Şahinkoç")["courses"])
        self.assertEqual(
            "department-context-only",
            next(person for person in self.specialists if person["name"] == "Efe Mert Şahinkoç")["evidence_class"],
        )

    def test_every_image_is_declared_once_and_assets_are_exact(self) -> None:
        people = [*self.instructors, *self.specialists]
        declared = [asset["path"] for asset in self.assets]
        expected = {person["image"] for person in people} | {"docs/assets/bilkent-ctis-logo.png"}
        self.assertEqual(len(declared), len(set(declared)))
        self.assertEqual(expected, set(declared))
        self.assertEqual(17, len(declared))
        for asset in self.assets:
            self.assertEqual(ASSET_FIELDS, set(asset))
            self.assertTrue(is_official_bilkent_url(asset["source_page"]))
            self.assertTrue(is_official_bilkent_url(asset["source_url"]))
            self.assertTrue(asset["retrieved"].startswith("2026-"))
            self.assertIn("copyright remains", asset["rights_note"].lower())
            self.assertIn("no license or endorsement", asset["rights_note"].lower())

    def test_local_assets_match_declared_bytes_and_dimensions(self) -> None:
        self.assertEqual([], validate_local_assets(ROOT, self.sources))
        for asset in self.assets:
            payload = (ROOT / asset["path"]).read_bytes()
            actual = inspect_image(payload, asset["mime"])
            self.assertLessEqual(len(payload), MAX_IMAGE_BYTES)
            self.assertEqual(asset["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual((asset["mime"], asset["width"], asset["height"]), actual)

    def test_image_inspection_rejects_spoofed_and_truncated_payloads(self) -> None:
        sample_asset = self.assets[1]
        payload = (ROOT / sample_asset["path"]).read_bytes()
        with self.assertRaises(AssetValidationError):
            inspect_image(payload, "text/html")
        with self.assertRaises(AssetValidationError):
            inspect_image(payload[:-8], sample_asset["mime"])
        with self.assertRaises(AssetValidationError):
            inspect_image(b"<html>not an image</html>", "image/jpeg")
        for truncated in (payload[:32], payload[: len(payload) // 2], payload[:-2]):
            with self.subTest(length=len(truncated)):
                with self.assertRaises(AssetValidationError):
                    inspect_image(truncated, sample_asset["mime"])

    def test_jpeg_decoder_rejects_frame_and_scan_with_zero_entropy(self) -> None:
        with self.assertRaises(AssetValidationError):
            inspect_image(jpeg_with_empty_entropy(), "image/jpeg")

    def test_image_validation_explains_how_to_install_missing_pillow(self) -> None:
        with patch("fetch_official_assets.Image", None, create=True):
            with self.assertRaisesRegex(
                AssetValidationError,
                r"python -m pip install -r requirements-dev\.txt",
            ):
                inspect_image(png_fixture(128, 128), "image/png")

    def test_image_inspection_rejects_oversized_and_small_images(self) -> None:
        with self.assertRaises(AssetValidationError):
            inspect_image(png_fixture(128, 128, MAX_IMAGE_BYTES), "image/png")
        with self.assertRaises(AssetValidationError):
            inspect_image(png_fixture(127, 128), "image/png")

    def test_official_url_boundary_rejects_lookalikes_and_insecure_urls(self) -> None:
        self.assertTrue(is_official_bilkent_url("https://www.ctis.bilkent.edu.tr/image.jpg"))
        self.assertTrue(is_official_bilkent_url("https://bilkent.edu.tr/image.jpg"))
        for url in (
            "http://www.ctis.bilkent.edu.tr/image.jpg",
            "https://bilkent.edu.tr.example.com/image.jpg",
            "https://evilbilkent.edu.tr/image.jpg",
            "https://example.com/image.jpg",
        ):
            self.assertFalse(is_official_bilkent_url(url))

    def test_validation_rejects_undeclared_files_and_symlinks(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            asset_root = root / "docs" / "assets"
            asset_root.mkdir(parents=True)
            (asset_root / "undeclared.png").write_bytes(b"not-an-image")
            errors = validate_local_assets(root, {"assets": []})
            self.assertTrue(any("undeclared" in error for error in errors))

        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            asset_root = root / "docs" / "assets"
            asset_root.mkdir(parents=True)
            link = asset_root / "linked.png"
            link.write_bytes(b"not-an-image")
            original_is_symlink = Path.is_symlink

            def report_one_link(candidate: Path) -> bool:
                return candidate == link or original_is_symlink(candidate)

            with patch.object(Path, "is_symlink", autospec=True, side_effect=report_one_link):
                errors = validate_local_assets(
                    root,
                    {"assets": [{"path": "docs/assets/linked.png"}]},
                )
            self.assertTrue(any("symbolic link" in error for error in errors))

    def test_validation_rejects_undeclared_nonimage_files(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            asset_root = root / "docs" / "assets"
            asset_root.mkdir(parents=True)
            (asset_root / "private-note.txt").write_text("not public", encoding="utf-8")

            errors = validate_local_assets(root, {"assets": []})

        self.assertTrue(any("private-note.txt" in error for error in errors))

    def test_fetch_preflight_rejects_outside_path_without_mutation_or_network(self) -> None:
        payload = png_fixture(128, 128)
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            readme = root / "README.md"
            readme.write_bytes(b"keep-me")
            manifest = source_manifest(asset_entry("README.md", payload))

            with patch(
                "fetch_official_assets.fetch_asset",
                return_value=(payload, "image/png", 128, 128),
            ) as fetch:
                errors = fetch_declared_assets(root, manifest)

            self.assertEqual(b"keep-me", readme.read_bytes())
            fetch.assert_not_called()
        self.assertTrue(any("docs/assets" in error for error in errors))

    def test_fetch_preflight_rejects_case_collisions_before_network(self) -> None:
        payload = png_fixture(128, 128)
        manifest = source_manifest(
            asset_entry("docs/assets/instructors/Photo.png", payload),
            asset_entry("docs/assets/instructors/photo.png", payload),
        )
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            with patch(
                "fetch_official_assets.fetch_asset",
                return_value=(payload, "image/png", 128, 128),
            ) as fetch:
                errors = fetch_declared_assets(root, manifest)
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            self.assertEqual(before, after)
            fetch.assert_not_called()
        self.assertTrue(any("case collision" in error for error in errors))

    def test_fetch_preflight_rejects_symlink_parent_before_network(self) -> None:
        payload = png_fixture(128, 128)
        manifest = source_manifest(
            asset_entry("docs/assets/instructors/person.png", payload)
        )
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            parent = root / "docs" / "assets" / "instructors"
            parent.mkdir(parents=True)
            original_is_symlink = Path.is_symlink

            def report_parent_link(candidate: Path) -> bool:
                return candidate == parent or original_is_symlink(candidate)

            with (
                patch.object(
                    Path,
                    "is_symlink",
                    autospec=True,
                    side_effect=report_parent_link,
                ),
                patch(
                    "fetch_official_assets.fetch_asset",
                    return_value=(payload, "image/png", 128, 128),
                ) as fetch,
            ):
                errors = fetch_declared_assets(root, manifest)

            fetch.assert_not_called()
            self.assertFalse((parent / "person.png").exists())
        self.assertTrue(any("symbolic link" in error for error in errors))

    def test_fetch_rolls_back_every_target_when_replacement_fails(self) -> None:
        old_a = png_fixture(128, 128, 1)
        old_b = png_fixture(128, 128, 2)
        new_a = png_fixture(128, 128, 3)
        new_b = png_fixture(128, 128, 4)
        manifest = source_manifest(
            asset_entry("docs/assets/a.png", new_a),
            asset_entry("docs/assets/b.png", new_b),
        )
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            asset_root = root / "docs" / "assets"
            asset_root.mkdir(parents=True)
            first = asset_root / "a.png"
            second = asset_root / "b.png"
            first.write_bytes(old_a)
            second.write_bytes(old_b)
            original_replace = __import__("os").replace
            replacement_count = 0

            def fail_second_replacement(source: Path, destination: Path) -> None:
                nonlocal replacement_count
                replacement_count += 1
                if replacement_count == 2:
                    raise OSError("injected second replacement failure")
                original_replace(source, destination)

            with (
                patch(
                    "fetch_official_assets.fetch_asset",
                    side_effect=[
                        (new_a, "image/png", 128, 128),
                        (new_b, "image/png", 128, 128),
                    ],
                ),
                patch(
                    "fetch_official_assets.os.replace",
                    side_effect=fail_second_replacement,
                ),
            ):
                errors = fetch_declared_assets(root, manifest)

            self.assertEqual(old_a, first.read_bytes())
            self.assertEqual(old_b, second.read_bytes())
            self.assertFalse(any(path.name.endswith(".fetching") for path in root.rglob("*")))
        self.assertTrue(any("replacement" in error for error in errors))

    def test_public_metadata_contains_no_private_state_claims(self) -> None:
        haystack = json.dumps(
            {"people": self.people, "sources": self.sources},
            ensure_ascii=False,
        ).casefold()
        self.assertFalse({term for term in FORBIDDEN_PRIVATE_STATE_TERMS if term in haystack})


if __name__ == "__main__":
    unittest.main()
