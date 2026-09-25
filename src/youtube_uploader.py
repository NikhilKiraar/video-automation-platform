import os
import csv
import time as time_module
import shutil
from pathlib import Path
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# ============================================================
# YOUTUBE SMART AUTO UPLOADER + SCHEDULER
# ============================================================

# ------------------------------------------------------------
# PROJECT SETTINGS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# Your split videos are created here
SOURCE_FOLDER = BASE_DIR / "output"

# Platform-specific folders
PROCESSING_FOLDER = BASE_DIR / "processing" / "youtube"

UPLOADED_FOLDER = BASE_DIR / "Uploaded" / "youtube"

FAILED_FOLDER = BASE_DIR / "failed" / "youtube"

LOG_FILE = BASE_DIR / "youtube_upload_log.csv"

CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"

TOKEN_FILE = BASE_DIR / "youtube_token.json"


# ------------------------------------------------------------
# TIMEZONE
# ------------------------------------------------------------

TIMEZONE = ZoneInfo("Asia/Kolkata")


# ------------------------------------------------------------
# DAILY YOUTUBE SCHEDULE
#
# 7 VIDEOS PER DAY
# ------------------------------------------------------------

DAILY_TIMES = [

    time(7, 0),    # 07:00 AM
    time(10, 0),   # 10:00 AM
    time(13, 0),   # 01:00 PM
    time(16, 0),   # 04:00 PM
    time(19, 0),   # 07:00 PM
    time(21, 0),   # 09:00 PM
    time(23, 0),   # 11:00 PM

]


# ------------------------------------------------------------
# VIDEO EXTENSIONS
# ------------------------------------------------------------

VIDEO_EXTENSIONS = {

    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".wmv",
    ".m4v"

}


# ------------------------------------------------------------
# YOUTUBE API
#
# youtube.upload = upload videos
# youtube.readonly = check existing scheduled videos
# ------------------------------------------------------------

SCOPES = [

    "https://www.googleapis.com/auth/youtube.upload",

    "https://www.googleapis.com/auth/youtube.readonly"

]


API_SERVICE_NAME = "youtube"

API_VERSION = "v3"


# ============================================================
# CREATE REQUIRED FOLDERS
# ============================================================

def create_folders():

    folders = [

        SOURCE_FOLDER,

        PROCESSING_FOLDER,

        UPLOADED_FOLDER,

        FAILED_FOLDER

    ]

    for folder in folders:

        folder.mkdir(

            parents=True,

            exist_ok=True

        )


# ============================================================
# CREATE LOG FILE
# ============================================================

def create_log_file():

    if not LOG_FILE.exists():

        with open(

            LOG_FILE,

            "w",

            newline="",

            encoding="utf-8"

        ) as file:

            writer = csv.writer(file)

            writer.writerow([

                "date_time",

                "file_name",

                "youtube_video_id",

                "scheduled_time",

                "status",

                "error"

            ])


# ============================================================
# WRITE LOG
# ============================================================

def write_log(

    file_name,

    video_id,

    scheduled_time,

    status,

    error=""

):

    with open(

        LOG_FILE,

        "a",

        newline="",

        encoding="utf-8"

    ) as file:

        writer = csv.writer(file)

        writer.writerow([

            datetime.now(TIMEZONE).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            file_name,

            video_id,

            scheduled_time,

            status,

            error

        ])


# ============================================================
# AUTHENTICATE YOUTUBE
# ============================================================

def authenticate_youtube():

    credentials = None


    # --------------------------------------------------------
    # LOAD SAVED TOKEN
    # --------------------------------------------------------

    if TOKEN_FILE.exists():

        try:

            credentials = Credentials.from_authorized_user_file(

                str(TOKEN_FILE),

                SCOPES

            )

        except Exception as error:

            print()

            print("Saved token problem:")

            print(error)

            credentials = None


    # --------------------------------------------------------
    # REFRESH TOKEN
    # --------------------------------------------------------

    if credentials and credentials.expired:

        if credentials.refresh_token:

            try:

                credentials.refresh(

                    Request()

                )

            except Exception as error:

                print()

                print("Token refresh failed:")

                print(error)

                credentials = None


    # --------------------------------------------------------
    # LOGIN AGAIN IF REQUIRED
    # --------------------------------------------------------

    if not credentials or not credentials.valid:

        print()

        print("=" * 60)

        print("GOOGLE / YOUTUBE LOGIN REQUIRED")

        print("=" * 60)

        print()

        print(
            "A browser window will open."
        )

        print(
            "Login with the YouTube channel you want to use."
        )

        print()

        flow = InstalledAppFlow.from_client_secrets_file(

            str(CLIENT_SECRET_FILE),

            SCOPES

        )

        credentials = flow.run_local_server(

            port=0

        )


    # --------------------------------------------------------
    # SAVE TOKEN
    # --------------------------------------------------------

    with open(

        TOKEN_FILE,

        "w",

        encoding="utf-8"

    ) as token:

        token.write(

            credentials.to_json()

        )


    # --------------------------------------------------------
    # CREATE YOUTUBE CONNECTION
    # --------------------------------------------------------

    youtube = build(

        API_SERVICE_NAME,

        API_VERSION,

        credentials=credentials

    )


    return youtube


