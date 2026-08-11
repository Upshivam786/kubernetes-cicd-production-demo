# Kubernetes CI/CD Production Demo

A production-style DevOps demonstration project implementing an end-to-end **CI/CD, containerization, Kubernetes deployment, and observability workflow** for a FastAPI application.

The project demonstrates how a code change moves from GitHub through automated testing and container image publishing into a Kubernetes cluster, followed by deployment verification and Prometheus-based application monitoring.

---

## Overview

This project was built to demonstrate practical DevOps engineering capabilities around:

* Python/FastAPI application deployment
* Docker containerization
* GitHub Actions CI/CD
* GitHub Container Registry (GHCR)
* Self-hosted GitHub Actions runner
* Kubernetes deployment
* Kubernetes health and readiness probes
* Private container registry authentication
* Rolling deployments
* Deployment verification and smoke testing
* Prometheus application metrics
* Prometheus Operator
* Kubernetes `ServiceMonitor`
* Grafana/Alertmanager monitoring stack
* Infrastructure configuration through YAML
* Troubleshooting and production-style operational practices

The application itself is intentionally simple. The main focus of this repository is the **engineering platform around the application**.

---

# Architecture

```text
                         Developer
                             │
                             │ git push
                             ▼
                    ┌─────────────────┐
                    │     GitHub      │
                    │   Repository    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ GitHub Actions  │
                    │                 │
                    │ 1. Run tests    │
                    │ 2. Build image  │
                    │ 3. Push image   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │      GHCR       │
                    │ GitHub Container │
                    │    Registry     │
                    └────────┬────────┘
                             │
                             │ image pull
                             ▼
             ┌──────────────────────────────┐
             │       Kubernetes / Kind      │
             │                              │
             │  ┌────────────────────────┐  │
             │  │ Backend Deployment      │  │
             │  │                        │  │
             │  │  ┌───────┐ ┌───────┐  │  │
             │  │  │ Pod 1 │ │ Pod 2 │  │  │
             │  │  └───┬───┘ └───┬───┘  │  │
             │  └──────┼──────────┼──────┘  │
             │         │          │         │
             │         └────┬─────┘         │
             │              ▼               │
             │        ClusterIP Service     │
             │              │               │
             │              ▼               │
             │          PostgreSQL          │
             └──────────────────────────────┘
                             │
                             │ /metrics
                             ▼
                    ┌─────────────────┐
                    │ ServiceMonitor  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Prometheus   │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
               Grafana           Alertmanager
```

---

# Technology Stack

| Area                    | Technology                        |
| ----------------------- | --------------------------------- |
| Application             | Python, FastAPI                   |
| Database                | PostgreSQL                        |
| ORM                     | SQLAlchemy                        |
| Testing                 | pytest, TestClient                |
| Containerization        | Docker                            |
| Container Registry      | GitHub Container Registry         |
| CI/CD                   | GitHub Actions                    |
| CI Runner               | Self-hosted GitHub Actions runner |
| Orchestration           | Kubernetes                        |
| Local Kubernetes        | Kind                              |
| Packaging               | Helm                              |
| Metrics                 | Prometheus                        |
| Metrics instrumentation | prometheus-fastapi-instrumentator |
| Kubernetes monitoring   | Prometheus Operator               |
| Service discovery       | ServiceMonitor                    |
| Visualization           | Grafana                           |
| Alerting                | Alertmanager                      |
| Configuration           | YAML                              |

---

# Repository Structure

```text
kubernetes-cicd-production-demo/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   └── requirements.txt
│
├── tests/
│   └── test_health.py
│
├── k8s/
│   ├── backend.yaml
│   └── monitoring/
│       ├── backend-servicemonitor.yaml
│       └── prometheus-values.yaml
│
├── .github/
│   └── workflows/
│       └── ci.yaml
│
├── Dockerfile
├── pytest.ini
└── README.md
```

---

# Application

The application is a small FastAPI service backed by PostgreSQL.

It exposes the following endpoints.

| Endpoint   | Method | Purpose                    |
| ---------- | ------ | -------------------------- |
| `/healthz` | GET    | Kubernetes liveness check  |
| `/readyz`  | GET    | Kubernetes readiness check |
| `/items`   | GET    | Retrieve database items    |
| `/items`   | POST   | Create an item             |
| `/metrics` | GET    | Prometheus metrics         |

