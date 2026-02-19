# Deployment Guide — Google Cloud Platform

This document covers the complete deployment process for the Payment Gateway Reconciliation System on Google Cloud Platform using Cloud Run, Cloud SQL, Secret Manager, and Cloud Build.

---

## Architecture Overview

The application is deployed as a **single Docker container** on Cloud Run:

```
                        Cloud Run Container (port 8080)
                    ┌──────────────────────────────────────┐
                    │            supervisord                │
                    │         ┌──────────┬────────────┐    │
Internet ──────►    │  nginx  │  :8080   │  gunicorn  │    │  ──► Cloud SQL
                    │  (SPA + │          │  :8000     │    │      (MySQL 8.0)
                    │  proxy) │          │  (FastAPI) │    │
                    │         └──────────┴────────────┘    │
                    └──────────────────────────────────────┘
```

- **nginx** (port 8080) — serves the React SPA and proxies `/api/` requests to gunicorn
- **gunicorn** (port 8000) — runs the FastAPI backend with Uvicorn workers
- **supervisord** — manages both nginx and gunicorn processes
- **Alembic** — runs database migrations automatically before gunicorn starts
- **Cloud SQL Auth Proxy** — handles secure database connectivity via Unix socket

---

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI) installed and authenticated
- A GCP project with billing enabled
- GitHub repository connected to Cloud Build

---

## Step-by-Step Deployment

### 1. Set your GCP project

```bash
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable required APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com
```

### 3. Create Artifact Registry repository

Stores Docker images built by Cloud Build.

```bash
gcloud artifacts repositories create recon \
  --repository-format=docker \
  --location=us-central1 \
  --description="Reconciler Docker images"
```

### 4. Create Cloud SQL instance

```bash
# Create MySQL 8.0 instance (takes a few minutes)
gcloud sql instances create recon-db \
  --database-version=MYSQL_8_0 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-size=10GB \
  --storage-auto-increase

# Wait until the instance is RUNNABLE
gcloud sql instances describe recon-db --format='value(state)'

# Create the database
gcloud sql databases create reconciler --instance=recon-db

# Create the database user
gcloud sql users create kevin \
  --instance=recon-db \
  --password='YOUR_DB_PASSWORD'
```

### 5. Get your project number

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
echo "Project ID: $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
```

### 6. Create secrets in Secret Manager

Six secrets are required. These are injected into Cloud Run as environment variables at runtime.

```bash
# DATABASE_URL — MySQL connection string via Cloud SQL Auth Proxy
echo -n "mysql+pymysql://kevin:YOUR_DB_PASSWORD@/reconciler?unix_socket=/cloudsql/${PROJECT_ID}:us-central1:recon-db" | \
  gcloud secrets create DATABASE_URL --data-file=-

# JWT_SECRET_KEY — signing key for authentication tokens (min 32 chars)
echo -n "$(openssl rand -hex 32)" | \
  gcloud secrets create JWT_SECRET_KEY --data-file=-

# SMTP credentials for email sending
echo -n 'your-smtp-password' | \
  gcloud secrets create SMTP_PASSWORD --data-file=-

echo -n 'your-email@gmail.com' | \
  gcloud secrets create SMTP_USERNAME --data-file=-

echo -n 'your-email@gmail.com' | \
  gcloud secrets create SMTP_FROM_EMAIL --data-file=-

# CORS origins — JSON array of allowed frontend URLs
# Use a placeholder; update after first deploy when you know the Cloud Run URL
echo -n '["https://placeholder.a.run.app"]' | \
  gcloud secrets create CORS_ORIGINS --data-file=-
```

### 7. Grant IAM permissions

The default Compute service account is used by both Cloud Build and Cloud Run.

```bash
# Cloud Run needs access to read secrets
for SECRET in DATABASE_URL JWT_SECRET_KEY SMTP_PASSWORD SMTP_USERNAME SMTP_FROM_EMAIL CORS_ORIGINS; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done

