# Web Nguyên Quân (bản viết lại) – Hướng dẫn

Đây là bản viết lại web quản lý `nguyenquan.bms79.com`. Web chạy trên máy của bạn và **đọc thẳng database NppNguyenQuan**.

Web này **dùng lại đúng cấu hình của web cũ** có sẵn trong database, nên thêm hay sửa menu/báo cáo ở database là web mới tự nhận:

| Cấu hình | Nằm ở đâu |
|---|---|
| Menu | `WA_Menu` |
| Quyền theo nhóm | `WA_UserGroupPermisstion` |
| Màn hình danh sách | `SY_FrmCfg`, `SY_FrmFltTbl` |
| Tiêu đề cột | `SY_FmtFldTbl` |
| Tham số báo cáo | `SY_RpTbl` |
| Báo cáo | store `<FormName>Stp` |

**Web chỉ ghi đúng một chỗ: đơn hàng sỉ/lẻ.** Thêm, sửa, xóa đơn đi qua các store `NQW_DonHang_*` và chỉ ghi vào `WB_OrderTbl` / `WB_OrderDetailTbl`. Mọi phần khác (danh sách, báo cáo, trang chủ) chỉ đọc: câu lệnh là SELECT hoặc chạy store báo cáo, và luôn được hủy (rollback) sau khi đọc xong. Tài khoản đăng nhập web và nhật ký lưu riêng trong file `data\nqweb_app.sqlite3`.

## Đăng nhập bằng tài khoản nhân viên trong phần mềm (`SY_User`)

Nhân viên đăng nhập web bằng **đúng tài khoản và mật khẩu trong phần mềm bán hàng** (bảng `SY_User`). Web không lưu và không đọc được mật khẩu gốc: mật khẩu trong `SY_User` là **băm một chiều (MD5 có muối)**. Khi nhân viên gõ mật khẩu, web băm lại theo đúng thuật toán của phần mềm rồi so sánh — giống hệt cách phần mềm kiểm tra.

Thứ tự kiểm tra khi đăng nhập:

1. Tài khoản riêng của web trong `data\nqweb_app.sqlite3` (ví dụ `admin` để quản trị web).
2. Nếu không khớp, kiểm tra tài khoản trong `SY_User`.

Quy tắc cho tài khoản `SY_User`:

- **Nhóm quyền** = `SY_User.UserGroupID`. Menu hiện theo `WA_UserGroupPermisstion` của nhóm đó (giống phần mềm).
- Nhóm thuộc danh sách quản trị (mặc định `Admin, Admin1, Admin2, Admin3`) thì được quyền quản trị web, xem đủ menu. Đổi danh sách này ở `config.ini`, mục `[app] bms_admin_groups`.
- **Chỉ xem dữ liệu của mình:** nếu `SY_User.EmployeeID` có giá trị và tài khoản không phải nhóm quản trị, người đó chỉ xem được dữ liệu của nhân viên ấy. Muốn giới hạn một nhân viên bán hàng, điền `EmployeeID` cho họ trong phần mềm.
- Tài khoản bị khóa trong phần mềm (`Disable = 1`) thì không đăng nhập web được.
- Đổi mật khẩu của tài khoản nhân viên làm **trong phần mềm**, web không đổi. Web nhận mật khẩu mới ngay lần đăng nhập sau.

Nếu mật khẩu có ký tự tiếng Việt có dấu mà đăng nhập không được, sửa `config.ini` mục `[app] bms_pass_encoding` (thử `utf-8`, `latin-1`, hoặc `windows-1258`).

Không cần chạy thêm SQL cho phần này — chỉ là cách web kiểm tra mật khẩu.

## Thay đổi database: 1 file duy nhất `sql\NQW_CapNhatDatabase.sql`

Mọi thay đổi database cho web (bảng, cột, store, menu) đều gộp trong file này.

1. Mở file trong SSMS, đăng nhập bằng `sa`.
2. Bấm **F5**.
3. Tắt và chạy lại `run.bat`, hoặc bấm tên tài khoản → *Làm mới cấu hình từ database*.