# ============================================================
# GET VIDEO FILES
# ============================================================

def get_videos():

    videos = []


    for file in SOURCE_FOLDER.iterdir():

        if file.is_file():

            if file.suffix.lower() in VIDEO_EXTENSIONS:

                videos.append(file)


    # Sort alphabetically
    videos.sort(

        key=lambda x: x.name.lower()

    )


    return videos


# ============================================================
# CREATE TITLE
# ============================================================

def create_title(video_file):

    title = video_file.stem


    # Replace separators
    title = title.replace(

        "_",

        " "

    )

    title = title.replace(

        "-",

        " "

    )


    # Remove extra spaces
    title = " ".join(

        title.split()

    )


    # Add Shorts
    if "#Shorts" not in title:

        title += " #Shorts"


    # YouTube maximum title length = 100 characters
    title = title[:100]


    return title


# ============================================================
# CREATE DESCRIPTION
# ============================================================

def create_description(video_file):

    clean_name = video_file.stem

    clean_name = clean_name.replace(

        "_",

        " "

    )

    clean_name = clean_name.replace(

        "-",

        " "

    )


    description = (

        f"{clean_name}\n\n"

        "Watch till the end! 🔥\n\n"

        "Like 👍\n"
        "Share 📤\n"
        "Subscribe ❤️\n\n"

        "#Shorts "
        "#YouTubeShorts "
        "#Viral "
        "#Trending"

    )


    return description


# ============================================================
# CREATE TAGS
# ============================================================

def create_tags(video_file):

    tags = [

        "shorts",

        "youtube shorts",

        "viral shorts",

        "trending",

        "short video"

    ]


    # Get words from filename
    words = (

        video_file.stem

        .lower()

        .replace("_", " ")

        .replace("-", " ")

        .split()

    )


    for word in words:

        # Ignore very short words
        if len(word) > 2:

            if word not in tags:

                tags.append(

                    word

                )


    # Limit tags
    return tags[:15]


# ============================================================
# GET CHANNEL UPLOADS PLAYLIST
# ============================================================

def get_uploads_playlist_id(youtube):

    response = youtube.channels().list(

        part="contentDetails",

        mine=True

    ).execute()


    items = response.get(

        "items",

        []

    )


    if not items:

        raise Exception(

            "No YouTube channel found."

        )


    uploads_playlist_id = (

        items[0]

        ["contentDetails"]

        ["relatedPlaylists"]

        ["uploads"]

    )


    return uploads_playlist_id


# ============================================================
# GET LATEST SCHEDULED VIDEO DATE
#
# This checks existing videos on your channel.
# ============================================================

