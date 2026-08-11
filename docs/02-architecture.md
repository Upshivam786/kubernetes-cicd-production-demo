# Fluid AI DevOps Challenge — Architecture

## 1. Architecture Overview

The project implements a small but production-oriented cloud-native deployment architecture.

The application is a FastAPI service backed by PostgreSQL and deployed to Kubernetes. GitHub Actions provides the CI/CD pipeline, GitHub Container Registry stores application images, and a self-hosted GitHub Actions runner performs the Kubernetes deployment.

Observability is implemented using the Prometheus Operator stack with Prometheus, Grafana, Alertmanager, kube-state-metrics, Node Exporter, and a custom ServiceMonitor for the backend application.

The complete architecture can be viewed as several connected layers:

```text
┌──────────────────────────────────────────────────────────────┐
│                         Developer                            │
│                                                              │
│                     git push / PR                            │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                         GitHub                                │
│                                                              │
│  Repository                  GitHub Actions                   │
│  ├── Application             ├── Test                         │
│  ├── Dockerfile              ├── Build                        │
│  ├── Kubernetes manifests    ├── Push                         │
│  └── Tests                   └── Deploy                       │
└──────────────────────┬───────────────────────┬───────────────┘
                       │                       │
                       │                       │
                       ▼                       ▼
             ┌─────────────────┐     ┌──────────────────────┐
             │      GHCR        │     │ Self-hosted Runner   │
             │                 │     │                      │
             │ Docker Images   │     │ kubectl + Kubernetes │
             └────────┬────────┘     └──────────┬───────────┘
                      │                         │
                      │                         │
                      └────────────┬────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                     Kubernetes / Kind                        │
│                                                              │
│  Namespace: fluid-ai                                         │
│                                                              │
│  ┌─────────────────────┐      ┌─────────────────────────┐    │
│  │ Backend Service     │─────▶│ Backend Deployment      │    │
│  │ ClusterIP :8000     │      │                         │    │
│  │                     │      │ ┌─────────┐ ┌─────────┐ │    │
│  │ app=backend         │      │ │ Pod #1  │ │ Pod #2  │ │    │
│  └─────────────────────┘      │ └─────────┘ └─────────┘ │    │
│                               └────────────┬────────────┘    │
│                                            │                 │
│                                            ▼                 │
│                               ┌────────────────────────┐    │
│                               │ PostgreSQL              │    │
│                               │ Service + Pod            │    │
│                               └────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘

                         Monitoring
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                     monitoring namespace                     │
│                                                              │
│  ServiceMonitor → Prometheus → Grafana                       │
│                         │                                    │
│                         └──────────▶ Alertmanager             │
│                                                              │
│  kube-state-metrics                                         │
│  Node Exporter                                               │
│  Prometheus Operator                                         │
└──────────────────────────────────────────────────────────────┘
```

---

# 2. Component Architecture

## 2.1 Developer

The development workflow starts with changes made to the Git repository.

The developer can:

```text
Modify code
   ↓
Run tests locally
   ↓
Commit
   ↓
git push
```

The push to the `main` branch triggers the CI/CD workflow.

---

## 2.2 GitHub Repository

The repository contains the application source code and infrastructure configuration.

Important directories:

```text
app/
tests/
k8s/
k8s/monitoring/
.github/workflows/
docs/
```

The repository therefore acts as the source of truth for:

* Application code
* Tests
* Container definition
* Kubernetes manifests
* Monitoring configuration
* CI/CD configuration
* Documentation

---

# 3. CI/CD Architecture

The GitHub Actions workflow consists of three jobs:

```text
                    ┌───────────────┐
                    │      test     │
                    │ ubuntu-latest │
                    └───────┬───────┘
                            │
                         success
                            │
                            ▼
                    ┌───────────────┐
                    │ build-and-push│
                    │ ubuntu-latest │
                    └───────┬───────┘
                            │
                      image pushed
                            │
                            ▼
                    ┌───────────────┐
                    │    deploy     │
                    │ self-hosted   │
                    │    runner     │
                    └───────┬───────┘
                            │
                            ▼
                       Kubernetes
```

The dependency chain prevents deployment when the application tests fail.

---

## 3.1 Test Job

The first job runs on GitHub-hosted infrastructure.

It performs:

