# Fluid AI DevOps Challenge — CI/CD Pipeline

## 1. Overview

The project implements a production-style CI/CD pipeline using GitHub Actions.

The pipeline automatically:

1. Runs application tests.
2. Builds the Docker image.
3. Pushes the image to GitHub Container Registry (GHCR).
4. Connects to the Kubernetes cluster through a self-hosted GitHub Actions runner.
5. Updates the Kubernetes Deployment with the exact Git commit image.
6. Waits for the Kubernetes rollout.
7. Verifies that the expected image is actually deployed.
8. Runs a Kubernetes smoke test.
9. Fails the deployment if verification fails.

The workflow is defined in:

```text
.github/workflows/ci.yaml
```

---

# 2. CI/CD Architecture

The complete flow is:

```text
Developer
    │
    │ git push
    ▼
GitHub Repository
    │
    ▼
GitHub Actions
    │
    ├─────────────────────────┐
    │                         │
    ▼                         ▼
Test Application       Build Docker Image
    │                         │
    │                         ▼
    │                    Push to GHCR
    │                         │
    └────────────┬────────────┘
                 │
                 ▼
        Self-hosted Runner
                 │
                 ▼
        Kubernetes Cluster
                 │
                 ▼
        Update Deployment
                 │
                 ▼
        Rolling Deployment
                 │
                 ▼
        Rollout Verification
                 │
                 ▼
          Image Verification
                 │
                 ▼
            Smoke Test
```

---

# 3. Workflow File

The workflow is:

```text
.github/workflows/ci.yaml
```

Validate the workflow YAML locally with Python:

```bash
python - <<'PY'
import yaml

with open(".github/workflows/ci.yaml") as f:
    data = yaml.safe_load(f)

print("Workflow YAML: OK")
print("Jobs:", list(data["jobs"].keys()))
PY
```

Expected:

```text
Workflow YAML: OK
Jobs: ['test', 'build-and-push', 'deploy']
```

---

# 4. Workflow Trigger

The workflow runs on:

```yaml
on:
  push:
    branches:
      - main

  pull_request:
    branches:
      - main
```

Therefore:

### Push to `main`

A push executes the complete deployment pipeline:

```text
test
  ↓
build-and-push
  ↓
deploy
```

### Pull Request

A Pull Request runs the test stage.

The image build and Kubernetes deployment stages are restricted to push events.

This prevents Pull Requests from automatically modifying the Kubernetes environment.

---

# 5. Permissions

The workflow uses:

```yaml
permissions:
  contents: read
  packages: write
```

`contents: read` allows GitHub Actions to check out repository content.

`packages: write` allows the workflow to push the Docker image to GitHub Container Registry.

---

# 6. Image Name

The workflow defines:

```yaml
env:
  IMAGE_NAME: ghcr.io/upshivam786/kubernetes-cicd-production-demo
```

The final image therefore looks like:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:<git-sha>
```

For example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:8d6df0cb3dc70942907c2e00cb8059bda1f03ed4
```

---

# 7. Job 1 — Test Application

The first job is:

```text
test
```

Its purpose is to prevent broken application code from reaching the image build and deployment stages.

The job runs on:

```yaml
runs-on: ubuntu-latest
```

---

# 8. Checkout Source Code

The first step uses:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
```

This checks out the repository into the GitHub Actions runner.

---

# 9. Python Environment

The workflow installs Python 3.12:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.12"
```

This provides a consistent Python version for CI testing.

---

# 10. Install Dependencies

The workflow runs:

```bash
python -m pip install --upgrade pip
pip install -r app/requirements.txt
pip install pytest httpx
```

The application dependencies are installed from:

```text
app/requirements.txt
```

The test environment additionally installs:

```text
pytest
httpx
```

---

# 11. Database Test Configuration

The test job defines:

```yaml
env:
  DB_PASSWORD: test-password
```

The test suite does not require the production Kubernetes database credentials.

This keeps CI testing isolated from production credentials.

---

# 12. Run Tests

The test command is:

```bash
pytest -q
```

The expected result is:

```text
2 passed
```

The tests currently cover:

```text
/healthz
/metrics
```

The metrics test verifies that Prometheus instrumentation is exposed.

---

# 13. Job Dependencies

The Docker build depends on successful tests:

```yaml
needs: test
```

Therefore:

```text
Test fails
   │
   ▼
Build does not run
```

This is an important CI/CD quality gate.

---

# 14. Job 2 — Build and Push Image

