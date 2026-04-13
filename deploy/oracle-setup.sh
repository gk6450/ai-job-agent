#!/bin/bash
# Oracle Cloud Always Free VM Setup Script
# Run this on a fresh Oracle Cloud Ubuntu/ARM instance

set -e

echo "=== JobPilot Server Setup ==="

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Setup swap (Oracle free tier has limited RAM for builds)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Open firewall ports
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
sudo netfilter-persistent save

# Install Nginx for reverse proxy
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Setup project directory
mkdir -p ~/jobpilot
cd ~/jobpilot

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Clone your repo: git clone <url> ."
echo "2. Copy .env.example to .env and fill in values"
echo "3. Place service-account.json in data/"
echo "4. Run: docker compose up -d"
echo "5. Setup SSL: sudo certbot --nginx -d yourdomain.com"
echo ""
