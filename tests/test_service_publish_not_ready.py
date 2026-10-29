"""Service render regression tests (Python stdlib and Helm only).

Run: python -m unittest discover -s tests -v
Set HELM_BINARY if helm is not on PATH.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


CHART = Path(__file__).resolve().parents[1] / "charts" / "universal-helm"


class ServiceRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ports = [
            {"name": "enabled", "port": 8080, "publishNotReadyAddresses": True},
            {"name": "disabled", "port": 8081, "publishNotReadyAddresses": False},
            {"name": "absent", "port": 8082},
        ]
        container = {
            "name": "app",
            "image": {"repository": "nginx", "tag": "stable"},
            "ports": ports,
        }
        values = {
            "deployments": [{"name": "deployment", "containers": [container]}],
            "statefulsets": [{
                "name": "statefulset",
                "containers": [container],
                "persistence": {"volumeMountPath": "/data", "size": "1Gi"},
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            values_path = Path(directory) / "values.json"
            values_path.write_text(json.dumps(values), encoding="utf-8")
            result = subprocess.run(
                [os.environ.get("HELM_BINARY", "helm"), "template", "regression",
                 str(CHART), "--show-only", "templates/service.yaml",
                 "--values", str(values_path)],
                check=True, capture_output=True, text=True,
            )
        cls.services = {}
        for document in re.split(r"(?m)^---\s*$", result.stdout):
            if not document.strip():
                continue
            if not re.search(r"(?m)^kind: Service$", document):
                raise AssertionError(f"Unexpected rendered document: {document}")
            name = re.search(r"(?m)^  name: (\S+)$", document).group(1)
            # Compare the complete spec at its rendered indentation. Helm parses
            # YAML during rendering; no third-party YAML parser is needed here.
            spec = document.split("\nspec:\n", 1)[1]
            cls.services[name] = "\n".join(
                line for line in spec.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )

    def assert_port_service(self, workload, state, port, enabled):
        expected = [
            "  selector:",
            f"    {workload}name: {workload}",
            "  type: ClusterIP",
        ]
        if enabled:
            expected.append("  publishNotReadyAddresses: true")
        expected.extend([
            "  ports:",
            f"    - port: {port}",
            f"      targetPort: {port}",
            "      protocol: TCP",
            f"      name: {state}",
        ])
        self.assertEqual(
            self.services[f"{workload}-app-{state}"], "\n".join(expected)
        )

    def test_deployment_true(self):
        self.assert_port_service("deployment", "enabled", 8080, True)

    def test_deployment_false(self):
        self.assert_port_service("deployment", "disabled", 8081, False)

    def test_deployment_absent(self):
        self.assert_port_service("deployment", "absent", 8082, False)

    def test_statefulset_true(self):
        self.assert_port_service("statefulset", "enabled", 8080, True)

    def test_statefulset_false(self):
        self.assert_port_service("statefulset", "disabled", 8081, False)

    def test_statefulset_absent(self):
        self.assert_port_service("statefulset", "absent", 8082, False)

    def test_headless_service_unchanged(self):
        self.assertEqual(self.services["statefulset"], "\n".join([
            "  selector:",
            "    statefulsetname: statefulset",
            "  ports:",
            "    - port: 12345",
            "  clusterIP: None",
            "  publishNotReadyAddresses: true",
        ]))
        self.assertEqual(len(self.services), 7)


if __name__ == "__main__":
    unittest.main()
