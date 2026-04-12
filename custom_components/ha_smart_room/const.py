"""Constants for HA Smart Room integration."""

DOMAIN = "ha_smart_room"
VERSION = "1.0.0"

# Config entry keys
CONF_ROOM_ID    = "room_id"
CONF_ROOM_TITLE = "room_title"
CONF_DELAY_MIN  = "delay_min"

# Default values
DEFAULT_DELAY_MIN = 5

# Entity unique id prefixes
PREFIX_AUTO   = "auto"
PREFIX_DELAY  = "delay"
PREFIX_STATUS = "status"
PREFIX_MOTION = "last_motion"

# Status sensor states
STATUS_IDLE      = "idle"
STATUS_OCCUPIED  = "occupied"
STATUS_COUNTDOWN = "countdown"
STATUS_TRIGGERED = "triggered"

# Storage
STORAGE_KEY     = "ha_smart_room_rooms"
STORAGE_VERSION = 1

# Service called by the card via websocket / REST to register a room
SERVICE_REGISTER_ROOM = "register_room"
SERVICE_UNREGISTER_ROOM = "unregister_room"
SERVICE_UPDATE_MOTION   = "update_motion"
SERVICE_TRIGGER_AUTOOFF = "trigger_autooff"

# Platforms
PLATFORMS = ["switch", "number", "sensor"]
