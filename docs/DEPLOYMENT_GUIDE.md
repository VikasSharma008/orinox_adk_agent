# ORINOX — Complete Setup & Deployment Guide

**From zero to a running public URL. Every command included.**

This guide uses Google Cloud Shell (browser terminal) for everything. You don't need anything installed on your local machine.

---

## Phase 1: Create the GCP Project (5 minutes)

### Step 1.1 — Open Google Cloud Console

Go to: https://console.cloud.google.com

Sign in with your Google account (free @gmail.com works).

### Step 1.2 — Create a new project

1. Click the project dropdown at the top of the page (next to "Google Cloud")
2. Click **"New Project"**
3. Project name: `orinox-wealth-copilot`
4. Click **"Create"**
5. Wait 30 seconds, then select the new project from the dropdown

### Step 1.3 — Note your Project ID

The Project ID is shown under the project name. It might be slightly different from the name (e.g. `orinox-wealth-copilot` or `orinox-wealth-copilot-12345`). You'll use this everywhere.

```
Your Project ID: _______________________ (write this down)
```

---

## Phase 2: Enable APIs (2 minutes)

### Step 2.1 — One-click enable

Open this URL (replace PROJECT_ID if different):

```
https://console.cloud.google.com/apis/enableflow?apiid=generativelanguage.googleapis.com,cloudbuild.googleapis.com,run.googleapis.com,artifactregistry.googleapis.com,alloydb.googleapis.com,compute.googleapis.com,servicenetworking.googleapis.com&project=orinox-wealth-copilot
```

Click **"Enable"** and wait for all 7 APIs to activate.

### Step 2.2 — Verify (optional)

Open Cloud Shell (click the terminal icon `>_` at the top right of the console), then run:

```bash
gcloud services list --enabled --filter="name:(generativelanguage OR cloudbuild OR run OR artifactregistry OR alloydb)"
```

You should see all the APIs listed.

---

## Phase 3: Create a Service Account (3 minutes)

### Step 3.1 — Open Cloud Shell

Click the `>_` icon at the top right of the Google Cloud Console. A terminal opens at the bottom of your browser.

### Step 3.2 — Set your project

```bash
export PROJECT_ID=orinox-wealth-copilot
gcloud config set project $PROJECT_ID
```

### Step 3.3 — Create the service account

```bash
gcloud iam service-accounts create orinox-sa \
  --display-name="ORINOX Service Account"
```

### Step 3.4 — Grant permissions

```bash
export SA_EMAIL=orinox-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Permission to call Gemini API
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

# Permission to connect to AlloyDB
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/alloydb.client"

# Permission for Cloud Run to use this SA
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker"
```

---

## Phase 4: Get the Code (2 minutes)

### Step 4.1 — Clone the repo (or upload)

In Cloud Shell:

```bash
cd ~
git clone https://github.com/YOUR-REPO/orinox.git
cd orinox
```

Or if uploading the tar.gz file — click the three-dot menu in Cloud Shell, select "Upload file", then:

```bash
cd ~
tar xzf orinox-v3-final.tar.gz
cd orinox
```

### Step 4.2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 4.3 — Verify Node.js (for MCP servers)

```bash
node --version   # Should show v18+ or v20+
npx --version    # Should work
```

Cloud Shell already has Node.js installed.

---

## Phase 5: Run Locally in Cloud Shell (5 minutes)

This runs the app with SQLite (no AlloyDB needed). Good for verifying everything works before deploying.

### Step 5.1 — Create the .env file

```bash
cat > .env << 'EOF'
PROJECT_ID=orinox-wealth-copilot
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/text-embedding-004
USE_SQLITE=true
SQLITE_PATH=orinox_dev.db
MCP_FETCH_ENABLED=true
MCP_MEMORY_ENABLED=true
MCP_FILESYSTEM_ENABLED=true
MCP_FS_ROOT=/tmp/orinox_output
PORT=8080
LOG_LEVEL=info
ENVIRONMENT=development
EOF
```

### Step 5.2 — Authenticate for Gemini API

```bash
gcloud auth application-default login
```

A browser tab opens. Sign in with your Google account and click "Allow". This creates local credentials that the Gemini SDK picks up automatically.

### Step 5.3 — Seed demo data

```bash
python -m db.seed_data
```

You should see:
```
Seeding ORINOX v3...
  Client: Priya Sharma
  Client: Rajesh Patel
  ...
Done: 12 clients seeded.
```

### Step 5.4 — Start the server

```bash
python app.py
```

You should see:
```
Starting MCP servers...
  MCP fetch: started (pid=12345)
  MCP memory: started (pid=12346)
  MCP filesystem: started (pid=12347)
ORINOX v3 ready — 30 tools registered
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### Step 5.5 — Test it

Open a **second Cloud Shell tab** (click the "+" icon), then run:

```bash
# Health check
curl -s http://localhost:8080/health | python3 -m json.tool

