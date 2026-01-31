#!/bin/bash
set -e

# Configuration
APP_DIR="/opt/raspi-ai"
DEPLOY_USER="deploy"

echo ">>> Starting Raspberry Pi Provisioning..."

# 1. Install Dependencies
echo ">>> Installing dependencies..."
sudo apt-get update
sudo apt-get install -y git python3-venv rsync build-essential alsa-utils ffmpeg

# 2. Create Deploy User
if id "$DEPLOY_USER" &>/dev/null; then
    echo ">>> User '$DEPLOY_USER' already exists."
else
    echo ">>> Creating user '$DEPLOY_USER'..."
    sudo useradd -m -s /bin/bash "$DEPLOY_USER"
fi

# Add to audio group
sudo usermod -aG audio "$DEPLOY_USER"

# Setup SSH keys directory if not exists
sudo -u "$DEPLOY_USER" mkdir -p /home/$DEPLOY_USER/.ssh
sudo -u "$DEPLOY_USER" chmod 700 /home/$DEPLOY_USER/.ssh
sudo -u "$DEPLOY_USER" touch /home/$DEPLOY_USER/.ssh/authorized_keys
sudo -u "$DEPLOY_USER" chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys

# 3. Setup Application Directory
echo ">>> Setting up directory structure at $APP_DIR..."
if [ ! -d "$APP_DIR" ]; then
    sudo mkdir -p "$APP_DIR"
    sudo mkdir -p "$APP_DIR/app"
fi
sudo chown -R "$DEPLOY_USER":root "$APP_DIR"
sudo chmod -R 755 "$APP_DIR"

# 4. Create Virtual Environment
echo ">>> Setting up python venv..."
if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u "$DEPLOY_USER" python3 -m venv "$APP_DIR/venv"
    sudo -u "$DEPLOY_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
else
    echo ">>> venv already exists."
fi

# 5. Setup sudoers for service restart
echo ">>> Configuring sudoers for seamless restart..."
SUDO_FILE="/etc/sudoers.d/raspi-ai-restart"
if [ ! -f "$SUDO_FILE" ]; then
    echo "$DEPLOY_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart raspi-ai" | sudo tee "$SUDO_FILE" > /dev/null
    sudo chmod 440 "$SUDO_FILE"
fi

echo ">>> Provisioning Complete!"
echo "Next step: Install systemd service using 'config/raspi-ai.service' available in the repo."
