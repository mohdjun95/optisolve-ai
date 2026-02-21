import os
import pathlib
from dotenv import load_dotenv

# Load .env if it exists
_dotenv_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    load_dotenv(dotenv_path=_dotenv_path)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

AVAILABLE_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

MAX_UPLOAD_SIZE_MB = 50

ALLOWED_EXTENSIONS = {
    ".pdf", ".txt", ".docx", ".doc",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif",
    ".xlsx", ".xls", ".csv",
}