The application also exposes HTTP request metrics through `prometheus-fastapi-instrumentator`.

Example:

```text
http_requests_total
```

This allows Prometheus to observe application traffic and response status.

---

# Health and Readiness

Two separate Kubernetes probes are implemented.

## Liveness

```text
GET /healthz
```

Response:

```json
{
  "status": "ok"
}
```

The liveness probe answers:

> Is the application process alive?

---

## Readiness

```text
GET /readyz
```

Response when the database is reachable:

```json
{
  "status": "ready"
}
```

The readiness endpoint performs a database connectivity check.

The readiness probe answers:

> Is this application instance ready to receive traffic?

This distinction allows Kubernetes to remove an unhealthy instance from Service traffic without necessarily restarting it.

---

# Docker

The application is packaged as a Docker image.

Images are published to:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo
```

Two tags are produced by CI/CD:

```text
:<commit-sha>
:latest
```

The commit SHA tag provides an immutable deployment reference.

For example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8ed2333bfeb03a55c7130bb5061580619d
```

Using the commit SHA rather than relying only on `latest` makes deployments traceable to a specific Git revision.

---

# GitHub Actions CI/CD

The workflow is located at:

```text
.github/workflows/ci.yaml
```

The pipeline contains three major jobs.

```text
test
  │
  ▼
build-and-push
  │
  ▼
deploy
```

---

## 1. Test

The test job:

1. Checks out the repository
2. Installs Python 3.12
3. Installs application dependencies
4. Installs testing dependencies
5. Runs pytest

Example:

```bash
pytest -q
```

The pipeline must pass the test stage before an image is built.

---

## 2. Build and Push

After tests pass, the workflow:

1. Checks out the repository
2. Authenticates to GHCR
3. Builds the Docker image
4. Pushes the image to GHCR

Images are tagged using both:

```text
${{ github.sha }}
latest
```

The GitHub Actions `GITHUB_TOKEN` is used for registry authentication.

---

# Self-Hosted GitHub Actions Runner

The Kubernetes deployment job uses a self-hosted runner:

```yaml
runs-on: self-hosted
```

The runner is installed on the machine that has access to the Kind Kubernetes cluster.

The runner allows the GitHub Actions deployment stage to execute:

```bash
kubectl
```

against the local Kubernetes cluster.

The deployment flow is therefore:

```text
GitHub Actions
      │
      ▼
Self-hosted runner
      │
      ▼
kubectl
      │
      ▼
Kind Kubernetes cluster
```

This is useful for demonstrating a deployment model where the CI system does not require direct public access to the Kubernetes API.

---

# Kubernetes

The application is deployed into the:

```text
fluid-ai
```

namespace.

The backend deployment runs two replicas:

```yaml
replicas: 2
```

This provides basic application redundancy.

The deployment includes:

* Container resource requests
* Container resource limits
* Liveness probe
* Readiness probe
* Private registry authentication
* Rolling update behavior

---

# Kubernetes Service

The backend is exposed internally through a `ClusterIP` Service.

```yaml
ports:
  - name: http
    port: 8000
    targetPort: 8000
```

The named port is important because the Prometheus `ServiceMonitor` references the port by name:

```yaml
port: http
```

The Service selects backend Pods using:

```yaml
selector:
  app: backend
```

---

# Private GHCR Authentication

The container image is stored in GitHub Container Registry.

Because the package is private, Kubernetes requires registry credentials to pull the image.

A Kubernetes Docker registry secret is created:

```text
ghcr-pull-secret
```

The Deployment references it using:

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```

This allows Kubernetes to pull private images from GHCR.

> Never commit registry tokens, passwords, or other credentials to the repository.

---

# Deployment Strategy

The GitHub Actions deployment stage updates the backend image using the commit SHA:

```bash
kubectl -n fluid-ai set image deployment/backend \
  backend=${IMAGE_NAME}:${GITHUB_SHA}
