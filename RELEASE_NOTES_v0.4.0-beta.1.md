# Netwatcher MikMi v0.4.0-beta.1 — Release Notes

- Đã nghiên cứu ha-mikrotik-extended, ha-mikrotik-netwatch và routeros_ha; chọn ý tưởng read-only phù hợp.
- Thêm riêng HardwareCoordinator đọc CPU/RAM 15 s, health sensor 60 s, board firmware 600 s qua API-SSL có SHA-256 pinning.
- 16 cảm biến phần cứng từ resource/health/routerboard, tình trạng nguồn đáng tin cậy, không bịa giá trị thiếu.
- Thêm WAN RX/TX bit/s, đo theo bộ đếm và thời gian thực, phát hiện counter reset.
- Thêm đọc Netwatch có sẵn (mặc định tắt) và tab Netwatch trong card.
- Bật/tắt cảnh báo CPU, RAM, nhiệt độ; ngưỡng; số mẫu; phục hồi; cooldown; lưu trạng thái qua restart.
- Gửi Zalo thường qua zalo_bot.send_message, không dùng OA; giữ các cài đặt Zalo v0.3.
- Card hiện đại với gauge đổi màu, cảnh báo có nhãn nổi bật, responsive, visual editor, tự đăng ký JS resource storage mode.
- 32 pure unit tests đạt; kiểm tra card thực tế bằng Chromium mock desktop/mobile. Chưa test với phần cứng/HA thật.
- Không thêm lệnh ghi RouterOS, không bật REST HTTP, không mở cổng WAN và không tự tạo Netwatch.
