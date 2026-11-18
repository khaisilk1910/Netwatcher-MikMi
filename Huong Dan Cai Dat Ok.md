# NETWATCHER MIKMI — TRIỂN KHAI MIKROTIK API-SSL VÀ LẤY SHA-256 FINGERPRINT

**Dành cho mạng đã trao đổi:** MikroTik `192.168.31.1`, API-SSL TCP `8729`, user chỉ đọc `nwm_reader`, nhóm `nwm_read`, IP nguồn được phép `192.168.31.100/32`, chứng chỉ `netwatcher-api`, Root CA `netwatcher-ca`.

**Cập nhật:** 18/11/2026. Ví dụ dành cho RouterOS v7 và Ubuntu Server. Chỉ thực thi lệnh theo từng mục; **không dán chạy toàn bộ từ đầu đến cuối**. Các mục B và C là hai tình huống **loại trừ nhau**.

> **Quan trọng với hệ thống của bạn:** Bạn đã lấy thành công fingerprint SHA-256. Hãy dùng **mục A + D + E** để kiểm tra; **KHÔNG tạo lại CA hoặc chứng chỉ** vì thay chứng chỉ có thể làm thay đổi fingerprint và khiến Netwatcher từ chối kết nối.

## A. Kiểm tra cấu hình hiện tại — MikroTik (WinBox > New Terminal)

```routeros
/system resource print
/ip service print detail where name=api-ssl
/certificate print detail where name=netwatcher-ca
/certificate print detail where name=netwatcher-api
/user print detail where name=nwm_reader
/user group print detail where name=nwm_read
/ip firewall filter print detail where chain=input
```

Xác nhận:

- `api-ssl` có `disabled=no`, `port=8729`, `certificate=netwatcher-api`.
- `netwatcher-api` đã ký, có private key và chưa hết hạn. Chứng chỉ cần có SAN `IP:192.168.31.1`.
- `nwm_reader` thuộc `nwm_read`, chỉ có quyền `read,api`; **không** cấp `write`, `policy`, `sensitive`, `reboot` hoặc nhóm `full`.
- User đang bị hạn chế `address=192.168.31.100/32`. Điều này chỉ đúng nếu **IP nguồn của Home Assistant theo góc nhìn MikroTik** là `192.168.31.100`.
- Dịch vụ API-SSL không tiếp nhận kết nối từ WAN.

### Đối chiếu fingerprint ngay trên MikroTik

```routeros
/certificate print detail where name=netwatcher-api
```

Trong các bản RouterOS có trường `fingerprint`, giá trị thường là 64 ký tự hex **không có dấu `:`**. So sánh với giá trị trên Ubuntu sau khi bỏ dấu `:` và không phân biệt hoa/thường. Chỉ so sánh từ một phiên WinBox/SSH đã xác thực và tin cậy.

## B. Chỉ cài mới: tạo CA và chứng chỉ lần đầu trên MikroTik

**Bỏ qua mục này nếu `netwatcher-api` đã ký và hoạt động.** Kiểm tra mục A trước. Chạy từng nhóm lệnh, đợi kết quả thành công; không tạo trùng tên.

**B1 — Tạo Root CA nội bộ (nếu chưa có):**

```routeros
/certificate add name=netwatcher-ca common-name=Netwatcher-Root-CA key-usage=key-cert-sign,crl-sign days-valid=3650
/certificate sign netwatcher-ca
:delay 5s
/certificate print detail where name=netwatcher-ca
```

**B2 — Tạo chứng chỉ TLS server (nếu chưa có):**

```routeros
/certificate add name=netwatcher-api common-name=192.168.31.1 subject-alt-name=IP:192.168.31.1 key-usage=digital-signature,key-encipherment,tls-server days-valid=825
/certificate sign netwatcher-api ca=netwatcher-ca
:delay 5s
/certificate print detail where name=netwatcher-api
```

Nếu **đã có template `netwatcher-api` chưa được ký**, chỉ cần lệnh `/certificate sign netwatcher-api ca=netwatcher-ca` sau khi xác nhận CA đã ký, không chạy `/certificate add` lần nữa.

**B3 — Gán chứng chỉ cho API-SSL:**

```routeros
/ip service set [find name=api-ssl] certificate=netwatcher-api disabled=no
/ip service print detail where name=api-ssl
```

Khi gán certificate sau khi sign, nếu RouterOS báo `input does not match any value of certificate`, đợi vài giây, kiểm tra kết quả `/certificate print detail` rồi thử gán lại. Không tự động xóa/chỉnh chứng chỉ cũ.

