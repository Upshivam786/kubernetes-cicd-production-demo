# Fluid AI DevOps Challenge — Monitoring & Observability

## 1. Overview

The project implements application and Kubernetes monitoring using:

* Prometheus
* Grafana
* Prometheus Operator
* `kube-prometheus-stack`
* Kubernetes Custom Resource Definitions (CRDs)
* ServiceMonitor
* Prometheus metrics exposed by FastAPI
* Kubernetes health probes
* Prometheus HTTP API

The monitoring architecture collects metrics from the Fluid AI backend and Kubernetes itself.

The main monitoring flow is:

```text
FastAPI Backend
      │
      │ /metrics
      ▼
Kubernetes Service
      │
      │ ServiceMonitor
      ▼
Prometheus Operator
      │
      ▼
Prometheus
      │
      ├──────────────► Prometheus Queries
      │
      ▼
    Grafana
```

---

# 2. Observability Goals

The monitoring implementation provides visibility into:

* Application availability
* Kubernetes Pod availability
* HTTP request counts
* HTTP request status
* Request handlers
* Application process metrics
* Python runtime metrics
* Kubernetes node metrics
* Kubernetes control-plane metrics
* Container metrics
* Prometheus target health

The project therefore demonstrates both:

```text
Application Observability
```

and:

```text
Infrastructure Observability
```

---

# 3. Application Metrics

The FastAPI application uses:

```text
prometheus-fastapi-instrumentator
```

The dependency is defined in:

```text
app/requirements.txt
```

Example:

```text
prometheus-fastapi-instrumentator==7.1.0
```

The application initializes the instrumentator:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

This exposes Prometheus-compatible metrics at:

```text
/metrics
```

---

# 4. FastAPI Health Endpoints

The application exposes two Kubernetes health endpoints.

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

This endpoint indicates that the application process is alive.

---

## Readiness

```text
GET /readyz
```

The readiness endpoint also checks database connectivity.

The application executes:

```sql
SELECT 1
```

If the database is reachable:

```json
{
  "status": "ready"
}
```

If the database is unavailable:

```text
HTTP 503
```

with:

```json
{
  "status": "not ready"
}
```

This allows Kubernetes to distinguish between:

```text
Application is running
```

and:

```text
Application is actually ready to serve traffic
```

---

# 5. Kubernetes Probes

The backend Deployment uses both probes.

## Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 2
  failureThreshold: 3
```

Kubernetes periodically calls:

```text
http://<pod>:8000/healthz
```

---

## Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /readyz
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 3
```

This checks whether the application can actually communicate with its database.

---

# 6. Why Liveness and Readiness Are Different

The distinction is important.

### Liveness

Answers:

> Is the application process alive?

### Readiness

Answers:

> Can this application currently serve requests?

For example, if PostgreSQL becomes unavailable:

```text
FastAPI process
      │
      ▼
still running
      │
      ▼
/healthz → 200
      │
      ▼
/readyz → 503
```

Kubernetes can then remove the Pod from Service endpoints without necessarily restarting the application.

---

# 7. Kubernetes Monitoring Namespace

Monitoring runs in its own namespace:

```text
monitoring
```

Create it with:

```bash
kubectl create namespace monitoring
```

Verify:

```bash
kubectl get namespace monitoring
```

Expected:

```text
NAME         STATUS
monitoring   Active
```

---

# 8. Helm

Helm is used to install the monitoring stack.

Verify Helm:

```bash
helm version
```

The project used:

```text
Helm v3.20.0
```

---

# 9. kube-prometheus-stack

The monitoring solution uses:

```text
prometheus-community/kube-prometheus-stack
```

The chart used in this project was:

```text
kube-prometheus-stack
Chart Version: 88.2.0
App Version: v0.93.0
```

Search the repository:

```bash
helm search repo prometheus-community/kube-prometheus-stack
```

Example:

```text
NAME
prometheus-community/kube-prometheus-stack
```

---

# 10. What Is kube-prometheus-stack?

`kube-prometheus-stack` packages several monitoring components together.

The deployed stack includes components such as:

