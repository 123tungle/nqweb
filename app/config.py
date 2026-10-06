"""Đọc cấu hình từ config.ini (đặt cạnh thư mục app). Biến môi trường NQWEB_<SECTION>_<KEY> ghi đè."""
import configparser
import os
import secrets
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = Path(os.environ.get("NQWEB_CONFIG", BASE_DIR / "config.ini"))

_cfg = configparser.ConfigParser(interpolation=None)  # mật khẩu có dấu % vẫn đọc đúng
if CONFIG_FILE.exists():
    _cfg.read(CONFIG_FILE, encoding="utf-8")


def get(section: str, key: str, default: str = "") -> str:
    env = os.environ.get(f"NQWEB_{section}_{key}".upper())
    if env is not None:
        return env
    return _cfg.get(section, key, fallback=default)


def get_bool(section: str, key: str, default: bool = False) -> bool:
    return get(section, key, "true" if default else "false").strip().lower() in ("1", "true", "yes", "co", "có")


def erp_url() -> str:
    """Chuỗi kết nối tới database phần mềm bán hàng (NppNguyenQuan).

    type = mssql (dùng thật) | sqlite (chỉ để chạy test tự động)
    """
    kind = get("database", "type", "mssql").lower()
    if kind == "sqlite":
        return "sqlite:///" + get("database", "path", str(BASE_DIR / "data" / "erp_test.sqlite3"))
    server = get("database", "server", r"LTT\SQL2016")
    db = get("database", "database", "NppNguyenQuan")
    driver = get("database", "driver", "ODBC Driver 17 for SQL Server")
    user = get("database", "user", "")
    pwd = get("database", "password", "")
    parts = [f"DRIVER={{{driver}}}", f"SERVER={server}", f"DATABASE={db}", "APP=NQWeb"]
    if user:
        # Bọc {…} để mật khẩu có ký tự đặc biệt (; = { } @ …) vẫn đúng
        brace = lambda v: "{" + v.replace("}", "}}") + "}"  # noqa: E731
        parts += [f"UID={brace(user)}", f"PWD={brace(pwd)}"]
    else:
        parts.append("Trusted_Connection=yes")
    extra = get("database", "extra", "TrustServerCertificate=yes")
    if extra:
        parts.append(extra)
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(";".join(parts) + ";")


def app_db_path() -> Path:
    p = Path(get("app", "app_db", str(BASE_DIR / "data" / "nqweb_app.sqlite3")))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def secret_key() -> str:
    key = get("app", "secret_key", "")
    if key:
        return key
    f = BASE_DIR / "data" / ".secret_key"
    f.parent.mkdir(parents=True, exist_ok=True)
    if not f.exists():
        f.write_text(secrets.token_hex(32), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


COMPANY = get("app", "company", "NGUYÊN QUÂN")
COMPANY_SUB = get("app", "company_sub", "Công ty TNHH TM DV Nguyên Quân")
MAX_ROWS = int(get("app", "max_rows", "5000"))
QUERY_TIMEOUT = int(get("app", "query_timeout", "120"))
SHOW_DISABLED_MENU = get_bool("app", "hien_menu_dang_tat", False)