File chạy lại nhiều lần được và không xóa dữ liệu. Mỗi lần chạy được ghi vào bảng `sy_WebCapNhat`. Khi lên VPS, chỉ cần chạy lại đúng file này trên database của VPS. Mỗi lần AI thay đổi database về sau sẽ thêm "PHẦN 02, 03…" vào cuối file này.

| Phần | Nội dung | Gỡ bỏ |
|---|---|---|
| 01 | Form nhập đơn hàng sỉ / lẻ: bảng `sy_WebLoaiDon`, cột `WB_OrderTbl.f_LoaiDon`, hàm `NQW_LoaiDonCuaKhachFnc`, view `NQW_OrderSiView`/`NQW_OrderLeView`, store `NQW_DonHang_*`, menu 1010 (lẻ) và 1012 (sỉ) | `sql\NQW_GoBo_P01_DonHangSiLe.sql` |

## Nhập đơn hàng sỉ / lẻ

Vào **Quản lý đơn hàng lẻ** hoặc **Quản lý đơn hàng sỉ** → **+ Thêm đơn…**

1. Chọn nhân viên. Tài khoản đã gán mã nhân viên thì tự điền và không đổi được.
2. Gõ để tìm khách hàng. Chỉ hiện khách **do nhân viên đó quản lý** (`CF_ObjectTbl.TuyenBanHang`) và **đúng loại khách** của màn hình.
3. Thêm dòng hàng: chọn mã, nhập két/chai, KM. Giá chuẩn tự lấy theo bảng giá (sỉ = `DonGiaSi`, lẻ = `DonGia`).
4. Chọn một trong hai cách lưu:
   - **Lưu nháp**: trạng thái *Đang lên đơn*.
   - **Lưu & gửi duyệt**: trạng thái *Chờ duyệt*, phần mềm Windows duyệt như đơn web cũ.

Giống web cũ: **chỉ sửa hoặc xóa được đơn "Đang lên đơn"**. Đơn đã gửi duyệt (*Chờ duyệt*) hoặc đã duyệt thì không sửa, không xóa được.

Ô **CTKM** gợi ý các chương trình khuyến mãi còn hiệu lực theo ngày đơn (hàm `B_KhuyenMaiTheoThoiGianFnc`, giống web cũ).

**Khác nhau giữa sỉ và lẻ** (sửa trong bảng `sy_WebLoaiDon`, không cần sửa code):

| | Sỉ (`SI`) | Lẻ (`LE`) |
|---|---|---|
| Khách hàng | nhóm khách `WS, WSMIX, WSC1, WSC2, WSDEPO, WSBB` | các nhóm còn lại |
| Giá | `DonGiaSi` | `DonGia` |
| Chiết khấu | được nhập | không |
| Số chứng từ | `DH` + yyMMdd + `001` (vd. DH260927001, giống web thật) | `DL` + yyMMdd + `001` (vd. DL260927010, giống web thật) |
| Kiểm tra nợ vượt mức / quá hạn | có | có |

**Kiểm tra khi lưu:**

- Dùng lại đúng store `WB_Order_CheckSaveStp` của web cũ để kiểm tra nợ và ngày giao.
- Không bán dưới giá chuẩn (trừ `TruGiaMin` trong `SY_Setup`).
- Mã hàng phải có trong bảng giá, số lượng phải > 0.
- Khách phải đúng loại và đúng nhân viên. Tài khoản quản trị được bỏ qua kiểm tra nhân viên.

Thành tiền tính đúng công thức `WB_OrderDetail_AfterSaveStp` cũ: `Két × (giá − CK) + Chai × làm tròn((giá − CK) / quy đổi)`.

**Quyền:**

- Người dùng thuộc nhóm có quyền thì được thêm, sửa, xóa theo `IsAdd`, `IsUpdate`, `IsDelete` trong `WA_UserGroupPermisstion`.
- Quản trị web được làm tất cả.

## Chức năng

