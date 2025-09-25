"""Button platform for Kotel MQTT Bluetooth reconnect."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

DOMAIN = "kotel_mqtt"

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up Kotel MQTT button entities."""
    _LOGGER.info("Setting up Kotel MQTT button entities")

    buttons = [
        KotelBluetoothButton(hass, 'bluetooth_reconnect', 'Переподключить Bluetooth', 'mdi:bluetooth'),
    ]

    async_add_entities(buttons, True)

class KotelBluetoothButton(ButtonEntity):
    """Representation of a Kotel Bluetooth reconnect button."""

    def __init__(self, hass: HomeAssistant, button_type, name, icon) -> None:
        """Initialize the button."""
        self.hass = hass
        self._button_type = button_type
        self._name = name
        self._icon = icon
        self._unique_id = f"kotel_mqtt_{button_type}_button"

    @property
    def unique_id(self):
        """Return unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the button."""
        return self._name

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Bluetooth reconnect button pressed")

        # Call the reconnect_bluetooth service
        await self.hass.services.async_call(
            DOMAIN, 'reconnect_bluetooth', {}
        )
