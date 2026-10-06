/* Gỡ PHẦN 02 – Gửi email báo cáo cuối ngày. Chạy khi muốn hoàn tác PHẦN 02. */
IF OBJECT_ID('dbo.NQW_BaoCaoCuoiNgay_DuLieuStp')      IS NOT NULL DROP PROCEDURE dbo.NQW_BaoCaoCuoiNgay_DuLieuStp;
IF OBJECT_ID('dbo.NQW_BaoCaoEmail_CauHinhStp')        IS NOT NULL DROP PROCEDURE dbo.NQW_BaoCaoEmail_CauHinhStp;
IF OBJECT_ID('dbo.NQW_BaoCaoEmail_CanGuiStp')         IS NOT NULL DROP PROCEDURE dbo.NQW_BaoCaoEmail_CanGuiStp;
IF OBJECT_ID('dbo.NQW_BaoCaoEmail_DanhDauDaGuiStp')   IS NOT NULL DROP PROCEDURE dbo.NQW_BaoCaoEmail_DanhDauDaGuiStp;
IF OBJECT_ID('dbo.NQW_BaoCaoEmailCf')                 IS NOT NULL DROP TABLE dbo.NQW_BaoCaoEmailCf;
DELETE FROM dbo.sy_WebCapNhat WHERE TenFile = N'P02_EmailBaoCaoCuoiNgay';
PRINT N'Đã gỡ PHẦN 02 – email báo cáo cuối ngày';
GO