```

Kubernetes then performs a rolling update.

The workflow waits for:

```bash
kubectl -n fluid-ai rollout status deployment/backend
```

The deployment is considered successful only after the rollout completes.

The workflow also verifies the deployed image.

---

# Deployment Verification

The pipeline verifies:

### Kubernetes access

```bash
kubectl cluster-info
kubectl get nodes
```

### Deployment rollout

```bash
kubectl rollout status deployment/backend
```

### Running Pods

```bash
kubectl get pods -n fluid-ai -l app=backend
```

### Deployed image

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### Application smoke test

The deployment workflow performs an HTTP health check through Kubernetes port forwarding.

This ensures the deployment is not considered successful simply because Kubernetes created the Pods.

---

# Rollback

Kubernetes maintains Deployment revision history.

The deployment history can be inspected with:

```bash
kubectl rollout history deployment/backend -n fluid-ai
```

A previous revision can be rolled back using:

```bash
kubectl rollout undo deployment/backend -n fluid-ai
```

The rollout can then be verified using:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

---

# Observability

The application exposes Prometheus metrics through:

```text
/metrics
```

Instrumentation is provided by:

```text
prometheus-fastapi-instrumentator
```

Example metric:

```text
http_requests_total
```

The metric contains useful labels such as:

```text
handler
method
status
pod
namespace
service
```

This allows application behavior to be queried at both service and Pod level.

---

# Prometheus Operator

The Kubernetes monitoring stack is based on:

```text
kube-prometheus-stack
```

The stack provides the Kubernetes monitoring components and Prometheus Operator resources.

The installation includes Kubernetes Custom Resource Definitions (CRDs) such as:

```text
Prometheus
Alertmanager
ServiceMonitor
PrometheusRule
PodMonitor
```

These extend the Kubernetes API with monitoring-specific resources.

---

# ServiceMonitor

The backend is discovered by Prometheus through:

```text
k8s/monitoring/backend-servicemonitor.yaml
```

The ServiceMonitor selects:

```yaml
selector:
  matchLabels:
    app: backend
```

and targets the Service port:

```yaml
endpoints:
  - port: http
    path: /metrics
    interval: 15s
```

The target namespace is:

```text
fluid-ai
```

The monitoring flow is:

```text
FastAPI
   │
   │ /metrics
   ▼
backend Service
   │
   ▼
ServiceMonitor
   │
   ▼
Prometheus
```

---

# Prometheus Verification

Prometheus was verified using the `up` metric.

Example query:

```promql
up{job="backend"}
```

The backend returned:

```text
instance="10.244.0.31:8000" → 1
instance="10.244.0.32:8000" → 1
```

A value of:

```text
1
```

means Prometheus successfully scraped the target.

Application request metrics were also verified:

```promql
http_requests_total
```

The result included metrics for:

```text
/healthz
/readyz
/metrics
```

for both backend replicas.

This confirms that application-level metrics are successfully flowing into Prometheus.

---

# Monitoring Stack

The monitoring namespace contains:

```text
Prometheus
Grafana
Alertmanager
Prometheus Operator
kube-state-metrics
node-exporter
```

The monitoring components are deployed in:

```text
monitoring
```

namespace.

The architecture is:

```text
Kubernetes
    │
    ├── kube-state-metrics
    ├── node-exporter
    │
    ▼
Prometheus
    │
    ├── application metrics
    ├── Kubernetes metrics
    └── infrastructure metrics
          │
          ▼
       Grafana
```

---

# Local Development

## Prerequisites

Install:

* Git
* Python
* Docker
* kubectl
* Kind
* Helm

Verify:

```bash
python --version
docker --version
kubectl version --client
kind version
helm version
```

---

# Clone Repository

```bash
git clone https://github.com/Upshivam786/kubernetes-cicd-production-demo.git
cd kubernetes-cicd-production-demo
```

---

# Python Environment

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r app/requirements.txt
```

---

# Run Tests Locally

Run:

```bash
pytest -q
```

The test suite verifies the application's health endpoint and Prometheus metrics endpoint.

---

# Run Application Locally

The application requires PostgreSQL configuration.

Example:

```bash
DB_HOST=127.0.0.1 \
DB_PORT=5432 \
DB_NAME=appdb \
DB_USER=appuser \
DB_PASSWORD='appsecret' \
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then verify:

```bash
curl http://127.0.0.1:8000/healthz
```

```bash
curl http://127.0.0.1:8000/readyz
```

```bash
curl http://127.0.0.1:8000/items
```

```bash
curl http://127.0.0.1:8000/metrics
```

---

# Kubernetes Deployment

Create the Kind cluster:

```bash
kind create cluster --name fluid-ai
```

Verify:

```bash
kubectl get nodes
```

Expected:

```text
fluid-ai-control-plane   Ready
```

Create the namespace:

```bash
kubectl create namespace fluid-ai
```

Create the required PostgreSQL secret:

```bash
kubectl create secret generic backend-db \
  -n fluid-ai \
  --from-literal=DB_NAME=appdb \
  --from-literal=DB_USER=appuser \
  --from-literal=DB_PASSWORD='appsecret'