## C. Chỉ cài mới: tạo user chỉ đọc nếu chưa tồn tại

**Bỏ qua nếu đã có `nwm_reader` và `nwm_read` như ảnh cấu hình của bạn.** Kiểm tra bằng các lệnh mục A.

```routeros
/user group add name=nwm_read policy=api,read
/user add name=nwm_reader group=nwm_read address=192.168.31.100/32 password="THAY_BANG_MAT_KHAU_NGAU_NHIEN_RIENG"
/user print detail where name=nwm_reader
/user group print detail where name=nwm_read
```

Đặt mật khẩu ngẫu nhiên dài tối thiểu 20 ký tự; **không dùng lại mật khẩu admin**, không chia sẻ password trong ảnh hoặc log. Không chạy `add` nếu tên group/user đã tồn tại. Lưu ý khai báo mật khẩu trực tiếp trên terminal có thể để lại dấu vết trong lịch sử thao tác; hãy bảo vệ phiên quản trị.

## D. Trên Ubuntu Server — cài công cụ, kiểm tra kết nối và lấy SHA-256

Đăng nhập **Ubuntu Server**, không chạy lệnh bash trên RouterOS.

**D1 — Cài công cụ:**

```bash
sudo apt update
sudo apt install -y openssl netcat-openbsd ca-certificates
```

**D2 — Xem địa chỉ IP nguồn Ubuntu chọn để đi đến MikroTik:**

```bash
ip -4 route get 192.168.31.1
```

Ví dụ trong đầu ra có `src 192.168.31.100`. Với Home Assistant chạy trong Docker hoặc VM, IP nguồn mà MikroTik nhìn thấy có thể **khác IP Ubuntu host**. Kiểm tra thực tế trước khi giới hạn `/32`.

**D3 — Kiểm tra TCP 8729:**

```bash
nc -vz -w 5 192.168.31.1 8729
```

`open`/`succeeded` chỉ chứng minh TCP có thể mở, **không** chứng minh TLS hoặc user/mật khẩu hợp lệ.

**D4 — Xem toàn bộ lỗi bắt tay TLS (không ẩn stderr):**

```bash
openssl s_client -connect 192.168.31.1:8729 -showcerts </dev/null
```

**D5 — Lấy SHA-256 fingerprint ngắn gọn:**

```bash
openssl s_client -connect 192.168.31.1:8729 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha256
```

Ví dụ kết quả: `sha256 Fingerprint=B0:2C:E2:2E:...` (phải đủ 32 byte, tức 64 ký tự hex sau khi bỏ dấu `:`). **Lệnh này chỉ tính fingerprint của chứng chỉ đầu bên kia trình ra**, chưa tự xác minh danh tính máy chủ; **bắt buộc đối chiếu** với chứng chỉ trong phiên quản trị MikroTik tin cậy (mục A).

**D6 — Xem chi tiết SAN, hạn chứng chỉ, chủ thể/đơn vị phát hành:**

