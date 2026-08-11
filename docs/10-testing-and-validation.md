# Fluid AI DevOps Challenge — Testing & Validation

## 1. Purpose

This document describes how the Fluid AI DevOps Challenge is tested and how deployment correctness is validated.

The validation strategy covers:

* Application tests
* API health checks
* Readiness checks
* Metrics endpoint
* Database connectivity
* Docker image validation
* Kubernetes deployment validation
* CI/CD validation
* Kubernetes rollout validation
* Prometheus scraping validation
* Smoke testing
* Release verification
* Rollback validation

The objective is to ensure that a change is not considered successfully deployed merely because Kubernetes created a Pod.

A successful deployment should satisfy multiple validation layers.

---

# 2. Validation Strategy

The project follows this flow:

```text
Code Change
    │
    ▼
Unit/API Tests
    │
    ▼
Docker Build
    │
    ▼
Container Image
    │
    ▼
Kubernetes Deployment
    │
    ▼
Readiness
    │
    ▼
Rollout
    │
    ▼
Smoke Test
    │
    ▼
Metrics
    │
    ▼
Prometheus Scraping
```

Each layer catches a different class of failure.

---

# 3. Test Categories

| Test                  | Purpose                       |
| --------------------- | ----------------------------- |
| Unit/API test         | Validate application behavior |
| Health test           | Validate liveness endpoint    |
| Readiness test        | Validate database readiness   |
| Metrics test          | Validate Prometheus endpoint  |
| Docker test           | Validate container packaging  |
| Kubernetes validation | Validate manifests            |
| Rollout test          | Validate Pod replacement      |
| Smoke test            | Validate live application     |
| Prometheus query      | Validate monitoring           |
| Image verification    | Validate release identity     |
| Rollback test         | Validate recovery capability  |

---

# 4. Python Test Environment

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Verify Python:

```bash
python --version
```

Verify pytest:

```bash
pytest --version
```

Install application dependencies:

```bash
pip install -r app/requirements.txt
```

---

# 5. Running the Test Suite

Run:

```bash
pytest -q
```

A successful run should report all tests passing.

Example:

```text
2 passed
```

The exact number may increase as additional tests are added.

---

# 6. Current Application Tests

The project currently validates at least:

```text
/healthz
/metrics
```

The health test verifies:

```json
{
  "status": "ok"
}
```

The metrics test verifies that Prometheus metrics are exposed and include:

```text
http_requests_total
```

---

# 7. Health Check Test

The application health endpoint is:

```text
GET /healthz
```

Test manually:

```bash
curl -i http://127.0.0.1:8002/healthz
```

Expected:

```text
HTTP/1.1 200 OK
```

and:

```json
{"status":"ok"}
```

---

# 8. Readiness Check

The readiness endpoint is:

```text
GET /readyz
```

Test:

```bash
curl -i http://127.0.0.1:8002/readyz
```

Expected:

```json
{"status":"ready"}
```

The readiness check verifies that the application can communicate with PostgreSQL.

This makes it different from `/healthz`.

---

# 9. Health vs Readiness

### Liveness

```text
/healthz
```

Answers:

> Is the application process alive?

### Readiness

```text
/readyz
```

Answers:

> Is the application ready to serve traffic?

Conceptually:

```text
healthz
   │
   └── Application process healthy

readyz
   │
   ├── Application running
   └── Database reachable
```

---

# 10. Kubernetes Probes

The backend Deployment configures:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: http
```

and:

```yaml
readinessProbe:
  httpGet:
    path: /readyz
    port: http
```

This allows Kubernetes to make automated health decisions.

---

# 11. Inspect Kubernetes Probes

Run:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o yaml
```

Search:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o yaml | grep -A15 -B3 livenessProbe
```

And:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o yaml | grep -A15 -B3 readinessProbe
```

---

# 12. Metrics Test

The application exposes:

```text
/metrics
```

Test:

```bash
curl -s http://127.0.0.1:8002/metrics
```

Search for request metrics:

```bash
curl -s http://127.0.0.1:8002/metrics \
  | grep http_requests
```

Expected metrics include:

```text
http_requests_total
http_requests_created
```

---

# 13. Prometheus Metrics Validation

The application uses:

```text
prometheus-fastapi-instrumentator
```

The instrumentator automatically exposes application-level HTTP metrics.

The implementation is configured in:

```text
app/main.py
```

The dependency is defined in:

```text
app/requirements.txt
```

---

# 14. API Functional Test

The application provides:

```text
GET /items
POST /items
```

Test:

```bash
curl -i http://127.0.0.1:8002/items
```

Expected:

```text
HTTP/1.1 200 OK
```

The initial result may be:

```json
[]
```

if no records have been created.

---

# 15. Create Item Test

The application exposes:

```text
POST /items
```

A functional test can be performed using:

```bash
curl -X POST \
  "http://127.0.0.1:8002/items?name=test-item"
```

Then:

```bash
curl http://127.0.0.1:8002/items
```

The created item should be returned.

---

# 16. Database Validation

PostgreSQL runs inside the `fluid-ai` namespace.

Check:

```bash
kubectl get pods -n fluid-ai
```

Expected application components include:

```text
backend
postgres
```

Check the PostgreSQL Service:

```bash
kubectl get service postgres -n fluid-ai
```

---

# 17. Database Connectivity

The backend readiness endpoint performs a database query:

```sql
SELECT 1
```

Therefore:

```bash
curl http://127.0.0.1:8002/readyz
```

is also an indirect database connectivity test.

If PostgreSQL is unavailable, readiness should fail rather than claiming the application is ready.

---

# 18. Docker Validation

Build the application image locally:

```bash
docker build \
  -t fluid-ai-backend:test \
  .
```

Check the image:

```bash
docker images | grep fluid-ai-backend
```

Inspect:

```bash
docker inspect fluid-ai-backend:test
```

---

# 19. Container Runtime Test

Run the image with the required environment configuration.

Example:

```bash
docker run --rm \
  -p 8000:8000 \
  -e DB_HOST=<database-host> \
  -e DB_PORT=5432 \
  -e DB_NAME=<database-name> \
  -e DB_USER=<database-user> \
  -e DB_PASSWORD=<database-password> \
  fluid-ai-backend:test
```

Then test:

```bash
curl http://127.0.0.1:8000/healthz
```

---

# 20. Kubernetes Manifest Validation

Before applying changes:

```bash
kubectl apply \
  --dry-run=client \
  -f k8s/backend.yaml
```

Expected:

```text
deployment.apps/backend configured (dry run)
service/backend unchanged (dry run)
```

This validates that Kubernetes can parse the manifest.

---

# 21. Manifest Formatting Validation

Use:

```bash
git diff --check
```

This catches common whitespace errors before committing.

For the workflow:

```bash
python - <<'PY'
import yaml

with open(".github/workflows/ci.yaml") as f:
    data = yaml.safe_load(f)

print("Workflow YAML: OK")
print("Jobs:", list(data["jobs"].keys()))
PY
```

Expected jobs:

```text
test
build-and-push
deploy
```

---

# 22. Kubernetes Deployment Validation

Check:

```bash
kubectl get deployment backend -n fluid-ai
```

Expected:

```text
READY     UP-TO-DATE     AVAILABLE
2/2       2              2
```

The exact values depend on the configured replica count.

---

# 23. Pod Validation

Run:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend
```

Expected:

```text
READY   STATUS
1/1     Running
```

All expected replicas should be running.

---

# 24. Rollout Validation

After a deployment:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

Expected:

```text
deployment "backend" successfully rolled out
```

This verifies that Kubernetes completed the rolling update.

---

# 25. Image Verification

The Deployment should reference the Git commit SHA.

Run:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8ed2333bfeb03a55c7130bb5061580619d
```

This verifies release identity.

---

# 26. Verify Actual Image Digest

The image configured in the Deployment and the image actually running in the Pod are related but not identical pieces of information.

Check:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend \
  -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

Example:

```text
backend-xxx -> ghcr.io/...@sha256:<digest>
```

This confirms which immutable image digest the container runtime actually pulled.

---

# 27. Kubernetes Service Validation

Check:

```bash
kubectl get service backend -n fluid-ai
```

Expected:

```text
TYPE        CLUSTER-IP
ClusterIP   <internal-ip>
```

The backend Service should target the backend Pods.

Check:

```bash
kubectl get service backend \
  -n fluid-ai \
  -o yaml
```

The selector should contain:

```yaml
selector:
  app: backend
```

---

# 28. Service Endpoint Validation

Check:

```bash
kubectl get endpoints backend -n fluid-ai
```

Or on newer Kubernetes versions:

```bash
kubectl get endpointslices \
  -n fluid-ai \
  -l kubernetes.io/service-name=backend
```

The Service should resolve to healthy backend Pod endpoints.

---

# 29. Local Smoke Test

Use a non-conflicting local port if another application already occupies port 8001.

Example:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8002:8000
```

Then:

```bash
curl http://127.0.0.1:8002/healthz
curl http://127.0.0.1:8002/readyz
curl http://127.0.0.1:8002/items
```

Expected:

```text
/healthz → 200
/readyz  → 200
/items   → 200
```

---

# 30. Port Conflict Handling

If:

```text
Unable to listen on port 8001
address already in use
```

do not necessarily terminate the existing process.

Find another available local port:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8002:8000
```

Then use:

```text
http://127.0.0.1:8002
```

