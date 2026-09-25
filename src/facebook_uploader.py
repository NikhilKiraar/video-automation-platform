import os
import shutil
from pathlib import Path
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


# ============================================================
# FACEBOOK REELS SCHEDULER
# ============================================================

# Load .env file
load_dotenv()

PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

# API VERSION
API_VERSION = "v26.0"

# Timezone
TIMEZONE = ZoneInfo("Asia/Kolkata")

# ------------------------------------------------------------
# FOLDERS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

INPUT_FOLDER = BASE_DIR / "input"
PROCESSING_FOLDER = BASE_DIR / "processing"
UPLOADED_FOLDER = BASE_DIR / "Uploaded"
FAILED_FOLDER = BASE_DIR / "failed"

# Create folders automatically if missing
for folder in [
    INPUT_FOLDER,
    PROCESSING_FOLDER,
    UPLOADED_FOLDER,
    FAILED_FOLDER,
]:
    folder.mkdir(exist_ok=True)


# ============================================================
# FACEBOOK DAILY SCHEDULE
# ============================================================

DAILY_TIMES = [
    time(7, 0),    # 7:00 AM
    time(10, 0),   # 10:00 AM
    time(13, 0),   # 1:00 PM
    time(16, 0),   # 4:00 PM
    time(19, 0),   # 7:00 PM
    time(21, 0),   # 9:00 PM
    time(23, 0),   # 11:00 PM
]


# ============================================================
# CHECK SETTINGS
# ============================================================

if not PAGE_ID:
    print("ERROR: FACEBOOK_PAGE_ID is missing.")
    print("Check your .env file.")
    raise SystemExit

if not ACCESS_TOKEN:
    print("ERROR: FACEBOOK_PAGE_ACCESS_TOKEN is missing.")
    print("Check your .env file.")
    raise SystemExit


# ============================================================
# GET VIDEO FILES
# ============================================================

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".wmv",
    ".m4v",
}


def get_videos():

    videos = []

    for file in INPUT_FOLDER.iterdir():

        if file.is_file():

            if file.suffix.lower() in VIDEO_EXTENSIONS:

                videos.append(file)

    # Sort videos alphabetically
    videos.sort(key=lambda x: x.name.lower())

    return videos


# ============================================================
# CREATE CAPTION FROM FILE NAME
# ============================================================

def create_caption(video_file):

    caption = video_file.stem

    # Replace underscores with spaces
    caption = caption.replace("_", " ")

    # Replace multiple spaces
    caption = " ".join(caption.split())

    return caption


# ============================================================
# FIND FIRST SCHEDULING DAY
# ============================================================

def get_first_schedule_day():

    now = datetime.now(TIMEZONE)

    # Start tomorrow at 7 AM.
    # This gives enough time for all videos to upload and schedule.
    tomorrow = now.date() + timedelta(days=1)

    return tomorrow


# ============================================================
# CREATE SCHEDULE TIMES
# ============================================================

def create_schedule(video_count):

    schedule = []

    current_day = get_first_schedule_day()

    video_number = 0

    while video_number < video_count:

        for publish_time in DAILY_TIMES:

            if video_number >= video_count:
                break

            scheduled_datetime = datetime.combine(
                current_day,
                publish_time,
                tzinfo=TIMEZONE
            )

            schedule.append(scheduled_datetime)

            video_number += 1

        # Move to next day
        current_day += timedelta(days=1)

    return schedule


# ============================================================
# MOVE VIDEO SAFELY
# ============================================================

def move_video(video_path, destination_folder):

    destination = destination_folder / video_path.name

    # If same name already exists
    if destination.exists():

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        destination = (
            destination_folder
            / f"{video_path.stem}_{timestamp}{video_path.suffix}"
        )

    shutil.move(
        str(video_path),
        str(destination)
    )

    return destination


# ============================================================
# STEP 1: CREATE FACEBOOK REEL UPLOAD SESSION
# ============================================================

def create_reel():

    host = "graph.facebook.com"

    url = (
        f"https://{host}/"
        f"{API_VERSION}/"
        f"{PAGE_ID}/video_reels"
    )

    data = {
        "access_token": ACCESS_TOKEN,
        "upload_phase": "start",
    }

    response = requests.post(
        url,
        data=data,
        timeout=120
    )

    print("\nCreate Reel Response:")

    print(response.text)

    response.raise_for_status()

    result = response.json()

    video_id = result.get("video_id")
    upload_url = result.get("upload_url")

    if not video_id:

        raise Exception(
            "Facebook did not return video_id."
        )

    if not upload_url:

        raise Exception(
            "Facebook did not return upload_url."
        )

    return video_id, upload_url


# ============================================================
# STEP 2: UPLOAD LOCAL VIDEO
# ============================================================

def upload_video(
    video_path,
    video_id,
    upload_url
):

    file_size = os.path.getsize(video_path)

    headers = {
        "Authorization": f"OAuth {ACCESS_TOKEN}",
        "offset": "0",
        "file_size": str(file_size),
    }

    print("\nUploading video...")

    with open(
        video_path,
        "rb"
    ) as video_file:

        response = requests.post(
            upload_url,
            headers=headers,
            data=video_file,
            timeout=1800
        )

    print("Upload Response:")

    print(response.text)

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):

        raise Exception(
            "Facebook upload was not successful."
        )

    print("Video uploaded successfully.")


# ============================================================
# STEP 3: SCHEDULE REEL ON FACEBOOK
# ============================================================

