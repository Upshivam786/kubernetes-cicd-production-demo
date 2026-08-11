# Fluid AI DevOps Challenge — Operations Runbook

## 1. Purpose

This runbook documents the operational procedures required to manage the Fluid AI application after deployment.

It focuses on day-2 operations:

* checking system health
* inspecting deployments
* verifying releases
* monitoring Pods
* viewing logs
* scaling the application
* restarting workloads safely
* rolling back deployments
* checking database connectivity
* validating Prometheus monitoring
* accessing Grafana
* performing post-deployment verification
* responding to common operational incidents

The goal is to provide a repeatable operational procedure rather than relying on ad-hoc commands.

---

# 2. System Overview

The deployed environment consists of:

```text
GitHub
   │
   │ Push to main
   ▼
GitHub Actions
   │
   ├── Test
   ├── Build Docker image
   ├── Push image to GHCR
   └── Deploy to Kubernetes
             │
             ▼
       Kind Kubernetes
             │
       ┌─────┴─────┐
       │           │
   fluid-ai     monitoring
       │           │
       │       Prometheus
       │       Grafana
       │       Alertmanager
       │
   ┌───┴────┐
   │        │
Backend   PostgreSQL
```

---

# 3. Operational Entry Points

## Application Namespace

```bash
kubectl get all -n fluid-ai
```

## Monitoring Namespace

```bash
kubectl get all -n monitoring
```

## Cluster

```bash
kubectl get nodes
```

---

# 4. Daily Health Check

A quick health check should begin with:

```bash
kubectl get nodes
```

Expected:

```text
STATUS
Ready
```

Then:

```bash
kubectl get pods -n fluid-ai
```

Expected:

```text
backend-...     1/1     Running
backend-...     1/1     Running
postgres-...    1/1     Running
```

Check monitoring:

```bash
kubectl get pods -n monitoring
```

Expected monitoring components should be Running.

---

# 5. Application Health

Check the backend Deployment:

```bash
kubectl get deployment backend -n fluid-ai
```

Expected:

```text
READY   UP-TO-DATE   AVAILABLE
2/2     2            2
```

Check rollout:

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

# 6. Health Endpoint

Create a temporary local connection:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/backend \
  8002:8000
```

Then:

```bash
curl -s \
  http://127.0.0.1:8002/healthz
```

Expected:

```json
{"status":"ok"}
```

---

# 7. Readiness Endpoint

Run:

```bash
curl -s \
  http://127.0.0.1:8002/readyz
```

Expected:

```json
{"status":"ready"}
```

The readiness endpoint verifies that the application can communicate with its database dependency.

---

# 8. Application Functional Check

Check the items endpoint:

```bash
curl -s \
  http://127.0.0.1:8002/items
```

Expected output depends on database contents.

An empty database may return:

```json
[]
```

Create an item:

```bash
curl -X POST \
  "http://127.0.0.1:8002/items?name=example"
```

Then verify:

```bash
curl -s \
  http://127.0.0.1:8002/items
```

---

# 9. Metrics Health Check

Verify the Prometheus endpoint:

```bash
curl -s \
  http://127.0.0.1:8002/metrics
```

Look for:

```text
http_requests_total
```

For a shorter check:

```bash
curl -s \
  http://127.0.0.1:8002/metrics \
  | grep http_requests
```

---

# 10. Identify the Running Image

Always verify the exact image running in Kubernetes:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8...
```

The Git SHA makes the deployed version traceable to a source revision.

---

# 11. Verify Pod Images

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend \
  -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

This verifies the actual image digest used by each Pod.

---

# 12. View Application Logs

List Pods:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend
```

Then:

```bash
kubectl logs \
  <pod-name> \
  -n fluid-ai
```

For live logs:

```bash
kubectl logs \
  -f <pod-name> \
  -n fluid-ai
```

---

# 13. View Logs From All Backend Pods

```bash
kubectl logs \
  -n fluid-ai \
  -l app=backend \
  --prefix=true
```

This is useful when comparing behavior across replicas.

---

# 14. Inspect Pod Events

```bash
kubectl describe pod \
  <pod-name> \
  -n fluid-ai
