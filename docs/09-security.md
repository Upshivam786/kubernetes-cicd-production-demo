# Fluid AI DevOps Challenge — Security

## 1. Purpose

This document describes the security controls, practices, risks, and recommended improvements implemented or identified in the Fluid AI DevOps Challenge.

The project uses:

* Docker
* Kubernetes
* GitHub Actions
* GitHub Container Registry
* Kubernetes Secrets
* Prometheus
* Grafana
* PostgreSQL
* FastAPI

Security is considered across the application, container, Kubernetes, CI/CD, registry, secrets, and observability layers.

---

# 2. Security Model

The main security boundaries are:

```text
Developer
   │
   ▼
GitHub Repository
   │
   ▼
GitHub Actions
   │
   ├── Test
   ├── Build
   └── Push
        │
        ▼
GitHub Container Registry
        │
        │ authenticated image pull
        ▼
Kubernetes
   │
   ├── Backend
   ├── PostgreSQL
   └── Monitoring
```

Each boundary introduces different security considerations.

---

# 3. Security Principles

The project follows these general principles:

### Least privilege

Give users, workloads, and CI/CD jobs only the permissions they need.

### Secrets should not be committed

Passwords, tokens, private keys, and registry credentials should never be stored directly in Git.

### Immutable releases

Use Git commit SHA image tags so deployments can be traced to source code.

### Defense in depth

Security should not depend on a single control.

### Observability

Security-relevant failures should be visible through logs, metrics, and Kubernetes events.

### Reproducibility

Infrastructure and deployment configuration should be represented as code.

---

# 4. Git Repository Security

The repository contains:

```text
app/
tests/
k8s/
docs/
Dockerfile
README.md
```

Sensitive values should not be committed.

Before committing changes:

```bash
git diff --check
```

Review staged content:

```bash
git diff --cached
```

Check repository state:

```bash
git status
```

---

# 5. Secret Management

Application credentials should be supplied through environment variables or Kubernetes Secrets rather than hardcoded values.

Example variables:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
```

The application should not contain production credentials directly in Python source code.

---

# 6. Kubernetes Secrets

The Kubernetes deployment uses a Secret for sensitive database configuration.

Check whether the Secret exists:

```bash
kubectl get secrets -n fluid-ai
```

Inspect metadata without printing secret values:

```bash
kubectl describe secret backend-db -n fluid-ai
```

Do not expose secret contents unnecessarily.

Avoid:

```bash
kubectl get secret backend-db \
  -n fluid-ai \
  -o yaml
```

when the output is being copied into tickets, chat, GitHub issues, or documentation.

---

# 7. Secret Handling Rules

Never commit:

```text
.env
.env.*
*.pem
*.key
credentials.json
service-account.json
registry passwords
API tokens
database passwords
private keys
```

Use `.gitignore` where appropriate.

Example:

```gitignore
.env
.env.*
*.pem
*.key
credentials.json
```

Be careful with broad patterns because some environment files may be intentionally required as examples.

---

# 8. GitHub Container Registry Security

The application image is published to:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo
```

The Kubernetes cluster pulls the image using registry authentication.

The authentication Secret should be present in the application namespace:

```bash
kubectl get secret \
  ghcr-pull-secret \
  -n fluid-ai
```

Verify the Secret type:

```bash
kubectl get secret \
  ghcr-pull-secret \
  -n fluid-ai \
  -o jsonpath='{.type}{"\n"}'
```

Expected:

```text
kubernetes.io/dockerconfigjson
```

---

# 9. Image Pull Authentication

Verify that the backend Deployment references the registry Secret:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.imagePullSecrets[*].name}{"\n"}'
```

Expected:

```text
ghcr-pull-secret
```

This allows Kubernetes to authenticate to GHCR when pulling a private image.

---

# 10. Image Tagging Strategy

The CI/CD pipeline publishes images using the Git commit SHA:

```text
ghcr.io/upshivam786/kubernetes-cicd-production-demo:<git-sha>
```

It also publishes:

```text
latest
```

The immutable SHA tag is preferred for deployment traceability.

For example:

```text
4cb39c8ed2333bfeb03a55c7130bb5061580619d
```

allows the deployed container to be associated with a specific Git commit.

---

# 11. Why SHA Tags Matter

Using only:

```text
latest
```

creates ambiguity.

For example:

```text
latest
```

can refer to different images at different points in time.

Using:

```text
:<git-sha>
```

provides:

```text
Git commit
     ↓
