# Changelog

## 0.0.65
  Breaking changes - NO.

Changes:
- Add smarter logic to remove volume snapshot from previous failed backup job.

## 0.0.64
  Breaking changes - NO.

Changes:
- Don't specify p2p NLB name with annotation `service.beta.kubernetes.io/aws-load-balancer-name:`, so the name will be generated automatically. This is due to it is very hard to generate a unique service name, when have 2 clusters of the same environment in the same region.

## 0.0.63
  Breaking changes - NO.

Changes:
- Comment out default readiness-probe container env vars

## 0.0.60
  Breaking changes - NO.

Changes:
- Set CPU/RAM limits on backup job pod, to decrease "noisy neighbour" impact.

## 0.0.58
  Breaking changes - NO.

Changes:
- Add readiness probe sidecar, so STS's pods will wait when each upgraded pod become ready, before upgrading the next one.
