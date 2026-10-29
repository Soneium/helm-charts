"""Render regressions: HELM_BIN=/path/to/helm python -m unittest discover -s tests.

Uses only Python's standard library and Helm. Fixtures use JSON (valid YAML),
and assertions inspect the rendered PodSpec's imagePullSecrets YAML block.
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
MISSING = object()
GLOBAL_SECRETS = [{"name": "global-primary"}, {"name": "global-backup"}]
LOCAL_SECRETS = [{"name": "workload-registry"}]


class ImagePullSecretsTest(unittest.TestCase):
    def render(self, global_secrets=MISSING, local_secrets=MISSING):
        values = {}
        if global_secrets is not MISSING:
            values["global"] = {"imagePullSecrets": global_secrets}
        for key in ("deployments", "statefulsets"):
            workload = {
                "name": "test-" + key,
                "containers": [{
                    "name": "app",
                    "image": {"repository": "nginx", "tag": "stable"},
                }],
            }
            if key == "statefulsets":
                workload["persistence"] = {
                    "volumeMountPath": "/data", "size": "1Gi",
                }
            if local_secrets is not MISSING:
                workload["imagePullSecrets"] = local_secrets
            values[key] = [workload]

        with tempfile.TemporaryDirectory() as directory:
            values_path = Path(directory) / "values.json"
            values_path.write_text(json.dumps(values), encoding="utf-8")
            result = subprocess.run(
                [HELM, "template", "pull-secrets-test", str(CHART),
                 "--values", str(values_path),
                 "--show-only", "templates/deployments.yaml",
                 "--show-only", "templates/statefulsets.yaml"],
                capture_output=True, text=True, check=True,
            )
        documents = re.split(r"(?m)^---\s*$", result.stdout)
        workloads = {}
        for document in documents:
            match = re.search(r"(?m)^kind: (Deployment|StatefulSet)$", document)
            if match:
                self.assertNotIn(match[1], workloads)
                workloads[match[1]] = document
        self.assertEqual(set(workloads), {"Deployment", "StatefulSet"})
        return workloads

    def assert_secrets(self, workloads, expected):
        for kind, document in workloads.items():
            with self.subTest(kind=kind):
                # Restrict assertions to the PodSpec, not container or metadata fields.
                pod_spec = document.split("    spec:\n", 1)[1]
                pod_spec = re.split(r"(?m)^  \S", pod_spec, maxsplit=1)[0]
                blocks = re.findall(
                    r"(?m)^      imagePullSecrets:[ \t]*\n(?:^        .*(?:\n|$))*",
                    pod_spec,
                )
                if expected:
                    self.assertEqual(len(blocks), 1, document)
                    expected_block = "      imagePullSecrets:\n" + "".join(
                        "        - name: " + secret["name"] + "\n"
                        for secret in expected
                    )
                    normalized = "\n".join(line.rstrip() for line in blocks[0].splitlines())
                    self.assertEqual(normalized, expected_block.rstrip("\n"))
                else:
                    self.assertNotIn("imagePullSecrets:", pod_spec)

    def test_global_fallback(self):
        self.assert_secrets(self.render(GLOBAL_SECRETS), GLOBAL_SECRETS)

    def test_workload_overrides_global(self):
        self.assert_secrets(
            self.render(GLOBAL_SECRETS, LOCAL_SECRETS), LOCAL_SECRETS,
        )

    def test_explicit_empty_workload_disables_global(self):
        self.assert_secrets(self.render(GLOBAL_SECRETS, []), [])

    def test_absent_settings_omit_secrets(self):
        self.assert_secrets(self.render(), [])

    def test_workload_secrets_without_global(self):
        self.assert_secrets(self.render(local_secrets=LOCAL_SECRETS), LOCAL_SECRETS)


if __name__ == "__main__":
    unittest.main()
