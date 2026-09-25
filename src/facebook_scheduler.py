import os
import json
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


# ============================================================
# FACEBOOK REELS SMART SCHEDULER
# ============================================================
# Uploads videos from OUTPUT folder
# Schedules them on Facebook
# Continues after the last scheduled video
# Laptop does NOT need to remain ON after scheduling completes
# ============================================================


# ------------------------------------------------------------
# LOAD .ENV
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

API_VERSION = os.getenv("FACEBOOK_API_VERSION", "v26.0")


# ------------------------------------------------------------
# FOLDERS
# ------------------------------------------------------------

OUTPUT_FOLDER = BASE_DIR / "output"
UPLOADED_FOLDER = BASE_DIR / "Uploaded"
FAILED_FOLDER = BASE_DIR / "failed"

SCHEDULE_FILE = BASE_DIR / "facebook_schedule.json"


# ------------------------------------------------------------
# FACEBOOK SETTINGS
# ------------------------------------------------------------

TIMEZONE = ZoneInfo("Asia/Kolkata")

# 7 Reels per day
#
# You can change these times later.
#
DAILY_SCHEDULE_TIMES = [
    "08:00",
    "10:30",
    "13:00",
    "15:30",
    "18:00",
    "20:30",
    "22:30",
]


# ------------------------------------------------------------
# VIDEO EXTENSIONS
# ------------------------------------------------------------

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".wmv",
    ".m4v",
}


# ============================================================
# CREATE REQUIRED FOLDERS
# ============================================================

OUTPUT_FOLDER.mkdir(exist_ok=True)
UPLOADED_FOLDER.mkdir(exist_ok=True)
FAILED_FOLDER.mkdir(exist_ok=True)


# ============================================================
# CHECK SETTINGS
# ============================================================

if not PAGE_ID:
    print("\nERROR: FACEBOOK_PAGE_ID is missing.")
    print("Check your .env file.\n")
    raise SystemExit()

if not ACCESS_TOKEN:
    print("\nERROR: FACEBOOK_PAGE_ACCESS_TOKEN is missing.")
    print("Check your .env file.\n")
    raise SystemExit()


# ============================================================
# LOAD SCHEDULE HISTORY
# ============================================================

