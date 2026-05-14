# CI/CD Design for Multi-Environment Databricks + AWS MWAA

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              CI/CD PIPELINE ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   GitHub Repository                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │  Branches: main ←── prod ←── uat ←── qa ←── dev ←── feature/*                  │  │
│   └─────────────────────────────────────────────────────────────────────────────────┘  │
│                    │         │         │         │                                      │
│                    ▼         ▼         ▼         ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │                        GitHub Actions Workflows                                  │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│   │  │ dev_cicd │  │ qa_cicd  │  │ uat_cicd │  │prod_cicd │  │ CodeQL + Tests   │  │  │
│   │  │   .yml   │  │   .yml   │  │   .yml   │  │   .yml   │  │    (PR gates)    │  │  │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────────────┘  │  │
│   └───────┼─────────────┼─────────────┼─────────────┼───────────────────────────────┘  │
│           │             │             │             │                                   │
│           ▼             ▼             ▼             ▼                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │                         Self-Hosted Runners (AWS EC2)                            │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                        │  │
│   │  │ runner-  │  │ runner-  │  │ runner-  │  │ runner-  │                        │  │
│   │  │   dev    │  │   qa     │  │   uat    │  │   prod   │                        │  │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                        │  │
│   └───────┼─────────────┼─────────────┼─────────────┼───────────────────────────────┘  │
│           │             │             │             │                                   │
│           ▼             ▼             ▼             ▼                                   │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│   │                         AWS Secrets Manager                                      │  │
│   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │  │
│   │  │sa-cicd-pop-  │ │sa-cicd-pop-  │ │sa-cicd-pop-  │ │sa-cicd-pop-  │           │  │
│   │  │     dev      │ │     qa       │ │     uat      │ │     prod     │           │  │
│   │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘           │  │
│   └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                              DEPLOYMENT TARGETS                                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   Databricks Workspaces                          AWS MWAA (Airflow)                    │
│   ┌──────────────────────────────────┐          ┌──────────────────────────────────┐  │
│   │  DEV:  dbc-xxx-dev.cloud.db.com  │          │  s3://project-dev-mwaa/dags/     │  │
│   │  QA:   dbc-xxx-qa.cloud.db.com   │          │  s3://project-qa-mwaa/dags/      │  │
│   │  UAT:  dbc-xxx-uat.cloud.db.com  │          │  s3://project-uat-mwaa/dags/     │  │
│   │  PROD: dbc-xxx-prod.cloud.db.com │          │  s3://project-prod-mwaa/dags/    │  │
│   └──────────────────────────────────┘          └──────────────────────────────────┘  │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Branch Strategy

```
main (protected)
  │
  └── prod ◄─────────────── Production releases (tagged)
        │
        └── uat ◄────────── UAT/Staging validation
              │
              └── qa ◄───── QA testing & integration
                    │
                    └── dev ◄── Development integration
                          │
                          └── feature/* ── Feature branches
```

| Branch | Trigger | Environment | Approval Required |
|--------|---------|-------------|-------------------|
| `feature/*` | PR to dev | - | Code review |
| `dev` | Push/Merge | DEV | No |
| `qa` | Push/Merge | QA | No |
| `uat` | Push/Merge | UAT | Yes (Tech Lead) |
| `prod` | Push/Merge | PROD | Yes (Release Manager) |

---

## Directory Structure

```
project-repo/
├── .github/
│   ├── workflows/
│   │   ├── dev_cicd.yml
│   │   ├── qa_cicd.yml
│   │   ├── uat_cicd.yml
│   │   ├── prod_cicd.yml
│   │   ├── pr_validation.yml
│   │   └── codeql.yml
│   └── CODEOWNERS
├── config/
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── values.yaml
│   │   │   └── cluster_config.yaml
│   │   ├── qa/
│   │   ├── uat/
│   │   └── prod/
│   ├── bundles/
│   │   ├── main-bundle/
│   │   │   ├── bundle.yaml
│   │   │   └── resources/
│   │   └── prerequisites-bundle/
│   └── constants/
│       └── param_values.yaml
├── scripts/
│   ├── deploy.py
│   ├── set_cluster_config.sh
│   ├── init-cluster.sh
│   └── rollback.sh
├── src/
│   ├── spark/
│   │   └── helpers/
│   └── workflow/
│       └── dags/
├── test/
│   └── unit/
└── README.md
```

---

## GitHub Secrets Configuration

### Repository Secrets (Settings → Secrets → Actions)

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DATABRICKS_DEV_HOST` | DEV workspace URL | `https://dbc-xxx.cloud.databricks.com` |
| `DATABRICKS_DEV_REPO_ID` | DEV Repos API ID | `1234567890` |
| `DATABRICKS_QA_HOST` | QA workspace URL | `https://dbc-yyy.cloud.databricks.com` |
| `DATABRICKS_QA_REPO_ID` | QA Repos API ID | `2345678901` |
| `DATABRICKS_UAT_HOST` | UAT workspace URL | `https://dbc-zzz.cloud.databricks.com` |
| `DATABRICKS_UAT_REPO_ID` | UAT Repos API ID | `3456789012` |
| `DATABRICKS_PROD_HOST` | PROD workspace URL | `https://dbc-aaa.cloud.databricks.com` |
| `DATABRICKS_PROD_REPO_ID` | PROD Repos API ID | `4567890123` |

### AWS Secrets Manager Structure

```json
// Secret: sa-cicd-pop-{env}
{
  "databricks-apikey": {
    "value": "dapi_xxxxxxxxxxxxx"
  },
  "aws-access-key": {
    "value": "AKIA..."
  },
  "aws-secret-key": {
    "value": "xxxxx"
  }
}
```

---

## Workflow Files

### 1. Reusable Workflow Template (`.github/workflows/deploy-template.yml`)

```yaml
name: Reusable Deploy Workflow

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      environment_upper:
        required: true
        type: string
      branch:
        required: true
        type: string
      run_tests:
        required: false
        type: boolean
        default: true
      require_approval:
        required: false
        type: boolean
        default: false
    secrets:
      DATABRICKS_HOST:
        required: true
      DATABRICKS_REPO_ID:
        required: true

env:
  REPO_NAME: "Population-Advyzer"
  AWS_REGION: "us-east-1"

jobs:
  # ---------------------------------------------------------------------------
  # Approval Gate (for UAT/PROD)
  # ---------------------------------------------------------------------------
  approval:
    if: ${{ inputs.require_approval }}
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}-approval
    steps:
      - name: Approval checkpoint
        run: echo "Deployment to ${{ inputs.environment_upper }} approved"

  # ---------------------------------------------------------------------------
  # Deploy Job
  # ---------------------------------------------------------------------------
  deploy:
    needs: [approval]
    if: always() && (needs.approval.result == 'success' || needs.approval.result == 'skipped')
    runs-on: [self-hosted, ${{ inputs.environment }}]
    
    steps:
      # -----------------------------------------------------------------------
      # Step 1: Checkout code
      # -----------------------------------------------------------------------
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          ref: ${{ inputs.branch }}

      # -----------------------------------------------------------------------
      # Step 2: Set cluster configuration
      # -----------------------------------------------------------------------
      - name: Set cluster config
        run: |
          chmod +x ./scripts/set_cluster_config.sh
          ./scripts/set_cluster_config.sh
        env:
          ENVIRONMENT: ${{ inputs.environment }}
          ENVIRONMENT_UPPER: ${{ inputs.environment_upper }}

      # -----------------------------------------------------------------------
      # Step 3: Get Databricks token from AWS Secrets Manager
      # -----------------------------------------------------------------------
      - name: Export Databricks Token
        run: |
          echo "[INFO] Fetching Databricks token for ${{ inputs.environment_upper }}..."
          DATABRICKS_TOKEN=$(aws secretsmanager get-secret-value \
            --region ${{ env.AWS_REGION }} \
            --secret-id sa-cicd-pop-${{ inputs.environment }} \
            --output json | jq -r '.SecretString' | jq -r '."databricks-apikey".value')
          echo "::add-mask::$DATABRICKS_TOKEN"
          echo "DATABRICKS_TOKEN=$DATABRICKS_TOKEN" >> $GITHUB_ENV

      # -----------------------------------------------------------------------
      # Step 4: Backup current commit (for rollback)
      # -----------------------------------------------------------------------
      - name: Backup current commit
        id: backup
        run: |
          RESP=$(curl -s -X GET "${{ secrets.DATABRICKS_HOST }}/api/2.0/repos/${{ secrets.DATABRICKS_REPO_ID }}" \
            -H "Authorization: Bearer $DATABRICKS_TOKEN")
          OLD_COMMIT=$(echo "$RESP" | jq -r '.head_commit_id')
          if [ -n "$OLD_COMMIT" ] && [ "$OLD_COMMIT" != "null" ]; then
            echo "OLD_COMMIT=$OLD_COMMIT" >> $GITHUB_ENV
            echo "old_commit=$OLD_COMMIT" >> $GITHUB_OUTPUT
            echo "[INFO] Backed up commit: $OLD_COMMIT"
          else
            echo "::warning::Could not fetch current commit ID"
          fi

      # -----------------------------------------------------------------------
      # Step 5: Run unit tests (conditional)
      # -----------------------------------------------------------------------
      - name: Run unit tests
        if: ${{ inputs.run_tests }}
        id: run_tests
        uses: databricks/run-notebook@v0
        with:
          databricks-host: ${{ secrets.DATABRICKS_HOST }}
          local-notebook-path: test/unit/spark/run_tests.py
          git-commit: ${{ github.sha }}
          new-cluster-json: ${{ env.CLUSTER_CONFIG }}
          notebook-params-json: '{"perform_coverage": "True"}'
          access-control-list-json: >
            [{"group_name": "DataBricks_POP-${{ inputs.environment_upper }}_DataEngineer", "permission_level": "CAN_MANAGE"}]
        env:
          DATABRICKS_TOKEN: ${{ env.DATABRICKS_TOKEN }}

      - name: Fail if tests failed
        if: ${{ inputs.run_tests && failure() }}
        run: |
          echo "::error::Unit tests failed. Aborting deployment."
          exit 1

      # -----------------------------------------------------------------------
      # Step 6: Update Databricks workspace repo
      # -----------------------------------------------------------------------
      - name: Update Databricks workspace repo
        run: |
          echo "[INFO] Updating Databricks repo to branch: ${{ inputs.branch }}"
          curl --fail --request PATCH \
            "${{ secrets.DATABRICKS_HOST }}/api/2.0/repos/${{ secrets.DATABRICKS_REPO_ID }}" \
            --header "Authorization: Bearer $DATABRICKS_TOKEN" \
            --header "Content-Type: application/json" \
            --data '{"branch": "${{ inputs.branch }}"}'

      # -----------------------------------------------------------------------
      # Step 7: Run deployment notebook (copies to MWAA S3)
      # -----------------------------------------------------------------------
      - name: Deploy to MWAA
        uses: databricks/run-notebook@v0
        with:
          databricks-host: ${{ secrets.DATABRICKS_HOST }}
          local-notebook-path: scripts/deploy.py
          git-commit: ${{ github.sha }}
          new-cluster-json: ${{ env.CLUSTER_CONFIG }}
          notebook-params-json: '{"env": "${{ inputs.environment_upper }}"}'
          access-control-list-json: >
            [
              {"group_name": "DataBricks_POP-${{ inputs.environment_upper }}_DataEngineer", "permission_level": "CAN_MANAGE"},
              {"group_name": "DataBricks_POP-${{ inputs.environment_upper }}_DataOps", "permission_level": "CAN_MANAGE"}
            ]
        env:
          DATABRICKS_TOKEN: ${{ env.DATABRICKS_TOKEN }}

      # -----------------------------------------------------------------------
      # Step 8: Deploy Databricks bundles
      # -----------------------------------------------------------------------
      - name: Setup Databricks CLI
        uses: databricks/setup-cli@main

      - name: Deploy Databricks Bundles
        run: |
          echo "[INFO] Deploying Databricks bundles to ${{ inputs.environment_upper }}..."
          
          for bundle in main-bundle prerequisites-bundle; do
            echo "[INFO] Deploying $bundle..."
            cd config/bundles/$bundle
            databricks bundle deploy -t "${{ inputs.environment_upper }}" --force --auto-approve
            cd -
          done
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ env.DATABRICKS_TOKEN }}

      # -----------------------------------------------------------------------
      # Step 9: Verify deployment
      # -----------------------------------------------------------------------
      - name: Verify deployment
        run: |
          echo "[INFO] Verifying deployment..."
          RESP=$(curl -s -X GET "${{ secrets.DATABRICKS_HOST }}/api/2.0/repos/${{ secrets.DATABRICKS_REPO_ID }}" \
            -H "Authorization: Bearer $DATABRICKS_TOKEN")
          NEW_COMMIT=$(echo "$RESP" | jq -r '.head_commit_id')
          echo "[INFO] Deployed commit: $NEW_COMMIT"
          
          if [ "$NEW_COMMIT" == "${{ github.sha }}" ]; then
            echo "✅ Deployment verified successfully"
          else
            echo "::warning::Deployed commit doesn't match expected. Expected: ${{ github.sha }}, Got: $NEW_COMMIT"
          fi

      # -----------------------------------------------------------------------
      # Step 10: Rollback on failure
      # -----------------------------------------------------------------------
      - name: Rollback on failure
        if: failure() && env.OLD_COMMIT != ''
        run: |
          echo "::warning::Deployment failed. Rolling back to commit: $OLD_COMMIT"
          curl --request PATCH \
            "${{ secrets.DATABRICKS_HOST }}/api/2.0/repos/${{ secrets.DATABRICKS_REPO_ID }}" \
            --header "Authorization: Bearer $DATABRICKS_TOKEN" \
            --header "Content-Type: application/json" \
            --data "{\"branch\": \"${{ inputs.branch }}\", \"tag\": null, \"commit_id\": \"$OLD_COMMIT\"}"
```

### 2. DEV Workflow (`.github/workflows/dev_cicd.yml`)

```yaml
name: PopA CICD DEV

on:
  push:
    branches: ["dev"]

jobs:
  deploy-dev:
    uses: ./.github/workflows/deploy-template.yml
    with:
      environment: dev
      environment_upper: DEV
      branch: dev
      run_tests: false  # Disabled for faster dev iterations
      require_approval: false
    secrets:
      DATABRICKS_HOST: ${{ secrets.DATABRICKS_DEV_HOST }}
      DATABRICKS_REPO_ID: ${{ secrets.DATABRICKS_DEV_REPO_ID }}
```

### 3. QA Workflow (`.github/workflows/qa_cicd.yml`)

```yaml
name: PopA CICD QA

on:
  push:
    branches: ["qa"]

jobs:
  deploy-qa:
    uses: ./.github/workflows/deploy-template.yml
    with:
      environment: qa
      environment_upper: QA
      branch: qa
      run_tests: true
      require_approval: false
    secrets:
      DATABRICKS_HOST: ${{ secrets.DATABRICKS_QA_HOST }}
      DATABRICKS_REPO_ID: ${{ secrets.DATABRICKS_QA_REPO_ID }}
```

### 4. UAT Workflow (`.github/workflows/uat_cicd.yml`)

```yaml
name: PopA CICD UAT

on:
  push:
    branches: ["uat"]

jobs:
  deploy-uat:
    uses: ./.github/workflows/deploy-template.yml
    with:
      environment: uat
      environment_upper: UAT
      branch: uat
      run_tests: true
      require_approval: true  # Requires manual approval
    secrets:
      DATABRICKS_HOST: ${{ secrets.DATABRICKS_UAT_HOST }}
      DATABRICKS_REPO_ID: ${{ secrets.DATABRICKS_UAT_REPO_ID }}
```

### 5. PROD Workflow (`.github/workflows/prod_cicd.yml`)

```yaml
name: PopA CICD PROD

on:
  push:
    branches: ["prod"]
    tags:
      - 'v*'  # Also trigger on version tags

jobs:
  deploy-prod:
    uses: ./.github/workflows/deploy-template.yml
    with:
      environment: prod
      environment_upper: PROD
      branch: prod
      run_tests: true
      require_approval: true  # Requires manual approval
    secrets:
      DATABRICKS_HOST: ${{ secrets.DATABRICKS_PROD_HOST }}
      DATABRICKS_REPO_ID: ${{ secrets.DATABRICKS_PROD_REPO_ID }}

  # Create release after successful deployment
  create-release:
    needs: deploy-prod
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref_name }}
          release_name: Release ${{ github.ref_name }}
          draft: false
          prerelease: false
```

### 6. PR Validation Workflow (`.github/workflows/pr_validation.yml`)

```yaml
name: PR Validation

on:
  pull_request:
    branches: [dev, qa, uat, prod, main]

jobs:
  # ---------------------------------------------------------------------------
  # Lint and Format Check
  # ---------------------------------------------------------------------------
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install black flake8 isort
      
      - name: Check formatting (black)
        run: black --check src/ test/
      
      - name: Check imports (isort)
        run: isort --check-only src/ test/
      
      - name: Lint (flake8)
        run: flake8 src/ test/ --max-line-length=120

  # ---------------------------------------------------------------------------
  # Unit Tests
  # ---------------------------------------------------------------------------
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov pytest-mock pyspark
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          pytest test/unit/ -v --cov=src --cov-report=xml --cov-report=term
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  # ---------------------------------------------------------------------------
  # Security Scan
  # ---------------------------------------------------------------------------
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'HIGH,CRITICAL'

  # ---------------------------------------------------------------------------
  # Bundle Validation
  # ---------------------------------------------------------------------------
  validate-bundles:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Databricks CLI
        uses: databricks/setup-cli@main
      
      - name: Validate bundles
        run: |
          for bundle in config/bundles/*/; do
            echo "Validating $bundle..."
            cd $bundle
            databricks bundle validate || exit 1
            cd -
          done
