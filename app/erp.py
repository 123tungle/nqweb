"""Đọc dữ liệu từ database phần mềm bán hàng (NppNguyenQuan) theo đúng cấu hình web cũ.

Web cũ (BMS) vẽ màn hình từ các bảng cấu hình trong database:
  WA_Menu                    menu web (FormKey = List | Report, FormName)
  WA_UserGroupPermisstion    quyền theo nhóm người dùng
  SY_FrmCfg                  cấu hình màn hình danh sách: view (T0/TV), cột lưới (T0/GD2), sắp xếp (T0/SO),
                             cột cộng tổng (T0/SUM), khóa (T0/PK), bảng chi tiết (T1/...), bố cục phiếu (LYT1)
  SY_FrmFltTbl               bộ lọc của màn hình danh sách
  SY_FmtFldTbl               tiêu đề cột + định dạng (N, N2, D)
  SY_RpTbl                   tiêu đề + nguồn chọn của tham số báo cáo
  Báo cáo = store <FormName>Stp

Module này CHỈ ĐỌC: mọi câu lệnh là SELECT hoặc EXEC store báo cáo, chạy trong giao dịch và luôn ROLLBACK.
"""
from __future__ import annotations

import re
import threading
import time
from datetime import date, datetime, timedelta
from decimal import Decimal

import sqlalchemy as sa

from . import config

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CACHE_TTL = 300

# Tiêu đề mặc định cho tham số báo cáo khi SY_RpTbl không có
PARAM_CAPTIONS = {
    "fromdate": "Từ ngày", "todate": "Đến ngày", "ngaybaocao": "Ngày báo cáo", "employeeid": "Mã nhân viên",
    "objectid": "Mã KH", "mahang": "Mã hàng", "loaixuat": "Loại xuất", "username": "Tên sử dụng",
    "nhomhangid": "Nhóm hàng", "dieukienid": "Điều kiện", "qlrouteid": "Giám sát", "storehouseid": "Kho",
}
# Tiêu đề dự phòng khi SY_FmtFldTbl chưa có (đặt theo chữ trên web cũ)
FALLBACK_CAPTIONS = {
    "statusname": "Trạng thái", "statusid": "Trạng thái", "objectinfo": "Khách hàng", "nodau": "Nợ đầu", "phone": "Điện thoại",
    "memo": "Ghi chú", "deliverydate": "Ngày giao", "istrongngay": "Giao trong ngày", "iskhongkm": "Không K.M",
    "idlinksuagia": "Link sửa giá", "khuyenmaiid": "CTKM", "sotienchietkhau": "Tiền chiết khấu",
    "sotiensauchietkhau": "Thành tiền sau CK", "slkm": "SLKM", "kettong": "Tổng Két / thùng", "chaitong": "Chai / Lon tổng",
    "tongsl": "Tổng SL", "bando": "Bản đồ", "tennguoigiao": "Tên người giao", "nguoigiao": "Người giao 01",
    "tentuyen": "Tên tuyến", "soxe": "Số xe", "isdagiao": "Đã giao", "phieuban": "Phiếu bán", "ngayban": "Ngày bán",
    "sotienban": "Số tiền bán", "tongtienchietkhau": "Tiền C.K", "tongtien": "Tổng tiền", "latitude": "Vĩ độ",
    "longitude": "Kinh độ", "ten": "Tên hàng", "ketcd": "Két/Thùng chuyển đổi", "chaicd": "Chai / Lon chuyển đổi",
    "slcd": "SL kho App", "ketgiao": "Két/Thùng đơn hàng", "chaigiao": "Chai/Lon đơn hàng", "slgiao": "SL đơn hàng",
    "stcd": "ST kho App", "stgiao": "ST đơn hàng", "objectname": "Tên khách hàng", "address": "Địa chỉ",
    "unit": "Đvt", "quydoi": "Quy đổi", "giachuan": "Đơn giá", "unitprice": "Đơn giá CK", "amount": "Tiền sau C.K",
    "tienchietkhau": "Tiền C.K", "ketkm": "Két km", "chaikm": "Chai km",
}
TYPE_CODES = {"1": "text", "4": "date", "5": "number", "6": "bool"}


class ErpError(Exception):
    pass