The local port is arbitrary; the Kubernetes Service port remains `8000`.

---

# 31. CI Test Validation

The GitHub Actions workflow contains:

```text
test
build-and-push
deploy
```

The intended pipeline is:

```text
Push to main
     │
     ▼
Test
     │
     ▼
Build & Push
     │
     ▼
Deploy
```

The deployment job depends on the build job.

---

# 32. CI Test Failure Behavior

If tests fail:

```text
test
  │
  └── FAILED
       │
       X
   Build blocked
```

This prevents an invalid application version from reaching the container registry and Kubernetes deployment stage.

---

# 33. Build Validation

The build job publishes:

```text
<image>:<github.sha>
<image>:latest
```

The SHA image is the deployment artifact.

The pipeline should not deploy an image different from the image produced by the same commit.

---

# 34. Deployment Validation

The deployment job:

1. Verifies Kubernetes access.
2. Updates the backend image.
3. Waits for rollout.
4. Verifies the deployed image.
5. Runs a smoke test.

Conceptually:

```text
kubectl access
      │
      ▼
set image
      │
      ▼
rollout status
      │
      ▼
verify image
      │
      ▼
smoke test
```

---

# 35. Smoke Test Validation

The CI/CD smoke test should verify that the deployed application responds successfully.

A basic test is:

```bash
curl -fsS \
  http://127.0.0.1:<port>/healthz
```

The `-f` flag causes curl to fail for HTTP error responses.

The CI job can therefore distinguish:

```text
HTTP 200 → success
HTTP 4xx/5xx → failure
```

---

# 36. Metrics Validation in Kubernetes

After deployment:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8002:8000
```

Then:

```bash
curl -s \
  http://127.0.0.1:8002/metrics \
  | grep http_requests
```

Expected metrics include:

```text
http_requests_total
```

---

# 37. Prometheus Target Validation

Prometheus should discover the backend through the ServiceMonitor.

Check:

```bash
kubectl get servicemonitor \
  fluid-ai-backend \
  -n monitoring
```

The ServiceMonitor should specify:

```text
namespace: fluid-ai
service selector: app=backend
port: http
path: /metrics
interval: 15s
```

---

# 38. Prometheus Target Validation

Query Prometheus:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool
```

Expected:

```text
"result": [
  ...
]
```

with:

```text
"value": [
  <timestamp>,
  "1"
]
```

A value of:

```text
1
```

means the target is currently being scraped successfully.

---

# 39. Application Metric Query

Query:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool
```

Expected labels include:

```text
job
namespace
pod
service
handler
method
status
```

Example:

```text
job="backend"
namespace="fluid-ai"
service="backend"
handler="/healthz"
```

This proves that application metrics have reached Prometheus.

---

# 40. Why `http_requests_total` May Initially Be Empty

Immediately after creating a ServiceMonitor, this query:

```promql
http_requests_total
```

may return no results.

Possible reasons:

```text
ServiceMonitor not discovered
       OR
target not scraped yet
       OR
application metrics endpoint unavailable
       OR
selector mismatch
```

Wait for the configured scrape interval and verify the target.

---

# 41. Monitoring Troubleshooting Validation

If:

```promql
up{job="backend"}
```

returns:

```text
"1"
```

but:

```promql
http_requests_total
```

returns nothing, investigate:

```text
/metrics endpoint
ServiceMonitor
Service selector
Service port name
Prometheus selector
scrape target
```

This exact distinction was useful during the project's monitoring setup.

---

# 42. ServiceMonitor Validation

Check:

```bash
kubectl describe servicemonitor \
  fluid-ai-backend \
  -n monitoring
```

Expected:

```text
Namespace Selector:
  fluid-ai

Selector:
  app: backend

Endpoint:
  Port: http
  Path: /metrics
  Interval: 15s
```

---

# 43. Prometheus Selector Validation

The Prometheus resource uses a ServiceMonitor selector.

Inspect:

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

Therefore the application ServiceMonitor must carry:

```yaml
labels:
  release: monitoring-crds
```

This label is critical for discovery.

---

# 44. End-to-End Monitoring Test

The complete monitoring validation is:

```text
FastAPI
  │
  │ /metrics
  ▼
Backend Service
  │
  ▼
ServiceMonitor
  │
  ▼
Prometheus Operator
  │
  ▼
Prometheus
  │
  ▼
PromQL
```

Validate each layer independently.

---

# 45. Rollback Validation

Kubernetes maintains Deployment revisions.

Check:

```bash
kubectl rollout history \
  deployment/backend \
  -n fluid-ai
```

Example:

```text
REVISION
1
2
3
4
5
```

---

# 46. Rollback Command

If a release must be reverted:

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

Verify:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend
```

---

# 47. Rollback Verification

