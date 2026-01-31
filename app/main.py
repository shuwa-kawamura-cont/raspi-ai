import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

MEDIA_TEST_ENABLED = os.getenv("RASPI_AI_MEDIA_TEST", "1") == "1"
MEDIA_TEST_EXIT = os.getenv("RASPI_AI_MEDIA_TEST_EXIT", "0") == "1"
DISPLAY_TTY = Path(os.getenv("RASPI_AI_DISPLAY_TTY", "/dev/tty1"))
DISPLAY_MESSAGE = os.getenv(
    "RASPI_AI_DISPLAY_MESSAGE",
    "=== DEPLOY TEST SUCCESS ===\nHello Shuwa!\nUpdate time: " + time.ctime() + "\n==========================",
)
DISPLAY_COMMAND = os.getenv("RASPI_AI_DISPLAY_COMMAND")
AUDIO_COMMAND = os.getenv("RASPI_AI_AUDIO_COMMAND")
AUDIO_SAMPLE = os.getenv("RASPI_AI_AUDIO_SAMPLE", "/usr/share/sounds/alsa/Front_Center.wav")


def run_command(cmd, description):
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"{description} succeeded.", flush=True)
        return True
    except FileNotFoundError:
        print(f"{description} failed: command not found ({cmd[0]}).", flush=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"{description} failed with exit code {exc.returncode}. stderr: {exc.stderr.decode().strip()}",
            flush=True,
        )
    return False


def show_display_test():
    if DISPLAY_COMMAND:
        return run_command(shlex.split(DISPLAY_COMMAND), "Custom display command")

    if DISPLAY_TTY.exists():
        try:
            with DISPLAY_TTY.open("w") as tty:
                tty.write(f"\n{DISPLAY_MESSAGE}\n")
            print(f"Wrote display message to {DISPLAY_TTY}.", flush=True)
            return True
        except PermissionError as exc:
            print(f"Failed to write to {DISPLAY_TTY}: {exc}", flush=True)

    ffplay = shutil.which("ffplay")

    if ffplay:
        cmd = [
            ffplay,
            "-autoexit",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x480:rate=30",
            "-t",
            os.getenv("RASPI_AI_DISPLAY_DURATION", "3"),
        ]
        return run_command(cmd, "ffplay display pattern")

    print("No display command available (set RASPI_AI_DISPLAY_COMMAND or provide /dev/tty1 access).", flush=True)
    return False


def play_audio_test():
    if AUDIO_COMMAND:
        return run_command(shlex.split(AUDIO_COMMAND), "Custom audio command")

    sample_path = Path(AUDIO_SAMPLE)
    if sample_path.exists():
        return run_command(["aplay", str(sample_path)], "aplay sample")

    speaker_test = shutil.which("speaker-test")
    if speaker_test:
        cmd = [speaker_test, "-t", "sine", "-f", os.getenv("RASPI_AI_AUDIO_TONE", "880"), "-l", "1"]
        return run_command(cmd, "speaker-test tone")

    ffplay = shutil.which("ffplay")
    if ffplay:
        cmd = [
            ffplay,
            "-autoexit",
            "-nodisp",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={os.getenv('RASPI_AI_AUDIO_TONE', '880')}:duration=2",
        ]
        return run_command(cmd, "ffplay sine tone")

    print("No audio playback command available (set RASPI_AI_AUDIO_COMMAND or provide sample file).", flush=True)
    return False


def run_media_test():
    print("Running media test (display + audio)...", flush=True)
    display_ok = show_display_test()
    audio_ok = play_audio_test()
    if display_ok and audio_ok:
        print("Media test passed.", flush=True)
    else:
        print(f"Media test incomplete (display_ok={display_ok}, audio_ok={audio_ok}).", flush=True)
    return display_ok and audio_ok


def main():
    if MEDIA_TEST_ENABLED:
        success = run_media_test()
        if MEDIA_TEST_EXIT:
            sys.exit(0 if success else 1)

    print("Raspi-AI Bot started...", flush=True)
    while True:
        print("Bot is running. Waiting for events...", flush=True)
        time.sleep(10)

if __name__ == "__main__":
    main()
