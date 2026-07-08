# universal-helm

A generic Helm chart for deploying arbitrary Kubernetes workloads (StatefulSets,
Deployments, and CronJobs) that share a common configuration — service account,
image pull secrets, pod annotations, security context, update strategy, etc.

It is used by the other charts in this repository (e.g. the Ethereum node charts)
as a reusable base, but can also be installed standalone to deploy custom
workloads without writing a dedicated chart from scratch.

## Features

- Deploys `StatefulSet`, `Deployment`, and `CronJob` resources from a single
  values file.
- Shared `global` configuration applied across all workloads:
  service account (with optional annotations, e.g. for IRSA), pod annotations,
  image pull policy/secrets, update strategy, and security context.
- Optional Emissary ingress support.
- `additionalManifests` / `additionalYamlManifests` for arbitrary extra resources
  (ConfigMaps, Secrets, etc.) deployed alongside the release.

## Installation

```bash
helm install my-release ./charts/universal-helm \
  -f charts/universal-helm/examples/example-values3.yaml
```

## Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `statefulsets` | list | `[]` | List of StatefulSet specs to deploy. |
| `deployments` | list | `[]` | List of Deployment specs to deploy. |
| `cronjobs` | list | `[]` | List of CronJob specs to deploy. |
| `global.serviceAccount.create` | bool | `true` | Create a service account for the release. |
| `global.serviceAccount.name` | string | `""` | Service account name; generated from the chart name when unset. |
| `global.serviceAccount.annotations` | map | `{}` | Annotations for the service account (e.g. IRSA role ARN). |
| `global.podAnnotations` | map | `{}` | Annotations applied to every pod. |
| `global.nameOverride` | string | `""` | Override the chart name. |
| `global.fullnameOverride` | string | `""` | Override the fully qualified app name. |
| `global.imagePullPolicy` | string | `IfNotPresent` | Default image pull policy. |
| `global.imagePullSecrets` | list | `[]` | Image pull secrets for private registries. |
| `global.updateStrategy` | string | `RollingUpdate` | Default workload update strategy. |
| `global.securityContext` | map | `{}` | Pod security context. |
| `additionalManifests` | list | `[]` | Extra manifests as a list of objects. |
| `additionalYamlManifests` | string | `""` | Extra manifests as a raw YAML string. |

See [`examples/example-values3.yaml`](./examples/example-values3.yaml) for a
complete real-world example deploying a Reth + Nimbus Ethereum node.

# Changelog

## 0.7.2
  Breaking changes - NO.

Changes:
- Initial ReadMe.