def load_schedule_history():

    if not SCHEDULE_FILE.exists():
        return []

    try:

        with open(SCHEDULE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except Exception as error:

        print(f"Warning: Could not read schedule history: {error}")

        return []


# ============================================================
# SAVE SCHEDULE HISTORY
# ============================================================

def save_schedule_history(history):

    with open(SCHEDULE_FILE, "w", encoding="utf-8") as file:

        json.dump(
            history,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# GET LAST SCHEDULED TIME
# ============================================================

def get_last_scheduled_time():

    history = load_schedule_history()

    latest_time = None

    for item in history:

        try:

            scheduled_time = datetime.fromisoformat(
                item["scheduled_time"]
            )

            if latest_time is None:

                latest_time = scheduled_time

            elif scheduled_time > latest_time:

                latest_time = scheduled_time

        except Exception:
            continue

    return latest_time


# ============================================================
# GET NEXT AVAILABLE SCHEDULE TIME
# ============================================================

def get_next_schedule_time(after_time=None):

    now = datetime.now(TIMEZONE)

    # If no previous scheduled video exists,
    # start from current time
    if after_time is None:

        search_from = now

    else:

        # Continue after previous scheduled video
        search_from = after_time + timedelta(seconds=1)

        # Never schedule in the past
        if search_from < now:
            search_from = now


    current_date = search_from.date()


    # Search future days
    for day_offset in range(0, 365):

        schedule_date = current_date + timedelta(days=day_offset)

        for time_string in DAILY_SCHEDULE_TIMES:

            hour, minute = map(
                int,
                time_string.split(":")
            )

            candidate_time = datetime(
                schedule_date.year,
                schedule_date.month,
                schedule_date.day,
                hour,
                minute,
                tzinfo=TIMEZONE
            )

            if candidate_time > search_from:

                return candidate_time


    raise Exception(
        "Could not find an available schedule time."
    )


# ============================================================
# GET VIDEO TITLE
# ============================================================

def create_title(video_file):

    title = video_file.stem

    # Replace underscores with spaces
    title = title.replace("_", " ")

    # Remove extra spaces
    title = " ".join(title.split())

    return title[:100]


# ============================================================
# GET DESCRIPTION
# ============================================================

def create_description(video_file):

    title = create_title(video_file)

    description = f"{title}\n\n#reels #facebookreels #viral #shortvideo"

    return description


# ============================================================
# CREATE REEL
# ============================================================

def create_reel():

    url = (
        f"https://graph.facebook.com/"
        f"{API_VERSION}/"
        f"{PAGE_ID}/video_reels"
    )

    data = {
        "access_token": ACCESS_TOKEN,
        "upload_phase": "start"
    }

    response = requests.post(
        url,
        data=data,
        timeout=120
    )

    result = response.json()

    if response.status_code != 200:

        raise Exception(
            f"Create Reel Error:\n{result}"
        )

    video_id = (
        result.get("video_id")
        or result.get("id")
    )

    upload_url = result.get("upload_url")

    if not video_id:

        raise Exception(
            f"No video ID returned:\n{result}"
        )

    if not upload_url:

        upload_url = (
            f"https://rupload.facebook.com/"
            f"video-upload/"
            f"{API_VERSION}/"
            f"{video_id}"
        )

    return video_id, upload_url


# ============================================================
# UPLOAD VIDEO FILE
# ============================================================

def upload_video_file(video_file, video_id, upload_url):

    file_size = video_file.stat().st_size

    headers = {
        "Authorization": f"OAuth {ACCESS_TOKEN}",
        "offset": "0",
        "file_size": str(file_size),
        "Content-Type": "application/octet-stream"
    }

    print("Uploading video file...")

    with open(video_file, "rb") as file:

        response = requests.post(
            upload_url,
            headers=headers,
            data=file,
            timeout=1800
        )

    try:

        result = response.json()

    except Exception:

        result = response.text

    if response.status_code not in [200, 201]:

        raise Exception(
            f"Upload Error:\n{result}"
        )

    print("Video uploaded successfully.")

    return result


# ============================================================
# SCHEDULE REEL
# ============================================================

def schedule_reel(
    video_id,
    title,
    description,
    scheduled_time
):

    url = (
        f"https://graph.facebook.com/"
        f"{API_VERSION}/"
        f"{PAGE_ID}/video_reels"
    )

    # Convert scheduled time to Unix timestamp
    unix_timestamp = int(
        scheduled_time.timestamp()
    )

    data = {

        "access_token": ACCESS_TOKEN,

        "video_id": video_id,

        "upload_phase": "finish",

        "video_state": "SCHEDULED",

        "scheduled_publish_time": unix_timestamp,

        "title": title,

        "description": description
    }

    print("Scheduling Reel...")

    response = requests.post(
        url,
        data=data,
        timeout=120
    )

    try:

        result = response.json()

    except Exception:

        result = response.text


    if response.status_code != 200:

        raise Exception(
            f"Schedule Error:\n{result}"
        )

    # Check Facebook success response
    if isinstance(result, dict):

        if result.get("error"):

            raise Exception(
                f"Facebook Error:\n{result}"
            )

    print("Reel scheduled successfully.")

    return result


# ============================================================
# MOVE VIDEO
# ============================================================

def move_video(video_file, destination_folder):

    destination = (
        destination_folder /
        video_file.name
    )

    # Prevent overwrite
    counter = 1

    original_stem = video_file.stem

    suffix = video_file.suffix


    while destination.exists():

        destination = (
            destination_folder /
            f"{original_stem}_{counter}{suffix}"
        )

        counter += 1


    shutil.move(
        str(video_file),
        str(destination)
    )

    return destination


# ============================================================
# GET VIDEOS
# ============================================================

def get_videos():

    videos = []

    for file in OUTPUT_FOLDER.iterdir():

        if (
            file.is_file()
            and file.suffix.lower()
            in VIDEO_EXTENSIONS
        ):

            videos.append(file)


    # Sort alphabetically
    videos.sort(
        key=lambda x: x.name.lower()
    )

    return videos


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print("\n")

    print("=" * 70)

    print("FACEBOOK REELS SMART SCHEDULER")

    print("=" * 70)

    print(f"Page ID: {PAGE_ID}")

    print(f"API Version: {API_VERSION}")

    print(f"Output Folder: {OUTPUT_FOLDER}")

    print("=" * 70)


    videos = get_videos()


    if not videos:

        print("\nNo videos found.")

        print(
            f"Put videos here:\n{OUTPUT_FOLDER}"
        )

        return


    print(
        f"\nFound {len(videos)} video(s)."
    )


    # --------------------------------------------------------
    # FIND LAST SCHEDULED VIDEO
    # --------------------------------------------------------

    last_scheduled_time = (
        get_last_scheduled_time()
    )


    if last_scheduled_time:

        print(
            "\nLast scheduled Reel:"
        )

        print(
            last_scheduled_time.strftime(
                "%d-%m-%Y %I:%M %p"
            )
        )

    else:

        print(
            "\nNo previous schedule found."
        )

        print(
            "Starting from the next available time."
        )


    print("\n")


    # --------------------------------------------------------
    # PROCESS VIDEOS
    # --------------------------------------------------------

    total = len(videos)


    successful = 0

    failed = 0


    for index, video_file in enumerate(
        videos,
        start=1
    ):

        print("\n")

        print("=" * 70)

        print(
            f"PROCESSING VIDEO {index} OF {total}"
        )

        print("=" * 70)

        print(
            f"File: {video_file.name}"
        )


        try:


            # ------------------------------------------------
            # CALCULATE NEXT SCHEDULE TIME
            # ------------------------------------------------

            scheduled_time = (
                get_next_schedule_time(
                    last_scheduled_time
                )
            )


            print(
                "Scheduled for:"
            )

            print(
                scheduled_time.strftime(
                    "%d-%m-%Y %I:%M %p"
                )
            )


            # ------------------------------------------------
            # CREATE TITLE
            # ------------------------------------------------

            title = create_title(
                video_file
            )


            description = create_description(
                video_file
            )


            # ------------------------------------------------
            # CREATE REEL
            # ------------------------------------------------

            print(
                "\nCreating Facebook Reel..."
            )


            video_id, upload_url = (
                create_reel()
            )


            print(
                f"Video ID: {video_id}"
            )


            # ------------------------------------------------
            # UPLOAD VIDEO
            # ------------------------------------------------

            upload_video_file(

                video_file,

                video_id,

                upload_url

            )


            # ------------------------------------------------
            # SCHEDULE REEL
            # ------------------------------------------------

            schedule_result = (
                schedule_reel(

                    video_id,

                    title,

                    description,

                    scheduled_time

                )
            )


            # ------------------------------------------------
            # SAVE HISTORY
            # ------------------------------------------------

            history = (
                load_schedule_history()
            )


            history.append({

                "filename":
                    video_file.name,

                "video_id":
                    video_id,

                "scheduled_time":
                    scheduled_time.isoformat(),

                "scheduled_timestamp":
                    int(
                        scheduled_time.timestamp()
                    ),

                "title":
                    title,

                "result":
                    schedule_result

            })


            save_schedule_history(
                history
            )


            # ------------------------------------------------
            # UPDATE LAST TIME
            # ------------------------------------------------

            last_scheduled_time = (
                scheduled_time
            )


            # ------------------------------------------------
            # MOVE VIDEO
            # ------------------------------------------------

            move_video(

                video_file,

                UPLOADED_FOLDER

            )


            successful += 1


            print("\n")

            print(
                "SUCCESSFULLY SCHEDULED!"
            )


        except Exception as error:


            print("\n")

            print("=" * 70)

            print("ERROR!")

            print("=" * 70)

            print(error)


            try:

                move_video(

                    video_file,

                    FAILED_FOLDER

                )

                print(
                    "Video moved to failed folder."
                )

            except Exception as move_error:

                print(
                    f"Could not move file: {move_error}"
                )


            failed += 1


        # Small delay between API requests
        time.sleep(2)


    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print("\n")

    print("=" * 70)

    print("FACEBOOK SCHEDULING COMPLETE")

    print("=" * 70)

    print(
        f"Successfully scheduled: {successful}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Remaining videos: {len(get_videos())}"
    )

    print("=" * 70)

    print("\nFacebook now handles the scheduled publishing.")

    print(
        "You can close CMD after the scheduling process finishes."
    )

    print(
        "Your laptop does not need to stay ON for Facebook to publish scheduled videos."
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()