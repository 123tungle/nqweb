"""Tạo database SQLite giả lập đúng cấu trúc + cấu hình web của NppNguyenQuan để chạy test tự động.

Cấu hình (WA_Menu, SY_FrmCfg, SY_FrmFltTbl, SY_RpTbl, SY_FmtFldTbl) chép từ database thật.
"""
import sqlite3


def build(path: str) -> None:
    cn = sqlite3.connect(path)
    c = cn.cursor()
    c.executescript(
        """
        CREATE TABLE WA_Menu(MenuID TEXT, VN TEXT, Parent TEXT, IconClass TEXT, FormKey TEXT, FormName TEXT, isDisable INT);
        CREATE TABLE WA_UserGroupPermisstion(ID INTEGER PRIMARY KEY, UserGroupID TEXT, MenuID TEXT, IsRun INT, IsAdd INT DEFAULT 0, IsUpdate INT DEFAULT 0, IsDelete INT DEFAULT 0, isExportExcel INT);
        CREATE TABLE SY_UserGroup(UserGroupID TEXT, UserGroupName TEXT, IsDisable INT);
        CREATE TABLE SY_User(UserName TEXT, HoTen TEXT, TenNgan TEXT, Password TEXT, UserGroupID TEXT, EmployeeID TEXT, Manager TEXT, Disable INT);
        CREATE TABLE CF_EmployeeTbl(EmployeeID TEXT, EmployeeName TEXT);
        CREATE TABLE vEmployee(EmployeeID TEXT, EmployeeName TEXT);
        CREATE TABLE SY_FmtFldTbl(AutoID INTEGER PRIMARY KEY, FormatID TEXT, FieldName TEXT, FormName TEXT, CaptionVN TEXT);
        CREATE TABLE SY_FrmCfg(UserAutoID INTEGER PRIMARY KEY, FID TEXT, KeyID TEXT, SubID TEXT, KeyValue TEXT, SubValue TEXT);
        CREATE TABLE SY_FrmFltTbl(UserAutoID INTEGER PRIMARY KEY, FormID TEXT, KeyID TEXT, ColumnID TEXT, Caption TEXT, Source TEXT,
                                  ValueColumn TEXT, DisplayColumn TEXT, DefaultValue TEXT, UseLikeOperator INT);
        CREATE TABLE SY_RpTbl(ParaName TEXT, VN TEXT, ValueList TEXT, ValueMember TEXT, DisplayMember TEXT, ColArr TEXT);
        CREATE TABLE dmStatusTbl(StatusID INT, StatusName TEXT);
        CREATE TABLE WA_OrderView(DocumentID TEXT, DocumentDate TEXT, ObjectID TEXT, Phone TEXT, DeliveryDate TEXT, EmployeeID TEXT,
            Memo TEXT, NoDau REAL, isTrongNgay INT, isKhongKM INT, BaseTotal REAL, DateCreate TEXT, ObjectName TEXT, Address TEXT,
            EmployeeName TEXT, ItemID TEXT, Gio TEXT, ObjectInfo TEXT, StatusName TEXT, BackColor INT, StatusID INT, TrangThai TEXT);
        CREATE TABLE WB_OrderDetailTbl(UserAutoID INTEGER PRIMARY KEY, DocumentID TEXT, ItemID TEXT, Ket REAL, Chai REAL,
            GiaChuan REAL, TienChietKhau REAL, UnitPrice REAL, Amount REAL, KhuyenMaiID TEXT, KetKM REAL, ChaiKM REAL, IDLinkSuaGia TEXT);
        CREATE TABLE vItem(ItemID TEXT, ItemName TEXT, Unit TEXT, QuyDoi REAL);
        CREATE TABLE tbHangvekehoachView(DocumentID TEXT, DocumentDate TEXT, BanDo TEXT, TenNguoiGiao TEXT, NguoiGiao TEXT,
            TenTuyen TEXT, SoXe TEXT, Memo TEXT);
        CREATE TABLE tbHangVeKeHoachPhieuBanct(UserAutoid INTEGER PRIMARY KEY, Documentid TEXT, PhieuBan TEXT, NgayBan TEXT,
            ObjectID TEXT, NoDau REAL, SoTienBan REAL, Tongtienchietkhau REAL, TongTien REAL, isDaGiao INT);
        CREATE TABLE vObject(ObjectID TEXT, ObjectName TEXT, Address TEXT, Latitude REAL, Longitude REAL);
        CREATE TABLE tbBannuoc(DocumentID TEXT, DocumentDate TEXT, ObjectID TEXT, EmployeeID TEXT, TongTienBan REAL,
            DuyetHangVe INT, isGuiKho INT);
        CREATE TABLE zz_broken(x INT);
        CREATE VIEW AR_DailyReport2View AS SELECT * FROM zz_broken;
        CREATE TABLE zz_proc_param(proc TEXT, name TEXT, t TEXT, ord INT);
        CREATE TABLE WA_BanHangTongHopTheoNVBHReportStp(EmployeeName TEXT, Mahang TEXT, Tenhang TEXT, Ket INT, Chai INT,
            SoLuong REAL, SoTien REAL, SoTienChietKhau REAL, SoTienSauChietKhau REAL);
        CREATE TABLE WA_KiemTraSoLuongReportStp(Mahang TEXT, Ten TEXT, KetCD INT, ChaiCD INT, SLCD REAL, KetGiao INT,
            ChaiGiao INT, SLGiao REAL, STCD REAL, STGiao REAL);
        """
    )
    menu = [
        ("10", "Đơn hàng", None, None, None, 0), ("1012", "Quản lý đơn hàng", "10", "List", "WA_OrderFrm", 0),
        ("1014", "Phiếu giao hàng", "10", "List", "WA_PhieuGiaoHangFrm", 0),
        ("1016", "Kiểm tra số lương", "10", "Report", "WA_KiemTraSoLuongReport", 0),
        ("1018", "Danh sách trả thưởng bằng hàng", "10", "List", "WA_TraThuongFrm", 1),
        ("20", "Báo cáo bán hàng", None, None, None, 0),
        ("2028", "Sản lượng bán tổng hợp theo NVBH", "20", "Report", "WA_BanHangTongHopTheoNVBHReport", 0),
        ("2030", "Sản lượng bán tổng hợp", "20", "Report", "WA_BanHangTongHopReport", 0),  # store không có -> ẩn
        ("80", "Khách hàng", None, None, None, 0), ("8012", "Cập nhật vị trí và hình ảnh", "80", "List", "WA_DailyReport2Frm", 0),
        ("90", "Hệ thống", None, None, None, 0), ("9008", "Danh sách người dùng", "90", "List", "NguoiDungFrm", 0),
    ]
    c.executemany("INSERT INTO WA_Menu VALUES (?,?,?,'',?,?,?)", menu)
    c.executemany("INSERT INTO WA_UserGroupPermisstion(UserGroupID, MenuID, IsRun, isExportExcel) VALUES (?,?,?,?)",
                  [("Sales", "1012", 1, 0), ("Sales", "2028", 1, 1), ("Sales", "1014", 0, 0)])
    c.executemany("INSERT INTO SY_UserGroup VALUES (?,?,0)", [("Admin", "Quản trị"), ("Sales", "Nhân viên bán hàng")])
    from app.erp import _bms_encrypt_test
    c.executemany("INSERT INTO SY_User VALUES (?,?,?,?,?,?,?,?)", [
        # mật khẩu băm theo đúng thuật toán phần mềm .NET
        ("NQNB07", "Nguyễn Văn Bảy", "Bảy", _bms_encrypt_test("NQNB07", "sanpham7"), "Admin2", None, None, 0),
        ("002RC40104", "Trần Ngọc Linh", "Linh", _bms_encrypt_test("002RC40104", "linh123"), "Sales", "002RC40104", None, 0),
        ("NQNB09", "Đã nghỉ", "Nghỉ", _bms_encrypt_test("NQNB09", "x"), "Admin2", None, None, 1)])
    emps = [("002RC40104", "Trần Ngọc Linh"), ("002RC40101", "Vương Thị Sen")]
    c.executemany("INSERT INTO CF_EmployeeTbl VALUES (?,?)", emps)
    c.executemany("INSERT INTO vEmployee VALUES (?,?)", emps)
    fmt = [("N", "BaseTotal", "Tổng tiền"), ("N", "Chai", "Chai / Lon"), ("N", "ChaiKM", "Chai km"), ("D", "DocumentDate", "Ngày CT"),
           (None, "DocumentID", "Số CT"), (None, "EmployeeID", "Mã nhân viên"), (None, "EmployeeName", "Tên nhân viên"),
           (None, "Gio", "Giờ"), (None, "ItemID", "Mã hàng"), (None, "ItemName", "Tên hàng"), ("N", "Ket", "Két / Thùng"),
           ("N", "KetKM", "Két km"), ("", "Mahang", "Mã hàng"), ("", "ObjectID", "Mã KH"), ("N2", "Soluong", "Số lượng"),
           ("N", "Sotien", "Số tiền"), ("", "TenHang", "Tên hàng"), (None, "ObjectName", "Tên khách hàng"), (None, "Address", "Địa chỉ"),
           ("N", "UnitPrice", "Đơn giá CK"), ("N", "GiaChuan", "Đơn giá"), ("N", "Amount", "Tiền sau C.K"), ("N", "TienChietKhau", "Tiền C.K")]
    c.executemany("INSERT INTO SY_FmtFldTbl(FormatID, FieldName, FormName, CaptionVN) VALUES (?,?,NULL,?)", fmt)
    cfg = [
        ("WA_DailyReport2Frm", "T0", "TV", "AR_DailyReport2View", ""),
        ("WA_OrderFrm", "DFP", "", "DocumentDate", ""),
        ("WA_OrderFrm", "T0", "SO", "DocumentDate desc, DateCreate desc", ""),
        ("WA_OrderFrm", "T0", "SUM", "BaseTotal", ""),
        ("WA_OrderFrm", "T0", "GD2", "DocumentID;DocumentDate;Gio;StatusName;ObjectInfo;ItemID;BaseTotal;EmployeeName", ""),
        ("WA_OrderFrm", "T0", "TN", "WB_OrderTbl", ""), ("WA_OrderFrm", "T0", "PK", "DocumentID", ""),
        ("WA_OrderFrm", "T0", "TV", "WA_OrderView", ""), ("WA_OrderFrm", "T0C1", "A", "StatusName", ""),
        ("WA_OrderFrm", "T0C1", "B", "BackColor", ""),
        ("WA_OrderFrm", "T1", "FKA1", "ItemID", ""), ("WA_OrderFrm", "T1", "FKB1", "ItemID", ""),
        ("WA_OrderFrm", "T1", "GD2", "ItemID;ItemName;Ket;Chai;GiaChuan;TienChietKhau;UnitPrice;Amount;IDLinkSuaGia;KhuyenMaiID;KetKM;ChaiKM", ""),
        ("WA_OrderFrm", "T1", "PK", "UserAutoID", ""), ("WA_OrderFrm", "T1", "SE1", "ItemName, Unit", ""),
        ("WA_OrderFrm", "T1", "SUM", "Amount;KetKM;ChaiKM;Ket;Chai", ""), ("WA_OrderFrm", "T1", "TN", "WB_OrderDetailTbl", ""),
        ("WA_OrderFrm", "T1", "TN1", "vItem", ""),
        ("WA_OrderFrm", "LYT1", "DocumentID", "1;7;1", "01"), ("WA_OrderFrm", "LYT1", "DocumentDate", "4;7;1", "02"),
        ("WA_OrderFrm", "LYT1", "EmployeeID", "1;7;1", "03"), ("WA_OrderFrm", "LYT1", "EmployeeName", "1;7;1", "04"),
        ("WA_OrderFrm", "LYT1", "ObjectID", "1;7;1", "05"), ("WA_OrderFrm", "LYT1", "NoDau", "5;7;1", "06"),
        ("WA_OrderFrm", "LYT1", "ObjectName", "1;7;1", "07"), ("WA_OrderFrm", "LYT1", "Address", "1;7;1", "08"),
        ("WA_OrderFrm", "LYT1", "Phone", "1;7;1", "09"), ("WA_OrderFrm", "LYT1", "Memo", "1;7;2", "10"),
        ("WA_OrderFrm", "LYT1", "DeliveryDate", "4;7;1", "11"), ("WA_OrderFrm", "LYT1", "isTrongNgay", "6;7;1", "12"),
        ("WA_OrderFrm", "LYT1", "isKhongKM", "6;7;1", "13"),
        ("WA_PhieuGiaoHangFrm", "T0", "GD2", "DocumentID;DocumentDate;BanDo;TenNguoiGiao;NguoiGiao;TenTuyen;SoXe;Memo", ""),
        ("WA_PhieuGiaoHangFrm", "T0", "PK", "DocumentID", ""), ("WA_PhieuGiaoHangFrm", "T0", "TN", "tbHangvekehoach", ""),
        ("WA_PhieuGiaoHangFrm", "T0", "TV", "tbHangvekehoachView", ""),
        ("WA_PhieuGiaoHangFrm", "T1", "FKA1", "ObjectID", ""), ("WA_PhieuGiaoHangFrm", "T1", "FKB1", "ObjectID", ""),
        ("WA_PhieuGiaoHangFrm", "T1", "GD2", "isDaGiao;PhieuBan;NgayBan;ObjectID;ObjectName;Address;NoDau;SoTienBan;Tongtienchietkhau;TongTien;Latitude;Longitude", ""),
        ("WA_PhieuGiaoHangFrm", "T1", "PK", "UserAutoID", ""),
        ("WA_PhieuGiaoHangFrm", "T1", "SE1", "ObjectName, Address, Latitude, Longitude", ""),
        ("WA_PhieuGiaoHangFrm", "T1", "SUM", "NoDau;SoTienBan;Tongtienchietkhau;TongTien", ""),
        ("WA_PhieuGiaoHangFrm", "T1", "TN", "tbHangvekehoachPhieuBanct", ""), ("WA_PhieuGiaoHangFrm", "T1", "TN1", "vObject", ""),
    ]
    c.executemany("INSERT INTO SY_FrmCfg(FID, KeyID, SubID, KeyValue, SubValue) VALUES (?,?,?,?,?)", cfg)
    c.executemany("INSERT INTO SY_FrmFltTbl(FormID, KeyID, ColumnID, Caption, Source, ValueColumn, DisplayColumn, DefaultValue, UseLikeOperator) "
                  "VALUES (?,?,?,?,?,?,?,?,0)", [
                      ("WA_OrderFrm", "006", "EmployeeID", None, "Select * from vEmployee", "EmployeeID", "EmployeeName", "{EmployeeID}"),
                      ("WA_OrderFrm", "007", "StatusID", None, "Select * from dmStatusTbl", "StatusID", "StatusName", None),
                      ("WA_PhieuGiaoHangFrm", "006", "EmployeeID", None, "Select * from vEmployee", "EmployeeID", "EmployeeName", "{EmployeeID}"),
                  ])
    c.executemany("INSERT INTO SY_RpTbl VALUES (?,?,?,?,?,?)", [
        ("EmployeeID", "Nhân viên", "Select EmployeeID, EmployeeName From CF_EmployeeTbl Order By EmployeeID", "EmployeeID", "EmployeeID", "EmployeeID;EmployeeName"),
        ("Mahang", None, "Select ItemID as Mahang, ItemName as Tenhang From vItem", "Mahang", "Mahang", "Mahang;Tenhang"),
    ])
    c.executemany("INSERT INTO dmStatusTbl VALUES (?,?)", [(-1, "Đang lên đơn"), (0, "Chờ duyệt"), (1, "Đã duyệt")])
    orders = [
        ("DL260926172435", "2026-09-27 00:00:00", "002RC40104", "", "2026-09-27", "002RC40104", "", 0, 1, 0, 200000,
         "2026-09-27 17:24:00", "Trần Ngọc Linh- BÙ TỔNG", "K35 An Nhơn, Phường 17, Quận Gò Vấp", "Trần Ngọc Linh",
         "10000011, 10000881, BUTONG, ", "17:24", "002RC40104 - Trần Ngọc Linh- BÙ TỔNG</br>K35 An Nhơn, Phường 17, Quận Gò Vấp",
         "Chờ duyệt", -26164, 0, None),
        ("DL260926171537", "2026-09-27 00:00:00", "002RC40101", "", "2026-09-27", "002RC40101", "", 0, 1, 0, 52000,
         "2026-09-27 17:15:00", "Vương Thị Sen- BÙ TỔNG", "K35 An Nhơn", "Vương Thị Sen", "BUTONG, ", "17:15",
         "002RC40101 - Vương Thị Sen- BÙ TỔNG</br>K35 An Nhơn", "Đã duyệt", -7876885, 1, None),
        ("DH240920/001", "2024-09-20 00:00:00", "CT00004726", "", "2024-09-21", "002RC40104", "", 0, 0, 0, 748000,
         "2024-09-20 08:00:00", "TH Anh Hải", "120/58 Thích Quảng Đức", "Trần Ngọc Linh", "10000011, ", "08:00",
         "CT00004726 - TH Anh Hải</br>120/58 Thích Quảng Đức", "Chờ duyệt", -26164, 0, None),
    ]
    c.executemany("INSERT INTO WA_OrderView VALUES (" + ",".join("?" * 22) + ")", orders)
    c.executemany("INSERT INTO vItem VALUES (?,?,?,?)", [("10000011", "Aquafina Chai nhựa 500x24", "Thùng", 24),
                                                          ("10000881", "Revive Chai nhựa 500x24 Lốc 6", "Thùng", 24),
                                                          ("BUTONG", "BÙ TỔNG", "Cái", 1)])
    c.executemany("INSERT INTO WB_OrderDetailTbl(DocumentID, ItemID, Ket, Chai, GiaChuan, TienChietKhau, UnitPrice, Amount, KhuyenMaiID, KetKM, ChaiKM) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
                      ("DL260926172435", "10000011", 0, 0, 92000, 0, 92000, 0, "13", 0, 0),
                      ("DL260926172435", "10000881", 1, 0, 170000, 3000, 167000, 167000, None, 0, 0),
                      ("DL260926172435", "BUTONG", 1, 0, 1, -32999, 33000, 33000, None, 0, 0),
                      ("DL260926171537", "BUTONG", 1, 0, 52000, 0, 52000, 52000, None, 0, 0),
                  ])
    c.execute("INSERT INTO tbHangvekehoachView VALUES (?,?,?,?,?,?,?,?)",
              ("PL068282", "2026-09-28 00:00:00",
               '<a href="/Mapdata.aspx?id=PL068282&id2=1&id3=2&ret=List/1014" class="btn btn-success btn-xs" target="_blank">Mở bản đồ</a>',
               "Trần Ngọc Linh", "002RC40104", "Tuyến 4", "51C-12345", ""))
    c.executemany("INSERT INTO tbHangVeKeHoachPhieuBanct(Documentid, PhieuBan, NgayBan, ObjectID, NoDau, SoTienBan, Tongtienchietkhau, TongTien, isDaGiao) "
                  "VALUES (?,?,?,?,?,?,?,?,?)", [
                      ("PL068282", "SO1", "2026-09-27", "CT00004726", 0, 748000, 0, 748000, 1),
                      ("PL068282", "SO2", "2026-09-27", "CT00003051", 100000, 564000, 4000, 660000, 0),
                  ])
    c.executemany("INSERT INTO vObject VALUES (?,?,?,?,?)", [("CT00004726", "TH Anh Hải", "120/58 Thích Quảng Đức", 10.7991, 106.6822),
                                                             ("CT00003051", "TH Chú Thắng", "42 Thích Quảng Đức", 10.8003, 106.6835)])
    c.executemany("INSERT INTO tbBannuoc VALUES (?,?,?,?,?,?,?)", [
        ("SO1", "2025-03-05 00:00:00", "CT1", "002RC40104", 1000000, 1, 0), ("SO2", "2025-04-08 00:00:00", "CT2", "002RC40101", 2500000, 1, 0),
        ("SO3", "2025-04-08 00:00:00", "CT1", "002RC40104", 500000, 0, 1), ("SO4", "2025-04-02 00:00:00", "CT3", "002RC40104", 700000, 0, 0),
    ])
    c.executemany("INSERT INTO zz_proc_param VALUES (?,?,?,?)", [
        ("WA_BanHangTongHopTheoNVBHReportStp", "@FromDate", "datetime", 1), ("WA_BanHangTongHopTheoNVBHReportStp", "@ToDate", "datetime", 2),
        ("WA_BanHangTongHopTheoNVBHReportStp", "@Mahang", "varchar", 3), ("WA_BanHangTongHopTheoNVBHReportStp", "@EmployeeID", "varchar", 4),
        ("WA_BanHangTongHopTheoNVBHReportStp", "@Objectid", "nvarchar", 5), ("WA_BanHangTongHopTheoNVBHReportStp", "@LoaiXuat", "varchar", 6),
        ("WA_KiemTraSoLuongReportStp", "@Todate", "datetime", 1), ("WA_KiemTraSoLuongReportStp", "@EmployeeID", "varchar", 2),
    ])
    c.executemany("INSERT INTO WA_BanHangTongHopTheoNVBHReportStp VALUES (?,?,?,?,?,?,?,?,?)", [
        ("NVBH : Trần Ngọc Linh", "10000011", "Aquafina Chai nhựa 500x24", 5, 0, 5.0, 459000, 0, 459000),
        ("NVBH : Trần Ngọc Linh", "10000881", "Revive Chai nhựa 500x24 Lốc 6", 2, 6, 2.25, 340000, 6000, 334000),
        ("NVBH : Vương Thị Sen", "10000011", "Aquafina Chai nhựa 500x24", 1, 0, 1.0, 92000, 0, 92000),
    ])
    c.execute("INSERT INTO WA_KiemTraSoLuongReportStp VALUES ('10000011','Aquafina',5,0,120,5,0,120,459000,459000)")
    c.execute("DROP TABLE zz_broken")   # view trỏ tới bảng không còn -> giống lỗi NPPNguyenQuanImage
    add_orders(c)
    cn.commit()
    cn.close()


