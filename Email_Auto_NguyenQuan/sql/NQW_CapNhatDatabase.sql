/* =====================================================================================
   NQW_CapNhatDatabase.sql – TẤT CẢ thay đổi database cho Web Nguyên Quân (gộp 1 file)
   ---------------------------------------------------------------------------------------
   Cách dùng: mở file trong SSMS (đăng nhập sa) → F5. Đang test trên LTT\SQL2016; khi đưa
   lên VPS chỉ cần chạy lại đúng file này trên database NppNguyenQuan của VPS.
   Chạy lại nhiều lần được: phần nào đã có thì bỏ qua, KHÔNG xóa dữ liệu.
   Mỗi lần chạy được ghi vào bảng sy_WebCapNhat (xem: SELECT * FROM sy_WebCapNhat).
   Mỗi thay đổi mới về sau sẽ được THÊM vào cuối file này thành "PHẦN 02, 03…".

   PHẦN 01 – Form nhập ĐƠN HÀNG SỈ / ĐƠN HÀNG LẺ   (gỡ bỏ: NQW_GoBo_P01_DonHangSiLe.sql)

   Thay đổi database:
     1. Bảng mới  sy_WebLoaiDon            : cấu hình từng loại đơn (sỉ / lẻ)
     2. Cột mới   WB_OrderTbl.f_LoaiDon    : 'SI' / 'LE' (đơn cũ để NULL, tự xếp loại theo nhóm khách)
     3. Hàm       NQW_LoaiDonCuaKhachFnc   : khách hàng thuộc loại đơn nào (theo CF_ObjectTbl.ObjectGroupID)
     4. View      NQW_OrderSiView, NQW_OrderLeView : danh sách đơn sỉ / lẻ (dựa trên WA_OrderView)
     5. Store     NQW_DonHang_KhachHangStp, NQW_DonHang_ThongTinKHStp, NQW_DonHang_HangHoaStp,
                  NQW_DonHang_LaySoCTStp, NQW_DonHang_LuuStp, NQW_DonHang_XoaStp
     6. Menu web  1010 "Quản lý đơn hàng lẻ" (mới), 1012 đổi thành "Quản lý đơn hàng sỉ"
                  + cấu hình màn hình SY_FrmCfg / SY_FrmFltTbl (chép từ WA_OrderFrm)
                  + quyền WA_UserGroupPermisstion của 1010 chép từ 1012
     7. Ghi nhận lần chạy vào bảng sy_WebCapNhat
   ===================================================================================== */
USE NppNguyenQuan;
GO
SET NOCOUNT ON;
GO

/* ---------- 0. Bảng ghi nhận các lần cập nhật database cho web ---------- */
IF OBJECT_ID('dbo.sy_WebCapNhat') IS NULL
    CREATE TABLE dbo.sy_WebCapNhat (
        TenFile   nvarchar(200) NOT NULL,
        NgayChay  datetime      NOT NULL CONSTRAINT DF_sy_WebCapNhat_NgayChay DEFAULT (GETDATE()),
        NguoiChay nvarchar(128) NOT NULL CONSTRAINT DF_sy_WebCapNhat_NguoiChay DEFAULT (SUSER_SNAME()),
        GhiChu    nvarchar(500) NULL
    );
GO

/* ---------- 1. Cấu hình loại đơn ---------- */
IF OBJECT_ID('dbo.sy_WebLoaiDon') IS NULL
    CREATE TABLE dbo.sy_WebLoaiDon (
        LoaiDon          varchar(10)   NOT NULL CONSTRAINT PK_sy_WebLoaiDon PRIMARY KEY,
        TenLoai          nvarchar(100) NOT NULL,
        MenuID           varchar(50)   NOT NULL,           -- WA_Menu.MenuID của màn hình
        FormName         varchar(50)   NOT NULL,           -- WA_Menu.FormName = SY_FrmCfg.FID
        TienTo           varchar(10)   NOT NULL,           -- tiền tố số chứng từ
        KieuSo           varchar(20)   NOT NULL,           -- NGAY_STT : TienTo + yyMMdd + 001 (giống web cũ: DH260927001, DL260927010)
                                                           -- THOI_GIAN: TienTo + yyMMddHHmmss
        NhomKhachHang    nvarchar(500) NULL,               -- các CF_ObjectTbl.ObjectGroupID, cách nhau dấu phẩy
                                                           -- để trống = khách không thuộc nhóm của loại đơn khác
        LayGiaSi         bit NOT NULL CONSTRAINT DF_sy_WebLoaiDon_LayGiaSi DEFAULT (0),   -- 1 = giá DonGiaSi, 0 = DonGia
        ChoPhepChietKhau bit NOT NULL CONSTRAINT DF_sy_WebLoaiDon_CK DEFAULT (0),
        KiemTraCongNo    bit NOT NULL CONSTRAINT DF_sy_WebLoaiDon_CN DEFAULT (1),        -- chặn khách nợ vượt mức / quá hạn
        IsSuDung         bit NOT NULL CONSTRAINT DF_sy_WebLoaiDon_SD DEFAULT (1),
        GhiChu           nvarchar(500) NULL
    );
GO
IF NOT EXISTS (SELECT 1 FROM dbo.sy_WebLoaiDon WHERE LoaiDon = 'SI')
    INSERT dbo.sy_WebLoaiDon (LoaiDon, TenLoai, MenuID, FormName, TienTo, KieuSo, NhomKhachHang, LayGiaSi, ChoPhepChietKhau, KiemTraCongNo, GhiChu)
    VALUES ('SI', N'Đơn hàng sỉ', '1012', 'NQW_DonHangSiFrm', 'DH', 'NGAY_STT', N'WS,WSMIX,WSC1,WSC2,WSDEPO,WSBB', 1, 1, 1,
            N'Khách sỉ = nhóm khách WS*. Giá sỉ (DonGiaSi), được chiết khấu.');
IF NOT EXISTS (SELECT 1 FROM dbo.sy_WebLoaiDon WHERE LoaiDon = 'LE')
    INSERT dbo.sy_WebLoaiDon (LoaiDon, TenLoai, MenuID, FormName, TienTo, KieuSo, NhomKhachHang, LayGiaSi, ChoPhepChietKhau, KiemTraCongNo, GhiChu)
    VALUES ('LE', N'Đơn hàng lẻ', '1010', 'NQW_DonHangLeFrm', 'DL', 'NGAY_STT', NULL, 0, 0, 1,
            N'Khách lẻ = các nhóm khách còn lại. Giá lẻ (DonGia), không chiết khấu.');
GO