```

Pay particular attention to:

* Events
* Container state
* Restart count
* Readiness probe
* Liveness probe
* Image
* Environment variables
* Resource requests and limits

---

# 15. Check Service

```bash
kubectl get service backend \
  -n fluid-ai
```

Detailed configuration:

```bash
kubectl get service backend \
  -n fluid-ai \
  -o yaml
```

Expected important configuration:

```yaml
metadata:
  labels:
    app: backend

spec:
  selector:
    app: backend

  ports:
    - name: http
      port: 8000
      targetPort: 8000
```

---

# 16. Check Service Endpoints

```bash
kubectl get endpoints backend \
  -n fluid-ai
```

The Service should have backend Pod addresses.

If there are no endpoints, investigate:

```bash
kubectl get pods \
  -n fluid-ai \
  --show-labels
```

and compare them with:

```yaml
selector:
  app: backend
```

---

# 17. Scale Backend

Current configuration uses two replicas.

Check:

```bash
kubectl get deployment backend \
  -n fluid-ai
```

Scale to three:

```bash
kubectl scale deployment backend \
  -n fluid-ai \
  --replicas=3
```

Verify:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend
```

Verify Deployment:

```bash
kubectl get deployment backend \
  -n fluid-ai
```

Expected:

```text
READY
3/3
```

---

# 18. Return to Normal Replica Count

The application's Kubernetes configuration currently defines two replicas.

Return to two:

```bash
kubectl scale deployment backend \
  -n fluid-ai \
  --replicas=2
```

Then:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

---

# 19. Restart Backend Pods

A controlled restart can be performed using:

```bash
kubectl rollout restart \
  deployment/backend \
  -n fluid-ai
```

Then immediately monitor:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

Check Pods:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend
```

---

# 20. When to Restart

A rollout restart may be appropriate when:

* Pods need to be recreated
* a non-image configuration change requires recreation
* a transient application issue needs a controlled restart
* validating startup behavior

Do not use restart as the first response to every failure.

First inspect:

```bash
kubectl logs
kubectl describe pod
kubectl get events
```

---

# 21. Deployment History

View revisions:

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

This allows operators to determine whether the Deployment has undergone multiple updates.

---

# 22. Inspect a Specific Revision

```bash
kubectl rollout history \
  deployment/backend \
  -n fluid-ai \
  --revision=<revision-number>
```

Use this before rolling back when possible.

---

# 23. Rollback a Deployment

If the current release is unhealthy:

```bash
kubectl rollout undo \
  deployment/backend \
  -n fluid-ai
```

Monitor:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

Then verify:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend
```

Finally verify the image:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

---

# 24. Roll Back to a Specific Revision

If a known-good revision is identified:

```bash
kubectl rollout undo \
  deployment/backend \
  -n fluid-ai \
  --to-revision=<revision-number>
```

Then:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

---

# 25. Post-Rollback Verification

Never consider a rollback complete just because the command succeeded.

Run:

```bash
kubectl get deployment backend -n fluid-ai
```

```bash
kubectl get pods -n fluid-ai -l app=backend
```

Then test:

```bash
curl -s http://127.0.0.1:8002/healthz
```

```bash
curl -s http://127.0.0.1:8002/readyz
```

And check Prometheus:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}'
```

---

# 26. Database Operations

Check PostgreSQL:

```bash
kubectl get pod \
  -n fluid-ai \
  -l app=postgres
```

Check Service:

```bash
kubectl get service postgres \
  -n fluid-ai
```

Check logs:

```bash
kubectl logs \
  -n fluid-ai \
  -l app=postgres
```

---

# 27. Database Port Forward

For local database debugging:

```bash
kubectl port-forward \
  -n fluid-ai \
  service/postgres \
  15432:5432
```

The database can then be reached locally at:

```text
127.0.0.1:15432
```

---

# 28. Database Credentials

The application database credentials are stored in a Kubernetes Secret.

Check the Secret exists:

```bash
kubectl get secret backend-db \
  -n fluid-ai
