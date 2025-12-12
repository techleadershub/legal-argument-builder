# Cohosting Guide: Legal Agent on Existing EC2 Server

This guide provides step-by-step instructions to deploy the **Legal Argument Builder** alongside your existing **HR Interview Agent** on the same AWS EC2 instance (Ubuntu 24.04).

## Prerequisites
- [x] **EC2 Instance**: `t3.medium` (running, configured with Elastic IP).
- [x] **Existing App**: HR Interview Agent works.
- [x] **New Domain**: DNS `A Record` for `legalargumentbuilder.futureproofindia.com` points to the Elastic IP.
- [x] **Tools**: Docker, Git, Nginx, Certbot installed.

---

## Part 1: Prepare the New Application (Local Computer)

We have already configured `docker-compose.yml` to minimize conflicts.
1. **Push your code** to GitHub.
   ```bash
   git add .
   git commit -m "feat: ready for deployment"
   git push origin main
   ```

---

## Part 2: Deploy to Server (SSH into EC2)

Log into your EC2 instance:
```bash
ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute-1.amazonaws.com
```

### 1. Clone & Configure
Navigate to your projects folder (e.g., `~/code` or just `~`).

```bash
# Clone the repository
git clone <YOUR_GITHUB_REPO_URL> legal-agent
cd legal-agent

# Create the .env file
nano .env
# PASTE: OPENAI_API_KEY=sk-proj-xxxx...
# Save & Exit (Ctrl+O, Enter, Ctrl+X)
```

### 2. Launch the Container
Start the app on port **8501**. The data ingestion happens automatically on first boot.

```bash
# Start in background
docker-compose up -d --build

# Verify it's running
docker ps
# You should see 'legal-agent' listening on 0.0.0.0:8501
```

---

## Part 3: Configure Nginx (Reverse Proxy)

Since your server uses the `conf.d` pattern, we will create a new config file right next to your existing one.

### 1. Create Nginx Config
```bash
sudo nano /etc/nginx/conf.d/legal-agent.conf
```

### 2. Paste Configuration
We include special headers for **Streamlit Websockets**.

```nginx
server {
    server_name legalargumentbuilder.futureproofindia.com;

    location / {
        proxy_pass http://127.0.0.1:8501/;
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### 3. Reload Nginx
No symbolic links needed for `conf.d`. Just test and reload.

```bash
# Test configuration (Ensure no syntax errors)
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 4. Enable HTTPS
Generate an SSL certificate so the site works on secure `https://`.
```bash
sudo certbot --nginx -d legalargumentbuilder.futureproofindia.com
```

---

## Part 4: Adjustments to Previous Application (Safety Check)

You likely **do not need to change code** in your HR application, but you must ensure **Port Safety**.

1. **Check Used Ports**:
   Run `sudo netstat -tulpn | grep LISTEN`
   - Ensure `docker-proxy` is listening on `8501` (Legal Agent).
   - Ensure your HR Agent is listening on its own port (e.g., `8000` or `3000`).
   
2. **Conflict Resolution**:
   If your HR Agent *was* using port 8501 (default Streamlit port, improbable for React/FastAPI), you must edit its `docker-compose.yml` to map to a different host port (e.g., `8502:8501`) and update its Nginx config file in `sites-available` to match. 
   
   *Likely scenario: HR Agent uses 3000/8000. No conflict.*

---

## Part 5: Resource Monitoring (Critical for t3.medium)

Running two AI agents + Nginx requires memory management.

1. **Check Memory**:
   ```bash
   htop
   ```
   If Mem bar is green/full > 3.5GB, proceed to step 2.

2. **Add Swap Space (Safety Net)**:
   This uses disk space as "emergency RAM" to prevent crashing.
   ```bash
   # Create a 4GB swap file
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   
   # Make it permanent
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

**Done!** Your server is now a multi-tenant AI powerhouse.

---

## Troubleshooting: GitHub Cloning Issues

If `git clone` fails despite adding SSH keys:

1. **Verify URL Type**: You MUST use the **SSH URL**, not HTTPS.
   - ❌ Wrong: `git clone https://github.com/techleadershub/legal-argument-builder.git`
   - ✅ Correct: `git clone git@github.com:techleadershub/legal-argument-builder.git`

2. **Test Connection**:
   Run this on EC2 to check if GitHub accepts your key:
   ```bash
   ssh -T git@github.com
   ```
   - If it says "Hi [username]!", it works.
   - If it says "Permission denied (publickey)", read step 3.

3. **Manual Key Usage**:
   If you named your key something custom (e.g., `github_key`), tell git to use it:
   ```bash
   # Add to SSH agent
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/github_key
   ```
   
4. **Permissions Fix**:
   SSH keys must be private.
   ```bash
   ```bash
   chmod 600 ~/.ssh/config ~/.ssh/id_rsa
   ```

---

## SSL Certificate Auto-Renewal

Certbot usually installs a systemd timer to check your certificates twice a day and renew them if they are within 30 days of expiration.

1. **Verify Auto-Renewal is Active**:
   ```bash
   sudo systemctl status snap.certbot.renew.service
   # OR
   sudo systemctl list-timers | grep certbot
   ```

2. **Test the Renewal Process**:
   To be absolutely sure it will work when the time comes, run a "dry run". This simulates the process without actually changing anything.
   ```bash
   ```bash
   sudo certbot renew --dry-run
   ```
   If this reports "Simulated renewal succeeded", your certificates will renew automatically forever.

---

## Final Check: Auto-Restart on Boot

We have configured `docker-compose.yml` with `restart: unless-stopped`. This means the container will start automatically after a reboot, **but only if the Docker service itself is managed by the OS**.

Run this one command to ensure Docker starts when the server boots:

```bash
sudo systemctl enable docker
```

**Verification Plan:**
1. Reboot the server: `sudo reboot`
2. Wait 1 minute.
3. Visit `https://legalargumentbuilder.futureproofindia.com`. acts
4. It should load automatically without you SSH-ing in.