After rollback:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

The image should correspond to the previous Deployment revision.

Then run:

```bash
curl http://127.0.0.1:8002/healthz
curl http://127.0.0.1:8002/readyz
```

---

# 48. Failure Injection

A production-style system should eventually validate failure behavior deliberately.

Examples:

### Application failure

Terminate a backend Pod:

```bash
kubectl delete pod \
  -n fluid-ai \
  -l app=backend
```

Observe:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend \
  -w
```

Kubernetes should recreate the Pods.

---

# 49. Readiness Failure

A future controlled test can make PostgreSQL unavailable and verify:

```text
/readyz → 503
```

The expected behavior is:

```text
Database unavailable
       │
       ▼
Readiness fails
       │
       ▼
Pod removed from ready endpoints
       │
       ▼
Traffic stops reaching unhealthy Pod
```

This should be tested carefully because it deliberately changes the running environment.

---

# 50. CI/CD Failure Scenarios

The pipeline should eventually validate:

```text
Test failure
Build failure
Registry authentication failure
Kubernetes authentication failure
Image pull failure
Readiness failure
Rollout timeout
Smoke-test failure
```

The expected behavior is that the deployment is considered unsuccessful rather than silently proceeding.

---

# 51. Assignment Validation Matrix

| Requirement           | Validation                   |
| --------------------- | ---------------------------- |
| Application works     | `pytest`, curl               |
| Docker image builds   | `docker build`               |
| Image published       | GHCR                         |
| Kubernetes deployment | `kubectl get deployment`     |
| Multiple replicas     | `kubectl get pods`           |
| Health checks         | `/healthz`                   |
| Readiness checks      | `/readyz`                    |
| Database integration  | `/readyz`, `/items`          |
| Private image pull    | `ghcr-pull-secret`           |
| CI/CD                 | GitHub Actions               |
| SHA deployment        | Deployment image             |
| Rollout               | `kubectl rollout status`     |
| Smoke test            | CI/CD curl                   |
| Metrics               | `/metrics`                   |
| Prometheus            | `up{job="backend"}`          |
| Application metrics   | `http_requests_total`        |
| ServiceMonitor        | `kubectl get servicemonitor` |
| Rollback              | `kubectl rollout undo`       |

---

# 52. Final Pre-Release Validation

Run:

```bash
pytest -q
```

Then:

```bash
git diff --check
```

Validate Kubernetes:

```bash
kubectl apply \
  --dry-run=client \
  -f k8s/backend.yaml
```

Check deployment:

```bash
kubectl get deployment backend -n fluid-ai
```

Check Pods:

```bash
kubectl get pods -n fluid-ai
```

Check rollout:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Check image:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Check application:

```bash
curl http://127.0.0.1:8002/healthz
curl http://127.0.0.1:8002/readyz
curl http://127.0.0.1:8002/items
```

Check metrics:

```bash
curl -s \
  http://127.0.0.1:8002/metrics \
  | grep http_requests
```

Check Prometheus:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool
```

---

# 53. Evidence of Successful Deployment

A strong deployment verification record should contain:

```text
✓ Tests passed
✓ Docker image built
✓ Image pushed to GHCR
✓ Kubernetes Deployment updated
✓ Desired replicas available
✓ Rollout completed
✓ Correct Git SHA deployed
✓ Pods running
✓ /healthz returns 200
✓ /readyz returns 200
✓ /items returns 200
✓ /metrics returns Prometheus data
✓ ServiceMonitor exists
✓ Prometheus target is UP
✓ http_requests_total visible
```

This provides evidence across the complete delivery chain rather than relying only on GitHub Actions showing a green status.

---

# 54. Testing Philosophy

The project uses progressive validation:

```text
Fast feedback
     │
     ▼
pytest
     │
     ▼
Manifest validation
     │
     ▼
Container build
     │
     ▼
Kubernetes rollout
     │
     ▼
Health/readiness
     │
     ▼
Smoke test
     │
     ▼
Metrics
     │
     ▼
Prometheus
```

This reduces the chance that a deployment problem is discovered only after the application reaches a running environment.

---

# 55. Related Documentation

* `README.md` — Project introduction
* `docs/01-project-overview.md` — Project scope
* `docs/02-architecture.md` — System architecture
* `docs/03-local-setup.md` — Local environment
* `docs/04-kubernetes-deployment.md` — Kubernetes deployment
* `docs/05-cicd-pipeline.md` — CI/CD implementation
* `docs/06-monitoring-observability.md` — Prometheus and Grafana
* `docs/07-troubleshooting.md` — Troubleshooting
* `docs/08-operations-runbook.md` — Day-2 operations
* `docs/09-security.md` — Security
* `docs/10-testing-and-validation.md` — Testing and validation
