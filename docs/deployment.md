# Deployment Guide — Google Cloud Platform

This guide covers deploying the Reconciliation System to GCP using Cloud Run (backend + frontend), Cloud SQL (MySQL), Cloud Storage (file uploads), and Secret Manager (credentials).

## Architecture

```
Cloud Run — recon-frontend (nginx)
    │
    │  Serves React SPA
    │  Proxies /api/** to backend
    ▼
Cloud Run — recon-api (FastAPI + gunicorn)
    │
    ├── Cloud SQL (MySQL 8.0) — via Unix socket (Cloud SQL Auth Proxy)
    ├── Cloud Storage (file uploads) — via Application Default Credentials
    └── Secret Manager (credentials) — mounted as environment variables
```

Both services run on Cloud Run. The frontend nginx container reverse-proxies API requests to the backend, so the browser only talks to one origin (no CORS needed).

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI)
- A GCP project with billing enabled
- Docker installed and running
- Node.js 20+ and npm (for local frontend builds)
- Your user added to the Docker group: `sudo usermod -aG docker $USER && newgrp docker`

## Step 1: GCP Project Setup

```bash
# Set your project ID and region
export PROJECT_ID=your-project-id
export REGION=us-central1

gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    iam.googleapis.com
```

## Step 2: Create Artifact Registry Repository

This stores Docker images for both backend and frontend services.

```bash
gcloud artifacts repositories create recon \
    --repository-format=docker \
    --location=$REGION \
    --description="Reconciliation system Docker images"

# Configure Docker to authenticate with Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

## Step 3: Create Cloud SQL Instance

```bash
# Create MySQL 8.0 instance
gcloud sql instances create recon-db \
    --database-version=MYSQL_8_0 \
    --tier=db-g1-small \
    --region=$REGION \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=02:00 \
    --availability-type=zonal

# Create database
gcloud sql databases create reconciler --instance=recon-db

# Create database user (save this password — you'll need it for DATABASE_URL)
DB_PASSWORD=$(openssl rand -base64 24)
echo "Save this password: $DB_PASSWORD"

gcloud sql users create your_db_user \
    --instance=recon-db \
    --password="$DB_PASSWORD"
```

## Step 4: Create Cloud Storage Bucket

```bash
# Create bucket for file uploads
gcloud storage buckets create gs://${PROJECT_ID}-uploads \
    --location=$REGION \
    --uniform-bucket-level-access

# Get the Compute Engine default service account email
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter='displayName:Compute Engine default' \
    --format='value(email)')

# Grant Cloud Run service account access to the bucket
gcloud storage buckets add-iam-policy-binding gs://${PROJECT_ID}-uploads \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/storage.objectAdmin
```

## Step 5: Grant IAM Permissions to Compute Engine Service Account

Cloud Run uses the Compute Engine default service account. It needs access to Secret Manager and Cloud SQL.

```bash
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter='displayName:Compute Engine default' \
    --format='value(email)')

# Allow reading secrets
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/secretmanager.secretAccessor

# Allow connecting to Cloud SQL
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/cloudsql.client
```

## Step 6: Store Secrets in Secret Manager

```bash
# Get Cloud SQL connection name (needed for DATABASE_URL)
CLOUD_SQL_INSTANCE=$(gcloud sql instances describe recon-db --format='value(connectionName)')

# Generate secrets
JWT_SECRET=$(openssl rand -hex 32)
SUPER_ADMIN_SECRET=$(openssl rand -hex 16)

echo "Save JWT_SECRET: $JWT_SECRET"
echo "Save SUPER_ADMIN_SECRET: $SUPER_ADMIN_SECRET"

# Store DATABASE_URL (replace your_db_user and YOUR_DB_PASSWORD)
echo -n "mysql+pymysql://your_db_user:YOUR_DB_PASSWORD@/reconciler?unix_socket=/cloudsql/${CLOUD_SQL_INSTANCE}" | \
    gcloud secrets create database-url --data-file=-

# Store JWT secret
echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret-key --data-file=-

# Store super admin secret
echo -n "$SUPER_ADMIN_SECRET" | gcloud secrets create super-admin-secret --data-file=-

# Store SMTP password (replace with your actual app password)
echo -n "your-smtp-app-password" | gcloud secrets create smtp-password --data-file=-
```

> **Important:** The `--data-file=-` flag (with the dash) tells gcloud to read from stdin (the piped value). Don't omit the dash.

### Updating a secret value

If you need to change a secret later (e.g., wrong password):

```bash
echo -n "new-value-here" | gcloud secrets versions add database-url --data-file=-
```

## Step 7: Build and Deploy Backend

### Build and push Docker image

```bash
# Build the backend image (run from project root)
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest ./backend

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest
```

### Deploy to Cloud Run

```bash
CLOUD_SQL_INSTANCE=$(gcloud sql instances describe recon-db --format='value(connectionName)')

