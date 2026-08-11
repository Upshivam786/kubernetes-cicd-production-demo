# Fluid AI DevOps Challenge — Troubleshooting Guide

## 1. Purpose

This document records the major issues encountered while developing, containerizing, deploying, monitoring, and operating the Fluid AI DevOps Challenge.

The goal is to make the project reproducible and easier to debug for another engineer.

The troubleshooting approach used throughout the project follows:

```text
Observe
   ↓
Identify failing layer
   ↓
Inspect configuration
   ↓
Validate assumptions
   ↓
Apply minimal fix
   ↓
Re-test
   ↓
Verify end-to-end
```

---

# 2. Troubleshooting Layers

When something fails, determine which layer is responsible.

```text
Application
    ↓
Docker
    ↓
Container Registry
    ↓
Kubernetes
    ↓
Service / Networking
    ↓
Database
    ↓
CI/CD
    ↓
Monitoring
```

Do not immediately modify Kubernetes configuration when the application itself is failing.

---

# 3. Basic Diagnostic Commands

## Kubernetes Context

```bash
kubectl config current-context
```

Check cluster:

```bash
kubectl cluster-info
```

Check nodes:

```bash
kubectl get nodes
```

---

## Namespaces

```bash
kubectl get namespaces
```

---

## All Pods

```bash
kubectl get pods -A
```

For the application:

```bash
kubectl get pods -n fluid-ai
```

For monitoring:

```bash
kubectl get pods -n monitoring
```

---

# 4. Check Deployment

```bash
kubectl get deployments -n fluid-ai
```

Detailed information:

```bash
kubectl describe deployment backend -n fluid-ai
```

Check the currently deployed image:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

This is particularly useful for verifying that CI/CD actually deployed the expected Git commit.

---

# 5. Verify Pods

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend
```

Expected:

```text
backend-...   1/1   Running
backend-...   1/1   Running
```

If a Pod is not running:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Then inspect logs:

```bash
kubectl logs <pod-name> -n fluid-ai
```

---

# 6. Pod Restart Investigation

Check restart counts:

```bash
kubectl get pods -n fluid-ai
```

If a Pod shows:

```text
RESTARTS > 0
```

inspect:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Also check previous container logs:

```bash
kubectl logs <pod-name> \
  -n fluid-ai \
  --previous
```

---

# 7. Database Connection Failure

One of the local development failures occurred when starting FastAPI with:

```bash
DB_PASSWORD=test-password \
uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8001
```

The application failed with:

```text
psycopg2.OperationalError:
connection to server at "localhost"
port 5432 failed:
FATAL: password authentication failed
for user "appuser"
```

---

## Root Cause

The PostgreSQL server was reachable, but the credentials supplied to the application did not match the PostgreSQL credentials.

The important distinction is:

```text
Connection refused
```

versus:

```text
Password authentication failed
```

The second means the database server was reachable.

---

## Fix

The correct database configuration used during local Kubernetes testing was:

```bash
DB_HOST=127.0.0.1 \
DB_PORT=15432 \
DB_NAME=appdb \
DB_USER=appuser \
DB_PASSWORD='appsecret' \
uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8008
```

The PostgreSQL Service was exposed locally with:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/postgres \
  15432:5432
```

This produced:

```text
127.0.0.1:15432
        ↓
Kubernetes Service
        ↓
PostgreSQL :5432
```

---

# 8. Port Already in Use

Port `8001` was already occupied.

Attempting:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8001:8000
```

produced:

```text
bind: address already in use
```

---

## Investigation

```bash
sudo lsof -i :8001
```

The output showed another process listening on the port.

---

## Decision

The existing process was intentionally **not killed**.

A different local port was selected:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8002:8000
```

This is a useful operational practice:

> If a port is occupied by a valid process and there is no requirement to stop it, use another available local port.

---

# 9. `/metrics` Returned 404

Initially:

```bash
curl -i http://127.0.0.1:8002/metrics
```

returned:

```text
HTTP/1.1 404 Not Found
```

Meanwhile:

```bash
curl http://127.0.0.1:8002/healthz
```

returned:

```json
{"status":"ok"}
```

and:

```bash
curl http://127.0.0.1:8002/readyz
```

returned:

```json
{"status":"ready"}
```

---

## Investigation

The application was checked for the Prometheus dependency:

```bash
grep -n "prometheus" app/requirements.txt
```

The dependency was:

```text
prometheus-fastapi-instrumentator==7.1.0
```

The application was then checked:

```bash
grep -n "Instrumentator" app/main.py
```

The expected configuration was:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

---

## Root Cause

The request was being sent to an application instance that did not yet contain the metrics configuration.

After restarting the correct application instance with the updated code, `/metrics` became available.

Verification:

```bash
curl -s http://127.0.0.1:8008/metrics
```

returned Prometheus metrics such as:

```text
python_info
process_virtual_memory_bytes
process_resident_memory_bytes
process_cpu_seconds_total
http_requests_total
```

---

# 10. Metrics Verification

Check:

```bash
curl -s \
  http://127.0.0.1:8008/metrics | \
  head -30
```

Check HTTP metrics:

```bash
curl -s \
  http://127.0.0.1:8008/metrics | \
  grep http_requests
```

Expected:

```text
# HELP http_requests_total
# TYPE http_requests_total counter
```

---

# 11. FastAPI Deprecation Warning

Tests initially produced:

```text
DeprecationWarning:
on_event is deprecated,
use lifespan event handlers instead.
```

The original application used:

```python
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
```

---

## Fix

The application was migrated to FastAPI lifespan handling:

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
```

Then:

```python
app = FastAPI(
    title="Fluid AI DevOps Challenge",
    lifespan=lifespan,
)
```

The deprecated `@app.on_event("startup")` implementation was removed.

---

## Verification

Run:

```bash
pytest -q
```

The tests completed without the previous deprecation warnings.

---

# 12. Metrics Test

A dedicated test was added:

```python
def test_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
```

Run:

```bash
pytest -q
```

This verifies that application metrics are exposed.

---

# 13. Kubernetes Monitoring CRD Error

When installing `kube-prometheus-stack` with CRDs not yet installed, Helm produced errors similar to:

```text
resource mapping not found

no matches for kind "Alertmanager"

no matches for kind "Prometheus"

no matches for kind "PrometheusRule"

ensure CRDs are installed first
```

---

## Root Cause

The Helm chart attempted to create resources such as:

```text
Prometheus
Alertmanager
PrometheusRule
```

but Kubernetes did not yet know those resource types.

They are provided by the Prometheus Operator CRDs.

---

# 14. Installing Prometheus Operator CRDs

The CRDs were installed through the Helm chart:

```bash
helm upgrade --install monitoring-crds \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set grafana.enabled=false \
  --set prometheus.enabled=false \
  --set alertmanager.enabled=false \
  --set kubeStateMetrics.enabled=false \
  --set nodeExporter.enabled=false \
  --skip-crds=false
```

Verify:

```bash
kubectl get crd | grep monitoring.coreos.com
```

Expected resource types include:

```text
alertmanagerconfigs
alertmanagers
podmonitors
probes
prometheusagents
prometheuses
prometheusrules
scrapeconfigs
servicemonitors
thanosrulers
```

---

# 15. Understanding the CRD Problem

The important dependency is:

```text
Kubernetes API
      │
      ▼
Prometheus Operator CRDs
      │
      ▼
Prometheus / Alertmanager / ServiceMonitor resources
      │
      ▼
Prometheus Operator
```

Without the CRDs, Kubernetes cannot accept those custom resources.

---

# 16. Helm Download Timeout

During a later Helm upgrade, the command:

```bash
helm upgrade monitoring-crds \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values k8s/monitoring/prometheus-values.yaml \
  --dry-run
```

failed with:

```text
context deadline exceeded
(Client.Timeout exceeded while awaiting headers)
```

The error occurred while downloading the chart archive from GitHub release assets.

---

## Root Cause

This was a chart download/network timeout rather than a Kubernetes resource configuration problem.

---

## Fix

The chart archive was obtained locally and the upgrade was performed using the local package:

```bash
helm upgrade monitoring-crds \
  ./kube-prometheus-stack-88.2.0.tgz \
  --namespace monitoring \
  --values k8s/monitoring/prometheus-values.yaml