```

---

## Environment Configuration Files

### `config/environments/dev/values.yaml`

```yaml
s3:
  buckets:
    bronze: project-dev-datalake-bronze-us-east-1
    silver: project-dev-datalake-silver-us-east-1
    gold: project-dev-datalake-gold-us-east-1
  arn: "arn:aws:iam::111111111111:instance-profile/POP-DEV_Databricks-Instance_role"

airflow:
  source: "WORKSPACE"
  databricks_instance: dbc-xxx-dev.cloud.databricks.com
  version: 2-10-3
  aws_region: us-east-1
  databricks_secret_name: sa-cicd-pop-dev
  databricks_repository: Population-Advyzer
  mwaa_bucket: project-dev-mwaa-us-east-1
  databricks_users_group:
    - DataBricks_POP-DEV_DataEngineer

env: DEV
catalog: pop_dev
config_schema: ma_reference

custom_tags:
  tenant: company
  project: population-advyzer
  billingcode: POP-DEV
  billable: "FALSE"
  env: dev
```

### `config/environments/prod/values.yaml`

```yaml
s3:
  buckets:
    bronze: project-prod-datalake-bronze-us-east-1
    silver: project-prod-datalake-silver-us-east-1
    gold: project-prod-datalake-gold-us-east-1
  arn: "arn:aws:iam::444444444444:instance-profile/POP-PROD_Databricks-Instance_role"

