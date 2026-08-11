# Fluid AI DevOps Challenge — Kubernetes Deployment Guide

This document describes how the application is deployed to a local Kubernetes cluster using Kind.

It covers:

* Kind cluster preparation
* Kubernetes namespaces
* PostgreSQL deployment
* Backend Deployment
* Kubernetes Service
* Secrets
* Private GitHub Container Registry authentication
* Health and readiness probes
* Resource requests and limits
* Image versioning
* Rolling deployments
* Rollout verification
* Rollback
* Troubleshooting common Kubernetes failures

---

# 1. Kubernetes Architecture

The application runs in the `fluid-ai` namespace.

The basic architecture is:

```text
                         Kubernetes Cluster
                                │
                         ┌──────┴──────┐
                         │  fluid-ai   │
                         │  namespace  │
                         └──────┬──────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
       ┌──────▼──────┐                    ┌──────▼──────┐
       │   Backend   │                    │  PostgreSQL │
       │ Deployment  │                    │ Deployment  │
       │  replicas:2 │                    │  replicas:1 │
       └──────┬──────┘                    └──────┬──────┘
              │                                  │
       ┌──────▼──────┐                    ┌──────▼──────┐
       │   Backend   │                    │  PostgreSQL │
       │   Service   │                    │   Service   │
       │  ClusterIP  │                    │  ClusterIP  │
       └─────────────┘                    └─────────────┘
```

The backend communicates with PostgreSQL through the Kubernetes Service name:

```text
postgres:5432
```

---

# 2. Kind Cluster

The project uses Kind to provide a local Kubernetes cluster.

Check the available nodes:

```bash
kubectl get nodes
```

Expected output:

```text
NAME                     STATUS   ROLES
fluid-ai-control-plane   Ready    control-plane
```

Check the Kubernetes version:

```bash
kubectl version
```

The cluster used during development was a single-node Kind cluster.

---

# 3. Verify Kubernetes Connectivity

Before deploying anything:

```bash
kubectl cluster-info
```

Then:

```bash
kubectl get nodes
```

The node must report:

```text
Ready
```

If the node is not Ready, application deployment should not continue until the cluster problem is resolved.

---

# 4. Kubernetes Namespace

The application is isolated inside a dedicated namespace:

```text
fluid-ai
```

List namespaces:

```bash
kubectl get namespaces
```

Create the namespace if it does not exist:

```bash
kubectl create namespace fluid-ai
```

Verify:

```bash
kubectl get namespace fluid-ai
```

Expected:

```text
NAME        STATUS
fluid-ai    Active
```

---

# 5. PostgreSQL Deployment

PostgreSQL runs inside the `fluid-ai` namespace.

Check the PostgreSQL Pod:

```bash
kubectl get pods -n fluid-ai
```

Check the PostgreSQL Service:

```bash
kubectl get svc -n fluid-ai
```

The PostgreSQL Service exposes:

```text
5432/TCP
```

The backend uses the Kubernetes DNS name:

```text
postgres
```

Therefore:

```text
DB_HOST=postgres
DB_PORT=5432
```

---

# 6. Backend Deployment

The backend Kubernetes manifest is:

```text
k8s/backend.yaml
```

It contains both:

```text
Deployment
Service
```

Apply the manifest:

```bash
kubectl apply -f k8s/backend.yaml
```

Before applying it, validate the manifest:

```bash
kubectl apply --dry-run=client -f k8s/backend.yaml
```

Expected:

```text
deployment.apps/backend configured (dry run)
service/backend configured (dry run)
```

---

# 7. Backend Deployment Configuration

The backend Deployment uses:

```yaml
replicas: 2
```

This means Kubernetes attempts to keep two backend Pods running.

The Pods use the label:

```text
app=backend
```

The Deployment selector matches:

```text
app=backend
```

The Service also selects:

```text
app=backend
```

This creates the following relationship:

```text
Deployment
    │
    ├── backend Pod
    │
    └── backend Pod
          │
          ▼
      app=backend
          │
          ▼
       Service
```

---

# 8. Container Image

