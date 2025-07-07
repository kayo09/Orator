import os
from typing import Optional

try:
    from supabase import create_client, Client
except Exception:  # library optional
    create_client = None  # type: ignore
    Client = object  # type: ignore

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "orator")

def supabase_enabled() -> bool:
    return bool(create_client and SUPABASE_URL and SUPABASE_KEY)

def get_client() -> Optional["Client"]:
    if not supabase_enabled():
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)  # type: ignore

def upload_audio_to_supabase(file_path: str, dest_name: str) -> Optional[str]:
    client = get_client()
    if not client:
        return None
    with open(file_path, "rb") as f:
        client.storage.from_(SUPABASE_BUCKET).upload(dest_name, f, {
            "content-type": "audio/wav",
        })
    return dest_name
