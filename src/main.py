import subprocess
from pathlib import Path
import shutil
import sys

# ==========================================
# FACEBOOK 15 SECOND VIDEO SPLITTER
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FOLDER = BASE_DIR / "input"
OUTPUT_FOLDER = BASE_DIR / "output" / "facebook"

CLIP_DURATION = 15

VIDEO_EXTENSIONS = [
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".m4v",
    ".webm"
]


def check_ffmpeg():
    """Check whether FFmpeg is installed."""
    if shutil.which("ffmpeg") is None:
        print("\nERROR: FFmpeg is not installed or not added to PATH.")
        print("Install FFmpeg first and restart Command Prompt.")
        sys.exit(1)


def get_video_duration(video_path):
    """Get video duration using ffprobe."""

    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        return float(result.stdout.strip())

    except Exception as e:
        print(f"Could not get duration: {e}")
        return None


def split_video(video_path):
    """Split one video into 15-second clips."""

    print("\n" + "=" * 70)
    print(f"PROCESSING: {video_path.name}")
    print("=" * 70)

    duration = get_video_duration(video_path)

    if duration is None:
        print("Skipping this video.")
        return

    print(f"Video Duration: {round(duration, 2)} seconds")
    print(f"Clip Duration: {CLIP_DURATION} seconds")

    video_name = video_path.stem

    clip_number = 1
    start_time = 0

    while start_time < duration:

        output_file = OUTPUT_FOLDER / (
            f"{video_name}_facebook_{clip_number:03d}.mp4"
        )

        print(
            f"\nCreating Clip {clip_number}: "
            f"{start_time}s → {min(start_time + CLIP_DURATION, duration)}s"
        )

        command = [
            "ffmpeg",
            "-y",

            "-ss", str(start_time),

            "-i", str(video_path),

            "-t", str(CLIP_DURATION),

            "-map", "0:v:0",
            "-map", "0:a?",

            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",

            "-c:a", "aac",
            "-b:a", "128k",

            "-movflags", "+faststart",

            str(output_file)
        ]

        try:
            subprocess.run(
                command,
                check=True
            )

            print(f"SUCCESS: {output_file.name}")

        except subprocess.CalledProcessError:
            print(f"FAILED: {video_path.name}")
            break

        start_time += CLIP_DURATION
        clip_number += 1

    print("\nVIDEO SPLITTING COMPLETED.")


def main():

    print("\n" + "=" * 70)
    print("FACEBOOK REELS AUTOMATION")
    print("15 SECOND VIDEO SPLITTER")
    print("=" * 70)

    check_ffmpeg()

    # Create folders automatically
    INPUT_FOLDER.mkdir(exist_ok=True)
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # Find videos
    videos = [
        file for file in INPUT_FOLDER.iterdir()
        if file.is_file()
        and file.suffix.lower() in VIDEO_EXTENSIONS
    ]

    if not videos:

        print("\nNO VIDEOS FOUND.")

        print("\nPut your long videos here:")
        print(INPUT_FOLDER)

        return

    print(f"\nFound {len(videos)} video(s).")
    print("\nOutput folder:")
    print(OUTPUT_FOLDER)

    for index, video in enumerate(videos, start=1):

        print("\n" + "#" * 70)
        print(f"VIDEO {index} OF {len(videos)}")
        print("#" * 70)

        split_video(video)

    print("\n" + "=" * 70)
    print("ALL FACEBOOK CLIPS CREATED SUCCESSFULLY")
    print("=" * 70)

    print("\nYour 15-second Facebook clips are here:")
    print(OUTPUT_FOLDER)


if __name__ == "__main__":
    main()