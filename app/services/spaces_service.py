import boto3
import os

session = boto3.session.Session()

s3 = session.client(
    "s3",
    region_name=os.getenv("SPACES_REGION"),
    endpoint_url=os.getenv("SPACES_ENDPOINT"),
    aws_access_key_id=os.getenv("SPACES_KEY"),
    aws_secret_access_key=os.getenv("SPACES_SECRET"),
)

BUCKET = os.getenv("SPACES_NAME")
CDN_URL = os.getenv("SPACES_CDN_URL")
BASE_PATH = (os.getenv("DO_SPACES_BASE_PATH") or "fitness_app").strip("/")

# EXACT category mapping based on your DigitalOcean folders
CATEGORY_MAP = {
    "newarms": "NewArms",
    "newcore": "NewCore",
    "newfullbody": "NewFullBody",
    "newlegs": "NewLegs"
}


def normalize_category(cat: str):
    """Convert user category to correct folder name"""
    key = cat.replace(" ", "").replace("-", "").lower()
    return CATEGORY_MAP.get(key)


def _join_path(*segments: str) -> str:
    cleaned = [segment.strip("/") for segment in segments if segment and segment.strip("/")]
    return "/".join(cleaned)


def get_videos_by_category(category: str):
    real_category = normalize_category(category)

    if not real_category:
        print("❌ Invalid category:", category)
        return []

    prefix_root = _join_path(BASE_PATH, real_category)
    prefix = f"{prefix_root}/" if prefix_root else ""

    print("📌 DEBUG PREFIX:", prefix)

    response = s3.list_objects_v2(
        Bucket=BUCKET,
        Prefix=prefix
    )

    if "Contents" not in response:
        print("⚠️ No files for:", prefix)
        return []

    urls = [
        f"{CDN_URL}/{obj['Key']}"
        for obj in response["Contents"]
        if obj["Key"].lower().endswith(".mp4")
    ]

    return urls


def _upload_file(data: bytes, key: str, content_type: str | None = None) -> str:
    extra_args = {"ACL": "public-read"}
    if content_type:
        extra_args["ContentType"] = content_type

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=data,
        **extra_args
    )
    return f"{CDN_URL}/{key}"


def _build_key(body_part: str, filename: str, subfolder: str | None = None) -> str:
    parts = [BASE_PATH, body_part]
    if subfolder:
        parts.append(subfolder)
    parts.append(filename)
    return _join_path(*parts)


def upload_category_video(data: bytes, filename: str, body_part: str, content_type: str | None = None) -> str:
    key = _build_key(body_part, filename)
    return _upload_file(data, key, content_type)


def upload_category_thumbnail(data: bytes, filename: str, body_part: str, content_type: str | None = None) -> str:
    key = _build_key(body_part, filename, subfolder="thumbnails")
    return _upload_file(data, key, content_type)
