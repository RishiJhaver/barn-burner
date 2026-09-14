# LeetCode Clone — Master Cloud Deployment Guide

An end-to-end, production-ready deployment guide for the LeetCode Clone platform. Optimized for **maximum security**, **zero static credentials on servers (IAM Instance Profiles)**, **free-tier cost efficiency ($0 to ~$14/month)**, and **high-performance code execution**.

---

## 1. High-Level System Architecture

```
                          [ Users & Browsers ]
                                   │
                  ┌────────────────┴────────────────┐
                  ▼                                 ▼
         [ Frontend on Vercel ]            [ Route 53 / DNS ]
         (React 18 + Vite CDN)             (api.yourdomain.com)
                  │                                 │
                  │ HTTPS REST API                  │
                  ▼                                 ▼
   ┌─────────────────────────────────────────────────────────────┐
   │ AWS VPC (10.0.0.0/16)                                       │
   │                                                             │
   │  ┌───────────────────────────────────────────────────────┐  │
   │  │ Public Subnet (Elastic IP: 54.x.x.x)                  │  │
   │  │                                                       │  │
   │  │   [ EC2: API + Celery + Redis ] (t3.micro / t4g.small)│  │
   │  │     - Reverse Proxy: Caddy (Automatic HTTPS / SSL)    │  │
   │  │     - Web API: FastAPI + Uvicorn (Port 8000)          │  │
   │  │     - Worker: Celery Worker (Evaluation Pipeline)     │  │
   │  │     - Cache: Local Redis 7 (localhost:6379, Free!)    │  │
   │  │     - Attached IAM Role: S3 Read/Write (Zero Keys!)   │  │
   │  └───────────────────┬───────────────────┬───────────────┘  │
   │                      │                   │                  │
   │     Port 2358 (Internal Only)            │ Port 5432 (Internal)
   │                      ▼                   ▼                  │
   │  ┌─────────────────────────┐  ┌──────────────────────────┐  │
   │  │ EC2: Judge0 Sandbox     │  │ AWS RDS PostgreSQL       │  │
   │  │ (t3.small, Ubuntu)      │  │ (db.t3.micro, Free Tier) │  │
   │  │ - Dockerized Judge0     │  │ - Isolated in Private SG │  │
   │  │ - Sandboxed Workers     │  │ - 100% Parameterized DB  │  │
   │  └─────────────────────────┘  └──────────────────────────┘  │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
[ AWS Cognito User Pool ]                     [ AWS S3 Bucket ]
  - Managed User Auth & JWT                     - 100% of Test Cases
  - Google OAuth / Social Login                 - User Avatars
  - 50,000 Monthly Active Users Free            - Direct Presigned Uploads
```

---

## 2. Infrastructure Inventory & Monthly Cost Breakdown

| Resource | Service / Sizing | Monthly Cost |
| :--- | :--- | :--- |
| **API, Celery & Redis** | AWS EC2 `t3.micro` or `t4g.small` (Ubuntu 24.04) | **$0.00** (Free Tier eligible) |
| **Code Runner Sandbox** | AWS EC2 `t3.small` (Dedicated for Judge0) | **~$14.00/mo** (Can stop when not testing) |
| **Database** | AWS RDS PostgreSQL (`db.t3.micro`, 20 GB gp3) | **$0.00** (Free Tier eligible) |
| **Cache & Message Broker** | Local `redis-server` on EC2 API instance | **$0.00** (Eliminated expensive ElastiCache) |
| **Storage (Test Cases & Avatars)** | AWS S3 Standard (Private Bucket) | **$0.00** (< 5 GB Free Tier) |
| **Authentication** | AWS Cognito User Pool | **$0.00** (First 50,000 MAU free) |
| **Frontend CDN & Edge** | Vercel (Hobby Tier) | **$0.00** |
| **SSL / TLS Certificates** | Let's Encrypt via Caddy Server | **$0.00** (Automatic renewal) |
| **Total Estimated Cost** | | **~$0 – $14 / month** |

---

## Phase 1: AWS VPC, Security Groups & IAM Role

### 1. Configure Security Groups
In the AWS EC2 Console, create three Security Groups in your VPC:

