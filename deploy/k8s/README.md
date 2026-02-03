# Kubernetes Deployment

Helm charts and K3s manifests for Aegis Mesh will be added in a future phase.

## Planned Structure

```
/k8s
├── charts/
│   └── aegis-mesh/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── manifests/
│   ├── namespace.yaml
│   ├── core-deployment.yaml
│   ├── mesh-bridge-deployment.yaml
│   └── ...
└── README.md
```

## Prerequisites

- K3s or Kubernetes cluster
- kubectl configured
- Helm 3.x (for chart deployment)

## Quick Start (Coming Soon)

```bash
# Using Helm
helm install aegis-mesh ./charts/aegis-mesh

# Using manifests directly
kubectl apply -f manifests/
```