# List clients (should show 12)
curl -s http://localhost:8080/clients?limit=3 | python3 -m json.tool

# List all tools (should show 30)
curl -s http://localhost:8080/tools | python3 -m json.tool

# MCP server status
curl -s http://localhost:8080/mcp/status | python3 -m json.tool

# Hero demo
curl -s -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "RBI hiked rates by 50bps. Who is exposed?"}' \
  | python3 -m json.tool
```

### Step 5.6 — Preview in browser (optional)

Click the **Web Preview** button (globe icon at top right of Cloud Shell) then "Preview on port 8080". Navigate to `/health` or `/tools`.

### Step 5.7 — Stop the server

Press `Ctrl+C` in the first tab.

---

## Phase 6: Set Up AlloyDB (15 minutes)

> **You can skip this phase entirely** and deploy with SQLite. AlloyDB is optional for the hackathon. Skip to Phase 7 if you want to deploy quickly.

### Step 6.1 — Reserve IP range for VPC peering

```bash
gcloud compute addresses create alloydb-ip-range \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network=default
```

### Step 6.2 — Create private VPC connection

```bash
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=alloydb-ip-range \
  --network=default
```

Wait 1-2 minutes for "Operation completed successfully."

### Step 6.3 — Create AlloyDB cluster

Pick a strong password and remember it:

```bash
export DB_PASSWORD="YourStrongPassword123!"

gcloud alloydb clusters create orinox-cluster \
  --region=us-central1 \
  --password=${DB_PASSWORD} \
  --network=default
```

Takes 2-3 minutes.

### Step 6.4 — Create primary instance

```bash
gcloud alloydb instances create orinox-primary \
  --cluster=orinox-cluster \
  --region=us-central1 \
  --instance-type=PRIMARY \
  --cpu-count=2
```

Takes 5-8 minutes. This is the longest wait.

### Step 6.5 — Get the private IP address

```bash
export ALLOYDB_IP=$(gcloud alloydb instances describe orinox-primary \
  --cluster=orinox-cluster \
  --region=us-central1 \
  --format="value(ipAddress)")

echo "AlloyDB IP: ${ALLOYDB_IP}"
```

### Step 6.6 — Create the orinox database and tables

```bash
# Install psql if not present
sudo apt-get install -y postgresql-client

# Create database
psql -h ${ALLOYDB_IP} -U postgres -c "CREATE DATABASE orinox;"
# Enter the password from Step 6.3 when prompted

# Create tables
psql -h ${ALLOYDB_IP} -U postgres -d orinox -f db/schema.sql
# Enter password again
```

### Step 6.7 — Seed AlloyDB with demo data

Update .env to use AlloyDB:

```bash
cat > .env << EOF
PROJECT_ID=orinox-wealth-copilot
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/text-embedding-004
USE_SQLITE=false
ALLOYDB_HOST=${ALLOYDB_IP}
ALLOYDB_PORT=5432
ALLOYDB_USER=postgres
ALLOYDB_PASSWORD=${DB_PASSWORD}
ALLOYDB_DATABASE=orinox
MCP_FETCH_ENABLED=true
MCP_MEMORY_ENABLED=true
MCP_FILESYSTEM_ENABLED=true
MCP_FS_ROOT=/tmp/orinox_output
PORT=8080
ENVIRONMENT=production
EOF
```

```bash
python -m db.seed_data
```

### Step 6.8 — Create VPC connector for Cloud Run

Cloud Run needs this to reach AlloyDB's private IP:

```bash
gcloud compute networks vpc-access connectors create orinox-connector \
  --region=us-central1 \
  --network=default \
  --range=10.8.0.0/28
```

---

## Phase 7: Deploy to Cloud Run (10 minutes)

### Step 7.1 — Bake seed data into Docker image

For SQLite mode, seed data must be in the image. Add this line to Dockerfile:

```bash
sed -i '/^CMD/i RUN python -m db.seed_data' Dockerfile
```

This inserts `RUN python -m db.seed_data` before the `CMD` line. Skip this if using AlloyDB (data is already in the database).

### Step 7.2 — Deploy

**Option A: SQLite (simple, no AlloyDB)**

```bash
export PROJECT_ID=orinox-wealth-copilot
export SA_EMAIL=orinox-sa@${PROJECT_ID}.iam.gserviceaccount.com

