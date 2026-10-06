"""Dữ liệu riêng của web (tài khoản đăng nhập, nhật ký) – lưu file SQLite trong thư mục data.

Web KHÔNG ghi gì vào database NppNguyenQuan.
"""
import hashlib
import hmac
import os
import sqlite3
import threading
from datetime import datetime

from . import config

_lock = threading.RLock()


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
