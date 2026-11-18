import hashlib
import json
import re
from pathlib import Path

from openrgb_display_control.topology import MATRIX_MAP

ROOT = Path(__file__).resolve().parents[1]


def test_native_patch_and_python_map_agree():
    patch = (ROOT / "upstream/0001-Add-X670E-Extreme-AniMe-Matrix-driver.patch").read_text()
    section = patch.split("+static const unsigned char ASUS_MATRIX_MAP", 1)[1].split("+};", 1)[0]
    numbers = []
    for line in section.splitlines()[1:]:
        if re.fullmatch(r"\+\s+[\d, ]+", line):
            numbers.extend(int(n) for n in re.findall(r"\d+", line))
    assert tuple(numbers) == MATRIX_MAP


def test_native_handoff_is_core_only_and_patch_hash_matches():
    manifest = json.loads((ROOT / "upstream/driver_manifest.json").read_text())
    patch = (ROOT / "upstream/0001-Add-X670E-Extreme-AniMe-Matrix-driver.patch").read_bytes()
    assert hashlib.sha256(patch).hexdigest() == manifest["patch_sha256"]
    assert all(
        p.startswith("Controllers/AsusAnimeMatrixController/")
        or p == "Documentation/ASUSAnimeMatrix.md"
        for p in manifest["files"]
    )
    assert not manifest["human_review_complete"]