```text
Prometheus
Alertmanager
Grafana
Prometheus Operator
kube-state-metrics
node-exporter
```

The stack also installs the Kubernetes monitoring resources required to connect these components.

---

# 11. Prometheus Operator

The Prometheus Operator manages Prometheus deployments through Kubernetes resources.

Instead of manually writing the complete Prometheus configuration, Kubernetes resources can describe what should be monitored.

For example:

```text
ServiceMonitor
```

describes how a Kubernetes Service should be scraped.

The Operator watches these resources and configures Prometheus accordingly.

---

# 12. What Are Kubernetes CRDs?

CRD means:

```text
Custom Resource Definition
```

Kubernetes has built-in resources such as:

```text
Pod
Deployment
Service
ConfigMap
Secret
```

CRDs allow an operator to introduce new Kubernetes resource types.

The Prometheus Operator introduces resources such as:

```text
Prometheus
Alertmanager
ServiceMonitor
PodMonitor
PrometheusRule
Probe
```

These become Kubernetes API resources.

---

# 13. Example CRDs

Check them with:

```bash
kubectl get crd | grep monitoring.coreos.com
```

The project installed resources including:

```text
alertmanagerconfigs.monitoring.coreos.com
alertmanagers.monitoring.coreos.com
podmonitors.monitoring.coreos.com
probes.monitoring.coreos.com
prometheusagents.monitoring.coreos.com
prometheuses.monitoring.coreos.com
prometheusrules.monitoring.coreos.com
scrapeconfigs.monitoring.coreos.com
servicemonitors.monitoring.coreos.com
thanosrulers.monitoring.coreos.com
```

---

# 14. CRD Mental Model

A useful way to understand the architecture is:

```text
Kubernetes API
      │
      ├── Deployment
      ├── Service
      ├── Pod
      │
      └── Prometheus Operator CRDs
              │
              ├── Prometheus
              ├── Alertmanager
              ├── ServiceMonitor
              ├── PodMonitor
              └── PrometheusRule
```

The CRDs extend the Kubernetes API.

---

# 15. Prometheus Resource

The Prometheus Operator creates a Prometheus resource.

Check it:

```bash
kubectl get prometheus -n monitoring
```

The project eventually showed:

```text
NAME                                    VERSION
monitoring-crds-kube-prome-prometheus   v3.13.2-distroless
```

---

# 16. Alertmanager Resource

Check:

```bash
kubectl get alertmanager -n monitoring
```

The project deployed an Alertmanager instance.

Alertmanager is responsible for handling alerts generated by Prometheus.

Conceptually:

```text
Prometheus
    │
    │ Alert
    ▼
Alertmanager
    │
    └── Notification / Routing
```

---

# 17. Monitoring Components

Check the monitoring Pods:

```bash
kubectl get pods -n monitoring
```

The final healthy environment contained components similar to:

```text
alertmanager-...                       2/2 Running
grafana-...                            3/3 Running
kube-prometheus-operator-...           1/1 Running
kube-state-metrics-...                 1/1 Running
prometheus-node-exporter-...           1/1 Running
prometheus-...                          2/2 Running
```

---

# 18. kube-state-metrics

`kube-state-metrics` exposes metrics about Kubernetes object state.

For example, it can expose information about:

* Deployments
* Pods
* ReplicaSets
* Nodes
* Services
* StatefulSets

This allows Prometheus to understand Kubernetes state.

---

# 19. node-exporter

The node exporter exposes operating-system and node-level metrics.

Examples include:

* CPU
* Memory
* Disk
* Filesystem
* Network
* System metrics

It provides infrastructure-level visibility.

---

# 20. Grafana

Grafana provides dashboards and visualization for Prometheus data.

The Kubernetes Service can be inspected with:

```bash
kubectl get svc -n monitoring
```

The Grafana Service is:

```text
monitoring-crds-grafana
```

It runs internally as a Kubernetes `ClusterIP` Service.

---

# 21. Access Grafana Locally

Because the cluster is local, Grafana can be accessed using port forwarding.

First identify the Pod:

```bash
kubectl get pods -n monitoring
```

