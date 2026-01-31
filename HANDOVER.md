# raspi-ai 引き継ぎメモ

最終更新: 2026-01-31
担当: Codex (Antigravity 引き継ぎ)

## 1. 全体像
- Raspberry Pi (Debian Bookworm, hostname `raspberrypi`, ユーザー `deploy`) 上で `raspi-ai` サービスを常駐。
- `/opt/raspi-ai/app` で GitHub リポジトリ `shuwa-kawamura-cont/raspi-ai` を pull。`/opt/raspi-ai/venv` の Python venv で `app/main.py` を実行。
- デプロイは Pi 側の systemd timer (`raspi-ai-update.timer`) が 2 分おきに `scripts/pull_latest.sh` を起動し、最新コミットに `git reset --hard` → 依存関係 install → `raspi-ai` サービス再起動。

## 2. コンポーネント
| 役割 | ファイル / サービス | メモ |
| --- | --- | --- |
| アプリ起動 | `config/raspi-ai.service`, `/opt/raspi-ai/app/run.sh`, `app/main.py` | `deploy` ユーザー、`Group=audio`。`SupplementaryGroups=tty` 追加済み。 |
| 自動更新 | `config/raspi-ai-update.service` (oneshot), `config/raspi-ai-update.timer` | タイマーが `scripts/pull_latest.sh` を呼び出し。 |
| Pull スクリプト | `scripts/pull_latest.sh` | Git clone/fetch/reset、`requirements.txt` install、Slack 通知、サービス Restart。
| Slack 通知 | `RASPI_AI_SLACK_*` 環境変数 | 成功/失敗/no-op を Webhook へ投稿。
| メディアテスト | `app/main.py` (環境変数で制御) | Display 文字出力＋音声再生。

## 3. 初期セットアップ手順 (既存 Pi の再構築用)
1. `cat scripts/provision_pi.sh | ssh pi@<PI_IP> "bash -"`
2. `deploy` で `/opt/raspi-ai` に repo clone (`git clone git@github.com:... app`).
3. `sudo cp config/raspi-ai*.service/timer /etc/systemd/system/` → `sudo systemctl daemon-reload` → `sudo systemctl enable --now raspi-ai raspi-ai-update.timer`。
4. `sudo systemctl start raspi-ai-update.service` で初回同期。

## 4. 運用コマンド
- ログ tail: `sudo journalctl -u raspi-ai -f` / `sudo journalctl -u raspi-ai-update.service -f`
- 手動更新: `sudo -u deploy /opt/raspi-ai/app/scripts/pull_latest.sh`
- サービス再起動: `sudo systemctl restart raspi-ai`
- タイマー状態: `sudo systemctl status raspi-ai-update.timer`

## 5. Slack 通知設定
`scripts/pull_latest.sh` で以下の環境変数を参照。
- `RASPI_AI_SLACK_WEBHOOK` (必須)
- `RASPI_AI_SLACK_CHANNEL`, `RASPI_AI_SLACK_USERNAME`, `RASPI_AI_SLACK_ICON`
- 通知制御: `RASPI_AI_SLACK_NOTIFY_ON_SUCCESS|FAILURE|NOOP` (`true`/`false`)

設定方法例:
```
sudo systemctl edit raspi-ai-update.service
[Service]
Environment=RASPI_AI_SLACK_WEBHOOK=https://hooks.slack.com/services/XXX/YYY/ZZZ
Environment=RASPI_AI_SLACK_CHANNEL=#raspi-ai
Environment=RASPI_AI_SLACK_NOTIFY_ON_NOOP=false
```
→ `sudo systemctl daemon-reload && sudo systemctl restart raspi-ai-update.timer`

## 6. ディスプレイ & 音声テスト
- `RASPI_AI_MEDIA_TEST=1` で `app/main.py` が起動時に display/audio テストを実施。
- デフォルト: `/dev/tty1` へメッセージ出力、`/usr/share/sounds/alsa/Front_Center.wav` を `aplay`。
- テストを有効化する drop-in 例:
```
sudo systemctl edit raspi-ai.service
[Service]
Environment=RASPI_AI_MEDIA_TEST=1
Environment=RASPI_AI_MEDIA_TEST_EXIT=1
Environment=RASPI_AI_DISPLAY_MESSAGE="Deploy test $(date)"
Environment=RASPI_AI_AUDIO_SAMPLE=/usr/share/sounds/alsa/Front_Center.wav
SupplementaryGroups=tty  # /dev/tty1 へ書き込むため
```
- 解除時は `RASPI_AI_MEDIA_TEST` 行を削除し、`daemon-reload` → `restart`。

## 7. トラブルシューティング
| 症状 | 対処 |
| --- | --- |
| `Failed to locate executable /opt/raspi-ai/app/run.sh` | `git reset --hard origin/main`、`chmod +x run.sh`。必要なら repo を再 clone。 |
| `Permission denied: '/dev/tty1'` | `deploy` を `tty` グループへ追加 + `SupplementaryGroups=tty`。`ls -l /dev/tty1` で権限確認。 |
| Slack 通知が飛ばない | `RASPI_AI_SLACK_WEBHOOK` 設定・URL 期限を確認。`journalctl -u raspi-ai-update.service` に Python 例外が出ていないか。 |
| pull script がロック待ちで停止 | `/run/lock/raspi-ai-update.lock` を削除するか、進行中プロセスを確認 (`ps aux | grep pull_latest`). |
| GitHub 認証失敗 | `deploy` の `~/.ssh/id_ed25519` (Deploy Key) を再確認。`ssh -T git@github.com` でテスト。

## 8. 権限メモ
- `deploy` には `systemctl`、`cp /etc/systemd/system/*`、`journalctl`、`tee` を NOPASSWD で許可する `/etc/sudoers.d/raspi-ai` を配置しておくと便利。
- `deploy` を `audio` と `tty` グループに所属させておく。

## 9. 今後の TODO / 改善案
- `RASPI_AI_MEDIA_TEST` の結果を Slack に送るオプション追加。
- `requirements.txt` を導入し、自動 pip install を活かす。
- `scripts/pull_latest.sh` にヘルスチェックや `systemctl is-active` の確認を足しても良い。

## 10. 連絡事項
- 自動デプロイは Pi 側の pull で完結しており、GitHub Actions は無効化済み。
- 何か問題が出た場合は `sudo journalctl -u raspi-ai-update.service -n 100` を共有すると切り分けが早いです。