def get_latest_scheduled_datetime(youtube):

    print()

    print("=" * 60)

    print("CHECKING EXISTING YOUTUBE SCHEDULE")

    print("=" * 60)


    uploads_playlist_id = (

        get_uploads_playlist_id(

            youtube

        )

    )


    latest_scheduled_time = None


    next_page_token = None


    checked_videos = 0


    while True:

        playlist_response = (

            youtube.playlistItems().list(

                part="contentDetails",

                playlistId=uploads_playlist_id,

                maxResults=50,

                pageToken=next_page_token

            ).execute()

        )


        video_ids = []


        for item in playlist_response.get(

            "items",

            []

        ):

            video_id = (

                item

                ["contentDetails"]

                .get("videoId")

            )


            if video_id:

                video_ids.append(

                    video_id

                )


        if video_ids:

            videos_response = (

                youtube.videos().list(

                    part="status",

                    id=",".join(video_ids)

                ).execute()

            )


            for video in videos_response.get(

                "items",

                []

            ):


                checked_videos += 1


                status = (

                    video.get(

                        "status",

                        {}

                    )

                )


                publish_at = (

                    status.get(

                        "publishAt"

                    )

                )


                privacy_status = (

                    status.get(

                        "privacyStatus"

                    )

                )


                # Scheduled videos are normally private
                # and have a future publishAt time
                if publish_at:


                    try:

                        publish_datetime = (

                            datetime.fromisoformat(

                                publish_at.replace(

                                    "Z",

                                    "+00:00"

                                )

                            )

                        )


                        publish_datetime = (

                            publish_datetime.astimezone(

                                TIMEZONE

                            )

                        )


                        now = (

                            datetime.now(

                                TIMEZONE

                            )

                        )


                        if publish_datetime > now:


                            if (

                                latest_scheduled_time

                                is None

                            ):


                                latest_scheduled_time = (

                                    publish_datetime

                                )


                            elif (

                                publish_datetime

                                >

                                latest_scheduled_time

                            ):


                                latest_scheduled_time = (

                                    publish_datetime

                                )


                    except Exception:

                        pass


        next_page_token = (

            playlist_response.get(

                "nextPageToken"

            )

        )


        # Stop when no more pages
        if not next_page_token:

            break


        # Safety limit
        if checked_videos >= 500:

            break


    if latest_scheduled_time:


        print()

        print(

            "Latest scheduled video found:"

        )

        print(

            latest_scheduled_time.strftime(

                "%d-%m-%Y %I:%M %p"

            )

        )


    else:


        print()

        print(

            "No future scheduled videos found."

        )


    return latest_scheduled_time


# ============================================================
# FIND START DATE FOR NEW VIDEOS
#
# Example:
#
# Existing schedule ends:
# 12 September
#
# New videos start:
# 13 September
# ============================================================

def get_start_date(youtube):

    latest_scheduled = (

        get_latest_scheduled_datetime(

            youtube

        )

    )


    today = (

        datetime.now(

            TIMEZONE

        ).date()

    )


    # --------------------------------------------------------
    # IF EXISTING SCHEDULE FOUND
    # --------------------------------------------------------

    if latest_scheduled:


        start_date = (

            latest_scheduled.date()

            + timedelta(days=1)

        )


        print()

        print(

            "New videos will start from:"

        )

        print(

            start_date.strftime(

                "%d-%m-%Y"

            )

        )


        return start_date


    # --------------------------------------------------------
    # NO EXISTING FUTURE SCHEDULE
    # --------------------------------------------------------

    tomorrow = (

        today

        + timedelta(days=1)

    )


    print()

    print(

        "Starting new schedule from:"

    )

    print(

        tomorrow.strftime(

            "%d-%m-%Y"

        )

    )


    return tomorrow


# ============================================================
# CREATE SCHEDULE
# ============================================================

def create_schedule(

    video_count,

    start_date

):

    schedule = []


    current_date = start_date


    video_number = 0


    while video_number < video_count:


        # ----------------------------------------------------
        # ADD DAILY TIMES
        # ----------------------------------------------------

        for publish_time in DAILY_TIMES:


            if video_number >= video_count:

                break


            scheduled_datetime = (

                datetime.combine(

                    current_date,

                    publish_time,

                    tzinfo=TIMEZONE

                )

            )


            schedule.append(

                scheduled_datetime

            )


            video_number += 1


        # ----------------------------------------------------
        # NEXT DAY
        # ----------------------------------------------------

        current_date = (

            current_date

            + timedelta(days=1)

        )


    return schedule


# ============================================================
# CONVERT TO YOUTUBE UTC TIME
# ============================================================

def convert_to_utc_iso(scheduled_datetime):

    utc_datetime = (

        scheduled_datetime.astimezone(

            ZoneInfo("UTC")

        )

    )


    return (

        utc_datetime.strftime(

            "%Y-%m-%dT%H:%M:%SZ"

        )

    )


# ============================================================
# SAFE MOVE VIDEO
# ============================================================

def move_video(

    video_path,

    destination_folder

):

    destination = (

        destination_folder

        / video_path.name

    )


    # Avoid duplicate names
    if destination.exists():


        timestamp = (

            datetime.now(

                TIMEZONE

            ).strftime(

                "%Y%m%d_%H%M%S"

            )

        )


        destination = (

            destination_folder

            /

            f"{video_path.stem}"

            f"_{timestamp}"

            f"{video_path.suffix}"

        )


    shutil.move(

        str(video_path),

        str(destination)

    )


    return destination


# ============================================================
# UPLOAD VIDEO
# ============================================================