Then:

```bash
kubectl port-forward -n monitoring \
  service/monitoring-crds-grafana 3000:80
```

Grafana can then be accessed locally at:

```text
http://127.0.0.1:3000
```

---

# 22. Grafana Credentials

The Helm installation provides an admin password through a Kubernetes Secret.

Example command:

```bash
kubectl get secret \
  -n monitoring \
  monitoring-crds-grafana \
  -o jsonpath="{.data.admin-password}" | base64 -d
```

The password should never be committed to Git.

---

# 23. ServiceMonitor

The backend is monitored using:

```text
ServiceMonitor
```

The resource is:

```text
k8s/monitoring/backend-servicemonitor.yaml
```

It was created with:

```bash
kubectl apply \
  -f k8s/monitoring/backend-servicemonitor.yaml
```

Verify:

```bash
kubectl get servicemonitor -n monitoring
```

---

# 24. Backend ServiceMonitor

The final ServiceMonitor looks conceptually like:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor

metadata:
  name: fluid-ai-backend
  namespace: monitoring
  labels:
    release: monitoring-crds

spec:
  endpoints:
    - interval: 15s
      path: /metrics
      port: http

  namespaceSelector:
    matchNames:
      - fluid-ai

  selector:
    matchLabels:
      app: backend
```

---

# 25. Understanding the ServiceMonitor

The ServiceMonitor tells Prometheus:

```text
Find Services
    │
    ▼
namespace = fluid-ai
    │
    ▼
label app=backend
    │
    ▼
use Service port named "http"
    │
    ▼
GET /metrics
    │
    ▼
every 15 seconds
```

---

# 26. Why `namespaceSelector` Is Required

The ServiceMonitor itself exists in:

```text
monitoring
```

The backend Service exists in:

```text
fluid-ai
```

Therefore the ServiceMonitor needs:

```yaml
namespaceSelector:
  matchNames:
    - fluid-ai
```

Without this, the ServiceMonitor would search the wrong namespace.

---

# 27. Why the Service Port Needs a Name

The backend Service originally had:

```yaml
ports:
  - port: 8000
    targetPort: 8000
```

The ServiceMonitor referred to:

```yaml
port: http
```

Prometheus Operator expects the named Service port.

Therefore the Service was changed to:

```yaml
ports:
  - name: http
    port: 8000
    targetPort: 8000
```

This is an important Kubernetes monitoring detail.

---

# 28. Service Labels vs Service Selectors

There are two different concepts.

The Service selector:

```yaml
selector:
  app: backend
```

selects backend Pods.

The Service label:

```yaml
labels:
  app: backend
```

identifies the Service itself.

The ServiceMonitor's:

```yaml
selector:
  matchLabels:
    app: backend
```

selects the Service.

Therefore:

```text
ServiceMonitor
      │
      │ Service label
      ▼
backend Service
      │
      │ Service selector
      ▼
backend Pods
```

This distinction was important during troubleshooting.

---

# 29. Initial Monitoring Problem

Initially, querying Prometheus for:

```promql
http_requests_total
```

returned:

```json
{
  "status": "success",
  "data": {
    "result": []
  }
}
```

This meant:

```text
Prometheus was running
```

but:

```text
backend metrics were not being collected
```

---

# 30. Debugging the ServiceMonitor

The ServiceMonitor was inspected:

```bash
kubectl describe servicemonitor \
  fluid-ai-backend \
  -n monitoring
```

Important configuration:

```text
Namespace Selector:
  fluid-ai

Selector:
  app=backend

Endpoint:
  /metrics

Port:
  http
```

---

# 31. Checking the Backend Service

The backend Service was inspected:

```bash
kubectl get svc backend -n fluid-ai -o yaml
```

The final Service contained:

```yaml
metadata:
  labels:
    app: backend

spec:
  ports:
    - name: http
      port: 8000
      targetPort: 8000

  selector:
    app: backend
```

This satisfied the ServiceMonitor requirements.

---

# 32. Prometheus ServiceMonitor Selection

The Prometheus resource was inspected:

```bash
kubectl get prometheus -n monitoring -o yaml
```

The important configuration was:

```yaml
serviceMonitorNamespaceSelector: {}

