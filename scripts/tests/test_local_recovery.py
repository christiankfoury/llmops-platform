"""Recovery cleanup must refuse unrelated resources even after a failed API probe."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from rehearse_local_recovery import stop_owned  # noqa: E402


class CleanupTest(unittest.TestCase):
    def test_foreign_or_invalid_container_cannot_be_stopped(self):
        run = Mock(
            return_value=json.dumps(
                [{"Config": {"Labels": {"com.docker.compose.project": "existing-project"}}}]
            ).encode()
        )
        with self.assertRaises(ValueError):
            stop_owned("a" * 64, "new-rehearsal", run)
        self.assertEqual(run.call_count, 1)
        run.assert_called_with("docker", "inspect", "a" * 64)
        run.reset_mock()
        with self.assertRaises(ValueError):
            stop_owned("existing-name", "new-rehearsal", run)
        run.assert_not_called()

    def test_owned_container_stops_without_removing_storage(self):
        run = Mock(
            return_value=json.dumps(
                [{"Config": {"Labels": {"com.docker.compose.project": "new-rehearsal"}}}]
            ).encode()
        )
        stop_owned("b" * 64, "new-rehearsal", run)
        self.assertEqual(run.call_count, 2)
        run.assert_called_with("docker", "stop", "--time", "60", "b" * 64)


if __name__ == "__main__":
    unittest.main()