airflow:
  source: "WORKSPACE"
  databricks_instance: dbc-xxx-prod.cloud.databricks.com
  version: 2-10-3
  aws_region: us-east-1
  databricks_secret_name: sa-cicd-pop-prod
  databricks_repository: Population-Advyzer
  mwaa_bucket: project-prod-mwaa-us-east-1
  databricks_users_group:
    - DataBricks_POP-PROD_DataEngineer
    - DataBricks_POP-PROD_DataOps

env: PROD
catalog: pop_prod
config_schema: ma_reference

custom_tags:
  tenant: company
  project: population-advyzer
  billingcode: POP-PROD
  billable: "TRUE"
  env: prod
```

---

## Deployment Script (`scripts/deploy.py`)

```python
# Databricks notebook source
# MAGIC %md
# MAGIC ## Deploy Artifacts to MWAA S3

# COMMAND ----------

dbutils.widgets.dropdown("env", "DEV", ["DEV", "QA", "UAT", "PROD"])

# COMMAND ----------

import os
import yaml

env_lower = dbutils.widgets.get("env").lower()
env_upper = dbutils.widgets.get("env")

# Load environment config
with open(f"../config/environments/{env_lower}/values.yaml") as f:
    config = yaml.safe_load(f)

# Extract config values
arn = config['s3']['arn']
airflow_version = config['airflow']['version']
repository = config['airflow']['databricks_repository']
mwaa_bucket = config['airflow']['mwaa_bucket']

