"""Number platform for Kotel MQTT parameters."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

DOMAIN = "kotel_mqtt"

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up Kotel MQTT number entities."""
    _LOGGER.info("Setting up Kotel MQTT number entities")

    numbers = [
        # Параметры ручного режима (как в веб-клиенте)
        KotelNumber(hass, 'fuel_supply', 'Подача топлива', 'сек', 'mdi:fuel', 0, 60, 1),
        KotelNumber(hass, 'pause_duration', 'Пауза', 'сек', 'mdi:timer', 0, 120, 1),
        KotelNumber(hass, 'fan_speed', 'Скорость вентилятора', '%', 'mdi:fan', 0, 25, 1),
        KotelNumber(hass, 'thermostat', 'Установка термостата', '°C', 'mdi:thermometer-lines', 10, 90, 1),

        # Параметры автоматического режима
        KotelNumber(hass, 'stabilization_temperature', 'Температура стабилизации', '°C', 'mdi:thermometer', 10, 90, 1),
    ]

    async_add_entities(numbers, True)
    _LOGGER.info("Kotel MQTT number entities added: %s", len(numbers))

class KotelNumber(NumberEntity):
    """Representation of a Kotel MQTT number parameter."""

    def __init__(self, hass: HomeAssistant, param_type, name, unit, icon, min_value, max_value, step) -> None:
        """Initialize the number entity."""
        self.hass = hass
        self._param_type = param_type
        self._name = name
        self._unit_of_measurement = unit
        self._icon = icon
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._value = None
        self._unique_id = f"kotel_mqtt_{param_type}_number"

    async def async_added_to_hass(self):
        """Register callbacks."""
        _LOGGER.debug("Number %s added to HA", self.name)
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_update", self._handle_update
            )
        )
        self._handle_update()

    @callback
    def _handle_update(self, param_name=None):
        """Handle update from dispatcher."""
        if param_name is None or param_name == self._param_type:
            if DOMAIN in self.hass.data:
                data = self.hass.data[DOMAIN]['data']
                new_value = data.get(self._param_type)
                if new_value != self._value:
                    self._value = new_value
                    self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the number entity."""
        return self._name

    @property
    def value(self):
        """Return the current value."""
        return self._value

    @property
    def min_value(self):
        """Return the minimum value."""
        return self._min_value

    @property
    def max_value(self):
        """Return the maximum value."""
        return self._max_value

    @property
    def step(self):
        """Return the step value."""
        return self._step

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    async def async_set_value(self, value: float):
        """Set new value."""
        # Map parameter type to parameter code
        param_mapping = {
            'fuel_supply': '0001',
            'pause_duration': '0002',
            'fan_speed': '0003',
            'thermostat': '0004',
            'stabilization_temperature': '0015',
        }

        param_code = param_mapping.get(self._param_type)
        if param_code:
            _LOGGER.info("Setting %s to %s", self.name, value)
            await self.hass.services.async_call(
                DOMAIN, 'send_command',
                {'cmd_type': 'set_param', 'param': param_code, 'value': int(value)}
            )
        else:
            _LOGGER.error("Unknown parameter type: %s", self._param_type)

    @property
    def should_poll(self):
        """No polling needed."""
        return False