gcloud run deploy recon-api \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --add-cloudsql-instances=$CLOUD_SQL_INSTANCE \
    --min-instances 0 \
    --max-instances 10 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 120 \
    --concurrency 80 \
    --set-env-vars "\
APP_NAME=Payment Gateway Reconciliation API,\
APP_VERSION=2.0.0,\
DEBUG=false,\
ENVIRONMENT=production,\
TZ=Africa/Nairobi,\
STORAGE_BACKEND=gcs,\
GCS_BUCKET=${PROJECT_ID}-uploads,\
JWT_ALGORITHM=HS256,\
ACCESS_TOKEN_EXPIRE_MINUTES=15,\
REFRESH_TOKEN_EXPIRE_HOURS=1,\
SMTP_HOST=smtp.gmail.com,\
SMTP_PORT=587,\
SMTP_USERNAME=your-email@company.com,\
SMTP_FROM_EMAIL=noreply@company.com,\
SMTP_FROM_NAME=Reconciler System,\
SMTP_USE_TLS=true,\
ALLOWED_EMAIL_DOMAIN=company.com,\
OTP_LOGIN_LIFETIME_SECONDS=60,\
OTP_WELCOME_LIFETIME_SECONDS=300,\
OTP_FORGOT_PASSWORD_LIFETIME_SECONDS=300,\
OTP_MAX_ATTEMPTS=3,\
OTP_RESEND_COOLDOWN_SECONDS=120,\
MAX_FAILED_LOGIN_ATTEMPTS=5,\
ACCOUNT_LOCKOUT_MINUTES=15,\
PASSWORD_EXPIRY_DAYS=90,\
PASSWORD_HISTORY_COUNT=5,\
PASSWORD_MIN_LENGTH=8,\
PASSWORD_REQUIRE_UPPERCASE=true,\
PASSWORD_REQUIRE_LOWERCASE=true,\
PASSWORD_REQUIRE_DIGIT=true,\
PASSWORD_REQUIRE_SPECIAL=true,\
LOG_LEVEL=INFO,\
LOG_FORMAT=json,\
LOG_FILE_ENABLED=false,\
LOG_SQL_QUERIES=false,\
LOG_REQUEST_BODY=false,\
LOG_RESPONSE_BODY=false" \
    --set-secrets "\
DATABASE_URL=database-url:latest,\
JWT_SECRET_KEY=jwt-secret-key:latest,\
SUPER_ADMIN_SECRET=super-admin-secret:latest,\
SMTP_PASSWORD=smtp-password:latest"
```

> **Note:** `LOG_FILE_ENABLED=false` for Cloud Run — container logs go to Cloud Logging automatically. No filesystem logging needed.

## Step 8: Run Database Migrations

```bash
CLOUD_SQL_INSTANCE=$(gcloud sql instances describe recon-db --format='value(connectionName)')

# Create a Cloud Run Job for migrations
gcloud run jobs create migrate-db \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest \
    --region $REGION \
    --set-cloudsql-instances=$CLOUD_SQL_INSTANCE \
    --set-env-vars "TZ=Africa/Nairobi" \
    --set-secrets "DATABASE_URL=database-url:latest" \
    --command "alembic" \
    --args "upgrade,head" \
    --max-retries 0

# Execute the migration job
gcloud run jobs execute migrate-db --region $REGION --wait
```

> **Note:** Cloud Run Jobs use `--set-cloudsql-instances` (not `--add-cloudsql-instances` which is for Cloud Run services).

### Verify migrations ran successfully

```bash
# Check job status
gcloud run jobs executions list --job migrate-db --region $REGION

# Check logs if it failed
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=migrate-db" --limit 20
```

## Step 9: Create the First Super Admin

```bash
SERVICE_URL=$(gcloud run services describe recon-api --region $REGION --format='value(status.url)')

curl -X POST ${SERVICE_URL}/api/v1/users/create-super-admin \
    -H "Content-Type: application/json" \
    -d '{
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@company.com",
        "password": "YourSecurePassword1!",
        "secret_key": "YOUR_SUPER_ADMIN_SECRET"
    }'
```

Replace:
- `admin@company.com` with the admin's email (must match `ALLOWED_EMAIL_DOMAIN`)
- `YourSecurePassword1!` with a strong password meeting the password policy
- `YOUR_SUPER_ADMIN_SECRET` with the value you stored in Secret Manager

## Step 10: Verify Backend

```bash
SERVICE_URL=$(gcloud run services describe recon-api --region $REGION --format='value(status.url)')

