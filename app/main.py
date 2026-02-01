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
    "=== AUTO DEPLOY SUCCESS ===\nNow showing on your desktop!\nUpdate time: " + time.ctime() + "\n==========================",
)
DISPLAY_COMMAND = os.getenv("RASPI_AI_DISPLAY_COMMAND")
AUDIO_COMMAND = os.getenv("RASPI_AI_AUDIO_COMMAND")
AUDIO_SAMPLE = os.getenv("RASPI_AI_AUDIO_SAMPLE", "/usr/share/sounds/alsa/Front_Center.wav")
AUDIO_LOOP = os.getenv("RASPI_AI_AUDIO_LOOP", "0") == "1"
AUDIO_DEVICE = os.getenv("RASPI_AI_AUDIO_DEVICE", "")  # e.g. "hw:1,0"


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
    zenity = shutil.which("zenity")
    if zenity and os.getenv("DISPLAY"):
        cmd = [
            zenity,
            "--info",
            "--text",
            DISPLAY_MESSAGE,
            "--timeout",
            os.getenv("RASPI_AI_DISPLAY_DURATION", "10"),
        ]
        # Run in background to not block the bot
        subprocess.Popen(cmd, env={**os.environ, "DISPLAY": ":0"})
        print("Triggered zenity info dialog on DISPLAY :0", flush=True)

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


def play_audio(cmd, description, loop=False):
    if loop:
        try:
            # Use Popen for looping so it doesn't block
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Started looping {description} in background.", flush=True)
            return True
        except Exception as exc:
            print(f"Failed to start looping {description}: {exc}", flush=True)
            return False
    return run_command(cmd, description)


def show_zenity_message(message, timeout=3):
    zenity = shutil.which("zenity")
    if zenity and os.getenv("DISPLAY"):
        cmd = [zenity, "--info", "--text", message, "--timeout", str(timeout)]
        subprocess.Popen(cmd, env={**os.environ, "DISPLAY": ":0"})
        return True
    return False


def play_audio_test():
    if AUDIO_COMMAND:
        show_zenity_message(f"Audio Test: Custom Command\n{AUDIO_COMMAND}")
        return play_audio(shlex.split(AUDIO_COMMAND), "Custom audio command", loop=AUDIO_LOOP)

    sample_path = Path(AUDIO_SAMPLE)
    ffplay = shutil.which("ffplay")
    
    # Device description for display
    dev_desc = AUDIO_DEVICE if AUDIO_DEVICE else "Default"
    msg = f"Audio Test: {dev_desc}\nSample: {sample_path.name}"
    show_zenity_message(msg)

    if AUDIO_LOOP and ffplay:
        cmd = [
            ffplay,
            "-loop", "0",
            "-nodisp",
            "-loglevel", "error",
        ]
        if AUDIO_DEVICE:
            cmd.extend(["-af", f"Volume=1.0", "-ao", f"alsa=device={AUDIO_DEVICE}"])
            # Note: ffplay alsa syntax is a bit different, trial and error or use -device
        
        if sample_path.exists():
            cmd.append(str(sample_path))
        else:
            cmd.extend(["-f", "lavfi", "-i", f"sine=frequency={os.getenv('RASPI_AI_AUDIO_TONE', '880')}"])
        
        return play_audio(cmd, f"ffplay loop ({dev_desc})", loop=True)

    if sample_path.exists():
        cmd = ["aplay"]
        # Try pulse/default first if no device specified, or use the specified one
        effective_device = AUDIO_DEVICE if AUDIO_DEVICE else "default"
        cmd.extend(["-D", effective_device])
        cmd.append(str(sample_path))
        
        # If it fails, we'll try 'pulse' explicitly as a fallback
        if not run_command(cmd, f"aplay sample ({effective_device})"):
            print("Retrying with 'pulse' device...", flush=True)
            return run_command(["aplay", "-D", "pulse", str(sample_path)], "aplay sample (pulse fallback)")
        return True

    speaker_test = shutil.which("speaker-test")
    if speaker_test:
        cmd = [speaker_test, "-t", "sine", "-f", os.getenv("RASPI_AI_AUDIO_TONE", "880"), "-l", "1"]
        if AUDIO_DEVICE:
            # speaker-test uses -D
            cmd.extend(["-D", AUDIO_DEVICE])
        return run_command(cmd, f"speaker-test tone ({dev_desc})")

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

    print("No audio playback command available.", flush=True)
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
