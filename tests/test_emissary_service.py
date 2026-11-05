"""Render Emissary routing regressions with Helm and Python's standard library.

Run: HELM_BIN=/path/to/helm python -m unittest discover -s tests -v
"""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


CHART = Path(__file__).resolve().parents[1] / "charts" / "universal-helm"
HELM = os.environ.get("HELM_BIN", "helm")
DEFAULT_SERVICE = "emissary-ingress.emissary-ingress"


class EmissaryServiceTest(unittest.TestCase):
    def render(self, workload_kind, global_emissary=None, enabled=True):
        workload = {
            "name": "test-node",
            "containers": [{
                "name": "rpc",
                "image": {"repository": "nginx", "tag": "stable"},
                "ports": [{
                    "name": "http",
                    "port": 8545,
                    "emissary": {"host": "rpc.example.test", "enabled": enabled},
                }],
            }],
        }
        if workload_kind == "statefulsets":
            workload["persistence"] = {"volumeMountPath": "/data", "size": "1Gi"}
        values = {workload_kind: [workload]}
        if global_emissary is not None:
            values["global"] = {"emissary": global_emissary}
        with tempfile.TemporaryDirectory() as directory:
            values_path = Path(directory) / "values.json"
            values_path.write_text(json.dumps(values), encoding="utf-8")
            result = subprocess.run(
                [HELM, "template", "emissary-test", str(CHART),
                 "--values", str(values_path),
                 "--show-only", "templates/emissary-ingress.yaml"],
                capture_output=True, text=True,
            )
        return result

    def assert_service(self, result, expected):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(re.findall(r"(?m)^kind: Host$", result.stdout)), 1)
        self.assertEqual(len(re.findall(r"(?m)^kind: Mapping$", result.stdout)), 1)
        annotations = re.findall(
            r"(?m)^    external-dns\.ambassador-service: (.+)$", result.stdout,
        )
        self.assertEqual(annotations, [expected])
        self.assertIn("  host: rpc.example.test", result.stdout)
        self.assertIn("  service: http://test-node-rpc-http:8545", result.stdout)

    def test_default_without_global_emissary(self):
        for kind in ("deployments", "statefulsets"):
            with self.subTest(kind=kind):
                self.assert_service(self.render(kind), DEFAULT_SERVICE)

    def test_empty_service_uses_default(self):
        for kind in ("deployments", "statefulsets"):
            with self.subTest(kind=kind):
                self.assert_service(
                    self.render(kind, {"emissaryServiceName": ""}), DEFAULT_SERVICE,
                )

    def test_custom_service(self):
        for kind in ("deployments", "statefulsets"):
            with self.subTest(kind=kind):
                self.assert_service(
                    self.render(kind, {"emissaryServiceName": "gateway.ingress"}),
                    "gateway.ingress",
                )


if __name__ == "__main__":
    unittest.main()