The production-style Kubernetes Deployment uses a GitHub Container Registry image:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo
```

The CI/CD pipeline publishes images using Git commit SHA tags.

Example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8ed2333bfeb03a55c7130bb5061580619d
```

This is preferable to relying only on:

```text
latest
```

because every deployed image can be traced back to an exact Git commit.

---

# 9. Image Pull Policy

The backend uses:

```yaml
imagePullPolicy: Always
```

This ensures Kubernetes checks the registry for the referenced image when creating a new Pod.

For production-style deployments, immutable Git SHA tags are used:

```text
:<git-sha>
```

rather than depending on a mutable `latest` tag.

---

# 10. Private GHCR Authentication

The GitHub Container Registry image was configured as private.

A Kubernetes image pull Secret is therefore required.

The Secret is:

```text
ghcr-pull-secret
```

Verify it:

```bash
kubectl get secret ghcr-pull-secret -n fluid-ai
```

Expected type:

```text
kubernetes.io/dockerconfigjson
```

---

# 11. Creating the GHCR Pull Secret

The Secret was created using:

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --namespace fluid-ai \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password='<github-token>'
```

The token must have permission to read the package.

For security, do not commit the token into Git.

Do not put it directly into:

```text
k8s/backend.yaml
```

---

# 12. Referencing the Pull Secret

The Deployment references:

```yaml
imagePullSecrets:
  - name: ghcr-pull-secret
```

The effective Pod configuration can be checked with:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.imagePullSecrets[*].name}{"\n"}'
```

Expected:

```text
ghcr-pull-secret
```

---

# 13. Verify the Exact Image

Check the Deployment:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Example:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:4cb39c8ed2333bfeb03a55c7130bb5061580619d
```

Check the actual image digest used by the running Pods:

```bash
kubectl get pods -n fluid-ai -l app=backend \
  -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

Example:

```text
backend-xxxxx -> ghcr.io/upshivam786/kubernetes-cicd-production-demo@sha256:<digest>
backend-yyyyy -> ghcr.io/upshivam786/kubernetes-cicd-production-demo@sha256:<digest>
```

The image tag identifies the Git version.

The image digest identifies the exact immutable image content.

---

# 14. Database Environment Variables

The backend receives database configuration through environment variables.

The host and port are configured directly:

```yaml
- name: DB_HOST
  value: postgres

- name: DB_PORT
  value: "5432"
```

Sensitive database credentials are loaded from the Kubernetes Secret:

```text
backend-db
```

The variables are:

```text
DB_NAME
DB_USER
DB_PASSWORD
```

---

# 15. Kubernetes Database Secret

Check the Secret:

```bash
kubectl get secret backend-db -n fluid-ai
```

Expected:

```text
NAME         TYPE     DATA
backend-db   Opaque   3
```

The values should not be printed or committed to source control.

Inspecting the Secret object metadata is safe:

```bash
kubectl describe secret backend-db -n fluid-ai
```

Avoid displaying decoded credentials in logs or documentation.

---

# 16. Resource Requests

The backend defines:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
```

Requests tell Kubernetes the minimum amount of resources required for scheduling.

Conceptually:

```text
CPU request:
100 millicores

Memory request:
128 MiB
```

---

# 17. Resource Limits

The backend defines:

```yaml
limits:
  cpu: 500m
  memory: 256Mi
```

This establishes an upper resource boundary.

Therefore the backend configuration is:

```text
CPU:
request = 100m
limit   = 500m

Memory:
request = 128Mi
limit   = 256Mi
```

---

# 18. Container Port

The backend container exposes:

```yaml
containerPort: 8000
```

The port is named:

```text
http
```

This name is later used by the Kubernetes health probes and ServiceMonitor.

---

# 19. Liveness Probe

The Deployment defines:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: http
```

Kubernetes calls:

```text
GET /healthz
```

A successful response is:

```json
{
  "status": "ok"
}
```

The liveness probe determines whether the container is still functioning.

If the liveness probe repeatedly fails, Kubernetes can restart the container.

---

# 20. Readiness Probe

The Deployment defines:

```yaml
readinessProbe:
  httpGet:
    path: /readyz
    port: http
```

The endpoint checks database connectivity.

Healthy response:

```json
{
  "status": "ready"
}
```

The readiness probe determines whether the Pod should receive Service traffic.

This distinction is important:

```text
Liveness
    ↓
"Is the application alive?"

Readiness
    ↓
"Can the application currently serve traffic?"
```

---

# 21. Probe Timing

The liveness probe uses:

```text
initialDelaySeconds: 10
periodSeconds: 10
timeoutSeconds: 2
failureThreshold: 3
```

The readiness probe uses:

```text
initialDelaySeconds: 5
periodSeconds: 5
timeoutSeconds: 2
failureThreshold: 3
```

This prevents Kubernetes from immediately declaring a newly started application unhealthy.

---

# 22. Verify Probes

Inspect the Deployment:

```bash
kubectl describe deployment backend -n fluid-ai
```

Inspect a Pod:

```bash
kubectl describe pod <backend-pod> -n fluid-ai
```

Look for:

```text
Liveness
Readiness
```

The Pod should eventually show:

```text
Ready: True
```

---

# 23. Backend Service

The backend Service is:

```text
backend
```

Check it:

```bash
kubectl get svc backend -n fluid-ai
```

Expected:

```text
NAME      TYPE        CLUSTER-IP      PORT(S)
backend   ClusterIP   <cluster-ip>    8000/TCP
```

The Service uses:

```text
selector:
  app=backend
```

---

# 24. Named Service Port

The backend Service exposes a named port:

```yaml
ports:
  - name: http
    port: 8000
    targetPort: 8000
```

The named port is useful because other Kubernetes resources can reference:

```text
port: http
```

instead of hard-coding the numeric port.

This is particularly useful for the Prometheus ServiceMonitor.

---

# 25. Verify Service Endpoints

Check:

```bash
kubectl get endpoints backend -n fluid-ai
```

Or on newer Kubernetes versions:

```bash
kubectl get endpointslice -n fluid-ai
```

The Service should have endpoints corresponding to the backend Pods.

If there are no endpoints, check:

```bash
kubectl get pods -n fluid-ai --show-labels
```

and compare the Pod labels with:

```text
app=backend
```

---

# 26. Local Access Through Port Forwarding

The backend Service is a ClusterIP Service and is therefore not directly exposed outside the cluster.

For local testing:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

Then:

```bash
curl -i http://127.0.0.1:8002/healthz
```

Expected:

```text
HTTP/1.1 200 OK
```

Test readiness:

```bash
curl -i http://127.0.0.1:8002/readyz
```

Test application:

```bash
curl -i http://127.0.0.1:8002/items
```

Test metrics:

```bash
curl -i http://127.0.0.1:8002/metrics
```

---

# 27. Handling Local Port Conflicts

If port `8001` or another local port is already occupied:

```text
bind: address already in use
```

do not need to terminate the existing process.

Find the process:

```bash
sudo lsof -i :8001
```

Then simply choose another local port:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

The mapping is:

```text
Local port : Kubernetes Service port
8002       : 8000
```

---

# 28. Deployment Rollout

After changing the Deployment:

```bash
kubectl apply -f k8s/backend.yaml
```

Check rollout:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Successful result:

```text
deployment "backend" successfully rolled out
```

Check Pods:

```bash
kubectl get pods -n fluid-ai -l app=backend
```

Expected:

```text
READY   STATUS
1/1     Running
1/1     Running
```

---

# 29. Rolling Update

Kubernetes updates the Pods gradually rather than removing all replicas at once.

Conceptually:

```text
Old version
Pod A
Pod B

       ↓

New version
Pod A → updated
Pod B → old

       ↓

New version
Pod A → updated
Pod B → updated
```

This provides a basic zero-downtime deployment strategy for the two-replica backend.

---

# 30. Deployment History

View Deployment revisions:

```bash
kubectl rollout history deployment/backend -n fluid-ai
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

The revision history provides a record of previous Deployment states.

---

# 31. Rollback

If a deployment introduces a problem, inspect the history:

```bash
kubectl rollout history deployment/backend -n fluid-ai
```

Rollback to the previous revision:

```bash
kubectl rollout undo deployment/backend -n fluid-ai
```

Wait for the rollback:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Verify:

```bash
kubectl get pods -n fluid-ai -l app=backend
```

Verify the image:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

---

# 32. Image-Based Rollback

Because CI/CD uses Git SHA image tags, a specific known-good version can also be deployed explicitly:

```bash
kubectl -n fluid-ai set image deployment/backend \
  backend=ghcr.io/upshivam786/kubernetes-cicd-production-demo:<known-good-sha>
```

Then:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

This provides a direct mapping:

```text
Git commit
    ↓
Container image tag
    ↓
Kubernetes Deployment
    ↓
Running Pods
```

---

# 33. Deployment Verification

After deployment, perform:

```bash
kubectl get deployment backend -n fluid-ai
```

Then:

```bash
kubectl get pods -n fluid-ai -l app=backend
```

Then:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Then:

```bash
kubectl get svc backend -n fluid-ai
```

Finally test:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

and:

```bash
curl -s http://127.0.0.1:8002/healthz
curl -s http://127.0.0.1:8002/readyz
curl -s http://127.0.0.1:8002/items
curl -s http://127.0.0.1:8002/metrics
```

---

# 34. Common Kubernetes Failure: ImagePullBackOff

If Pods show:

```text
ImagePullBackOff
```

or:

```text
ErrImagePull
```

inspect the Pod:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Look at the Events section.

Common causes:

* Incorrect image name
* Incorrect image tag
* Private GHCR package
* Missing `imagePullSecrets`
* Invalid registry credentials
* Package permissions
* Registry connectivity

Verify:

```bash
kubectl get secret ghcr-pull-secret -n fluid-ai
```

Verify the Deployment references it:

```bash
kubectl get deployment backend -n fluid-ai \
  -o jsonpath='{.spec.template.spec.imagePullSecrets[*].name}{"\n"}'
```

---

# 35. Common Failure: CrashLoopBackOff

If the Pod shows:

```text
CrashLoopBackOff
```

check logs:

```bash
kubectl logs <pod-name> -n fluid-ai
```

For the previous crashed container:

```bash
kubectl logs <pod-name> -n fluid-ai --previous
```

Then inspect:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Common causes include:

* Invalid environment variables
* Database connection failure
* Application startup failure
* Missing dependency
* Incorrect container command
* Configuration errors

---

# 36. Common Failure: Readiness Probe Failure

If Pods are:

```text
Running
```

but:

```text
READY 0/1
```

check:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

Then test the application:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

and:

```bash
curl -i http://127.0.0.1:8002/readyz
```

If `/readyz` returns:

```text
503
```

the database connection should be investigated.

---

# 37. Common Failure: Service Has No Endpoints

Check:

```bash
kubectl get endpoints backend -n fluid-ai
```

If there are no endpoints, inspect Pod labels:

```bash
kubectl get pods -n fluid-ai --show-labels
```

The Service expects:

```text
app=backend
```

The Deployment Pods must have:

```yaml
labels:
  app: backend
```

The Service selector must match:

```yaml
selector:
  app: backend
```

---

# 38. Common Failure: Local Port Already in Use

Error:

```text
bind: address already in use
```

Check:

```bash
sudo lsof -i :8001
```

Use another port:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

No Kubernetes configuration change is required.

---

# 39. Common Failure: Deployment Does Not Roll Out

Check:

```bash
kubectl rollout status deployment/backend -n fluid-ai
```

Then:

```bash
kubectl describe deployment backend -n fluid-ai
```

Then:

```bash
kubectl get pods -n fluid-ai
```

Then inspect the relevant Pod:

```bash
kubectl describe pod <pod-name> -n fluid-ai
```

And:

```bash
kubectl logs <pod-name> -n fluid-ai
```

This gives a layered debugging path:

```text
Deployment
    ↓
ReplicaSet
    ↓
Pod
    ↓
Container
    ↓