# COMMAND ----------

# Mount S3 buckets if not already mounted
buckets = list(config['s3']['buckets'].values()) + [mwaa_bucket]

for bucket_name in buckets:
    mount_point = f"/mnt/{bucket_name}"
    if mount_point in [m.mountPoint for m in dbutils.fs.mounts()]:
        print(f"✓ Mount exists: {bucket_name}")
    else:
        print(f"Mounting: {bucket_name}")
        dbutils.fs.mount(f"s3a://{bucket_name}", mount_point)

# COMMAND ----------

# Define paths
root_path = f"Repos/{env_upper}/{repository}"
mwaa_dags_path = f"dbfs:/mnt/{mwaa_bucket}/POP-{env_upper}_Airflow_{airflow_version}/dags"

print(f"Source: /Workspace/{root_path}")
print(f"Target: {mwaa_dags_path}")

# COMMAND ----------

# Copy artifacts to MWAA S3
artifacts = [
    # Requirements
    ("config/workflow/requirements.txt", f"../requirements.txt"),
    
    # Environment config
    (f"config/environments/{env_lower}/values.yaml", "src/spark/helpers/values.yaml"),
    ("config/constants/param_values.yaml", "src/spark/helpers/param_values.yaml"),
    
    # Cluster configs
    (f"config/environments/{env_lower}/cluster_config.yaml", 
     f"src/spark/helpers/config/environments/{env_lower}/cluster_config.yaml"),
    
    # Helper utilities
    ("src/spark/helpers/airflow_utils.py", "src/spark/helpers/airflow_utils.py"),
    ("src/spark/helpers/config_util.py", "src/spark/helpers/config_util.py"),
]