class Erp:
    def __init__(self, url: str | None = None):
        url = url or config.erp_url()
        kw = {}
        if url.startswith("mssql") and config.get_bool("app", "doc_khong_cho_khoa", True):
            # Phần mềm bán hàng hay giữ khóa bảng (tbBannuoc...) -> đọc không chờ khóa như WITH (NOLOCK)
            kw["isolation_level"] = "READ UNCOMMITTED"
        self.engine = sa.create_engine(url, pool_pre_ping=True, future=True, **kw)
        self.mssql = self.engine.dialect.name == "mssql"
        self._cache: dict = {}
        self._lock = threading.RLock()
        self.last_proc_call: tuple | None = None  # để test kiểm tra tham số
        self.fake_procs: dict = {}                 # store giả lập khi chạy test trên SQLite
        if self.mssql:
            @sa.event.listens_for(self.engine, "connect")
            def _on_connect(dbapi_conn, _rec):  # thời gian chờ tối đa mỗi câu lệnh
                try:
                    dbapi_conn.timeout = config.QUERY_TIMEOUT
                except Exception:
                    pass

    # ------------------------------------------------------------------ tiện ích
    def cached(self, key, fn):
        with self._lock:
            hit = self._cache.get(key)
            if hit and time.time() - hit[0] < CACHE_TTL:
                return hit[1]
        val = fn()
        with self._lock:
            self._cache[key] = (time.time(), val)
        return val

    def clear_cache(self):
        with self._lock:
            self._cache.clear()

    def qi(self, name: str) -> str:
        if not IDENT.match(name or ""):
            raise ErpError(f"Tên không hợp lệ: {name!r}")
        return f"[{name}]" if self.mssql else f'"{name}"'

    def rows(self, sql: str, params: dict | None = None, limit: int | None = None) -> list[dict]:
        with self.engine.connect() as cn:
            try:
                res = cn.execute(sa.text(sql), params or {})
                keys = list(res.keys())
                data = res.fetchmany(limit) if limit else res.fetchall()
                return [dict(zip(keys, r)) for r in data]
            finally:
                cn.rollback()

    def top(self, n: int) -> tuple[str, str]:
        """(tiền tố sau SELECT, hậu tố cuối câu) để lấy n dòng."""
        return (f"TOP {int(n)} ", "") if self.mssql else ("", f" LIMIT {int(n)}")

    def columns(self, obj: str) -> list[str]:
        def load():
            t, l = self.top(0)
            with self.engine.connect() as cn:
                try:
                    return list(cn.execute(sa.text(f"SELECT {t}* FROM {self.qi(obj)}{l}")).keys())
                finally:
                    cn.rollback()
        return self.cached(("cols", obj.lower()), load)

    def match_col(self, cols: list[str], name: str | None) -> str | None:
        if not name:
            return None
        low = name.strip().lower()
        for c in cols:
            if c.lower() == low:
                return c
        return None

    def object_exists(self, name: str) -> bool:
        if not IDENT.match(name or ""):
            return False
        def load():
            if self.mssql:
                return bool(self.rows("SELECT CASE WHEN OBJECT_ID(:n) IS NULL THEN 0 ELSE 1 END AS x", {"n": "dbo." + name})[0]["x"])
            return bool(self.rows("SELECT COUNT(*) AS x FROM sqlite_master WHERE lower(name) = lower(:n)", {"n": name})[0]["x"])
        return self.cached(("exists", name.lower()), load)

    # ------------------------------------------------------------------ menu + quyền
    def menu_all(self) -> list[dict]:
        return self.cached("menu", lambda: self.rows(
            "SELECT MenuID, VN, Parent, IconClass, FormKey, FormName, isDisable FROM WA_Menu ORDER BY MenuID"))

    def menu_item(self, menu_id: str) -> dict:
        for m in self.menu_all():
            if str(m["MenuID"]) == str(menu_id):
                return m
        raise ErpError("Không có menu " + str(menu_id))

    def group_permissions(self, group: str) -> dict[str, dict]:
        def load():
            rs = self.rows("SELECT MenuID, IsRun, IsAdd, IsUpdate, IsDelete, isExportExcel FROM WA_UserGroupPermisstion "
                           "WHERE UserGroupID = :g", {"g": group})
            return {str(r["MenuID"]): r for r in rs}
        return self.cached(("perm", group), load)

    def user_groups(self) -> list[dict]:
        return self.cached("groups", lambda: self.rows(
            "SELECT UserGroupID, UserGroupName FROM SY_UserGroup WHERE COALESCE(IsDisable, 0) = 0 ORDER BY UserGroupID"))

    def employees(self) -> list[dict]:
        return self.cached("emps", lambda: self.rows(
            "SELECT EmployeeID, EmployeeName FROM CF_EmployeeTbl ORDER BY EmployeeID"))

    # ------------------------------------------------------------------ đăng nhập bằng tài khoản phần mềm (SY_User)
    def sy_user(self, username: str) -> dict | None:
        """1 dòng SY_User (không cache mật khẩu lâu: TTL ngắn để đổi mật khẩu bên phần mềm có hiệu lực nhanh)."""
        if not username:
            return None
        rs = self.rows("SELECT UserName, HoTen, TenNgan, Password, UserGroupID, EmployeeID, Manager, "
                       "COALESCE(Disable, 0) AS Disable FROM SY_User WHERE UserName = :u", {"u": username})
        return rs[0] if rs else None

    def verify_sy_user(self, username: str, password: str) -> dict | None:
        """Trả về dòng SY_User nếu mật khẩu đúng và tài khoản đang dùng; ngược lại None.

        Băm lại theo đúng thuật toán phần mềm .NET (salted MD5) — KHÔNG giải mã mật khẩu.
        """
        u = self.sy_user(username)
        if not u or u.get("Disable"):
            return None
        if _bms_verify(username, password, u.get("Password") or "", config.get("app", "bms_pass_encoding", "utf-8")):
            return u
        return None

    def target_check(self, m: dict) -> str | None:
        """None = màn hình chạy được; ngược lại trả lý do bị ẩn (view lỗi, thiếu store...)."""
        def load():
            try:
                if m.get("FormKey") == "Report":
                    name = (m.get("FormName") or "") + "Stp"
                    return None if self.object_exists(name) else f"chưa có store {name}"
                if m.get("FormKey") == "List":
                    self.form_def(m["FormName"])
                    return None
                return "không phải màn hình danh sách/báo cáo"
            except Exception as e:  # view hỏng (vd. trỏ tới database không tồn tại) chỉ ẩn menu đó
                return str(e).splitlines()[0][:200]
        return self.cached(("target", str(m.get("MenuID"))), load)

    def target_ok(self, m: dict) -> bool:
        return self.target_check(m) is None

    # ------------------------------------------------------------------ định dạng cột
    def formats(self, form: str | None) -> dict[str, dict]:
        def load_global():
            rs = self.rows("SELECT FieldName, CaptionVN, FormatID FROM SY_FmtFldTbl WHERE FormName IS NULL OR FormName = ''")
            return {r["FieldName"].lower(): {"caption": r["CaptionVN"], "fmt": (r["FormatID"] or "").strip()} for r in rs if r["FieldName"]}
        out = dict(self.cached("fmt_global", load_global))
        if form:
            rs = self.cached(("fmt", form), lambda: self.rows(
                "SELECT FieldName, CaptionVN, FormatID FROM SY_FmtFldTbl WHERE FormName = :f", {"f": form}))
            for r in rs:
                if r["FieldName"]:
                    out[r["FieldName"].lower()] = {"caption": r["CaptionVN"], "fmt": (r["FormatID"] or "").strip()}
        return out

    def describe(self, cols: list[str], form: str | None, sums: list[str] | None = None, sample: list[dict] | None = None) -> list[dict]:
        fm = self.formats(form)
        sums_l = {s.lower() for s in (sums or [])}
        out = []
        for c in cols:
            f = fm.get(c.lower(), {})
            fmt = f.get("fmt") or ""
            if not fmt and sample:
                v = next((r.get(c) for r in sample if r.get(c) is not None), None)
                if isinstance(v, bool):
                    fmt = "B"
                elif isinstance(v, (int, float, Decimal)):
                    fmt = "N2" if isinstance(v, (float, Decimal)) and any(
                        (r.get(c) or 0) % 1 for r in sample[:200] if isinstance(r.get(c), (int, float, Decimal))) else "N"
                elif isinstance(v, (datetime, date)):
                    fmt = "D"
            out.append({"name": c, "caption": f.get("caption") or FALLBACK_CAPTIONS.get(c.lower()) or c, "fmt": fmt, "sum": c.lower() in sums_l or (sums is None and fmt in ("N", "N2") and _is_amount(c))})
        return out

    # ------------------------------------------------------------------ màn hình danh sách
    def form_cfg(self, fid: str) -> list[dict]:
        return self.cached(("cfg", fid), lambda: self.rows(
            "SELECT KeyID, SubID, KeyValue, SubValue FROM SY_FrmCfg WHERE FID = :f", {"f": fid}))

    def form_def(self, fid: str) -> dict:
        def load():
            cfg = self.form_cfg(fid)
            if not cfg:
                raise ErpError(f"Màn hình {fid} chưa có cấu hình trong SY_FrmCfg")
            kv = {((r["KeyID"] or "").upper(), (r["SubID"] or "").upper()): (r["KeyValue"] or "") for r in cfg}
            view = kv.get(("T0", "TV")) or kv.get(("T0", "TN"))
            if not view or not self.object_exists(view):
                raise ErpError(f"Màn hình {fid}: không tìm thấy view/bảng {view}")
            vcols = self.columns(view)
            mc = lambda n: self.match_col(vcols, n)  # noqa: E731
            pk = mc(kv.get(("T0", "PK"))) or vcols[0]
            grid = [c for c in (mc(x) for x in _split(kv.get(("T0", "GD2")) or kv.get(("T0", "GDW")))) if c] or vcols[:12]
            order = []
            for part in (kv.get(("T0", "SO")) or "").split(","):
                bits = part.strip().split()
                col = mc(bits[0]) if bits else None
                if col:
                    order.append((col, "DESC" if len(bits) > 1 and bits[1].lower() == "desc" else "ASC"))
            date_field = mc(kv.get(("DFP", ""))) or mc("DocumentDate")
            master = {
                "view": view, "pk": pk, "grid": grid, "order": order or [(pk, "DESC")],
                "sums": [c for c in (mc(x) for x in _split(kv.get(("T0", "SUM")))) if c],
                "status": mc(kv.get(("T0C1", "A"))), "color": mc(kv.get(("T0C1", "B"))), "date": date_field,
            }
            detail = None
            tn = kv.get(("T1", "TN"))
            if tn and self.object_exists(tn):
                dcols = self.columns(tn)
                link = self.match_col(dcols, pk)
                if link:
                    lookup = kv.get(("T1", "TN1"))
                    lookup_fields, fka, fkb = [], None, None
                    if lookup and self.object_exists(lookup):
                        lcols = self.columns(lookup)
                        fka = self.match_col(dcols, kv.get(("T1", "FKA1")))
                        fkb = self.match_col(lcols, kv.get(("T1", "FKB1")))
                        lookup_fields = [c for c in (self.match_col(lcols, x) for x in _split(kv.get(("T1", "SE1")), ","))
                                         if c and not self.match_col(dcols, c)]
                    if not (fka and fkb):
                        lookup = None
                    allcols = dcols + lookup_fields
                    grid_d = [c for c in (self.match_col(allcols, x) for x in _split(kv.get(("T1", "GD2")) or kv.get(("T1", "GDW")))) if c]
                    detail = {
                        "table": tn, "link": link, "lookup": lookup, "fka": fka, "fkb": fkb, "lookup_fields": lookup_fields,
                        "grid": grid_d or dcols, "sums": [c for c in (self.match_col(allcols, x) for x in _split(kv.get(("T1", "SUM")))) if c],
                        "order": self.match_col(dcols, kv.get(("T1", "PK"))) or link,
                    }
            layout = []
            for r in cfg:
                if (r["KeyID"] or "").upper() == "LYT1" and mc(r["SubID"]):
                    code = (r["KeyValue"] or "").split(";")[0]
                    layout.append({"name": mc(r["SubID"]), "order": r["SubValue"] or "", "type": TYPE_CODES.get(code, "text")})
            layout.sort(key=lambda x: x["order"])
            filters = []
            for f in self.rows("SELECT ColumnID, Caption, Source, ValueColumn, DisplayColumn, DefaultValue, UseLikeOperator "
                               "FROM SY_FrmFltTbl WHERE FormID = :f ORDER BY KeyID", {"f": fid}):
                col = mc(f["ColumnID"])
                if col:
                    filters.append({"col": col, "caption": f["Caption"], "source": f["Source"], "value": f["ValueColumn"] or col,
                                    "display": f["DisplayColumn"], "default": f["DefaultValue"], "like": bool(f["UseLikeOperator"])})
            return {"fid": fid, "master": master, "detail": detail, "layout": layout, "filters": filters}
        return self.cached(("def", fid), load)

    def filter_options(self, fid: str, col: str, only: str | None = None) -> list[dict]:
        d = self.form_def(fid)
        f = next((x for x in d["filters"] if x["col"] == col), None)
        if not f or not f["source"]:
            return []
        rs = self.cached(("fopt", fid, col), lambda: self.rows(f["source"], limit=config.MAX_ROWS))
        out = []
        for r in rs:
            v = _get_ci(r, f["value"])
            if v is None or (only and str(v) != only):
                continue
            lab = _get_ci(r, f["display"]) if f["display"] else None
            out.append({"value": str(v), "label": f"{lab} - {v}" if lab not in (None, "", v) else str(v)})
        return out

    def list_rows(self, fid: str, tu: date | None, den: date | None, filters: dict, search: str, emp_only: str | None):
        d = self.form_def(fid)
        m = d["master"]
        view_cols = self.columns(m["view"])
        want = list(dict.fromkeys(m["grid"] + [m["pk"]] + [c for c in (m["status"], m["color"]) if c]))
        where, params = [], {}
        if m["date"] and tu:
            where.append(f"{self.qi(m['date'])} >= :tu")
            params["tu"] = datetime.combine(tu, datetime.min.time())
        if m["date"] and den:
            where.append(f"{self.qi(m['date'])} < :den")
            params["den"] = datetime.combine(den + timedelta(days=1), datetime.min.time())
        emp_col = self.match_col(view_cols, "EmployeeID")
        if emp_only and not emp_col:
            raise PermissionError("Màn hình này không lọc được theo nhân viên nên tài khoản giới hạn nhân viên không xem được")
        if emp_only and emp_col:
            where.append(f"{self.qi(emp_col)} = :emp_only")
            params["emp_only"] = emp_only
        for i, f in enumerate(d["filters"]):
            v = (filters or {}).get(f["col"])
            if v in (None, "") or (emp_only and f["col"] == emp_col):
                continue
            if f["like"]:
                where.append(f"{self.qi(f['col'])} LIKE :f{i}")
                params[f"f{i}"] = f"%{v}%"
            else:
                where.append(f"{self.qi(f['col'])} = :f{i}")
                params[f"f{i}"] = v
        if search:
            cast = (lambda c: f"CAST({self.qi(c)} AS NVARCHAR(4000))") if self.mssql else self.qi
            where.append("(" + " OR ".join(f"{cast(c)} LIKE :s" for c in m["grid"]) + ")")
            params["s"] = f"%{search.strip()}%"
        t, l = self.top(config.MAX_ROWS + 1)
        sql = (f"SELECT {t}{', '.join(self.qi(c) for c in want)} FROM {self.qi(m['view'])}"
               + (" WHERE " + " AND ".join(where) if where else "")
               + " ORDER BY " + ", ".join(f"{self.qi(c)} {o}" for c, o in m["order"]) + l)
        rs = self.rows(sql, params)
        truncated = len(rs) > config.MAX_ROWS
        return rs[: config.MAX_ROWS], truncated

    def record(self, fid: str, key: str, emp_only: str | None):
        d = self.form_def(fid)
        m = d["master"]
        t, l = self.top(1)
        rs = self.rows(f"SELECT {t}* FROM {self.qi(m['view'])} WHERE {self.qi(m['pk'])} = :k{l}", {"k": key})
        if not rs:
            raise ErpError("Không tìm thấy chứng từ " + key)
        head = rs[0]
        emp_col = self.match_col(list(head.keys()), "EmployeeID")
        if emp_only and (not emp_col or str(head.get(emp_col) or "") != emp_only):
            raise PermissionError("Bạn chỉ được xem chứng từ của nhân viên " + emp_only)
        lines, dcols = [], []
        det = d["detail"]
        if det:
            sel = "d.*" + "".join(f", l.{self.qi(c)}" for c in det["lookup_fields"])
            join = (f" LEFT JOIN {self.qi(det['lookup'])} l ON l.{self.qi(det['fkb'])} = d.{self.qi(det['fka'])}"
                    if det["lookup"] else "")
            lines = self.rows(f"SELECT {sel} FROM {self.qi(det['table'])} d{join} WHERE d.{self.qi(det['link'])} = :k "
                              f"ORDER BY d.{self.qi(det['order'])}", {"k": key})
            dcols = det["grid"]
        return head, lines, dcols

    # ------------------------------------------------------------------ báo cáo (store)
    def proc_params(self, rp: str) -> list[dict]:
        proc = rp + "Stp"
        if not self.object_exists(proc):
            raise ErpError(f"Chưa có store {proc} trong database")
        def load():
            if self.mssql:
                ps = self.rows("SELECT p.name, TYPE_NAME(p.user_type_id) AS t FROM sys.parameters p "
                               "WHERE p.object_id = OBJECT_ID(:p) ORDER BY p.parameter_id", {"p": "dbo." + proc})
            else:
                ps = self.rows("SELECT name, t FROM zz_proc_param WHERE proc = :p ORDER BY ord", {"p": proc})
            rp_meta = {r["ParaName"].lower(): r for r in self.cached("rptbl", lambda: self.rows(
                "SELECT ParaName, VN, ValueList, ValueMember, DisplayMember, ColArr FROM SY_RpTbl"))}
            fm = self.formats(rp)
            out = []
            for p in ps:
                key = p["name"].lstrip("@")
                t = (p["t"] or "").lower()
                meta = rp_meta.get(key.lower())
                kind = "date" if "date" in t else "number" if t in ("int", "bigint", "smallint", "tinyint", "decimal", "numeric", "float", "money") \
                    else "bool" if t == "bit" else "text"
                caption = (meta or {}).get("VN") or PARAM_CAPTIONS.get(key.lower()) or (fm.get(key.lower()) or {}).get("caption") or key
                out.append({"name": key, "type": kind, "caption": caption,
                            "has_options": bool(meta and meta.get("ValueList")) and kind in ("text", "number")})
            return out
        return self.cached(("params", proc), load)

    def param_options(self, rp: str, pname: str, only: str | None = None) -> list[dict]:
        meta = next((r for r in self.cached("rptbl", lambda: self.rows(
            "SELECT ParaName, VN, ValueList, ValueMember, DisplayMember, ColArr FROM SY_RpTbl")) if r["ParaName"].lower() == pname.lower()), None)
        if not meta or not meta["ValueList"]:
            return []
        rs = self.cached(("popt", pname.lower()), lambda: self.rows(meta["ValueList"], limit=config.MAX_ROWS))
        cols = [c for c in (meta["ColArr"] or "").split(";") if c]
        vcol = meta["ValueMember"] or (cols[0] if cols else None)
        other = [c for c in cols if c.lower() != (vcol or "").lower()]
        out = []
        for r in rs:
            v = _get_ci(r, vcol)
            if v is None or (only and str(v) != only):
                continue
            lab = " | ".join(str(_get_ci(r, c)) for c in other[:2] if _get_ci(r, c) not in (None, ""))
            out.append({"value": str(v), "label": f"{lab} - {v}" if lab else str(v)})
        return out

    def run_report(self, rp: str, values: dict, emp_only: str | None) -> tuple[list[str], list[dict], bool]:
        params = self.proc_params(rp)
        args = []
        for p in params:
            raw = values.get(p["name"])
            if emp_only and p["name"].lower() in ("employeeid", "semployeeid"):
                raw = emp_only
            if p["type"] == "date":
                val = _to_date(raw)
            elif p["type"] == "number":
                val = None if raw in (None, "") else (int(raw) if re.fullmatch(r"-?\d+", str(raw)) else float(raw))
            elif p["type"] == "bool":
                val = 1 if str(raw).lower() in ("1", "true", "on") else 0
            else:
                val = "" if raw is None else str(raw)
            args.append((p["name"], val))
        proc = rp + "Stp"
        self.last_proc_call = (proc, dict(args))
        if not self.mssql:
            rs = self.rows(f"SELECT * FROM {self.qi(proc)}")
            cols = list(rs[0].keys()) if rs else self.columns(proc)
            return cols, rs, False
        raw_cn = self.engine.raw_connection()
        try:
            cur = raw_cn.cursor()
            placeholders = ", ".join(f"@{n} = ?" for n, _ in args)
            cur.execute(f"SET NOCOUNT ON; EXEC dbo.{self.qi(proc)} {placeholders}", [v for _, v in args])
            while cur.description is None:
                if not cur.nextset():
                    return [], [], False
            cols = [c[0] or f"Cot{i + 1}" for i, c in enumerate(cur.description)]
            data = cur.fetchmany(config.MAX_ROWS + 1)
            rows = [dict(zip(cols, r)) for r in data]
            truncated = len(rows) > config.MAX_ROWS
            return cols, rows[: config.MAX_ROWS], truncated
        finally:
            try:
                raw_cn.rollback()
            finally:
                raw_cn.close()

    # ------------------------------------------------------------------ gọi store (đọc hoặc ghi)
    def call_proc(self, proc: str, args: list[tuple[str, object]], write: bool = False) -> list[dict]:
        """EXEC dbo.<proc> @a = ?, ... và trả về bảng kết quả đầu tiên.

        write=False: luôn ROLLBACK (chỉ đọc). write=True: COMMIT, đọc/ghi theo READ COMMITTED.
        Trên SQLite (chạy test) gọi hàm giả lập trong self.fake_procs.
        """
        if not IDENT.match(proc):
            raise ErpError("Tên store không hợp lệ")
        if not self.mssql:
            fn = self.fake_procs.get(proc)
            if fn is None:
                raise ErpError(f"Chưa có store {proc} (chạy file sql\\NQW_CapNhatDatabase.sql)")
            return fn(dict(args))
        raw_cn = self.engine.raw_connection()
        try:
            cur = raw_cn.cursor()
            if write:
                cur.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            ph = ", ".join(f"@{n} = ?" for n, _ in args)
            cur.execute(f"SET NOCOUNT ON; EXEC dbo.{self.qi(proc)} {ph}", [v for _, v in args])
            while cur.description is None:
                if not cur.nextset():
                    break
            rows = []
            if cur.description is not None:
                cols = [c[0] for c in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            while cur.nextset():   # đọc hết để store chạy xong trước khi commit
                pass
            if write:
                raw_cn.commit()
            else:
                raw_cn.rollback()
            return rows
        except Exception as e:
            try:
                raw_cn.rollback()
            except Exception:
                pass
            if "Could not find stored procedure" in str(e):
                raise ErpError(f"Chưa có store {proc} trong database – chạy file sql\\NQW_CapNhatDatabase.sql trước")
            raise
        finally:
            try:
                if write:
                    raw_cn.cursor().execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
            except Exception:
                pass
            raw_cn.close()

    # ------------------------------------------------------------------ đơn hàng sỉ / lẻ
    def order_types(self) -> dict[str, dict]:
        """FormName -> cấu hình trong sy_WebLoaiDon (rỗng nếu chưa chạy sql/NQW_CapNhatDatabase.sql)."""
        def load():
            if not self.object_exists("sy_WebLoaiDon"):
                return {}
            rs = self.rows("SELECT LoaiDon, TenLoai, MenuID, FormName, TienTo, KieuSo, LayGiaSi, ChoPhepChietKhau, "
                           "KiemTraCongNo FROM sy_WebLoaiDon WHERE IsSuDung = 1")
            return {r["FormName"]: r for r in rs}
        return self.cached("order_types", load)

    def order_doc(self, key: str) -> tuple[dict | None, list[dict]]:
        t, l = self.top(1)
        head = self.rows(f"SELECT {t}O.*, K.ObjectName, K.Address, E.EmployeeName FROM WB_OrderTbl O "
                         f"LEFT JOIN CF_ObjectTbl K ON K.ObjectID = O.ObjectID LEFT JOIN CF_EmployeeTbl E ON E.EmployeeID = O.EmployeeID "
                         f"WHERE O.DocumentID = :k{l}", {"k": key})
        if not head:
            return None, []
        lines = self.rows("SELECT D.*, H.Tenhang AS ItemName, H.DvtID AS Unit FROM WB_OrderDetailTbl D "
                          "LEFT JOIN dmHangHoaView H ON H.Mahang = D.ItemID WHERE D.DocumentID = :k ORDER BY D.UserAutoID", {"k": key})
        return head[0], lines

    # ------------------------------------------------------------------ trang chủ
    def dashboard(self, den: date | None, emp_only: str | None) -> dict:
        cond = "(DuyetHangVe = 1 OR isGuiKho = 1)"
        params: dict = {}
        if emp_only:
            cond += " AND EmployeeID = :emp"
            params["emp"] = emp_only
        if den is None:
            r = self.rows(f"SELECT MAX(DocumentDate) AS d FROM tbBannuoc WHERE {cond} AND DocumentDate < :mai",
                          {**params, "mai": datetime.combine(date.today() + timedelta(days=1), datetime.min.time())})
            den = _to_date(r[0]["d"]) if r and r[0]["d"] else date.today()
        dau_thang = den.replace(day=1)
        m6 = (dau_thang - timedelta(days=150)).replace(day=1)
        p = {**params, "m6": _dt(m6), "dau": _dt(dau_thang), "ngay": _dt(den), "mai": _dt(den + timedelta(days=1))}
        ym = "CONVERT(char(7), DocumentDate, 126)" if self.mssql else "substr(DocumentDate, 1, 7)"
        thang = self.rows(f"SELECT {ym} AS thang, SUM(COALESCE(TongTienBan, 0)) AS tien, COUNT(*) AS so_phieu FROM tbBannuoc "
                          f"WHERE {cond} AND DocumentDate >= :m6 AND DocumentDate < :mai GROUP BY {ym} ORDER BY 1", p)
        t, l = self.top(10)
        nv = self.rows(f"SELECT {t}B.EmployeeID, E.EmployeeName, SUM(COALESCE(B.TongTienBan, 0)) AS tien FROM tbBannuoc B "
                       f"LEFT JOIN CF_EmployeeTbl E ON E.EmployeeID = B.EmployeeID "
                       f"WHERE {cond.replace('EmployeeID', 'B.EmployeeID')} AND B.DocumentDate >= :dau AND B.DocumentDate < :mai "
                       f"GROUP BY B.EmployeeID, E.EmployeeName ORDER BY 3 DESC{l}", p)
        k = self.rows(f"SELECT SUM(CASE WHEN DocumentDate >= :ngay THEN COALESCE(TongTienBan, 0) ELSE 0 END) AS ngay, "
                      f"SUM(COALESCE(TongTienBan, 0)) AS thang, COUNT(*) AS so_phieu, COUNT(DISTINCT ObjectID) AS so_kh "
                      f"FROM tbBannuoc WHERE {cond} AND DocumentDate >= :dau AND DocumentDate < :mai", p)[0]
        cho_duyet = None
        if self.object_exists("WA_OrderView"):
            q = "SELECT COUNT(*) AS n FROM WA_OrderView WHERE StatusID = 0" + (" AND EmployeeID = :emp" if emp_only else "")
            try:
                cho_duyet = self.rows(q, params)[0]["n"]
            except Exception:
                cho_duyet = None
        return {"den": den.isoformat(), "kpi": {**k, "don_cho_duyet": cho_duyet}, "thang": thang, "nhan_vien": nv}


# ---------------------------------------------------------------------- kiểm tra mật khẩu SY_User
# Viết lại đúng hàm VerifyUserPass của phần mềm .NET: MD5 có muối, chuỗi băm = User.ToUpper()+"190177"+Pass.
# Đây là băm MỘT CHIỀU: chỉ kiểm tra mật khẩu người dùng gõ có khớp không, KHÔNG lấy lại được mật khẩu gốc.
import hashlib  # noqa: E402


def _bms_verify(user: str, password: str, stored: str, encoding: str = "utf-8") -> bool:
    s = (user or "").upper() + "190177" + (password or "")
    try:
        if len(stored) < 6:
            return False
        addr = int(stored[3:5])                 # SaltAddress = Hash.Substring(3,2)
        h = stored[:3] + stored[5:]             # Hash.Remove(3,2)
        salt = h[addr:addr + 4]                 # SaltID = Hash.Substring(SaltAddress,4)
        h = h[:addr] + h[addr + 4:]             # Hash.Remove(SaltAddress,4) -> MD5 gốc (32 hex)
        for enc in (encoding, "utf-8", "latin-1"):   # phòng khi phần mềm dùng encoding khác cho mật khẩu có dấu
            if hashlib.md5((s + salt).encode(enc, "ignore")).hexdigest().upper() == h:
                return True
        return False
    except (ValueError, IndexError):
        return False


def _bms_encrypt_test(user: str, password: str, ran: str = "1234", loc: int = 7, encoding: str = "utf-8") -> str:
    """Tạo chuỗi băm đúng định dạng phần mềm (chỉ dùng cho test tự động)."""
    s = (user or "").upper() + "190177" + (password or "")
    h = hashlib.md5((s + ran).encode(encoding)).hexdigest().upper()
    h = h[:loc] + ran + h[loc:]
    return h[:3] + f"{loc:02d}" + h[3:]


# ---------------------------------------------------------------------- hàm phụ
def _split(s: str | None, sep: str = ";") -> list[str]:
    return [x.strip() for x in (s or "").split(sep) if x.strip()]


def _get_ci(row: dict, name: str | None):
    if not name:
        return None
    if name in row:
        return row[name]
    low = name.lower()
    for k, v in row.items():
        if k.lower() == low:
            return v
    return None


def _is_amount(c: str) -> bool:
    c = c.lower()
    return any(w in c for w in ("tien", "amount", "total", "soluong", "sl", "ket", "chai", "no"))


def _dt(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time())


def _to_date(v) -> date | None:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError("Ngày không hợp lệ: " + str(v))
