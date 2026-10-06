"""Dữ liệu riêng của web (tài khoản đăng nhập, nhật ký) – lưu file SQLite trong thư mục data.

Web KHÔNG ghi gì vào database NppNguyenQuan.
"""
import hashlib
import hmac
import math
import os
import sqlite3
import threading
from datetime import datetime, timedelta

from . import config

_lock = threading.RLock()

# ---- Quy tắc khóa đăng nhập khi nhập sai mật khẩu nhiều lần ----
#   Từ lần sai thứ 5  -> tạm khóa 20 phút (mỗi lần sai tiếp lại khóa lại 20')
#   Từ lần sai thứ 10 -> tạm khóa 60 phút
#   Từ lần sai thứ 15 -> khóa vĩnh viễn (admin phải mở lại)
KHOA_NGUONG_1, KHOA_PHUT_1 = 5, 20
KHOA_NGUONG_2, KHOA_PHUT_2 = 10, 60
KHOA_VINH_VIEN = 15


def _conn() -> sqlite3.Connection:
    cn = sqlite3.connect(config.app_db_path(), check_same_thread=False)
    cn.row_factory = sqlite3.Row
    return cn


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 200_000)
    return "pbkdf2$" + salt.hex() + "$" + dk.hex()


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt, dk = stored.split("$")
        got = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), 200_000)
        return hmac.compare_digest(got.hex(), dk)
    except Exception:
        return False


def init() -> None:
    with _lock, _conn() as cn:
        cn.executescript(
            """
            CREATE TABLE IF NOT EXISTS nguoi_dung(
                ten_dang_nhap TEXT PRIMARY KEY COLLATE NOCASE,
                ho_ten TEXT NOT NULL DEFAULT '',
                mat_khau TEXT NOT NULL,
                la_admin INTEGER NOT NULL DEFAULT 0,
                nhom TEXT,            -- SY_UserGroup.UserGroupID: quyền menu lấy từ WA_UserGroupPermisstion
                ma_nv TEXT,           -- EmployeeID: nếu có thì chỉ xem dữ liệu của nhân viên này
                dang_dung INTEGER NOT NULL DEFAULT 1,
                ngay_tao TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS nhat_ky(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thoi_gian TEXT NOT NULL,
                nguoi TEXT,
                hanh_dong TEXT,
                chi_tiet TEXT
            );
            CREATE TABLE IF NOT EXISTS dang_nhap_khoa(
                ten_dang_nhap TEXT PRIMARY KEY COLLATE NOCASE,
                so_lan_sai INTEGER NOT NULL DEFAULT 0,
                khoa_den TEXT,              -- tạm khóa đến thời điểm này (NULL = không)
                khoa_vinh_vien INTEGER NOT NULL DEFAULT 0,
                lan_sai_cuoi TEXT
            );
            """
        )
        if cn.execute("SELECT COUNT(*) FROM nguoi_dung").fetchone()[0] == 0:
            cn.execute(
                "INSERT INTO nguoi_dung(ten_dang_nhap, ho_ten, mat_khau, la_admin, ngay_tao) VALUES (?,?,?,1,?)",
                ("admin", "Quản trị", hash_password("admin123"), _now()),
            )


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_user(name: str) -> dict | None:
    with _lock, _conn() as cn:
        r = cn.execute("SELECT * FROM nguoi_dung WHERE ten_dang_nhap = ?", (name,)).fetchone()
        return dict(r) if r else None


def list_users() -> list[dict]:
    with _lock, _conn() as cn:
        rows = cn.execute("SELECT ten_dang_nhap, ho_ten, la_admin, nhom, ma_nv, dang_dung, ngay_tao FROM nguoi_dung ORDER BY ten_dang_nhap").fetchall()
        return [dict(r) for r in rows]


def save_user(u: dict, password: str | None) -> None:
    with _lock, _conn() as cn:
        old = cn.execute("SELECT 1 FROM nguoi_dung WHERE ten_dang_nhap = ?", (u["ten_dang_nhap"],)).fetchone()
        if old:
            cn.execute(
                "UPDATE nguoi_dung SET ho_ten=?, la_admin=?, nhom=?, ma_nv=?, dang_dung=? WHERE ten_dang_nhap=?",
                (u["ho_ten"], int(u["la_admin"]), u.get("nhom") or None, u.get("ma_nv") or None, int(u["dang_dung"]), u["ten_dang_nhap"]),
            )
            if password:
                cn.execute("UPDATE nguoi_dung SET mat_khau=? WHERE ten_dang_nhap=?", (hash_password(password), u["ten_dang_nhap"]))
        else:
            if not password:
                raise ValueError("Tài khoản mới phải có mật khẩu")
            cn.execute(
                "INSERT INTO nguoi_dung(ten_dang_nhap, ho_ten, mat_khau, la_admin, nhom, ma_nv, dang_dung, ngay_tao) VALUES (?,?,?,?,?,?,?,?)",
                (u["ten_dang_nhap"], u["ho_ten"], hash_password(password), int(u["la_admin"]), u.get("nhom") or None,
                 u.get("ma_nv") or None, int(u["dang_dung"]), _now()),
            )


def set_password(name: str, password: str) -> None:
    with _lock, _conn() as cn:
        cn.execute("UPDATE nguoi_dung SET mat_khau=? WHERE ten_dang_nhap=?", (hash_password(password), name))


def delete_user(name: str) -> None:
    with _lock, _conn() as cn:
        cn.execute("DELETE FROM nguoi_dung WHERE ten_dang_nhap=?", (name,))