serviceMonitorSelector:
  matchLabels:
    release: monitoring-crds
```

Therefore the backend ServiceMonitor needed:

```yaml
labels:
  release: monitoring-crds
```

This label allows the Prometheus instance to select the ServiceMonitor.

---

# 33. Complete Monitoring Chain

The final working configuration is:

```text
FastAPI
  │
  │ /metrics
  ▼
Backend Pod
  │
  ▼
Backend Service
  │
  │ label: app=backend
  ▼
ServiceMonitor
  │
  │ label: release=monitoring-crds
  ▼
Prometheus Operator
  │
  ▼
Prometheus
```

---

# 34. Verify Prometheus Targets

Prometheus exposes information about scrape targets.

The Prometheus API can be queried through:

```text
/api/v1/targets
```

For a local port-forward:

```bash
kubectl port-forward \
  -n monitoring \
  service/monitoring-crds-kube-prome-prometheus \
  9090:9090
```

Then inspect:

```bash
curl -s \
  http://127.0.0.1:9090/api/v1/targets
```

---

# 35. Prometheus `up` Metric

A simple PromQL query is:

```promql
up
```

It shows whether Prometheus can successfully scrape targets.

For the backend:

```promql
up{namespace="fluid-ai"}
```

The final result contained backend targets with:

```text
value = 1
```

For example:

```text
job: backend
namespace: fluid-ai
service: backend
```

A value of:

```text
1
```

means the target is currently up.

---

# 36. Backend Target Verification

Query:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool
```

The final result showed two backend Pods:

```text
instance: 10.244.x.x:8000
job: backend
namespace: fluid-ai
pod: backend-...
service: backend
value: 1
```

This confirms Prometheus is scraping both backend replicas.

---

# 37. HTTP Request Metrics

The FastAPI application exposes:

```text
http_requests_total
```

Query:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool
```

The final result contained metrics such as:

```text
handler="/healthz"
handler="/readyz"
handler="/metrics"
```

with labels including:

```text
method
status
pod
service
namespace
job
instance
```

---

# 38. Example HTTP Metric

A backend metric can look like:

```text
http_requests_total{
  container="backend",
  endpoint="http",
  handler="/healthz",
  instance="10.244.0.22:8000",
  job="backend",
  method="GET",
  namespace="fluid-ai",
  pod="backend-...",
  service="backend",
  status="2xx"
}
```

This gives Prometheus enough dimensions to analyze application traffic.

---

# 39. Request Rate

Because `http_requests_total` is a counter, request rate should normally be calculated with `rate()`.

Example:

```promql
rate(http_requests_total{job="backend"}[5m])
```

This estimates requests per second over the previous five minutes.

---

# 40. Request Rate by Endpoint

To group request traffic by handler:

```promql
sum by (handler) (
  rate(http_requests_total{job="backend"}[5m])
)
```

This can show which API endpoints receive the most traffic.

---

# 41. Request Rate by Pod

Use:

```promql
sum by (pod) (
  rate(http_requests_total{job="backend"}[5m])
)
```

This helps identify traffic distribution across replicas.

---

# 42. HTTP Error Monitoring

The status label can be used to identify unsuccessful responses.

For example:

```promql
sum(
  rate(http_requests_total{
    job="backend",
    status=~"5xx"
  }[5m])
)
```

This can be used as an application error-rate signal.

---

# 43. HTTP Success Rate

A simple success-rate calculation is:

```promql
sum(rate(http_requests_total{
  job="backend",
  status=~"2xx"
}[5m]))
/
sum(rate(http_requests_total{
  job="backend"
}[5m]))
```

This produces an approximate percentage when multiplied by 100.

---

# 44. Pod Availability

Check:

```promql
up{job="backend"}
```

Expected:

```text
1
1
```

for two healthy replicas.

If one Pod becomes unavailable:

```text
1
0
```

This immediately exposes a degraded backend.

---

# 45. Application Process Metrics

The `/metrics` endpoint also exposes process-level metrics.

Examples include:

```text
process_virtual_memory_bytes
process_resident_memory_bytes
process_cpu_seconds_total
process_start_time_seconds
```

These provide visibility into the Python application process.

---

# 46. Python Runtime Metrics

Python runtime metrics include:

```text
python_info
python_gc_objects_collected_total
python_gc_objects_uncollectable_total
python_gc_collections_total
```

These are useful when investigating application resource behavior.

---

# 47. Prometheus Self-Monitoring

Prometheus also monitors its own environment.

The `up` query demonstrated targets such as:

```text
coredns
kubelet
prometheus-operator
node-exporter
kube-state-metrics
prometheus
```

This means the monitoring system is monitoring the monitoring infrastructure as well.

---

# 48. Monitoring Stack Verification Commands

Check all monitoring Pods:

```bash
kubectl get pods -n monitoring
```

Check Deployments:

```bash
kubectl get deployments -n monitoring
```

Check StatefulSets:

```bash
kubectl get statefulsets -n monitoring
```

Check Prometheus:

```bash
kubectl get prometheus -n monitoring
```

Check Alertmanager:

```bash
kubectl get alertmanager -n monitoring
```

Check Services:

```bash
kubectl get svc -n monitoring
```

Check ServiceMonitors:

```bash
kubectl get servicemonitor -n monitoring
```

---

# 49. Helm Verification

Check the Helm release:

```bash
helm list -n monitoring
```

Expected release:

```text
monitoring-crds
```

Check release status:

```bash
helm status monitoring-crds -n monitoring
```

---

# 50. Monitoring Troubleshooting

## Problem: Prometheus does not show backend metrics

Start with:

```bash
kubectl get servicemonitor -n monitoring
```

Then:

```bash
kubectl describe servicemonitor \
  fluid-ai-backend \
  -n monitoring
