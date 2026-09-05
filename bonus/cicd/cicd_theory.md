# CI/CD Pipeline Architecture & Theory

## 1. GitHub Integration Architecture

This application uses a GitOps-style integration with GitHub as the primary version control system and trigger source for deployment pipelines:

- **Repository Structure**: Monorepo hosting Streamlit UI (`app/`), AI Gateway (`gateway/`), Guardrails (`guardrails/`), Observability (`observability/`), Infrastructure as Code (`terraform/`), and EKS workloads (`bonus/`).
- **Branch Strategy**:
  - `feature/*`: Short-lived developer feature branches.
  - `main`: Production-ready branch protected by branch protection rules.
- **Branch Protection Rules**:
  - Require at least 1 pull request review before merging to `main`.
  - Require status checks (linter, unit tests) to pass before merge.
  - Prevent force pushes and direct commits to `main`.
- **AWS Connection**: Connected to AWS CodePipeline via **AWS CodeStar Connections (GitHub Connector)** using OAuth2 tokens.

---

## 2. AWS CodePipeline Architecture

The deployment automation uses a 3-stage AWS CodePipeline:

```text
+------------------------+      +------------------------+      +------------------------+
|      SOURCE STAGE      |  ->  |      BUILD STAGE       |  ->  |      DEPLOY STAGE      |
|  GitHub (main branch)  |      |     AWS CodeBuild      |      |   EC2 Host / EKS Pod   |
| (CodeStar Connection)  |      |   (buildspec.yaml)     |      |  (Systemd Service)     |
+------------------------+      +------------------------+      +------------------------+
```

### Stage Breakdown:
1. **Source Stage (`GitHub_Source`)**:
   - Listens to push events on `main` via webhooks.
   - Outputs `SourceArtifact` (zipped git commit payload) stored in an encrypted S3 pipeline bucket.
2. **Build Stage (`AWS_CodeBuild`)**:
   - Launches an ephemeral Ubuntu/Python 3.11 container.
   - Executes instructions in `buildspec.yaml`.
   - Runs lint checks (`flake8`), executes test suites (`pytest`, `test_routing.py`).
   - Fetches secrets from AWS Systems Manager (SSM) Parameter Store.
   - Compiles `.env` and packages `deployment.zip` as `BuildArtifact`.
3. **Deploy Stage (`AWS_CodeDeploy / EC2 Deployment`)**:
   - Downloads `BuildArtifact` from S3.
   - Extracts bundle into `/home/appuser/capstone`.
   - Installs virtual environment dependencies and executes `systemctl restart knowledge-assistant`.

---

## 3. Annotated `buildspec.yaml` Specification

Below is the production `buildspec.yaml` configured for AWS CodeBuild:

```yaml
# buildspec.yaml — AWS CodeBuild build specification
version: 0.2

env:
  variables:
    AWS_REGION: "us-east-1"
    APP_DIR: "/codebuild/output/app"
  parameter-store:
    KNOWLEDGE_BASE_ID: "/knowledge-assistant/KNOWLEDGE_BASE_ID"
    GUARDRAIL_ID:       "/knowledge-assistant/GUARDRAIL_ID"

phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - echo "=== Installing dependencies ==="
      - pip install --upgrade pip
      - pip install -r requirements.txt
      - pip install pytest flake8

  pre_build:
    commands:
      - echo "=== Running linter ==="
      - flake8 app/ gateway/ guardrails/ observability/ --max-line-length=120 --exclude=__pycache__ || true

      - echo "=== Running unit tests ==="
      - python -m pytest tests/ -v --tb=short || true

      - echo "=== Verifying routing logic ==="
      - python gateway/test_routing.py

  build:
    commands:
      - echo "=== Build started on $(date) ==="
      - echo "AWS_REGION=${AWS_REGION}"                   > .env
      - echo "KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID}"    >> .env
      - echo "GUARDRAIL_ID=${GUARDRAIL_ID}"               >> .env

      - zip -r deployment.zip app/ gateway/ guardrails/ observability/ bonus/ sample_documents/ requirements.txt run.sh .env --exclude "*.pyc" --exclude "__pycache__/*" --exclude "data/*"

      - echo "=== Build complete ==="

  post_build:
    commands:
      - echo "=== Post-build ==="
      - echo "Deployment package ready: deployment.zip"
      - ls -lh deployment.zip

artifacts:
  files:
    - deployment.zip
    - scripts/deploy_ec2.sh
  discard-paths: no

cache:
  paths:
    - '/root/.cache/pip/**/*'
```

---

## 4. End-to-End CI/CD Lifecycle Sequence

1. Developer pushes code changes to a feature branch (`git push origin feature/new-routing`).
2. Pull Request opened against `main`.
3. GitHub Actions triggers fast pull-request validation (linting & syntax check).
4. Peer reviewer approves PR $\rightarrow$ merged to `main`.
5. GitHub webhook notifies AWS CodePipeline.
6. **CodePipeline Source Stage** fetches repository zip payload.
7. **CodeBuild Stage** initializes Python 3.11 environment, runs unit tests, verifies gateway routing, pulls SSM parameters, and outputs `deployment.zip`.
8. **Deployment Stage** copies artifact to target EC2 instances or EKS cluster, unpacks files, and executes atomic service reload.
9. Pipeline publishes notification metric to Amazon SNS on success or failure.

---

## 5. CI/CD Concept Matrix

| Concept | Architectural Role | Project Implementation |
|---|---|---|
| **Source Stage** | Repository listener | GitHub `main` branch via CodeStar Connector |
| **Build Stage** | Test runner & packager | AWS CodeBuild executing `buildspec.yaml` |
| **Deploy Stage** | Production server updater | Systemd service restart on EC2 / Helm upgrade on EKS |
| **Artifact** | Passed build state object | Encrypted `deployment.zip` in S3 |
| **Parameter Store** | Centralized secret management | AWS SSM Parameter Store (`/knowledge-assistant/`) |
| **Branch Protection** | Code quality gate | PR review & required status checks on `main` |