def upload_video(

    youtube,

    video_path,

    scheduled_datetime

):

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    title = (

        create_title(

            video_path

        )

    )


    description = (

        create_description(

            video_path

        )

    )


    tags = (

        create_tags(

            video_path

        )

    )


    publish_time_utc = (

        convert_to_utc_iso(

            scheduled_datetime

        )

    )


    print()

    print("=" * 65)

    print("UPLOADING VIDEO")

    print("=" * 65)


    print(

        "File:",

        video_path.name

    )


    print(

        "Title:",

        title

    )


    print(

        "Scheduled IST:",

        scheduled_datetime.strftime(

            "%d-%m-%Y %I:%M %p"

        )

    )


    print(

        "Scheduled UTC:",

        publish_time_utc

    )


    # --------------------------------------------------------
    # YOUTUBE DATA
    # --------------------------------------------------------

    body = {

        "snippet": {

            "title":

                title,

            "description":

                description,

            "tags":

                tags,

            "categoryId":

                "24"

        },


        "status": {

            # Required for scheduling
            "privacyStatus":

                "private",

            "publishAt":

                publish_time_utc,

            "selfDeclaredMadeForKids":

                False

        }

    }


    # --------------------------------------------------------
    # VIDEO FILE
    # --------------------------------------------------------

    media = MediaFileUpload(

        str(video_path),

        mimetype="video/*",

        resumable=True,

        chunksize=-1

    )


    request = (

        youtube.videos().insert(

            part="snippet,status",

            body=body,

            media_body=media

        )

    )


    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    response = None


    while response is None:


        status, response = (

            request.next_chunk()

        )


        if status:


            progress = int(

                status.progress()

                * 100

            )


            print(

                f"Upload Progress: "

                f"{progress}%"

            )


    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    if response:


        video_id = (

            response.get(

                "id"

            )

        )


        return (

            True,

            video_id

        )


    return (

        False,

        None

    )


# ============================================================
# SHOW SCHEDULE PLAN
# ============================================================

