# Deployment Guide — Google Cloud Platform

This guide covers deploying the Reconciliation System to GCP using Cloud Run (backend), Cloud SQL (MySQL), Cloud Storage (files), and Firebase Hosting (frontend).

## Architecture

```
Firebase Hosting (React SPA)
    │
    │ /api/** → rewrite
    ▼
Cloud Run (FastAPI container)
    │
    ├── Cloud SQL (MySQL 8.0)
    ├── Cloud Storage (file uploads)
    └── Secret Manager (credentials)
```

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI)
- [Firebase CLI](https://firebase.google.com/docs/cli) (`npm install -g firebase-tools`)
- A GCP project with billing enabled
- Node.js 20+ and npm
- Docker (for local testing)

## Step 1: GCP Project Setup

```bash
# Set your project ID
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

```bash
gcloud artifacts repositories create recon \
    --repository-format=docker \
    --location=$REGION \
    --description="Reconciliation system Docker images"
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

# Create user
gcloud sql users create recon_user \
    --instance=recon-db \
    --password="$(openssl rand -base64 24)"
# Save this password — you'll need it for DATABASE_URL
```

## Step 4: Create Cloud Storage Bucket

```bash
# Create bucket for file uploads
gcloud storage buckets create gs://${PROJECT_ID}-uploads \
    --location=$REGION \
    --uniform-bucket-level-access

# Grant Cloud Run service account access
gcloud storage buckets add-iam-policy-binding gs://${PROJECT_ID}-uploads \
    --member="serviceAccount:$(gcloud iam service-accounts list \
        --filter='displayName:Compute Engine default' \
        --format='value(email)')" \
    --role=roles/storage.objectAdmin
```

## Step 5: Store Secrets in Secret Manager

```bash
# Generate secrets
JWT_SECRET=$(openssl rand -hex 32)
SUPER_ADMIN_SECRET=$(openssl rand -hex 16)
CLOUD_SQL_INSTANCE=$(gcloud sql instances describe recon-db --format='value(connectionName)')

# Create secrets (you'll be prompted for values)
echo -n "mysql+pymysql://recon_user:YOUR_DB_PASSWORD@/${PROJECT_ID}:${REGION}:recon-db/reconciler?unix_socket=/cloudsql/${CLOUD_SQL_INSTANCE}" | \
    gcloud secrets create database-url --data-file=-

echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret-key --data-file=-
echo -n "$SUPER_ADMIN_SECRET" | gcloud secrets create super-admin-secret --data-file=-

# SMTP credentials
echo -n "your-smtp-password" | gcloud secrets create smtp-password --data-file=-
```

## Step 6: Build and Deploy Backend

### First-time deployment

```bash
# Configure Docker for Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest

# Get Cloud SQL connection name
CLOUD_SQL_INSTANCE=$(gcloud sql instances describe recon-db --format='value(connectionName)')

# Deploy to Cloud Run
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
CORS_ORIGINS=[\"https://your-domain.com\"],\
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
LOG_FILE_PATH=logs/app.log,\
LOG_FILE_MAX_BYTES=10485760,\
LOG_FILE_BACKUP_COUNT=5,\
LOG_SQL_QUERIES=false,\
LOG_REQUEST_BODY=false,\
LOG_RESPONSE_BODY=false" \
    --set-secrets "\
DATABASE_URL=database-url:latest,\
JWT_SECRET_KEY=jwt-secret-key:latest,\
SUPER_ADMIN_SECRET=super-admin-secret:latest,\
SMTP_PASSWORD=smtp-password:latest"
```

> **Note:** `LOG_FILE_ENABLED=false` for Cloud Run since container logs go to Cloud Logging automatically. No filesystem logging needed.

### Run database migrations

```bash
# Create a one-off Cloud Run job for migrations
gcloud run jobs create migrate-db \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/recon/recon-api:latest \
    --region $REGION \
    --add-cloudsql-instances=$CLOUD_SQL_INSTANCE \
    --set-env-vars "TZ=Africa/Nairobi" \
    --set-secrets "DATABASE_URL=database-url:latest" \
    --command "alembic" \
    --args "upgrade,head" \
    --max-retries 0

# Execute the migration job
gcloud run jobs execute migrate-db --region $REGION --wait
```

### Create the first super admin

```bash
# Get the Cloud Run service URL
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

## Step 7: Deploy Frontend

### Initialize Firebase

```bash
# Login to Firebase
firebase login

# Link to your GCP project
firebase use $PROJECT_ID

# Update .firebaserc with your project ID
```

### Update firebase.json

Edit `firebase.json` and set the correct Cloud Run region if different from `us-central1`:

```json
"run": {
    "serviceId": "recon-api",
    "region": "us-central1"
}
```

### Build and deploy

```bash
# Install dependencies and build
cd frontend
npm ci
npm run build
cd ..

# Deploy to Firebase Hosting
firebase deploy --only hosting
```

### Verify

Your app is now available at:
- Frontend: `https://PROJECT_ID.web.app` (or your custom domain)
- API: `https://PROJECT_ID.web.app/api/v1/health`
- API calls from the frontend go through Firebase Hosting rewrites to Cloud Run (same origin, no CORS needed)

## Step 8: Set Up CI/CD (GitHub Actions)

### Configure Workload Identity Federation (recommended over service account keys)

```bash
# Create a Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --location=global \
    --display-name="GitHub Actions Pool"

# Create a Provider for GitHub
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
REPO=your-github-username/your-repo-name

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --role=roles/iam.workloadIdentityUser \
    --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO}"
```

### Add GitHub repository secrets and variables

**Repository Variables** (Settings > Secrets and variables > Actions > Variables):
- `GCP_PROJECT_ID`: Your GCP project ID
- `GCP_REGION`: `us-central1` (or your preferred region)

**Repository Secrets** (Settings > Secrets and variables > Actions > Secrets):
- `WIF_PROVIDER`: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- `WIF_SERVICE_ACCOUNT`: `github-actions@PROJECT_ID.iam.gserviceaccount.com`
- `FIREBASE_SERVICE_ACCOUNT`: Firebase service account JSON (generate from Firebase console > Project Settings > Service Accounts)

### How it works

After setup, pushing to `main` triggers automatic deployments:
- Changes in `app/`, `alembic/`, `requirements.txt`, or `Dockerfile` → deploys backend to Cloud Run
- Changes in `frontend/` → builds and deploys to Firebase Hosting

## Custom Domain

### Firebase Hosting (frontend)

```bash
firebase hosting:channel:deploy production
# Or configure custom domain in Firebase Console > Hosting > Custom domains
```

### Cloud Run (API) — only needed if not using Firebase rewrites

```bash
gcloud run domain-mappings create \
    --service recon-api \
    --domain api.yourdomain.com \
    --region $REGION
```

When using Firebase Hosting rewrites (recommended), the API is accessed through the same domain as the frontend. No separate API domain is needed.

## Monitoring

### Cloud Run logs

```bash
# View recent logs
gcloud run services logs read recon-api --region $REGION --limit 50

# Stream logs in real-time
gcloud run services logs tail recon-api --region $REGION
```

### Cloud SQL monitoring

```bash
# Check instance status
gcloud sql instances describe recon-db --format='yaml(state, settings.activationPolicy)'
```

## Cost Optimization

- **Cloud Run**: Set `--min-instances 0` to scale to zero during off-hours
- **Cloud SQL**: Use `db-f1-micro` ($8/month) for development; `db-g1-small` ($25/month) for production
- **Cloud SQL**: Stop the instance when not in use: `gcloud sql instances patch recon-db --activation-policy=NEVER`
- **Cloud Storage**: Standard class is fine; lifecycle rules can archive old batch files

## Troubleshooting

### Cloud Run container won't start

```bash
# Check deployment logs
gcloud run revisions list --service recon-api --region $REGION
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=recon-api" --limit 20 --format json
```

### Database connection issues

```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe recon-db --format='value(state)'

# Verify the Cloud Run service has the Cloud SQL connection
gcloud run services describe recon-api --region $REGION --format='yaml(spec.template.metadata.annotations)'
```

### Migrations fail

```bash
# Run migrations manually
gcloud run jobs execute migrate-db --region $REGION --wait

# Check migration job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=migrate-db" --limit 20
```
