@echo off
rem Chay bang quyen Administrator: mo cong 8090 cho may khac trong mang LAN vao web
netsh advfirewall firewall add rule name="Web Nguyen Quan 8090" dir=in action=allow protocol=TCP localport=8090
pause
