# LeetCode Clone — Cloud Deployment Architecture & Plan

This document outlines the end-to-end production cloud deployment strategy for the LeetCode Clone application, designed for **high security**, **low cost (free-tier optimized)**, and **scalable execution**.

---

## 1. High-Level Architecture Diagram

```
                              [ Users / Browsers ]
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         [ Frontend Hosting ]                  [ Custom Domain / DNS ]
         (Vercel or S3 + CloudFront)                 (Route 53)
                      │                                 │
                      │ HTTPS API Calls                 │
                      ▼                                 ▼
       ┌──────────────────────────────────────────────────────────────────┐
       │ AWS VPC (e.g. 10.0.0.0/16)                                       │
       │                                                                  │
       │  ┌────────────────────────────────────────────────────────────┐  │
       │  │ Public Subnet (10.0.1.0/24)                                │  │
       │  │                                                            │  │
       │  │   [ FastAPI Backend & Services (EC2 t3.micro/small) ]      │  │
       │  │     - Reverse Proxy: Caddy / Nginx (Auto-SSL via Let's Enc) │  │
       │  │     - Web Server: Uvicorn / Gunicorn (systemd)             │  │
       │  │     - Background Tasks: Celery Worker (systemd)            │  │
       │  │     - Cache & Queue: Local Redis 7 (localhost:6379)        │  │
       │  │     - IAM Role Attached: S3 Read/Write (Zero static keys!) │  │
       │  │     - Security Group: Ports 80, 443 (Public), 22 (SSH)     │  │
       │  └───────────────────┬──────────────────────┬─────────────────┘  │
       │                      │                      │                    │
       │                      │ Inbound 2358 only    │                    │
       │                      ▼                      │                    │
       │  ┌──────────────────────────────────────┐   │                    │
       │  │ Protected Subnet (10.0.2.0/24)       │   │                    │
       │  │                                      │   │                    │
       │  │   [ Judge0 Sandbox Engine (EC2) ]    │   │                    │
       │  │     - Dockerized Judge0 + Isolated   │   │                    │
       │  │       Worker Sandboxes               │   │                    │
       │  │     - SG: Port 2358 FROM API SG ONLY │   │                    │
       │  └──────────────────────────────────────┘   │                    │
       │                                             │                    │
       │  ┌──────────────────────────────────────────┴─────────────────┐  │
       │  │ Private Subnet (Isolated, No Public IP)                    │  │
       │  │                                                            │  │
       │  │   [ AWS RDS PostgreSQL ]                                   │  │
       │  │     - db.t3.micro (Free Tier eligible)                     │  │
       │  │     - Single-AZ (Dev/Staging)                              │  │
       │  │     - Port 5432 (Inbound ONLY from API SG)                 │  │
       │  └────────────────────────────────────────────────────────────┘  │
       └──────────────────────────────┬───────────────────────────────────┘
                                      │
              ┌───────────────────────┴────────────────────────┐
              ▼                                                ▼
[ AWS Cognito User Pool ]                         [ AWS S3 Object Storage ]
  - Managed User Auth                               - User Profile Avatars (`/avatars/...`)
  - 50,000 MAU Free Tier                            - All Test Cases (`/testcases/{id}/...`)
                                                    - Presigned Uploads & IAM Instance Profile
```

---

## 2. Infrastructure Inventory & Cost Strategy

| Component | AWS Resource / Service | Sizing / Plan | Estimated Monthly Cost |
| :--- | :--- | :--- | :--- |
| **API, Celery & Redis** | EC2 Instance | `t3.micro` or `t4g.small` (Ubuntu 24.04) | Free Tier eligible ($0 - $7/mo) |
| **Code Runner** | EC2 Instance | `t3.small` (dedicated for Judge0 sandboxes) | ~$14/mo (Can stop when not testing) |
| **Database** | AWS RDS PostgreSQL | `db.t3.micro`, 20 GB gp3 storage | Free Tier eligible ($0 - $13/mo) |
| **Cache & Queue** | Local Redis on EC2 | `redis-server` (systemd, bound to `127.0.0.1`) | **$0.00** (Eliminated ElastiCache fee!) |
| **Media & All Test Cases**| AWS S3 Standard | 5 GB Free Tier (Avatars + 100% of Test Cases) | **$0.00** (~$0.02/GB if exceeding free tier)|
| **Authentication**| AWS Cognito User Pool | 50,000 MAU included free | $0.00 |
| **Frontend** | Vercel or AWS S3 + CloudFront | Global Edge CDN | $0.00 (Hobby / Free Tier) |
| **SSL / TLS** | Let's Encrypt / Caddy | Automatic SSL certificates | $0.00 |
| **Total Est.** | | | **~$14 – $20 / month** (or ~$0 on Free Tier) |

