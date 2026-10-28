# 🚀 Complete Production Cloud Deployment Runbook (`ap-south-2` Hyderabad)

> **Audience**: Complete start-to-finish production deployment guide designed for beginners.  
> **Region**: **`ap-south-2` (Asia Pacific - Hyderabad)**  
> **Estimated Monthly Cost**: ~$0 to $14 (leveraging AWS Free Tier).

---

## 📌 Values to Write in Your Notepad

As you progress through each step, keep a text note open on your computer and save these values:

```text
RDS_ENDPOINT         = <your-db-identifier>.xxxx.ap-south-2.rds.amazonaws.com
RDS_PASSWORD         = <your-chosen-password>
S3_BUCKET_NAME       = <your-unique-s3-bucket-name>
JUDGE0_PRIVATE_IP    = <e.g. 172.31.xx.xx (from AWS EC2 Console)>
BACKEND_ELASTIC_IP   = <e.g. 54.xx.xx.xx (public IP from AWS Console)>
COGNITO_USER_POOL_ID = ap-south-2_xxxxxxxxx (Optional / Step 6)
COGNITO_APP_CLIENT_ID= xxxxxxxxxxxxxxxxxx (Optional / Step 6)
```

---

## ⚠️ Important Rule Before You Start
In the **top-right header** of the AWS Console (next to your username), click the region selector and make sure it is set to **`Asia Pacific (Hyderabad) ap-south-2`**. Keep all services in this region!

---

## 🛡️ STEP 1: Key Pair & Security Groups (Firewalls)