```bash
openssl s_client -connect 192.168.31.1:8729 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

**D7 — Tùy chọn dùng script có kiểm tra đầu ra:**

```bash
bash get_mikrotik_fingerprint.sh 192.168.31.1 8729
```

## E. Hardening quyền truy cập — chỉ áp dụng sau khi xác nhận IP nguồn

Dựa trên ảnh hiện tại, `nwm_reader` đã giới hạn `192.168.31.100/32`. Để API-SSL cũng chỉ cho nguồn đó, **chỉ chạy lệnh dưới nếu Home Assistant thực sự kết nối từ `192.168.31.100` và không còn client quản trị khác cần API-SSL**:

```routeros
/user set [find name=nwm_reader] address=192.168.31.100/32
/ip service set [find name=api-ssl] address=192.168.31.100/32
/ip service print detail where name=api-ssl
```

**Firewall RouterOS:** Mục tiêu là chỉ cho `192.168.31.100/32` vào TCP `8729` trên `chain=input`, chặn các IP khác, đặc biệt từ WAN. **Không dán lệnh `add` firewall vô điều kiện**: thứ tự rule quyết định hiệu lực, có thể bị các rule chấp nhận toàn LAN hiện hữu vượt qua. Trong WinBox **bật Safe Mode**, xem `/ip firewall filter print detail where chain=input`, sau đó tạo **allow** cho IP Home Assistant và **drop** các nguồn khác đối với TCP 8729 **trước mọi rule chấp nhận LAN rộng**. Giữ rule `established,related` và các rule quản trị cần thiết. Với mạng có VLAN quản trị, ưu tiên tách VLAN.

Một số lựa chọn cứng hóa khác (chỉ khi chắc chắn không có ứng dụng đang sử dụng):

```routeros
/ip service print detail where name=api
# Nếu không sử dụng API không mã hóa trên TCP 8728:
/ip service set [find name=api] disabled=yes
```

Không mở hoặc chuyển tiếp TCP 8729 từ Internet vào MikroTik. Không dùng tài khoản admin/full cho Netwatcher MikMi.

## F. Điền vào Home Assistant > Netwatcher MikMi

| Trường | Giá trị theo mạng đã trao đổi |
|---|---|
| MikroTik management IPv4 | `192.168.31.1` |
| MikroTik API-SSL port | `8729` |
| Read-only API username | `nwm_reader` |
| Read-only API password | Mật khẩu thực của `nwm_reader` |
| SHA-256 Fingerprint | Toàn bộ SHA-256 đã lấy và đối chiếu |

**Không dùng nhầm** `192.168.88.1` hoặc `ha_reader` theo các ví dụ cũ. Nếu biểu mẫu tích hợp yêu cầu không có dấu `:`, bỏ dấu `:` theo định dạng trường nhập; không cắt ngắn fingerprint.

## G. Khắc phục sự cố thường gặp

| Dấu hiệu | Kiểm tra và xử lý |
|---|---|
| `Could not find certificate from <stdin>` | S_client không nhận certificate PEM; chạy D4 để xem lỗi thật; kiểm tra IP, TCP 8729, cấu hình certificate. |
| `no peer certificate available` / `handshake failure` | API-SSL có thể chưa gán certificate hoặc không tương thích TLS; xem mục A/B và RouterOS log. |
| `failure: CA not found` | Đã tạo template server nhưng ký không chỉ định CA; ký CA trước, sau đó `/certificate sign netwatcher-api ca=netwatcher-ca`. |
| `input does not match any value of certificate` | Certificate vẫn là template hoặc vừa ký chưa sẵn sàng; xem `/certificate print detail`, đợi 5 giây. |
| `nc: connection refused` | Sai IP/port, API-SSL disabled hoặc router từ chối kết nối. |
| `nc: connection timed out` | Tuyến mạng/firewall/địa chỉ nguồn chưa được phép. |
| `MikroTik rejected the read-only account` | Kiểm tra đúng `nwm_reader`, mật khẩu, `nwm_read` (read,api), `address` user và IP nguồn thực tế của HA. |
| Fingerprint Ubuntu khác MikroTik | **Dừng, không chấp nhận**; xác minh đúng IP/cert qua WinBox tin cậy và kiểm tra nguy cơ nhầm host/MITM. |
| Trên Ubuntu kết nối được, HA không kết nối | Home Assistant container/VM có thể dùng mạng khác; xem IP nguồn trên MikroTik và firewall/route từ container/VM. |

Lệnh xem log đăng nhập trên MikroTik (không gửi nguyên bản các log nhạy cảm):

```routeros
/log print where message~"nwm_reader"
/log print where topics~"account"
```

## H. Khuyến nghị bảo mật và sao lưu

- Trước khi chỉnh firewall/chứng chỉ, tạo backup và export bằng WinBox, bảo quản ở nơi an toàn; tránh chia sẻ bản export chứa dữ liệu nhạy cảm.
- Certificate public fingerprint không phải mật khẩu, nhưng **không gửi** private key, mật khẩu, token, export chứa secrets.
- Fingerprint pinning giúp phát hiện thay chứng chỉ, nhưng cần xác minh ban đầu qua kênh tin cậy. Khi chứng chỉ được gia hạn/thay đổi, phải xác minh và cập nhật fingerprint.
- Các lệnh `/certificate add`, `/certificate sign`, `/user add` là lệnh **thay đổi cấu hình**; chỉ dùng trong tình huống chưa thiết lập. Lệnh `openssl x509` trên Ubuntu chỉ đọc chứng chỉ.
- API-SSL yêu cầu kết nối TLS hợp lệ; đừng nhầm lẫn thành `api` TCP 8728 không mã hóa.

## Tài liệu chính thức tham khảo

- RouterOS Certificates: https://manual.mikrotik.com/docs/authentication-authorization-accounting/certificates/
- RouterOS API / API-SSL: https://manual.mikrotik.com/docs/developer-guides/api/
- RouterOS Services: https://help.mikrotik.com/docs/spaces/ROS/pages/103841820/Services
