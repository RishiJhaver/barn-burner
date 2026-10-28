# CodeGrid — Master AWS Deployment & Environment Configuration Runbook

> **Audience**: Step-by-step production deployment guide designed for clarity, security, and beginners.  
> **Cost**: **$0.00 to ~$14.00/month** (leveraging AWS Free Tier).

---

## 1. Where Do You Change Environment Variables? (In Code or Where?)

> [!IMPORTANT]
> **You DO NOT change any `.py` or `.ts` code files!**  
> Never hardcode database passwords, AWS secrets, or IP addresses into source code.  
> The code is built using `pydantic-settings` (backend) and `import.meta.env` (frontend) which automatically read external environment variables.

You will configure environment variables in **exactly TWO places**:

```
 ┌────────────────────────────────────────┐       ┌────────────────────────────────────────┐
 │       PLACE 1: BACKEND SERVER          │       │       PLACE 2: FRONTEND ON VERCEL      │
 │  (Inside EC2 Instance 2)               │       │  (Vercel Web Dashboard)                │
 ├────────────────────────────────────────┤       ├────────────────────────────────────────┤
 │ Location: A file named `.env`          │       │ Location: vercel.com Web Console       │
 │ Path: `/opt/leetcode-backend/.env`     │       │ Path: Project Settings > Env Variables │
 │ How: Created via terminal command:     │       │ How: Click "Add Environment Variable"  │
 │      `nano /opt/leetcode-backend/.env` │       │      Paste Key & Value into form       │
 └────────────────────────────────────────┘       └────────────────────────────────────────┘
```

---

### Detailed Breakdown of PLACE 1: Backend Server `.env` File

When you log in to your **Backend EC2 Instance**, you will create a text file named `.env` in the project root:
```bash
nano /opt/leetcode-backend/.env
```
Inside that file, paste the template below, replacing the `<PLACEHOLDERS>` with your actual AWS values:

```ini
# ==============================================================================
# 1. APPLICATION ENVIRONMENT
# ==============================================================================
ENVIRONMENT=production
DEBUG=False

# ==============================================================================
# 2. MANAGED POSTGRESQL DATABASE (From AWS RDS Console)
# ==============================================================================
# Format: postgresql+asyncpg://<username>:<password>@<rds-endpoint>:5432/<dbname>
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT.rds.amazonaws.com:5432/leetcode_clone
SYNC_DATABASE_URL=postgresql://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT.rds.amazonaws.com:5432/leetcode_clone

# ==============================================================================
# 3. REDIS & CELERY (Runs locally on this same EC2 instance)
# ==============================================================================
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ==============================================================================
# 4. AWS S3 STORAGE (Authenticates automatically via EC2 IAM Role)
# ==============================================================================
MOCK_S3=False
AWS_REGION=ap-south-2
S3_BUCKET_NAME=YOUR_UNIQUE_S3_BUCKET_NAME

# ==============================================================================
# 5. AWS COGNITO AUTHENTICATION (From AWS Cognito Console)
# ==============================================================================
MOCK_COGNITO=False
COGNITO_USER_POOL_ID=ap-south-2_xxxxxxxxx
COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_ISSUER=https://cognito-idp.ap-south-2.amazonaws.com/ap-south-2_xxxxxxxxx

# ==============================================================================
# 6. DEDICATED JUDGE0 CODE EXECUTION (From EC2 Instance 1 Private IP)
# ==============================================================================
MOCK_JUDGE0=False
# Must use the PRIVATE IP of EC2 Instance 1 so traffic stays inside AWS VPC
JUDGE0_URL=http://YOUR_JUDGE0_PRIVATE_IP:2358
JUDGE0_CALLBACK_URL=http://YOUR_API_ELASTIC_IP:8000/api/v1/internal/judge0-callback
JUDGE0_CPU_TIME_LIMIT=2.0
JUDGE0_MEMORY_LIMIT=128000
JUDGE0_POLL_TIMEOUT_SECONDS=15.0
JUDGE0_AUTH_TOKEN=
JUDGE0_API_KEY=

# ==============================================================================
# 7. SECURITY & CORS (Allows Vercel to communicate with this API)
# ==============================================================================
ALLOWED_ORIGINS=https://*.vercel.app,http://localhost:5173
```