```text
Checkout
   ↓
Setup Python 3.12
   ↓
Install dependencies
   ↓
Run pytest
```

The important principle is:

> Never deploy an image if the application test stage has failed.

The `build-and-push` job therefore depends on:

```yaml
needs: test
```

---

## 3.2 Build and Push Job

After successful tests, the Docker image is built.

The image is tagged with both:

```text
<git-sha>
latest
```

Example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8ed2333bfeb03a55c7130bb5061580619d
```

and:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:latest
```

The Git SHA is the deployment identity.

This is preferable to deploying only `latest` because the exact image associated with a deployment can be identified later.

---

# 4. GitHub Container Registry Architecture

GHCR acts as the container image registry.

```text
GitHub Actions
      |
      | docker build
      ▼
Docker Image
      |
      | docker push
      ▼
GitHub Container Registry
      |
      | pull
      ▼
Kubernetes
```

The image repository is:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo
```

The Kubernetes cluster uses a Docker registry Secret:

```text
ghcr-pull-secret
```

This allows Kubernetes to authenticate when pulling the private image.

The Deployment references the secret through:

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```

---

# 5. Kubernetes Architecture

The Kubernetes environment uses a Kind cluster.

The cluster contains one control-plane node:

```text
fluid-ai-control-plane
```

The application resources are isolated in:

```text
fluid-ai
```

The monitoring resources are isolated in:

```text
monitoring
```

This creates a basic namespace separation:

```text
Kubernetes Cluster
│
├── fluid-ai
│   ├── backend
│   ├── postgres
│   ├── backend Service
│   ├── postgres Service
│   ├── backend-db Secret
│   └── ghcr-pull-secret
│
├── monitoring
│   ├── Prometheus
│   ├── Grafana
│   ├── Alertmanager
│   ├── Prometheus Operator
│   ├── kube-state-metrics
│   ├── Node Exporter
│   └── ServiceMonitors
│
└── kube-system
    └── Kubernetes system components
```

---

# 6. Backend Deployment

The backend is deployed using a Kubernetes Deployment.

The Deployment maintains two replicas:

```text
Deployment/backend
        |
        +──────────────+
        |              |
        ▼              ▼
     Backend Pod    Backend Pod
        #1              #2
```

The two replicas provide basic availability during normal rolling updates.

The Deployment uses the image:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:<git-sha>
```

---

# 7. Backend Pod Configuration

Each backend Pod contains the FastAPI application.

The container listens on:

```text
8000
```

The container exposes a named port:

```yaml
ports:
  - name: http
    containerPort: 8000
```

The named port is important because the ServiceMonitor references the port by name:

```yaml
port: http
```

This creates the following relationship:

```text
ServiceMonitor
     |
     | port=http
     ▼
Service
     |
     | targetPort=8000
     ▼
Backend Container
     |
     ▼
FastAPI :8000
```

---

# 8. Kubernetes Service

The backend is exposed internally using a ClusterIP Service.

```text
Service/backend
        |
        | selector:
        | app=backend
        |
        +──────────────┐
        │              │
        ▼              ▼
    Backend Pod     Backend Pod
```

The Service configuration is conceptually:

```yaml
ports:
  - name: http
    port: 8000
    targetPort: 8000

selector:
  app: backend
```

The Service provides stable internal networking even when Pods are replaced.

Pod IP addresses can change during deployments, but the Service remains stable.

---

# 9. PostgreSQL Architecture

The application communicates with PostgreSQL through a Kubernetes Service.

```text
Backend Pod
    |
    | DB_HOST=postgres
    |
    ▼
postgres Service
    |
    ▼
PostgreSQL Pod
```

The application uses environment variables for database configuration:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
```

Sensitive database values are stored in the Kubernetes Secret:

```text
backend-db
```

The application therefore does not require database credentials to be hard-coded into the image.

---

# 10. Application Health Architecture

The backend exposes two Kubernetes health endpoints.

## Liveness

```text
GET /healthz
```

Flow:

```text
Kubernetes
    |
    | HTTP GET
    ▼
Backend Pod
    |
    ▼
/healthz
    |
    ▼
{"status":"ok"}
```

If the container becomes unhealthy, Kubernetes can restart it.

---

## Readiness

```text
GET /readyz
```

Flow:

```text
Kubernetes
    |
    | HTTP GET
    ▼
Backend Pod
    |
    ▼
/readyz
    |
    ▼
Database connectivity check
    |
    +──── success ────▶ Ready
    |
    └──── failure ────▶ Not Ready
```

The readiness endpoint executes:

```sql
SELECT 1
```

against PostgreSQL.

This means a running application that cannot communicate with its database can be removed from Service traffic until it becomes ready again.

---

# 11. Rolling Deployment Architecture

The Deployment uses Kubernetes rolling update behavior.

A new image does not require manually deleting all Pods.

Instead:

```text
Old ReplicaSet
     |
     | new image
     ▼
New ReplicaSet
     |
     ▼
New Pods become Ready
     |
     ▼
Old Pods terminate
```

The deployment is considered successful only after:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

reports success.

---

# 12. Deployment Verification

The CI/CD pipeline performs several checks after deployment.

### Verify Kubernetes access

```bash
kubectl cluster-info
kubectl get nodes
```

### Update image

```bash
kubectl -n fluid-ai set image deployment/backend \
  backend=<image>:<git-sha>
```

### Wait for rollout

```bash
kubectl -n fluid-ai rollout status deployment/backend
```

### Verify deployed image

The actual image configured in the Deployment is queried and compared with the expected Git SHA.

Conceptually:

```text
Expected:
image:<current-git-sha>

        versus

Actual:
deployment.spec.template.spec.containers[0].image
```

If they differ, the CI/CD job fails.

---

# 13. Smoke Test Architecture

After the Kubernetes rollout succeeds, the deployment pipeline performs an application-level smoke test.

The backend Service is temporarily exposed to the self-hosted runner using port forwarding:

```text
Runner
  |
  | localhost:<port>
  ▼
kubectl port-forward
  |
  ▼
backend Service :8000
  |
  ▼
Backend Pod
```

The pipeline then calls:

```text
/healthz
```

This validates more than Kubernetes resource creation.

It verifies that:

```text
Deployment exists
        +
Pods are Ready
        +
Service routes traffic
        +
FastAPI responds
```

---

# 14. Observability Architecture

The monitoring architecture is based on Prometheus Operator.

```text
                    ┌───────────────────┐
                    │ Prometheus        │
                    │ Operator          │
                    └─────────┬─────────┘
                              │
                 watches monitoring CRDs
                              │
                              ▼
                    ┌───────────────────┐
                    │ ServiceMonitor    │
                    └─────────┬─────────┘
                              │
                       selects Service
                              │
                              ▼
                    ┌───────────────────┐
                    │ backend Service   │
                    └─────────┬─────────┘
                              │
                       routes to Pods
                              │
                              ▼
                    ┌───────────────────┐
                    │ FastAPI /metrics │
                    └─────────┬─────────┘
                              │
                         HTTP scrape
                              │
                              ▼
                    ┌───────────────────┐
                    │ Prometheus        │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Grafana           │
                    └───────────────────┘
```

---

# 15. Prometheus Metrics Flow

The FastAPI application uses:

```text
prometheus-fastapi-instrumentator
```

to expose application metrics.

The endpoint is:

```text
/metrics
```

Prometheus periodically scrapes this endpoint.

The backend metrics include:

```text
http_requests_total
```

with labels such as:

```text
handler
method
status
namespace
pod
service
job
instance
```

Example:

```text
http_requests_total{
    handler="/healthz",
    method="GET",
    status="2xx"
}
```

This allows metrics to be aggregated by endpoint, pod, service, status, or other labels.

---

# 16. ServiceMonitor Architecture

The custom ServiceMonitor is:

```text
fluid-ai-backend
```

It is created in the `monitoring` namespace but monitors a Service in the `fluid-ai` namespace.

Its namespace selector is:

```yaml
namespaceSelector:
  matchNames:
    - fluid-ai
```

Its Service selector is:

```yaml
selector:
  matchLabels:
    app: backend
```

The endpoint is:

```yaml
endpoints:
  - interval: 15s
    path: /metrics
    port: http
```

Therefore:

```text
ServiceMonitor
      |
      | namespace = fluid-ai
      | label = app: backend
      | port = http
      | path = /metrics
      | interval = 15s
      ▼
backend Service
      |
      ▼
Backend Pods
      |
      ▼
/metrics
```

---

# 17. Prometheus Target Discovery

Prometheus discovers the backend as a monitoring target through the ServiceMonitor.

