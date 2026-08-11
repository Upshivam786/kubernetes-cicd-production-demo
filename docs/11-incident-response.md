# Incident Response Guide

## 1. Purpose

This document defines the incident response process for the Fluid AI DevOps Challenge project.

It provides a consistent approach for detecting, diagnosing, mitigating, recovering from, and documenting production incidents affecting:

- FastAPI backend
- PostgreSQL
- Kubernetes workloads
- GHCR container images
- GitHub Actions CI/CD
- Prometheus monitoring
- Kubernetes networking and services

---

## 2. Incident Response Lifecycle

The standard incident lifecycle is:

1. Detect
2. Triage
3. Diagnose
4. Mitigate
5. Recover
6. Validate
7. Document
8. Prevent recurrence

---

## 3. Initial Incident Checks

Start with the overall Kubernetes state:

```bash
kubectl get nodes
kubectl get pods -A
kubectl get deployments -A
kubectl get services -A

Check recent Kubernetes events:

kubectl get events -A --sort-by=.lastTimestamp

Check the backend:

kubectl get pods -n fluid-ai -l app=backend
kubectl get deployment backend -n fluid-ai
kubectl get service backend -n fluid-ai
4. Backend Pod Failure
Symptoms

Typical symptoms include:

Pod is not Running
Pod is not Ready
Pod restarts repeatedly
Application health checks fail
Diagnosis
kubectl get pods -n fluid-ai -l app=backend

Inspect the pod:

kubectl describe pod <pod-name> -n fluid-ai

Check logs:

kubectl logs <pod-name> -n fluid-ai

If the container restarted:

kubectl logs <pod-name> -n fluid-ai --previous
Recovery

If the application itself is healthy but pods need to be recreated:

kubectl rollout restart deployment/backend -n fluid-ai

Wait for recovery:

kubectl rollout status deployment/backend -n fluid-ai

Verify:

kubectl get pods -n fluid-ai -l app=backend

Expected:

READY   STATUS
1/1     Running
5. CrashLoopBackOff
Symptoms

A pod repeatedly starts and crashes.

Check:

kubectl get pods -n fluid-ai

Example:

backend-xxxxx   0/1   CrashLoopBackOff
Diagnosis
kubectl describe pod <pod-name> -n fluid-ai

Check current logs:

kubectl logs <pod-name> -n fluid-ai

Check logs from the previous crashed container:

kubectl logs <pod-name> -n fluid-ai --previous

Check recent events:

kubectl get events -n fluid-ai --sort-by=.lastTimestamp
Common Causes
Application startup failure
Database connection failure
Incorrect environment variables
Missing Kubernetes Secret
Incorrect image
Failed dependency
Liveness probe failure
6. ImagePullBackOff
Symptoms

The pod cannot download its container image.

Check:

kubectl get pods -n fluid-ai

Possible status:

ImagePullBackOff
ErrImagePull
Diagnosis
kubectl describe pod <pod-name> -n fluid-ai

Check the image configured in the Deployment:

kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

Check the image pull secret:

kubectl get secret ghcr-pull-secret -n fluid-ai

Check that the Deployment references it:

kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.imagePullSecrets[*].name}{"\n"}'

Expected:

ghcr-pull-secret
Common Causes
Incorrect image name
Incorrect image tag
Private GHCR repository
Missing imagePullSecrets
Invalid GHCR credentials
Image does not exist
Registry connectivity problem
7. Failed Kubernetes Rollout

Check rollout status:

kubectl rollout status deployment/backend -n fluid-ai

Check rollout history:

kubectl rollout history deployment/backend -n fluid-ai

Inspect the Deployment:

kubectl describe deployment backend -n fluid-ai

Check pods:

kubectl get pods -n fluid-ai -l app=backend
Rollback

If the latest deployment is unhealthy:

kubectl rollout undo deployment/backend -n fluid-ai

Wait for the rollback:

kubectl rollout status deployment/backend -n fluid-ai

Verify:

kubectl get pods -n fluid-ai -l app=backend
8. Database Failure

The backend depends on PostgreSQL.

Symptoms

Typical symptoms include:

/readyz returns 503
Backend cannot connect to PostgreSQL
Database connection errors appear in application logs
Backend pods remain running but are not ready
Check PostgreSQL
kubectl get pods -n fluid-ai -l app=postgres

Check the PostgreSQL Service:

kubectl get service postgres -n fluid-ai

Check backend logs:

kubectl logs deployment/backend -n fluid-ai

Inspect the backend pod:

kubectl describe pod <backend-pod> -n fluid-ai
Important Configuration

The backend uses:

DB_HOST=postgres
DB_PORT=5432

The database credentials are supplied through the Kubernetes Secret:

backend-db

Check the Secret exists:

kubectl get secret backend-db -n fluid-ai

Do not print secret values into logs or documentation.

9. Readiness Failure

The backend exposes:

GET /readyz

The readiness probe verifies database connectivity.

Test Locally

Port-forward the backend:

kubectl port-forward -n fluid-ai service/backend 8002:8000

Then:

curl http://127.0.0.1:8002/readyz

Healthy response:

{"status":"ready"}

If the application is not ready, inspect:

kubectl get pods -n fluid-ai
kubectl describe pod <pod-name> -n fluid-ai
kubectl logs <pod-name> -n fluid-ai
10. Liveness Failure

The backend exposes:

GET /healthz

Test:

curl http://127.0.0.1:8002/healthz

Expected:

{"status":"ok"}

If Kubernetes repeatedly restarts the pod:

kubectl describe pod <pod-name> -n fluid-ai

Check events:

kubectl get events -n fluid-ai --sort-by=.lastTimestamp

Check restart count:

kubectl get pods -n fluid-ai
11. Prometheus Target Down

Prometheus monitors the backend through the ServiceMonitor:

fluid-ai-backend

Check the ServiceMonitor:

kubectl get servicemonitor fluid-ai-backend -n monitoring

Inspect it:

kubectl describe servicemonitor fluid-ai-backend -n monitoring

The ServiceMonitor should target:

namespace: fluid-ai
service: backend
endpoint: /metrics
port: http

Check monitoring pods:

kubectl get pods -n monitoring
Check Backend Target

Query Prometheus:

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool

Healthy backend targets should return:

"value": [
    "...",
    "1"
]

A value of:

0

means Prometheus cannot successfully scrape that target.

12. Missing Application Metrics

The FastAPI application exposes Prometheus metrics at:

/metrics

Port-forward:

kubectl port-forward -n fluid-ai service/backend 8002:8000

Check:

curl -s http://127.0.0.1:8002/metrics

Check HTTP request metrics:

curl -s http://127.0.0.1:8002/metrics | grep http_requests

Expected metrics include:

http_requests_total

Then verify that Prometheus has collected them:

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool

If the application exposes metrics but Prometheus does not contain them, investigate:

Service labels
ServiceMonitor selector
ServiceMonitor namespace selector
Service port name
Prometheus serviceMonitorSelector
Prometheus target status
13. CI/CD Failure

The GitHub Actions pipeline contains:

test
build-and-push
deploy

If the workflow fails, inspect the failed job in GitHub Actions.

Validate Workflow YAML Locally
python - <<'PY'
import yaml

with open(".github/workflows/ci.yaml") as f:
    data = yaml.safe_load(f)

print("Workflow YAML: OK")
print("Jobs:", list(data["jobs"].keys()))
PY

Expected:

Workflow YAML: OK
Jobs: ['test', 'build-and-push', 'deploy']

Check formatting:

git diff --check
14. Kubernetes Connectivity Failure

Check cluster access:

kubectl cluster-info

Check nodes:

kubectl get nodes

Expected node state:

Ready

Check all workloads:

kubectl get pods -A

For this project the Kubernetes cluster is a Kind cluster with the control-plane node:

fluid-ai-control-plane
15. GHCR Image Verification

Check the image configured in Kubernetes:

kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

The production deployment uses an immutable Git commit SHA tag, for example:

ghcr.io/upshivam786/kubernetes-cicd-production-demo:<git-sha>

Check the actual image ID used by pods:

kubectl get pods -n fluid-ai -l app=backend \
  -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.status.containerStatuses[0].imageID}{"\n"}{end}'

This helps confirm which image digest is actually running.

16. Evidence Collection During an Incident

Collect Kubernetes state:

kubectl get nodes
kubectl get pods -A
kubectl get deployments -A
kubectl get services -A

Collect recent events:

kubectl get events -A --sort-by=.lastTimestamp

Collect backend information:

kubectl get deployment backend -n fluid-ai
kubectl get pods -n fluid-ai -l app=backend
kubectl describe deployment backend -n fluid-ai

Collect logs:

kubectl logs deployment/backend -n fluid-ai

Collect rollout information:

kubectl rollout history deployment/backend -n fluid-ai
17. Recovery Validation

After mitigation, verify Kubernetes:

kubectl get deployment backend -n fluid-ai

Expected:

READY   UP-TO-DATE   AVAILABLE
2/2     2            2

Check pods:

kubectl get pods -n fluid-ai -l app=backend

Check rollout:

kubectl rollout status deployment/backend -n fluid-ai

Check application health:

kubectl port-forward -n fluid-ai service/backend 8002:8000

Then:

curl http://127.0.0.1:8002/healthz
curl http://127.0.0.1:8002/readyz
curl http://127.0.0.1:8002/items
curl http://127.0.0.1:8002/metrics

Expected:

/healthz  -> {"status":"ok"}
/readyz   -> {"status":"ready"}
/items    -> application response
/metrics  -> Prometheus metrics
18. Monitoring Recovery

Verify Prometheus:

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool

Expected:

"value": [
    "...",
    "1"
]

Verify application metrics:

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool
19. Post-Incident Review

Every significant incident should record:

What happened?
When did it happen?
How was it detected?
What components were affected?
What was the user impact?
What was the root cause?
What mitigation was applied?
How was recovery verified?
What monitoring detected the issue?
What preventive action should be taken?
20. Example Incident Timeline
Time	Event	Action
T+0	Incident detected	Incident acknowledged
T+5	Initial investigation	Kubernetes state and logs inspected
T+10	Root cause identified	Mitigation applied
T+15	Application recovered	Rollout and health checks verified
T+20	Monitoring verified	Prometheus targets confirmed healthy
T+30	Incident closed	Post-incident documentation started
21. Golden Recovery Checklist

Use this checklist during an incident:

 Identify the affected component
 Check Kubernetes node status
 Check pod status
 Check deployment status
 Check recent Kubernetes events
 Inspect application logs
 Check previous container logs
 Check health endpoint
 Check readiness endpoint
 Check PostgreSQL
 Check container image
 Check GHCR image pull secret
 Check rollout history
 Check Prometheus targets
 Check application metrics
 Apply mitigation
 Verify application recovery
 Verify Kubernetes recovery
 Verify monitoring recovery
 Document root cause
 Create preventive action
22. Important Safety Notes

Do not expose secrets while troubleshooting.

Avoid commands that print secret values such as:

kubectl get secret <secret> -o yaml

unless the output is being handled securely.

Prefer checking whether a Secret exists:

kubectl get secret backend-db -n fluid-ai

Similarly, do not commit:

Kubernetes credentials
GHCR tokens
API keys
database passwords
.env files containing secrets
generated credentials
23. Related Documentation

See:

01-project-overview.md — Project overview
02-architecture.md — System architecture
03-local-setup.md — Local development setup
04-kubernetes-deployment.md — Kubernetes deployment
05-cicd-pipeline.md — CI/CD pipeline
06-monitoring-observability.md — Monitoring and Prometheus
07-troubleshooting.md — Troubleshooting guide
08-operations-runbook.md — Operational procedures
09-security.md — Security practices
10-testing-and-validation.md — Testing and validation
