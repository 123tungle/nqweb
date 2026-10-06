/* =====================================================================================
   NQW_GoBo_P01_DonHangSiLe.sql – GỠ BỎ PHẦN 01 (đơn hàng sỉ/lẻ) của NQW_CapNhatDatabase.sql
   KHÔNG xóa đơn hàng đã nhập (WB_OrderTbl / WB_OrderDetailTbl giữ nguyên).
   Cột WB_OrderTbl.f_LoaiDon được giữ lại (xóa cột sẽ mất thông tin sỉ/lẻ của đơn đã nhập);
   muốn xóa hẳn thì bỏ dấu -- ở dòng cuối.
   ===================================================================================== */
USE NppNguyenQuan;
GO
SET NOCOUNT ON;

-- trả lại menu 1012 như trước khi chạy script
DECLARE @cu nvarchar(500) = (SELECT TOP 1 GhiChu FROM dbo.sy_WebCapNhat WHERE TenFile = N'P01_DonHangSiLe#menu1012');
IF @cu IS NOT NULL
    UPDATE dbo.WA_Menu
    SET VN = SUBSTRING(@cu, 4, CHARINDEX(N'|FormName=', @cu) - 4),
        FormName = SUBSTRING(@cu, CHARINDEX(N'|FormName=', @cu) + 10, 100)
    WHERE MenuID = '1012';

DELETE dbo.WA_UserGroupPermisstion WHERE MenuID = '1010';
DELETE dbo.WA_UserPermisstion WHERE MenuID = '1010';
DELETE dbo.WA_Menu WHERE MenuID = '1010' AND FormName = 'NQW_DonHangLeFrm';
DELETE dbo.SY_FrmCfg WHERE FID IN ('NQW_DonHangSiFrm', 'NQW_DonHangLeFrm');
DELETE dbo.SY_FrmFltTbl WHERE FormID IN ('NQW_DonHangSiFrm', 'NQW_DonHangLeFrm');
DELETE dbo.SY_FmtFldTbl WHERE FieldName = 'LoaiDonHang' AND FormName IS NULL;
GO
IF OBJECT_ID('dbo.NQW_DonHang_XoaStp') IS NOT NULL DROP PROCEDURE dbo.NQW_DonHang_XoaStp;
IF OBJECT_ID('dbo.NQW_DonHang_LuuStp') IS NOT NULL DROP PROCEDURE dbo.NQW_DonHang_LuuStp;
IF OBJECT_ID('dbo.NQW_DonHang_LaySoCTStp') IS NOT NULL DROP PROCEDURE dbo.NQW_DonHang_LaySoCTStp;
IF OBJECT_ID('dbo.NQW_DonHang_HangHoaStp') IS NOT NULL DROP PROCEDURE dbo.NQW_DonHang_HangHoaStp;
IF OBJECT_ID('dbo.NQW_DonHang_ThongTinKHStp') IS NOT NULL DROP PROCEDURE dbo.NQW_DonHang_ThongTinKHStp;
IF OBJECT_ID('dbo.NQW_DonHang_KhachHangStp') IS NOT NULL DROP PROCEDURE dbo.NQW_DonHang_KhachHangStp;
IF OBJECT_ID('dbo.NQW_OrderSiView') IS NOT NULL DROP VIEW dbo.NQW_OrderSiView;
IF OBJECT_ID('dbo.NQW_OrderLeView') IS NOT NULL DROP VIEW dbo.NQW_OrderLeView;
IF OBJECT_ID('dbo.NQW_LoaiDonCuaKhachFnc') IS NOT NULL DROP FUNCTION dbo.NQW_LoaiDonCuaKhachFnc;
IF OBJECT_ID('dbo.sy_WebLoaiDon') IS NOT NULL DROP TABLE dbo.sy_WebLoaiDon;
DELETE dbo.sy_WebCapNhat WHERE TenFile LIKE N'P01_DonHangSiLe%';
-- ALTER TABLE dbo.WB_OrderTbl DROP COLUMN f_LoaiDon;
PRINT N'Đã gỡ PHẦN 01 – đơn hàng sỉ / lẻ';
GO