Application logs
```

---

# 40. Kubernetes Debugging Command Set

## Cluster

```bash
kubectl cluster-info
kubectl get nodes
kubectl get namespaces
```

## Namespace

```bash
kubectl get all -n fluid-ai
```

## Deployment

```bash
kubectl get deployment backend -n fluid-ai
kubectl describe deployment backend -n fluid-ai
kubectl rollout status deployment/backend -n fluid-ai
kubectl rollout history deployment/backend -n fluid-ai
```

## Pods

```bash
kubectl get pods -n fluid-ai
kubectl get pods -n fluid-ai -l app=backend
kubectl describe pod <pod-name> -n fluid-ai
kubectl logs <pod-name> -n fluid-ai
```

## Service

```bash
kubectl get svc -n fluid-ai
kubectl describe svc backend -n fluid-ai
kubectl get endpoints backend -n fluid-ai
```

## Secrets

```bash
kubectl get secrets -n fluid-ai
kubectl describe secret backend-db -n fluid-ai
kubectl describe secret ghcr-pull-secret -n fluid-ai
```

---

# 41. Recommended Deployment Verification Sequence

After every deployment:

```bash
kubectl apply --dry-run=client -f k8s/backend.yaml

kubectl apply -f k8s/backend.yaml

kubectl rollout status deployment/backend -n fluid-ai

kubectl get deployment backend -n fluid-ai

kubectl get pods -n fluid-ai -l app=backend

kubectl get svc backend -n fluid-ai

kubectl get endpoints backend -n fluid-ai
```

Then test:

```bash
kubectl port-forward -n fluid-ai service/backend 8002:8000
```

and:

```bash
curl -s http://127.0.0.1:8002/healthz
curl -s http://127.0.0.1:8002/readyz
curl -s http://127.0.0.1:8002/items
curl -s http://127.0.0.1:8002/metrics
```

---

# 42. Production-Style Principles Demonstrated

The Kubernetes implementation demonstrates several production-oriented practices:

### Declarative configuration

Kubernetes resources are stored as YAML:

```text
k8s/backend.yaml
```

### Multiple replicas

```text
replicas: 2
```

### Health checks

```text
/healthz
/readyz
```

### Resource management

```text
requests
limits
```

### Private registry authentication

```text
ghcr-pull-secret
```

### Immutable image versions

```text
:<git-sha>
```

### Rolling deployment

```text
kubectl rollout status
```

### Rollback support

```text
kubectl rollout undo
```

### Internal service discovery

```text
backend
postgres
```

### Monitoring integration

```text
/metrics
ServiceMonitor
Prometheus
```

---

# 43. Final Kubernetes Checklist

Before considering the Kubernetes deployment healthy:

```text
[ ] Kind cluster is Ready
[ ] fluid-ai namespace exists
[ ] PostgreSQL Pod is Running
[ ] PostgreSQL Service exists
[ ] backend-db Secret exists
[ ] ghcr-pull-secret exists
[ ] Backend Deployment exists
[ ] Backend has two replicas
[ ] Backend Pods are Running
[ ] Backend Pods are Ready
[ ] Backend Service exists
[ ] Service selector matches Pod labels
[ ] Service has endpoints
[ ] Liveness probe succeeds
[ ] Readiness probe succeeds
[ ] /healthz returns 200
[ ] /readyz returns 200
[ ] /items responds
[ ] /metrics responds
[ ] Running image uses expected Git SHA
[ ] Deployment rollout succeeds
[ ] Rollback procedure is understood
```

---

# 44. Related Documentation

* `README.md` — Project introduction and quick start
* `docs/01-project-overview.md` — Project goals and scope
* `docs/02-architecture.md` — System architecture
* `docs/03-local-setup.md` — Local development setup
* `docs/04-kubernetes-deployment.md` — Kubernetes deployment
* `docs/05-cicd-pipeline.md` — CI/CD pipeline
* `docs/06-monitoring-observability.md` — Monitoring and observability
* `docs/07-troubleshooting.md` — Troubleshooting
* `docs/08-operations-runbook.md` — Day-2 operations
