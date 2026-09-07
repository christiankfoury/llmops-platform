"""Reject corrupted, ambiguous and unsafe immutable image archives before any registry call."""

import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from release_bundle import inspect_oci, json_bytes  # noqa: E402


class BundleTest(unittest.TestCase):
    def setUp(self):
        cache = ROOT / ".maven-cache"
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache, prefix="oci-tests-")
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(cache.resolve())
        self.addCleanup(self.temp.cleanup)
        self.members = {}

        def blob(data, media):
            digest = hashlib.sha256(data).hexdigest()
            self.members["blobs/sha256/" + digest] = data
            return {"digest": "sha256:" + digest, "size": len(data), "mediaType": media}

        self.config = blob(
            b'{"os":"linux","architecture":"amd64"}', "application/vnd.oci.image.config.v1+json"
        )
        layer = blob(b"synthetic-layer", "application/vnd.oci.image.layer.v1.tar+gzip")
        self.manifest = blob(
            json.dumps({"schemaVersion": 2, "config": self.config, "layers": [layer]}).encode(),
            "application/vnd.oci.image.manifest.v1+json",
        )
        self.members["index.json"] = json.dumps(
            {"schemaVersion": 2, "manifests": [self.manifest]}
        ).encode()
        self.members["oci-layout"] = b'{"imageLayoutVersion":"1.0.0"}'

    def archive(self, extra=None):
        path = self.root / "image.oci.tar"
        with tarfile.open(path, "w") as archive:
            for name, data in self.members.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
            if extra is not None:
                archive.addfile(extra)
        return path

    def test_valid_content_and_configuration_digests(self):
        result = inspect_oci(self.archive())
        self.assertEqual(result["digest"], self.manifest["digest"])
        self.assertEqual(result["config_digest"], self.config["digest"])

    def test_blob_tampering_is_rejected(self):
        self.members["blobs/sha256/" + self.config["digest"].split(":")[1]] = b"corrupted"
        with self.assertRaises(ValueError):
            inspect_oci(self.archive())

    def test_missing_blob_is_rejected(self):
        del self.members["blobs/sha256/" + self.config["digest"].split(":")[1]]
        with self.assertRaises((ValueError, KeyError)):
            inspect_oci(self.archive())

    def test_traversal_links_duplicate_and_unreferenced_data_are_rejected(self):
        for name, kind in (
            ("../outside", tarfile.REGTYPE),
            ("/absolute", tarfile.REGTYPE),
            ("index.json", tarfile.REGTYPE),
            ("link", tarfile.SYMTYPE),
        ):
            item = tarfile.TarInfo(name)
            item.type = kind
            with self.subTest(name=name), self.assertRaises(ValueError):
                inspect_oci(self.archive(item))
        self.members["blobs/sha256/" + "0" * 64] = b"unreferenced"
        with self.assertRaises(ValueError):
            inspect_oci(self.archive())

    def test_ambiguous_roots_and_descriptor_size_changes_are_rejected(self):
        self.members["index.json"] = json.dumps(
            {
                "schemaVersion": 2,
                "manifests": [self.manifest, {**self.manifest, "digest": "sha256:" + "0" * 64}],
            }
        ).encode()
        with self.assertRaises(ValueError):
            inspect_oci(self.archive())
        self.members["index.json"] = json.dumps(
            {"schemaVersion": 2, "manifests": [{**self.manifest, "size": 1}]}
        ).encode()
        with self.assertRaises(ValueError):
            inspect_oci(self.archive())

    def test_duplicate_json_properties_are_rejected(self):
        with self.assertRaises(ValueError):
            json_bytes(b'{"digest":"first","digest":"second"}')


if __name__ == "__main__":
    unittest.main()
