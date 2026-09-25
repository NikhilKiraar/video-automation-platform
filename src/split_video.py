import argparse
import subprocess
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).parent
DEFAULT_INPUT = PROJECT_DIR / "input"
DEFAULT_OUTPUT = PROJECT_DIR / "output"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".wmv"}


def get_video_duration(video_path):
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Cannot read video duration:\n{result.stderr}"
        )

    return float(result.stdout.strip())


def split_video(video_path, output_dir, duration):

    total_duration = get_video_duration(video_path)

    print(f"\nProcessing: {video_path.name}")
    print(f"Video duration: {int(total_duration)} seconds")

    start_time = 0
    part_number = 1

    while start_time < total_duration:

        output_file = output_dir / (
            f"{video_path.stem}_part_{part_number:03d}.mp4"
        )

        command = [
            "ffmpeg",
            "-y",
            "-ss", str(start_time),
            "-i", str(video_path),
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_file)
        ]

        print(
            f"Creating part {part_number}: "
            f"{int(start_time)}s → "
            f"{int(min(start_time + duration, total_duration))}s"
        )

        result = subprocess.run(command)

        if result.returncode != 0:
            print(f"ERROR splitting: {video_path.name}")
            return

        start_time += duration
        part_number += 1

    print(f"Finished: {video_path.name}")


def main():

    parser = argparse.ArgumentParser(
        description="Split videos into smaller parts"
    )

    parser.add_argument(
        "--seconds",
        type=int,
        required=True,
        help="Length of each video part in seconds"
    )

    parser.add_argument(
        "--input",
        type=str,
        default=str(DEFAULT_INPUT),
        help="Input folder path"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Output folder path"
    )

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        print(f"Input folder does not exist: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    videos = [
        file for file in input_dir.iterdir()
        if file.is_file()
        and file.suffix.lower() in VIDEO_EXTENSIONS
    ]

    if not videos:
        print("No videos found in input folder.")
        return

    print("\n==============================")
    print("VIDEO SPLITTER")
    print("==============================")
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Split duration: {args.seconds} seconds")
    print(f"Videos found: {len(videos)}")

    for video in videos:

        try:
            split_video(
                video,
                output_dir,
                args.seconds
            )

        except Exception as error:

            print(
                f"\nFAILED: {video.name}"
            )

            print(error)

    print("\n==============================")
    print("ALL PROCESSING FINISHED")
    print("==============================")


if __name__ == "__main__":
    main()