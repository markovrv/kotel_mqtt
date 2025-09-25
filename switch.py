"""Switch platform for Kotel MQTT."""
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import ToggleEntity

DOMAIN = "kotel_mqtt"

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up Kotel MQTT switches."""
    _LOGGER.info("Setting up Kotel MQTT switches")

    switches = [
        KotelSwitch(hass, 'ignition', 'Розжиг котла', 'mdi:fire'),
    ]

    async_add_entities(switches, True)

class KotelSwitch(ToggleEntity):
    """Representation of a Kotel MQTT switch."""

    def __init__(self, hass: HomeAssistant, switch_type, name, icon) -> None:
        """Initialize the switch."""
        self.hass = hass
        self._switch_type = switch_type
        self._name = name
        self._icon = icon
        self._unique_id = f"kotel_mqtt_{switch_type}_switch"
        self._is_on = False

        # Map switch type to parameter code
        self._param_mapping = {
            'ignition': '0007'
        }

    async def async_added_to_hass(self):
        """Register callbacks."""
        _LOGGER.debug("Switch %s added to HA", self.name)
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_update", self._handle_update
            )
        )
        self._handle_update()

    @callback
    def _handle_update(self, param_name=None):
        """Handle update from dispatcher."""
        if param_name is None or param_name == self._switch_type:
            if DOMAIN in self.hass.data:
                data = self.hass.data[DOMAIN]['data']
                new_state = data.get(self._switch_type, 0) == 1
                if new_state != self._is_on:
                    self._is_on = new_state
                    self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.info("Turning on %s", self._switch_type)
        param_code = self._param_mapping.get(self._switch_type)
        if param_code:
            await self.hass.services.async_call(
                DOMAIN, 'send_command',
                {'cmd_type': 'set_param', 'param': param_code, 'value': 1}
            )

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.info("Turning off %s", self._switch_type)
        param_code = self._param_mapping.get(self._switch_type)
        if param_code:
            await self.hass.services.async_call(
                DOMAIN, 'send_command',
                {'cmd_type': 'set_param', 'param': param_code, 'value': 0}
            )

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    @property
    def should_poll(self):
        """No polling needed."""
        return False
