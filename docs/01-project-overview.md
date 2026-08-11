# Fluid AI DevOps Challenge — Project Overview

## 1. Project Purpose

This project demonstrates a production-style deployment workflow for a Python FastAPI application running on Kubernetes.

The primary objective is to demonstrate practical DevOps engineering capabilities across:

* Application containerization
* Kubernetes deployment and service management
* Private container image management with GitHub Container Registry (GHCR)
* GitHub Actions CI/CD
* Self-hosted GitHub Actions runners
* Automated Kubernetes deployments
* Deployment verification and rollback
* Application health and readiness checks
* Prometheus-based application monitoring
* Grafana-based visualization
* Kubernetes monitoring using the Prometheus Operator
* ServiceMonitor-based metrics discovery
* Troubleshooting and operational practices

The project is intentionally designed as a small application so that the infrastructure, deployment, CI/CD, observability, and operational practices remain easy to understand.

---

## 2. Application

The application is a Python FastAPI service backed by PostgreSQL.

The API provides:

* Health endpoint
* Readiness endpoint
* Prometheus metrics endpoint
* Item listing endpoint
* Item creation endpoint

### Application endpoints

| Endpoint   | Method | Purpose                                                    |
| ---------- | ------ | ---------------------------------------------------------- |
| `/healthz` | GET    | Kubernetes liveness/health check                           |
| `/readyz`  | GET    | Kubernetes readiness check including database connectivity |
| `/metrics` | GET    | Prometheus metrics                                         |
| `/items`   | GET    | Retrieve application items                                 |
| `/items`   | POST   | Create an application item                                 |

The application uses SQLAlchemy for database access and PostgreSQL as the persistent database.

---

## 3. Technology Stack

### Application

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Uvicorn
* Prometheus FastAPI Instrumentator
* Pytest

### Containerization

* Docker
* GitHub Container Registry (GHCR)

### CI/CD

* GitHub Actions
* Self-hosted GitHub Actions runner
* Docker Buildx / Docker Build Push Action
* Kubernetes CLI (`kubectl`)

### Kubernetes

* Kubernetes
* Kind
* Deployment
* Service
* Secrets
* Configured resource requests and limits
* Liveness probes
* Readiness probes
* Rolling deployments
* Rollout history
* Rollback capability

### Observability

* Prometheus
* Grafana
* Alertmanager
* Prometheus Operator
* kube-state-metrics
* Node Exporter
* ServiceMonitor
* Prometheus metrics

### Package Management

* Helm
* kube-prometheus-stack

---

## 4. High-Level Architecture

The project follows this deployment flow:

```text
Developer
    |
    | git push
    v
GitHub Repository
    |
    v
GitHub Actions
    |
    +----------------------+
    |                      |
    v                      v
Test Application      Build Docker Image
                           |
                           v
                    GitHub Container Registry
                           |
                           v
                    Self-hosted Runner
                           |
                           v
                       Kubernetes
                           |
                 +---------+---------+
                 |                   |
                 v                   v
          FastAPI Backend        PostgreSQL
                 |
                 v
             /metrics
                 |
                 v
             Prometheus
                 |
                 v
              Grafana
```

---

## 5. CI/CD Workflow

The CI/CD pipeline is divided into three major stages.

### Stage 1 — Test

GitHub Actions:

1. Checks out the repository.
2. Installs Python.
3. Installs application dependencies.
4. Runs the Pytest test suite.

The build stage depends on successful completion of the test stage.

```text
git push
   |
   v
Test
   |
   +---- failure ---> Pipeline stops
   |
   v
Build
```

---

### Stage 2 — Build and Push

After tests pass:

1. Docker image is built.
2. GitHub Container Registry authentication is performed.
3. The image is pushed to GHCR.

Two tags are generated:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:<git-sha>

ghcr.io/upshivam786/kubernetes-cicd-production-demo:latest
```

The Git commit SHA provides an immutable deployment reference.

For example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8ed2333bfeb03a55c7130bb5061580619d
```

---

### Stage 3 — Deploy

The deployment job runs on the self-hosted GitHub Actions runner.

The runner has access to the Kubernetes cluster and executes:

```bash
kubectl set image deployment/backend ...
```

The deployment then waits for a successful Kubernetes rollout.

The pipeline also verifies that the expected image is actually running.

Finally, a smoke test verifies application availability.

The resulting flow is:

```text
Test
  |
  v
Build Docker Image
  |
  v
Push to GHCR
  |
  v
Update Kubernetes Deployment
  |
  v
Rolling Update
  |
  v
Rollout Verification
  |
  v
Smoke Test
```

---

## 6. Kubernetes Environment

The application runs in the `fluid-ai` namespace.

The main Kubernetes resources are:

```text
Namespace: fluid-ai

Deployment:
    backend

Service:
    backend

Database:
    postgres

Secrets:
    backend-db
    ghcr-pull-secret
```

The backend deployment runs two replicas:

```text
backend
├── Pod 1
└── Pod 2
```

This provides basic availability during normal rolling deployments.

---

## 7. Container Registry