### 1.1 Create an EC2 Key Pair (To SSH into your servers)
1. Open the [AWS EC2 Console](https://console.aws.amazon.com/ec2/) in `ap-south-2`.
2. On the left menu under **Network & Security**, click **Key Pairs** > **Create key pair**.
3. Settings:
   * **Name**: `leetcode-key`
   * **Key pair type**: `RSA`
   * **Private key file format**: `.pem`
4. Click **Create key pair**.
5. The `leetcode-key.pem` file will download to your computer. Save it in a safe folder (e.g. `C:\Users\rishi\.ssh\leetcode-key.pem`).

---

### 1.2 Create the 3 Security Groups
In the EC2 Console on the left menu, click **Security Groups** > click the orange **Create security group** button.

#### Group 1: `sg_api` (Backend Server Firewall)
* **Security group name**: `sg_api`
* **Description**: Backend FastAPI, Redis, and Caddy server
* **VPC**: Select your default VPC
* **Inbound rules** (Click "Add rule" for each):
  1. **HTTP** | Port `80` | Source: `Anywhere-IPv4` (`0.0.0.0/0`)
  2. **HTTPS** | Port `443` | Source: `Anywhere-IPv4` (`0.0.0.0/0`)
  3. **SSH** | Port `22` | Source: `My IP`
* Click **Create security group**.

#### Group 2: `sg_judge0` (Code Runner Sandbox Firewall)
* **Security group name**: `sg_judge0`
* **Description**: Isolated Judge0 code execution engine
* **VPC**: Default VPC
* **Inbound rules**:
  1. **Custom TCP** | Port `2358` | Source: Choose **Custom** > type and select **`sg_api`** *(This ensures Judge0 can only be contacted by your backend, never by the public internet!)*
  2. **SSH** | Port `22` | Source: `My IP`
* Click **Create security group**.

#### Group 3: `sg_rds` (Database Firewall)
* **Security group name**: `sg_rds`
* **Description**: Managed PostgreSQL RDS database
* **VPC**: Default VPC
* **Inbound rules**:
  1. **PostgreSQL** | Port `5432` | Source: Choose **Custom** > type and select **`sg_api`** *(This ensures only your backend can talk to the database)*
* Click **Create security group**.

---

## 🗄️ STEP 2: IAM Role, S3 Storage & RDS Database

### 2.1 Create the IAM Role for EC2 (`leetcode-ec2-s3-role`)
*(Allows your backend to access S3 securely without saving secret access keys in plain text).*

1. Search **IAM** in the top search bar and open it.
2. In the left menu, click **Roles** > **Create role**.
3. Select **AWS service** > Under "Use case", select **EC2** > click **Next**.
4. Click **Create inline policy** (or click the JSON tab):
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
5. Name the policy `leetcode-s3-policy` and save it.
6. Name the Role:
   ```text
   leetcode-ec2-s3-role
   ```
7. Click **Create role**.

---

### 2.2 Create the Amazon S3 Bucket
1. Search **S3** in the top search bar and open it.
2. Click **Create bucket**.
3. Settings:
   * **Bucket name**: e.g., `leetcode-storage-yourname` *(must be lowercase, no spaces; note this name in your notepad as `S3_BUCKET_NAME`)*.
   * **AWS Region**: `ap-south-2` (Hyderabad).
   * Leave **Block all public access** checked (ON).
4. Click **Create bucket**.
5. Click your new bucket > **Permissions** tab > scroll down to **Cross-origin resource sharing (CORS)** > click **Edit** and paste:
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

---

### 2.3 Create the RDS PostgreSQL Database
1. Search **RDS** in the top search bar and open it.
2. Click **Create database**.
3. Settings:
   * **Creation method**: **Standard create** (or **Full configuration**).
   * **Engine**: **PostgreSQL**.
   * **Templates**: Select **Free tier** *(prevents unexpected charges)*.
   * **DB instance identifier**: `leetcode-db`
   * **Master username**: `postgres`
   * **Master password**: Choose a strong password and write it down in your notepad as `RDS_PASSWORD`.
   * **Instance configuration**: `db.t3.micro`.
   * **Storage**: `20 GiB` gp3.
4. **Connectivity**:
   * **Compute resource**: Select **Don't connect to an EC2 compute resource**.
   * **Virtual private cloud (VPC)**: Default VPC.
   * **Public access**: **No**.
   * **VPC security group (firewall)**: Choose **Existing** > select **`sg_rds`** (uncheck `default`).
5. **Additional configuration** (expand the dropdown at the bottom):
   * **Initial database name**: Type:
     ```text
     leetcode_clone
     ```
6. Leave all other settings as their defaults and click **Create database**.
7. *Wait ~5–8 minutes until status turns **Available**.* Click on `leetcode-db` and copy the **Endpoint** URL (e.g. `leetcode-db.c12345.ap-south-2.rds.amazonaws.com`) into your notepad as `RDS_ENDPOINT`.

---

## ⚙️ STEP 3: Launch Judge0 Code Runner Server (EC2)

This isolated server safely compiles and executes student code inside Docker containers.

### 3.1 Launch Instance
1. Open the [AWS EC2 Console](https://console.aws.amazon.com/ec2/) in `ap-south-2`.
2. Click **Launch instance**:
   * **Name**: `leetcode-judge0`
   * **OS**: **Ubuntu Server 24.04 LTS (64-bit x86)**
   * **Instance type**: `t3.small` (requires ~2 GB RAM for compiler containers)
   * **Key pair**: `leetcode-key`
   * **Network settings**: Click **Edit** > Select existing security group **`sg_judge0`**
   * **Storage**: `30 GiB` gp3
3. Click **Launch instance**.

### 3.2 Install Docker & Start Judge0
1. Once running, copy its **Public IPv4 address** and its **Private IPv4 address** (save the Private IP in your notepad as `JUDGE0_PRIVATE_IP`).
2. Open PowerShell or Terminal on your computer and connect:
   ```bash
   ssh -i "path/to/leetcode-key.pem" ubuntu@<JUDGE0-PUBLIC-IP>
   ```
3. Run these setup commands on the server:
   ```bash
   # 1. Install Docker & Git
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
   sudo usermod -aG docker ubuntu
   newgrp docker

   # 2. Clone and start Judge0
   git clone https://github.com/judge0/judge0.git
   cd judge0
   cp judge0.conf.example judge0.conf
   docker compose up -d
   ```
4. Verify Judge0 is ready:
   ```bash
   curl -s http://localhost:2358/health
   # Expected output: {"status":"ready"}
   ```
5. Type `exit` to disconnect.

---

## 🚀 STEP 4: Launch Backend API Server (EC2)

Runs FastAPI, Redis, Celery workers, and the Caddy reverse proxy.

### 4.1 Launch Instance & Allocate Elastic IP
1. Open [AWS EC2 Console](https://console.aws.amazon.com/ec2/) > **Launch instance**:
   * **Name**: `leetcode-backend-api`
   * **OS**: **Ubuntu 24.04 LTS**
   * **Instance type**: `t3.micro` (Free Tier)
   * **Key pair**: `leetcode-key`
   * **Network settings**: Select existing security group **`sg_api`**
   * **Advanced details** (at the bottom) > **IAM instance profile**: Select `leetcode-ec2-s3-role`
2. Click **Launch instance**.
3. Allocate a permanent Elastic IP:
   * Left menu > **Elastic IPs** > **Allocate Elastic IP** > **Allocate**.
   * Select the IP > **Actions** > **Associate Elastic IP** > Choose instance `leetcode-backend-api` > Click **Associate**.
   * Copy this IP into your notepad as `BACKEND_ELASTIC_IP`.

### 4.2 Install Software & Clone Repository
1. Connect via SSH:
   ```bash
   ssh -i "path/to/leetcode-key.pem" ubuntu@<BACKEND_ELASTIC_IP>
   ```
2. Install dependencies:
   ```bash
   sudo apt-get update && sudo apt-get install -y python3-pip python3-venv git redis-server caddy
   ```
3. Clone repo and install Python requirements:
   ```bash
   sudo git clone https://github.com/RishiJhaver/barn-burner.git /opt/leetcode-backend
   sudo chown -R ubuntu:ubuntu /opt/leetcode-backend
   cd /opt/leetcode-backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

### 4.3 Configure the `.env` File
Run:
```bash
nano /opt/leetcode-backend/.env
```
Paste this configuration, replacing the capitalized placeholders with your values:

```ini
ENVIRONMENT=production
DEBUG=False

# Database (From Step 2.3)
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/leetcode_clone
SYNC_DATABASE_URL=postgresql://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/leetcode_clone

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Judge0 Sandbox (Use Private IP from Step 3.2)
MOCK_JUDGE0=False
JUDGE0_URL=http://YOUR_JUDGE0_PRIVATE_IP:2358
JUDGE0_CALLBACK_URL=http://YOUR_BACKEND_ELASTIC_IP:8000/api/v1/internal/judge0-callback
JUDGE0_CPU_TIME_LIMIT=2.0
JUDGE0_MEMORY_LIMIT=128000

# S3 Storage (Set MOCK_S3=True for initial zero-setup test, or False with your bucket)
MOCK_S3=True
AWS_REGION=ap-south-2
S3_BUCKET_NAME=YOUR_S3_BUCKET_NAME

# Authentication (Set MOCK_COGNITO=True for instant working auth without Cognito setup)
MOCK_COGNITO=True
DEMO_JWT_SECRET=super-secure-production-jwt-secret-key-32-chars-minimum

# CORS (Automatically permits all Vercel apps)
ALLOWED_ORIGINS=https://*.vercel.app,http://localhost:5173
```
> Press `Ctrl + O`, hit `Enter`, then `Ctrl + X` to save and exit.

### 4.4 Run Database Migrations & Problem Seeding
```bash
cd /opt/leetcode-backend
source .venv/bin/activate
alembic upgrade head
python seed_problems.py
```

### 4.5 Start Background Daemons (Systemd & Caddy)

1. **FastAPI Service**:
   ```bash
   sudo nano /etc/systemd/system/leetcode-api.service
   ```
   Paste:
   ```ini
   [Unit]
   Description=FastAPI Backend
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

2. **Celery Worker Service**:
   ```bash
   sudo nano /etc/systemd/system/leetcode-worker.service
   ```
   Paste:
   ```ini
   [Unit]
   Description=Celery Evaluation Worker
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

3. **Start Both Services**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now leetcode-api leetcode-worker
   ```

4. **Configure Caddy (Reverse Proxy)**:
   ```bash
   sudo nano /etc/caddy/Caddyfile
   ```
   Replace file contents with:
   ```caddy
   :80 {
       reverse_proxy 127.0.0.1:8000
   }
   ```
   Reload Caddy:
   ```bash
   sudo systemctl reload caddy
   ```

5. **Test Your Backend**:
   Visit `http://<YOUR_BACKEND_ELASTIC_IP>/docs` in your browser. The Swagger UI will load.

---

## 🌐 STEP 5: Deploy Frontend on Vercel

1. Log in to [vercel.com](https://vercel.com/) with GitHub.
2. Click **Add New...** > **Project** > Import `barn-burner`.
3. In configuration:
   * **Root Directory**: Click **Edit** and select `frontend`.
   * **Framework Preset**: Vite (detected automatically).
   * **Environment Variables**: Add:
     * **Name**: `VITE_API_URL`
     * **Value**: `http://<YOUR_BACKEND_ELASTIC_IP>`
4. Click **Deploy**.
5. Vercel will build and give you a live URL (e.g. `https://barn-burner.vercel.app`).

---

## 🔐 STEP 6: AWS Cognito User Authentication (Optional)

*(With `MOCK_COGNITO=True` above, user signup & login works immediately without AWS Cognito! To connect real AWS Cognito emails:)*

1. Open AWS **Cognito** in `ap-south-2` > **Create user pool**.
2. **Sign-in options**: Email.
3. **Password policy**: Select "No MFA".
4. **App client**: Name it `leetcode-web` and ensure **Don't generate a client secret** is selected.
5. Copy the **User Pool ID** and **App Client ID**.
6. In `/opt/leetcode-backend/.env` on your EC2 backend server:
   ```ini
   MOCK_COGNITO=False
   COGNITO_USER_POOL_ID=ap-south-2_xxxxxxxxx
   COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxx
   COGNITO_ISSUER=https://cognito-idp.ap-south-2.amazonaws.com/ap-south-2_xxxxxxxxx
   ```
7. Restart the backend:
   ```bash
   sudo systemctl restart leetcode-api
   ```

---

## ✅ STEP 7: End-to-End Verification

1. Open your live Vercel frontend URL.
2. Click **Sign In / Register** and create an account.
3. Open problem **Two Sum**.
4. Click **Run Code** (evaluates sample test cases via Judge0).
5. Click **Submit Solution** (evaluates against full hidden test suite, displays verdict & confetti).

---

## 🛠️ Maintenance & Useful Commands (On Backend EC2)

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