- **Trang chủ:**
  - doanh thu ngày và tháng, số phiếu, số khách mua, số đơn web chờ duyệt;
  - biểu đồ doanh thu 6 tháng;
  - top 10 nhân viên bán hàng.

  Số liệu lấy từ `tbBannuoc`, chỉ tính phiếu có DuyetHangVe = 1 hoặc isGuiKho = 1.
- **Màn hình danh sách** (Quản lý đơn hàng, Phiếu giao hàng…):
  - lọc từ ngày–đến ngày, nhân viên, trạng thái, tìm nhanh;
  - bấm vào một dòng để xem chi tiết phiếu;
  - phiếu giao hàng có bản đồ các điểm giao và nút chỉ đường Google Maps;
  - xuất Excel;
  - trên điện thoại, danh sách tự hiện dạng thẻ.
- **Báo cáo:** mọi báo cáo trên menu web đều chạy bằng store gốc, ô điều kiện tự tạo theo tham số của store. Báo cáo được nhóm theo nhân viên và có dòng cộng từng nhóm, cộng tổng. Có xuất Excel.
- **Người dùng web** (chỉ quản trị):
  - tạo tài khoản, gán **nhóm quyền** (lấy danh sách nhóm từ `SY_UserGroup`, quyền menu theo `WA_UserGroupPermisstion`);
  - gán **mã nhân viên** để tài khoản đó chỉ xem được dữ liệu của nhân viên ấy.
- **Nhật ký web:** ai đăng nhập, xem báo cáo, xuất Excel lúc nào.

## Cài lần đầu (máy LTT)

1. Cần Python 3.11 (đã cài khi làm app Quét Chữ Kho). Nếu chưa có, tải ở https://www.python.org/downloads/windows/ và nhớ tick **Add python.exe to PATH** khi cài.
2. Giải nén thư mục `WebNguyenQuan`, ví dụ vào `D:\WebNguyenQuan`.
3. Nhấp đúp **`setup.bat`**:
   - Script cài thư viện, mất khoảng 1–3 phút.
   - Notepad mở file `config.ini`. Điền mật khẩu `sa` (hoặc tài khoản chỉ đọc, xem phần dưới), **Lưu**, đóng Notepad.
   - Script tự chọn driver ODBC, kết nối thử và in ra danh sách menu đọc được (dòng `OK` = chạy được).
4. Nhấp đúp **`run.bat`**. Trình duyệt tự mở `http://localhost:8090`.
5. Đăng nhập **admin / admin123**, rồi vào tên tài khoản (góc phải) → **Đổi mật khẩu** ngay.
6. Vào **Người dùng web** để tạo tài khoản cho nhân viên.

**Dùng từ máy khác hoặc điện thoại cùng mạng:**

1. Chuột phải `mo_firewall.bat` → *Run as administrator*.
2. Mở `http://<IPv4 của máy LTT>:8090`. Cửa sổ `run.bat` có in sẵn địa chỉ IPv4 này.

## Nên dùng tài khoản SQL riêng cho web (`nqweb_doc`)

Mở `sql\tao_login_chi_doc.sql` trong SSMS, đổi mật khẩu trong file, rồi chạy bằng tài khoản `sa`. Sau đó trong `config.ini` sửa `user = nqweb_doc` và `password = <mật khẩu vừa đặt>`.

Tài khoản này đọc được mọi bảng, chạy được các store báo cáo trên menu và các store nhập đơn `NQW_DonHang_*`. Nó không ghi trực tiếp vào bảng nào, nên kể cả khi web bị lỗi cũng không sửa được dữ liệu khác. Sau khi chạy `NQW_CapNhatDatabase.sql` hoặc thêm báo cáo mới vào `WA_Menu`, chạy lại script này để cấp quyền cho store mới.

## Thêm báo cáo mới lên web

