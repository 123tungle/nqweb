"""Test toàn bộ API trên database SQLite giả lập (không đụng SQL Server). Chạy: python -m pytest -q tests"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="nqweb-test-"))
os.environ["NQWEB_DATABASE_TYPE"] = "sqlite"
os.environ["NQWEB_DATABASE_PATH"] = str(TMP / "erp.sqlite3")
os.environ["NQWEB_APP_APP_DB"] = str(TMP / "app.sqlite3")
os.environ["NQWEB_CONFIG"] = str(TMP / "none.ini")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import fixture  # noqa: E402
fixture.build(str(TMP / "erp.sqlite3"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app, erp  # noqa: E402


@pytest.fixture(scope="module")
def admin():
    with TestClient(app) as c:
        assert c.post("/api/login", json={"username": "admin", "password": "admin123"}).status_code == 200
        yield c


def test_login(admin):
    with TestClient(app) as c:
        assert c.get("/api/me").status_code == 401
        assert c.post("/api/login", json={"username": "admin", "password": "sai"}).status_code == 401


def test_menu_admin(admin):
    me = admin.get("/api/me").json()
    ids = [i["id"] for g in me["menu"] for i in g["items"]]
    assert ids == ["1010", "1012", "1014", "1016", "2028"]          # 1018 đang tắt, 2030 chưa có store, 9008 là màn hình riêng
    assert me["menu"][0]["title"] == "Đơn hàng"
    assert [m["id"] for m in me["menu_skipped"]] == ["2030", "8012"] and me["menu_error"] is None


def test_order_list_and_record(admin):
    meta = admin.get("/api/list/1012/meta").json()
    assert meta["has_date"] and [f["col"] for f in meta["filters"]] == ["EmployeeID", "StatusID"]
    assert meta["filters"][0]["caption"] == "Mã nhân viên"
    opts = admin.get("/api/list/1012/options/StatusID").json()
    assert {"value": "0", "label": "Chờ duyệt - 0"} in opts
    r = admin.post("/api/list/1012/rows", json={"tu": "2026-09-26", "den": "2026-10-11"}).json()
    caps = [c["caption"] for c in r["cols"]]
    assert caps == ["Số CT", "Ngày CT", "Giờ", "Trạng thái", "Khách hàng", "Mã hàng", "Tổng tiền", "Tên nhân viên"]
    assert [row[0] for row in r["rows"]] == ["DL260926172435", "DL260926171537"]   # DateCreate giảm dần
    assert r["cols"][6]["sum"] and r["keys"][0][1] == "Chờ duyệt"
    r = admin.post("/api/list/1012/rows", json={"tu": "2024-01-01", "den": "2026-12-31", "filters": {"StatusID": "0"}}).json()
    assert len(r["rows"]) == 2
    r = admin.post("/api/list/1012/rows", json={"tu": "2024-01-01", "den": "2026-12-31", "q": "Anh Hải"}).json()
    assert [row[0] for row in r["rows"]] == ["DH240920/001"]
    rec = admin.get("/api/list/1012/record/DL260926172435").json()
    assert [f["name"] for f in rec["fields"]][:4] == ["DocumentID", "DocumentDate", "EmployeeID", "EmployeeName"]
    assert rec["cols"][1]["caption"] == "Tên hàng" and rec["lines"][1][1] == "Revive Chai nhựa 500x24 Lốc 6"
    assert sum(l[7] for l in rec["lines"]) == 200000
    assert admin.get("/api/list/1012/record/DH240920/001").status_code == 200   # số CT có dấu /


def test_delivery_map(admin):
    r = admin.post("/api/list/1014/rows", json={"tu": "2026-09-28", "den": "2026-09-28"}).json()
    assert r["rows"][0][0] == "PL068282" and "Mapdata" in r["rows"][0][2]
    rec = admin.get("/api/list/1014/record/PL068282").json()
    assert len(rec["points"]) == 2 and rec["points"][0]["name"] == "TH Anh Hải"


def test_report(admin):
    meta = admin.get("/api/report/2028/meta").json()
    assert [p["name"] for p in meta["params"]] == ["FromDate", "ToDate", "Mahang", "EmployeeID", "Objectid", "LoaiXuat"]
    assert meta["params"][0]["caption"] == "Từ ngày" and meta["params"][0]["type"] == "date"
    assert meta["params"][3]["has_options"] and not meta["params"][4]["has_options"]
    opts = admin.get("/api/report/2028/options/EmployeeID").json()
    assert opts[0] == {"value": "002RC40101", "label": "Vương Thị Sen - 002RC40101"}
    r = admin.post("/api/report/2028/run", json={"values": {"FromDate": "2026-09-01", "ToDate": "2026-09-27", "EmployeeID": ""}}).json()
    assert r["groups"][0] == "NVBH : Trần Ngọc Linh" and r["cols"][0]["caption"] == "Mã hàng"
    assert len(r["rows"]) == 3
    proc, args = erp().last_proc_call
    assert proc == "WA_BanHangTongHopTheoNVBHReportStp" and str(args["FromDate"]) == "2026-09-01"
    x = admin.post("/api/report/2028/excel", json={"values": {"FromDate": "2026-09-01"}})
    assert x.status_code == 200 and x.content[:2] == b"PK"
    x = admin.post("/api/list/1012/excel", json={"tu": "2024-01-01", "den": "2026-12-31"})
    assert x.status_code == 200 and x.content[:2] == b"PK"


def test_dashboard(admin):
    d = admin.get("/api/dashboard").json()
    assert d["den"] == "2025-04-08"
    assert d["kpi"]["ngay"] == 3000000 and d["kpi"]["thang"] == 3000000 and d["kpi"]["don_cho_duyet"] == 2
    assert [t["thang"] for t in d["thang"]] == ["2025-03", "2025-04"]


def test_sales_user_restricted(admin):
    assert admin.post("/api/nguoi-dung", json={"ten_dang_nhap": "linh", "ho_ten": "Linh", "nhom": "Sales",
                                               "ma_nv": "002RC40104", "mat_khau": "123456"}).status_code == 200
    assert admin.post("/api/nguoi-dung", json={"ten_dang_nhap": "x1", "mat_khau": "123456"}).status_code == 400  # thiếu nhóm
    with TestClient(app) as c:
        assert c.post("/api/login", json={"username": "linh", "password": "123456"}).status_code == 200
        me = c.get("/api/me").json()
        assert [i["id"] for g in me["menu"] for i in g["items"]] == ["1010", "1012", "2028"]
        assert c.get("/api/list/1014/meta").status_code == 403
        meta = c.get("/api/list/1012/meta").json()
        assert meta["filters"][0]["locked"] and meta["filters"][0]["default"] == "002RC40104" and not meta["excel"]
        r = c.post("/api/list/1012/rows", json={"tu": "2024-01-01", "den": "2026-12-31", "filters": {"EmployeeID": "002RC40101"}}).json()
        assert {row[7] for row in r["rows"]} == {"Trần Ngọc Linh"}                       # không xem được NV khác
        assert c.get("/api/list/1012/record/DL260926171537").status_code == 403
        assert c.get("/api/list/1012/record/DL260926172435").status_code == 200
        assert c.post("/api/list/1012/excel", json={}).status_code == 403
        c.post("/api/report/2028/run", json={"values": {"EmployeeID": "002RC40101"}})
        assert erp().last_proc_call[1]["EmployeeID"] == "002RC40104"
        assert c.get("/api/report/2028/options/EmployeeID").json() == [{"value": "002RC40104", "label": "Trần Ngọc Linh - 002RC40104"}]
        assert c.get("/api/nguoi-dung").status_code == 403
        assert c.post("/api/doi-mat-khau", json={"old": "123456", "new": "abcdef"}).status_code == 200


def test_admin_guard(admin):
    assert admin.delete("/api/nguoi-dung/admin").status_code == 400
    assert admin.post("/api/nguoi-dung", json={"ten_dang_nhap": "admin", "la_admin": False, "nhom": "Sales"}).status_code == 400
    logs = admin.get("/api/nhat-ky", params={"tu": "2000-01-01", "den": "2100-01-01"}).json()
    assert any(l["hanh_dong"] == "Xem báo cáo" for l in logs)


# ---------------------------------------------------------------- nhập đơn sỉ / lẻ (store giả lập)
CALLS = []


def _fake_procs():
    def kh(a):
        CALLS.append(("kh", a))
        rows = [{"ObjectID": "002RC40104", "ObjectName": "Trần Ngọc Linh- BÙ TỔNG", "Address": "K35", "Phone": "09", "EmployeeID": "002RC40104"},
                {"ObjectID": "002RC40101", "ObjectName": "Vương Thị Sen- BÙ TỔNG", "Address": "K35", "Phone": "", "EmployeeID": "002RC40101"}]
        return [r for r in rows if not a["EmployeeID"] or r["EmployeeID"] == a["EmployeeID"]]

    def ttkh(a):
        rows = {r["ObjectID"]: r for r in kh({"EmployeeID": ""})}
        r = rows.get(a["ObjectID"])
        return [dict(r, LoaiDon="LE", NoDau=150000, ConNo=150000)] if r else []

    def hh(a):
        CALLS.append(("hh", a))
        return [{"ItemID": "10000011", "ItemName": "Aquafina Chai nhựa 500x24", "Unit": "PET", "QuyDoi": 24, "GiaChuan": 88000}]

    def luu(a):
        CALLS.append(("luu", a))
        if "<ItemID>XXX</ItemID>" in a["Lines"]:
            return [{"MsgType": 1, "Title": "Dòng 1: mã hàng XXX không có trong bảng giá", "DocumentID": None}]
        return [{"MsgType": -1, "Title": "Đã lưu", "DocumentID": a["DocumentID"] or "DL260928090000"}]

    def xoa(a):
        CALLS.append(("xoa", a))
        return [{"MsgType": -1, "Title": "Đã xóa"}]

    erp().fake_procs.update({"NQW_DonHang_KhachHangStp": kh, "NQW_DonHang_ThongTinKHStp": ttkh, "NQW_DonHang_HangHoaStp": hh,
                             "NQW_DonHang_LuuStp": luu, "NQW_DonHang_XoaStp": xoa})


def test_order_entry_admin(admin):
    _fake_procs()
    meta = admin.get("/api/list/1010/meta").json()
    assert meta["entry"] == {"loai": "LE", "ten": "Đơn hàng lẻ", "ck": False, "add": True, "edit": True, "delete": True}
    assert admin.get("/api/list/1014/meta").json()["entry"] is None
    assert len(admin.get("/api/order/1010/customers", params={"q": "Linh"}).json()) == 2
    assert CALLS[-1] == ("kh", {"LoaiDon": "LE", "EmployeeID": "", "S": "Linh"})
    c = admin.get("/api/order/1010/customer/002RC40104").json()
    assert c["NoDau"] == 150000 and c["LoaiDon"] == "LE"
    assert admin.get("/api/order/1010/items", params={"obj": "002RC40104"}).json()[0]["GiaChuan"] == 88000
    assert admin.get("/api/order/1010/promos").json() == []                  # chưa có hàm KM trong DB test
    body = {"DocumentDate": "2026-09-28", "DeliveryDate": "2026-09-29", "ObjectID": "002RC40104", "EmployeeID": "002RC40104",
            "Memo": "giao sáng <gấp>", "HoanTat": True,
            "lines": [{"ItemID": "10000011", "Ket": 2, "Chai": 3.0, "UnitPrice": 88000}, {"ItemID": ""}]}
    r = admin.post("/api/order/1010/save", json=body)
    assert r.status_code == 200 and r.json()["DocumentID"] == "DL260928090000"
    a = CALLS[-1][1]
    assert a["LoaiDon"] == "LE" and a["HoanTat"] == 1 and a["IsAdmin"] == 1 and a["User"] == "admin"
    assert a["Lines"] == "<Lines><L><ItemID>10000011</ItemID><Ket>2</Ket><Chai>3</Chai><UnitPrice>88000</UnitPrice></L></Lines>"
    assert str(a["DocumentDate"]) == "2026-09-28" and a["Memo"] == "giao sáng <gấp>"
    r = admin.post("/api/order/1010/save", json=dict(body, lines=[{"ItemID": "XXX", "Ket": 1}]))
    assert r.status_code == 422 and r.json()["errors"] == ["Dòng 1: mã hàng XXX không có trong bảng giá"]
    assert admin.post("/api/order/1010/save", json=dict(body, lines=[])).status_code == 400
    d = admin.get("/api/order/1010/doc/DL260926172435").json()
    assert d["approved"] is False                                         # MaTrangThai -1: đang lên đơn -> sửa được
    assert admin.get("/api/order/1010/doc/DL260926171537").json()["approved"] is True
    assert d["head"]["ObjectName"].startswith("Trần") and len(d["lines"]) == 3 and d["lines"][1]["ItemName"].startswith("Revive")
    rec = admin.get("/api/list/1010/record/DL260926172435").json()
    assert rec["entry"]["loai"] == "LE" and rec["approved"] is True and "Chờ duyệt" in rec["lock_reason"]   # chờ duyệt: không sửa
    assert admin.get("/api/list/1010/record/DL260926171537").json()["approved"] is True
    assert admin.delete("/api/order/1010/doc/DL260926172435").status_code == 200 and CALLS[-1][0] == "xoa"


def test_form_config_va_outputtype(admin):
    """Lớp cấu hình ZNQW_* (metadata-driven): chưa cài thì form chạy mặc định, OutputType gửi được qua lưu."""
    _fake_procs()
    # Chưa cài bảng ZNQW_* trong DB test -> endpoint cấu hình trả cfg=None, form dùng bố cục cũ
    r = admin.get("/api/order/1010/config")
    assert r.status_code == 200 and r.json()["cfg"] is None
    # Lưu đơn có kèm OutputType: không lỗi, store lưu OutputType (ZNQW_DonLe_SetOutputTypeStp) vắng mặt thì bỏ qua êm
    body = {"DocumentDate": "2026-09-28", "ObjectID": "002RC40104", "EmployeeID": "002RC40104", "OutputType": "SO",
            "lines": [{"ItemID": "10000011", "Ket": 1, "UnitPrice": 88000}]}
    assert admin.post("/api/order/1010/save", json=body).status_code == 200


def test_field_locked():
    """Phân quyền field theo NhomDuocSua: rỗng = ai cũng sửa; có nhóm = chỉ nhóm đó (admin luôn sửa)."""
    from app.main import _field_locked
    admin_u = {"la_admin": True, "nhom": "SomeGroup"}
    sale_u = {"la_admin": False, "nhom": "Sales"}
    adm_grp = {"la_admin": False, "nhom": "Admin2"}
    assert _field_locked(sale_u, {"nhom_sua": ""}) is False          # rỗng: ai cũng sửa
    assert _field_locked(sale_u, {"nhom_sua": None}) is False
    assert _field_locked(admin_u, {"nhom_sua": "Admin,Admin2"}) is False   # admin web luôn sửa
    assert _field_locked(sale_u, {"nhom_sua": "Admin,Admin1,Admin2,Admin3"}) is True   # Sales không thuộc nhóm -> khóa
    assert _field_locked(adm_grp, {"nhom_sua": "Admin,Admin1,Admin2,Admin3"}) is False  # Admin2 thuộc nhóm -> sửa được


def test_order_entry_sales_user(admin):
    _fake_procs()
    with TestClient(app) as c:
        assert c.post("/api/login", json={"username": "linh", "password": "abcdef"}).status_code == 200
        meta = c.get("/api/list/1010/meta").json()
        assert meta["entry"]["add"] and meta["entry"]["edit"] and not meta["entry"]["delete"]
        assert c.get("/api/list/1012/meta").json()["entry"]["add"] is False          # sỉ: nhóm Sales không có IsAdd
        assert c.post("/api/order/1012/save", json={"DocumentDate": "2026-09-28", "ObjectID": "x", "EmployeeID": "y",
                                                    "lines": [{"ItemID": "10000011", "Ket": 1}]}).status_code == 403
        assert [e["value"] for e in c.get("/api/order/1010/employees").json()] == ["002RC40104"]
        c.get("/api/order/1010/customers", params={"emp": "002RC40101"})
        assert CALLS[-1][1]["EmployeeID"] == "002RC40104"                           # luôn ép về nhân viên của mình
        assert c.get("/api/order/1010/customer/002RC40101").status_code == 403
        r = c.post("/api/order/1010/save", json={"DocumentDate": "2026-09-28", "ObjectID": "002RC40104", "EmployeeID": "002RC40101",
                                                  "lines": [{"ItemID": "10000011", "Ket": 1}]})
        assert r.status_code == 200 and CALLS[-1][1]["EmployeeID"] == "002RC40104" and CALLS[-1][1]["IsAdmin"] == 0
        assert c.post("/api/order/1010/save", json={"DocumentID": "DL260926171537", "DocumentDate": "2026-09-28", "ObjectID": "002RC40101",
                                                    "EmployeeID": "", "lines": [{"ItemID": "10000011", "Ket": 1}]}).status_code == 403
        assert c.delete("/api/order/1010/doc/DL260926172435").status_code == 403


# ---------------------------------------------------------------- đăng nhập bằng tài khoản phần mềm SY_User
def test_login_sy_user():
    with TestClient(app) as c:
        # nhân viên văn phòng (nhóm Admin2) -> quản trị web, thấy đủ menu
        assert c.post("/api/login", json={"username": "NQNB07", "password": "sanpham7"}).status_code == 200
        me = c.get("/api/me").json()
        assert me["nguon"] == "sy_user" and me["admin"] is True and me["name"] == "Nguyễn Văn Bảy" and me["ma_nv"] is None
        assert c.post("/api/doi-mat-khau", json={"old": "sanpham7", "new": "khac12"}).status_code == 400   # đổi trong phần mềm
        assert c.post("/api/login", json={"username": "NQNB07", "password": "SAI"}).status_code == 401
    with TestClient(app) as c:
        # nhân viên bán hàng -> chỉ xem dữ liệu của mình
        assert c.post("/api/login", json={"username": "002RC40104", "password": "linh123"}).status_code == 200
        me = c.get("/api/me").json()
        assert me["admin"] is False and me["ma_nv"] == "002RC40104" and me["nguon"] == "sy_user"
        assert [i["id"] for g in me["menu"] for i in g["items"]] == ["1010", "1012", "2028"]  # theo quyền nhóm Sales
        meta = c.get("/api/list/1012/meta").json()
        assert meta["filters"][0]["locked"] and meta["filters"][0]["default"] == "002RC40104"
        c.post("/api/report/2028/run", json={"values": {"EmployeeID": "002RC40101"}})
        assert erp().last_proc_call[1]["EmployeeID"] == "002RC40104"   # ép về nhân viên của mình
    with TestClient(app) as c:
        assert c.post("/api/login", json={"username": "NQNB09", "password": "x"}).status_code == 401   # Disable=1