```

The upgrade succeeded:

```text
Release "monitoring-crds" has been upgraded.
STATUS: deployed
REVISION: 2
```

---

# 17. Monitoring Pods Initially Not Ready

Immediately after installing the full monitoring stack:

```bash
kubectl get pods -n monitoring
```

showed:

```text
PodInitializing
ContainerCreating
```

for Prometheus, Alertmanager, and Grafana.

---

## Interpretation

This was not automatically a failure.

The monitoring stack contains multiple components that need to:

* create containers
* mount volumes
* pull images
* initialize configuration
* start dependent processes

After waiting for initialization, the Pods became:

```text
2/2 Running
3/3 Running
1/1 Running
```

---

# 18. Monitoring Stack Verification

Use:

```bash
kubectl get pods -n monitoring
```

Final healthy state:

```text
alertmanager-...       2/2 Running
grafana-...            3/3 Running
operator-...           1/1 Running
kube-state-metrics...  1/1 Running
node-exporter-...      1/1 Running
prometheus-...         2/2 Running
```

---

# 19. Prometheus Had No Application Metrics

A major monitoring issue occurred when:

```promql
http_requests_total
```

returned:

```text
result: []
```

Prometheus itself was working.

For example:

```promql
up
```

returned healthy Kubernetes monitoring targets.

Therefore the problem was specifically with backend metric discovery.

---

# 20. ServiceMonitor Investigation

The ServiceMonitor was checked:

```bash
kubectl describe servicemonitor \
  fluid-ai-backend \
  -n monitoring
```

Configuration:

```text
Endpoint:
  /metrics

Interval:
  15s

Port:
  http

Namespace:
  fluid-ai

Selector:
  app=backend
```

This looked correct.

The next step was to inspect the Kubernetes Service.

---

# 21. ServiceMonitor Requires a Service

The ServiceMonitor does not directly select Pods.

The relationship is:

```text
ServiceMonitor
      │
      ▼
Kubernetes Service
      │
      ▼
Pods
```

Therefore both the ServiceMonitor and Service configuration must be correct.

---

# 22. Backend Service Selector

The backend Service had:

```yaml
selector:
  app: backend
```

This selects backend Pods.

Verify:

```bash
kubectl get svc backend \
  -n fluid-ai \
  -o custom-columns='NAME:.metadata.name,SELECTOR:.spec.selector'
```

Expected:

```text
NAME      SELECTOR
backend   map[app:backend]
```

---

# 23. ServiceMonitor Selector vs Service Selector

This distinction caused confusion during troubleshooting.

The Service selector:

```yaml
selector:
  app: backend
```

means:

```text
Service → Pods
```

The ServiceMonitor selector:

```yaml
selector:
  matchLabels:
    app: backend
```

means:

```text
ServiceMonitor → Service
```

They operate at different levels.

---

# 24. Backend Service Label

The backend Service needed:

```yaml
metadata:
  labels:
    app: backend
```

Verify:

```bash
kubectl get svc backend \
  -n fluid-ai \
  --show-labels
```

Expected:

```text
backend   ...   app=backend
```

---

# 25. Named Service Port

The ServiceMonitor used:

```yaml
port: http
```

Therefore the Kubernetes Service needed a port named `http`.

The final configuration:

```yaml
ports:
  - name: http
    port: 8000
    targetPort: 8000
```

Verify:

```bash
kubectl get svc backend \
  -n fluid-ai \
  -o yaml
```

---

# 26. Prometheus ServiceMonitor Selector

The Prometheus instance used:

```yaml
serviceMonitorSelector:
  matchLabels:
    release: monitoring-crds
```

Therefore the backend ServiceMonitor needed:

```yaml
metadata:
  labels:
    release: monitoring-crds
```

Verify:

```bash
kubectl get servicemonitor fluid-ai-backend \
  -n monitoring \
  -o jsonpath='{.metadata.labels}{"\n"}'
```

Expected:

```text
release=monitoring-crds
```

---

# 27. Final Monitoring Fix

The complete discovery chain became:

```text
Prometheus
    │
    │ release=monitoring-crds
    ▼
ServiceMonitor
    │
    │ namespace=fluid-ai
    │ app=backend
    ▼
Backend Service
    │
    │ selector app=backend
    ▼
Backend Pods
    │
    │ :8000/metrics
    ▼
FastAPI metrics
```

---

# 28. Verify Backend Target

After fixing the Service and ServiceMonitor:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool
```

The result contained both backend replicas with:

```text
value: "1"
```

This confirmed that Prometheus was successfully scraping the backend.

---

