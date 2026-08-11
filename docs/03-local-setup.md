# Fluid AI DevOps Challenge — Local Setup & Development Guide

This document describes how to set up the project locally, install dependencies, configure PostgreSQL, run the FastAPI application, execute tests, build the Docker image, and verify the application.

---

## 1. Prerequisites

The development environment requires:

* Linux/macOS/WSL environment
* Python 3.10+
* `pip`
* `venv`
* PostgreSQL
* Docker
* Git
* `kubectl` for Kubernetes development
* Kind for the local Kubernetes cluster
* Helm for Kubernetes package management

Verify the basic tools:

```bash
python3 --version
pip --version
git --version
docker --version
kubectl version --client
helm version
```

---

# 2. Clone the Repository

Clone the project:

```bash
git clone https://github.com/Upshivam786/kubernetes-cicd-production-demo.git
cd kubernetes-cicd-production-demo
```

For an existing checkout:

```bash
cd ~/fluid-ai-devops-challenge
```

---

# 3. Create the Python Virtual Environment

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

After activation, the shell should show:

```text
(.venv)
```

Example:

```text
(.venv) user@user:~/fluid-ai-devops-challenge$
```

---

# 4. Install Python Dependencies

Install the application dependencies:

```bash
pip install --upgrade pip
pip install -r app/requirements.txt
```

The requirements include the FastAPI application dependencies as well as testing and Prometheus instrumentation packages.

Prometheus instrumentation is provided by:

```text
prometheus-fastapi-instrumentator==7.1.0
```

---

# 5. Project Python Dependencies

The application uses the following important packages:

| Package                           | Purpose                   |
| --------------------------------- | ------------------------- |
| FastAPI                           | REST API framework        |
| Uvicorn                           | ASGI application server   |
| SQLAlchemy                        | Database ORM              |
| psycopg2-binary                   | PostgreSQL driver         |
| pydantic-settings                 | Application configuration |
| pytest                            | Automated testing         |
| httpx                             | HTTP client used by tests |
| prometheus-fastapi-instrumentator | Prometheus metrics        |

---

# 6. PostgreSQL Configuration

The FastAPI application requires PostgreSQL.

The application reads database configuration using environment variables.

The main variables are:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
```

A local development configuration can look like:

```bash
export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_NAME=appdb
export DB_USER=appuser
export DB_PASSWORD='appsecret'
```

The exact values must match the PostgreSQL instance being used.

---

# 7. PostgreSQL Through Kubernetes Port Forwarding

During Kubernetes development, PostgreSQL can be accessed locally through `kubectl port-forward`.

The PostgreSQL Service runs inside the `fluid-ai` namespace.

Start the port forward:

```bash
kubectl port-forward -n fluid-ai service/postgres 15432:5432
```

This creates:

```text
Local machine
127.0.0.1:15432
       |
       ▼
kubectl port-forward
       |
       ▼
Kubernetes Service/postgres
       |
       ▼
PostgreSQL :5432
```

The application can then be started locally using:

```bash
DB_HOST=127.0.0.1 \
DB_PORT=15432 \
DB_NAME=appdb \
DB_USER=appuser \
DB_PASSWORD='appsecret' \
uvicorn app.main:app --host 127.0.0.1 --port 8008
```

---

# 8. Start the FastAPI Application

With the required database available, start the application:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If port `8000` is already in use, use another local port:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8008
```

The application will be available at:

```text
http://127.0.0.1:8008
```

---

# 9. FastAPI Endpoints

The application exposes the following important endpoints.

## Health

```http
GET /healthz
```

Expected response:

```json
{
  "status": "ok"
}
```

Test:

```bash
curl -s http://127.0.0.1:8008/healthz
```

---

## Readiness

```http
GET /readyz
```

The readiness endpoint checks database connectivity.

Test:

```bash
curl -s http://127.0.0.1:8008/readyz
```

Expected healthy response:

```json
{
  "status": "ready"
}
```

If the database is unavailable, the endpoint returns HTTP `503`.

---

## List Items

```http
GET /items
```

Test:

```bash
curl -s http://127.0.0.1:8008/items
```

---

## Create Item

```http
POST /items
```

The endpoint accepts an item name.

Example:

```bash
curl -X POST \
  "http://127.0.0.1:8008/items?name=test-item"
```

---