The second job is:

```text
build-and-push
```

It runs only after:

```text
test
```

succeeds.

It also contains:

```yaml
if: github.event_name == 'push'
```

Therefore it does not publish images for Pull Requests.

---

# 15. GitHub Container Registry Authentication

The workflow logs into GHCR:

```yaml
- name: Log in to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

The workflow uses the automatically provided:

```text
GITHUB_TOKEN
```

instead of storing a personal GitHub token in the repository.

---

# 16. Docker Build and Push

The workflow uses:

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v6
```

The build context is:

```text
.
```

The image is pushed using two tags:

```text
<image>:<github-sha>
<image>:latest
```

For example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:8d6df0cb3dc70942907c2e00cb8059bda1f03ed4

ghcr.io/upshivam786/kubernetes-cicd-production-demo:latest
```

---

# 17. Why Git SHA Tags Are Important

The Git SHA tag is the important deployment tag.

Example:

```text
8d6df0cb3dc70942907c2e00cb8059bda1f03ed4
```

This creates a traceable relationship:

```text
Git Commit
    │
    ▼
Docker Image
    │
    ▼
Kubernetes Deployment
```

If a deployment fails, we can identify exactly which source revision produced the image.

This is safer than deploying only:

```text
latest
```

because `latest` is mutable.

---

# 18. Successful Image Build

A successful GitHub Actions run reports the image tags in the Docker Build summary.

Example:

```text
context: .
push: true

tags:
  - ghcr.io/upshivam786/kubernetes-cicd-production-demo:<sha>
  - ghcr.io/upshivam786/kubernetes-cicd-production-demo:latest
```

The Docker build also produces a build record artifact.

---

# 19. Job 3 — Deploy to Kubernetes

The third job is:

```text
deploy
```

It depends on:

```yaml
needs: build-and-push
```

It also runs only for:

```yaml
if: github.event_name == 'push'
```

The job uses:

```yaml
runs-on: self-hosted
```

---

# 20. Why a Self-hosted Runner?

The deployment job needs access to the Kubernetes cluster.

The local Kind cluster is not directly accessible from GitHub-hosted runners.

The self-hosted runner runs in the environment that has:

```text
kubectl
```

configured for the Kind cluster.

Therefore the deployment flow is:

```text
GitHub
   │
   ▼
Self-hosted Runner
   │
   ▼
kubectl
   │
   ▼
Kind Kubernetes Cluster
```

---

# 21. Verify Kubernetes Access

The first deployment step runs:

```bash
kubectl cluster-info
kubectl get nodes
```

This confirms that the runner can communicate with Kubernetes.

If this step fails, the deployment stops immediately.

---

# 22. Update Backend Image

The deployment updates the backend image using:

```bash
kubectl -n fluid-ai set image deployment/backend \
  backend=${{ env.IMAGE_NAME }}:${{ github.sha }}
```

For example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:8d6df0cb3dc70942907c2e00cb8059bda1f03ed4
```

This is the key deployment operation.

---

# 23. Why `kubectl set image`?

The CI/CD pipeline does not modify the entire Kubernetes manifest during deployment.

Instead, it updates only the application image:

```text
Deployment
   │
   └── container image
          │
          ▼
       new Git SHA
```

This keeps the deployment configuration in Git while allowing CI/CD to update the release version.

---

# 24. Kubernetes Rolling Update

Changing the Deployment image causes Kubernetes to create a new ReplicaSet.

The process is approximately:

```text
Current Deployment
       │
       ▼
New ReplicaSet
       │
       ├── New Pod
       │
       ▼
Old Pod removed
       │
       ▼
New Pod
```

Because the backend runs two replicas, Kubernetes can perform a rolling update.

---

# 25. Wait for Rollout

The pipeline runs:

```bash
kubectl -n fluid-ai rollout status deployment/backend --timeout=120s
```

The pipeline waits for the Deployment to become healthy.

If the rollout does not complete within 120 seconds, the job fails.

This prevents CI/CD from reporting a successful deployment while Kubernetes is still unhealthy.

---

# 26. Verify Running Pods

The pipeline checks:

```bash
kubectl -n fluid-ai get pods -l app=backend
```

Expected:

```text
NAME                       READY   STATUS
backend-xxxxx              1/1     Running
backend-yyyyy              1/1     Running
```

---

# 27. Verify the Deployed Image

The pipeline retrieves the actual Deployment image:

```bash
DEPLOYED_IMAGE=$(kubectl -n fluid-ai get deployment backend \
  -o jsonpath='{.spec.template.spec.containers[0].image}')
```

It constructs the expected image:

```bash
EXPECTED_IMAGE="${{ env.IMAGE_NAME }}:${{ github.sha }}"
```

Then compares them:

```bash
if [ "$DEPLOYED_IMAGE" != "$EXPECTED_IMAGE" ]; then
  echo "ERROR: deployed image does not match expected image"
  exit 1
fi
```

This is an important deployment integrity check.

---

# 28. Why Verify the Image?

A successful `kubectl set image` command alone does not provide the strongest possible verification.

The pipeline explicitly checks:

```text
Expected:
ghcr.io/...:<current-git-sha>

Actual:
ghcr.io/...:<running-git-sha>
```

The deployment only passes this stage if both are identical.

This gives a clear chain of evidence:

```text
GitHub Commit
      ↓
GitHub Actions
      ↓
GHCR Image
      ↓
Kubernetes Deployment
      ↓
Expected SHA == Actual SHA
```

---

# 29. Smoke Test

After deployment verification, the pipeline performs an application-level smoke test.

The backend Service is temporarily exposed to the runner using:

```bash
kubectl -n fluid-ai port-forward service/backend 18000:8000
```

The Service listens on:

```text
8000
```

The runner accesses it locally through:

```text
18000
```

---

# 30. Smoke Test Port Forwarding

The port-forward runs in the background:

```bash
kubectl -n fluid-ai port-forward service/backend 18000:8000 \
  > /tmp/backend-port-forward.log 2>&1 &
```

The process ID is stored:

```bash
PF_PID=$!
```

A cleanup function terminates the port-forward after testing:

```bash
cleanup() {
  kill "$PF_PID" 2>/dev/null || true
}
```

The cleanup function is registered:

```bash
trap cleanup EXIT
```

This prevents the background port-forward process from being left behind on the runner.

---

# 31. Smoke Test Health Endpoint

The pipeline waits for:

```text
/healthz
```

It repeatedly checks:

```bash
curl -fsS http://127.0.0.1:18000/healthz
```

The expected response is:

```json
{
  "status": "ok"
}
```

If the backend does not become reachable within the configured retry period, the smoke test fails.

---

# 32. Why Smoke Tests Matter

Kubernetes-level health is not enough.

A Pod can be:

```text
Running
```

while the application itself is broken.

The deployment therefore verifies multiple layers:

```text
Container
   ↓
Pod
   ↓
Deployment
   ↓
Service
   ↓
HTTP endpoint
```

This is much stronger than checking only:

```bash
kubectl get pods
```

---

# 33. CI/CD Quality Gates

The pipeline contains multiple gates.

```text
               ┌──────────────┐
               │ Git Push     │
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────┐
               │ Unit Tests   │
               └──────┬───────┘
                      │
                 success?
                 /     \
               no       yes
               │         │
             STOP        ▼
                  ┌──────────────┐
                  │ Docker Build │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Push to GHCR │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ K8s Deploy   │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Rollout      │
                  │ Verification │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Image Check  │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Smoke Test   │
                  └──────────────┘
```

---

# 34. Deployment Failure Behavior

If tests fail:

```text
Test failure
    ↓
Build skipped
    ↓
Deployment skipped
```

If the Docker build fails:

```text
Build failure
    ↓
Deployment skipped
```

If Kubernetes rollout fails:

```text
Rollout failure
    ↓
Deploy job fails
```

If the deployed image is incorrect:

```text
Image mismatch
    ↓
Deploy job fails
```

If the smoke test fails:

```text
Application failure
    ↓
Deploy job fails
```

---

# 35. GitHub Actions Run Verification

After pushing code:

```bash
git push origin main
```

Open the repository's Actions page and verify the workflow.

The expected jobs are:

```text
Test Application
Build and Push Image
Deploy to Kubernetes
```

All three should complete successfully for a production deployment.

---

# 36. Local Verification Before Push

Before pushing changes, run:

```bash
git diff --check
```

Then:

```bash
pytest -q
```

Then validate the workflow:

```bash
python - <<'PY'
import yaml

with open(".github/workflows/ci.yaml") as f:
    data = yaml.safe_load(f)

print("Workflow YAML: OK")
print("Jobs:", list(data["jobs"].keys()))
PY
```

Then inspect:

```bash
git status
```

This catches formatting, test, and YAML problems before they reach GitHub Actions.

---

# 37. Example Successful Deployment