/* ---------- 2. Cột loại đơn trong WB_OrderTbl ---------- */
IF COL_LENGTH('dbo.WB_OrderTbl', 'f_LoaiDon') IS NULL
    ALTER TABLE dbo.WB_OrderTbl ADD f_LoaiDon varchar(10) NULL;
GO

/* ---------- 3. Hàm: khách hàng thuộc loại đơn nào ---------- */
IF OBJECT_ID('dbo.NQW_LoaiDonCuaKhachFnc') IS NULL
    EXEC ('CREATE FUNCTION dbo.NQW_LoaiDonCuaKhachFnc (@ObjectID varchar(50)) RETURNS varchar(10) AS BEGIN RETURN NULL END');
GO
ALTER FUNCTION dbo.NQW_LoaiDonCuaKhachFnc (@ObjectID varchar(50))
RETURNS varchar(10)
AS
BEGIN
    DECLARE @Nhom nvarchar(100), @Loai varchar(10);
    SELECT @Nhom = LTRIM(RTRIM(COALESCE(ObjectGroupID, ''))) FROM dbo.CF_ObjectTbl WHERE ObjectID = @ObjectID;
    IF @Nhom IS NULL RETURN NULL;   -- không có khách này

    SELECT TOP 1 @Loai = L.LoaiDon
    FROM dbo.sy_WebLoaiDon L
        CROSS APPLY STRING_SPLIT(COALESCE(L.NhomKhachHang, N''), N',') S
    WHERE L.IsSuDung = 1 AND @Nhom <> N'' AND LTRIM(RTRIM(S.value)) = @Nhom
    ORDER BY L.LoaiDon;

    IF @Loai IS NULL
        SELECT TOP 1 @Loai = LoaiDon FROM dbo.sy_WebLoaiDon
        WHERE IsSuDung = 1 AND LTRIM(RTRIM(COALESCE(NhomKhachHang, N''))) = N''
        ORDER BY LoaiDon;

    RETURN @Loai;
END
GO

/* ---------- 4. View danh sách đơn sỉ / lẻ ---------- */
IF OBJECT_ID('dbo.NQW_OrderSiView') IS NULL EXEC ('CREATE VIEW dbo.NQW_OrderSiView AS SELECT 1 AS x');
GO
ALTER VIEW dbo.NQW_OrderSiView
AS
SELECT V.*, O.f_LoaiDon AS MaLoaiDon, N'Sỉ' AS LoaiDonHang
FROM dbo.WA_OrderView V
    INNER JOIN dbo.WB_OrderTbl O ON O.DocumentID = V.DocumentID
WHERE COALESCE(O.f_LoaiDon, dbo.NQW_LoaiDonCuaKhachFnc(O.ObjectID)) = 'SI';
GO
IF OBJECT_ID('dbo.NQW_OrderLeView') IS NULL EXEC ('CREATE VIEW dbo.NQW_OrderLeView AS SELECT 1 AS x');
GO
ALTER VIEW dbo.NQW_OrderLeView
AS
SELECT V.*, O.f_LoaiDon AS MaLoaiDon, N'Lẻ' AS LoaiDonHang
FROM dbo.WA_OrderView V
    INNER JOIN dbo.WB_OrderTbl O ON O.DocumentID = V.DocumentID
WHERE COALESCE(O.f_LoaiDon, dbo.NQW_LoaiDonCuaKhachFnc(O.ObjectID), 'LE') = 'LE';
GO