# Cloud Run needs Cloud SQL Client role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Cloud Build needs permission to deploy to Cloud Run
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/run.admin"

# Cloud Build needs to act as the service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

> **Note:** Some projects use a dedicated Cloud Build service account (`PROJECT_NUMBER@cloudbuild.gserviceaccount.com`). Check which account your builds use with:
> ```bash
> gcloud iam service-accounts list --project=$PROJECT_ID
> ```

### 8. Connect GitHub repository to Cloud Build

This step requires the GCP Console (OAuth flow):

1. Go to **Cloud Build > Triggers**: `https://console.cloud.google.com/cloud-build/triggers`
2. Click **Connect Repository**
3. Select **GitHub** > Authenticate > Select your repository
4. Create a trigger:
   - **Name:** `deploy-recon`
   - **Event:** Push to branch
   - **Branch:** `^main$`
   - **Configuration:** Cloud Build config file > `cloudbuild.yaml`

### 9. Deploy

Push a commit to `main` to trigger Cloud Build, or trigger manually:

```bash
# Option A: Push to trigger
git add -A && git commit -m "deploy" && git push

# Option B: Manual trigger from project root
gcloud builds submit --config=cloudbuild.yaml .
```

### 10. Update CORS origins

After the first deploy, get your Cloud Run URL and update the CORS secret:

```bash
# Get the service URL
gcloud run services describe recon --region=us-central1 --format='value(status.url)'

# Update CORS_ORIGINS with the actual URL
echo -n '["https://recon-XXXXX-uc.a.run.app"]' | \
  gcloud secrets versions add CORS_ORIGINS --data-file=-

# Force Cloud Run to pick up the new secret version
gcloud run services update recon --region=us-central1 \
  --update-secrets=CORS_ORIGINS=CORS_ORIGINS:latest
```

### 11. Create the super admin user

Wake the container first (cold starts take a few seconds), then call the endpoint:

```bash
URL=$(gcloud run services describe recon --region=us-central1 --format='value(status.url)')

# Wake the container
curl -s "$URL/" > /dev/null && sleep 10

# Create super admin
curl -X POST "${URL}/api/v1/users/create-super-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "your-email@gmail.com",
    "password": "YourStr0ng!Password",
    "first_name": "Admin",
    "last_name": "User"
  }'
```

---

## What Happens on Each Deploy

The CI/CD pipeline (`cloudbuild.yaml`) executes three steps:

1. **Build** — Docker multi-stage build: Node 20 compiles the React frontend, Python 3.11-slim packages the backend with nginx and supervisord
2. **Push** — Image is pushed to Artifact Registry (`us-central1-docker.pkg.dev/PROJECT/recon/recon:COMMIT_SHA`)
3. **Deploy** — Cloud Run service is updated with the new image, secrets, env vars, and Cloud SQL connection

On container startup:

1. **supervisord** starts nginx (priority 10) and gunicorn (priority 20)
2. **Alembic** runs `upgrade head` before gunicorn starts — creates/migrates database tables
3. **gunicorn** starts the FastAPI application with 2 Uvicorn workers
4. **FastAPI** validates auth config and runs `create_all()` as a safety net

---

## Configuration

### Environment Variables (set in `cloudbuild.yaml`)

| Variable | Value | Description |
|----------|-------|-------------|
| `ENVIRONMENT` | `production` | Disables debug mode, docs, verbose logging |
| `TZ` | `Africa/Nairobi` | Container timezone |

### Secrets (managed in Secret Manager)

| Secret | Format | Description |
|--------|--------|-------------|
| `DATABASE_URL` | `mysql+pymysql://user:pass@/db?unix_socket=/cloudsql/...` | MySQL connection via Cloud SQL Auth Proxy |
| `JWT_SECRET_KEY` | String (min 32 chars) | JWT signing key |
| `SMTP_PASSWORD` | String | SMTP authentication password |
| `SMTP_USERNAME` | String | SMTP authentication username |
| `SMTP_FROM_EMAIL` | String | Sender email address |
| `CORS_ORIGINS` | JSON array: `["https://..."]` | Allowed frontend origins |

