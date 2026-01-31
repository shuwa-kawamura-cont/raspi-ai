# Deployment Guide

## Automated Deployment
This repository is configured to automatically deploy to the Raspberry Pi on every push to the `main` branch.

### Prerequisites (GitHub Secrets)
The following secrets must be set in the repo configuration:
- `PI_HOST`: IP address or Hostname of the Pi.
- `PI_SSH_KEY`: Private SSH key for the `deploy` user.
- `PI_USERNAME`: `deploy` (default) or your custom username.

## Manual Provisioning (First Time Only)

1.  **Run Provisioning Script**:
    Run the `scripts/provision_pi.sh` script on the Pi. You can do this from your local machine via SSH:
    ```bash
    cat scripts/provision_pi.sh | ssh pi@<PI_IP> "bash -"
    ```

2.  **Generate Deploy Keys**:
    On your separate machine (or temporarily on the Pi), generate an SSH keypair for the deploy user:
    ```bash
    ssh-keygen -t ed25519 -f deploy_key -C "deploy@raspi-ai"
    ```
    Add `deploy_key` content to GitHub Secret `PI_SSH_KEY`.
    Add `deploy_key.pub` content to `/home/deploy/.ssh/authorized_keys` on the Pi.

3.  **Install Systemd Service**:
    Copy the service file and enable it (This is usually done after the first deploy, or manually):
    ```bash
    scp config/raspi-ai.service pi@<PI_IP>:/tmp/
    ssh pi@<PI_IP> "sudo mv /tmp/raspi-ai.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable raspi-ai"
    ```

## Operations
- **Check Logs**: `sudo journalctl -u raspi-ai -f`
- **Restart**: `sudo systemctl restart raspi-ai`