1. **`sg_api` (FastAPI Server)**:
   - **Inbound**:
     - `HTTP (80)` from `0.0.0.0/0`
     - `HTTPS (443)` from `0.0.0.0/0`
     - `SSH (22)` from **Your IP only**
   - **Outbound**: All traffic (`0.0.0.0/0`)

2. **`sg_judge0` (Code Execution Engine)**:
   - **Inbound**:
     - `Custom TCP (2358)` from **Security Group `sg_api` ONLY** *(never expose Judge0 to the public internet)*
     - `SSH (22)` from **Your IP only**
   - **Outbound**: All traffic

3. **`sg_rds` (PostgreSQL Database)**:
   - **Inbound**:
     - `PostgreSQL (5432)` from **Security Group `sg_api` ONLY**
   - **Outbound**: All traffic

---

### 2. IAM Instance Profile (`leetcode-ec2-s3-role`)
*Attaching this role allows the FastAPI server to access S3 directly via instance metadata without saving any static AWS Access Keys or Secret Keys in `.env` files.*

1. Go to **AWS IAM Console** > **Roles** > **Create Role**.
2. Select **AWS Service** > **EC2**.
3. Attach an inline policy named `LeetCodeS3Access`:
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
      "Resource": [
        "arn:aws:s3:::leetcode-clone-storage-*",
        "arn:aws:s3:::leetcode-clone-storage-*/*"
      ]
    }
  ]
}
```
4. Name the role **`leetcode-ec2-s3-role`**.

---

## Phase 2: Storage & Database Setup (S3 & RDS)

### 1. Amazon S3 Bucket
1. Open **Amazon S3** > **Create bucket**.
2. Name: `leetcode-clone-storage-<your-account-id>` (must be globally unique).
3. Region: Select your primary region (e.g. `us-east-1`).
4. **Block Public Access**: Keep **Checked (ON)** — all files are served via IAM or short-lived Presigned URLs.
5. In the **Permissions** tab, add the **CORS configuration**:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT", "GET"],
    "AllowedOrigins": [
      "https://*.vercel.app",
      "http://localhost:5173",
      "https://yourdomain.com"
    ],
    "ExposeHeaders": ["ETag"]
  }
]
```

### 2. AWS RDS PostgreSQL Database
1. Go to **Amazon RDS** > **Create database**.
2. Choose **Standard create** > **PostgreSQL** (Version 16 or 15).
3. Template: **Free Tier**.
4. Settings:
   - DB instance identifier: `leetcode-db`
   - Master username: `postgres`
   - Master password: `YourStrongPassword123!`
5. Instance configuration: `db.t3.micro`.
6. Storage: `20 GB gp3` (Enable storage autoscaling up to 50 GB).
7. Connectivity:
   - Virtual Private Cloud (VPC): Same VPC as EC2.
   - Public access: **No** (Database stays strictly internal).
   - VPC Security Group: Select **`sg_rds`**.
8. Initial Database Name (under Additional Configuration): `leetcode_clone`.
9. Click **Create database**.
10. Note down the **Endpoint** (e.g., `leetcode-db.xxxx.us-east-1.rds.amazonaws.com`).

---

## Phase 3: Judge0 Sandbox Setup (EC2)

1. **Launch EC2 Instance**:
   - AMI: **Ubuntu Server 24.04 LTS** (64-bit x86).
   - Instance Type: **`t3.small`** (Judge0 requires ~2 GB RAM for sandboxed compilers).
   - Storage: **30 GB gp3**.
   - Security Group: **`sg_judge0`**.
   - Name tag: `leetcode-judge0`.

2. **SSH into the instance**:
   ```bash
   ssh -i your-key.pem ubuntu@<judge0-public-ip>
   ```