A successful deployment resulted in the Kubernetes Deployment pointing to a Git SHA image such as:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8ed2333bfeb03a55c7130bb5061580619d
```

The backend Pods were:

```text
backend-7c4c94b8f6-7mhkd   1/1   Running
backend-7c4c94b8f6-kqvzp   1/1   Running
```

This confirmed:

```text
Image published
      ↓
Deployment updated
      ↓
Pods recreated
      ↓
Pods healthy
```

---

# 38. CI/CD Troubleshooting

## Tests fail

Run locally:

```bash
pytest -q
```

Inspect:

```bash
pytest -vv
```

Check application dependencies:

```bash
pip install -r app/requirements.txt
```

---

## Docker build fails

Run locally:

```bash
docker build -t fluid-ai-backend .
```

Check:

```text
Dockerfile
requirements
application imports
build context
```

---

## GHCR push fails

Verify:

```text
permissions:
  packages: write
```

and:

```text
docker/login-action
```

Check that the repository's GitHub Actions token has permission to publish packages.

---

## Kubernetes access fails

Run on the self-hosted runner:

```bash
kubectl cluster-info
kubectl get nodes
```

If this fails, inspect the Kubernetes context:

```bash
kubectl config current-context
```

Then:

```bash
kubectl config get-contexts
```

---

## Deployment does not roll out

Run:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Then:

```bash
kubectl get pods -n fluid-ai
```

Then:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Then:

```bash
kubectl logs <pod-name> -n fluid-ai
```

---

## ImagePullBackOff

Check:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Verify:

```bash
kubectl get secret ghcr-pull-secret -n fluid-ai
```

Check the Deployment:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

---

## Smoke test fails

First verify:

```bash
kubectl get pods -n fluid-ai -l app=backend
```

Then:

```bash
kubectl get svc backend -n fluid-ai
```

Then manually port-forward:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

Then:

```bash
curl -i http://127.0.0.1:8002/healthz
```

and:

```bash
curl -i http://127.0.0.1:8002/readyz
```

---

# 39. Deployment Rollback

If a release is unhealthy:

```bash
kubectl rollout history deployment/backend -n fluid-ai
```

Rollback:

```bash
kubectl rollout undo deployment/backend -n fluid-ai
```

Wait:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Verify:

```bash
kubectl get pods -n fluid-ai -l app=backend
```

Verify the restored image:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

---

# 40. Production Practices Demonstrated

This CI/CD implementation demonstrates:

* Automated testing
* Test gates before deployment
* Docker image creation
* GHCR integration
* Git SHA image versioning
* Self-hosted Kubernetes deployment
* Automated rolling updates
* Deployment timeout handling
* Running image verification
* Application smoke testing
* Kubernetes health checks
* Deployment rollback
* Separation between Pull Request validation and production deployment

---

# 41. End-to-End Release Procedure

The normal release process is:

```bash
git status
git diff --check
pytest -q
git add .
git commit -m "feat: ..."
git push origin main
```

GitHub Actions then performs:

```text
1. Checkout
2. Install Python
3. Install dependencies
4. Run tests
5. Build Docker image
6. Push image to GHCR
7. Connect to Kubernetes
8. Update backend image
9. Wait for rollout
10. Verify deployed image
11. Run smoke test
12. Mark deployment successful
```

---

# 42. Final CI/CD Checklist

```text
[ ] Workflow YAML is valid
[ ] Tests pass
[ ] Pull Requests run tests
[ ] Main pushes trigger deployment
[ ] GHCR authentication works
[ ] Docker image builds
[ ] Git SHA image is pushed
[ ] Self-hosted runner has kubectl access
[ ] Kubernetes rollout succeeds
[ ] Expected image is deployed
[ ] Backend Pods are Ready
[ ] Smoke test succeeds
[ ] Failed deployments stop the pipeline
[ ] Rollback procedure is documented
```

---

# 43. Related Documentation

* `README.md` — Project introduction and quick start
* `docs/01-project-overview.md` — Project goals and scope
* `docs/02-architecture.md` — System architecture
* `docs/03-local-setup.md` — Local development setup
* `docs/04-kubernetes-deployment.md` — Kubernetes deployment
* `docs/05-cicd-pipeline.md` — CI/CD pipeline
* `docs/06-monitoring-observability.md` — Prometheus and Grafana
* `docs/07-troubleshooting.md` — Troubleshooting
* `docs/08-operations-runbook.md` — Day-2 operations
