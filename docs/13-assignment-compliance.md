# Assignment Compliance and Evidence Matrix

## 1. Purpose

This document maps the assignment requirements to the implementation in this repository and provides commands that can be used to verify each requirement.

The purpose is to make the project evaluation reproducible and easy to audit.

---

# 2. Requirement Summary

The project implements a production-style DevOps platform containing:

- FastAPI backend
- PostgreSQL database
- Docker containerization
- Kubernetes deployment
- Private GHCR image
- Kubernetes health probes
- Resource requests and limits
- GitHub Actions CI/CD
- Automated container image build and push
- Automated Kubernetes deployment
- Rollout verification
- Deployment smoke testing
- Rollback capability
- Prometheus metrics
- Prometheus Operator
- ServiceMonitor
- Grafana
- Kubernetes state metrics
- Node exporter
- Troubleshooting documentation
- Security documentation
- Operations runbook
- Incident response documentation
- Developer contribution documentation

---

# 3. Application Requirement

## Requirement

A working backend application should be available.

## Implementation

FastAPI application:

```text
app/main.py

Current endpoints:

GET  /healthz
GET  /readyz
GET  /items
POST /items
GET  /metrics
Verification
pytest -q

Expected:

2 passed

Health check:

curl http://127.0.0.1:8002/healthz

Expected:

{"status":"ok"}

Readiness check:

curl http://127.0.0.1:8002/readyz

Expected:

{"status":"ready"}
4. PostgreSQL Requirement
Requirement

The application should communicate with PostgreSQL.

Implementation

Kubernetes PostgreSQL workload:

k8s/postgres.yaml

Backend database configuration:

DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD

Database credentials are stored using Kubernetes Secrets.

Verification
kubectl get pods -n fluid-ai

PostgreSQL should be:

1/1 Running

Check the service:

kubectl get service postgres -n fluid-ai

Check backend readiness:

curl http://127.0.0.1:8002/readyz
5. Docker Requirement
Requirement

The application should be containerized.

Implementation

Container definition:

Dockerfile

Build locally:

docker build -t fluid-ai-backend:dev .

Verify:

docker images | grep fluid-ai-backend
6. Kubernetes Requirement
Requirement

The application should run on Kubernetes.

Implementation

Kubernetes resources are located under:

k8s/

The backend uses:

Deployment
Service
Secret
Verification
kubectl get pods -n fluid-ai
kubectl get deployments -n fluid-ai
kubectl get services -n fluid-ai

Expected backend state:

2/2 Ready
7. Multiple Backend Replicas
Requirement

The application should support multiple backend replicas.

Implementation

The backend Deployment is configured with:

replicas: 2
Verification
kubectl get deployment backend -n fluid-ai

Expected:

READY   UP-TO-DATE   AVAILABLE
2/2     2            2
8. Kubernetes Health Checks
Requirement

The application should provide Kubernetes health checks.

Implementation

The backend has:

Liveness Probe
Readiness Probe

Liveness:

/healthz

Readiness:

/readyz
Verification
kubectl describe deployment backend -n fluid-ai

Check the configured probes.

Application verification:

curl http://127.0.0.1:8002/healthz
curl http://127.0.0.1:8002/readyz
9. Resource Management
Requirement

The application should define Kubernetes resource requests and limits.

Implementation

Backend configuration includes:

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
Verification
kubectl get deployment backend -n fluid-ai -o yaml
10. Private GHCR Image
Requirement

The Kubernetes deployment should be able to pull a private container image.

Implementation

The backend uses:

ghcr.io/upshivam786/kubernetes-cicd-production-demo

Kubernetes uses:

ghcr-pull-secret

The Deployment references the secret through:

imagePullSecrets:
  - name: ghcr-pull-secret
Verification
kubectl get secret ghcr-pull-secret -n fluid-ai

Verify the Deployment:

kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.imagePullSecrets[*].name}{"\n"}'

Expected:

ghcr-pull-secret
11. Immutable Production Image
Requirement

Production deployments should identify the exact container version.

Implementation

GitHub Actions publishes:

<image>:<github.sha>

The Kubernetes deployment receives the commit SHA image during CI/CD.

Example:

ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8ed2333bfeb03a55c7130bb5061580619d
Verification
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
12. GitHub Actions CI/CD
Requirement

The project should have automated CI/CD.

Implementation

Workflow:

.github/workflows/ci.yaml

Jobs:

test
build-and-push
deploy

Pipeline flow:

Git Push
   |
   v
Test
   |
   v
Build Docker Image
   |
   v
Push to GHCR
   |
   v
Deploy to Kubernetes
   |
   v
Rollout Verification
   |
   v
Smoke Test
Verification

Validate locally:

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
13. Automated Testing
Requirement

The CI pipeline should test the application before building the production image.

Implementation

GitHub Actions executes:

pytest -q

Tests are located under:

tests/
Verification
pytest -q

Expected:

2 passed
14. Docker Image Build and Push
Requirement

The CI pipeline should build and publish the application image.

Implementation

GitHub Actions uses:

docker/login-action
docker/build-push-action

The image is published to GHCR.

Tags include:

<github.sha>
latest
Verification

Check GitHub Actions build output and GHCR package.

The deployment uses the commit-specific image.

15. Automated Kubernetes Deployment
Requirement

Successful CI should deploy the new image to Kubernetes.

Implementation

The deploy job runs on a self-hosted runner with Kubernetes access.

The image is updated using:

kubectl -n fluid-ai set image deployment/backend \
  backend=${IMAGE_NAME}:${GITHUB_SHA}
Verification
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
16. Rollout Verification
Requirement

The pipeline should verify that Kubernetes successfully rolled out the new version.

Implementation

CI/CD executes:

kubectl -n fluid-ai rollout status deployment/backend \
  --timeout=120s
Verification
kubectl rollout status deployment/backend -n fluid-ai

Expected:

deployment "backend" successfully rolled out
17. Deployment Verification
Requirement

The pipeline should verify the deployed image.

Implementation

The workflow compares:

Expected image

against:

Image configured in Kubernetes

The deployment fails if they do not match.

This prevents a successful pipeline from silently deploying the wrong image.

18. Deployment Smoke Test
Requirement

The deployment should be functionally validated after rollout.

Implementation

The CI/CD workflow port-forwards the backend Service and verifies:

/healthz

The workflow fails if the backend does not respond successfully.

Manual Verification
kubectl port-forward -n fluid-ai service/backend 8002:8000

Then:

curl http://127.0.0.1:8002/healthz

Expected:

{"status":"ok"}
19. Rollback
Requirement

The deployment should support recovery from an unsuccessful release.

Implementation

Kubernetes Deployment rollout history is available.

Check:

kubectl rollout history deployment/backend -n fluid-ai

Rollback:

kubectl rollout undo deployment/backend -n fluid-ai

Verify:

kubectl rollout status deployment/backend -n fluid-ai
20. Prometheus Metrics
Requirement

The application should expose metrics.

Implementation

Prometheus instrumentation is provided by:

prometheus-fastapi-instrumentator

Endpoint:

/metrics
Verification
curl http://127.0.0.1:8002/metrics

Application request metrics include:

http_requests_total
21. Prometheus Operator
Requirement

The Kubernetes environment should provide production-style monitoring.

Implementation

The project uses:

kube-prometheus-stack

The stack provides:

Prometheus Operator
Prometheus
Alertmanager
Grafana
kube-state-metrics
node-exporter
ServiceMonitor resources
PrometheusRule resources
Verification
kubectl get pods -n monitoring

Expected monitoring components include:

Prometheus
Alertmanager
Grafana
kube-state-metrics
node-exporter
Prometheus Operator
22. ServiceMonitor
Requirement

Prometheus should discover the backend automatically.

Implementation

Backend ServiceMonitor:

k8s/monitoring/backend-servicemonitor.yaml

It selects:

app=backend

and scrapes:

/metrics

using the:

http

service port.

Verification
kubectl get servicemonitor fluid-ai-backend -n monitoring

Inspect:

kubectl describe servicemonitor fluid-ai-backend -n monitoring
23. Prometheus Target Verification
Requirement

The backend should appear as a healthy Prometheus target.

Verification

Query:

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool

Healthy targets return:

"1"

The project was successfully verified with two backend targets.

24. Application Metric Verification in Prometheus

Query:

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool

Expected result contains metrics for:

/healthz
/readyz
/metrics
/items

This confirms:

Application
   |
   v
/metrics
   |
   v
Service
   |
   v
ServiceMonitor
   |
   v
Prometheus
25. Grafana
Requirement

The monitoring stack should provide visualization capability.

Implementation

Grafana is deployed through:

kube-prometheus-stack

Service:

monitoring-crds-grafana
Verification
kubectl get pods -n monitoring
kubectl get svc -n monitoring

Grafana can be accessed locally using port-forwarding.

26. Kubernetes Monitoring Components

The monitoring namespace contains:

Prometheus
Alertmanager
Grafana
kube-state-metrics
node-exporter
Prometheus Operator

Verification:

kubectl get pods -n monitoring
27. Documentation Requirement

The project includes dedicated documentation for:

01-project-overview.md
02-architecture.md
03-local-setup.md
04-kubernetes-deployment.md
05-cicd-pipeline.md
06-monitoring-observability.md
07-troubleshooting.md
08-operations-runbook.md
09-security.md
10-testing-and-validation.md
11-incident-response.md
12-development-and-contribution.md
13-assignment-compliance.md

This provides:

Architecture documentation
Setup instructions
Deployment instructions
CI/CD documentation
Monitoring documentation
Troubleshooting
Operations
Security
Testing
Incident response
Contribution guidance
Assignment evidence
28. Final Compliance Matrix
Requirement	Implementation	Verification
FastAPI backend	app/main.py	pytest -q
PostgreSQL	k8s/postgres.yaml	kubectl get pods -n fluid-ai
Docker	Dockerfile	docker build
Kubernetes	k8s/	kubectl get pods
2 backend replicas	Backend Deployment	kubectl get deployment
Health checks	/healthz, /readyz	curl
Resource limits	Backend Deployment	kubectl get deployment -o yaml
Private GHCR	ghcr-pull-secret	kubectl get secret
CI/CD	.github/workflows/ci.yaml	GitHub Actions
Automated tests	tests/	pytest -q
Image build	Docker Buildx action	GitHub Actions
GHCR push	GHCR	GitHub Actions
Kubernetes deployment	Deploy job	kubectl rollout status
Immutable image	Git SHA tag	kubectl get deployment
Smoke test	CI/CD workflow	GitHub Actions
Rollback	Kubernetes rollout	kubectl rollout undo
Prometheus metrics	/metrics	curl
Prometheus Operator	kube-prometheus-stack	kubectl get pods -n monitoring
ServiceMonitor	fluid-ai-backend	kubectl get servicemonitor
Backend monitoring	Prometheus	up{job="backend"}
Application metrics	http_requests_total	Prometheus API
Grafana	kube-prometheus-stack	kubectl get svc -n monitoring
Troubleshooting	07-troubleshooting.md	Documentation review
Operations	08-operations-runbook.md	Documentation review
Security	09-security.md	Documentation review
Testing	10-testing-and-validation.md	pytest -q
Incident response	11-incident-response.md	Documentation review
Contribution guide	12-development-and-contribution.md	Documentation review
29. Final Verification Commands

Run the following before considering the assignment complete:

Application
pytest -q
Repository
git diff --check
git status
Kubernetes
kubectl get nodes
kubectl get pods -n fluid-ai
kubectl get deployment backend -n fluid-ai
kubectl rollout status deployment/backend -n fluid-ai
Backend Image
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
Monitoring
kubectl get pods -n monitoring
kubectl get servicemonitor -n monitoring
Prometheus
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{job="backend"}' \
  | python -m json.tool
Metrics
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool
30. Final Assessment

The project demonstrates an end-to-end production-style DevOps workflow:

Developer
    |
    v
GitHub
    |
    v
GitHub Actions
    |
    +--> Tests
    |
    +--> Docker Build
    |
    +--> GHCR
    |
    v
Self-Hosted Runner
    |
    v
Kubernetes
    |
    +--> FastAPI
    |
    +--> PostgreSQL
    |
    +--> Health Checks
    |
    +--> Rollout
    |
    +--> Rollback
    |
    v
Prometheus
    |
    +--> ServiceMonitor
    |
    +--> Application Metrics
    |
    v
Grafana

The repository therefore provides not only an application deployment but a complete DevOps lifecycle covering:

Development
Testing
Containerization
CI/CD
Kubernetes
Secrets
Health checks
Rollouts
Rollbacks
Monitoring
Observability
Troubleshooting
Security
Incident response
Operations
Developer contribution