## Prometheus Metrics

```http
GET /metrics
```

Test:

```bash
curl -s http://127.0.0.1:8008/metrics
```

The endpoint exposes Prometheus-compatible metrics.

For example:

```text
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{...} 1.0
```

Application request metrics include:

```text
http_requests_total
```

---

# 10. Running Tests

The project uses pytest.

Run all tests:

```bash
pytest -q
```

A successful run should report all tests passing.

Example:

```text
2 passed
```

The health test verifies:

```text
GET /healthz
```

The metrics test verifies:

```text
GET /metrics
```

and checks that:

```text
http_requests_total
```

is present.

---

# 11. Test Configuration

The health tests define local database environment defaults before importing the application.

The test configuration includes:

```text
DB_HOST=localhost
DB_PORT=5432
DB_NAME=testdb
DB_USER=testuser
DB_PASSWORD=testpassword
```

This allows the test suite to load the application configuration without depending on production Kubernetes secrets.

---

# 12. FastAPI Lifespan

The application initializes database tables through FastAPI's lifespan mechanism.

The application uses:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
```

This replaces the deprecated:

```python
@app.on_event("startup")
```

approach.

Using the lifespan mechanism avoids the FastAPI deprecation warning that was encountered during testing.

---

# 13. Prometheus Instrumentation

The application integrates:

```python
from prometheus_fastapi_instrumentator import Instrumentator
```

Metrics are enabled with:

```python
Instrumentator().instrument(app).expose(app)
```

This creates the:

```text
/metrics
```

endpoint.

After starting the application:

```bash
curl -s http://127.0.0.1:8008/metrics
```

To inspect HTTP request metrics:

```bash
curl -s http://127.0.0.1:8008/metrics | grep http_requests
```

---

# 14. Local Metrics Verification

A successful metrics response contains standard Python process metrics such as:

```text
python_gc_objects_collected_total
python_info
process_virtual_memory_bytes
process_resident_memory_bytes
process_cpu_seconds_total
```

It also contains application HTTP metrics:

```text
http_requests_total
http_requests_created
```

For example:

```text
http_requests_total{
    handler="/healthz",
    method="GET",
    status="2xx"
}
```

This confirms that application-level Prometheus instrumentation is active.

---

# 15. Docker Build

The project includes a Dockerfile.

Build the image:

```bash
docker build -t fluid-ai-backend:dev .
```

Verify the image:

```bash
docker images | grep fluid-ai
```

---

# 16. Kubernetes Local Development

The project uses Kind for local Kubernetes development.

Verify the cluster:

```bash
kubectl get nodes
```

Example:

```text
NAME                    STATUS
fluid-ai-control-plane  Ready
```

Check all namespaces:

```bash
kubectl get namespaces
```

The project uses:

```text
fluid-ai
```

for application resources.

---

# 17. Kubernetes Application Deployment

The main Kubernetes application manifest is:

```text
k8s/backend.yaml
```

Apply it:

```bash
kubectl apply -f k8s/backend.yaml
```

Validate without changing the cluster:

```bash
kubectl apply --dry-run=client -f k8s/backend.yaml
```

Expected result is similar to:

```text
deployment.apps/backend configured (dry run)
service/backend configured (dry run)
```

---

# 18. Verify Backend Deployment

Check the Deployment:

```bash
kubectl get deployment backend -n fluid-ai
```

Check Pods:

```bash
kubectl get pods -n fluid-ai -l app=backend
```

Expected state:

```text
READY   STATUS
1/1     Running
1/1     Running
```

Check the rollout:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Expected:

```text
deployment "backend" successfully rolled out
```

---

# 19. Verify the Deployed Image

To see the exact image currently deployed:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:<git-sha>
```

The Git SHA allows the running application version to be mapped directly to a Git commit.

---

# 20. Access the Backend Service Locally

The backend Service is a ClusterIP Service.

Verify it:

```bash
kubectl get svc backend -n fluid-ai
```

Port-forward it:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

The local endpoint becomes:

```text
http://127.0.0.1:8002
```

Test health:

```bash
curl -s http://127.0.0.1:8002/healthz
```

Test readiness:

```bash
curl -s http://127.0.0.1:8002/readyz
```

Test metrics:

```bash
curl -s http://127.0.0.1:8002/metrics
```

---

# 21. Avoiding Local Port Conflicts

