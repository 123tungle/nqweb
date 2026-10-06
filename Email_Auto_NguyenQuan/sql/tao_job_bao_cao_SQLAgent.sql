/* ============================================================================
   TÙY CHỌN: Tạo SQL Server Agent job chạy script gửi báo cáo mỗi 10 phút.
   Chạy bằng tài khoản sysadmin (vd sa) trong SSMS.
   Nếu thấy phức tạp, dùng Windows Task Scheduler thay thế (xem HUONG_DAN_EMAIL.md) — đơn giản hơn.

   SỬA lại đường dẫn @duongdan cho đúng thư mục web trên máy chủ trước khi chạy.
   ============================================================================ */
USE msdb;
GO
DECLARE @duongdan nvarchar(500) = N'C:\WebNguyenQuan\tien_ich\bao_cao_cuoi_ngay.bat';  -- <== SỬA đường dẫn
DECLARE @job nvarchar(100) = N'NQW - Bao cao ban hang cuoi ngay';

IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = @job)
    EXEC msdb.dbo.sp_delete_job @job_name = @job;

EXEC msdb.dbo.sp_add_job @job_name = @job, @enabled = 1,
     @description = N'Chay script canh gio va gui email bao cao ban hang cuoi ngay cho Web Nguyen Quan';

EXEC msdb.dbo.sp_add_jobstep @job_name = @job, @step_name = N'Chay script',
     @subsystem = N'CmdExec',
     @command = @duongdan,
     @on_success_action = 1, @on_fail_action = 2;

/* Lịch: mỗi 10 phút, từ 06:00 đến 23:00 hằng ngày (script tự canh giờ + Chủ nhật trong bảng cấu hình) */
EXEC msdb.dbo.sp_add_jobschedule @job_name = @job, @name = N'Moi 10 phut',
     @freq_type = 4,               -- daily
     @freq_interval = 1,
     @freq_subday_type = 4,        -- minutes
     @freq_subday_interval = 10,
     @active_start_time = 060000,  -- 06:00:00
     @active_end_time = 230000;    -- 23:00:00

EXEC msdb.dbo.sp_add_jobserver @job_name = @job;
PRINT N'Da tao job: ' + @job;
GO
