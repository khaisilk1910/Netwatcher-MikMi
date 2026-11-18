"""Constants for Netwatcher MikMi."""
from __future__ import annotations

DOMAIN = "netwatcher_mikmi"
NAME = "Netwatcher MikMi"
VERSION = "0.4.1-beta.6"

CONF_ROUTER_HOST = "router_host"
CONF_ROUTER_PORT = "router_port"
CONF_ROUTER_USERNAME = "router_username"
CONF_ROUTER_PASSWORD = "router_password"
CONF_ROUTER_FINGERPRINT = "router_sha256_fingerprint"
CONF_POLL_INTERVAL = "poll_interval"
CONF_OFFLINE_AFTER = "offline_after"
CONF_NOTIFY_EXISTING = "notify_existing_dynamic"
CONF_NOTIFY_PERSISTENT = "notify_persistent"
CONF_LAN_PORTS = "lan_endpoint_ports"
CONF_TRACKERS = "enable_device_trackers"

DEFAULT_POLL = 30
DEFAULT_OFFLINE = 120
MAX_DEVICES = 2500
EVENT_NEW_DYNAMIC = "netwatcher_mikmi_new_dynamic_device"
EVENT_CONNECTED = "netwatcher_mikmi_device_connected"
EVENT_DISCONNECTED = "netwatcher_mikmi_device_disconnected"
CARD_URL = "/netwatcher-mikmi/netwatcher-mikmi-card.js"

# Zalo personal-account notifications via the separately installed Zalo Bot integration.
# Deliberately different names from v0.2.0-beta.1 OA options (safe migration).
CONF_ZALO_BOT_ENABLED = "zalo_bot_enabled"
CONF_ZALO_BOT_ACCOUNT = "zalo_bot_account_selection"
CONF_ZALO_BOT_USERS = "zalo_bot_user_thread_ids"
CONF_ZALO_BOT_GROUPS = "zalo_bot_group_thread_ids"
CONF_ZALO_NOTIFY_DYNAMIC = "zalo_notify_dynamic"
CONF_ZALO_NOTIFY_ONLINE = "zalo_notify_online"
CONF_ZALO_NOTIFY_OFFLINE = "zalo_notify_offline"
CONF_ZALO_INCLUDE_MAC = "zalo_include_mac"

# RouterOS logs: read-only memory buffer, optional WAN/security notifications.
CONF_LOG_ENABLED = "enable_router_logs"
CONF_LOG_INTERVAL = "router_log_poll_interval"
CONF_WAN_ALERTS = "notify_wan_security"
CONF_ZALO_NOTIFY_WAN = "zalo_notify_wan_security"
CONF_LOGIN_FAIL_THRESHOLD = "login_failures_threshold"
CONF_FIREWALL_THRESHOLD = "wan_firewall_threshold"
DEFAULT_LOG_INTERVAL = 60
EVENT_WAN_SECURITY = "netwatcher_mikmi_wan_security_alert"

# v0.4.0: independent RouterOS health poll and threshold alerts.
CONF_HARDWARE_INTERVAL = "hardware_poll_interval"
CONF_HEALTH_DETAIL_INTERVAL = "health_detail_poll_interval"
CONF_HARDWARE_ALERTS = "hardware_alerts_enabled"
CONF_HARDWARE_CPU_ENABLED = "hardware_cpu_alert_enabled"
CONF_HARDWARE_RAM_ENABLED = "hardware_ram_alert_enabled"
CONF_HARDWARE_TEMP_ENABLED = "hardware_temperature_alert_enabled"
CONF_HARDWARE_CPU_THRESHOLD = "hardware_cpu_threshold"
CONF_HARDWARE_RAM_THRESHOLD = "hardware_ram_threshold"
CONF_HARDWARE_TEMP_THRESHOLD = "hardware_temperature_threshold"
CONF_HARDWARE_SAMPLES = "hardware_confirm_samples"
CONF_HARDWARE_RECOVERY = "hardware_notify_recovery"
CONF_HARDWARE_ZALO = "hardware_notify_zalo"
CONF_HARDWARE_COOLDOWN = "hardware_cooldown_minutes"
DEFAULT_HARDWARE_INTERVAL = 15
DEFAULT_HEALTH_DETAIL_INTERVAL = 60
EVENT_HARDWARE_ALERT = "netwatcher_mikmi_hardware_alert"
CONF_NETWATCH_ENABLED = "netwatch_read_enabled"
CONF_NETWATCH_INTERVAL = "netwatch_poll_interval"
DEFAULT_NETWATCH_INTERVAL = 120

CONF_WAN_INTERFACE = "router_wan_interface"