# 29. Verify HTTP Metrics

Query:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool
```

The result contained metrics for endpoints such as:

```text
/healthz
/readyz
/metrics
```

with labels such as:

```text
job
namespace
pod
service
instance
handler
method
status
```

---

# 30. Git-SHA Image Verification

The CI/CD pipeline builds images using the Git commit SHA.

For example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:<commit-sha>
```

The deployment can be verified with:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

This is important because:

```text
latest
```

does not tell you exactly which source revision is running.

A commit SHA does.

---

# 31. Rollout History

Check deployment revisions:

```bash
kubectl rollout history deployment/backend \
  -n fluid-ai
```

Example:

```text
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
3         <none>
4         <none>
5         <none>
```

The revisions confirm that Kubernetes has recorded multiple Deployment updates.

---

# 32. Rollout Status

Always verify the rollout after deployment:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

Expected:

```text
deployment "backend" successfully rolled out
```

---

# 33. Rollback

If a deployment is unhealthy:

```bash
kubectl rollout undo \
  deployment/backend \
  -n fluid-ai
```

Then:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

Verify the resulting image:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

---

# 34. CI/CD Verification

After a Git push, verify GitHub Actions.

Check the workflow:

```text
CI/CD
```

Confirm:

```text
Test Application
Build and Push Image
Deploy to Kubernetes
```

All jobs should succeed before considering the deployment complete.

---

# 35. GitHub Actions Warning

The CI/CD run displayed warnings related to:

```text
Node.js 20 is deprecated
```

The actions involved included:

```text
actions/checkout
actions/setup-python
docker/build-push-action
docker/login-action
```

The workflow still succeeded.

This should be treated as technical debt to address in a future maintenance pass rather than as a failed deployment.

---

# 36. Test Before Deployment

Run tests locally:

```bash
pytest -q
```

Then:

```bash
git diff --check
```

Then inspect:

```bash
git status
```

This creates a basic quality gate before committing.

---

# 37. Kubernetes YAML Validation

Before applying Kubernetes manifests:

```bash
kubectl apply \
  --dry-run=client \
  -f k8s/backend.yaml
```

For monitoring:

```bash
kubectl apply \
  --dry-run=client \
  -f k8s/monitoring/backend-servicemonitor.yaml
```

This catches many manifest syntax/configuration errors before changing the cluster.

---

# 38. Idempotent `kubectl apply`

Running:

```bash
kubectl apply -f k8s/backend.yaml
```

again should produce:

```text
deployment.apps/backend unchanged
service/backend unchanged
```

Similarly:

```bash
kubectl apply \
  -f k8s/monitoring/backend-servicemonitor.yaml
```

can produce:

```text
servicemonitor.monitoring.coreos.com/fluid-ai-backend unchanged
```

This is expected behavior.

---

# 39. Application Smoke Tests

After deployment:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8002:8000
```

Then:

```bash
curl -s http://127.0.0.1:8002/healthz
```

Expected:

```json
{"status":"ok"}
```

Readiness:

```bash
curl -s http://127.0.0.1:8002/readyz
```

Expected:

```json
{"status":"ready"}
```

Items:

```bash
curl -s http://127.0.0.1:8002/items
```

Expected:

```json
[]
```

or the currently stored items.

Metrics:

```bash
curl -s http://127.0.0.1:8002/metrics
```

Expected Prometheus-formatted output.

---

# 40. End-to-End Troubleshooting Checklist

When a deployment fails, use this sequence.

### Step 1 — Check Pods

```bash
kubectl get pods -n fluid-ai
```

### Step 2 — Check Pod events

```bash
kubectl describe pod <pod> -n fluid-ai
```

### Step 3 — Check logs

```bash
kubectl logs <pod> -n fluid-ai
```

### Step 4 — Check Deployment

```bash
kubectl describe deployment backend -n fluid-ai
```

### Step 5 — Check image

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

### Step 6 — Check Service

```bash
kubectl get svc backend -n fluid-ai -o yaml
```

### Step 7 — Check endpoints

```bash
kubectl get endpoints backend -n fluid-ai
```

### Step 8 — Test application

```bash
curl http://127.0.0.1:8002/healthz
```

### Step 9 — Check monitoring

```bash
kubectl get servicemonitor -n monitoring
```

### Step 10 — Check Prometheus

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}'
```