### Application Defaults

All other configuration has sensible defaults defined in the code:

- **`backend/app/config/settings.py`** — App name, version, logging, storage settings
- **`backend/app/auth/config.py`** — JWT algorithm, SMTP host/port, password policy, account lockout

These defaults are used in production unless overridden by environment variables.

---

## Cloud Run Service Configuration

Defined in `cloudbuild.yaml` deploy step:

| Setting | Value |
|---------|-------|
| Port | 8080 |
| Memory | 1Gi |
| CPU | 1 |
| Min instances | 1 |
| Cloud SQL | `PROJECT_ID:us-central1:recon-db` |
| Auth | Unauthenticated (public) |

---

## Request Routing

Defined in `nginx.conf`:

| Path | Destination |
|------|-------------|
| `/api/*` | Proxied to gunicorn on `localhost:8000` |
| `/health` | Proxied to gunicorn on `localhost:8000` |
| `/assets/*` | Served by nginx with 1-year cache |
| `/*` (everything else) | React SPA (`index.html`) |

---

## Troubleshooting

### Check build logs

```bash
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

### Check Cloud Run logs

```bash
gcloud run services logs read recon --region=us-central1 --limit=50
```

### Check service status and env vars

```bash
gcloud run services describe recon --region=us-central1
gcloud run services describe recon --region=us-central1 \
  --format='yaml(spec.template.spec.containers[0].env)'
```

### Check Cloud SQL instance

```bash
gcloud sql instances describe recon-db --format='value(state)'
gcloud sql databases list --instance=recon-db
gcloud sql users list --instance=recon-db
```

### Connect to database directly

```bash
gcloud sql connect recon-db --user=kevin --database=reconciler
```

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Build fails with "permission denied" | Missing IAM roles on service account | Grant `roles/run.admin` and `roles/iam.serviceAccountUser` |
| 502 Bad Gateway | gunicorn not started yet (cold start or migration running) | Wait 10-15 seconds and retry |
| Database connection refused | Wrong credentials in `DATABASE_URL` secret | Verify user/password with `gcloud sql users list`, update secret |
| CORS errors in browser | `CORS_ORIGINS` doesn't include Cloud Run URL | Update the secret with the correct URL (JSON array format) |
| Validation errors on startup | Missing required secrets | Ensure all 6 secrets exist and are accessible |
| `/docs` accessible in production | `ENVIRONMENT` not set to `production` | Check with `gcloud run services describe`, update if needed |

---

## Updating Secrets

To update a secret value:

```bash
echo -n 'new-value' | gcloud secrets versions add SECRET_NAME --data-file=-

# Force Cloud Run to pick up the new version
gcloud run services update recon --region=us-central1 \
  --update-secrets=SECRET_NAME=SECRET_NAME:latest
```

---

## Database Migrations

Alembic migrations run automatically on every container startup (before gunicorn starts). To add a new migration:

```bash
cd backend
alembic revision --autogenerate -m "description of change"
```

Review the generated file in `alembic/versions/`, then commit and push. The migration will run on the next deploy.

---

## Key Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build: Node (frontend) + Python/nginx/supervisord (runtime) |
| `cloudbuild.yaml` | CI/CD pipeline: build, push, deploy to Cloud Run |
| `nginx.conf` | Request routing: SPA, API proxy, static assets |
| `supervisord.conf` | Process management: nginx + alembic/gunicorn |
| `backend/alembic.ini` | Alembic configuration |
| `backend/alembic/env.py` | Alembic environment (reads `DATABASE_URL` from env) |
| `backend/app/config/settings.py` | Application settings with defaults |
| `backend/app/auth/config.py` | Auth settings with defaults |
