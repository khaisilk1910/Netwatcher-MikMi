"""Serve bundled Lovelace card, auto-register storage resources without data loss."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import CARD_URL, VERSION

_LOGGER = logging.getLogger(__name__)


async def register_card(hass: HomeAssistant) -> None:
    base = "/netwatcher-mikmi"
    await hass.http.async_register_static_paths([
        StaticPathConfig(base, str(Path(__file__).parent), False),
    ])
    lovelace = hass.data.get("lovelace")
    if lovelace is None or lovelace.resource_mode != "storage":
        _LOGGER.info("Netwatcher card served at %s; add resource manually in YAML mode", CARD_URL)
        return
    resources = lovelace.resources
    # IMPORTANT: async_items() before async_load() could overwrite users' resources.
    if not resources.loaded:
        await resources.async_load()
    expected = f"{CARD_URL}?v={VERSION}"
    matching = [item for item in resources.async_items() if item.get("url", "").split("?", 1)[0] == CARD_URL]
    if not matching:
        await resources.async_create_item({"res_type": "module", "url": expected})
        _LOGGER.info("Netwatcher Lovelace card resource registered")
    elif matching[0].get("url") != expected:
        await resources.async_update_item(matching[0]["id"], {"res_type": "module", "url": expected})
        _LOGGER.info("Netwatcher Lovelace card resource updated")