def show_schedule_plan(

    videos,

    schedule

):

    print()

    print("=" * 70)

    print("NEW YOUTUBE SCHEDULING PLAN")

    print("=" * 70)


    for index, video in enumerate(videos):


        scheduled_time = (

            schedule[index]

        )


        print()

        print(

            f"{index + 1}. "

            f"{video.name}"

        )


        print(

            "   Publish:",

            scheduled_time.strftime(

                "%d-%m-%Y %I:%M %p"

            )

        )


    print()

    print("=" * 70)


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    # --------------------------------------------------------
    # CREATE FOLDERS
    # --------------------------------------------------------

    create_folders()


    # --------------------------------------------------------
    # CREATE LOG
    # --------------------------------------------------------

    create_log_file()


    # --------------------------------------------------------
    # START MESSAGE
    # --------------------------------------------------------

    print()

    print("=" * 70)

    print("YOUTUBE SMART AUTO UPLOADER + SCHEDULER")

    print("=" * 70)


    print()

    print(

        "Source Folder:"

    )

    print(

        SOURCE_FOLDER

    )


    print()

    print(

        "Videos Per Day:"

    )

    print(

        len(

            DAILY_TIMES

        )

    )


    print()

    print(

        "Timezone:"

    )

    print(

        "Asia/Kolkata"

    )


    # --------------------------------------------------------
    # CHECK CLIENT SECRET
    # --------------------------------------------------------

    if not CLIENT_SECRET_FILE.exists():

        print()

        print("ERROR!")

        print(

            "client_secret.json not found."

        )

        print()

        print(

            "Put it inside:"

        )

        print(

            BASE_DIR

        )

        return


    # --------------------------------------------------------
    # FIND VIDEOS
    # --------------------------------------------------------

    videos = (

        get_videos()

    )


    if not videos:


        print()

        print(

            "NO VIDEOS FOUND."

        )


        print()

        print(

            "Put videos inside:"

        )

        print(

            SOURCE_FOLDER

        )

        return


    print()

    print(

        f"Found {len(videos)} new videos."

    )


    # --------------------------------------------------------
    # CONNECT TO YOUTUBE
    # --------------------------------------------------------

    print()

    print(

        "Connecting to YouTube..."

    )


    youtube = (

        authenticate_youtube()

    )


    print(

        "YouTube connected successfully."

    )


    # --------------------------------------------------------
    # FIND START DATE
    # --------------------------------------------------------

    start_date = (

        get_start_date(

            youtube

        )

    )


    # --------------------------------------------------------
    # CREATE NEW SCHEDULE
    # --------------------------------------------------------

    schedule = (

        create_schedule(

            len(videos),

            start_date

        )

    )


    # --------------------------------------------------------
    # SHOW PLAN
    # --------------------------------------------------------

    show_schedule_plan(

        videos,

        schedule

    )


    # --------------------------------------------------------
    # CONFIRM
    # --------------------------------------------------------

    confirmation = input(

        "\nType YES to upload and "

        "schedule these videos: "

    ).strip()


    if confirmation.upper() != "YES":


        print()

        print(

            "UPLOAD CANCELLED."

        )

        return


    # --------------------------------------------------------
    # COUNTERS
    # --------------------------------------------------------

    success_count = 0

    failed_count = 0


    # --------------------------------------------------------
    # PROCESS ALL VIDEOS
    # --------------------------------------------------------

    for index, video in enumerate(videos):


        scheduled_time = (

            schedule[index]

        )


        print()

        print("#" * 70)

        print(

            f"VIDEO "

            f"{index + 1} "

            f"OF "

            f"{len(videos)}"

        )

        print("#" * 70)


        processing_path = (

            PROCESSING_FOLDER

            / video.name

        )


        try:


            # ------------------------------------------------
            # MOVE TO PROCESSING
            # ------------------------------------------------

            shutil.move(

                str(video),

                str(processing_path)

            )


            # ------------------------------------------------
            # UPLOAD
            # ------------------------------------------------

            success, video_id = (

                upload_video(

                    youtube,

                    processing_path,

                    scheduled_time

                )

            )


            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            if success:


                print()

                print("SUCCESS!")

                print(

                    "YouTube Video ID:",

                    video_id

                )


                print(

                    "Scheduled:",

                    scheduled_time.strftime(

                        "%d-%m-%Y %I:%M %p"

                    )

                )


                moved_file = (

                    move_video(

                        processing_path,

                        UPLOADED_FOLDER

                    )

                )


                # Write log
                write_log(

                    file_name=

                        moved_file.name,

                    video_id=

                        video_id,

                    scheduled_time=

                        scheduled_time.strftime(

                            "%Y-%m-%d %H:%M:%S"

                        ),

                    status=

                        "SUCCESS"

                )


                success_count += 1


                print()

                print(

                    "Moved to:"

                )

                print(

                    UPLOADED_FOLDER

                )


            # ------------------------------------------------
            # FAILED
            # ------------------------------------------------

            else:


                if processing_path.exists():


                    moved_file = (

                        move_video(

                            processing_path,

                            FAILED_FOLDER

                        )

                    )


                    write_log(

                        file_name=

                            moved_file.name,

                        video_id=

                            "",

                        scheduled_time=

                            scheduled_time.strftime(

                                "%Y-%m-%d %H:%M:%S"

                            ),

                        status=

                            "FAILED",

                        error=

                            "Unknown upload error"

                    )


                failed_count += 1


        except HttpError as error:


            print()

            print("YOUTUBE API ERROR:")

            print(error)


            if processing_path.exists():


                moved_file = (

                    move_video(

                        processing_path,

                        FAILED_FOLDER

                    )

                )


                write_log(

                    file_name=

                        moved_file.name,

                    video_id=

                        "",

                    scheduled_time=

                        scheduled_time.strftime(

                            "%Y-%m-%d %H:%M:%S"

                        ),

                    status=

                        "FAILED",

                    error=

                        str(error)

                )


            failed_count += 1


        except Exception as error:


            print()

            print("ERROR:")

            print(error)


            if processing_path.exists():


                moved_file = (

                    move_video(

                        processing_path,

                        FAILED_FOLDER

                    )

                )


                write_log(

                    file_name=

                        moved_file.name,

                    video_id=

                        "",

                    scheduled_time=

                        scheduled_time.strftime(

                            "%Y-%m-%d %H:%M:%S"

                        ),

                    status=

                        "FAILED",

                    error=

                        str(error)

                )


            failed_count += 1


    # --------------------------------------------------------
    # FINISHED
    # --------------------------------------------------------

    print()

    print("=" * 70)

    print("YOUTUBE UPLOAD SESSION COMPLETE")

    print("=" * 70)


    print()

    print(

        "Successfully Scheduled:",

        success_count

    )


    print(

        "Failed:",

        failed_count

    )


    print()

    print(

        "Upload Log:"

    )

    print(

        LOG_FILE

    )


    print()

    print(

        "You can now close CMD."

    )


    print(

        "YouTube will publish videos "

        "at their scheduled times."

    )


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":

    main()