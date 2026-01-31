# Deployment Guide

This project now performs pull-based deployments: the Raspberry Pi periodically pulls the latest commit from GitHub and restarts the `raspi-ai` service whenever a change lands on `main`.

## Workflow Overview
1. `deploy` user on the Pi owns `/opt/raspi-ai`.
2. `config/raspi-ai.service` keeps the bot running from `/opt/raspi-ai/app`.
3. `config/raspi-ai-update.timer` starts `scripts/pull_latest.sh` every two minutes. The script clones the repo if missing, runs `git fetch/reset`, installs Python requirements (if `requirements.txt` exists), and restarts the app service.

## Prerequisites
- Deploy key from the Pi is registered in GitHub (**Settings → Deploy Keys**) with read access to `shuwa-kawamura-cont/raspi-ai`.
- `deploy` user has that private key at `~/.ssh/id_ed25519` (or update `~/.ssh/config` accordingly) and can `ssh git@github.com`.
- Raspberry Pi has the usual dependencies (`git`, `python3-venv`, `rsync`, `build-essential`, `alsa-utils`, `ffmpeg`). Use `scripts/provision_pi.sh` to bootstrap the box if it's brand new.

## Initial Setup
1. **Provision base image (once):**
   ```bash
   cat scripts/provision_pi.sh | ssh pi@<PI_IP> "bash -"
   ```
   This creates the `deploy` user, `/opt/raspi-ai`, venv, and sudoers rule for restarting the service.

2. **SSH as deploy and clone the repo:**
   ```bash
   ssh deploy@<PI_IP>
   mkdir -p /opt/raspi-ai
   cd /opt/raspi-ai
   git clone git@github.com:shuwa-kawamura-cont/raspi-ai.git app
   cd app && chmod +x scripts/pull_latest.sh
   ```

3. **Install/enable the runtime service:**
   ```bash
   sudo cp /opt/raspi-ai/app/config/raspi-ai.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now raspi-ai
   ```

4. **Install/enable the auto-update timer:**
   ```bash
   sudo cp /opt/raspi-ai/app/config/raspi-ai-update.service /etc/systemd/system/
   sudo cp /opt/raspi-ai/app/config/raspi-ai-update.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now raspi-ai-update.timer
   ```

5. **Force an immediate sync (optional but recommended):**
   ```bash
   sudo systemctl start raspi-ai-update.service
   ```

## Operations
- **Check application logs:** `sudo journalctl -u raspi-ai -f`
- **Check update timer logs:** `sudo journalctl -u raspi-ai-update.service -f`
- **Manual pull:** `sudo -u deploy /opt/raspi-ai/app/scripts/pull_latest.sh`
- **Manual restart:** `sudo systemctl restart raspi-ai`

## Advanced Configuration
- Override defaults by exporting environment variables before invoking `scripts/pull_latest.sh`:
  - `RASPI_AI_REPO_URL` – alternate fork URL.
  - `RASPI_AI_BRANCH` – branch to track (default `main`).
  - `RASPI_AI_SERVICE_NAME` – service name to restart (default `raspi-ai`).
  - `RASPI_AI_LOCK_FILE` – custom lock to coordinate parallel runs.
  - `RASPI_AI_SLACK_WEBHOOK` – Incoming Webhook URL for deployment notifications.
  - `RASPI_AI_SLACK_CHANNEL` – Channel override (e.g. `#raspi-ai-deploy`).
  - `RASPI_AI_SLACK_USERNAME` / `RASPI_AI_SLACK_ICON` – Customize display name or emoji/icon.
  - `RASPI_AI_SLACK_NOTIFY_ON_SUCCESS` / `RASPI_AI_SLACK_NOTIFY_ON_FAILURE` / `RASPI_AI_SLACK_NOTIFY_ON_NOOP` – toggle notifications (`true`/`false` as strings).
- To change the polling cadence, adjust `OnBootSec` and `OnUnitActiveSec` inside `config/raspi-ai-update.timer`.

### Slack Webhook Example
1. Slack で Incoming Webhook を作成して URL をコピーする。
2. Pi 上で `sudo systemctl edit raspi-ai-update.service` を実行し、以下のように環境変数を設定する。
   ```
   [Service]
   Environment=RASPI_AI_SLACK_WEBHOOK=https://hooks.slack.com/services/XXX/YYY/ZZZ
   Environment=RASPI_AI_SLACK_CHANNEL=#raspi-ai-deploy
   Environment=RASPI_AI_SLACK_NOTIFY_ON_NOOP=false
   ```
3. `sudo systemctl daemon-reload && sudo systemctl restart raspi-ai-update.timer`

これで pull 成功時は ✅、失敗時は ❌ を含むメッセージが指定チャンネルに送信され、必要なら無変更（no-op）時の通知も制御できます。

### Display & Audio Smoke Test
`app/main.py` にはメディア動作確認モードを追加しています。デプロイパイプラインを試験したいときは、`raspi-ai.service` に以下の環境変数を設定してください。

```
[Service]
Environment=RASPI_AI_MEDIA_TEST=1
# オプション:
# Environment=RASPI_AI_MEDIA_TEST_EXIT=1         # テスト後にプロセス終了
# Environment=RASPI_AI_DISPLAY_TTY=/dev/tty1     # 文字列を表示したい TTY
# Environment=RASPI_AI_DISPLAY_MESSAGE="Hello"   # TTY に流すメッセージ
# Environment=RASPI_AI_AUDIO_SAMPLE=/path/file   # `aplay` で再生する WAV
# Environment=RASPI_AI_AUDIO_COMMAND="speaker-test -t sine -f 660 -l 1"
# Environment=RASPI_AI_DISPLAY_COMMAND="ffplay -autoexit -f lavfi -i testsrc -t 5"
```

1. `sudo systemctl edit raspi-ai.service` で上記設定を追加。
2. `sudo systemctl daemon-reload && sudo systemctl restart raspi-ai`.
3. `journalctl -u raspi-ai -f` で `Media test passed.` を確認。TTY にメッセージが出力され、オーディオが再生されます（`/usr/share/sounds/alsa/Front_Center.wav` が既定）。
4. テスト完了後は `RASPI_AI_MEDIA_TEST` を削除して再起動すれば通常動作に戻ります。
