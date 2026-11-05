"""Pod volume render regressions; requires Helm and Python's standard library.

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


def workload(kind, name="test-node", source="secretName", shared=True):
    containers = []
    for index in range(2):
        volume_name = "shared-config" if shared else f"config-{index}"
        containers.append({
            "name": f"app-{index}",
            "image": {"repository": "nginx", "tag": "stable"},
            "extraVolumes": [{source: volume_name, "mountPath": "/config"}],
        })
    result = {"name": name, "containers": containers}
    if kind == "statefulsets":
        result["persistence"] = {"volumeMountPath": "/data", "size": "1Gi"}
    return result


class SharedVolumesTest(unittest.TestCase):
    def render(self, kind, workloads):
        with tempfile.TemporaryDirectory() as directory:
            values = Path(directory) / "values.json"
            values.write_text(json.dumps({kind: workloads}), encoding="utf-8")
            return subprocess.run(
                [HELM, "template", "shared-volumes", str(CHART),
                 "--values", str(values),
                 "--show-only", f"templates/{kind}.yaml"],
                capture_output=True, text=True,
            )

    def documents(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        documents = {}
        for document in re.split(r"(?m)^---\s*$", result.stdout):
            if not re.search(r"(?m)^kind: (Deployment|StatefulSet)$", document):
                continue
            name = re.search(r"(?m)^  name: (\S+)$", document).group(1)
            self.assertNotIn(name, documents)
            documents[name] = document
        return documents

    def volumes(self, document):
        # Inspect only the PodSpec volumes, excluding container mounts and PVCs.
        lines = document.splitlines()
        start = lines.index("      volumes:") + 1
        block = []
        for line in lines[start:]:
            if line.strip() and len(line) - len(line.lstrip()) <= 6:
                break
            block.append(line)
        block = "\n".join(block)
        names = re.findall(r"(?m)^        - name: (\S+)$", block)
        self.assertEqual(len(names), len(set(names)), block)
        return names, block

    def test_shared_sources_are_defined_once_and_mounted_twice(self):
        for kind in ("deployments", "statefulsets"):
            for source, expected_kind in (
                ("secretName", "secret"),
                ("configMap", "configMap"),
                ("persistentVolumeClaim", "persistentVolumeClaim"),
            ):
                with self.subTest(kind=kind, source=source):
                    document = self.documents(self.render(kind, [workload(kind, source=source)]))["test-node"]
                    names, block = self.volumes(document)
                    self.assertEqual(names, ["shared-config"])
                    self.assertIn(f"          {expected_kind}:", block)
                    self.assertEqual(len(re.findall(
                        r"(?m)^            - name: shared-config$", document,
                    )), 2)

    def test_distinct_sources_remain_distinct(self):
        for kind in ("deployments", "statefulsets"):
            with self.subTest(kind=kind):
                document = self.documents(self.render(kind, [workload(kind, shared=False)]))["test-node"]
                names, _ = self.volumes(document)
                self.assertEqual(names, ["config-0", "config-1"])

    def test_no_optional_volumes_remains_empty(self):
        for kind in ("deployments", "statefulsets"):
            with self.subTest(kind=kind):
                item = workload(kind)
                for container in item["containers"]:
                    del container["extraVolumes"]
                document = self.documents(self.render(kind, [item]))["test-node"]
                self.assertEqual(self.volumes(document)[0], [])

    def test_volume_names_are_scoped_to_each_workload(self):
        for kind in ("deployments", "statefulsets"):
            with self.subTest(kind=kind):
                documents = self.documents(self.render(kind, [
                    workload(kind, "first"), workload(kind, "second"),
                ]))
                self.assertEqual(set(documents), {"first", "second"})
                for document in documents.values():
                    self.assertEqual(self.volumes(document)[0], ["shared-config"])

    def test_statefulset_legacy_and_extra_volume_sources_share_the_ledger(self):
        item = workload("statefulsets", source="persistentVolumeClaim")
        for container in item["containers"]:
            container["mountConfigMaps"] = [{"name": "settings", "mountPath": "/settings"}]
            container["mountSecrets"] = [{"name": "credentials", "mountPath": "/credentials"}]
            container["extraVolumes"].extend([
                {"configMap": "settings", "mountPath": "/other-settings"},
                {"secretName": "credentials", "mountPath": "/other-credentials"},
            ])
        item["persistence"]["extraVolumes"] = [{"persistentVolumeClaim": "shared-config"}]
        document = self.documents(self.render("statefulsets", [item]))["test-node"]
        names, block = self.volumes(document)
        self.assertEqual(set(names), {"settings", "credentials", "shared-config"})
        self.assertEqual(len(names), 3)
        self.assertIn("            optional: false", block)

    def test_conflicting_source_kinds_fail_instead_of_choosing_one(self):
        for kind in ("deployments", "statefulsets"):
            with self.subTest(kind=kind):
                item = workload(kind)
                item["containers"][1]["extraVolumes"] = [
                    {"configMap": "shared-config", "mountPath": "/config"},
                ]
                result = self.render(kind, [item])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("conflicting volume sources for shared-config", result.stderr)


if __name__ == "__main__":
    unittest.main()