def add_orders(c) -> None:
    """Cấu hình + dữ liệu sau khi chạy sql/NQW_CapNhatDatabase.sql (PHẦN 01)."""
    c.executescript(
        """
        CREATE TABLE sy_WebLoaiDon(LoaiDon TEXT PRIMARY KEY, TenLoai TEXT, MenuID TEXT, FormName TEXT, TienTo TEXT, KieuSo TEXT,
            NhomKhachHang TEXT, LayGiaSi INT, ChoPhepChietKhau INT, KiemTraCongNo INT, IsSuDung INT);
        CREATE TABLE WB_OrderTbl(DocumentID TEXT, DocumentDate TEXT, ObjectID TEXT, Phone TEXT, DeliveryDate TEXT, EmployeeID TEXT,
            Memo TEXT, isTrongNgay INT, isKhongKM INT, isSelect INT, MaTrangThai INT, f_LoaiDon TEXT);
        CREATE TABLE CF_ObjectTbl(ObjectID TEXT, ObjectName TEXT, Address TEXT, ObjectGroupID TEXT, TuyenBanHang TEXT);
        CREATE TABLE dmHangHoaView(Mahang TEXT, Tenhang TEXT, DvtID TEXT, QuyDoi REAL);
        CREATE TABLE NQW_OrderSiView AS SELECT *, 'Sỉ' AS LoaiDonHang FROM WA_OrderView;
        CREATE TABLE NQW_OrderLeView AS SELECT *, 'Lẻ' AS LoaiDonHang FROM WA_OrderView WHERE DocumentID LIKE 'DL%';
        """
    )
    c.executemany("INSERT INTO sy_WebLoaiDon VALUES (?,?,?,?,?,?,?,?,?,1,1)", [
        ("SI", "Đơn hàng sỉ", "1012", "NQW_DonHangSiFrm", "DH", "NGAY_STT", "WS,WSMIX", 1, 1),
        ("LE", "Đơn hàng lẻ", "1010", "NQW_DonHangLeFrm", "DL", "NGAY_STT", None, 0, 0)])
    c.execute("UPDATE WA_Menu SET VN='Quản lý đơn hàng sỉ', FormName='NQW_DonHangSiFrm' WHERE MenuID='1012'")
    c.execute("INSERT INTO WA_Menu VALUES ('1010','Quản lý đơn hàng lẻ','10','','List','NQW_DonHangLeFrm',0)")
    for fid, view in (("NQW_DonHangSiFrm", "NQW_OrderSiView"), ("NQW_DonHangLeFrm", "NQW_OrderLeView")):
        c.execute("INSERT INTO SY_FrmCfg(FID, KeyID, SubID, KeyValue, SubValue) SELECT ?, KeyID, SubID, "
                  "CASE WHEN KeyID='T0' AND SubID='TV' THEN ? ELSE KeyValue END, SubValue FROM SY_FrmCfg WHERE FID='WA_OrderFrm'", (fid, view))
        c.execute("INSERT INTO SY_FrmFltTbl(FormID, KeyID, ColumnID, Caption, Source, ValueColumn, DisplayColumn, DefaultValue, UseLikeOperator) "
                  "SELECT ?, KeyID, ColumnID, Caption, Source, ValueColumn, DisplayColumn, DefaultValue, UseLikeOperator FROM SY_FrmFltTbl WHERE FormID='WA_OrderFrm'", (fid,))
    c.executemany("INSERT INTO WA_UserGroupPermisstion(UserGroupID, MenuID, IsRun, IsAdd, IsUpdate, IsDelete, isExportExcel) VALUES (?,?,?,?,?,?,?)",
                  [("Sales", "1010", 1, 1, 1, 0, 0)])
    c.executemany("INSERT INTO WB_OrderTbl VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("DL260926172435", "2026-09-27", "002RC40104", "", "2026-09-27", "002RC40104", "", 1, 0, 0, -1, "LE"),
        ("DL260926171537", "2026-09-27", "002RC40101", "", "2026-09-27", "002RC40101", "", 1, 0, 1, 0, "LE")])
    c.executemany("INSERT INTO CF_ObjectTbl VALUES (?,?,?,?,?)", [
        ("002RC40104", "Trần Ngọc Linh- BÙ TỔNG", "K35 An Nhơn", "TH", "002RC40104"),
        ("002RC40101", "Vương Thị Sen- BÙ TỔNG", "K35 An Nhơn", "TH", "002RC40101")])
    c.executemany("INSERT INTO dmHangHoaView VALUES (?,?,?,?)", [("10000011", "Aquafina Chai nhựa 500x24", "PET", 24),
                                                                ("10000881", "Revive Chai nhựa 500x24 Lốc 6", "PET", 24),
                                                                ("BUTONG", "BÙ TỔNG", "Cái", 1)])