def count_admins(exclude: str | None = None) -> int:
    with _lock, _conn() as cn:
        return cn.execute(
            "SELECT COUNT(*) FROM nguoi_dung WHERE la_admin=1 AND dang_dung=1 AND ten_dang_nhap <> ?", (exclude or "",)
        ).fetchone()[0]


def log(user: str | None, action: str, detail: str = "") -> None:
    with _lock, _conn() as cn:
        cn.execute("INSERT INTO nhat_ky(thoi_gian, nguoi, hanh_dong, chi_tiet) VALUES (?,?,?,?)", (_now(), user, action, detail[:1000]))


def logs(tu: str, den: str, nguoi: str = "") -> list[dict]:
    with _lock, _conn() as cn:
        rows = cn.execute(
            "SELECT thoi_gian, nguoi, hanh_dong, chi_tiet FROM nhat_ky WHERE substr(thoi_gian,1,10) BETWEEN ? AND ? "
            "AND (? = '' OR nguoi = ?) ORDER BY id DESC LIMIT 2000",
            (tu, den, nguoi, nguoi),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------- khóa đăng nhập
def _parse(ts: str | None) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") if ts else None
    except Exception:
        return None


def kiem_khoa(name: str) -> dict:
    """Trạng thái khóa hiện tại của 1 tên đăng nhập.
    Trả về {bi_khoa, vinh_vien, con_phut, thong_bao}."""
    name = (name or "").strip()
    with _lock, _conn() as cn:
        r = cn.execute("SELECT * FROM dang_nhap_khoa WHERE ten_dang_nhap = ?", (name,)).fetchone()
    if not r:
        return {"bi_khoa": False, "vinh_vien": False, "con_phut": 0, "thong_bao": ""}
    if r["khoa_vinh_vien"]:
        return {"bi_khoa": True, "vinh_vien": True, "con_phut": 0,
                "thong_bao": "Tài khoản đã bị khóa do nhập sai mật khẩu quá nhiều lần. Vui lòng liên hệ quản trị để mở khóa."}
    den = _parse(r["khoa_den"])
    if den and datetime.now() < den:
        con = max(1, math.ceil((den - datetime.now()).total_seconds() / 60))
        return {"bi_khoa": True, "vinh_vien": False, "con_phut": con,
                "thong_bao": f"Tài khoản đang tạm khóa. Vui lòng thử lại sau {con} phút."}
    return {"bi_khoa": False, "vinh_vien": False, "con_phut": 0, "thong_bao": ""}


def ghi_that_bai(name: str) -> dict:
    """Ghi nhận 1 lần đăng nhập sai, áp dụng khóa theo ngưỡng. Trả về trạng thái mới."""
    name = (name or "").strip()
    now = _now()
    with _lock, _conn() as cn:
        r = cn.execute("SELECT so_lan_sai FROM dang_nhap_khoa WHERE ten_dang_nhap = ?", (name,)).fetchone()
        n = (r["so_lan_sai"] if r else 0) + 1
        khoa_den = None
        vinh_vien = 0
        if n >= KHOA_VINH_VIEN:
            vinh_vien = 1
        elif n >= KHOA_NGUONG_2:
            khoa_den = (datetime.now() + timedelta(minutes=KHOA_PHUT_2)).strftime("%Y-%m-%d %H:%M:%S")
        elif n >= KHOA_NGUONG_1:
            khoa_den = (datetime.now() + timedelta(minutes=KHOA_PHUT_1)).strftime("%Y-%m-%d %H:%M:%S")
        cn.execute(
            "INSERT INTO dang_nhap_khoa(ten_dang_nhap, so_lan_sai, khoa_den, khoa_vinh_vien, lan_sai_cuoi) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT(ten_dang_nhap) DO UPDATE SET so_lan_sai=excluded.so_lan_sai, khoa_den=excluded.khoa_den, "
            "khoa_vinh_vien=excluded.khoa_vinh_vien, lan_sai_cuoi=excluded.lan_sai_cuoi",
            (name, n, khoa_den, vinh_vien, now),
        )
    return {"so_lan_sai": n, "khoa_den": khoa_den, "vinh_vien": bool(vinh_vien)}


def reset_that_bai(name: str) -> None:
    """Xóa đếm sai khi đăng nhập đúng."""
    name = (name or "").strip()
    with _lock, _conn() as cn:
        cn.execute("DELETE FROM dang_nhap_khoa WHERE ten_dang_nhap = ?", (name,))


def mo_khoa(name: str) -> None:
    """Admin mở khóa 1 tài khoản (xóa đếm sai + bỏ khóa)."""
    reset_that_bai(name)


def ds_khoa() -> list[dict]:
    """Danh sách tài khoản đang bị khóa (tạm hoặc vĩnh viễn) để admin xem/mở."""
    out = []
    with _lock, _conn() as cn:
        rows = cn.execute("SELECT * FROM dang_nhap_khoa ORDER BY lan_sai_cuoi DESC").fetchall()
    for r in rows:
        st = kiem_khoa(r["ten_dang_nhap"])
        if st["bi_khoa"]:
            out.append({"ten_dang_nhap": r["ten_dang_nhap"], "so_lan_sai": r["so_lan_sai"],
                        "vinh_vien": st["vinh_vien"], "con_phut": st["con_phut"], "lan_sai_cuoi": r["lan_sai_cuoi"]})
    return out
