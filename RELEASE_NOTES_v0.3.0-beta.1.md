# Netwatcher MikMi 0.3.0-beta.1 — Beta changes

- Bỏ Zalo OA và OAuth token. Dùng action `zalo_bot.send_message` từ tích hợp Zalo Bot do người dùng cài riêng, hỗ trợ UID cá nhân / nhóm thường.
- Đọc `/log/print` qua RouterOS API-SSL, cấu hình chu kỳ và công tắc bật/tắt.
- Bộ phát hiện truy cập WAN: login admin từ public IP, thất bại liên tiếp (3/5 phút), firewall prefix `NWMIKMI-WAN` (10/5 phút); cooldown 30 phút, chống trùng sau restart.
- Cảnh báo WAN Home Assistant + công tắc riêng để gửi qua Zalo.
- Tab MikroTik Logs trong Lovelace card (admin-only), tìm kiếm/filter/phân trang.
- Xóa tuỳ chọn OAuth OA cũ trong quá trình nâng cấp; không tự bật Zalo cá nhân.
- Bổ sung README tiếng Việt hướng dẫn firewall/log/rủi ro riêng tư và pháp lý.

**Giới hạn:** Bản beta, chưa kiểm thử trên Home Assistant/RouterOS/Zalo Server thật; không phải IDS hay công cụ phòng vệ tự động.
