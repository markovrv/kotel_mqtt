"""Select platform for Kotel MQTT mode selection."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

DOMAIN = "kotel_mqtt"

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up Kotel MQTT select entities."""
    _LOGGER.info("Setting up Kotel MQTT select entities")

    selects = [
        KotelModeSelect(hass, 'operation_mode', 'Режим работы котла', 'mdi:cog'),
    ]

    async_add_entities(selects, True)

class KotelModeSelect(SelectEntity):
    """Representation of a Kotel mode select."""

    def __init__(self, hass: HomeAssistant, select_type, name, icon) -> None:
        """Initialize the select entity."""
        self.hass = hass
        self._select_type = select_type
        self._name = name
        self._icon = icon
        self._current_option = None
        self._unique_id = f"kotel_mqtt_{select_type}_select"

        # Options like in web client
        self._options = ['Стоп', 'Ручной', 'Авто']

    async def async_added_to_hass(self):
        """Register callbacks."""
        _LOGGER.debug("Select %s added to HA", self.name)
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_update", self._handle_update
            )
        )
        self._handle_update()

    @callback
    def _handle_update(self, param_name=None):
        """Handle update from dispatcher."""
        if param_name is None or param_name == self._select_type:
            if DOMAIN in self.hass.data:
                data = self.hass.data[DOMAIN]['data']
                mode = data.get(self._select_type, 0)

                # Map numeric mode to text option
                if mode == 0:
                    new_option = 'Стоп'
                elif mode == 1:
                    new_option = 'Ручной'
                elif mode == 2:
                    new_option = 'Авто'
                else:
                    new_option = 'Стоп'

                if new_option != self._current_option:
                    self._current_option = new_option
                    self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the select entity."""
        return self._name

    @property
    def current_option(self):
        """Return the current selected option."""
        return self._current_option

    @property
    def options(self):
        """Return the list of available options."""
        return self._options

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    async def async_select_option(self, option: str):
        """Select new option."""
        # Map text option to numeric mode
        mode_mapping = {
            'Стоп': 0,
            'Ручной': 1,
            'Авто': 2
        }

        mode = mode_mapping.get(option)
        if mode is not None:
            _LOGGER.info("Setting mode to: %s", option)
            await self.hass.services.async_call(
                DOMAIN, 'send_command',
                {'cmd_type': 'set_param', 'param': '001D', 'value': mode}
            )
        else:
            _LOGGER.error("Unknown mode option: %s", option)

    @property
    def should_poll(self):
        """No polling needed."""
        return False