A successful target appears conceptually as:

```text
job="backend"
namespace="fluid-ai"
service="backend"
```

The target health can be queried using:

```promql
up{job="backend"}
```

A value of:

```text
1
```

indicates that Prometheus successfully scraped the target.

For the two backend replicas, the expected result is two healthy targets:

```text
backend Pod #1 → up = 1
backend Pod #2 → up = 1
```

---

# 18. Grafana Architecture

Grafana consumes metrics from Prometheus.

```text
Backend
   |
   | /metrics
   ▼
Prometheus
   |
   | PromQL
   ▼
Grafana
```

Grafana can therefore visualize:

* Request volume
* Application availability
* Pod health
* Kubernetes resource usage
* Node metrics
* Container metrics
* Application performance

The project uses the Grafana instance provided by `kube-prometheus-stack`.

---

# 19. Alertmanager Architecture

Alertmanager is deployed alongside Prometheus.

Its responsibility is to handle alerts generated by Prometheus.

Conceptually:

```text
Metrics
   |
   ▼
Prometheus
   |
   | alerting rules
   ▼
Alertmanager
   |
   +── notifications
   +── grouping
   +── routing
   +── silencing
```

Alertmanager separates alert evaluation from alert routing and notification handling.

---

# 20. Kubernetes Monitoring Components

The monitoring stack also includes Kubernetes-level components.

### Prometheus Operator

Manages Prometheus-related Kubernetes resources.

### Prometheus

Collects and stores time-series metrics.

### Grafana

Visualizes metrics.

### Alertmanager

Handles alerts.

### kube-state-metrics

Exposes Kubernetes object state as metrics.

Examples include:

* Deployment status
* Pod status
* Replica counts
* Kubernetes resource state

### Node Exporter

Exposes host-level metrics such as:

* CPU
* Memory
* Filesystem
* Network
* System statistics

Together these components provide both:

```text
Application Observability
```

and:

```text
Infrastructure / Kubernetes Observability
```

---

# 21. Kubernetes Custom Resource Architecture

The Prometheus Operator introduces Kubernetes Custom Resource Definitions (CRDs).

Important CRDs include:

```text
Prometheus
Alertmanager
ServiceMonitor
PrometheusRule
PodMonitor
Probe
```

The CRD extends the Kubernetes API.

Instead of configuring everything through command-line flags, monitoring configuration can be represented as Kubernetes objects.

For example:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
```

This allows monitoring configuration to be version-controlled alongside the application.

---

# 22. Why ServiceMonitor Is Useful

Without the Prometheus Operator, Prometheus scrape configuration can be maintained manually.

With ServiceMonitor:

```text
Kubernetes Service
        +
Service labels
        +
ServiceMonitor
```

can define the monitoring relationship declaratively.

This is particularly useful in dynamic Kubernetes environments because Pods can be created, deleted, and replaced frequently.

The ServiceMonitor allows Prometheus to discover the correct endpoints without hard-coding Pod IP addresses.

---

# 23. End-to-End Request Flow

A normal application request follows:

```text
Client
  |
  ▼
backend Service
  |
  ▼
Backend Pod
  |
  ▼
FastAPI
  |
  ▼
PostgreSQL
```

For monitoring:

```text
Prometheus
  |
  ▼
backend Service
  |
  ▼
Backend Pod
  |
  ▼
/metrics
```

For visualization:

```text
Prometheus
  |
  ▼
Grafana
```

---

# 24. End-to-End Deployment Flow

A code change follows this lifecycle:

```text
Developer changes code
        |
        ▼
git commit
        |
        ▼
git push
        |
        ▼
GitHub Actions
        |
        ▼
Run tests
        |
        +---- failure → stop
        |
        ▼
Build Docker image
        |
        ▼
Push image to GHCR
        |
        ▼
Self-hosted runner
        |
        ▼
kubectl set image
        |
        ▼
Kubernetes rolling update
        |
        ▼
New Pods start
        |
        ▼
Liveness / Readiness checks
        |
        ▼
Rollout succeeds
        |
        ▼
Smoke test
        |
        ▼
Deployment complete
        |
        ▼
Prometheus discovers Pods
        |
        ▼
Metrics collected
        |
        ▼