# Health check
curl ${SERVICE_URL}/health

# API docs (Swagger UI)
echo "Swagger UI: ${SERVICE_URL}/docs"
```

## Step 11: Build and Deploy Frontend

The frontend is a React SPA served by nginx on Cloud Run. Nginx reverse-proxies `/api/**` requests to the backend service.

### Build and push Docker image

```bash
# Build the frontend image (from project root)
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-frontend:latest ./frontend

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-frontend:latest
```

### Deploy to Cloud Run

```bash
# Get the backend service URL (nginx will proxy API requests here)
BACKEND_URL=$(gcloud run services describe recon-api --region $REGION --format='value(status.url)')

gcloud run deploy recon-frontend \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-frontend:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --min-instances 0 \
    --max-instances 5 \
    --memory 256Mi \
    --cpu 1 \
    --set-env-vars "BACKEND_URL=${BACKEND_URL}"
```

### How it works

The frontend Docker image uses a multi-stage build:
1. **Stage 1 (Node.js):** Installs dependencies and builds the React app (`npm run build`)
2. **Stage 2 (nginx):** Copies the built static files and the nginx config

The `nginx.conf` template uses `${BACKEND_URL}` which is substituted at container startup via nginx's built-in `envsubst` support. This allows the same image to work with different backend URLs.

Nginx handles three concerns:
- `/api/**` — proxied to the backend Cloud Run service
- `/assets/**` — served with 1-year cache headers (Vite hashes filenames)
- `/**` — falls back to `index.html` for SPA client-side routing

### Verify frontend

```bash
FRONTEND_URL=$(gcloud run services describe recon-frontend --region $REGION --format='value(status.url)')
echo "Frontend: ${FRONTEND_URL}"
```

Open this URL in your browser — you should see the login page.

## Step 12: Set Up CI/CD (GitHub Actions)

Automated deployments on push to `main`. Uses Workload Identity Federation (no service account keys stored in GitHub).

### Configure Workload Identity Federation

```bash
# Create a Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --location=global \
    --display-name="GitHub Actions Pool"

# Create an OIDC Provider for GitHub
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location=global \
    --workload-identity-pool=github-pool \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com"

# Create a service account for GitHub Actions
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Deploy"

# Grant necessary roles
SA_EMAIL=github-actions@${PROJECT_ID}.iam.gserviceaccount.com

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/run.admin

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/artifactregistry.writer

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/iam.serviceAccountUser

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/secretmanager.secretAccessor

# Allow GitHub Actions to impersonate the service account
# Replace with your GitHub repo (e.g., your-username/recon)
REPO=your-github-username/your-repo-name
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --role=roles/iam.workloadIdentityUser \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO}"
```

### Add GitHub repository secrets and variables

Go to your GitHub repo > **Settings** > **Secrets and variables** > **Actions**.

**Repository Variables** (Variables tab):

| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_REGION` | `us-central1` (or your region) |

**Repository Secrets** (Secrets tab):

| Secret | Value |
|--------|-------|
| `WIF_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `WIF_SERVICE_ACCOUNT` | `github-actions@PROJECT_ID.iam.gserviceaccount.com` |

Replace `PROJECT_NUMBER` with your actual project number (from `gcloud projects describe $PROJECT_ID --format='value(projectNumber)'`).

### How CI/CD works

After setup, pushing to `main` triggers automatic deployments:

| Trigger (files changed) | Workflow | Action |
|--------------------------|----------|--------|
| `app/`, `alembic/`, `requirements.txt`, `Dockerfile` | `deploy-backend.yml` | Build image → run migrations → deploy `recon-api` to Cloud Run |
| `frontend/` | `deploy-frontend.yml` | Build image → deploy `recon-frontend` to Cloud Run |

Workflow files are in `.github/workflows/`.

## Custom Domain

### Map a custom domain to the frontend

```bash
gcloud run domain-mappings create \
    --service recon-frontend \
    --domain app.yourdomain.com \
    --region $REGION
```

Follow the DNS verification instructions that gcloud outputs. Once DNS propagates, your app is available at `https://app.yourdomain.com`.

### Map a custom domain to the API (optional)

Only needed if you want direct API access outside the frontend proxy.

```bash
gcloud run domain-mappings create \
    --service recon-api \
    --domain api.yourdomain.com \
    --region $REGION
```

## Monitoring

### View Cloud Run logs

```bash
# Backend logs
gcloud run services logs read recon-api --region $REGION --limit 50

# Frontend logs
gcloud run services logs read recon-frontend --region $REGION --limit 50

# Stream logs in real-time
gcloud run services logs tail recon-api --region $REGION
```

### Cloud SQL monitoring

```bash
# Check instance status
gcloud sql instances describe recon-db --format='yaml(state, settings.activationPolicy)'

# List database users
gcloud sql users list --instance=recon-db
```

### Cloud Run service status

```bash
# List all services
gcloud run services list --region $REGION

# Describe a specific service
gcloud run services describe recon-api --region $REGION
```

## Updating the Application

### Manual backend update

```bash
# Rebuild and push
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest ./backend
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest

# Run migrations (if schema changed)
gcloud run jobs update migrate-db \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest \
    --region $REGION
gcloud run jobs execute migrate-db --region $REGION --wait

# Deploy new revision
gcloud run services update recon-api \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest \
    --region $REGION
```

### Manual frontend update

```bash
# Rebuild and push
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-frontend:latest ./frontend
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-frontend:latest

# Deploy new revision
gcloud run services update recon-frontend \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-frontend:latest \
    --region $REGION
```

## Cost Optimization

| Service | Dev/Staging | Production |
|---------|-------------|------------|
| **Cloud Run (backend)** | `--min-instances 0` (scale to zero) | `--min-instances 1` (avoid cold starts) |
| **Cloud Run (frontend)** | `--min-instances 0` | `--min-instances 0` (nginx starts fast) |
| **Cloud SQL** | `db-f1-micro` (~$8/month) | `db-g1-small` (~$25/month) |

**Stop Cloud SQL when not in use** (dev/staging):

```bash
# Stop
gcloud sql instances patch recon-db --activation-policy=NEVER

# Start
gcloud sql instances patch recon-db --activation-policy=ALWAYS
```

## Troubleshooting

### Docker permission denied

```
permission denied while trying to connect to the Docker daemon socket
```

Fix: Add your user to the Docker group.

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Docker push "Unauthenticated request"

```
denied: Unauthenticated request
```

Cause: Running `sudo docker push` — root doesn't have gcloud credentials.

Fix: Run without `sudo` (add your user to the Docker group instead).

### Secret Manager "permission denied"

```
does not have secretmanager.versions.access
```

Fix: Grant the Compute Engine service account the Secret Accessor role.

```bash
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter='displayName:Compute Engine default' \
    --format='value(email)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/secretmanager.secretAccessor
```

### Cloud SQL "permission denied" from Cloud Run

```
Possibly missing permission cloudsql.instances.get
```

Fix: Grant the Cloud SQL Client role.

```bash
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter='displayName:Compute Engine default' \
    --format='value(email)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/cloudsql.client
```

### Cloud SQL "Access denied for user"

The DATABASE_URL secret has the wrong username or password.

```bash
# Check which users exist
gcloud sql users list --instance=recon-db

# Update the secret with the correct credentials
CLOUD_SQL_INSTANCE=$(gcloud sql instances describe recon-db --format='value(connectionName)')

echo -n "mysql+pymysql://correct_user:correct_password@/reconciler?unix_socket=/cloudsql/${CLOUD_SQL_INSTANCE}" | \
    gcloud secrets versions add database-url --data-file=-
```

### Migration job fails

```bash
# Check logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=migrate-db" --limit 20

# Update the job image (if you rebuilt)
gcloud run jobs update migrate-db \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest \
    --region $REGION

# Re-run
gcloud run jobs execute migrate-db --region $REGION --wait
```

### Cloud Run container won't start

```bash
# Check recent revisions
gcloud run revisions list --service recon-api --region $REGION

# Check detailed logs
gcloud logging read \
    "resource.type=cloud_run_revision AND resource.labels.service_name=recon-api" \
    --limit 20 --format json
```

### GCS "permission denied" on file upload

```
does not have storage.objects.list access
```

Fix: Grant the Storage Object Admin role on the bucket.

```bash
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter='displayName:Compute Engine default' \
    --format='value(email)')

gcloud storage buckets add-iam-policy-binding gs://${PROJECT_ID}-uploads \
    --member="serviceAccount:${SA_EMAIL}" \
    --role=roles/storage.objectAdmin
```

### Cloud Run Jobs flag differences

Cloud Run **services** use `--add-cloudsql-instances`.
Cloud Run **jobs** use `--set-cloudsql-instances`.

Using the wrong flag will cause an "unrecognized arguments" error.

## File Reference

| File | Purpose |
|------|---------|
| `backend/Dockerfile` | Backend Docker image (Python 3.11 + gunicorn + uvicorn) |
| `frontend/Dockerfile` | Frontend Docker image (multi-stage: Node build + nginx) |
| `frontend/nginx.conf` | Nginx config template (API proxy + SPA routing) |
| `backend/.dockerignore` | Excludes .env files, uploads, logs from backend image |
| `backend/alembic/` | Database migration files |
| `backend/.env.production` | Production env var template (do NOT commit with real values) |
