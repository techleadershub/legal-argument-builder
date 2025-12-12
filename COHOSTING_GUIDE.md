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

We need Nginx to direct traffic from `legalargumentbuilder...` to this new container.

### 1. Create Nginx Config
```bash
sudo nano /etc/nginx/sites-available/legal-agent
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

### 3. Enable the Site
```bash
# Link the file to sites-enabled
sudo ln -s /etc/nginx/sites-available/legal-agent /etc/nginx/sites-enabled/

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
