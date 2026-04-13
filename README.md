# 🧠 HA Smart Room Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-1.0.0-blue)
![HA](https://img.shields.io/badge/Home%20Assistant-2023.1+-green)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

> 🇻🇳 **Phiên bản tiếng Việt:** [README_vi.md](README_vi.md)

The server-side automation backend for [HA Smart Room Card](https://github.com/doanlong1412/ha-smart-room-card).

This integration runs entirely on Home Assistant — auto-off, motion tracking, and room state sync all work **even when the browser is closed**. No helpers to create manually, no localStorage limitations.

---

## ✨ What this integration does

- **Registers rooms** — each card registers its room ID, device list, and delay settings on first save
- **Tracks motion** — monitors the motion sensor entity and records last-seen timestamps server-side
- **Auto-off logic** — when the room has been empty for the configured delay, turns off all selected devices automatically
- **Countdown sensor** — exposes a `sensor` with seconds remaining so the card can display a live countdown
- **Auto mode switch** — exposes a `switch` entity per room that the card reads/writes to sync the Manual/Auto button across all devices
- **Unregisters cleanly** — when a card is removed from the dashboard (after an 8-second grace period), the room is unregistered and its entities are cleaned up

---

## 📦 Installation

### Via HACS *(recommended)*

**Step 1:** Add this repository as a custom integration in HACS:

**HACS → Integrations → ⋮ → Custom repositories**

```
URL:  https://github.com/doanlong1412/ha-smart-room
Type: Integration
```

**Step 2:** Search **HA Smart Room** in the integrations list → **Install**

**Step 3:** **Restart Home Assistant**

**Step 4:** Go to **Settings → Devices & Services → Add Integration** → search **HA Smart Room** → complete the setup wizard

---

### Manual installation

1. Download or clone this repository
2. Copy the `custom_components/ha_smart_room/` folder to your HA config directory:
   ```
   /config/custom_components/ha_smart_room/
   ```
3. **Restart Home Assistant**
4. Go to **Settings → Devices & Services → Add Integration** → search **HA Smart Room**

---

## 🔗 Connecting the Card

Once the integration is installed:

1. Open your dashboard and edit the **HA Smart Room Card**
2. Go to **Automation → Sync mode**
3. Select **🧠 HA Smart Room Integration**
4. Click **Save**

The card automatically calls `ha_smart_room.register_room` on save, passing the room ID, motion entity, device list, and delay. From this point all automation runs server-side.

You can have **multiple rooms** — each card registers independently using its room name as a unique ID.

---

## 🗂️ Entities created per room

For each registered room, the integration creates:

| Entity | Type | Description |
|--------|------|-------------|
| `switch.hsrc_{room_id}_auto_mode` | Switch | Manual/Auto state — synced across all devices |
| `sensor.hsrc_{room_id}_countdown` | Sensor | Seconds remaining before auto-off (0 when inactive) |

These entities are managed automatically. You can use them in HA automations, dashboards, or notifications if needed.

---

## ⚙️ Services

The integration exposes these services (called internally by the card):

| Service | Description |
|---------|-------------|
| `ha_smart_room.register_room` | Register a room with its config (called on card save) |
| `ha_smart_room.unregister_room` | Unregister a room and clean up its entities |
| `ha_smart_room.set_auto_mode` | Set auto mode on/off for a room |

---

## 🖥️ Compatibility

| | |
|---|---|
| Home Assistant | 2023.1+ |
| Card required | [HA Smart Room Card v1.1+](https://github.com/doanlong1412/ha-smart-room-card) |
| HACS | Supported |

---

## 📋 Changelog

### v1.0.0
- 🚀 Initial release
- Room registration and unregistration
- Server-side motion tracking and auto-off
- Per-room switch and countdown sensor entities
- 8-second grace period on disconnect to avoid accidental unregister

---

## 📄 License

MIT — free to use, modify, and distribute.

---

## 🙏 Credits

Developed by **[@doanlong1412](https://github.com/doanlong1412)** from 🇻🇳 Vietnam.
Follow on TikTok: [@long.1412](https://www.tiktok.com/@long.1412)

> 👉 Looking for the card? [github.com/doanlong1412/ha-smart-room-card](https://github.com/doanlong1412/ha-smart-room-card)
