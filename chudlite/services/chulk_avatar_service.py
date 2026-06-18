from pathlib import Path

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
DEFAULT_CHULK_AVATAR = "chulk-default.svg"


def _avatar_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "static" / "chulk_avatars"


def list_chulk_avatar_files() -> list[str]:
    avatar_dir = _avatar_dir()
    if not avatar_dir.exists():
        return [DEFAULT_CHULK_AVATAR]

    files: list[str] = []
    for item in avatar_dir.iterdir():
        if not item.is_file() or item.name.startswith("."):
            continue
        if item.suffix.lower() in ALLOWED_EXTENSIONS:
            files.append(item.name)

    files = sorted(files, key=str.lower)

    if DEFAULT_CHULK_AVATAR in files:
        files.remove(DEFAULT_CHULK_AVATAR)
        files.insert(0, DEFAULT_CHULK_AVATAR)

    if not files:
        return [DEFAULT_CHULK_AVATAR]
    return files


def sanitize_chulk_avatar_choice(choice: str | None, available_files: list[str]) -> str:
    if choice and choice in available_files:
        return choice
    if DEFAULT_CHULK_AVATAR in available_files:
        return DEFAULT_CHULK_AVATAR
    return available_files[0]


def build_chulk_avatar_url(file_name: str) -> str:
    return f"/static/chulk_avatars/{file_name}"
