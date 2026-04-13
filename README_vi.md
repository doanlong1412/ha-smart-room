# 🧠 HA Smart Room Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-1.0.0-blue)
![HA](https://img.shields.io/badge/Home%20Assistant-2023.1+-green)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

> 🇬🇧 **English version:** [README.md](README.md)

Backend tự động hóa server-side cho [HA Smart Room Card](https://github.com/doanlong1412/ha-smart-room-card).

Integration này chạy hoàn toàn trên Home Assistant — tự động tắt, theo dõi chuyển động, đồng bộ trạng thái phòng đều hoạt động **kể cả khi đóng trình duyệt**. Không cần tạo helper thủ công, không bị giới hạn bởi localStorage.

---

## ✨ Integration này làm gì

- **Đăng ký phòng** — mỗi card đăng ký room ID, danh sách thiết bị và cài đặt độ trễ ngay khi lưu lần đầu
- **Theo dõi chuyển động** — giám sát entity cảm biến chuyển động và lưu timestamp phát hiện cuối cùng phía server
- **Logic tự động tắt** — khi phòng trống quá thời gian đã cài, tự động tắt tất cả thiết bị đã chọn
- **Cảm biến đếm ngược** — tạo entity `sensor` chứa số giây còn lại để card hiển thị đếm ngược trực tiếp
- **Switch chế độ tự động** — tạo entity `switch` cho từng phòng để card đọc/ghi, đồng bộ nút Thủ công/Tự động trên mọi thiết bị
- **Hủy đăng ký sạch sẽ** — khi card bị xóa khỏi dashboard (sau 8 giây grace period), phòng được hủy đăng ký và các entity bị dọn dẹp

---

## 📦 Cài Đặt

### Qua HACS *(khuyến nghị)*

**Bước 1:** Thêm repo này vào HACS dưới dạng custom integration:

**HACS → Integrations → ⋮ → Custom repositories**

```
URL:  https://github.com/doanlong1412/ha-smart-room
Type: Integration
```

**Bước 2:** Tìm **HA Smart Room** trong danh sách integrations → **Install**

**Bước 3:** **Restart Home Assistant**

**Bước 4:** Vào **Settings → Devices & Services → Add Integration** → tìm **HA Smart Room** → làm theo hướng dẫn cài đặt

---

### Cài thủ công

1. Tải hoặc clone repo này
2. Sao chép thư mục `custom_components/ha_smart_room/` vào thư mục config của HA:
   ```
   /config/custom_components/ha_smart_room/
   ```
3. **Restart Home Assistant**
4. Vào **Settings → Devices & Services → Add Integration** → tìm **HA Smart Room**

---

## 🔗 Kết Nối với Card

Sau khi cài xong integration:

1. Mở dashboard và chỉnh sửa **HA Smart Room Card**
2. Vào **Tự động hóa → Chế độ đồng bộ**
3. Chọn **🧠 HA Smart Room Integration**
4. Nhấn **Lưu**

Card sẽ tự động gọi `ha_smart_room.register_room` khi lưu, truyền room ID, entity chuyển động, danh sách thiết bị và độ trễ. Từ đây mọi tự động hóa chạy hoàn toàn trên server.

Bạn có thể dùng **nhiều phòng** — mỗi card đăng ký độc lập, lấy tên phòng làm ID duy nhất.

---

## 🗂️ Entities được tạo cho mỗi phòng

Với mỗi phòng đã đăng ký, integration tạo ra:

| Entity | Loại | Mô tả |
|--------|------|-------|
| `switch.hsrc_{room_id}_auto_mode` | Switch | Trạng thái Thủ công/Tự động — đồng bộ trên mọi thiết bị |
| `sensor.hsrc_{room_id}_countdown` | Sensor | Số giây còn lại trước khi tự tắt (0 khi không hoạt động) |

Các entity này được quản lý tự động. Bạn có thể dùng chúng trong HA automations, dashboard hoặc thông báo nếu cần.

---

## ⚙️ Services

Integration cung cấp các service sau (được card gọi nội bộ):

| Service | Mô tả |
|---------|-------|
| `ha_smart_room.register_room` | Đăng ký phòng với cấu hình (gọi khi lưu card) |
| `ha_smart_room.unregister_room` | Hủy đăng ký phòng và dọn dẹp entities |
| `ha_smart_room.set_auto_mode` | Bật/tắt chế độ tự động cho một phòng |

---

## 🖥️ Tương Thích

| | |
|---|---|
| Home Assistant | 2023.1+ |
| Card yêu cầu | [HA Smart Room Card v1.1+](https://github.com/doanlong1412/ha-smart-room-card) |
| HACS | Được hỗ trợ |

---

## 📋 Lịch Sử Thay Đổi

### v1.0.0
- 🚀 Phát hành lần đầu
- Đăng ký và hủy đăng ký phòng
- Theo dõi chuyển động và tự động tắt server-side
- Entity switch và sensor đếm ngược riêng cho từng phòng
- Grace period 8 giây khi ngắt kết nối để tránh hủy đăng ký nhầm

---

## 📄 Giấy Phép

MIT — miễn phí sử dụng, chỉnh sửa và phân phối.

---

## 🙏 Credits

Phát triển bởi **[@doanlong1412](https://github.com/doanlong1412)** từ 🇻🇳 Việt Nam.
Theo dõi TikTok: [@long.1412](https://www.tiktok.com/@long.1412)

> 👉 Tìm card? [github.com/doanlong1412/ha-smart-room-card](https://github.com/doanlong1412/ha-smart-room-card)
