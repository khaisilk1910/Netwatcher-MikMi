# Netwatcher MikMi 0.3.0-beta.1 — Kiến trúc hiện hành

> Đặc tả v0.1 trước đây đã được thay bằng README mới. Xem [`README.md`](README.md) để triển khai và thông tin bảo mật/pháp lý.

## Các đường dữ liệu

- MikroTik RouterOS 7 `API-SSL`: backend đọc `lease`, `arp`, `bridge-host`, `resource`, `interface`; xác thực bằng SHA256 certificate pin.
- `RouterLogMonitor`: đọc `/log/print` qua API-SSL **trong executor, độc lập với inventory**; hash chống trùng lưu trong Home Assistant `.storage`, không lưu full log lâu dài.
- MiWiFi: đọc HTTP nội bộ khi người dùng chủ động bật; không thực hiện lệnh ghi, không suy đoán node AP từ danh sách aggregate.
- `Inventory`: correlation MAC, trạng thái, comment DHCP và cờ D.
- `ZaloNotifier`: gọi Home Assistant action `zalo_bot.send_message` của tích hợp **Zalo Bot cá nhân** đã cài riêng, không sử dụng OA API/token.
- WebSocket admin-only: `netwatcher_mikmi/inventory`, `netwatcher_mikmi/router_logs`, `netwatcher_mikmi/approve`, `netwatcher_mikmi/test_zalo`.
- Lovelace custom card: dùng textContent để render giá trị thiết bị/log, tránh HTML injection.

## Chính sách bảo mật

- Chỉ HA với IP quản trị có quyền tới MikroTik TCP 8729; dịch vụ RouterOS và firewall buộc giới hạn nguồn.
- Dữ liệu log chỉ hiển thị cho tài khoản quản trị HA; nếu HA có remote access thì phải bảo vệ remote access riêng.
- Cảnh báo WAN yêu cầu bật thủ công; đếm theo IP công cộng + mức độ tin cậy; threshold và cooldown giảm cảnh báo giả.
- Zalo cá nhân là action của bên thứ ba, gửi thông tin hạ tầng ra ngoài LAN và có rủi ro điều khoản dịch vụ.
- Không thay thế firewall, IDS, syslog server, NAC hoặc giám sát bảo mật chuyên nghiệp.

## Bộ phận kiểm thử

`tests/test_inventory.py`, `tests/test_zalo.py`, `tests/test_router_logs.py` dùng dữ liệu mô phỏng. Chưa test end-to-end với thiết bị thật.