```

---

## Check backend Service labels

```bash
kubectl get svc backend \
  -n fluid-ai \
  --show-labels
```

Expected:

```text
app=backend
```

---

## Check Service port

```bash
kubectl get svc backend \
  -n fluid-ai \
  -o yaml
```

The port should contain:

```yaml
- name: http
  port: 8000
  targetPort: 8000
```

---

## Check ServiceMonitor selector

```bash
kubectl get servicemonitor \
  fluid-ai-backend \
  -n monitoring \
  -o jsonpath='{.spec.selector.matchLabels}{"\n"}'
```

Expected:

```json
{"app":"backend"}
```

---

## Check Prometheus selector

```bash
kubectl get prometheus \
  -n monitoring \
  -o yaml | \
  grep -A8 -B2 serviceMonitorSelector
```

Expected:

```yaml
serviceMonitorSelector:
  matchLabels:
    release: monitoring-crds
```

Therefore:

```bash
kubectl get servicemonitor fluid-ai-backend \
  -n monitoring \
  -o jsonpath='{.metadata.labels}{"\n"}'
```

should contain:

```text
release=monitoring-crds
```

---

# 51. Check Application Metrics Directly

Port-forward the backend:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8002:8000
```

Then:

```bash
curl -s \
  http://127.0.0.1:8002/metrics
```

Check HTTP metrics:

```bash
curl -s \
  http://127.0.0.1:8002/metrics | \
  grep http_requests
```

If this works but Prometheus does not contain the metric, the problem is likely in the ServiceMonitor/Prometheus discovery chain rather than the application.

---

# 52. Check Prometheus Query API

Check all targets:

```bash
curl -s \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up' \
  | python -m json.tool
```

Check backend:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool
```

Check application metrics:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool
```

---

# 53. Useful PromQL Queries

## Backend availability

```promql
up{job="backend"}
```

## Total request rate

```promql
sum(rate(http_requests_total{job="backend"}[5m]))
```

## Requests by endpoint

```promql
sum by (handler) (
  rate(http_requests_total{job="backend"}[5m])
)
```

## Requests by status

```promql
sum by (status) (
  rate(http_requests_total{job="backend"}[5m])
)
```

## Five-minute error rate