```

Do not print production credentials into terminal history, Git, CI logs, or documentation.

Inspecting the existence of the Secret is normally sufficient:

```bash
kubectl describe secret backend-db \
  -n fluid-ai
```

---

# 29. GHCR Pull Secret

The backend uses a private GitHub Container Registry image.

Verify the image pull Secret:

```bash
kubectl get secret ghcr-pull-secret \
  -n fluid-ai
```

Expected type:

```text
kubernetes.io/dockerconfigjson
```

Verify the Deployment references it:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.imagePullSecrets[*].name}{"\n"}'
```

Expected:

```text
ghcr-pull-secret
```

---

# 30. Never Commit Registry Tokens

GHCR authentication tokens must never be committed to:

```text
Git
README.md
documentation
Kubernetes manifests
GitHub Actions logs
shell history
```

If a registry token is accidentally exposed, revoke it immediately and create a replacement.

---

# 31. CI/CD Operational Check

After pushing to `main`, open the GitHub Actions workflow and verify:

```text
Test Application
       ↓
Build and Push Image
       ↓
Deploy to Kubernetes
       ↓
Rollout
       ↓
Smoke Tests
```

A successful workflow should result in the expected Git SHA image running in Kubernetes.

---

# 32. CI/CD Release Verification

After a successful pipeline:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Compare the output with the Git commit that triggered the workflow.

Then:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

---

# 33. Monitoring Stack Health

Check:

```bash
kubectl get pods \
  -n monitoring
```

Expected components include:

```text
Prometheus
Alertmanager
Grafana
Prometheus Operator
kube-state-metrics
node-exporter
```

---

# 34. Prometheus Health

Check the Prometheus custom resource:

```bash
kubectl get prometheus \
  -n monitoring
```

Expected:

```text
READY
1
```

Check Prometheus Pods:

```bash
kubectl get pods \
  -n monitoring \
  -l app.kubernetes.io/name=prometheus
```

---

# 35. Prometheus Port Forward

```bash
kubectl port-forward \
  -n monitoring \
  service/monitoring-crds-kube-prome-prometheus \
  9090:9090
```

Prometheus can then be accessed locally at:

```text
http://127.0.0.1:9090
```

---

# 36. Check Prometheus Targets

Use the Prometheus API:

```bash
curl -s \
  http://127.0.0.1:9090/api/v1/targets
```

For the backend:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}'
```

Expected:

```text
value = 1
```

for each healthy backend replica.

---

# 37. Check Application Metrics

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total'
```

The backend should expose metrics for endpoints such as:

```text
/healthz
/readyz
/metrics
```

---

# 38. Check ServiceMonitor

```bash
kubectl get servicemonitor \
  -n monitoring
```

Inspect:

```bash
kubectl describe servicemonitor \
  fluid-ai-backend \
  -n monitoring
```

Important configuration:

```text
Namespace:
fluid-ai

Path:
/metrics

Port:
http

Selector:
app=backend
```

---

# 39. Verify Prometheus Selector

Inspect the Prometheus resource:

```bash
kubectl get prometheus \
  -n monitoring \
  -o yaml \
  | grep -A8 -B2 serviceMonitorSelector
```

Expected:

```yaml
serviceMonitorSelector:
  matchLabels:
    release: monitoring-crds
```

The backend ServiceMonitor must have:

```yaml
metadata:
  labels:
    release: monitoring-crds
```

---

# 40. Grafana Operations

Check Grafana:

```bash
kubectl get pod \
  -n monitoring \
  -l app.kubernetes.io/name=grafana
```

Port-forward:

```bash
kubectl port-forward \
  -n monitoring \
  service/monitoring-crds-grafana \
  3000:80
```

Access locally:

```text
http://127.0.0.1:3000
```

---

# 41. Grafana Credentials

Retrieve the generated Grafana admin password:

```bash
kubectl get secret \
  -n monitoring \
  monitoring-crds-grafana \
  -o jsonpath="{.data.admin-password}" \
  | base64 -d
```

Do not store the password in Git.

---

# 42. Alertmanager Operations