> [!TIP]
> **Zero Database Bloat with S3**: Offloading **all** test cases (inputs and expected outputs) to S3 leaves PostgreSQL exclusively storing metadata (`input_s3_key`, `expected_output_s3_key`). This guarantees lightning-fast DB queries, instant backups, and zero table fragmentation.

---

## 3. Step-by-Step Deployment Plan

### Step 1: Network & Security Foundations (VPC)
1. **Create a VPC**:
   - CIDR block: `10.0.0.0/16`.
   - Create 2 Public Subnets (for API and optional ALB) and 2 Private Subnets (for RDS across 2 availability zones).
   - Attach an **Internet Gateway (IGW)** to the public subnets.
2. **Configure Security Groups**:
   - `sg_api`:
     - Inbound: `80` (HTTP), `443` (HTTPS) from `0.0.0.0/0`, and `22` (SSH) from your IP.
     - Outbound: All traffic (HTTPS to S3, Cognito, package managers).
   - `sg_judge0`:
     - Inbound: `2358` **ONLY from `sg_api`** (never expose Judge0 publicly!).
     - Outbound: All traffic.
   - `sg_rds`:
     - Inbound: `5432` **ONLY from `sg_api`**.
   *(Note: No `sg_redis` needed because Redis runs internally on localhost inside the API instance!)*

---

### Step 2: Managed Database Provisioning (RDS PostgreSQL)
1. **RDS PostgreSQL**:
   - Engine: PostgreSQL 16.
   - Instance Class: `db.t3.micro` (Free Tier).
   - Storage: 20 GB gp3 (Storage autoscaling enabled up to 50 GB).
   - Multi-AZ: Disabled for dev/staging.
   - Subnet Group: Private subnets.
   - Security Group: `sg_rds`.

---

### Step 3: AWS S3 Bucket & IAM Instance Profile (Avatars & All Test Cases)
1. **Create S3 Bucket**:
   - Bucket name: `leetcode-clone-storage-<your-account-id>` (globally unique).
   - Region: Same as your VPC/EC2 (e.g. `us-east-1`).
   - Block Public Access: **Enabled** (private by default; files are accessed via IAM Instance Profile on EC2 or Presigned URLs).
2. **Bucket Directory Layout**:
   ```
   leetcode-clone-storage/
   ├── avatars/
   │   └── {user_id}/avatar.webp
   └── testcases/
       └── {problem_id}/
           ├── {test_case_id}_input.txt
           └── {test_case_id}_expected.txt
   ```
3. **100% S3 Test Case Architecture**:
   - **PostgreSQL role**: Stores only lightweight metadata in the `test_cases` table (`id`, `problem_id`, `is_sample`, `input_s3_key`, `expected_output_s3_key`, `created_at`). No large text blobs in the DB!
   - **Sample test cases for UI**: When displaying problem descriptions, the API fetches the sample test case files from S3 and caches them in Redis.
   - **Execution flow**: The Celery background worker reads test inputs directly from S3 (or worker local cache) and streams them to Judge0 during code evaluation.
4. **IAM Instance Profile (`leetcode-ec2-s3-role`)**:
   - Create an IAM Role for EC2 with an attached inline policy:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "s3:GetObject",
             "s3:PutObject",
             "s3:DeleteObject"
           ],
           "Resource": "arn:aws:s3:::leetcode-clone-storage-*/*"
         }
       ]
     }
     ```
   - Attach this IAM Role to the FastAPI EC2 instance. **No AWS credentials (access key / secret key) need to be written in `.env` or stored on the server!** The AWS SDK (`boto3`) will automatically authenticate using EC2 instance metadata.
5. **CORS Configuration on S3**:
   - Allows the frontend to upload avatars directly using secure presigned URLs:
     ```json
     [
       {
         "AllowedHeaders": ["*"],
         "AllowedMethods": ["PUT", "GET"],
         "AllowedOrigins": ["https://yourdomain.com", "http://localhost:5173"],
         "ExposeHeaders": ["ETag"]
       }
     ]
     ```

---

### Step 4: Judge0 Execution Sandbox (EC2)
1. **Launch EC2 Instance**:
   - Instance: `t3.small` (Ubuntu 24.04).
   - Storage: 30 GB gp3.
   - Security Group: `sg_judge0`.
2. **Install Docker & Judge0**:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
   git clone https://github.com/judge0/judge0.git /opt/judge0
   cd /opt/judge0
   # Configure judge0.conf with internal authentication token and Redis password
   docker compose up -d
   ```
3. **Verify Health**:
   - Test connectivity from the API instance: `curl http://<judge0_private_ip>:2358/health`.

---