```

Create the GHCR pull secret:

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --namespace fluid-ai \
  --docker-server=ghcr.io \
  --docker-username=<GITHUB_USERNAME> \
  --docker-password='<GITHUB_TOKEN>'
```

Apply the backend resources:

```bash
kubectl apply -f k8s/backend.yaml
```

Verify:

```bash
kubectl get pods -n fluid-ai
```

```bash
kubectl get deployment backend -n fluid-ai
```

```bash
kubectl get service backend -n fluid-ai
```

---

# Monitoring Installation

Create the monitoring namespace:

```bash
kubectl create namespace monitoring
```

Install the kube-prometheus-stack:

```bash
helm upgrade --install monitoring-crds \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values k8s/monitoring/prometheus-values.yaml
```

Verify:

```bash
kubectl get pods -n monitoring
```

Install/apply the backend ServiceMonitor:

```bash
kubectl apply \
  -f k8s/monitoring/backend-servicemonitor.yaml
```

Verify:

```bash
kubectl get servicemonitor -n monitoring
```

---

# Access Prometheus Locally

Prometheus can be accessed through port forwarding:

```bash
kubectl port-forward \
  -n monitoring \
  service/monitoring-crds-kube-prome-prometheus \
  9090:9090
```

Then open:

```text
http://127.0.0.1:9090
```

Example PromQL query:

```promql
up{job="backend"}
```

Application request metrics:

```promql
http_requests_total
```

---

# Access Grafana Locally

Find the Grafana Pod:

```bash
kubectl get pods -n monitoring
```

Port forward Grafana:

```bash
kubectl port-forward \
  -n monitoring \
  service/monitoring-crds-grafana \
  3000:80
```

Then open:

```text
http://127.0.0.1:3000
```

---

# CI/CD Workflow

The complete deployment lifecycle is:

```text
Developer
    │
    │ git push
    ▼
GitHub
    │
    ▼
GitHub Actions
    │
    ├── pytest
    │
    ├── Docker build
    │
    ├── Push to GHCR
    │
    └── Self-hosted runner
             │
             ▼
          kubectl
             │
             ▼
      Kubernetes Deployment
             │
             ▼
       Rolling Update
             │
             ▼
       Health Verification
             │
             ▼
          Smoke Test
```

---

# Security Considerations

The project follows several basic security practices:

* Container images are pulled from a private registry using a Kubernetes registry secret.
* Registry credentials are not stored in source code.
* GitHub Actions uses `GITHUB_TOKEN` for GHCR publishing.
* Kubernetes Secrets are used for database credentials.
* Deployment uses immutable Git commit SHA image tags.
* Kubernetes resources use explicit namespaces.
* Resource requests and limits are configured for the backend.
* Health and readiness checks prevent unhealthy instances from receiving traffic.

For a real production environment, additional controls should be considered, including:

* External secret management
* Workload identity
* Network policies
* RBAC hardening
* Container image signing
* Vulnerability scanning
* Pod Security Standards
* TLS
* Ingress
* Centralized logging
* Backup and disaster recovery

---

# Troubleshooting

## GHCR image pull denied

If:

```bash
docker pull ghcr.io/upshivam786/kubernetes-cicd-production-demo:latest
```

returns:

```text
denied
```

verify that the package is private and authenticate with GHCR.

For Kubernetes, verify:

```bash
kubectl get secret ghcr-pull-secret -n fluid-ai
```

and:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.imagePullSecrets}{"\n"}'
```

---

## Kubernetes Pod stuck in ImagePullBackOff

Check:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Common causes:

* Missing `imagePullSecrets`
* Invalid GitHub token
* Incorrect image name
* Package permissions
* Image tag does not exist

---

## Deployment does not roll out

Check:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Then:

```bash
kubectl get pods -n fluid-ai
```

and:

```bash
kubectl describe deployment backend -n fluid-ai
```

---

## Readiness probe failing

Check:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Then inspect application logs:

```bash
kubectl logs <pod-name> -n fluid-ai
```

The `/readyz` endpoint performs a database connectivity check, so PostgreSQL availability should also be verified.

---

## Prometheus does not show application metrics

Verify that the application exposes:

```text
/metrics
```

Then verify the Service has the expected port:

```bash
kubectl get svc backend -n fluid-ai -o yaml
```

The Service should contain:

```yaml
ports:
  - name: http
    port: 8000
    targetPort: 8000