Check:

```bash
kubectl get alertmanager \
  -n monitoring
```

Check Pod:

```bash
kubectl get pods \
  -n monitoring \
  | grep alertmanager
```

Inspect:

```bash
kubectl describe alertmanager \
  monitoring-crds-kube-prome-alertmanager \
  -n monitoring
```

---

# 43. Helm Release

Check the monitoring Helm release:

```bash
helm list \
  -n monitoring
```

Expected:

```text
monitoring-crds
```

Check status:

```bash
helm status \
  monitoring-crds \
  -n monitoring
```

---

# 44. Helm Release History

```bash
helm history \
  monitoring-crds \
  -n monitoring
```

This is useful when investigating monitoring-stack upgrades.

---

# 45. Monitoring Stack Upgrade

Before upgrading:

```bash
helm list -n monitoring
```

Inspect the current chart:

```bash
helm show chart \
  prometheus-community/kube-prometheus-stack
```

Validate values before applying:

```bash
helm upgrade monitoring-crds \
  <chart> \
  --namespace monitoring \
  --values k8s/monitoring/prometheus-values.yaml \
  --dry-run
```

If the remote chart download is unavailable, a locally downloaded chart archive can be used.

---

# 46. Kubernetes Manifest Changes

Before applying changes:

```bash
kubectl apply \
  --dry-run=client \
  -f k8s/backend.yaml
```

Then:

```bash
git diff --check
```

Only after validation:

```bash
kubectl apply \
  -f k8s/backend.yaml
```

Verify:

```bash
kubectl rollout status \
  deployment/backend \
  -n fluid-ai
```

---

# 47. Monitoring Manifest Changes

Validate:

```bash
kubectl apply \
  --dry-run=client \
  -f k8s/monitoring/backend-servicemonitor.yaml
```

Apply:

```bash
kubectl apply \
  -f k8s/monitoring/backend-servicemonitor.yaml
```

Verify:

```bash
kubectl get servicemonitor \
  -n monitoring
```

---

# 48. Safe Change Procedure

For normal application changes:

```text
1. Modify source
      ↓
2. Run tests
      ↓
3. Run git diff --check
      ↓
4. Review git diff
      ↓
5. Commit
      ↓
6. Push
      ↓
7. GitHub Actions runs
      ↓
8. Verify deployment
      ↓
9. Verify Pods
      ↓
10. Verify health/readiness
      ↓
11. Verify metrics
      ↓
12. Verify Prometheus
```

---

# 49. Production-Like Deployment Verification

After every release:

```bash
kubectl get deployment backend -n fluid-ai
```

```bash
kubectl get pods -n fluid-ai -l app=backend
```

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Then test:

```bash
curl -s http://127.0.0.1:8002/healthz
```

```bash
curl -s http://127.0.0.1:8002/readyz
```

```bash
curl -s http://127.0.0.1:8002/items
```

Metrics:

```bash
curl -s http://127.0.0.1:8002/metrics | grep http_requests
```

Prometheus:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}'
```

---

# 50. Incident Response Procedure

When an application incident occurs:

## Step 1 — Establish scope

```bash
kubectl get pods -n fluid-ai
```

## Step 2 — Check deployment

```bash
kubectl get deployment backend -n fluid-ai
```

## Step 3 — Check recent events

```bash
kubectl get events \
  -n fluid-ai \
  --sort-by=.lastTimestamp
```

## Step 4 — Inspect logs

```bash
kubectl logs \
  -n fluid-ai \
  -l app=backend \
  --prefix=true
```

## Step 5 — Check health

```bash
curl http://127.0.0.1:8002/healthz
```

## Step 6 — Check readiness

```bash
curl http://127.0.0.1:8002/readyz
```

## Step 7 — Check Prometheus

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}'
```

## Step 8 — Determine whether rollback is required

If the problem started immediately after a release:

```bash
kubectl rollout history deployment/backend -n fluid-ai
```

Consider:

```bash
kubectl rollout undo deployment/backend -n fluid-ai
```

## Step 9 — Verify recovery

