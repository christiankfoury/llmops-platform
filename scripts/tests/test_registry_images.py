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
from validate_ci_policy import check_image_source_labels  # noqa: E402


class RegistryImagesTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BundleTest()
        self.fixture.source = "https://github.com/" + REPOSITORY
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

    def test_public_foreign_and_inaccessible_packages_fail_closed(self):
        package = {
            "name": "production-ai-platform-ci-api",
            "package_type": "container",
            "visibility": "private",
            "repository": {"full_name": REPOSITORY},
            "owner": {"login": REPOSITORY.split("/")[0]},
        }
        for bad in (
            {**package, "visibility": "public"},
            {**package, "repository": {"full_name": "foreign/repo"}},
            {**package, "owner": {"login": "foreign"}},
            {**package, "owner": None},
            {**package, "name": "foreign-package"},
            {**package, "package_type": "npm"},
        ):
            with patch(
                "registry_images.urllib.request.urlopen",
                return_value=io.BytesIO(json.dumps(bad).encode()),
            ):
                with self.assertRaises(ValueError):
                    registry.private_package("api", "synthetic-token")
        with patch(
            "registry_images.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(package).encode()),
        ):
            registry.private_package("api", "synthetic-token")
        # GHCR's granular metadata can omit repository even when the UI is linked.
        # Privacy and ownership are still checked; image source is verified below.
        for repository_field in ({"repository": None}, {}):
            response = {k: v for k, v in package.items() if k != "repository"}
            response.update(repository_field)
            with patch(
                "registry_images.urllib.request.urlopen",
                return_value=io.BytesIO(json.dumps(response).encode()),
            ):
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

    def test_every_image_build_requires_its_source_label_before_testing(self):
        step = {
            "uses": "docker/build-push-action@" + "a" * 40,
            "with": {"labels": "org.opencontainers.image.source=https://github.com/" + REPOSITORY},
        }
        job = {"steps": [copy.deepcopy(step) for _ in IMAGES]}
        check_image_source_labels(job)
        for index in range(3):
            for label in (None, "org.opencontainers.image.source=https://github.com/foreign/repo"):
                bad = copy.deepcopy(job)
                bad["steps"][index]["with"]["labels"] = label
                with self.subTest(index=index, label=label), self.assertRaises(ValueError):
                    check_image_source_labels(bad)

    def test_verified_registry_bytes_require_the_exact_source_repository(self):
        for source in (None, "https://github.com/foreign/repo"):
            fixture = fixtures.BundleTest()
            fixture.source = source
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            path = fixture.archive()
            record = inspect_oci(path)
            # Historical Actions archives retain their original byte checks.
            registry.verify_image(path, record, registry=False)
            for registry_mode in (True, False):
                with (
                    self.subTest(source=source, registry=registry_mode),
                    self.assertRaises(ValueError),
                ):
                    registry.verify_image(path, record, registry=registry_mode, require_source=True)

    def test_registry_errors_do_not_echo_credentials_or_response_bodies(self):
        with patch("registry_images.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = b"fixture-sensitive-response"
            with self.assertRaisesRegex(RuntimeError, "^Verified registry transfer failed$"):
                registry.invoke(["docker", "fixture"])


if __name__ == "__main__":
    unittest.main()
