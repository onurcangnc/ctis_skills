from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import tempfile
import warnings
import zlib
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    Image = None  # type: ignore[assignment]
    UnidentifiedImageError = OSError  # type: ignore[misc,assignment]


MAX_IMAGE_BYTES = 2 * 1024 * 1024
MIN_IMAGE_DIMENSION = 128
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
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
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AssetValidationError(ValueError):
    """Raised when a declared source or image crosses the public asset boundary."""


@dataclass(frozen=True)
class _AssetSpec:
    index: int
    display: str
    destination: Path
    entry: dict[str, object]


def is_official_bilkent_url(value: str) -> bool:
    """Return whether value is an HTTPS URL under Bilkent's DNS boundary."""
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname.casefold() if parsed.hostname else ""
        port = parsed.port
    except (AttributeError, TypeError, ValueError):
        return False
    return (
        parsed.scheme.casefold() == "https"
        and parsed.username is None
        and parsed.password is None
        and port in {None, 443}
        and (hostname == "bilkent.edu.tr" or hostname.endswith(".bilkent.edu.tr"))
    )


def is_official_source_url(value: str) -> bool:
    """Return whether value is an allowed provenance URL.

    Allows Bilkent HTTPS plus the official CTIS Facebook page. This governs
    manifest provenance only; the download boundary stays Bilkent-only.
    """
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname.casefold() if parsed.hostname else ""
    except (AttributeError, TypeError, ValueError):
        return False
    if is_official_bilkent_url(value):
        return True
    return (
        hostname == "www.facebook.com"
        and parsed.path.casefold() == "/ctisbilkent/"
        and parsed.scheme.casefold() == "https"
        and parsed.username is None
        and parsed.password is None
    )


class _OfficialRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if not is_official_bilkent_url(newurl):
            raise AssetValidationError(f"redirect leaves the Bilkent HTTPS boundary: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def inspect_image(payload: bytes, declared_mime: str) -> tuple[str, int, int]:
    """Validate complete PNG/JPEG structure and return MIME plus dimensions."""
    if len(payload) > MAX_IMAGE_BYTES:
        raise AssetValidationError(f"image exceeds {MAX_IMAGE_BYTES} bytes")
    mime = declared_mime.partition(";")[0].strip().casefold()
    if mime not in ALLOWED_MIME_TYPES:
        raise AssetValidationError(f"unsupported image MIME type: {declared_mime}")

    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime, width, height = _inspect_png(payload)
    elif payload.startswith(b"\xff\xd8"):
        detected_mime, width, height = _inspect_jpeg(payload)
    else:
        raise AssetValidationError("payload has no supported image signature")

    if mime != detected_mime:
        raise AssetValidationError(
            f"declared MIME {mime} does not match detected {detected_mime}"
        )
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        raise AssetValidationError(
            f"image dimensions {width}x{height} are below "
            f"{MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}"
        )
    _verify_decodable_image(payload, detected_mime, width, height)
    return detected_mime, width, height


def _verify_decodable_image(
    payload: bytes, expected_mime: str, expected_width: int, expected_height: int
) -> None:
    if Image is None:
        raise AssetValidationError(
            "Pillow is required for complete image validation; run "
            "python -m pip install -r requirements-dev.txt"
        )
    expected_format = "JPEG" if expected_mime == "image/jpeg" else "PNG"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with Image.open(BytesIO(payload)) as image:
                if image.format != expected_format or image.size != (
                    expected_width,
                    expected_height,
                ):
                    raise AssetValidationError(
                        "decoder format or dimensions disagree with image structure"
                    )
                image.verify()
            with Image.open(BytesIO(payload)) as decoded:
                decoded.load()
                if decoded.format != expected_format or decoded.size != (
                    expected_width,
                    expected_height,
                ):
                    raise AssetValidationError(
                        "decoded image format or dimensions changed"
                    )
    except AssetValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Warning) as error:
        raise AssetValidationError(f"image decoder rejected payload: {error}") from error


