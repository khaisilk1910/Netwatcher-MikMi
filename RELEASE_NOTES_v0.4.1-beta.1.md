# Netwatcher MikMi 0.4.1-beta.1 — Modern Icon Pack

**Cập nhật giao diện, không thay đổi phương thức truy cập mạng**

- 8 bộ brand image light/dark @1x/@2x theo chuẩn custom integration HA 2026.3+.
- 33 icon SVG tự chứa, CSS gradient theo trạng thái, không tải CDN.
- Lovelace header, tab, Router Health, phần cứng, inventory, Netwatch và Logs sử dụng icon mới.
- Tùy chọn visual editor `icon_style=cyber|mono` và `show_brand=true|false`.
- Cảm biến tổng hợp, trạng thái nguồn và device tracker có MDI icon tương ứng.
- Không thay đổi config entry, storage, OAuth/Zalo Bot, DHCP hoặc firewall.
- Preview có số liệu mô phỏng, không đại diện cho router thực tế.

**Kiểm thử**: pytest, node --check, XML/SVG, file ảnh và UI Chromium (desktop/mobile). Chưa kiểm thử trên RouterOS/Xiaomi/Home Assistant thực tế.