---

# 41. Troubleshooting Decision Tree

```text
Deployment failed?
       │
       ▼
kubectl get pods
       │
       ├── ImagePullBackOff
       │       └── Check registry/auth/image tag
       │
       ├── CrashLoopBackOff
       │       └── Check application logs/config/database
       │
       ├── Pending
       │       └── Check scheduling/events/resources
       │
       └── Running
               │
               ▼
          Check healthz
               │
               ├── 500/failed
               │       └── Application problem
               │
               └── 200
                       │
                       ▼
                  Check readyz
                       │
                       ├── 503
                       │       └── Dependency/database problem
                       │
                       └── 200
                               │
                               ▼
                         Check Service
                               │
                               ▼
                         Check /metrics
                               │
                               ▼
                       Check ServiceMonitor
                               │
                               ▼
                         Check Prometheus
```

---

# 42. Key Lessons

## Lesson 1 — Debug from the bottom up

Do not assume Kubernetes is the problem.

First verify:

```text
Application → Container → Pod → Service → Monitoring
```

---

## Lesson 2 — Read the exact error

For example:

```text
password authentication failed
```

means something different from:

```text
connection refused
```

---

## Lesson 3 — Kubernetes resources have relationships

A ServiceMonitor depends on:

```text
Service
   ↓
Service labels
   ↓
Service port
   ↓
Pod selector
```

---

## Lesson 4 — Prometheus discovery has selectors

The Prometheus instance must select the ServiceMonitor.

The ServiceMonitor must select the Service.

The Service must select the Pods.

---

## Lesson 5 — Health and readiness are different

A running process is not necessarily ready to serve traffic.

---

## Lesson 6 — Git SHA images improve traceability

Use:

```text
commit SHA
```

instead of relying only on:

```text
latest
```

---

## Lesson 7 — Verify the final state

A successful command is not enough.

Always verify:

```text
Deployment
→ Pod
→ Service
→ Application
→ Metrics
→ Prometheus
```

---

# 43. Quick Command Reference

## Application

```bash
pytest -q

git diff --check
```

## Kubernetes

```bash
kubectl get nodes
kubectl get pods -A
kubectl get pods -n fluid-ai
kubectl get svc -n fluid-ai
kubectl get deployments -n fluid-ai
kubectl rollout status deployment/backend -n fluid-ai
kubectl rollout history deployment/backend -n fluid-ai
```

## Logs

```bash
kubectl logs <pod> -n fluid-ai
kubectl logs <pod> -n fluid-ai --previous
```

## Port Forwarding

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8002:8000
```

PostgreSQL:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/postgres \
  15432:5432
```

Prometheus:

```bash
kubectl port-forward \
  -n monitoring \
  service/monitoring-crds-kube-prome-prometheus \
  9090:9090
```

Grafana:

```bash
kubectl port-forward \
  -n monitoring \
  service/monitoring-crds-grafana \
  3000:80
```

## Monitoring

```bash
kubectl get pods -n monitoring
kubectl get prometheus -n monitoring
kubectl get alertmanager -n monitoring
kubectl get servicemonitor -n monitoring
kubectl get crd | grep monitoring.coreos.com
```

## Prometheus

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up'

curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}'

curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total'
```

---

# 44. Final Validation

Before considering a troubleshooting investigation complete:

```text
[ ] Root cause identified
[ ] Error reproduced
[ ] Minimal fix applied
[ ] Application tested
[ ] Kubernetes resource tested
[ ] Deployment verified
[ ] Pods healthy
[ ] Service healthy
[ ] Health endpoint works
[ ] Readiness endpoint works
[ ] Metrics endpoint works
[ ] Prometheus target is UP
[ ] Prometheus metric is queryable
[ ] Git diff is clean
[ ] Documentation updated
```

---

# 45. Related Documentation

* `README.md` — Project introduction and quick start
* `docs/01-project-overview.md` — Project scope
* `docs/02-architecture.md` — Architecture
* `docs/03-local-setup.md` — Local setup
* `docs/04-kubernetes-deployment.md` — Kubernetes deployment
* `docs/05-cicd-pipeline.md` — CI/CD
* `docs/06-monitoring-observability.md` — Monitoring
* `docs/07-troubleshooting.md` — This document
* `docs/08-operations-runbook.md` — Day-2 operations