def schedule_reel(
    video_id,
    title,
    description,
    scheduled_datetime
):

    host = "graph.facebook.com"

    url = (
        f"https://{host}/"
        f"{API_VERSION}/"
        f"{PAGE_ID}/video_reels"
    )

    # Convert IST time to Unix timestamp
    scheduled_timestamp = int(
        scheduled_datetime.timestamp()
    )

    data = {
        "access_token": ACCESS_TOKEN,
        "video_id": video_id,
        "upload_phase": "finish",

        # IMPORTANT:
        # This tells Facebook to schedule,
        # not publish immediately.
        "video_state": "SCHEDULED",

        "scheduled_publish_time":
            scheduled_timestamp,

        "title": title,

        "description":
            description,
    }

    print("\nScheduling Reel...")

    print(
        "Scheduled Time (IST):",
        scheduled_datetime.strftime(
            "%d-%m-%Y %I:%M %p"
        )
    )

    response = requests.post(
        url,
        data=data,
        timeout=120
    )

    print("Schedule Response:")

    print(response.text)

    response.raise_for_status()

    return response.json()


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print("\n" + "=" * 65)

    print("FACEBOOK REELS AUTO SCHEDULER")

    print("=" * 65)

    print(
        "\nPage ID:",
        PAGE_ID
    )

    print(
        "Timezone:",
        "India / Asia-Kolkata"
    )

    print(
        "\nDaily Schedule:"
    )

    for publish_time in DAILY_TIMES:

        print(
            publish_time.strftime(
                "%I:%M %p"
            )
        )

    print("=" * 65)

    # --------------------------------------------------------
    # GET VIDEOS
    # --------------------------------------------------------

    videos = get_videos()

    if not videos:

        print(
            "\nNo videos found."
        )

        print(
            "Put videos inside:"
        )

        print(
            INPUT_FOLDER
        )

        return

    print(
        f"\nFound {len(videos)} videos."
    )

    # --------------------------------------------------------
    # CREATE SCHEDULE
    # --------------------------------------------------------

    schedule = create_schedule(
        len(videos)
    )

    # --------------------------------------------------------
    # SHOW SCHEDULE PLAN
    # --------------------------------------------------------

    print(
        "\nSCHEDULING PLAN"
    )

    print("-" * 65)

    for index, video in enumerate(videos):

        publish_time = schedule[index]

        print(
            f"{index + 1}. "
            f"{video.name}"
        )

        print(
            "   Publish:",
            publish_time.strftime(
                "%d-%m-%Y %I:%M %p"
            )
        )

    print("-" * 65)

    # --------------------------------------------------------
    # CONFIRM
    # --------------------------------------------------------

    confirmation = input(

        "\nType YES to upload and schedule "
        "all these videos: "

    ).strip()

    if confirmation.upper() != "YES":

        print(
            "\nScheduling cancelled."
        )

        return

    # --------------------------------------------------------
    # PROCESS VIDEOS
    # --------------------------------------------------------

    for index, video in enumerate(videos):

        scheduled_datetime = schedule[index]

        print("\n")

        print("=" * 65)

        print(
            f"PROCESSING VIDEO "
            f"{index + 1} "
            f"OF "
            f"{len(videos)}"
        )

        print("=" * 65)

        print(
            "File:",
            video.name
        )

        print(
            "Scheduled:",
            scheduled_datetime.strftime(
                "%d-%m-%Y %I:%M %p"
            )
        )

        processing_video = (
            PROCESSING_FOLDER
            / video.name
        )

        try:

            # Move to processing
            shutil.move(
                str(video),
                str(processing_video)
            )

            # Caption
            caption = create_caption(
                processing_video
            )

            title = caption[:255]

            # ------------------------------------------------
            # CREATE REEL
            # ------------------------------------------------

            video_id, upload_url = create_reel()

            print(
                "\nFacebook Video ID:",
                video_id
            )

            # ------------------------------------------------
            # UPLOAD VIDEO
            # ------------------------------------------------

            upload_video(
                processing_video,
                video_id,
                upload_url
            )

            # ------------------------------------------------
            # SCHEDULE VIDEO
            # ------------------------------------------------

            schedule_response = schedule_reel(

                video_id=video_id,

                title=title,

                description=caption,

                scheduled_datetime=
                    scheduled_datetime,

            )

            print("\nSUCCESS!")

            print(
                "Schedule Response:"
            )

            print(
                schedule_response
            )

            # ------------------------------------------------
            # MOVE TO UPLOADED
            # ------------------------------------------------

            moved_file = move_video(
                processing_video,
                UPLOADED_FOLDER
            )

            print(
                "\nMoved to Uploaded:"
            )

            print(
                moved_file
            )

        except Exception as error:

            print("\nERROR!")

            print(
                str(error)
            )

            # Move file to failed folder
            if processing_video.exists():

                move_video(
                    processing_video,
                    FAILED_FOLDER
                )

                print(
                    "Video moved to failed folder."
                )

            continue

    # --------------------------------------------------------
    # FINISHED
    # --------------------------------------------------------

    print("\n")

    print("=" * 65)

    print(
        "ALL VIDEOS FINISHED PROCESSING"
    )

    print("=" * 65)

    print(
        "\nVideos successfully scheduled are now"
    )

    print(
        "inside the Uploaded folder."
    )

    print(
        "\nFacebook will handle the scheduled"
    )

    print(
        "publishing times."
    )

    print(
        "\nYou do not need this program"
    )

    print(
        "to wait between Reels."
    )

    print("=" * 65)


# ============================================================
# RUN PROGRAM
# ============================================================

if __name__ == "__main__":

    main()