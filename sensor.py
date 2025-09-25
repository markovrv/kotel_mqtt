"""Sensor platform for Kotel MQTT."""
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

DOMAIN = "kotel_mqtt"

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up Kotel MQTT sensors."""
    _LOGGER.info("Setting up Kotel MQTT sensors")

    sensors = [
        # Основные показатели (как в веб-клиенте)
        KotelSensor(hass, 'temperature', 'Температура котла', '°C', 'mdi:thermometer'),
        KotelSensor(hass, 'flame_level', 'Уровень пламени', 'ADC', 'mdi:fire'),
        KotelSensor(hass, 'automat_point', 'Номер точки автомата', '', 'mdi:chart-line'),

        # Параметры ручного режима
        #KotelSensor(hass, 'fuel_supply', 'Подача топлива', 'сек', 'mdi:fuel'),
        #KotelSensor(hass, 'pause_duration', 'Пауза', 'сек', 'mdi:timer'),
        #KotelSensor(hass, 'fan_speed', 'Скорость вентилятора', '%', 'mdi:fan'),
        #KotelSensor(hass, 'thermostat', 'Установка термостата', '°C', 'mdi:thermometer-lines'),

        # Параметры автоматического режима
        #KotelSensor(hass, 'stabilization_temperature', 'Температура стабилизации', '°C', 'mdi:thermometer'),

        # Статусы
        #KotelSensor(hass, 'operation_mode', 'Режим работы', '', 'mdi:cog'),
        #KotelSensor(hass, 'ignition', 'Статус розжига', '', 'mdi:fire'),
        KotelSensor(hass, 'connection_status', 'Статус MQTT подключения', '', 'mdi:connection'),
        KotelSensor(hass, 'bluetooth_status', 'Статус Bluetooth подключения', '', 'mdi:bluetooth'),
        KotelSensor(hass, 'last_message_time', 'Время последнего сообщения', '', 'mdi:clock'),
    ]

    async_add_entities(sensors, True)
    _LOGGER.info("Kotel MQTT sensors added: %s", len(sensors))

class KotelSensor(Entity):
    """Representation of a Kotel MQTT sensor."""

    def __init__(self, hass: HomeAssistant, sensor_type, name, unit, icon) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._sensor_type = sensor_type
        self._name = name
        self._unit_of_measurement = unit
        self._icon = icon
        self._state = None
        self._unique_id = f"kotel_mqtt_{sensor_type}"

    async def async_added_to_hass(self):
        """Register callbacks."""
        _LOGGER.debug("Sensor %s added to HA", self.name)

        # For status sensors
        if self._sensor_type in ['connection_status', 'bluetooth_status', 'last_message_time']:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass, f"{DOMAIN}_status_update", self._handle_update
                )
            )
        else:
            # For data sensors
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass, f"{DOMAIN}_update", self._handle_update
                )
            )

        # Initial update
        self._handle_update()

    @callback
    def _handle_update(self, param_name=None):
        """Handle update from dispatcher."""
        if DOMAIN not in self.hass.data:
            return

        config = self.hass.data[DOMAIN]

        # Handle status sensors
        if self._sensor_type == 'connection_status':
            new_state = "Подключено" if config.get("connected", False) else "Отключено"
        elif self._sensor_type == 'bluetooth_status':
            new_state = "Подключено" if config.get("bluetooth_connected", False) else "Отключено"
        elif self._sensor_type == 'last_message_time':
            last_msg = config.get("last_kotel_message")
            if last_msg:
                new_state = last_msg.strftime("%H:%M:%S")
            else:
                new_state = "Никогда"
        else:
            new_state = config['data'].get(self._sensor_type)

        if new_state != self._state:
            self._state = new_state
            self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        # Convert temperature from deci-Celsius to Celsius
        if self._sensor_type == 'temperature' and self._state is not None:
            return float(self._state) / 10

        # Convert operation mode to readable text
        if self._sensor_type == 'operation_mode':
            if self._state == 0:
                return 'Стоп'
            if self._state == 1:
                return 'Ручной'
            if self._state == 2:
                return 'Авто'
            return 'Неизвестно'

        # Convert ignition status to readable text
        if self._sensor_type == 'ignition':
            return 'Вкл' if self._state == 1 else 'Выкл'

        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    @property
    def should_poll(self):
        """No polling needed."""
        return False
