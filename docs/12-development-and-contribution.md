# Development and Contribution Guide

## 1. Purpose

This document explains how developers can work on, test, modify, and contribute to the Fluid AI DevOps Challenge project.

The goal is to make the repository understandable and reproducible for another engineer.

---

## 2. Repository Structure

```text
fluid-ai-devops-challenge/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   └── requirements.txt
├── tests/
│   └── test_health.py
├── k8s/
│   ├── backend.yaml
│   ├── postgres.yaml
│   └── monitoring/
│       └── backend-servicemonitor.yaml
├── .github/
│   └── workflows/
│       └── ci.yaml
├── docs/
├── Dockerfile
├── pytest.ini
└── README.md


3. Prerequisites

Required tools:

Python 3.10+
Docker
kubectl
Kind
Helm
Git

For Kubernetes monitoring:

Prometheus Operator
kube-prometheus-stack
Prometheus
Grafana
4. Create Python Environment
python3 -m venv .venv
source .venv/bin/activate

Upgrade pip:

python -m pip install --upgrade pip

Install application dependencies:

pip install -r app/requirements.txt
5. Run Tests

Run the complete test suite:

pytest -q

Expected result:

2 passed

Check repository formatting:

git diff --check
6. Run the Application Locally

The application requires PostgreSQL.

Example environment:

DB_HOST=127.0.0.1 \
DB_PORT=15432 \
DB_NAME=appdb \
DB_USER=appuser \
DB_PASSWORD='appsecret' \
uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8008

Verify:

curl http://127.0.0.1:8008/healthz
curl http://127.0.0.1:8008/readyz
curl http://127.0.0.1:8008/items
curl http://127.0.0.1:8008/metrics
7. Application Development

The main FastAPI application is:

app/main.py

Current endpoints include:

GET  /healthz
GET  /readyz
GET  /items
POST /items
GET  /metrics
Adding an Endpoint

When adding a new endpoint:

Implement the endpoint in the appropriate application module.
Add database logic if required.
Add or update tests.
Run pytest -q.
Run git diff --check.
Test the endpoint locally.
Build the Docker image.
Validate the Kubernetes deployment if required.
8. Database Changes

Database configuration is provided through environment variables:

DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD

Do not hard-code database credentials into source code.

When changing database models:

Update the SQLAlchemy model.
Update application logic.
Update tests.
Verify database connectivity.
Test the affected API endpoints.
9. Kubernetes Development

Kubernetes manifests are stored under:

k8s/

Before applying a manifest:

kubectl apply --dry-run=client -f <manifest>

Then apply:

kubectl apply -f <manifest>

Check status:

kubectl get pods -n fluid-ai
kubectl get deployments -n fluid-ai
kubectl get services -n fluid-ai

For the backend:

kubectl rollout status deployment/backend -n fluid-ai
10. Changing the Backend Deployment

The backend Deployment is:

k8s/backend.yaml

Important configuration includes:

replica count
container image
image pull policy
image pull secret
environment variables
resource requests
resource limits
liveness probe
readiness probe

After changing the manifest:

kubectl apply --dry-run=client -f k8s/backend.yaml

Then:

kubectl apply -f k8s/backend.yaml
kubectl rollout status deployment/backend -n fluid-ai
11. Container Image Development

Build locally:

docker build -t fluid-ai-backend:dev .

Inspect:

docker images | grep fluid-ai-backend

The CI/CD pipeline builds and publishes the production image to GHCR.

Production image format:

ghcr.io/upshivam786/kubernetes-cicd-production-demo:<git-sha>
12. CI/CD Development

The GitHub Actions workflow is:

.github/workflows/ci.yaml

It contains three major jobs:

test
build-and-push
deploy

Validate the workflow YAML:

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
13. CI/CD Change Checklist

Before pushing workflow changes:

pytest -q
git diff --check

Validate YAML:

python - <<'PY'
import yaml

with open(".github/workflows/ci.yaml") as f:
    yaml.safe_load(f)

print("Workflow YAML: OK")
PY

Then review:

git diff -- .github/workflows/ci.yaml
14. Monitoring Development

Monitoring configuration is stored under:

k8s/monitoring/

The backend exposes:

/metrics

Prometheus discovers the backend through:

ServiceMonitor

The backend ServiceMonitor is:

k8s/monitoring/backend-servicemonitor.yaml

Validate:

kubectl apply --dry-run=client \
  -f k8s/monitoring/backend-servicemonitor.yaml

Apply:

kubectl apply \
  -f k8s/monitoring/backend-servicemonitor.yaml

Verify:

kubectl get servicemonitor -n monitoring
15. Adding a Prometheus Metric

Application metrics are provided through:

prometheus-fastapi-instrumentator

The instrumentation is configured in:

app/main.py

After modifying metrics:

pytest -q

Run the application and verify:

curl http://127.0.0.1:8008/metrics

Look for:

http_requests_total

After Kubernetes deployment, verify Prometheus:

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total' \
  | python -m json.tool
16. Git Workflow

Before starting work:

git checkout main
git pull

Create a feature branch:

git checkout -b feature/<short-description>

Example:

git checkout -b feature/add-metrics

Make changes and test them.

Review:

git status
git diff

Validate:

pytest -q
git diff --check

Stage:

git add <files>

Review staged changes:

git diff --cached

Commit:

git commit -m "feat: add application metrics"

Push:

git push -u origin feature/add-metrics
17. Commit Message Convention

Use descriptive commit messages.

Examples:

feat: add application metrics
fix: correct backend readiness probe
ci: deploy backend to Kubernetes
k8s: configure private GHCR image
monitoring: add backend ServiceMonitor
docs: add troubleshooting guide
test: add metrics endpoint coverage
18. Pull Request Checklist

Before opening a Pull Request:

 Tests pass
 YAML validation passes
 git diff --check passes
 No secrets are committed
 Kubernetes manifests are validated
 Documentation is updated
 CI/CD workflow is validated
 Monitoring changes are documented
 Commit messages are descriptive
19. Security Checklist

Never commit:

.env
.env.*
*.pem
*.key
credentials
API keys
passwords
tokens
Kubernetes authentication credentials

Review staged files before committing:

git status
git diff --cached
20. Local Validation Checklist

Run before pushing:

pytest -q
git diff --check

Validate Kubernetes:

kubectl apply --dry-run=client -f k8s/backend.yaml

Validate monitoring:

kubectl apply --dry-run=client \
  -f k8s/monitoring/backend-servicemonitor.yaml

Validate CI/CD YAML:

python - <<'PY'
import yaml

with open(".github/workflows/ci.yaml") as f:
    data = yaml.safe_load(f)

print("Workflow YAML: OK")
print("Jobs:", list(data["jobs"].keys()))
PY
21. Contribution Principles

Contributions should:

Solve a clearly defined problem.
Include appropriate tests.
Avoid unnecessary complexity.
Follow the existing project structure.
Preserve Kubernetes health checks.
Preserve observability.
Avoid introducing secrets.
Update documentation when behavior changes.
Keep deployments reproducible.
Prefer immutable container image tags in production.
22. Final Contributor Checklist

Before submitting changes:

[ ] Application change implemented
[ ] Tests added or updated
[ ] pytest -q passes
[ ] git diff --check passes
[ ] Kubernetes manifests validated
[ ] CI/CD workflow validated
[ ] Monitoring updated if necessary
[ ] Documentation updated
[ ] No secrets committed
[ ] Staged changes reviewed
[ ] Commit message is descriptive
23. Related Documentation
01-project-overview.md — Project overview
02-architecture.md — Architecture
03-local-setup.md — Local setup
04-kubernetes-deployment.md — Kubernetes deployment
05-cicd-pipeline.md — CI/CD
06-monitoring-observability.md — Monitoring
07-troubleshooting.md — Troubleshooting
08-operations-runbook.md — Operations
09-security.md — Security
10-testing-and-validation.md — Testing
11-incident-response.md — Incident response
