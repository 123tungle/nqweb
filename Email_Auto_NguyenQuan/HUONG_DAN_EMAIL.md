# Gửi email báo cáo bán hàng cuối ngày (PHẦN 02)

Tự động gửi email cho Sếp một **báo cáo bán hàng cuối ngày** (đính kèm **PDF**, hoặc **Excel**, hoặc cả hai),
**giờ gửi đổi lúc nào cũng được**, và có **tùy chọn gửi Chủ nhật hay không**.

## Cơ chế
- Logic *"tới giờ chưa / hôm nay Chủ nhật có gửi không / đã gửi chưa"* nằm trong **store SQL** (`NQW_BaoCaoEmail_CanGuiStp`) và **bảng cấu hình** `NQW_BaoCaoEmailCf`.
- Một **script Python** (`tien_ich/bao_cao_cuoi_ngay.py`) chạy mỗi ~10 phút: tới giờ đã đặt thì gọi store lấy số liệu, dựng PDF/Excel rồi gửi mail, và đánh dấu để **không gửi trùng** trong ngày.
- **Không cần cài Database Mail** — script gửi thẳng qua SMTP (Gmail hoặc mail công ty). (Database Mail chỉ là cách khác nếu sau này muốn chính SQL Server đứng ra gửi.)

## Nội dung email
- **Tổng quan**: doanh số bán, số phiếu, số khách, tiền thu tại điểm bán, thu công nợ, tổng thu, công nợ phát sinh, số đơn web sỉ/lẻ.
- **Doanh số & công nợ theo nhân viên** (xếp hạng theo doanh số) + dòng tổng cộng.
- Sau này cần thêm báo cáo thì bổ sung vào store `NQW_BaoCaoCuoiNgay_DuLieuStp` và script, không phải làm lại từ đầu.

---

## Cài đặt (làm 1 lần trên máy chủ)

### Bước 1 — Thư viện Python
Trong thư mục web chạy:
```
pip install fpdf2 openpyxl
```
(hoặc `pip install -r requirements.txt`)

### Bước 2 — Khai báo SMTP trong `config.ini`, mục `[email]`
Ví dụ dùng Gmail:
```
[email]
host = smtp.gmail.com
port = 587
use_ssl = false
use_tls = true
user = email_cua_ban@gmail.com
password = <mật khẩu ứng dụng 16 ký tự>
from = email_cua_ban@gmail.com
```
> Gmail: vào Google Account → Security → bật 2‑Step Verification → **App passwords** → tạo mật khẩu ứng dụng, dán vào `password`.
> **Không** dùng mật khẩu đăng nhập Gmail thường. Mail công ty (Office365/hosting) thì điền host/port do bên mail cung cấp.

### Bước 3 — Cấu hình người nhận, giờ gửi (bảng `NQW_BaoCaoEmailCf`)
Chạy trong SSMS (đổi lại email + giờ cho đúng):
```sql
UPDATE dbo.NQW_BaoCaoEmailCf
SET EmailNhan  = N'sep@congty.com',      -- nhiều người: ngăn bằng ; ví dụ N'a@x.com; b@y.com'
    EmailCC    = N'',                    -- CC nếu cần
    GioGui     = '18:00',                -- GIỜ GỬI (đổi lúc nào cũng được)
    GuiChuNhat = 0,                      -- 0 = KHÔNG gửi Chủ nhật, 1 = gửi cả Chủ nhật
    DinhDang   = 'PDF',                  -- 'PDF' | 'EXCEL' | 'PDF_EXCEL'
    SoNgayTre  = 0,                      -- 0 = báo cáo hôm nay; 1 = báo cáo hôm qua
    BatTat     = 1                       -- 1 = BẬT gửi tự động
WHERE ID = 1;
```

### Bước 4 — Chạy thử (chưa cần chờ tới giờ)
```
REM Gửi 1 mail thử để kiểm tra SMTP
python tien_ich\bao_cao_cuoi_ngay.py --test-email

REM Chỉ tạo file PDF/Excel của 1 ngày cụ thể, KHÔNG gửi (xem trong data\bao_cao\)
python tien_ich\bao_cao_cuoi_ngay.py --ngay 2025-04-05 --preview

REM Gửi ngay báo cáo hôm nay, bỏ qua canh giờ
python tien_ich\bao_cao_cuoi_ngay.py --force
```

### Bước 5 — Hẹn giờ tự động (chọn 1 trong 2)

**Cách A — Windows Task Scheduler (đơn giản, khuyến nghị).** Mở CMD *Run as Administrator*, sửa đường dẫn cho đúng rồi chạy:
```
schtasks /Create /TN "NQW Bao cao cuoi ngay" ^
 /TR "C:\WebNguyenQuan\tien_ich\bao_cao_cuoi_ngay.bat" ^
 /SC MINUTE /MO 10 /ST 06:00 /RL HIGHEST /F
```
Cứ 10 phút chạy 1 lần; script tự biết tới giờ mới gửi và mỗi ngày chỉ gửi 1 lần.

**Cách B — SQL Server Agent job.** Mở `sql\tao_job_bao_cao_SQLAgent.sql`, sửa đường dẫn `@duongdan`, chạy bằng quyền sysadmin.

---

## Đổi giờ / bật tắt / gửi Chủ nhật về sau
Chỉ 1 câu lệnh, **không phải sửa job hay script**:
```sql
-- Đổi giờ gửi sang 17:30
UPDATE dbo.NQW_BaoCaoEmailCf SET GioGui = '17:30' WHERE ID = 1;
-- Cho gửi cả Chủ nhật
UPDATE dbo.NQW_BaoCaoEmailCf SET GuiChuNhat = 1 WHERE ID = 1;
-- Tạm ngừng gửi
UPDATE dbo.NQW_BaoCaoEmailCf SET BatTat = 0 WHERE ID = 1;
-- Gửi kèm cả Excel
UPDATE dbo.NQW_BaoCaoEmailCf SET DinhDang = 'PDF_EXCEL' WHERE ID = 1;
```

## Các cột bảng `NQW_BaoCaoEmailCf`
| Cột | Ý nghĩa |
|---|---|
| BatTat | 1 = bật gửi tự động, 0 = tắt |
| EmailNhan | Email người nhận (nhiều người ngăn bằng `;` hoặc `,`) |
| EmailCC | Email CC (không bắt buộc) |
| GioGui | Giờ gửi dạng `HH:mm` (vd `18:00`) |
| GuiChuNhat | 0 = không gửi Chủ nhật, 1 = gửi cả CN |
| DinhDang | `PDF` \| `EXCEL` \| `PDF_EXCEL` |
| TieuDe | Tiêu đề mail, `{Ngay}` sẽ thay bằng ngày báo cáo |
| SoNgayTre | 0 = báo cáo hôm nay, 1 = báo cáo hôm qua |
| LanGuiCuoi / ThoiDiemGuiCuoi | Hệ thống tự ghi, dùng để chống gửi trùng |

## Bảo mật
- Mật khẩu ứng dụng SMTP nằm trong `config.ini` — giữ kín, khóa quyền thư mục web (giống các mục bảo mật khi lên VPS).
- Khi đưa lên VPS: chạy lại `sql\NQW_CapNhatDatabase.sql` (đã gồm PHẦN 02) là có sẵn bảng + store.