1. Viết store tên `<TenBaoCao>ReportStp`, ví dụ `NQ_CongNoTheoDieuKienNoReportStp`.
2. Thêm 1 dòng vào `WA_Menu`: `FormKey = 'Report'`, `FormName = '<TenBaoCao>Report'` (không có chữ Stp), `Parent` = mã nhóm menu, `isDisable = 0`.
3. Cấp quyền cho nhóm trong `WA_UserGroupPermisstion` (IsRun = 1; muốn cho xuất Excel thì isExportExcel = 1).
4. Trên web: tên tài khoản → **Làm mới cấu hình từ database** (hoặc chờ 5 phút). Menu mới sẽ hiện ra.

Tiêu đề cột lấy theo `SY_FmtFldTbl` (FieldName → CaptionVN). Tên tham số và danh sách chọn lấy theo `SY_RpTbl` (ParaName).

## Chuyển lên VPS / database thật

Database đang dùng trên máy LTT là bản sao cũ: đơn web đến 20/09/2024, bán hàng đến 08/04/2025. Web cũ thì đang chạy trên database mới hơn đặt trên server của bms79. Muốn web mới xem số liệu hiện tại:

- **Cách 1:** Sửa `server`, `database`, `user`, `password` trong `config.ini` trỏ tới SQL Server thật, rồi chạy `python kiem_tra.py` để kiểm tra.
- **Cách 2:** Đưa cả thư mục lên VPS (Windows Server) và cài như bước trên.

Khi mở ra Internet:

- dùng HTTPS: IIS (URL Rewrite + ARR) hoặc Caddy làm cổng trước, chuyển về `http://127.0.0.1:8090`;
- chỉ mở cổng 443, **không mở cổng SQL 1433**.

Muốn web tự chạy khi khởi động máy, dùng NSSM (`nssm install WebNguyenQuan`) trỏ tới `run.bat`.

## ⚠ BẮT BUỘC trước khi đưa lên VPS / mở ra Internet

Chưa làm các mục dưới đây thì chỉ dùng trong mạng nội bộ. Khi chuẩn bị lên VPS, nhắn AI: **"làm các việc bảo mật trước khi lên VPS cho web Nguyên Quân"**.

1. **Khóa đăng nhập tạm thời** khi nhập sai mật khẩu nhiều lần (chống dò mật khẩu). *(AI sửa code)*
2. **Ẩn chi tiết lỗi SQL** với người dùng thường, chỉ quản trị mới xem được. *(AI sửa code)*
3. **Mã hóa mật khẩu SQL** trong `config.ini` bằng Windows DPAPI. *(AI sửa code)*
4. Dùng tài khoản SQL riêng **`nqweb_doc`** (`sql\tao_login_chi_doc.sql`), không dùng `sa`.
5. Bật **HTTPS**: IIS (URL Rewrite + ARR) hoặc Caddy làm cổng trước, chuyển về `http://127.0.0.1:8090`. **Không** để IIS phục vụ thẳng thư mục web, không đặt web trong `wwwroot`.
6. Tường lửa: chỉ mở cổng **443**. Đóng 8090 và **1433 (SQL)** với Internet.
7. Khóa quyền thư mục web (NTFS): chỉ tài khoản chạy web và admin đọc được. Chỉ admin có tài khoản Remote Desktop, đặt mật khẩu mạnh.
8. Đổi các mật khẩu đã từng gửi trong lúc trao đổi với AI: `sa`, Admin2 (web cũ), admin (web mới).

## Kiểm tra tự động

```
.venv\Scripts\activate
pip install pytest httpx
python -m pytest -q tests
```

Bộ test dùng database SQLite giả lập, chép cấu hình web từ NppNguyenQuan, và không đụng SQL Server.

## Chưa làm ở bản này

- **Duyệt đơn** vẫn làm trên phần mềm Windows như trước.
- **Tự tính khuyến mãi.** Trong database, các đoạn tính khuyến mãi tự động của web cũ đang tắt (được chú thích bỏ qua). Web mới cho nhập tay két/chai KM và mã CTKM trên từng dòng.
- **"Kiểm tra số lượng tổng hợp" (1017)** chưa có trong database ở LTT.
- **"Cập nhật vị trí và hình ảnh" (8012).** Trên web thật màn hình này đang lỗi, vì thiếu database `NPPNguyenQuanImage`.
