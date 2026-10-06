"""Kiểm tra kết nối SQL Server, tự chọn driver ODBC, đọc thử menu web. Không ghi gì vào database."""
import configparser
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG = BASE / "config.ini"
DRIVERS = ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "ODBC Driver 13.1 for SQL Server",
           "ODBC Driver 13 for SQL Server", "ODBC Driver 11 for SQL Server", "SQL Server Native Client 11.0", "SQL Server"]


def main():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(CFG, encoding="utf-8")
    import pyodbc
    have = pyodbc.drivers()
    want = cfg.get("database", "driver", fallback="")
    drv = want if want in have else next((d for d in DRIVERS if d in have), None)
    if not drv:
        print("Khong tim thay driver ODBC cho SQL Server. Cai 'ODBC Driver 17 for SQL Server' cua Microsoft roi chay lai.")
        print("Driver dang co:", have)
        sys.exit(1)
    if drv != want:
        cfg.set("database", "driver", drv)
        with open(CFG, "w", encoding="utf-8") as f:
            cfg.write(f)
        print("Da chon driver:", drv)
    sys.path.insert(0, str(BASE))
    from app import config
    print("Dang ket noi:", config.get("database", "server"), "/", config.get("database", "database"),
          "/ user:", config.get("database", "user") or "(Windows)",
          "/ mat khau:", len(config.get("database", "password")), "ky tu")
    from app.erp import Erp
    try:
        e = Erp()
        ver = e.rows("SELECT @@VERSION AS v")[0]["v"].splitlines()[0]
        print("Ket noi SQL Server OK:", ver)
        menus = [m for m in e.menu_all() if m["FormKey"] in ("List", "Report") and not m["isDisable"]]
        ok = [m for m in menus if e.target_ok(m)]
        print(f"Doc duoc {len(menus)} menu web dang bat, {len(ok)} menu co du cau hinh/store de chay:")
        for m in menus:
            print("  ", "OK " if m in ok else "-- ", m["MenuID"], m["VN"])
    except Exception as ex:
        print("LOI ket noi / doc du lieu:", str(ex).splitlines()[0])
        print("Kiem tra lai server, database, user, password trong config.ini")
        sys.exit(1)
    from app import appdb
    appdb.init()
    print("Tai khoan dang nhap web mac dinh: admin / admin123 (doi ngay sau khi vao).")


if __name__ == "__main__":
    main()