Grafana visualization
```

---

# 25. Failure Handling

The architecture includes multiple points where failures can stop or contain a deployment problem.

## Test failure

```text
pytest fails
    ↓
build job does not run
```

## Image build failure

```text
Docker build fails
    ↓
image is not pushed
    ↓
deployment does not run
```

## Kubernetes rollout failure

```text
New Pods fail
    ↓
rollout status fails
    ↓
CI/CD job fails
```

## Readiness failure

```text
Database unavailable
    ↓
/readyz returns 503
    ↓
Pod is not Ready
    ↓
Service does not send normal traffic to it
```

## Smoke test failure

```text
Deployment appears successful
        ↓
Application endpoint fails
        ↓
Smoke test fails
        ↓
CI/CD job reports failure
```

This layered verification is important because infrastructure success does not necessarily mean application success.

---

# 26. Rollback Architecture

Kubernetes stores Deployment revisions.

Deployment history can be viewed using:

```bash
kubectl rollout history deployment/backend -n fluid-ai
```

If a deployment introduces a problem, the previous revision can be restored:

```bash
kubectl rollout undo deployment/backend -n fluid-ai
```

The rollback flow is:

```text
Current Deployment
       |
       | problem detected
       ▼
Previous ReplicaSet
       |
       ▼
kubectl rollout undo
       |
       ▼
Previous application image
```

---

# 27. Security Boundaries

The project separates sensitive configuration from application code.

Database credentials are stored in:

```text
backend-db
```

Container registry credentials are stored in:

```text
ghcr-pull-secret
```

The application image itself does not contain the database password or registry credential.

The GitHub Actions workflow uses the GitHub-provided:

```text
GITHUB_TOKEN
```

for GHCR authentication during image publishing.

The Kubernetes cluster uses its own registry pull credential for pulling the private image.

This creates separate authentication boundaries:

```text
GitHub Actions
      |
      | GITHUB_TOKEN
      ▼
GHCR push

Kubernetes
      |
      | ghcr-pull-secret
      ▼
GHCR pull
```

---

# 28. Infrastructure Boundaries

The project separates responsibilities into logical layers:

```text
Source Control
    |
    ▼
CI/CD
    |
    ▼
Container Registry
    |
    ▼
Kubernetes Runtime
    |
    ├── Application
    ├── Database
    └── Networking
    |
    ▼
Observability
    |
    ├── Metrics
    ├── Prometheus
    ├── Grafana
    └── Alertmanager
```

This separation makes the system easier to operate and troubleshoot.

---

# 29. Architecture Design Principles

The implementation follows several important cloud-native principles.

### Immutable deployments

Images are tagged using Git SHA values.

### Declarative infrastructure

Kubernetes configuration is stored as YAML.

### Automated delivery

GitHub Actions performs deployment automatically.

### Health-aware deployment

Kubernetes uses liveness and readiness probes.

### Observable workloads

The application exposes Prometheus metrics.

### Dynamic discovery

ServiceMonitor discovers application monitoring targets through Kubernetes Services.

### Separation of secrets

Credentials are stored separately from application code.

### Reproducibility

Application, Kubernetes, CI/CD, and monitoring configuration are version-controlled.

### Operational verification

Deployment success is verified at multiple levels rather than relying only on command completion.

---

# 30. Architecture Summary

The final architecture connects software delivery, containerization, Kubernetes, and observability into a single workflow:

```text
                    SOFTWARE DELIVERY
                           │
                           ▼
                     GitHub Actions
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
              Testing              Build
                                     │
                                     ▼
                                   GHCR
                                     │
                                     ▼
                              Self-hosted Runner
                                     │
                                     ▼
                    ┌──────────────────────────┐
                    │       Kubernetes         │
                    │                          │
                    │  Backend ─── PostgreSQL │
                    │     │                    │
                    │     └── /metrics         │
                    └──────┬───────────────────┘
                           │
                           ▼
                     ServiceMonitor
                           │
                           ▼
                       Prometheus
                           │
                    ┌──────┴───────┐
                    ▼              ▼
                 Grafana       Alertmanager
```

The architecture therefore demonstrates a complete DevOps lifecycle:

```text
Develop
  ↓
Test
  ↓
Build
  ↓
Package
  ↓
Publish
  ↓
Deploy
  ↓
Verify
  ↓
Observe
  ↓
Troubleshoot
  ↓
Rollback when required
```