If a port is already being used, `kubectl port-forward` will fail with an error similar to:

```text
bind: address already in use
```

Do not necessarily terminate the existing process.

Use another local port.

For example:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

or:

```bash
kubectl port-forward -n fluid-ai service/backend 8008:8000
```

The format is:

```text
<local-port>:<service-port>
```

The Kubernetes Service continues to listen on port `8000`; only the local forwarding port changes.

---

# 22. Kubernetes Database Verification

Check the PostgreSQL Pod:

```bash
kubectl get pods -n fluid-ai
```

Check the PostgreSQL Service:

```bash
kubectl get svc postgres -n fluid-ai
```

Expected Service port:

```text
5432/TCP
```

Port-forward PostgreSQL when required:

```bash
kubectl port-forward -n fluid-ai service/postgres 15432:5432
```

---

# 23. Monitoring Installation

The monitoring stack uses:

```text
kube-prometheus-stack
```

managed with Helm.

The monitoring namespace is:

```text
monitoring
```

Create it if necessary:

```bash
kubectl create namespace monitoring
```

Verify:

```bash
kubectl get namespace monitoring
```

---

# 24. Monitoring Components

The monitoring stack provides:

```text
Prometheus
Grafana
Alertmanager
Prometheus Operator
kube-state-metrics
Node Exporter
```

Check:

```bash
kubectl get pods -n monitoring
```

A healthy installation should eventually show the monitoring Pods as:

```text
Running
```

---

# 25. Prometheus Custom Resources

The Prometheus Operator uses Kubernetes CRDs.

Verify them:

```bash
kubectl get crd | grep monitoring.coreos.com
```

Important resources include:

```text
alertmanagers.monitoring.coreos.com
prometheuses.monitoring.coreos.com
prometheusrules.monitoring.coreos.com
servicemonitors.monitoring.coreos.com
podmonitors.monitoring.coreos.com
```

---

# 26. Backend ServiceMonitor

The application monitoring configuration is:

```text
k8s/monitoring/backend-servicemonitor.yaml
```

Apply it:

```bash
kubectl apply \
  -f k8s/monitoring/backend-servicemonitor.yaml
```

Validate:

```bash
kubectl apply --dry-run=client \
  -f k8s/monitoring/backend-servicemonitor.yaml
```

Verify:

```bash
kubectl get servicemonitor fluid-ai-backend -n monitoring
```

---

# 27. ServiceMonitor Configuration

The backend ServiceMonitor uses:

```text
Namespace:
fluid-ai

Service selector:
app=backend

Port:
http

Path:
/metrics

Interval:
15s
```

This means Prometheus discovers the backend Service and scrapes:

```text
http://<backend-endpoint>:8000/metrics
```

every 15 seconds.

---

# 28. Verify Prometheus Targets

Port-forward Prometheus:

```bash
kubectl port-forward -n monitoring \
  service/monitoring-crds-kube-prome-prometheus 9090:9090
```

Prometheus becomes available at:

```text
http://127.0.0.1:9090
```

Query target health:

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool
```

A healthy backend replica should have:

```text
"1"
```

as the value of the `up` metric.

With two replicas, two healthy backend targets should normally appear.

---

# 29. Verify Application Metrics in Prometheus

Query:

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool
```

Successful results contain labels such as:

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

Example job:

```text
job="backend"
```

Example service:

```text
service="backend"
```

Example namespace:

```text
namespace="fluid-ai"
```

---

# 30. Useful PromQL Queries

### Backend availability

```promql
up{job="backend"}
```

### Total HTTP requests

```promql
http_requests_total{job="backend"}
```

### Requests by endpoint

```promql
sum by (handler) (
  http_requests_total{job="backend"}
)
```

### Requests per second

```promql
rate(http_requests_total{job="backend"}[5m])
```

### Backend target count

```promql
count(up{job="backend"})
```

### Healthy backend target count

```promql
count(up{job="backend"} == 1)
```

---

# 31. Grafana Access

Find the Grafana Pod:

```bash
kubectl get pods -n monitoring
```

Port-forward Grafana:

```bash
kubectl port-forward -n monitoring \
  service/monitoring-crds-grafana 3000:80
```

Then access:

```text
http://127.0.0.1:3000
```

Grafana uses Prometheus as its metrics data source.

---

