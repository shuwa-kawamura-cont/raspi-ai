# Raspberry Pi Setup & Connection Guide

## Configuration Details
This Raspberry Pi has been configured for headless operation with the following settings:

- **Hostname**: `raspberrypi`
- **User**: `pi`
- **Password**: `admin`
- **WiFi SSID**: `Shuwa & Mai`
- **SSH**: Enabled
- **MAC Address Prefix**: `d8:3a:dd` (Used for device discovery)

## How to Connect

### Option 1: Dynamic Connection (Recommended)
Since the IP address may change (DHCP), use this command to automatically find the Pi by its MAC address and connect.

**On Mac Terminal:**
```bash
ssh pi@$(arp -a | grep "d8:3a:dd" | awk '{print $2}' | tr -d '()')
```
- **Password**: `admin`

### Option 2: Hostname
If your network supports mDNS properly:
```bash
ssh pi@raspberrypi.local
```

### Option 3: Static IP (Current)
Currently identified at `192.168.1.194`.
```bash
ssh pi@192.168.1.194
```

## Setup Handy Alias
To make it easier, add this to your `~/.zshrc`:
```bash
echo "alias ssh-pi='ssh pi@\$(arp -a | grep \"d8:3a:dd\" | awk \"{print \\\$2}\" | tr -d \"()\")'" >> ~/.zshrc
source ~/.zshrc
```
Then you can simply run:
```bash
ssh-pi
```