Repeat the health, readiness, Pod, and Prometheus checks.

---

# 51. Recovery Validation

A recovery is successful only when all of the following are true:

```text
[✓] Deployment available
[✓] All expected Pods Running
[✓] No unexpected restarts
[✓] /healthz returns 200
[✓] /readyz returns 200
[✓] Application endpoint works
[✓] /metrics returns metrics
[✓] Prometheus backend target is UP
[✓] http_requests_total is available
```

---

# 52. Useful One-Liners

Backend status:

```bash
kubectl get deployment backend -n fluid-ai && \
kubectl get pods -n fluid-ai -l app=backend
```

Current image:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Rollout:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Backend logs:

```bash
kubectl logs -n fluid-ai -l app=backend --prefix=true
```

Monitoring:

```bash
kubectl get pods -n monitoring
```

Backend Prometheus health:

```bash
curl -sG \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}'
```

---

# 53. Operational Principles

### Prefer observation before intervention

Use:

```bash
kubectl get
kubectl describe
kubectl logs
kubectl get events
```

before changing resources.

### Prefer reversible changes

Use:

```bash
kubectl rollout restart
kubectl rollout undo
```

when appropriate.

### Verify every change

Never assume:

```text
command succeeded = system healthy
```

Instead verify the resulting system state.

### Keep releases traceable

Prefer immutable Git SHA image tags over relying exclusively on `latest`.

### Keep secrets out of documentation

Document:

* Secret name
* Secret purpose
* How to verify existence

Do not document:

* passwords
* access tokens
* registry credentials
* private keys

---

# 54. Operational Command Cheat Sheet

| Task               | Command                                                     |
| ------------------ | ----------------------------------------------------------- |
| Cluster status     | `kubectl get nodes`                                         |
| Application Pods   | `kubectl get pods -n fluid-ai`                              |
| Monitoring Pods    | `kubectl get pods -n monitoring`                            |
| Backend deployment | `kubectl get deployment backend -n fluid-ai`                |
| Backend logs       | `kubectl logs -n fluid-ai -l app=backend --prefix=true`     |
| Pod details        | `kubectl describe pod <pod> -n fluid-ai`                    |
| Service            | `kubectl get svc backend -n fluid-ai`                       |
| Rollout            | `kubectl rollout status deployment/backend -n fluid-ai`     |
| Rollout history    | `kubectl rollout history deployment/backend -n fluid-ai`    |
| Restart            | `kubectl rollout restart deployment/backend -n fluid-ai`    |
| Rollback           | `kubectl rollout undo deployment/backend -n fluid-ai`       |
| Scale              | `kubectl scale deployment/backend -n fluid-ai --replicas=3` |
| Metrics            | `curl http://127.0.0.1:8002/metrics`                        |
| Prometheus         | `kubectl get prometheus -n monitoring`                      |
| ServiceMonitor     | `kubectl get servicemonitor -n monitoring`                  |
| Helm               | `helm list -n monitoring`                                   |

---

# 55. End-of-Day Operational Check

Before finishing an operational session:

```bash
kubectl get nodes
kubectl get pods -n fluid-ai
kubectl get pods -n monitoring
kubectl get deployment backend -n fluid-ai
kubectl rollout status deployment/backend -n fluid-ai
git status
```

The expected application state is:

```text
Cluster:       Ready
Backend:       2/2 available
PostgreSQL:    Running
Prometheus:    Running
Grafana:       Running
Alertmanager:  Running
```

The repository should also have no unintended working-tree changes.

---

# 56. Related Documentation

* `README.md` — Project introduction and quick start
* `docs/01-project-overview.md` — Project scope
* `docs/02-architecture.md` — System architecture
* `docs/03-local-setup.md` — Local development setup
* `docs/04-kubernetes-deployment.md` — Kubernetes deployment
* `docs/05-cicd-pipeline.md` — CI/CD implementation
* `docs/06-monitoring-observability.md` — Monitoring and observability
* `docs/07-troubleshooting.md` — Troubleshooting and failure analysis
* `docs/08-operations-runbook.md` — Day-2 operations
