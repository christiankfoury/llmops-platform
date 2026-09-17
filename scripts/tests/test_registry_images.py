"""Reject changed registry bytes, public packages and untrusted image publication."""

import copy
import io
import json
import os
import sys
import tarfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import registry_images as registry  # noqa: E402
import test_release_bundle as fixtures  # noqa: E402
from release_bundle import IMAGES, REPOSITORY, inspect_oci  # noqa: E402


class RegistryImagesTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BundleTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.path = self.fixture.archive()
        self.record = inspect_oci(self.path)
        self.manifest = {
            "image_storage": {
                "provider": "ghcr",
                "visibility": "private",
                "verified_images": list(IMAGES),
            },
            "images": {
                name: {
                    **self.record,
                    "registry_source": registry.image_repository(name)
                    + "@"
                    + self.record["digest"],
                }
                for name in IMAGES
            },
        }

    def test_registry_transport_allows_repacked_tar_but_not_changed_image_bytes(self):
        repacked = self.path.with_name("repacked.tar")
        with tarfile.open(self.path) as source, tarfile.open(repacked, "w") as dest:
            for member in source:
                member.mtime = 12345
                dest.addfile(member, source.extractfile(member))
        registry.verify_image(repacked, self.record, registry=True)
        with self.assertRaises(ValueError):
            registry.verify_image(repacked, self.record, registry=False)
        for field in registry.FIELDS:
            bad = {**self.record, field: "changed"}
            with self.subTest(field=field), self.assertRaises(ValueError):
                registry.verify_image(repacked, bad, registry=True)
        key = "blobs/sha256/" + self.record["config_digest"].split(":")[1]
        self.fixture.members[key] = b"tampered"
        with self.assertRaises(ValueError):
            registry.verify_image(self.fixture.archive(), self.record, registry=True)

    def test_only_private_complete_fixed_registry_sources_are_accepted(self):
        registry.validate_storage(self.manifest)
        for source in (
            "ghcr.io/other/image@" + self.record["digest"],
            registry.image_repository("api") + ":latest",
            registry.image_repository("web") + "@" + self.record["digest"],
        ):
            bad = copy.deepcopy(self.manifest)
            bad["images"]["api"]["registry_source"] = source
            with self.assertRaises(ValueError):
                registry.validate_storage(bad)
        for field, value in (
            ("visibility", "public"),
            ("verified_images", ["api"]),
            ("provider", "other"),
        ):
            bad = copy.deepcopy(self.manifest)
            bad["image_storage"][field] = value
            with self.assertRaises(ValueError):
                registry.validate_storage(bad)

    def test_public_unlinked_and_inaccessible_packages_fail_closed(self):
        package = {
            "name": "production-ai-platform-ci-api",
            "package_type": "container",
            "visibility": "private",
            "repository": {"full_name": REPOSITORY},
        }
        for bad in (
            {**package, "visibility": "public"},
            {**package, "repository": {"full_name": "foreign/repo"}},
        ):
            with patch(
                "registry_images.urllib.request.urlopen",
                return_value=io.BytesIO(json.dumps(bad).encode()),
            ):
                with self.assertRaises(ValueError):
                    registry.private_package("api", "synthetic-token")
        for code in (401, 403, 404, 500):
            error = urllib.error.HTTPError("https://api.github.com", code, "fixture", {}, None)
            with patch("registry_images.urllib.request.urlopen", side_effect=error):
                with self.assertRaises(ValueError):
                    registry.private_package("api", "synthetic-token")
        for private in (True, False):
            missing = urllib.error.HTTPError("https://api.github.com", 404, "fixture", {}, None)
            response = io.BytesIO(
                json.dumps({"private": private, "full_name": REPOSITORY}).encode()
            )
            with patch("registry_images.urllib.request.urlopen", side_effect=[missing, response]):
                if private:
                    registry.private_package("api", "synthetic-token", allow_missing=True)
                else:
                    with self.assertRaises(ValueError):
                        registry.private_package("api", "synthetic-token", allow_missing=True)

    def test_untrusted_publication_is_rejected_before_any_registry_or_file_access(self):
        trusted = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REPOSITORY": REPOSITORY,
        }
        for field, value in (
            ("GITHUB_ACTIONS", "false"),
            ("GITHUB_EVENT_NAME", "pull_request"),
            ("GITHUB_REF", "refs/heads/feature"),
            ("GITHUB_REPOSITORY", "fork/repo"),
        ):
            with (
                patch.dict(os.environ, {**trusted, field: value}, clear=True),
                patch("registry_images.invoke") as call,
            ):
                with self.assertRaises(ValueError):
                    registry.publish_images()
                call.assert_not_called()

    def test_registry_errors_do_not_echo_credentials_or_response_bodies(self):
        with patch("registry_images.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = b"fixture-sensitive-response"
            with self.assertRaisesRegex(RuntimeError, "^Verified registry transfer failed$"):
                registry.invoke(["docker", "fixture"])


if __name__ == "__main__":
    unittest.main()