### Step 5: Backend API & Celery Worker Deployment (EC2)
1. **Launch EC2 Instance**:
   - Instance: `t3.micro` or `t4g.small` (Ubuntu 24.04).
   - Assign an **Elastic IP** (static public IP) for clean DNS mapping.
   - Attach IAM Role: `leetcode-ec2-s3-role` (created in Step 3).
   - Security Group: `sg_api`.
2. **System Dependencies & Local Redis**:
   ```bash
   sudo apt-get update && sudo apt-get install -y python3-pip python3-venv git caddy redis-server
   sudo systemctl enable --now redis-server
   # Verify Redis is running locally:
   redis-cli ping  # Returns PONG
   ```
3. **Deploy Codebase**:
   ```bash
   git clone <your-repo-url> /opt/leetcode-backend
   cd /opt/leetcode-backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Environment Variables (`.env`)**:
   - Populate RDS endpoint: `DATABASE_URL=postgresql+asyncpg://<user>:<password>@<rds-endpoint>:5432/leetcode_clone`
   - Local Redis endpoints:
     ```env
     REDIS_URL=redis://localhost:6379/0
     CELERY_BROKER_URL=redis://localhost:6379/1
     CELERY_RESULT_BACKEND=redis://localhost:6379/2
     ```
   - Populate S3 Storage Configuration:
     ```env
     S3_BUCKET_NAME=leetcode-clone-storage-<your-account-id>
     S3_REGION=us-east-1
     ```
   - Populate Judge0 endpoint: `JUDGE0_URL=http://<judge0-internal-ip>:2358`
   - Populate AWS Cognito Pool ID & App Client ID.
5. **Run Migrations**:
   ```bash
   alembic upgrade head
   ```
6. **Configure Systemd Daemons**:
   - **FastAPI service** (`/etc/systemd/system/leetcode-api.service`):
     ```ini
     [Unit]
     Description=LeetCode Clone FastAPI
     After=network.target

     [Service]
     User=ubuntu
     WorkingDirectory=/opt/leetcode-backend
     ExecStart=/opt/leetcode-backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
     Restart=always

     [Install]
     WantedBy=multi-user.target
     ```
   - **Celery Worker service** (`/etc/systemd/system/leetcode-worker.service`):
     ```ini
     [Unit]
     Description=LeetCode Clone Celery Worker
     After=network.target

     [Service]
     User=ubuntu
     WorkingDirectory=/opt/leetcode-backend
     ExecStart=/opt/leetcode-backend/.venv/bin/celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
     Restart=always

     [Install]
     WantedBy=multi-user.target
     ```
7. **Configure Reverse Proxy & SSL (Caddy)**:
   - Caddy automatically provisions and renews SSL certificates from Let's Encrypt:
     ```caddy
     api.yourdomain.com {
         reverse_proxy 127.0.0.1:8000
     }
     ```
   - Restart Caddy: `sudo systemctl restart caddy`.

---

### Step 6: AWS Cognito Configuration
1. **User Pool Setup**:
   - Create User Pool `leetcode-users` in the same AWS region.
   - Enable Email sign-in.
2. **App Client Setup**:
   - Create Public Client `leetcode-web-client` (no client secret).
   - Set Allowed Callback URLs: `https://yourdomain.com/auth/callback`.
   - Set Allowed Sign-out URLs: `https://yourdomain.com`.

---

### Step 7: Frontend Deployment (Vercel or S3 + CloudFront)
1. **Option A: Vercel (Recommended for Speed & Global Edge CDN)**:
   - Link your GitHub repository.
   - Set Build Command: `npm run build` or `vite build`.
   - Environment Variables:
     - `VITE_API_URL=https://api.yourdomain.com`
     - `VITE_COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx`
     - `VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx`
2. **Option B: AWS Native (S3 + CloudFront)**:
   - Create S3 bucket for static assets.
   - Create CloudFront distribution with S3 origin.
   - Attach custom domain with ACM SSL certificate (`yourdomain.com`).

---

### Step 8: DNS & CORS Configuration
1. **Route 53 / Domain Registrar**:
   - `yourdomain.com` -> Points to Vercel / CloudFront.
   - `api.yourdomain.com` -> Points to Backend Elastic IP.
2. **FastAPI CORS**:
   - Update `ALLOWED_ORIGINS` in `app/core/config.py` to allow `https://yourdomain.com`.

---

### Step 9: CloudWatch & Cost Monitoring
1. **CloudWatch Billing Alarm**:
   - Create an alarm triggering when estimated charges exceed **$5.00** or **$10.00**.
   - Attach SNS notification to your email.
2. **Automated Stop Schedule (Optional)**:
   - Use AWS EventBridge + Lambda to shut down the EC2 instances at night if not in use.