# 32. Git Workflow

Before committing changes:

```bash
git status
```

Check formatting:

```bash
git diff --check
```

Review changes:

```bash
git diff
```

Stage:

```bash
git add .
```

Review staged changes:

```bash
git diff --cached
```

Commit:

```bash
git commit -m "docs: add project documentation"
```

Push:

```bash
git push
```

---

# 33. Recommended Local Verification Sequence

For normal development, the following sequence provides a quick validation:

```bash
source .venv/bin/activate

pytest -q

git diff --check

kubectl get nodes

kubectl get pods -n fluid-ai

kubectl get deployment backend -n fluid-ai

kubectl rollout status deployment/backend -n fluid-ai

kubectl get svc -n fluid-ai
```

For monitoring:

```bash
kubectl get pods -n monitoring

kubectl get servicemonitor -n monitoring

kubectl get prometheus -n monitoring

kubectl get alertmanager -n monitoring
```

---

# 34. Clean Working Tree Check

Before finishing a change:

```bash
git status
```

The desired state is:

```text
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

If new documentation or Kubernetes files are intentionally being added, they should appear as expected before staging.

---

# 35. Development Troubleshooting Quick Reference

| Problem                 | First command                                           |
| ----------------------- | ------------------------------------------------------- |
| Tests fail              | `pytest -q`                                             |
| Formatting issue        | `git diff --check`                                      |
| Pod not running         | `kubectl get pods -n fluid-ai`                          |
| Pod crash               | `kubectl logs <pod> -n fluid-ai`                        |
| Deployment issue        | `kubectl describe deployment backend -n fluid-ai`       |
| Rollout issue           | `kubectl rollout status deployment/backend -n fluid-ai` |
| Service issue           | `kubectl get svc -n fluid-ai`                           |
| Service endpoints       | `kubectl get endpoints -n fluid-ai`                     |
| Health check            | `curl http://127.0.0.1:<port>/healthz`                  |
| Readiness check         | `curl http://127.0.0.1:<port>/readyz`                   |
| Metrics check           | `curl http://127.0.0.1:<port>/metrics`                  |
| Prometheus target issue | `kubectl get servicemonitor -n monitoring`              |
| Prometheus query        | `curl http://127.0.0.1:9090/api/v1/query`               |
| Monitoring Pod issue    | `kubectl get pods -n monitoring`                        |
| Port conflict           | `sudo lsof -i :<port>`                                  |

---

# 36. Local Development Philosophy

The project intentionally supports validation at multiple layers:

```text
Python tests
     ↓
Application startup
     ↓
FastAPI endpoints
     ↓
Docker image
     ↓
Kubernetes Deployment
     ↓
Kubernetes Service
     ↓
Health/readiness checks
     ↓
Prometheus metrics
     ↓
Monitoring targets
```

This makes it possible to isolate failures early rather than discovering every problem only after deployment.

---

# 37. Final Local Setup Checklist

Before considering the local environment ready:

```text
[ ] Repository cloned
[ ] Python virtual environment created
[ ] Virtual environment activated
[ ] Python dependencies installed
[ ] PostgreSQL available
[ ] Database environment variables configured
[ ] FastAPI starts successfully
[ ] /healthz returns 200
[ ] /readyz returns 200
[ ] /items responds
[ ] /metrics returns Prometheus metrics
[ ] pytest passes
[ ] Docker image builds
[ ] Kind cluster is available
[ ] Kubernetes backend is running
[ ] Backend Service is available
[ ] Prometheus is running
[ ] ServiceMonitor exists
[ ] Backend target reports up=1
[ ] Grafana is accessible
```

---

# 38. Related Documentation

Additional project documentation:

* `README.md` — Project introduction and quick start
* `docs/01-project-overview.md` — Project goals, scope, and components
* `docs/02-architecture.md` — Detailed architecture and component interactions
* `docs/03-local-setup.md` — Local development and setup
* `docs/04-kubernetes-deployment.md` — Kubernetes deployment procedure
* `docs/05-cicd-pipeline.md` — GitHub Actions CI/CD workflow
* `docs/06-monitoring-observability.md` — Prometheus, Grafana, and ServiceMonitor
* `docs/07-troubleshooting.md` — Troubleshooting guide and failure scenarios
* `docs/08-operations-runbook.md` — Day-2 operational commands