```

Verify the ServiceMonitor:

```bash
kubectl get servicemonitor fluid-ai-backend -n monitoring -o yaml
```

Then query Prometheus:

```promql
up{job="backend"}
```

A value of `1` indicates a successful scrape.

---

# Useful Kubernetes Commands

## Pods

```bash
kubectl get pods -n fluid-ai
```

## Deployment

```bash
kubectl get deployment backend -n fluid-ai
```

## Services

```bash
kubectl get svc -n fluid-ai
```

## Logs

```bash
kubectl logs deployment/backend -n fluid-ai
```

## Rollout status

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

## Rollout history

```bash
kubectl rollout history deployment/backend -n fluid-ai
```

## Rollback

```bash
kubectl rollout undo deployment/backend -n fluid-ai
```

## Monitoring resources

```bash
kubectl get pods -n monitoring
```

```bash
kubectl get servicemonitor -n monitoring
```

```bash
kubectl get prometheus -n monitoring
```

```bash
kubectl get alertmanager -n monitoring
```

---

# Verification Checklist

A successful deployment should satisfy the following:

```text
[ ] GitHub Actions test job passes
[ ] Docker image successfully builds
[ ] Image is pushed to GHCR
[ ] Self-hosted runner receives deployment job
[ ] Kubernetes deployment is updated
[ ] Two backend replicas are running
[ ] Liveness probe passes
[ ] Readiness probe passes
[ ] Backend Service is available
[ ] Application responds to /healthz
[ ] Application responds to /readyz
[ ] Application responds to /items
[ ] Application exposes /metrics
[ ] ServiceMonitor exists
[ ] Prometheus discovers backend
[ ] up{job="backend"} == 1
[ ] http_requests_total is available
[ ] Grafana is running
[ ] Alertmanager is running
```

---

# Design Decisions

## Why use commit SHA image tags?

Using the Git commit SHA makes every deployed container traceable to a specific source revision.

Instead of:

```text
latest
```

the deployment can reference:

```text
:<git-sha>
```

This improves reproducibility and makes rollback and debugging easier.

---

## Why use a self-hosted runner?

The Kubernetes cluster is a local Kind cluster.

A self-hosted runner provides a controlled execution environment that can access the cluster's Kubernetes API and execute:

```bash
kubectl
```

without exposing the local Kubernetes API publicly.

---

## Why use a ServiceMonitor?

The ServiceMonitor provides Kubernetes-native monitoring configuration.

Instead of manually configuring Prometheus targets, Prometheus Operator discovers the monitoring configuration from Kubernetes resources.

This scales better as services are added.

---

# Current Capabilities

The project currently demonstrates:

```text
Application
    ↓
Docker
    ↓
GitHub Actions
    ↓
GHCR
    ↓
Self-hosted Runner
    ↓
Kubernetes
    ↓
Health / Readiness
    ↓
Prometheus
    ↓
ServiceMonitor
    ↓
Grafana / Alertmanager
```

The result is a reproducible DevOps workflow covering application delivery, deployment automation, Kubernetes orchestration, and observability.

---

# Future Improvements

Possible next steps include:

* Production Grafana dashboards
* Prometheus alert rules
* SLO/SLI definitions
* Ingress and TLS
* NetworkPolicies
* Horizontal Pod Autoscaling
* PodDisruptionBudget
* Resource-based autoscaling
* Container vulnerability scanning
* Image signing
* SBOM generation
* GitHub Actions security hardening
* External secret management
* Centralized logging
* Distributed tracing
* GitOps deployment using Argo CD
* Environment separation for development/staging/production

---

# Author

**Shivam Upadhyay**

This project demonstrates practical experience across:

* DevOps
* Kubernetes
* CI/CD
* Cloud-native infrastructure
* Containerization
* Observability
* MLOps/AI infrastructure

The architecture is intentionally designed to demonstrate how modern application delivery and operational practices can be applied to an AI/ML-oriented engineering environment.