for src, dst in artifacts:
    source = f"file:/Workspace/{root_path}/{src}"
    target = f"{mwaa_dags_path}/{dst}"
    print(f"Copying: {src} → {dst}")
    dbutils.fs.cp(source, target, recurse=True)

# Copy DAGs directory
print("Copying DAGs...")
dbutils.fs.cp(
    f"file:/Workspace/{root_path}/src/workflow/dags/",
    f"{mwaa_dags_path}/",
    recurse=True
)

print("✅ Deployment complete")
```

---

## Cluster Configuration Script (`scripts/set_cluster_config.sh`)

```bash
#!/bin/bash

# Cluster configuration for CI/CD deployments
# Environment variables expected: ENVIRONMENT, ENVIRONMENT_UPPER, IAM_ID, REPO_NAME

IAM_ID="${IAM_ID:-111111111111}"
REPO_NAME="${REPO_NAME:-Population-Advyzer}"

CLUSTER_CONFIG=$(cat <<EOF
{
  "autoscale": {
    "min_workers": 1,
    "max_workers": 2
  },
  "aws_attributes": {
    "availability": "SPOT_WITH_FALLBACK",
    "first_on_demand": 1,
    "instance_profile_arn": "arn:aws:iam::${IAM_ID}:instance-profile/POP-${ENVIRONMENT_UPPER}_Databricks-Instance_role",
    "spot_bid_price_percent": 100,
    "zone_id": "us-east-1a"
  },
  "data_security_mode": "SINGLE_USER",
  "driver_node_type_id": "i4i.large",
  "node_type_id": "i4i.large",
  "spark_version": "14.3.x-scala2.12",
  "runtime_engine": "STANDARD",
  "enable_elastic_disk": false,
  "custom_tags": {
    "env": "${ENVIRONMENT}",
    "project": "POP",
    "tenant": "company",
    "BillingCode": "POP-${ENVIRONMENT_UPPER}"
  },
  "init_scripts": [
    {"workspace": {"destination": "/Repos/${ENVIRONMENT_UPPER}/${REPO_NAME}/scripts/init-cluster.sh"}}
  ],
  "spark_env_vars": {
    "POP_CONFIG_DIR": "/Workspace/Repos/${ENVIRONMENT_UPPER}/${REPO_NAME}/config"
  }
}
EOF
)