The Docker image is stored in GitHub Container Registry:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo
```

The repository is configured to use a private GHCR image.

Kubernetes authenticates to GHCR using:

```text
ghcr-pull-secret
```

The secret is referenced through the deployment's `imagePullSecrets`.

This separates registry authentication from the application container itself.

---

## 8. Health and Readiness

The Kubernetes Deployment uses two HTTP probes.

### Liveness

```text
GET /healthz
```

Purpose:

Determine whether the application process is alive.

A successful response:

```json
{
  "status": "ok"
}
```

### Readiness

```text
GET /readyz
```

Purpose:

Determine whether the application is ready to receive traffic.

The readiness check also verifies database connectivity.

A successful response:

```json
{
  "status": "ready"
}
```

This allows Kubernetes to distinguish between:

```text
Application process is running
```

and:

```text
Application is ready to serve requests
```

---

## 9. Observability

The application exposes Prometheus-compatible metrics at:

```text
/metrics
```

The application uses:

```text
prometheus-fastapi-instrumentator
```

to automatically expose application metrics.

Example metric:

```text
http_requests_total
```

The metric contains labels such as:

```text
method
handler
status
pod
namespace
service
```

This allows Prometheus to answer questions such as:

* Is the application up?
* How many requests are being served?
* Which endpoints are receiving traffic?
* What is the request status distribution?
* Which backend pod is serving traffic?

---

## 10. Prometheus Operator

Monitoring is deployed using the `kube-prometheus-stack` Helm chart.

The stack provides components including:

* Prometheus Operator
* Prometheus
* Grafana
* Alertmanager
* kube-state-metrics
* Node Exporter

The project also uses Kubernetes custom resources provided by the Prometheus Operator.

Important resources include:

```text
Prometheus
Alertmanager
ServiceMonitor
PrometheusRule
```

These resources extend the Kubernetes API and allow monitoring configuration to be represented as Kubernetes resources.

---

## 11. ServiceMonitor

The backend is monitored through a custom `ServiceMonitor`:

```text
fluid-ai-backend
```

The ServiceMonitor:

* Searches for the backend Service in the `fluid-ai` namespace.
* Selects the Service using the `app=backend` label.
* Uses the Service port named `http`.
* Scrapes `/metrics`.
* Scrapes every 15 seconds.

Conceptually:

```text
ServiceMonitor
      |
      | selects app=backend
      v
Kubernetes Service
      |
      v
Backend Pods
      |
      | GET /metrics
      v
Prometheus
```

Prometheus ultimately exposes metrics such as:

```text
up{job="backend"}
```

and:

```text
http_requests_total
```

---

## 12. Deployment Strategy

The backend uses a Kubernetes Deployment with two replicas.

Deployments provide controlled rolling updates.

When a new image is deployed:

```text
Old Replica 1
Old Replica 2
       |
       v
New Replica 1
New Replica 2
```

Kubernetes gradually replaces the old Pods while maintaining application availability.

The deployment history can be inspected using:

```bash
kubectl rollout history deployment/backend -n fluid-ai
```

A previous revision can be restored using:

```bash
kubectl rollout undo deployment/backend -n fluid-ai
```

---

## 13. Verification Strategy

The project does not consider a deployment successful merely because the Kubernetes command completed.

Verification happens at multiple levels.

### Kubernetes verification

```bash
kubectl get deployment backend -n fluid-ai
```

### Pod verification

```bash
kubectl get pods -n fluid-ai -l app=backend
```

### Rollout verification

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

### Image verification

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

### Health verification

```bash
curl http://127.0.0.1:<port>/healthz
```

### Readiness verification

```bash
curl http://127.0.0.1:<port>/readyz
```

### Metrics verification

```bash
curl http://127.0.0.1:<port>/metrics
```

### Prometheus verification

Example:

```promql
up{job="backend"}
```

and:

```promql
http_requests_total
```

---

## 14. Production-Oriented Practices Demonstrated

Although this is a compact demonstration project, it incorporates several practices used in production environments:

* Immutable image tags using Git commit SHA
* Private container registry authentication
* Kubernetes Secrets
* Resource requests and limits
* Liveness and readiness probes
* Multiple application replicas
* Rolling deployments
* Automated rollout verification
* Deployment smoke testing
* Rollback capability
* CI/CD dependency ordering
* Self-hosted runner deployment
* Prometheus metrics
* Kubernetes-native monitoring configuration
* Service discovery through ServiceMonitor
* Operational troubleshooting documentation

---

## 15. Project Documentation

Detailed implementation and operational information is documented under:

```text
docs/
```

The documentation is organized by lifecycle:

```text
Project Understanding
        ↓
Architecture
        ↓
Local Setup
        ↓
Kubernetes Setup
        ↓
CI/CD
        ↓
Container Registry
        ↓
Observability
        ↓
Operations
        ↓
Troubleshooting
        ↓
Security
        ↓
Assignment Mapping
```

This structure is intended to make the project understandable both to a developer setting it up for the first time and to a DevOps engineer operating the environment.

---

## 16. Repository Structure

The important project directories are:

```text
fluid-ai-devops-challenge/
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
├── README.md
└── docs/
```

---

## 17. Engineering Goal

The goal of the project is not simply to deploy a FastAPI application.

The project demonstrates the complete path from source code to an observable Kubernetes workload:

```text
Code
 ↓
Tests
 ↓
Docker Image
 ↓
GHCR
 ↓
CI/CD
 ↓
Kubernetes
 ↓
Health Checks
 ↓
Metrics
 ↓
Prometheus
 ↓
Grafana
 ↓
Operations & Troubleshooting
```

This provides a practical demonstration of DevOps engineering principles combined with cloud-native application deployment and observability.
