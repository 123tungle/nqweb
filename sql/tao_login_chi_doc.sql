/* Tạo tài khoản SQL cho web: nqweb_doc – đọc mọi bảng; KHÔNG ghi trực tiếp được bảng nào,
   chỉ ghi đơn hàng qua các store NQW_DonHang_* (form nhập đơn sỉ/lẻ)
   Chạy trong SSMS bằng tài khoản sa. Đổi mật khẩu bên dưới trước khi chạy.
   Chạy lại nhiều lần được (khi có store báo cáo mới, chạy lại để cấp quyền chạy store). */
USE master;
IF SUSER_ID(N'nqweb_doc') IS NULL
    CREATE LOGIN nqweb_doc WITH PASSWORD = N'DoiMatKhau@123', CHECK_POLICY = OFF, DEFAULT_DATABASE = NppNguyenQuan;
GO
USE NppNguyenQuan;
IF USER_ID(N'nqweb_doc') IS NULL
    CREATE USER nqweb_doc FOR LOGIN nqweb_doc;
ALTER ROLE db_datareader ADD MEMBER nqweb_doc;   -- đọc mọi bảng/view, KHÔNG có quyền ghi
GO
/* Quyền chạy các store báo cáo đang gắn trên menu web (WA_Menu, FormKey = 'Report') */
DECLARE @sql nvarchar(max) = N'';
SELECT @sql = @sql + N'GRANT EXECUTE ON dbo.' + QUOTENAME(p.name) + N' TO nqweb_doc;' + CHAR(10)
FROM sys.procedures p
WHERE p.name IN (SELECT FormName + 'Stp' FROM dbo.WA_Menu WHERE FormKey = 'Report')
   OR p.name LIKE 'NQW[_]%';   -- store nhập đơn sỉ/lẻ: chỉ ghi được vào WB_OrderTbl/WB_OrderDetailTbl thông qua các store này
PRINT @sql;
EXEC sp_executesql @sql;
GO