---

### Detailed Breakdown of PLACE 2: Frontend Environment Variables on Vercel

When you deploy the React frontend on **Vercel**, you do **not** upload a `.env` file.  
Instead, you configure them in the Vercel web UI:

1. Open [vercel.com](https://vercel.com) and go to your **Project**.
2. Click **Settings** (top navigation bar) > click **Environment Variables** (left sidebar).
3. Add the following **4 key-value pairs**:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `http://54.210.15.20` *(or `https://api.yourdomain.com`)* | Public IP or domain of your Backend EC2 instance |
| `VITE_COGNITO_USER_POOL_ID` | `ap-south-2_AbCdEf123` | Your AWS Cognito User Pool ID |
| `VITE_COGNITO_CLIENT_ID` | `3nki6b5...` | Your AWS Cognito App Client ID |
| `VITE_AWS_REGION` | `ap-south-2` | AWS region where you created Cognito |

---

## 2. Full Architecture Blueprint

```
                      [ User Browser (React / Monaco Editor) ]
                                         │
                                         ▼
                      [ Vercel Edge Global CDN (Frontend) ]
                                         │
                                         │ HTTPS REST Requests
                                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ AWS VPC (Virtual Private Cloud)                                          │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ EC2 Instance 2: Backend API & Worker (Ubuntu 24.04, t3.micro)    │   │
│  │   • Public Elastic IP: 54.x.x.x (Internet facing)                │   │
│  │   • Caddy: Reverse proxy (Handles Port 80 / Port 443 SSL)        │   │
│  │   • FastAPI + Uvicorn: Application server (Port 8000)            │   │
│  │   • Celery Worker: Background task processor                     │   │
│  │   • Local Redis: High-speed cache & queue (Port 6379, Free!)     │   │
│  │   • Attached IAM Role: S3 Read/Write (Zero static credentials!)  │   │
│  └──────────────────┬───────────────────────────────┬───────────────┘   │
│                     │                               │                   │
│      Port 2358      │                               │ Port 5432         │
│      (VPC Internal) │                               │ (VPC Internal)    │
│                     ▼                               ▼                   │
│  ┌───────────────────────────────────┐    ┌──────────────────────────┐  │
│  │ EC2 Instance 1: Dedicated Judge0  │    │ AWS RDS PostgreSQL       │  │
│  │ (Ubuntu 24.04, t3.small)          │    │ (db.t3.micro, Free Tier) │  │
│  │   • Private IP: 172.31.x.x        │    │   • Private & Encrypted  │  │
│  │   • Isolated Docker Sandboxes     │    │   • Automatic Backups    │  │
│  │   • Compilers: Python, C++, Java  │    │   • Auto-scaling Storage │  │
│  └───────────────────────────────────┘    └──────────────────────────┘  │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
[ AWS Cognito User Pool ]                         [ AWS S3 Private Bucket ]
  • User sign-up & OTP verification                 • Problem test cases & driver code
  • Cryptographic RS256 JWT tokens                  • User avatars
  • Free for first 50,000 active users              • Free tier storage (< 5 GB)
```

---

## 3. Step-by-Step Deployment Instructions

### Phase 1: Security Groups & IAM Role (5 Minutes)

#### Step 1.1: Create Security Groups
Open the [AWS EC2 Security Groups Console](https://console.aws.amazon.com/ec2/v2/home#SecurityGroups:) and create three security groups in your default VPC:

1. **`sg_api`** (Backend Server):
   * **Inbound Rules**:
     * `HTTP (80)` from `0.0.0.0/0`
     * `HTTPS (443)` from `0.0.0.0/0`
     * `SSH (22)` from `My IP`
   * **Outbound Rules**: Leave as All traffic (`0.0.0.0/0`)

2. **`sg_judge0`** (Judge0 Code Execution):
   * **Inbound Rules**:
     * `Custom TCP (2358)` from **Security Group `sg_api`** *(Crucial: This ensures Judge0 is never exposed to the public internet)*
     * `SSH (22)` from `My IP`
   * **Outbound Rules**: All traffic (`0.0.0.0/0`)

3. **`sg_rds`** (PostgreSQL Database):
   * **Inbound Rules**:
     * `PostgreSQL (5432)` from **Security Group `sg_api`**
   * **Outbound Rules**: All traffic (`0.0.0.0/0`)

#### Step 1.2: Create IAM Role for S3
Open the [AWS IAM Console](https://console.aws.amazon.com/iam/home#/roles) > **Create role**:
1. Select **AWS Service** > **EC2** > click **Next**.
2. Click **Create inline policy** > select the **JSON** tab > paste:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:PutObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": ["arn:aws:s3:::*"]
       }
     ]
   }
   ```
3. Click **Next** > name the role **`leetcode-ec2-s3-role`** > click **Create role**.

---

### Phase 2: S3 Bucket & RDS Database (5 Minutes)

#### Step 2.1: Create Amazon S3 Bucket
1. Open the [AWS S3 Console](https://console.aws.amazon.com/s3/) > click **Create bucket**.
2. **Bucket name**: e.g., `leetcode-storage-yourname` (must be unique).
3. **Region**: `ap-south-2` (keep all services in the same region).
4. Leave **Block all public access** checked (ON).
5. Under the **Permissions** tab > **Cross-origin resource sharing (CORS)**, paste:
   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET", "PUT"],
       "AllowedOrigins": ["*"],
       "ExposeHeaders": ["ETag"]
     }
   ]
   ```