Docker image
     ↓
Kubernetes Deployment
     ↓
Running Pod
```

This creates a traceable release chain.

---

# 12. Verify the Running Image

Use:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Verify the actual image used by Pods:

```bash
kubectl get pods \
  -n fluid-ai \
  -l app=backend \
  -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

---

# 13. Container Security

The Docker image should follow container security best practices.

Recommended controls include:

* minimal base image
* non-root execution
* pinned dependencies
* no embedded credentials
* deterministic builds
* vulnerability scanning
* small image footprint

The Dockerfile should be reviewed periodically as the project evolves.

---

# 14. Dependency Security

Python dependencies are pinned in:

```text
app/requirements.txt
```

Example:

```text
fastapi
sqlalchemy
psycopg2-binary
pytest
httpx
prometheus-fastapi-instrumentator
```

Pinned versions improve reproducibility.

Dependency upgrades should be tested before deployment.

---

# 15. Dependency Vulnerability Checks

For production use, integrate a dependency scanner such as:

```text
pip-audit
Trivy
Dependabot
GitHub dependency scanning
```

Example local check:

```bash
pip-audit
```

This should be integrated into CI/CD as the project matures.

---

# 16. Container Image Scanning

A production-oriented pipeline should scan the built image before publishing or deploying it.

A common choice is Trivy.

Example:

```bash
trivy image \
  ghcr.io/upshivam786/kubernetes-cicd-production-demo:<git-sha>
```

The CI pipeline can enforce a policy such as:

```text
HIGH/CRITICAL vulnerabilities
        ↓
     fail build
```

The exact severity policy should be defined according to organizational risk tolerance.

---

# 17. Kubernetes Namespace Isolation

The application runs in:

```text
fluid-ai
```

Monitoring runs in:

```text
monitoring
```

This provides logical isolation between application and observability resources.

Check:

```bash
kubectl get namespaces
```

Expected:

```text
fluid-ai
monitoring
```

---

# 18. Kubernetes Service Exposure

The backend Service is:

```text
ClusterIP
```

Check:

```bash
kubectl get service backend -n fluid-ai
```

A ClusterIP Service is internally accessible inside the Kubernetes cluster.

This is preferable to exposing PostgreSQL directly outside the cluster.

---

# 19. Database Exposure

PostgreSQL is also exposed through:

```text
ClusterIP
```

Check:

```bash
kubectl get service postgres -n fluid-ai
```

The database should not be exposed publicly unless there is a specific operational requirement and appropriate network controls.

---

# 20. Kubernetes RBAC

Kubernetes Role-Based Access Control should be used to restrict what workloads and users can do.

Inspect existing RBAC:

```bash
kubectl get roles -A
```

```bash
kubectl get rolebindings -A
```

Cluster-wide permissions:

```bash
kubectl get clusterroles
```

```bash
kubectl get clusterrolebindings
```

---

# 21. Least-Privilege RBAC

The backend application should not automatically receive administrative Kubernetes permissions.

Avoid giving application Pods:

```text
cluster-admin
```

unless there is a clearly documented requirement.

A production implementation should create a dedicated ServiceAccount with only the permissions required by the application.

---

# 22. Service Accounts

Inspect:

```bash
kubectl get serviceaccounts \
  -n fluid-ai
```

Check the backend Deployment:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}'
```

If no custom ServiceAccount is specified, Kubernetes uses the namespace's default ServiceAccount.

For production hardening, consider creating a dedicated ServiceAccount.

---

# 23. Pod Security

Production workloads should consider:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
```

Additional hardening may include:

```yaml
securityContext:
  capabilities:
    drop:
      - ALL
```

and:

```yaml
seccompProfile:
  type: RuntimeDefault
```

These controls should be validated against application requirements before enabling them.

---

# 24. Read-Only Root Filesystem

Where supported, consider:

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

This prevents the container from modifying its root filesystem.

If the application requires temporary files, use an appropriate writable volume such as:

```yaml
emptyDir: {}
```