/* ---------- 5a. Danh sách khách hàng theo loại đơn + nhân viên quản lý ---------- */
IF OBJECT_ID('dbo.NQW_DonHang_KhachHangStp') IS NULL EXEC ('CREATE PROCEDURE dbo.NQW_DonHang_KhachHangStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_DonHang_KhachHangStp
    @LoaiDon    varchar(10),
    @EmployeeID varchar(50) = '',     -- '' = mọi nhân viên (chỉ quản trị)
    @S          nvarchar(100) = ''    -- tìm theo mã / tên / địa chỉ / điện thoại
AS
SET NOCOUNT ON;
SELECT TOP 300 K.ObjectID, K.ObjectName, K.Address, K.Phone, K.ObjectGroupID,
       K.TuyenBanHang AS EmployeeID, E.EmployeeName
FROM dbo.CF_ObjectTbl K
    LEFT JOIN dbo.CF_EmployeeTbl E ON E.EmployeeID = K.TuyenBanHang
WHERE COALESCE(K.ObjectID, '') <> ''
  AND (COALESCE(@EmployeeID, '') = '' OR K.TuyenBanHang = @EmployeeID)
  AND (COALESCE(@S, N'') = N'' OR K.ObjectID LIKE '%' + @S + '%' OR K.ObjectName LIKE N'%' + @S + N'%'
       OR K.Address LIKE N'%' + @S + N'%' OR K.Phone LIKE '%' + @S + '%')
  AND dbo.NQW_LoaiDonCuaKhachFnc(K.ObjectID) = @LoaiDon
ORDER BY K.ObjectName;
GO

/* ---------- 5b. Thông tin 1 khách hàng + nợ đầu ---------- */
IF OBJECT_ID('dbo.NQW_DonHang_ThongTinKHStp') IS NULL EXEC ('CREATE PROCEDURE dbo.NQW_DonHang_ThongTinKHStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_DonHang_ThongTinKHStp
    @ObjectID varchar(50),
    @Ngay     datetime = NULL
AS
SET NOCOUNT ON;
IF @Ngay IS NULL SET @Ngay = CONVERT(date, GETDATE());
SELECT K.ObjectID, K.ObjectName, K.Address, K.Phone, K.ObjectGroupID, K.TuyenBanHang AS EmployeeID, E.EmployeeName,
       dbo.NQW_LoaiDonCuaKhachFnc(K.ObjectID) AS LoaiDon,
       COALESCE(N.NoDau, 0) AS NoDau, COALESCE(N.ConNo, 0) AS ConNo
FROM dbo.CF_ObjectTbl K
    LEFT JOIN dbo.CF_EmployeeTbl E ON E.EmployeeID = K.TuyenBanHang
    OUTER APPLY (SELECT TOP 1 NoDau, ConNo FROM dbo.B_LayNoDauKhachHangPhaiThuFnc(@Ngay, @ObjectID)) N
WHERE K.ObjectID = @ObjectID;
GO

/* ---------- 5c. Hàng hóa + giá bán theo loại đơn ---------- */
IF OBJECT_ID('dbo.NQW_DonHang_HangHoaStp') IS NULL EXEC ('CREATE PROCEDURE dbo.NQW_DonHang_HangHoaStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_DonHang_HangHoaStp
    @LoaiDon  varchar(10),
    @ObjectID varchar(50) = ''
AS
SET NOCOUNT ON;
DECLARE @GiaSi bit = 0;
SELECT @GiaSi = LayGiaSi FROM dbo.sy_WebLoaiDon WHERE LoaiDon = @LoaiDon;
IF EXISTS (SELECT 1 FROM dbo.CF_ObjectTbl WHERE ObjectID = @ObjectID AND isLayGiaSi = 1) SET @GiaSi = 1;

SELECT H.Mahang AS ItemID, H.Tenhang AS ItemName, H.DvtID AS Unit,
       CAST(COALESCE(NULLIF(H.QuyDoi, 0), 1) AS int) AS QuyDoi,
       CAST(CASE WHEN @GiaSi = 1 THEN COALESCE(NULLIF(H.DonGiaSi, 0), H.DonGia) ELSE H.DonGia END AS decimal(18, 0)) AS GiaChuan
FROM dbo.dmHangHoaDonGiaView H
WHERE COALESCE(H.isNgungSuDung, 0) = 0
  AND COALESCE(CASE WHEN @GiaSi = 1 THEN COALESCE(NULLIF(H.DonGiaSi, 0), H.DonGia) ELSE H.DonGia END, 0) > 0
ORDER BY H.Mahang;
GO

/* ---------- 5d. Cấp số chứng từ mới (gọi bên trong giao dịch của NQW_DonHang_LuuStp) ---------- */
IF OBJECT_ID('dbo.NQW_DonHang_LaySoCTStp') IS NULL EXEC ('CREATE PROCEDURE dbo.NQW_DonHang_LaySoCTStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_DonHang_LaySoCTStp
    @LoaiDon    varchar(10),
    @Ngay       datetime,
    @DocumentID varchar(50) OUTPUT
AS
SET NOCOUNT ON;
DECLARE @TienTo varchar(10), @KieuSo varchar(20), @Dau varchar(30), @Max varchar(50), @Stt int, @t datetime = GETDATE();
SELECT @TienTo = TienTo, @KieuSo = KieuSo FROM dbo.sy_WebLoaiDon WHERE LoaiDon = @LoaiDon;

IF @KieuSo = 'NGAY_STT'
BEGIN
    SET @Dau = @TienTo + CONVERT(char(6), @Ngay, 12);                            -- DH260927
    -- chỉ tính các số đúng dạng DH260927001 (bỏ qua số dạng thời gian DL260927172435 của app điện thoại)
    SELECT @Max = MAX(DocumentID) FROM dbo.WB_OrderTbl WITH (UPDLOCK, HOLDLOCK)
    WHERE DocumentID LIKE @Dau + '[0-9][0-9][0-9]' AND LEN(DocumentID) = LEN(@Dau) + 3;
    SET @Stt = COALESCE(TRY_CAST(RIGHT(@Max, 3) AS int), 0) + 1;
    SET @DocumentID = @Dau + RIGHT('000' + CAST(@Stt AS varchar(10)), 3);        -- DH260927001
END
ELSE
BEGIN
    SET @DocumentID = @TienTo + CONVERT(char(6), @t, 12) + REPLACE(CONVERT(char(8), @t, 108), ':', '');  -- DL260927172435
    WHILE EXISTS (SELECT 1 FROM dbo.WB_OrderTbl WITH (UPDLOCK, HOLDLOCK) WHERE DocumentID = @DocumentID)
    BEGIN
        SET @t = DATEADD(second, 1, @t);
        SET @DocumentID = @TienTo + CONVERT(char(6), @t, 12) + REPLACE(CONVERT(char(8), @t, 108), ':', '');
    END
END
GO

/* ---------- 5e. Lưu đơn hàng (thêm mới hoặc sửa) ----------
   @Lines = <Lines><L><ItemID>..</ItemID><Ket>1</Ket><Chai>0</Chai><KetKM/>..<UnitPrice>..</UnitPrice>
                     <TienChietKhau>..</TienChietKhau><KhuyenMaiID>..</KhuyenMaiID><Notes>..</Notes></L>...</Lines>
   Trả về: 1 bảng thông báo (MsgType 1 = lỗi, không lưu; 0 = cảnh báo) + DocumentID đã lưu.
   Giá chuẩn (GiaChuan) luôn tính lại từ bảng giá, không lấy từ trình duyệt.                     */
IF OBJECT_ID('dbo.NQW_DonHang_LuuStp') IS NULL EXEC ('CREATE PROCEDURE dbo.NQW_DonHang_LuuStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_DonHang_LuuStp
    @DocumentID   varchar(50),          -- '' = đơn mới
    @LoaiDon      varchar(10),
    @DocumentDate datetime,
    @DeliveryDate datetime,
    @ObjectID     varchar(50),
    @EmployeeID   varchar(50),
    @Phone        varchar(50) = NULL,
    @Memo         nvarchar(200) = NULL,
    @isTrongNgay  bit = 0,
    @isKhongKM    bit = 0,
    @HoanTat      bit = 0,             -- 1 = chuyển sang "Chờ duyệt"; 0 = "Đang lên đơn"
    @Lines        xml,
    @User         varchar(50),
    @IsAdmin      bit = 0
AS
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Msg TABLE (MsgType int, Title nvarchar(500));
DECLARE @L TABLE (RowNo int IDENTITY(1, 1), ItemID varchar(50), Ket decimal(18, 0), Chai decimal(18, 0),
                  KetKM decimal(18, 0), ChaiKM decimal(18, 0), UnitPrice decimal(18, 0), TienChietKhau decimal(18, 0),
                  KhuyenMaiID nvarchar(50), Notes nvarchar(50), GiaChuan decimal(18, 0), QuyDoi int, HopLe bit);
DECLARE @Moi bit = CASE WHEN COALESCE(@DocumentID, '') = '' THEN 1 ELSE 0 END;
DECLARE @CK bit, @KTNo bit, @LoaiKH varchar(10), @TuyenKH varchar(50), @TruGiaMin decimal(18, 0), @NoDau decimal(18, 0);

SET @DocumentDate = CONVERT(date, @DocumentDate);
SET @DeliveryDate = CONVERT(date, COALESCE(@DeliveryDate, @DocumentDate));
IF @isTrongNgay = 1 SET @DeliveryDate = @DocumentDate;

SELECT @CK = ChoPhepChietKhau, @KTNo = KiemTraCongNo FROM dbo.sy_WebLoaiDon WHERE LoaiDon = @LoaiDon AND IsSuDung = 1;
SELECT @LoaiKH = dbo.NQW_LoaiDonCuaKhachFnc(@ObjectID);
SELECT @TuyenKH = TuyenBanHang FROM dbo.CF_ObjectTbl WHERE ObjectID = @ObjectID;
SELECT @TruGiaMin = TRY_CAST(CodeValue AS decimal(18, 0)) FROM dbo.SY_Setup WHERE CodeID = 'TruGiaMin';

INSERT @L (ItemID, Ket, Chai, KetKM, ChaiKM, UnitPrice, TienChietKhau, KhuyenMaiID, Notes)
SELECT LTRIM(RTRIM(x.value('(ItemID/text())[1]', 'varchar(50)'))),
       x.value('(Ket/text())[1]', 'decimal(18,0)'), x.value('(Chai/text())[1]', 'decimal(18,0)'),
       x.value('(KetKM/text())[1]', 'decimal(18,0)'), x.value('(ChaiKM/text())[1]', 'decimal(18,0)'),
       x.value('(UnitPrice/text())[1]', 'decimal(18,0)'), x.value('(TienChietKhau/text())[1]', 'decimal(18,0)'),
       NULLIF(x.value('(KhuyenMaiID/text())[1]', 'nvarchar(50)'), N''), NULLIF(x.value('(Notes/text())[1]', 'nvarchar(50)'), N'')
FROM @Lines.nodes('/Lines/L') T(x);

-- giá chuẩn + quy đổi lấy lại từ bảng giá
DECLARE @Gia TABLE (ItemID varchar(50) PRIMARY KEY, ItemName nvarchar(250), Unit nvarchar(50), QuyDoi int, GiaChuan decimal(18, 0));
INSERT @Gia EXEC dbo.NQW_DonHang_HangHoaStp @LoaiDon, @ObjectID;
UPDATE L SET GiaChuan = G.GiaChuan, QuyDoi = G.QuyDoi, HopLe = CASE WHEN G.ItemID IS NULL THEN 0 ELSE 1 END
FROM @L L LEFT JOIN @Gia G ON G.ItemID = L.ItemID;
UPDATE @L SET UnitPrice = GiaChuan WHERE UnitPrice IS NULL;

/* ----- kiểm tra đầu phiếu ----- */
IF @CK IS NULL INSERT @Msg VALUES (1, N'Loại đơn ' + COALESCE(@LoaiDon, '') + N' không có hoặc đang tắt (sy_WebLoaiDon)');
IF @Moi = 0 AND NOT EXISTS (SELECT 1 FROM dbo.WB_OrderTbl WHERE DocumentID = @DocumentID)
    INSERT @Msg VALUES (1, N'Không tìm thấy đơn ' + @DocumentID);
IF @Moi = 0 AND EXISTS (SELECT 1 FROM dbo.WB_OrderTbl WHERE DocumentID = @DocumentID AND COALESCE(isSelect, 0) = 1)
    INSERT @Msg VALUES (1, N'Không thể sửa phiếu đã duyệt');
ELSE IF @Moi = 0 AND EXISTS (SELECT 1 FROM dbo.WB_OrderTbl WHERE DocumentID = @DocumentID AND COALESCE(MaTrangThai, -1) <> -1)
    INSERT @Msg VALUES (1, N'Không thể sửa/thêm phiếu chờ duyệt');     -- giống web cũ: chỉ sửa khi "Đang lên đơn"
IF @LoaiKH IS NULL INSERT @Msg VALUES (1, N'Mã khách hàng không hợp lệ');
ELSE IF @LoaiKH <> @LoaiDon INSERT @Msg VALUES (1, N'Khách hàng ' + @ObjectID + N' không thuộc loại đơn này (khách thuộc loại ' + @LoaiKH + N')');
IF @IsAdmin = 0 AND COALESCE(@TuyenKH, '') <> COALESCE(@EmployeeID, '')
    INSERT @Msg VALUES (1, N'Khách hàng không do nhân viên ' + COALESCE(@EmployeeID, '') + N' quản lý');
IF NOT EXISTS (SELECT 1 FROM dbo.CF_EmployeeTbl WHERE EmployeeID = @EmployeeID)
    INSERT @Msg VALUES (1, N'Mã nhân viên không hợp lệ');
IF @DeliveryDate < @DocumentDate
    INSERT @Msg VALUES (1, N'Ngày giao không hợp lệ, ngày giao >= ngày đặt (' + CONVERT(varchar(10), @DocumentDate, 103) + ')');
IF NOT EXISTS (SELECT 1 FROM @L) INSERT @Msg VALUES (1, N'Đơn hàng chưa có mặt hàng nào');

-- nợ vượt mức / quá hạn: dùng lại đúng kiểm tra của web cũ
IF COALESCE(@KTNo, 0) = 1 AND @LoaiKH IS NOT NULL
BEGIN
    DECLARE @X xml = (SELECT @DocumentID AS DocumentID, CONVERT(varchar(10), @DocumentDate, 126) AS DocumentDate,
                             CONVERT(varchar(10), @DeliveryDate, 126) AS DeliveryDate, @ObjectID AS ObjectID
                      FOR XML PATH('T0'), ROOT('Data'), TYPE);
    INSERT @Msg (Title, MsgType) EXEC dbo.WB_Order_CheckSaveStp @DocumentID, @X;
END

/* ----- kiểm tra từng dòng hàng ----- */
INSERT @Msg
SELECT 1, N'Dòng ' + CAST(RowNo AS varchar(10)) + N': mã hàng ' + COALESCE(ItemID, '') + N' không có trong bảng giá'
FROM @L WHERE COALESCE(HopLe, 0) = 0
UNION ALL
SELECT 1, N'Dòng ' + CAST(RowNo AS varchar(10)) + N' (' + ItemID + N'): chưa nhập số lượng'
FROM @L WHERE COALESCE(Ket, 0) + COALESCE(Chai, 0) + COALESCE(KetKM, 0) + COALESCE(ChaiKM, 0) = 0
UNION ALL
SELECT 1, N'Dòng ' + CAST(RowNo AS varchar(10)) + N' (' + ItemID + N'): số lượng không được âm'
FROM @L WHERE COALESCE(Ket, 0) < 0 OR COALESCE(Chai, 0) < 0 OR COALESCE(KetKM, 0) < 0 OR COALESCE(ChaiKM, 0) < 0
UNION ALL
SELECT 1, N'Dòng ' + CAST(RowNo AS varchar(10)) + N' (' + ItemID + N'): loại đơn này không được chiết khấu'
FROM @L WHERE COALESCE(TienChietKhau, 0) <> 0 AND COALESCE(@CK, 0) = 0
UNION ALL
SELECT 1, N'Dòng ' + CAST(RowNo AS varchar(10)) + N' (' + ItemID + N'): không thể bán dưới giá quy định ' + CONVERT(varchar(20), GiaChuan)
FROM @L WHERE HopLe = 1 AND COALESCE(UnitPrice, 0) < COALESCE(GiaChuan, 0) - COALESCE(@TruGiaMin, 0);

IF EXISTS (SELECT 1 FROM @Msg WHERE MsgType = 1)
BEGIN
    SELECT DISTINCT MsgType, Title, CAST(NULL AS varchar(50)) AS DocumentID FROM @Msg ORDER BY MsgType DESC;
    RETURN;
END

SELECT TOP 1 @NoDau = NoDau FROM dbo.B_LayNoDauKhachHangPhaiThuFnc(@DocumentDate, @ObjectID);

/* ----- ghi dữ liệu ----- */
BEGIN TRAN;
    IF @Moi = 1
    BEGIN
        EXEC dbo.NQW_DonHang_LaySoCTStp @LoaiDon, @DocumentDate, @DocumentID OUTPUT;
        INSERT dbo.WB_OrderTbl (DocumentID, DocumentDate, ObjectID, Phone, DeliveryDate, EmployeeID, Memo, isTrongNgay, isKhongKM,
                                NoDau, MaTrangThai, isSelect, UserCreate, DateCreate, f_LoaiDon)
        VALUES (@DocumentID, @DocumentDate, @ObjectID, @Phone, @DeliveryDate, @EmployeeID, @Memo, @isTrongNgay, @isKhongKM,
                COALESCE(@NoDau, 0), -1, 0, @User, GETDATE(), @LoaiDon);
    END
    ELSE
    BEGIN
        UPDATE dbo.WB_OrderTbl
        SET DocumentDate = @DocumentDate, ObjectID = @ObjectID, Phone = @Phone, DeliveryDate = @DeliveryDate, EmployeeID = @EmployeeID,
            Memo = @Memo, isTrongNgay = @isTrongNgay, isKhongKM = @isKhongKM, NoDau = COALESCE(@NoDau, 0),
            UserUpdate = @User, DateUpdate = GETDATE(), f_LoaiDon = @LoaiDon
        WHERE DocumentID = @DocumentID;
        DELETE dbo.WB_OrderDetailTbl WHERE DocumentID = @DocumentID;
    END

    -- UserAutoID giống phần mềm: yyMMddHHmmss + 13 số
    INSERT dbo.WB_OrderDetailTbl (UserAutoID, DocumentID, ItemID, Ket, Chai, KetKM, ChaiKM, GiaChuan, UnitPrice, TienChietKhau,
                                  KhuyenMaiID, Notes, QuyDoi, isKoKM, isKhongSuaGia)
    SELECT CONVERT(char(6), GETDATE(), 12) + REPLACE(CONVERT(char(8), GETDATE(), 108), ':', '')
           + RIGHT('000' + CAST(RowNo AS varchar(10)), 3)
           + RIGHT('0000000000' + CAST(ABS(CHECKSUM(NEWID())) % 10000000000 AS varchar(10)), 10),
           @DocumentID, ItemID, NULLIF(Ket, 0), NULLIF(Chai, 0), NULLIF(KetKM, 0), NULLIF(ChaiKM, 0), GiaChuan, UnitPrice,
           NULLIF(TienChietKhau, 0), KhuyenMaiID, Notes, QuyDoi, @isKhongKM, 0
    FROM @L ORDER BY RowNo;

    -- Số lượng, thành tiền: đúng công thức WB_OrderDetail_AfterSaveStp của web cũ
    UPDATE A
    SET Quantity  = COALESCE(A.Ket, 0) * B.QuyDoi + COALESCE(A.Chai, 0),
        Amount    = COALESCE(A.Ket, 0) * (COALESCE(A.UnitPrice, 0) - COALESCE(A.TienChietKhau, 0))
                    + COALESCE(A.Chai, 0) * ROUND((COALESCE(A.UnitPrice, 0) - COALESCE(A.TienChietKhau, 0)) / COALESCE(NULLIF(B.QuyDoi, 0), 1), 0),
        SoLuongKM = COALESCE(A.KetKM, 0) * B.QuyDoi + COALESCE(A.ChaiKM, 0)
    FROM dbo.WB_OrderDetailTbl A
        LEFT JOIN dbo.dmHanghoaView B ON A.ItemID = B.Mahang
    WHERE A.DocumentID = @DocumentID;

    UPDATE dbo.WB_OrderTbl
    SET BaseTotal = (SELECT SUM(Amount) FROM dbo.WB_OrderDetailTbl WHERE DocumentID = @DocumentID)
    WHERE DocumentID = @DocumentID;

    EXEC dbo.WB_Order_AfterSaveStp @DocumentID;            -- giao trong ngày, trạng thái "Đang lên đơn"
    IF @HoanTat = 1
        UPDATE dbo.WB_OrderTbl SET MaTrangThai = 0 WHERE DocumentID = @DocumentID;   -- "Chờ duyệt"
COMMIT;

SELECT DISTINCT MsgType, Title, @DocumentID AS DocumentID FROM @Msg
UNION ALL
SELECT -1, N'Đã lưu', @DocumentID
ORDER BY MsgType DESC;
GO

/* ---------- 5f. Xóa đơn (chỉ đơn chưa duyệt) ---------- */
IF OBJECT_ID('dbo.NQW_DonHang_XoaStp') IS NULL EXEC ('CREATE PROCEDURE dbo.NQW_DonHang_XoaStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_DonHang_XoaStp
    @DocumentID varchar(50),
    @User       varchar(50)
AS
SET NOCOUNT ON;
SET XACT_ABORT ON;
IF NOT EXISTS (SELECT 1 FROM dbo.WB_OrderTbl WHERE DocumentID = @DocumentID)
BEGIN SELECT 1 AS MsgType, N'Không tìm thấy đơn ' + @DocumentID AS Title; RETURN; END
IF EXISTS (SELECT 1 FROM dbo.WB_OrderTbl WHERE DocumentID = @DocumentID AND COALESCE(isSelect, 0) = 1)
BEGIN SELECT 1 AS MsgType, N'Không thể xóa phiếu đã duyệt' AS Title; RETURN; END
IF EXISTS (SELECT 1 FROM dbo.WB_OrderTbl WHERE DocumentID = @DocumentID AND COALESCE(MaTrangThai, -1) <> -1)
BEGIN SELECT 1 AS MsgType, N'Không thể xóa phiếu chờ duyệt' AS Title; RETURN; END
BEGIN TRAN;
    DELETE dbo.WB_OrderDetailTbl WHERE DocumentID = @DocumentID;
    DELETE dbo.WB_OrderTbl WHERE DocumentID = @DocumentID;
COMMIT;
SELECT -1 AS MsgType, N'Đã xóa ' + @DocumentID + N' (' + @User + N')' AS Title;
GO

/* ---------- 6. Menu + cấu hình màn hình + quyền ---------- */
-- 6a. Menu 1010 (lẻ) mới; 1012 đổi sang màn hình sỉ (giá trị cũ ghi trong bảng sy_WebCapNhat để gỡ lại)
IF NOT EXISTS (SELECT 1 FROM dbo.sy_WebCapNhat WHERE TenFile = N'P01_DonHangSiLe#menu1012')
    INSERT dbo.sy_WebCapNhat (TenFile, GhiChu)
    SELECT N'P01_DonHangSiLe#menu1012', N'VN=' + COALESCE(VN, N'') + N'|FormName=' + COALESCE(FormName, '')
    FROM dbo.WA_Menu WHERE MenuID = '1012';

UPDATE dbo.WA_Menu SET VN = N'Quản lý đơn hàng sỉ', FormKey = 'List', FormName = 'NQW_DonHangSiFrm', isDisable = 0
WHERE MenuID = '1012';

IF NOT EXISTS (SELECT 1 FROM dbo.WA_Menu WHERE MenuID = '1010')
    INSERT dbo.WA_Menu (MenuID, VN, EN, CH, Parent, IconClass, FormKey, FormName, isDisable, isNotCheckPermission)
    VALUES ('1010', N'Quản lý đơn hàng lẻ', 'Retail orders', 'Retail orders', '10', 'ti ti-shopping-cart', 'List', 'NQW_DonHangLeFrm', 0, 0);
GO

-- 6b. Cấu hình màn hình: chép toàn bộ từ WA_OrderFrm, đổi view danh sách
DECLARE @F TABLE (FID varchar(50), ViewName varchar(50));
INSERT @F VALUES ('NQW_DonHangSiFrm', 'NQW_OrderSiView'), ('NQW_DonHangLeFrm', 'NQW_OrderLeView');

INSERT dbo.SY_FrmCfg (UserAutoID, FID, KeyID, SubID, KeyValue, SubValue, VDate, PFID)
SELECT CAST(NEWID() AS varchar(50)), F.FID, C.KeyID, C.SubID,
       CASE WHEN C.KeyID = 'T0' AND C.SubID = 'TV' THEN F.ViewName
            WHEN C.KeyID = 'T0' AND C.SubID = 'GD2' THEN 'DocumentID;DocumentDate;LoaiDonHang;Gio;StatusName;ObjectInfo;ItemID;BaseTotal;EmployeeName'
            ELSE C.KeyValue END,
       C.SubValue, GETDATE(), C.PFID
FROM dbo.SY_FrmCfg C CROSS JOIN @F F
WHERE C.FID = 'WA_OrderFrm'
  AND NOT EXISTS (SELECT 1 FROM dbo.SY_FrmCfg X WHERE X.FID = F.FID);

INSERT dbo.SY_FrmFltTbl (UserAutoID, FormID, KeyID, ColumnID, Caption, ControlWidth, Type, Source, SourceType, ValueColumn, DisplayColumn,
                         ColumnArr, WidthArr, IsSetDefaultValue, RememberLastValue, isLockWhenEditData, UseLikeOperator, LinkColumn,
                         ParaArr, IsDisable, IsReload, WhereString, IsPrimaryKeyCombine, PrimaryKeyFormat, PrimaryKeyLen, Operator,
                         DefaultValue, DefaultValueSQL, GroupColumnArr, EditType, DisplayMember2)
SELECT LEFT(CAST(NEWID() AS varchar(50)), 36), F.FID, T.KeyID, T.ColumnID, T.Caption, T.ControlWidth, T.Type, T.Source, T.SourceType,
       T.ValueColumn, T.DisplayColumn, T.ColumnArr, T.WidthArr, T.IsSetDefaultValue, T.RememberLastValue, T.isLockWhenEditData,
       T.UseLikeOperator, T.LinkColumn, T.ParaArr, T.IsDisable, T.IsReload, T.WhereString, T.IsPrimaryKeyCombine, T.PrimaryKeyFormat,
       T.PrimaryKeyLen, T.Operator, T.DefaultValue, T.DefaultValueSQL, T.GroupColumnArr, T.EditType, T.DisplayMember2
FROM dbo.SY_FrmFltTbl T CROSS JOIN @F F
WHERE T.FormID = 'WA_OrderFrm'
  AND NOT EXISTS (SELECT 1 FROM dbo.SY_FrmFltTbl X WHERE X.FormID = F.FID);
GO

-- 6c. Tiêu đề cột "Loại đơn hàng"
IF NOT EXISTS (SELECT 1 FROM dbo.SY_FmtFldTbl WHERE FieldName = 'LoaiDonHang' AND FormName IS NULL)
    INSERT dbo.SY_FmtFldTbl (FieldName, FormName, CaptionVN, CaptionEN) VALUES ('LoaiDonHang', NULL, N'Loại đơn hàng', 'Order type');
GO

-- 6d. Quyền menu 1010 chép từ 1012 cho từng nhóm / người dùng
INSERT dbo.WA_UserGroupPermisstion (UserGroupID, MenuID, IsRun, IsAdd, IsUpdate, IsDelete, isManager, isAdmin, isAutoLock,
                                    isHideAmount, isLockDoc, isUnLockDoc, isExportExcel)
SELECT P.UserGroupID, '1010', P.IsRun, P.IsAdd, P.IsUpdate, P.IsDelete, P.isManager, P.isAdmin, P.isAutoLock,
       P.isHideAmount, P.isLockDoc, P.isUnLockDoc, P.isExportExcel
FROM dbo.WA_UserGroupPermisstion P
WHERE P.MenuID = '1012'
  AND NOT EXISTS (SELECT 1 FROM dbo.WA_UserGroupPermisstion X WHERE X.UserGroupID = P.UserGroupID AND X.MenuID = '1010');

INSERT dbo.WA_UserPermisstion (UserName, MenuID, IsRun, IsAdd, IsUpdate, IsDelete, isManager, isAdmin, isAutoLock,
                               isHideAmount, isLockDoc, isUnLockDoc, isExportExcel)
SELECT P.UserName, '1010', P.IsRun, P.IsAdd, P.IsUpdate, P.IsDelete, P.isManager, P.isAdmin, P.isAutoLock,
       P.isHideAmount, P.isLockDoc, P.isUnLockDoc, P.isExportExcel
FROM dbo.WA_UserPermisstion P
WHERE P.MenuID = '1012'
  AND NOT EXISTS (SELECT 1 FROM dbo.WA_UserPermisstion X WHERE X.UserName = P.UserName AND X.MenuID = '1010');
GO

/* ---------- 7. Ghi nhận PHẦN 01 ---------- */
INSERT dbo.sy_WebCapNhat (TenFile, GhiChu) VALUES (N'P01_DonHangSiLe', N'Form nhập đơn hàng sỉ / lẻ cho web');
PRINT N'Xong PHẦN 01 – đơn hàng sỉ / lẻ';
GO

/* ====================================== HẾT PHẦN 01 ====================================== */

/* ============================ PHẦN 02 – Gửi email báo cáo cuối ngày ============================ */
/* Bảng cấu hình + store lấy dữ liệu báo cáo. Việc dựng PDF/Excel và gửi mail do script Python
   (tien_ich/bao_cao_cuoi_ngay.py) đảm nhận, SQL Agent chạy script mỗi ~10 phút để canh giờ. */

/* ---------- 1. Bảng cấu hình (1 dòng, ID = 1) ---------- */
IF OBJECT_ID('dbo.NQW_BaoCaoEmailCf') IS NULL
CREATE TABLE dbo.NQW_BaoCaoEmailCf (
    ID              int          NOT NULL PRIMARY KEY,
    BatTat          bit          NOT NULL DEFAULT (0),      -- 1 = bật gửi tự động
    EmailNhan       nvarchar(1000) NULL,                    -- người nhận, cách nhau bằng ; hoặc ,
    EmailCC         nvarchar(1000) NULL,
    GioGui          varchar(5)   NOT NULL DEFAULT ('18:00'),-- 'HH:mm', sửa lúc nào cũng được
    GuiChuNhat      bit          NOT NULL DEFAULT (0),      -- 0 = KHÔNG gửi Chủ nhật, 1 = gửi cả CN
    DinhDang        varchar(10)  NOT NULL DEFAULT ('PDF'),  -- 'PDF' | 'EXCEL' | 'PDF_EXCEL'
    TieuDe          nvarchar(200) NOT NULL DEFAULT (N'Báo cáo bán hàng ngày {Ngay}'),
    SoNgayTre       int          NOT NULL DEFAULT (0),      -- 0 = báo cáo hôm nay; 1 = báo cáo hôm qua
    LanGuiCuoi      date         NULL,                       -- ngày đã gửi gần nhất (chống gửi trùng)
    ThoiDiemGuiCuoi datetime     NULL,
    GhiChu          nvarchar(500) NULL
);
GO

IF NOT EXISTS (SELECT 1 FROM dbo.NQW_BaoCaoEmailCf WHERE ID = 1)
    INSERT dbo.NQW_BaoCaoEmailCf (ID, BatTat, EmailNhan, GioGui, GuiChuNhat, DinhDang, TieuDe, SoNgayTre, GhiChu)
    VALUES (1, 0, N'', '18:00', 0, 'PDF', N'Báo cáo bán hàng ngày {Ngay}', 0,
            N'Điền EmailNhan rồi đặt BatTat = 1 để bắt đầu gửi. GuiChuNhat = 1 nếu muốn gửi cả Chủ nhật.');
GO

/* ---------- 2. Store lấy dữ liệu báo cáo (3 phần: tổng quan + theo nhân viên) ---------- */
IF OBJECT_ID('dbo.NQW_BaoCaoCuoiNgay_DuLieuStp') IS NULL EXEC('CREATE PROCEDURE dbo.NQW_BaoCaoCuoiNgay_DuLieuStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_BaoCaoCuoiNgay_DuLieuStp
    @Ngay date = NULL
AS
SET NOCOUNT ON;
IF @Ngay IS NULL SET @Ngay = CONVERT(date, GETDATE());

-- Phiếu bán hợp lệ trong ngày (DuyetHangVe = 1 hoặc isGuiKho = 1); quét tbBannuoc 1 lần
CREATE TABLE #B (DocumentID nvarchar(50), ObjectID varchar(50), EmployeeID varchar(50),
                 TongTienBan decimal(18,0), Thanhtoan decimal(18,0), NoPS decimal(18,0));
INSERT #B (DocumentID, ObjectID, EmployeeID, TongTienBan, Thanhtoan, NoPS)
SELECT b.DocumentID, b.ObjectID, b.EmployeeID,
       ISNULL(b.TongTienBan,0), ISNULL(b.Thanhtoan,0),
       CASE WHEN ISNULL(b.isNhanVienNo,0) = 0
                 AND (ISNULL(b.TongTienBan,0)+ISNULL(b.SoTienCuoc,0)+ISNULL(b.STPalletCuoc,0)+ISNULL(b.TienBanVo,0))-ISNULL(b.Thanhtoan,0) > 0
            THEN (ISNULL(b.TongTienBan,0)-(ISNULL(b.STPalletHC,0)+ISNULL(b.Sotienhoancuoc,0)))-ISNULL(b.Thanhtoan,0)
            ELSE 0 END
FROM dbo.tbBannuoc b WITH (NOLOCK)
WHERE CONVERT(date, b.DocumentDate) = @Ngay AND (b.DuyetHangVe = 1 OR b.isGuiKho = 1);

-- Thu công nợ trong ngày (phiếu thu KH)
DECLARE @ThuCongNo decimal(18,0) = (
    SELECT ISNULL(SUM(ISNULL(d.SoTienThu,0)),0)
    FROM dbo.tbPhieuThuKHDetailTbl d WITH (NOLOCK)
    JOIN dbo.tbPhieuThuKH h WITH (NOLOCK) ON h.DocumentID = d.DocumentID
    WHERE CONVERT(date, h.DocumentDate) = @Ngay AND ISNULL(h.isTinhCongNo,0) = 1 AND ISNULL(d.isThuNoNhanVien,0) = 0);

-- (1) Tổng quan
SELECT
    @Ngay AS Ngay,
    (SELECT COUNT(*) FROM #B)                          AS SoPhieuBan,
    (SELECT COUNT(DISTINCT ObjectID) FROM #B)          AS SoKhach,
    (SELECT ISNULL(SUM(TongTienBan),0) FROM #B)        AS DoanhSoBan,
    (SELECT ISNULL(SUM(Thanhtoan),0) FROM #B)          AS ThuTaiDiemBan,
    @ThuCongNo                                         AS ThuCongNo,
    (SELECT ISNULL(SUM(Thanhtoan),0) FROM #B) + @ThuCongNo AS TongThu,
    (SELECT ISNULL(SUM(NoPS),0) FROM #B)               AS NoPhatSinh,
    (SELECT COUNT(*) FROM dbo.WB_OrderTbl WITH (NOLOCK) WHERE CONVERT(date,DocumentDate)=@Ngay AND f_LoaiDon='SI') AS DonSi,
    (SELECT COUNT(*) FROM dbo.WB_OrderTbl WITH (NOLOCK) WHERE CONVERT(date,DocumentDate)=@Ngay AND f_LoaiDon='LE') AS DonLe;

-- (2) Theo nhân viên bán hàng (sắp theo doanh số giảm dần)
SELECT b.EmployeeID,
       ISNULL(e.EmployeeName, b.EmployeeID) AS EmployeeName,
       COUNT(*)                     AS SoPhieu,
       ISNULL(SUM(b.TongTienBan),0) AS DoanhSo,
       ISNULL(SUM(b.Thanhtoan),0)   AS TienThu,
       ISNULL(SUM(b.NoPS),0)        AS NoPhatSinh
FROM #B b
LEFT JOIN dbo.CF_EmployeeTbl e WITH (NOLOCK) ON e.EmployeeID = b.EmployeeID
GROUP BY b.EmployeeID, e.EmployeeName
ORDER BY DoanhSo DESC;

DROP TABLE #B;
GO

/* ---------- 3. Store đọc cấu hình ---------- */
IF OBJECT_ID('dbo.NQW_BaoCaoEmail_CauHinhStp') IS NULL EXEC('CREATE PROCEDURE dbo.NQW_BaoCaoEmail_CauHinhStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_BaoCaoEmail_CauHinhStp
AS
SET NOCOUNT ON;
SELECT ID, BatTat, EmailNhan, EmailCC, GioGui, GuiChuNhat, DinhDang, TieuDe, SoNgayTre,
       LanGuiCuoi, ThoiDiemGuiCuoi, GhiChu
FROM dbo.NQW_BaoCaoEmailCf WHERE ID = 1;
GO

/* ---------- 4. Store kiểm tra "đã tới lúc gửi chưa" ---------- */
IF OBJECT_ID('dbo.NQW_BaoCaoEmail_CanGuiStp') IS NULL EXEC('CREATE PROCEDURE dbo.NQW_BaoCaoEmail_CanGuiStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_BaoCaoEmail_CanGuiStp
    @Now datetime = NULL
AS
SET NOCOUNT ON;
IF @Now IS NULL SET @Now = GETDATE();

DECLARE @BatTat bit, @EmailNhan nvarchar(1000), @EmailCC nvarchar(1000), @GioGui varchar(5),
        @GuiChuNhat bit, @DinhDang varchar(10), @TieuDe nvarchar(200), @SoNgayTre int, @LanGuiCuoi date;
SELECT @BatTat=BatTat, @EmailNhan=EmailNhan, @EmailCC=EmailCC, @GioGui=GioGui, @GuiChuNhat=GuiChuNhat,
       @DinhDang=DinhDang, @TieuDe=TieuDe, @SoNgayTre=SoNgayTre, @LanGuiCuoi=LanGuiCuoi
FROM dbo.NQW_BaoCaoEmailCf WHERE ID = 1;

DECLARE @NgayHomNay date = CONVERT(date, @Now);
DECLARE @NgayBC date = DATEADD(day, -ISNULL(@SoNgayTre,0), @NgayHomNay);
DECLARE @LaChuNhat bit = CASE WHEN (DATEDIFF(day,'19000101',@NgayHomNay) % 7) = 6 THEN 1 ELSE 0 END;  -- 6 = Chủ nhật
DECLARE @GioGuiT time(0) = TRY_CAST(@GioGui AS time);

DECLARE @CanGui bit = 1, @LyDo nvarchar(200);
IF @BatTat IS NULL BEGIN SET @CanGui = 0; SET @LyDo = N'Chưa có cấu hình (bảng NQW_BaoCaoEmailCf trống)'; END
ELSE IF ISNULL(@BatTat,0) = 0 BEGIN SET @CanGui = 0; SET @LyDo = N'Tính năng đang tắt (BatTat = 0)'; END
ELSE IF ISNULL(@EmailNhan,N'') = N'' BEGIN SET @CanGui = 0; SET @LyDo = N'Chưa khai báo email người nhận'; END
ELSE IF @LaChuNhat = 1 AND ISNULL(@GuiChuNhat,0) = 0 BEGIN SET @CanGui = 0; SET @LyDo = N'Hôm nay Chủ nhật, cấu hình không gửi Chủ nhật'; END
ELSE IF @GioGuiT IS NULL BEGIN SET @CanGui = 0; SET @LyDo = N'Giờ gửi không hợp lệ (cần dạng HH:mm)'; END
ELSE IF CONVERT(time(0), @Now) < @GioGuiT BEGIN SET @CanGui = 0; SET @LyDo = N'Chưa tới giờ gửi'; END
ELSE IF @LanGuiCuoi IS NOT NULL AND @LanGuiCuoi >= @NgayHomNay BEGIN SET @CanGui = 0; SET @LyDo = N'Hôm nay đã gửi rồi'; END
ELSE SET @LyDo = N'Đủ điều kiện gửi';

SELECT @CanGui AS CanGui, @NgayBC AS Ngay, @NgayHomNay AS NgayHomNay, @LyDo AS LyDo,
       @EmailNhan AS EmailNhan, @EmailCC AS EmailCC, @DinhDang AS DinhDang, @TieuDe AS TieuDe,
       @GioGui AS GioGui, @GuiChuNhat AS GuiChuNhat;
GO

/* ---------- 5. Store đánh dấu đã gửi hôm nay (chống gửi trùng) ---------- */
IF OBJECT_ID('dbo.NQW_BaoCaoEmail_DanhDauDaGuiStp') IS NULL EXEC('CREATE PROCEDURE dbo.NQW_BaoCaoEmail_DanhDauDaGuiStp AS RETURN 0');
GO
ALTER PROCEDURE dbo.NQW_BaoCaoEmail_DanhDauDaGuiStp
    @NgayGui date = NULL
AS
SET NOCOUNT ON;
IF @NgayGui IS NULL SET @NgayGui = CONVERT(date, GETDATE());
UPDATE dbo.NQW_BaoCaoEmailCf SET LanGuiCuoi = @NgayGui, ThoiDiemGuiCuoi = GETDATE() WHERE ID = 1;
SELECT N'Đã đánh dấu gửi ngày ' + CONVERT(varchar(10), @NgayGui, 103) AS KetQua;
GO

/* ---------- 6. Ghi nhận PHẦN 02 ---------- */
IF NOT EXISTS (SELECT 1 FROM dbo.sy_WebCapNhat WHERE TenFile = N'P02_EmailBaoCaoCuoiNgay')
    INSERT dbo.sy_WebCapNhat (TenFile, GhiChu)
    VALUES (N'P02_EmailBaoCaoCuoiNgay', N'Bảng cấu hình + store báo cáo bán hàng cuối ngày gửi email');
GO
/* ====================================== HẾT PHẦN 02 ====================================== */

PRINT N'=== Đã cập nhật xong database cho Web Nguyên Quân ===';
GO