def _inspect_png(payload: bytes) -> tuple[str, int, int]:
    offset = 8
    width = height = None
    saw_iend = False
    chunk_index = 0
    while offset < len(payload):
        if len(payload) - offset < 12:
            raise AssetValidationError("truncated PNG chunk header")
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(payload):
            raise AssetValidationError("truncated PNG chunk payload")
        chunk_data = payload[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", payload[offset + 8 + length : end])[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise AssetValidationError("PNG chunk CRC mismatch")
        if chunk_index == 0 and chunk_type != b"IHDR":
            raise AssetValidationError("PNG does not start with IHDR")
        if chunk_type == b"IHDR":
            if chunk_index != 0 or length != 13:
                raise AssetValidationError("malformed PNG IHDR")
            width, height = struct.unpack(">II", chunk_data[:8])
        if chunk_type == b"IEND":
            if length != 0 or end != len(payload):
                raise AssetValidationError("malformed PNG IEND")
            saw_iend = True
            break
        offset = end
        chunk_index += 1
    if not saw_iend or width is None or height is None:
        raise AssetValidationError("incomplete PNG image")
    return "image/png", width, height


def _inspect_jpeg(payload: bytes) -> tuple[str, int, int]:
    if len(payload) < 4 or not payload.endswith(b"\xff\xd9"):
        raise AssetValidationError("truncated JPEG image")
    offset = 2
    width = height = None
    saw_scan = False
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while offset < len(payload) - 2:
        if payload[offset] != 0xFF:
            if not saw_scan:
                raise AssetValidationError("malformed JPEG marker stream")
            offset += 1
            continue
        while offset < len(payload) and payload[offset] == 0xFF:
            offset += 1
        if offset >= len(payload):
            raise AssetValidationError("truncated JPEG marker")
        marker = payload[offset]
        offset += 1
        if marker == 0x00 or 0xD0 <= marker <= 0xD7:
            if not saw_scan:
                raise AssetValidationError("unexpected JPEG entropy marker")
            continue
        if marker == 0xD9:
            if offset != len(payload):
                raise AssetValidationError("JPEG has trailing data")
            break
        if marker == 0xD8 or marker == 0x01:
            continue
        if offset + 2 > len(payload):
            raise AssetValidationError("truncated JPEG segment length")
        segment_length = struct.unpack(">H", payload[offset : offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(payload):
            raise AssetValidationError("invalid JPEG segment length")
        if marker in sof_markers:
            if segment_length < 7:
                raise AssetValidationError("truncated JPEG frame header")
            height, width = struct.unpack(">HH", payload[offset + 3 : offset + 7])
        if marker == 0xDA:
            saw_scan = True
        offset += segment_length
    if width is None or height is None or not saw_scan:
        raise AssetValidationError("JPEG is missing frame or scan data")
    return "image/jpeg", width, height


def fetch_asset(source_url: str) -> tuple[bytes, str, int, int]:
    """Download one official image while validating every redirect and byte."""
    if not is_official_bilkent_url(source_url):
        raise AssetValidationError(f"source URL is not official Bilkent HTTPS: {source_url}")
    opener = build_opener(_OfficialRedirectHandler())
    request = Request(source_url, headers={"User-Agent": "ctis-skills-source-check/1.0"})
    try:
        with opener.open(request, timeout=30) as response:
            final_url = response.geturl()
            if not is_official_bilkent_url(final_url):
                raise AssetValidationError(
                    f"final URL leaves the Bilkent HTTPS boundary: {final_url}"
                )
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_IMAGE_BYTES:
                raise AssetValidationError(
                    f"remote image exceeds {MAX_IMAGE_BYTES} bytes"
                )
            payload = response.read(MAX_IMAGE_BYTES + 1)
            mime = response.headers.get_content_type()
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        if isinstance(error, AssetValidationError):
            raise
        raise AssetValidationError(f"could not fetch {source_url}: {error}") from error
    detected_mime, width, height = inspect_image(payload, mime)
    return payload, detected_mime, width, height


def _preflight_manifest(
    root: Path, manifest: dict[str, object]
) -> tuple[list[_AssetSpec], set[str], list[str]]:
    """Validate the complete destination set without network or filesystem writes."""
    root = root.absolute()
    errors: list[str] = []
    specs: list[_AssetSpec] = []
    expected_root_fields = {"schema_version", "assets"}
    if set(manifest) != expected_root_fields:
        errors.append("sources.json: root fields must be exactly schema_version and assets")
    if manifest.get("schema_version") != 1:
        errors.append("sources.json: schema_version must be 1")
    entries = manifest.get("assets")
    if not isinstance(entries, list):
        return [], set(), sorted(set([*errors, "sources.json: assets must be a list"]))

    seen_exact: set[str] = set()
    seen_casefolded: dict[str, str] = {}
    asset_root = root / "docs" / "assets"
    for index, raw_entry in enumerate(entries):
        label = f"sources.json: assets[{index}]"
        if not isinstance(raw_entry, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        if set(raw_entry) != ASSET_FIELDS:
            errors.append(f"{label}: fields must match the exact asset schema")

        path_value = raw_entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"{label}: path must be a non-empty string")
            continue
        normalized = PurePosixPath(path_value)
        invalid_path = (
            "\\" in path_value
            or normalized.is_absolute()
            or bool(re.match(r"^[A-Za-z]:", path_value))
            or ".." in normalized.parts
            or normalized.as_posix() != path_value
            or len(normalized.parts) < 3
            or normalized.parts[:2] != ("docs", "assets")
            or path_value == "docs/assets/sources.json"
        )
        if invalid_path:
            errors.append(f"{label}: path must stay strictly under docs/assets")
            continue
        display = normalized.as_posix()
        folded = display.casefold()
        if display in seen_exact:
            errors.append(f"{label}: duplicate path {display}")
            continue
        if folded in seen_casefolded:
            errors.append(
                f"{label}: case collision with {seen_casefolded[folded]}"
            )
            continue
        seen_exact.add(display)
        seen_casefolded[folded] = display

        for field in ("source_page", "source_url"):
            value = raw_entry.get(field)
            if not isinstance(value, str) or not is_official_source_url(value):
                errors.append(f"{label}: {field} must be an official Bilkent HTTPS or CTIS page")
        retrieved = raw_entry.get("retrieved")
        if not isinstance(retrieved, str) or not DATE_RE.fullmatch(retrieved):
            errors.append(f"{label}: retrieved must be an ISO date")
        else:
            try:
                date.fromisoformat(retrieved)
            except ValueError:
                errors.append(f"{label}: retrieved must be a valid ISO date")
        rights_note = raw_entry.get("rights_note")
        if not isinstance(rights_note, str) or not rights_note.strip():
            errors.append(f"{label}: rights_note must be non-empty")
        digest = raw_entry.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{label}: sha256 must be 64 lowercase hexadecimal characters")
        mime = raw_entry.get("mime")
        if mime not in ALLOWED_MIME_TYPES:
            errors.append(f"{label}: mime must be image/jpeg or image/png")
        for field in ("width", "height"):
            value = raw_entry.get(field)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < MIN_IMAGE_DIMENSION
            ):
                errors.append(
                    f"{label}: {field} must be an integer at least {MIN_IMAGE_DIMENSION}"
                )
        suffix = normalized.suffix.casefold()
        if (mime == "image/png" and suffix != ".png") or (
            mime == "image/jpeg" and suffix not in {".jpg", ".jpeg"}
        ):
            errors.append(f"{label}: path suffix does not match mime")

        destination = root.joinpath(*normalized.parts)
        try:
            destination.resolve(strict=False).relative_to(
                asset_root.resolve(strict=False)
            )
        except ValueError:
            errors.append(f"{label}: resolved path leaves docs/assets")
            continue
        current = root
        for part in normalized.parts:
            if current.is_symlink():
                errors.append(
                    f"{label}: destination or parent is a symbolic link: {current}"
                )
                break
            current = current / part
        if current.is_symlink():
            errors.append(
                f"{label}: destination or parent is a symbolic link: {current}"
            )
        if destination.exists() and not destination.is_file():
            errors.append(f"{label}: destination is not a regular file")
        specs.append(_AssetSpec(index, display, destination, raw_entry))

    actual_files: set[str] = set()
    if asset_root.is_symlink():
        errors.append("docs/assets: symbolic link is not allowed")
    elif asset_root.exists():
        for candidate in asset_root.rglob("*"):
            relative = candidate.relative_to(root).as_posix()
            if candidate.is_symlink():
                errors.append(f"{relative}: symbolic link is not allowed")
            if candidate.is_file() and relative != "docs/assets/sources.json":
                actual_files.add(relative)
    for undeclared in sorted(actual_files - seen_exact):
        errors.append(f"{undeclared}: undeclared asset file")
    return specs, actual_files, sorted(set(errors))


def validate_local_assets(root: Path, manifest: dict[str, object]) -> list[str]:
    """Return deterministic errors for local/manifest mismatch without network."""
    specs, actual_files, errors = _preflight_manifest(root, manifest)
    for spec in specs:
        if spec.display not in actual_files and not spec.destination.is_symlink():
            errors.append(f"{spec.display}: declared image is missing")
            continue
        if not spec.destination.is_file() or spec.destination.is_symlink():
            continue
        try:
            payload = spec.destination.read_bytes()
            mime, width, height = inspect_image(payload, str(spec.entry.get("mime", "")))
            digest = hashlib.sha256(payload).hexdigest()
        except (OSError, AssetValidationError) as error:
            errors.append(f"{spec.display}: {error}")
            continue
        expected = (
            spec.entry.get("mime"),
            spec.entry.get("width"),
            spec.entry.get("height"),
            spec.entry.get("sha256"),
        )
        actual = (mime, width, height, digest)
        if expected != actual:
            errors.append(f"{spec.display}: byte/hash/MIME/dimension mismatch")
    return sorted(set(errors))


def check_remote_assets(manifest: dict[str, object]) -> list[str]:
    """Fetch every declared official image and compare it with recorded metadata."""
    entries = manifest.get("assets")
    if not isinstance(entries, list):
        return ["sources.json: assets must be a list"]
    errors: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"sources.json: assets[{index}]: entry must be an object")
            continue
        display = str(entry.get("path", f"assets[{index}]"))
        try:
            payload, mime, width, height = fetch_asset(str(entry.get("source_url", "")))
        except AssetValidationError as error:
            errors.append(f"{display}: {error}")
            continue
        actual = (hashlib.sha256(payload).hexdigest(), mime, width, height)
        expected = (
            entry.get("sha256"),
            entry.get("mime"),
            entry.get("width"),
            entry.get("height"),
        )
        if actual != expected:
            errors.append(f"{display}: remote bytes no longer match sources.json")
    return sorted(errors)


def fetch_declared_assets(root: Path, manifest: dict[str, object]) -> list[str]:
    """Fetch, fully validate, and transactionally replace declared asset bytes."""
    root = root.absolute()
    specs, _, errors = _preflight_manifest(root, manifest)
    if errors:
        return errors

    with tempfile.TemporaryDirectory(prefix="ctis-assets-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        stage_root = temporary_root / "stage"
        backup_root = temporary_root / "backup"
        stage_root.mkdir()
        backup_root.mkdir()
        staged: list[tuple[_AssetSpec, Path]] = []

        for spec in specs:
            try:
                payload, mime, width, height = fetch_asset(
                    str(spec.entry["source_url"])
                )
            except AssetValidationError as error:
                errors.append(f"{spec.display}: {error}")
                continue
            actual = (hashlib.sha256(payload).hexdigest(), mime, width, height)
            expected = (
                spec.entry["sha256"],
                spec.entry["mime"],
                spec.entry["width"],
                spec.entry["height"],
            )
            if actual != expected:
                errors.append(
                    f"{spec.display}: remote bytes do not match declared metadata"
                )
                continue
            staged_path = stage_root / f"{spec.index:04d}{spec.destination.suffix.lower()}"
            staged_path.write_bytes(payload)
            staged.append((spec, staged_path))
        if errors:
            return sorted(set(errors))

        for spec, staged_path in staged:
            try:
                payload = staged_path.read_bytes()
                mime, width, height = inspect_image(
                    payload, str(spec.entry["mime"])
                )
            except (OSError, AssetValidationError) as error:
                errors.append(f"{spec.display}: staged image is invalid: {error}")
                continue
            actual = (hashlib.sha256(payload).hexdigest(), mime, width, height)
            expected = (
                spec.entry["sha256"],
                spec.entry["mime"],
                spec.entry["width"],
                spec.entry["height"],
            )
            if actual != expected:
                errors.append(f"{spec.display}: staged bytes failed full-set validation")
        if errors:
            return sorted(set(errors))

        _, _, second_preflight_errors = _preflight_manifest(root, manifest)
        if second_preflight_errors:
            return second_preflight_errors
        return _replace_staged_assets(
            root, manifest, staged, backup_root
        )


def _replace_staged_assets(
    root: Path,
    manifest: dict[str, object],
    staged: list[tuple[_AssetSpec, Path]],
    backup_root: Path,
) -> list[str]:
    backups: dict[str, Path] = {}
    created_directories: set[Path] = set()
    try:
        for spec, _ in staged:
            if spec.destination.exists():
                backup = backup_root / f"{spec.index:04d}.backup"
                shutil.copy2(spec.destination, backup)
                backups[spec.display] = backup
    except OSError as error:
        return [f"asset replacement aborted before mutation; backup failed: {error}"]

    try:
        for spec, _ in staged:
            missing = [
                parent
                for parent in spec.destination.parent.parents
                if parent != root and root in parent.parents and not parent.exists()
            ]
            if not spec.destination.parent.exists():
                missing.append(spec.destination.parent)
            for directory in sorted(set(missing), key=lambda item: len(item.parts)):
                directory.mkdir(exist_ok=True)
                created_directories.add(directory)
    except OSError as error:
        cleanup_errors = _remove_created_directories(created_directories)
        return sorted(
            set(
                [
                    "asset replacement aborted before file mutation; "
                    f"directory creation failed: {error}",
                    *cleanup_errors,
                ]
            )
        )

    try:
        for spec, staged_path in staged:
            os.replace(staged_path, spec.destination)
    except OSError as error:
        rollback_errors = _rollback_assets(staged, backups, created_directories)
        return sorted(
            set(
                [
                    "asset replacement failed; attempted full rollback: " + str(error),
                    *rollback_errors,
                ]
            )
        )

    validation_errors = validate_local_assets(root, manifest)
    if validation_errors:
        rollback_errors = _rollback_assets(staged, backups, created_directories)
        return sorted(
            set(
                [
                    "asset replacement failed post-write validation; attempted full rollback",
                    *validation_errors,
                    *rollback_errors,
                ]
            )
        )
    return []


def _rollback_assets(
    staged: list[tuple[_AssetSpec, Path]],
    backups: dict[str, Path],
    created_directories: set[Path],
) -> list[str]:
    errors: list[str] = []
    for spec, _ in reversed(staged):
        backup = backups.get(spec.display)
        try:
            if backup is not None and backup.exists():
                try:
                    os.replace(backup, spec.destination)
                except OSError:
                    shutil.copy2(backup, spec.destination)
            elif spec.destination.exists() or spec.destination.is_symlink():
                spec.destination.unlink()
        except OSError as error:
            errors.append(f"{spec.display}: rollback failed: {error}")
    errors.extend(_remove_created_directories(created_directories))
    return errors


def _remove_created_directories(created_directories: set[Path]) -> list[str]:
    errors: list[str] = []
    for directory in sorted(created_directories, key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            if directory.exists():
                errors.append(f"{directory}: rollback could not remove created directory")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch or verify declared CTIS assets from official Bilkent sources."
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="perform the explicit network byte-for-byte source check",
    )
    arguments = parser.parse_args()
    manifest_path = arguments.root / "docs" / "assets" / "sources.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"SOURCE_CHECK_FAILED: {error}")
        return 1

    local_errors = validate_local_assets(arguments.root, manifest)
    if arguments.check:
        errors = local_errors or check_remote_assets(manifest)
        label = "SOURCE_CHECK_OK"
    else:
        errors = fetch_declared_assets(arguments.root, manifest)
        label = "ASSET_FETCH_OK"
    for error in sorted(set(errors)):
        print(error)
    if errors:
        return 1
    print(f"{label}: {len(manifest.get('assets', []))} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