gcloud run deploy orinox \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account ${SA_EMAIL} \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},GEMINI_MODEL=gemini-2.5-flash,EMBEDDING_MODEL=models/text-embedding-004,USE_SQLITE=true,SQLITE_PATH=/tmp/orinox_dev.db,MCP_FETCH_ENABLED=true,MCP_MEMORY_ENABLED=true,MCP_FILESYSTEM_ENABLED=true,MCP_FS_ROOT=/tmp/orinox_output,ENVIRONMENT=production" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 3
```

**Option B: AlloyDB (persistent data)**

```bash
export PROJECT_ID=orinox-wealth-copilot
export SA_EMAIL=orinox-sa@${PROJECT_ID}.iam.gserviceaccount.com

gcloud run deploy orinox \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account ${SA_EMAIL} \
  --vpc-connector orinox-connector \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},GEMINI_MODEL=gemini-2.5-flash,EMBEDDING_MODEL=models/text-embedding-004,USE_SQLITE=false,ALLOYDB_HOST=${ALLOYDB_IP},ALLOYDB_PORT=5432,ALLOYDB_USER=postgres,ALLOYDB_PASSWORD=${DB_PASSWORD},ALLOYDB_DATABASE=orinox,MCP_FETCH_ENABLED=true,MCP_MEMORY_ENABLED=true,MCP_FILESYSTEM_ENABLED=true,MCP_FS_ROOT=/tmp/orinox_output,ENVIRONMENT=production" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 3
```

### Step 7.3 — Wait for build + deploy

Cloud Build will:
1. Build Docker image (Python + Node.js + MCP servers) — ~3 minutes
2. Push to Artifact Registry — ~1 minute
3. Deploy to Cloud Run — ~1 minute

When done you see:

```
Service [orinox] revision [orinox-00001-xxx] has been deployed
and is serving 100 percent of traffic.
Service URL: https://orinox-xxxxx-uc.a.run.app
```

### Step 7.4 — Save the URL

```bash
export SERVICE_URL=$(gcloud run services describe orinox \
  --region us-central1 \
  --format="value(status.url)")

echo "ORINOX is live at: ${SERVICE_URL}"
```

---

## Phase 8: Verify the Deployment (2 minutes)

```bash
# 1. Health check
curl -s ${SERVICE_URL}/health | python3 -m json.tool

# 2. Tools (should show 30)
curl -s ${SERVICE_URL}/tools | python3 -m json.tool

# 3. MCP servers
curl -s ${SERVICE_URL}/mcp/status | python3 -m json.tool

# 4. Clients (should show 12)
curl -s "${SERVICE_URL}/clients?limit=5" | python3 -m json.tool

# 5. Hero demo
curl -s -X POST ${SERVICE_URL}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "RBI hiked rates by 50bps. Who is exposed and what should I tell them?"}' \
  | python3 -m json.tool

# 6. Pre-call brief
curl -s -X POST ${SERVICE_URL}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Brief me on Priya Sharma before my call"}' \
  | python3 -m json.tool
```

**The URL is public. Anyone can access it without authentication. Share it in your hackathon submission.**

---

## Phase 9: Quick Reference Commands

```bash
# ─── Redeploy after code changes ───
gcloud run deploy orinox --source . --region us-central1

# ─── View live logs ───
gcloud run services logs tail orinox --region us-central1

# ─── View recent logs ───
gcloud run services logs read orinox --region us-central1 --limit 50

# ─── Get the public URL ───
gcloud run services describe orinox --region us-central1 --format="value(status.url)"

# ─── Update an environment variable ───
gcloud run services update orinox --region us-central1 \
  --update-env-vars="GEMINI_MODEL=gemini-2.5-flash"

# ─── Keep one instance warm (avoids cold start delay) ───
gcloud run services update orinox --region us-central1 --min-instances 1

# ─── Delete everything after hackathon ───
gcloud run services delete orinox --region us-central1 --quiet
# If AlloyDB was created:
gcloud alloydb instances delete orinox-primary --cluster=orinox-cluster --region=us-central1 --quiet
gcloud alloydb clusters delete orinox-cluster --region=us-central1 --quiet
gcloud compute networks vpc-access connectors delete orinox-connector --region=us-central1 --quiet
```

---

## Summary: What You Just Built

| Layer | What | How |
|-------|------|-----|
| Orchestrator | ADK + Gemini primary agent | Routes to 4 sub-agents |
| Sub-agents | Market, Client Brief, Comms, Schedule | Python + Gemini |
| Database | AlloyDB or SQLite | 9 tables, vector search ready |
| MCP: Fetch | Live market news via MCP protocol | Zero-config npx server |
| MCP: Memory | Client context knowledge graph | Zero-config npx server |
| MCP: Filesystem | Save briefs, reports, exports | Zero-config npx server |
| API | FastAPI, 12+ endpoints | Cloud Run, public URL |
| Tools | 30 registered | 16 direct + 14 via MCP |