# Export for GitHub Actions
echo "CLUSTER_CONFIG=$CLUSTER_CONFIG" >> $GITHUB_ENV
echo "[INFO] Cluster config set for ${ENVIRONMENT_UPPER}"
```

---

## GitHub Environments Setup

Configure these in GitHub Repository Settings → Environments:

| Environment | Protection Rules | Reviewers |
|-------------|-----------------|-----------|
| `dev` | None | - |
| `qa` | None | - |
| `uat-approval` | Required reviewers | Tech Leads |
| `prod-approval` | Required reviewers | Release Managers |

---

## Deployment Flow Summary

```
Developer → feature branch → PR → dev
                                   │
                                   ▼
                            [DEV Deploy]
                            - No tests (fast)
                            - Auto deploy
                                   │
                                   ▼
                            Merge to qa
                                   │
                                   ▼
                            [QA Deploy]
                            - Unit tests ✓
                            - Auto deploy
                                   │
                                   ▼
                            Merge to uat
                                   │
                                   ▼
                            [UAT Deploy]
                            - Unit tests ✓
                            - Manual approval required
                            - Tech Lead sign-off
                                   │
                                   ▼
                            Merge to prod
                                   │
                                   ▼
                            [PROD Deploy]
                            - Unit tests ✓
                            - Manual approval required
                            - Release Manager sign-off
                            - GitHub Release created
```

---

## Rollback Procedure

### Automatic Rollback
The workflow automatically rolls back to the previous commit if deployment fails.

### Manual Rollback
```bash
# Option 1: Via Databricks API
curl --request PATCH "https://dbc-xxx.cloud.databricks.com/api/2.0/repos/{REPO_ID}" \
  --header "Authorization: Bearer $TOKEN" \
  --data '{"branch": "prod", "commit_id": "abc123"}'

# Option 2: Via Git
git revert HEAD
git push origin prod
```

---

## Monitoring & Alerts

1. **GitHub Actions**: Monitor workflow runs in Actions tab
2. **Slack Integration**: Add Slack notifications for deployment status
3. **Databricks Jobs**: Monitor via Databricks workflows UI
4. **MWAA**: Monitor via AWS MWAA console

### Add Slack Notification (optional step in workflow)

```yaml
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    channel: '#deployments'
    fields: repo,message,commit,author,action,eventName,workflow
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```