6. Click **Save changes**.

#### Step 2.2: Create RDS PostgreSQL Database
1. Open the [AWS RDS Console](https://console.aws.amazon.com/rds/) > click **Create database**.
2. **Method**: Standard create > Engine: **PostgreSQL**.
3. **Template**: Select **Free Tier**.
4. **Settings**:
   * DB identifier: `leetcode-db`
   * Master username: `postgres`
   * Master password: Choose a password (e.g. `MySecurePass2026!`) and note it down!
5. **Instance configuration**: `db.t3.micro`. Storage: `20 GB gp3`.
6. **Connectivity**:
   * Public access: **No**.
   * VPC security group: Select **`sg_rds`**.
7. **Additional configuration**:
   * Initial database name: `leetcode_clone`.
8. Click **Create database**. Wait ~5 minutes until the status is **Available**.
9. Copy the **Endpoint** URL (e.g., `leetcode-db.c12345.ap-south-2.rds.amazonaws.com`).

---

### Phase 3: Launch EC2 Instance 1 (Dedicated Judge0) (10 Minutes)

1. Open the [AWS EC2 Console](https://console.aws.amazon.com/ec2/) > **Launch instance**:
   * Name: `leetcode-judge0`
   * OS: **Ubuntu 24.04 LTS (64-bit x86)**
   * Instance type: **`t3.small`** (requires ~2GB RAM for compilers)
   * Key pair: Create or choose an existing `.pem` key
   * Network settings: Select existing security group **`sg_judge0`**
   * Storage: `30 GB gp3`
   * Click **Launch instance**.
2. Connect to the instance via SSH in PowerShell/Terminal:
   ```bash
   ssh -i your-key.pem ubuntu@<JUDGE0-PUBLIC-IP>
   ```
3. Install Docker:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
   sudo usermod -aG docker ubuntu
   exit
   ```
4. Re-connect and start Judge0:
   ```bash
   ssh -i your-key.pem ubuntu@<JUDGE0-PUBLIC-IP>
   git clone https://github.com/judge0/judge0.git
   cd judge0
   cp judge0.conf.example judge0.conf
   docker compose up -d
   ```
5. Test Judge0 health:
   ```bash
   curl -s http://localhost:2358/health
   # Expected output: {"status":"ready"}
   ```
6. In the AWS EC2 Console, copy the **Private IP** of this instance (e.g., `172.31.25.100`).

---

### Phase 4: Launch EC2 Instance 2 (FastAPI Backend, Redis, Worker & Caddy) (15 Minutes)

#### Step 4.1: Launch Instance & Allocate Elastic IP
1. Open the [AWS EC2 Console](https://console.aws.amazon.com/ec2/) > **Launch instance**:
   * Name: `leetcode-backend-api`
   * OS: **Ubuntu 24.04 LTS**
   * Instance type: **`t3.micro`** (Free Tier)
   * Key pair: Select your `.pem` key
   * Security group: Select **`sg_api`**
   * **Advanced details** > **IAM instance profile**: Select **`leetcode-ec2-s3-role`**
   * Click **Launch instance**.
2. Allocate an Elastic IP:
   * EC2 Menu > **Elastic IPs** > **Allocate Elastic IP**.
   * Select it > **Actions** > **Associate Elastic IP** > Choose `leetcode-backend-api`.

#### Step 4.2: Install Software & Clone Repository
1. Connect via SSH:
   ```bash
   ssh -i your-key.pem ubuntu@<YOUR-ELASTIC-IP>
   ```
2. Install system packages, Redis, and Caddy:
   ```bash
   sudo apt-get update && sudo apt-get install -y python3-pip python3-venv git redis-server caddy
   ```
3. Clone repository and install Python requirements:
   ```bash
   git clone https://github.com/RishiJhaver/barn-burner.git /opt/leetcode-backend
   cd /opt/leetcode-backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

#### Step 4.3: Create `.env` Configuration File
Create your `.env` file:
```bash
nano /opt/leetcode-backend/.env
```
Paste your real values:
```ini
ENVIRONMENT=production
DEBUG=False

# Database (From Phase 2)
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/leetcode_clone
SYNC_DATABASE_URL=postgresql://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/leetcode_clone

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# AWS Cognito (Configured in Phase 5)
MOCK_COGNITO=False
AWS_REGION=ap-south-2
COGNITO_USER_POOL_ID=YOUR_COGNITO_POOL_ID
COGNITO_APP_CLIENT_ID=YOUR_COGNITO_CLIENT_ID
COGNITO_ISSUER=https://cognito-idp.ap-south-2.amazonaws.com/YOUR_COGNITO_POOL_ID

# AWS S3 Storage
MOCK_S3=False
S3_BUCKET_NAME=YOUR_S3_BUCKET_NAME

# Judge0 Sandbox (Private IP from Phase 3)
MOCK_JUDGE0=False
JUDGE0_URL=http://YOUR_JUDGE0_PRIVATE_IP:2358
JUDGE0_CALLBACK_URL=http://YOUR_ELASTIC_IP:8000/api/v1/internal/judge0-callback
JUDGE0_CPU_TIME_LIMIT=2.0
JUDGE0_MEMORY_LIMIT=128000

# Security & CORS
ALLOWED_ORIGINS=https://*.vercel.app,http://localhost:5173
```
Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit.

#### Step 4.4: Run Database Migrations & Problem Seeding
```bash
cd /opt/leetcode-backend
source .venv/bin/activate
alembic upgrade head
python seed_problems.py
```

#### Step 4.5: Configure System Daemons (Systemd)
1. Create the FastAPI service:
   ```bash
   sudo nano /etc/systemd/system/leetcode-api.service
   ```
   Paste:
   ```ini
   [Unit]
   Description=LeetCode FastAPI Backend
   After=network.target redis-server.service

   [Service]
   User=ubuntu
   WorkingDirectory=/opt/leetcode-backend
   ExecStart=/opt/leetcode-backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
2. Create the Celery Worker service:
   ```bash
   sudo nano /etc/systemd/system/leetcode-worker.service
   ```
   Paste:
   ```ini
   [Unit]
   Description=LeetCode Celery Background Worker
   After=network.target redis-server.service

   [Service]
   User=ubuntu
   WorkingDirectory=/opt/leetcode-backend
   ExecStart=/opt/leetcode-backend/.venv/bin/celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
3. Enable and start both services:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now leetcode-api leetcode-worker
   sudo systemctl status leetcode-api
   ```

#### Step 4.6: Configure Reverse Proxy (Caddy)
```bash
sudo nano /etc/caddy/Caddyfile
```
Paste:
```caddy
:80 {
    reverse_proxy 127.0.0.1:8000
}
```
Reload Caddy:
```bash
sudo systemctl reload caddy
```
*Test by visiting `http://<YOUR-ELASTIC-IP>/docs` in your browser. You will see Swagger UI!*

---

### Phase 5: AWS Cognito Setup (5 Minutes)

1. Open the [AWS Cognito Console](https://console.aws.amazon.com/cognito/) > **Create user pool**.
2. **Sign-in options**: Check **Email**. Click **Next**.
3. **Password policy**: Select **No MFA**. Click **Next**.
4. **Sign-up experience**: Keep **Self-registration** enabled. Check **email** as required attribute. Click **Next**.
5. **Configure message delivery**: Select **Send email with Cognito**. Click **Next**.
6. **App integration**:
   * User pool name: `leetcode-users`
   * App client name: `leetcode-web-client`
   * Client secret: Select **Don't generate a client secret** *(essential for React single-page apps)*.
7. Click **Create user pool**.
8. Copy the **User Pool ID** and **App Client ID**.
9. Update them in `/opt/leetcode-backend/.env` on your EC2 instance and restart the backend:
   ```bash
   sudo systemctl restart leetcode-api
   ```

---

### Phase 6: Frontend Deployment on Vercel (3 Minutes)

1. Go to [vercel.com](https://vercel.com) and log in with your GitHub account.
2. Click **Add New** > **Project** > Import `barn-burner`.
3. In the project configuration:
   * **Root Directory**: Click edit and select `frontend`.
   * **Framework Preset**: Vite (detected automatically).
   * **Environment Variables**: Add these 4:
     * `VITE_API_URL` = `http://<YOUR-ELASTIC-IP>` *(or your custom HTTPS domain)*
     * `VITE_COGNITO_USER_POOL_ID` = `ap-south-2_xxxxxxxxx`
     * `VITE_COGNITO_CLIENT_ID` = `xxxxxxxxxxxxxxxxxx`
     * `VITE_AWS_REGION` = `ap-south-2`
4. Click **Deploy**. Vercel will build and provide your live URL (e.g. `https://barn-burner.vercel.app`).

---

## 4. Verification & Health Checklist

* [ ] **API Health Probe**: Visit `http://<YOUR-ELASTIC-IP>/health` (Returns `{"status": "healthy"}`).
* [ ] **API Docs**: Visit `http://<YOUR-ELASTIC-IP>/docs` (Interactive Swagger UI loads).
* [ ] **User Registration**: Register an account on your live Vercel frontend and verify via email OTP.
* [ ] **Run Code**: Open a problem and click **Run Code** (Executes sample test cases via Judge0).
* [ ] **Custom Input**: Click **+ Custom Input**, enter custom data, and click **Run Code**.
* [ ] **Official Submit**: Click **Submit Solution** (Evaluates against full hidden test suite, displays verdict & confetti).

---

## 5. Helpful Commands & Maintenance

```bash
# View live API logs
sudo journalctl -u leetcode-api -f

# View live Celery worker logs
sudo journalctl -u leetcode-worker -f

# Restart services after updating .env
sudo systemctl restart leetcode-api leetcode-worker

# Pull latest code from GitHub on EC2
cd /opt/leetcode-backend
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart leetcode-api leetcode-worker
```