```promql
sum(
  rate(http_requests_total{
    job="backend",
    status=~"5xx"
  }[5m])
)
```

## Requests by Pod

```promql
sum by (pod) (
  rate(http_requests_total{job="backend"}[5m])
)
```

---

# 54. Monitoring Architecture

The final architecture is:

```text
                         Kubernetes Cluster
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  fluid-ai namespace                                        │
│                                                             │
│  ┌──────────────────┐       ┌──────────────────┐             │
│  │ Backend Pod      │       │ Backend Pod      │             │
│  │                  │       │                  │             │
│  │ FastAPI          │       │ FastAPI          │             │
│  │ /healthz         │       │ /healthz         │             │
│  │ /readyz          │       │ /readyz          │             │
│  │ /metrics         │       │ /metrics         │             │
│  └────────┬─────────┘       └────────┬─────────┘             │
│           │                          │                       │
│           └──────────┬───────────────┘                       │
│                      │                                       │
│                Backend Service                              │
│                      │                                       │
└──────────────────────┼───────────────────────────────────────┘
                       │
                       │ ServiceMonitor
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ monitoring namespace                                        │
│                                                             │
│  Prometheus Operator                                        │
│         │                                                   │
│         ▼                                                   │
│  Prometheus ───────────────► Prometheus TSDB                │
│         │                                                   │
│         ├──────────────► Kubernetes metrics                  │
│         │                                                   │
│         └──────────────► Application metrics                 │
│                                                             │
│         │                                                   │
│         ▼                                                   │
│      Grafana                                                │
│                                                             │
│      Alertmanager                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

# 55. What This Monitoring Implementation Demonstrates

This project demonstrates practical observability concepts rather than simply installing Prometheus.

It includes:

* Application metrics
* HTTP metrics
* Kubernetes health probes
* Prometheus scraping
* Prometheus Operator
* Kubernetes CRDs
* ServiceMonitor
* Cross-namespace monitoring
* Service label selection
* Named Service ports
* Prometheus target verification
* PromQL queries
* Grafana integration
* Kubernetes infrastructure metrics
* Monitoring troubleshooting

---

# 56. Important Troubleshooting Lesson

The most important troubleshooting lesson from this implementation was:

> Installing Prometheus does not automatically mean the application is being monitored.

The complete chain must work:

```text
Application
    ↓
/metrics
    ↓
Pod
    ↓
Service
    ↓
Service labels
    ↓
ServiceMonitor
    ↓
Prometheus selector
    ↓
Prometheus target
    ↓
PromQL metric
```

If any link is broken, the metric will not appear.

---

# 57. Final Monitoring Checklist

```text
[ ] FastAPI exposes /metrics
[ ] prometheus-fastapi-instrumentator installed
[ ] /healthz works
[ ] /readyz works
[ ] Kubernetes liveness probe configured
[ ] Kubernetes readiness probe configured
[ ] monitoring namespace exists
[ ] kube-prometheus-stack installed
[ ] Prometheus Operator running
[ ] Prometheus running
[ ] Grafana running
[ ] Alertmanager running
[ ] kube-state-metrics running
[ ] node-exporter running
[ ] Prometheus CRDs installed
[ ] ServiceMonitor created
[ ] Service has app=backend label
[ ] Service port is named http
[ ] ServiceMonitor selects fluid-ai namespace
[ ] ServiceMonitor has release=monitoring-crds
[ ] Prometheus selects ServiceMonitor
[ ] backend target shows up=1
[ ] http_requests_total available
[ ] Grafana accessible
```

---

# 58. Related Documentation

* `README.md` — Project introduction and quick start
* `docs/01-project-overview.md` — Project scope
* `docs/02-architecture.md` — System architecture
* `docs/03-local-setup.md` — Local development
* `docs/04-kubernetes-deployment.md` — Kubernetes deployment
* `docs/05-cicd-pipeline.md` — CI/CD implementation
* `docs/06-monitoring-observability.md` — Monitoring and observability
* `docs/07-troubleshooting.md` — Troubleshooting guide
* `docs/08-operations-runbook.md` — Day-2 operations