3. **Install Docker and Docker Compose**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y ca-certificates curl gnupg
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   sudo chmod a+r /etc/apt/keyrings/docker.gpg
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt-get update
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   sudo usermod -aG docker ubuntu
   ```

4. **Start Judge0**:
   ```bash
   # Log out and log back in for docker group permissions to take effect
   exit
   ssh -i your-key.pem ubuntu@<judge0-public-ip>

   git clone https://github.com/judge0/judge0.git /home/ubuntu/judge0
   cd /home/ubuntu/judge0
   cp judge0.conf.example judge0.conf
   docker compose up -d
   ```

5. **Verify Judge0 Health**:
   ```bash
   curl -s http://localhost:2358/health | grep -o '"status":"ready"'
   ```
   *Note down the **Private IP** of this EC2 instance (e.g., `10.0.1.45`).*

---

## Phase 4: Backend API, Celery & Local Redis (EC2)

1. **Launch EC2 Instance**:
   - AMI: **Ubuntu Server 24.04 LTS**.
   - Instance Type: **`t3.micro`** (Free Tier) or **`t4g.small`**.
   - IAM Role: Attach **`leetcode-ec2-s3-role`**.
   - Security Group: **`sg_api`**.
   - Name tag: `leetcode-backend-api`.

2. **Allocate & Associate an Elastic IP** (Static Public IP) to this instance.

3. **SSH into the instance**:
   ```bash
   ssh -i your-key.pem ubuntu@<api-elastic-ip>
   ```

4. **Install System Packages, Caddy, and Local Redis**:
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   sudo apt-get install -y python3-pip python3-venv git redis-server debian-keyring debian-archive-keyring apt-transport-https curl

   # Install Caddy (automatic SSL reverse proxy)
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt-get update
   sudo apt-get install -y caddy

   # Enable and verify local Redis
   sudo systemctl enable --now redis-server
   redis-cli ping  # Returns PONG
   ```

5. **Deploy Codebase from GitHub**:
   ```bash
   sudo mkdir -p /opt/leetcode-backend
   sudo chown -R ubuntu:ubuntu /opt/leetcode-backend
   git clone https://github.com/RishiJhaver/barn-burner.git /opt/leetcode-backend
   cd /opt/leetcode-backend

   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. **Create Production `.env` File**:
   ```bash
   nano /opt/leetcode-backend/.env
   ```
   Paste the following configuration (replace placeholders):
   ```env
   ENVIRONMENT=production
   DEBUG=False

   # AWS RDS Database Connection
   DATABASE_URL=postgresql+asyncpg://postgres:YourStrongPassword123!@<rds-endpoint>:5432/leetcode_clone
   SYNC_DATABASE_URL=postgresql://postgres:YourStrongPassword123!@<rds-endpoint>:5432/leetcode_clone

   # Local High-Speed Redis (Cache & Celery Queue)
   REDIS_URL=redis://127.0.0.1:6379/0
   CELERY_BROKER_URL=redis://127.0.0.1:6379/1
   CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/2

   # AWS S3 Storage (Authenticates automatically via IAM Role)
   S3_BUCKET_NAME=leetcode-clone-storage-<your-account-id>
   AWS_REGION=us-east-1
   MOCK_S3=False

   # AWS Cognito (Configured in Phase 5)
   MOCK_COGNITO=False
   COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
   COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
   COGNITO_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxxxxxx

   # Judge0 Private Instance Connection
   MOCK_JUDGE0=False
   JUDGE0_URL=http://<judge0-private-ip>:2358
   JUDGE0_CPU_TIME_LIMIT=2.0
   JUDGE0_MEMORY_LIMIT=128000

   # Security & CORS
   ALLOWED_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
   ```

7. **Run Migrations & Seed Initial Problems**:
   ```bash
   cd /opt/leetcode-backend
   source .venv/bin/activate
   alembic upgrade head
   python seed_problems.py
   ```

8. **Configure Systemd Daemons**:
   - **FastAPI API Service** (`/etc/systemd/system/leetcode-api.service`):
     ```bash
     sudo nano /etc/systemd/system/leetcode-api.service
     ```
     ```ini
     [Unit]
     Description=LeetCode Clone FastAPI Application
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

   - **Celery Background Worker Service** (`/etc/systemd/system/leetcode-worker.service`):
     ```bash
     sudo nano /etc/systemd/system/leetcode-worker.service
     ```
     ```ini
     [Unit]
     Description=LeetCode Clone Celery Background Worker
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

   - **Start & Enable Services**:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl enable --now leetcode-api
     sudo systemctl enable --now leetcode-worker
     sudo systemctl status leetcode-api
     sudo systemctl status leetcode-worker
     ```