instead of making the entire filesystem writable.

---

# 25. Network Security

A production Kubernetes implementation should consider NetworkPolicies.

Example desired model:

```text
Internet
   │
   ▼
Ingress
   │
   ▼
Backend
   │
   ▼
PostgreSQL
```

Unnecessary communication paths should be blocked.

For example:

```text
Backend → PostgreSQL       ALLOW
Backend → arbitrary Pods   DENY
External → PostgreSQL      DENY
```

---

# 26. NetworkPolicy

Check whether NetworkPolicies exist:

```bash
kubectl get networkpolicies -A
```

If none exist, this is an identified production-hardening opportunity.

A future implementation should define:

* backend ingress policy
* backend egress policy
* PostgreSQL ingress policy
* monitoring access policy

---

# 27. CI/CD Permissions

GitHub Actions should follow least privilege.

The workflow should request only the permissions required for:

```text
source checkout
image build
GHCR authentication
image push
Kubernetes deployment
```

Avoid unnecessary:

```text
write-all
```

permissions.

---

# 28. GitHub Actions Secret Handling

Credentials used by CI/CD should be stored in:

```text
GitHub Actions Secrets
```

rather than hardcoded in:

```text
.github/workflows/*.yaml
```

Never write:

```yaml
password: my-real-password
```

into a workflow.

Use:

```yaml
${{ secrets.SOME_SECRET }}
```

instead.

---

# 29. CI/CD Token Scope

Registry credentials should have only the permissions required for image publishing.

For GitHub Container Registry, prefer modern GitHub authentication mechanisms where possible.

Avoid long-lived personal credentials when short-lived or workflow-scoped credentials can be used.

---

# 30. Deployment Credentials

Kubernetes deployment credentials should also be protected.

A production architecture should avoid placing a powerful kubeconfig directly into repository files.

Deployment access should be:

* scoped
* auditable
* rotated
* stored as secrets
* limited to the required namespace/resources

---

# 31. TLS

The current local Kind environment primarily demonstrates internal Kubernetes communication and port-forwarded administrative access.

A production deployment should provide TLS for externally exposed services.

Recommended architecture:

```text
Client
  │
 HTTPS
  ▼
Ingress
  │
 TLS termination
  ▼
Backend Service
```

Tools such as cert-manager can automate certificate management.

---

# 32. Prometheus Security

Prometheus exposes operational data.

Prometheus should not be exposed publicly without authentication and network controls.

Current local access uses:

```bash
kubectl port-forward
```

which is appropriate for local development and debugging.

---

# 33. Grafana Security

Grafana should also be protected.

The default administrative password should be changed for any persistent production deployment.

Never commit:

```text
Grafana password
Grafana API token
Grafana session secret
```

to Git.

---

# 34. Alertmanager Security

Alertmanager can contain sensitive operational information and notification destinations.

Protect:

* webhook URLs
* SMTP credentials
* notification tokens
* receiver configuration

These should be managed as secrets where appropriate.

---

# 35. Monitoring as a Security Control

Monitoring is not only for performance.

Metrics can help detect:

* sudden traffic spikes
* application failures
* repeated readiness failures
* Pod restarts
* abnormal resource consumption
* unexpected error rates

For example:

```promql
up{job="backend"}
```

shows whether Prometheus can successfully scrape the backend.

---

# 36. Application Health Security

The backend exposes:

```text
/healthz
/readyz
/metrics
```

These endpoints should be considered when defining production ingress rules.

Health endpoints may be publicly reachable only if required.

Metrics endpoints should generally be restricted to the monitoring system.

---

# 37. Database Security

PostgreSQL security should include:

* strong credentials
* restricted network access
* encrypted connections where required
* regular backups
* controlled database users
* least-privilege database permissions
* credential rotation

The application should not connect using a PostgreSQL superuser.

---

# 38. Database User Permissions

The application database user should ideally have only the permissions required by the application.

Avoid using:

```text
postgres
```

as the application identity.

Prefer a dedicated user such as:

```text
appuser
```

with application-specific privileges.

---

# 39. Secrets in Documentation

Documentation should explain:

```text
Secret name
Purpose
Creation process
Rotation process
Verification command
```

It should never contain:

```text
actual password
actual token
actual private key
```

Example:

```bash
kubectl get secret backend-db -n fluid-ai
```

is safe for documentation.

Dumping its decoded password into documentation is not.

---

# 40. Security Verification Checklist

Before a production-style release:

```text
[ ] No secrets committed to Git
[ ] .env files ignored
[ ] Registry credentials protected
[ ] Image uses immutable SHA tag
[ ] Dependencies pinned
[ ] Dependency vulnerabilities scanned
[ ] Container image scanned
[ ] Container runs as non-root
[ ] Privilege escalation disabled
[ ] Linux capabilities minimized
[ ] Kubernetes RBAC reviewed
[ ] Dedicated ServiceAccount considered
[ ] NetworkPolicies configured
[ ] Database not publicly exposed
[ ] Metrics endpoint restricted
[ ] Grafana protected
[ ] Prometheus protected
[ ] TLS configured for external traffic
[ ] CI/CD permissions minimized
[ ] Deployment credentials protected
[ ] Secrets have rotation strategy
```

---

# 41. Current Project Security Posture

The project already demonstrates several useful security practices:

```text
✓ Kubernetes namespaces
✓ Kubernetes Secrets
✓ GHCR image authentication
✓ Immutable Git SHA image tags
✓ ClusterIP internal services
✓ Separate monitoring namespace
✓ Dependency pinning
✓ CI/CD separation
✓ No requirement to expose PostgreSQL publicly
```

Additional hardening should be treated as future production work rather than claiming controls that have not yet been implemented.

---

# 42. Recommended Security Roadmap

## Phase 1 — Current

```text
Secrets
Namespaces
GHCR authentication
SHA image tags
Internal Services
```

## Phase 2 — Container Hardening

```text
Non-root containers
Read-only filesystem
Drop capabilities
Seccomp
Image scanning
Dependency scanning
```

## Phase 3 — Kubernetes Hardening

```text
RBAC
Dedicated ServiceAccounts
NetworkPolicies
Pod Security Standards
Resource limits
Security contexts
```

## Phase 4 — Production Security

```text
TLS
Ingress security
Secret rotation
External secret manager
Audit logging
Centralized security monitoring
Backup and disaster recovery
```

---

# 43. Security Incident Procedure

If a credential is accidentally exposed:

### Step 1

Immediately revoke the credential.

### Step 2

Create a replacement credential.

### Step 3

Update the Kubernetes/GitHub Secret.

### Step 4

Restart affected workloads if required.

### Step 5

Check logs for unauthorized use.

### Step 6

Remove the credential from the repository history where appropriate.

### Step 7

Document the incident and corrective action.

Never assume deleting the secret from the latest Git commit is sufficient if it existed in Git history.

---

# 44. Security Review Commands

Check Secrets:

```bash
kubectl get secrets -A
```

Check RBAC:

```bash
kubectl get roles -A
kubectl get rolebindings -A
kubectl get clusterroles
kubectl get clusterrolebindings
```

Check NetworkPolicies:

```bash
kubectl get networkpolicies -A
```

Check ServiceAccounts:

```bash
kubectl get serviceaccounts -A
```

Check Pod security contexts:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o yaml
```

Check image:

```bash
kubectl get deployment backend \
  -n fluid-ai \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

---

# 45. Security Philosophy

The project should be considered **production-style**, not automatically production-ready.

Production readiness requires environment-specific controls such as:

* identity management
* TLS
* network policies
* hardened containers
* centralized secret management
* vulnerability scanning
* backup and recovery
* audit logging
* compliance requirements
* incident response

These should be explicitly implemented and validated before deploying to a real production environment.

---

# 46. Related Documentation

* `README.md` — Project introduction
* `docs/01-project-overview.md` — Project scope
* `docs/02-architecture.md` — Architecture
* `docs/03-local-setup.md` — Local setup
* `docs/04-kubernetes-deployment.md` — Kubernetes deployment
* `docs/05-cicd-pipeline.md` — CI/CD
* `docs/06-monitoring-observability.md` — Monitoring
* `docs/07-troubleshooting.md` — Troubleshooting
* `docs/08-operations-runbook.md` — Day-2 operations
* `docs/09-security.md` — Security