9. **Configure Caddy Reverse Proxy (Automatic HTTPS / SSL)**:
   ```bash
   sudo nano /etc/caddy/Caddyfile
   ```
   ```caddy
   # If using a custom domain with automatic Let's Encrypt SSL:
   api.yourdomain.com {
       reverse_proxy 127.0.0.1:8000
   }

   # Or if testing initially with your Elastic IP over HTTP:
   :80 {
       reverse_proxy 127.0.0.1:8000
   }
   ```
   ```bash
   sudo systemctl restart caddy
   ```

---

## Phase 5: AWS Cognito Configuration

1. Open **Amazon Cognito** > **Create User Pool**.
2. **Authentication providers**: Choose **User name / Email**.
3. **Password policy**: Standard (min 8 chars, lowercase, numbers, symbols).
4. **User pool name**: `leetcode-users`.
5. **App Client Configuration**:
   - App type: **Public client (Single-page application)**.
   - App client name: `leetcode-web-client`.
   - Client secret: **Don't generate a client secret** (SPAs must not use client secrets).
6. Under **App integration** > **Hosted UI**:
   - Domain: Create a Cognito domain prefix (e.g. `auth-leetcode-<unique-id>.auth.us-east-1.amazoncognito.com`).
   - Allowed callback URLs: `https://your-frontend.vercel.app/`
   - Allowed sign-out URLs: `https://your-frontend.vercel.app/`
   - Identity Providers: Check **Cognito user pool** (and optionally **Google**).
7. Copy the **User Pool ID** and **App Client ID** into `/opt/leetcode-backend/.env`.
8. Restart the API service:
   ```bash
   sudo systemctl restart leetcode-api
   ```

---

## Phase 6: Frontend Deployment (Vercel)

1. Go to [Vercel.com](https://vercel.com) and click **Add New** > **Project**.
2. Import your GitHub repository: `RishiJhaver/barn-burner`.
3. Configure Project Settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click Edit and select **`frontend`**
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Configure **Environment Variables**:
   | Key | Value |
   | :--- | :--- |
   | `VITE_API_URL` | `https://api.yourdomain.com` (or `http://<elastic-ip>` for testing) |
   | `VITE_COGNITO_USER_POOL_ID` | Your Cognito User Pool ID |
   | `VITE_COGNITO_CLIENT_ID` | Your Cognito App Client ID |
5. Click **Deploy**.
6. Once deployed, copy your production Vercel URL (e.g. `https://barn-burner.vercel.app`).
7. Add this URL to `ALLOWED_ORIGINS` in your EC2 `.env` file and restart Caddy/FastAPI:
   ```bash
   sudo systemctl restart leetcode-api
   ```

---

## Phase 7: Production Verification Checklist

Run these smoke tests once all services are deployed:

- [ ] **API Health Check**:
  ```bash
  curl https://api.yourdomain.com/health
  # Expected: {"status":"healthy","environment":"production","mock_cognito":false}
  ```
- [ ] **Swagger Documentation**: Open `https://api.yourdomain.com/docs` in your browser.
- [ ] **Frontend Loading**: Open your Vercel URL. Confirm problem catalog loads from PostgreSQL.
- [ ] **DevTools Security Check**: Open DevTools > Network tab on problem detail: verify `cognito_sub` and `driver_code` are **not** present.
- [ ] **Run Code Test**: Select a problem, enter a solution, and click **Run Code** (verifies live Judge0 execution).
- [ ] **Submit Code Test**: Click **Submit Code** (verifies Celery worker async execution against full hidden test suite).
- [ ] **User Registration & Login**: Test user registration with email confirmation code or 1-Click Demo.

---

## Phase 8: CloudWatch Cost Safeguard

To guarantee zero surprise charges:
1. Go to **AWS CloudWatch** > **Alarms** > **Create Alarm**.
2. Select metric: **Billing** > **EstimatedCharges**.
3. Set threshold: **Greater than $5.00 USD**.
4. Configure an SNS topic to notify your email address immediately.
