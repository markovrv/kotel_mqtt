"""Integration for Kotel MQTT communication."""

import asyncio
from datetime import datetime, timedelta
import json
import logging

import aiohttp
import voluptuous as vol

from homeassistant.components import mqtt

# MQTT integration
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

DOMAIN = "kotel_mqtt"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_MQTT_TOPIC_PREFIX = "mqtt_topic_prefix"
CONF_BLUETOOTH_TIMEOUT = "bluetooth_timeout"

DEFAULT_PORT = 1883
DEFAULT_POLLING_INTERVAL = 10
DEFAULT_MQTT_TOPIC_PREFIX = "kotel"
DEFAULT_BLUETOOTH_TIMEOUT = 10  # seconds

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_USERNAME): cv.string,
                vol.Optional(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL
                ): cv.positive_int,
                vol.Optional(
                    CONF_MQTT_TOPIC_PREFIX, default=DEFAULT_MQTT_TOPIC_PREFIX
                ): cv.string,
                vol.Optional(
                    CONF_BLUETOOTH_TIMEOUT, default=DEFAULT_BLUETOOTH_TIMEOUT
                ): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Полное соответствие параметров из клиента
PARAM_MAPPING = {
    # Основные параметры
    "0001": "fuel_supply",  # Подача топлива (сек)
    "0002": "pause_duration",  # Пауза (сек)
    "0003": "fan_speed",  # Скорость вентилятора (%)
    "0004": "thermostat",  # Термостат (°C)
    "0007": "ignition",  # Розжиг (0/1)
    "0015": "stabilization_temperature",  # Температура стабилизации (°C)
    "001D": "operation_mode",  # Режим работы (0-стоп, 1-ручной, 2-авто)

    # Переменные (данные в реальном времени)
    "04": "temperature",  # Температура носителя (°C×10)
    "09": "flame_level",  # Уровень пламени (ADC)
    "11": "automat_point",  # Номер точки автомата
}

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Kotel MQTT component."""

    _LOGGER.info("Setting up Kotel MQTT integration")

    conf = config.get(DOMAIN)
    if conf is None:
        _LOGGER.error("Configuration for Kotel MQTT not found")
        return False

    # Initialize data storage
    hass.data[DOMAIN] = {
        "host": conf[CONF_HOST],
        "port": conf[CONF_PORT],
        "username": conf.get(CONF_USERNAME),
        "password": conf.get(CONF_PASSWORD),
        "polling_interval": conf[CONF_POLLING_INTERVAL],
        "topic_prefix": conf[CONF_MQTT_TOPIC_PREFIX],
        "bluetooth_timeout": conf[CONF_BLUETOOTH_TIMEOUT],
        "data": {},
        "connected": False,
        "bluetooth_connected": False,
        "last_kotel_message": None,  # Timestamp of last message from kotel
        "subscriptions": [],
        "monitor_task": None
    }

    # Setup services
    await setup_services(hass)

    # Setup MQTT subscription
    await setup_mqtt(hass)

    # Start Bluetooth monitoring
    await start_bluetooth_monitoring(hass)

    # Load platforms
    await load_platforms(hass, config)

    # Start polling for initial data
    await start_polling(hass)

    _LOGGER.info("Kotel MQTT integration setup complete")
    return True

async def load_platforms(hass: HomeAssistant, config: dict):
    """Load sensor and switch platforms."""
    # Load sensor platform
    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    # Load switch platform
    hass.async_create_task(
        discovery.async_load_platform(hass, "switch", DOMAIN, {}, config)
    )

    # Load number platform for parameters
    hass.async_create_task(
        discovery.async_load_platform(hass, "number", DOMAIN, {}, config)
    )

    # Load select platform for mode selection
    hass.async_create_task(
        discovery.async_load_platform(hass, "select", DOMAIN, {}, config)
    )

    # Load button platform for Bluetooth reconnect
    hass.async_create_task(
        discovery.async_load_platform(hass, "button", DOMAIN, {}, config)
    )

    _LOGGER.info("Platforms loading started")

async def setup_mqtt(hass: HomeAssistant):
    """Set up MQTT subscription for Kotel data."""
    config = hass.data[DOMAIN]
    topic_prefix = config["topic_prefix"]

    data_topic = f"{topic_prefix}/data"

    # Subscribe to data topic
    subscription = await mqtt.async_subscribe(
        hass,
        data_topic,
        lambda msg: async_handle_mqtt_message(hass, msg)
    )

    config["subscriptions"].append(subscription)
    config["status_topic"] = f"{topic_prefix}/status_request"
    config["control_topic"] = f"{topic_prefix}/control"

    _LOGGER.info("Subscribed to MQTT topic: %s", data_topic)

def async_handle_mqtt_message(hass: HomeAssistant, msg):
    """Handle incoming MQTT messages."""
    try:
        config = hass.data[DOMAIN]
        data = json.loads(msg.payload)

        _LOGGER.debug("Received MQTT message: %s", data)

        # Update last message timestamp for Bluetooth monitoring
        config["last_kotel_message"] = datetime.now()

        # Handle status messages
        if data.get("type") == "status":
            status = data.get("status")
            message = data.get("message", "")
            bluetooth_connected = data.get("bluetooth_connected", False)

            config["connected"] = status == "connected"
            config["bluetooth_connected"] = bluetooth_connected

            _LOGGER.info("Kotel status: %s - %s (Bluetooth: %s)",
                        status, message, bluetooth_connected)

            # Send update signal
            hass.loop.call_soon_threadsafe(
                async_dispatcher_send, hass, f"{DOMAIN}_status_update"
            )

        # Handle data messages
        else:
            param_code = data.get("name", {}).get("code", "").replace("0x", "")
            value = data.get("value")

            if param_code and value is not None:
                param_name = PARAM_MAPPING.get(param_code)
                if param_name:
                    config["data"][param_name] = value
                    hass.loop.call_soon_threadsafe(
                        async_dispatcher_send, hass, f"{DOMAIN}_update", param_name
                    )
                    _LOGGER.debug("Parameter %s updated to %s", param_name, value)
                else:
                    _LOGGER.debug("Unknown parameter code: %s", param_code)

    except Exception as e:  # noqa: BLE001
        _LOGGER.error("Error processing MQTT message: %s", e)

async def setup_services(hass: HomeAssistant):
    """Set up services for Kotel MQTT."""

    async def send_command_service(call: ServiceCall):
        """Service to send command to kotel via MQTT."""
        cmd_type = call.data.get("cmd_type")
        param = call.data.get("param")
        value = call.data.get("value", 0)

        _LOGGER.info("Sending MQTT command: %s %s=%s", cmd_type, param, value)
        result = await send_mqtt_command(hass, cmd_type, param, value)

        if result:
            _LOGGER.info("MQTT command sent successfully")
        else:
            _LOGGER.error("Failed to send MQTT command")

    async def request_status_service(call: ServiceCall):
        """Service to request status from kotel."""
        _LOGGER.info("Requesting kotel status")
        await request_kotel_status(hass)

    async def reconnect_bluetooth_service(call: ServiceCall):
        """Service to reconnect Bluetooth connection."""
        _LOGGER.info("Sending Bluetooth reconnect request")
        await reconnect_bluetooth(hass)

    async def change_parameter_service(call: ServiceCall):
        """Service to change parameter with validation."""
        param = call.data.get("param")
        value = call.data.get("value")
        delta = call.data.get("delta")

        if delta is not None:
            # Change parameter by delta
            current_value = hass.data[DOMAIN]['data'].get(PARAM_MAPPING.get(param, ''), 0)
            new_value = current_value + delta

            # Apply limits like in the web client
            if param == '0003':  # Fan speed
                new_value = max(0, min(25, new_value))
            elif param in ['0015', '0004']:  # Temperatures
                new_value = max(10, min(90, new_value))
            else:
                new_value = max(0, new_value)

            _LOGGER.info("Changing parameter %s by %s: %s -> %s", param, delta, current_value, new_value)
            await send_mqtt_command(hass, "set_param", param, new_value)
        elif value is not None:
            # Set parameter to specific value
            _LOGGER.info("Setting parameter %s to %s", param, value)
            await send_mqtt_command(hass, "set_param", param, value)

    # Register services
    hass.services.async_register(
        DOMAIN,
        "send_command",
        send_command_service,
        schema=vol.Schema(
            {
                vol.Required("cmd_type"): vol.In(["set_param", "get_param", "get_var"]),
                vol.Required("param"): cv.string,
                vol.Optional("value", default=0): cv.positive_int,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        "request_status",
        request_status_service,
    )

    hass.services.async_register(
        DOMAIN,
        "reconnect_bluetooth",
        reconnect_bluetooth_service,
    )

    hass.services.async_register(
        DOMAIN,
        "change_parameter",
        change_parameter_service,
        schema=vol.Schema(
            {
                vol.Required("param"): cv.string,
                vol.Optional("value"): cv.positive_int,
                vol.Optional("delta"): int,
            }
        ),
    )

    _LOGGER.info("Kotel MQTT services registered")

async def start_bluetooth_monitoring(hass: HomeAssistant):
    """Start monitoring Bluetooth connection status."""
    config = hass.data[DOMAIN]

    async def monitor_bluetooth_connection(_):
        """Monitor Bluetooth connection and detect timeouts."""
        if config["last_kotel_message"]:
            time_since_last_message = (datetime.now() - config["last_kotel_message"]).total_seconds()

            if time_since_last_message > config["bluetooth_timeout"]:
                # Bluetooth timeout detected
                if config["bluetooth_connected"]:
                    _LOGGER.warning("Bluetooth timeout detected - no messages for %.1f seconds",
                                   time_since_last_message)
                    config["bluetooth_connected"] = False
                    hass.loop.call_soon_threadsafe(
                        async_dispatcher_send, hass, f"{DOMAIN}_status_update"
                    )
            elif not config["bluetooth_connected"] and config["connected"]:
                config["bluetooth_connected"] = True
                _LOGGER.info("Bluetooth connection restored")
                hass.loop.call_soon_threadsafe(
                    async_dispatcher_send, hass, f"{DOMAIN}_status_update"
                )

    # Start monitoring
    config["monitor_task"] = async_track_time_interval(
        hass, monitor_bluetooth_connection, timedelta(seconds=1)
    )

async def start_polling(hass: HomeAssistant):
    """Start polling for data at regular intervals."""
    config = hass.data[DOMAIN]

    async def async_update(_):
        """Update data from kotel via MQTT."""
        if config["connected"]:
            _LOGGER.debug("Polling for data update via MQTT")
            await request_initial_data(hass)
        else:
            _LOGGER.debug("Not connected, requesting status")
            await request_kotel_status(hass)

    # Initial update after short delay
    await asyncio.sleep(3)
    await async_update(None)

    # Set up periodic polling
    async_track_time_interval(
        hass, async_update, timedelta(seconds=config["polling_interval"])
    )

async def request_kotel_status(hass: HomeAssistant):
    """Request status from kotel via MQTT."""
    config = hass.data[DOMAIN]

    payload = {
        "type": "status_request",
        "timestamp": asyncio.get_event_loop().time()
    }

    try:
        await mqtt.async_publish(
            hass,
            config["status_topic"],
            json.dumps(payload)
        )
        _LOGGER.debug("Status request sent")
    except Exception as e:  # noqa: BLE001
        _LOGGER.error("Error sending status request: %s", e)

async def reconnect_bluetooth(hass: HomeAssistant):
    """Send Bluetooth reconnect command to kotel_mqtt.py."""
    config = hass.data[DOMAIN]
    base_url = f"http://{config['host']}:9999"  # kotel_mqtt.py runs on port 9999

    try:
        _LOGGER.info("Sending Bluetooth reconnect request to %s/reconnect", base_url)
        async with aiohttp.ClientSession() as session:  # noqa: SIM117
            async with session.get(f"{base_url}/reconnect") as response:
                if response.status == 200:
                    _LOGGER.info("Bluetooth reconnect request sent successfully")
                    return True
                _LOGGER.error("Bluetooth reconnect failed with status: %s", response.status)
                return False

    except Exception as e:  # noqa: BLE001
        _LOGGER.error("Error sending Bluetooth reconnect request: %s", e)
        return False

async def request_initial_data(hass: HomeAssistant):
    """Request initial data parameters from kotel."""

    # Request all important parameters like in web client
    params_to_request = [
        # Parameters
        ("get_param", "0001"),  # Fuel supply
        ("get_param", "0002"),  # Pause duration
        ("get_param", "0003"),  # Fan speed
        ("get_param", "0004"),  # Thermostat
        ("get_param", "0007"),  # Ignition
        ("get_param", "0015"),  # Stabilization temp
        ("get_param", "001D"),  # Operation mode

        # Variables
        ("get_var", "04"),      # Temperature
        ("get_var", "09"),      # Flame level
        ("get_var", "11"),      # Automat point
    ]

    for cmd_type, param in params_to_request:
        await send_mqtt_command(hass, cmd_type, param)

async def send_mqtt_command(hass: HomeAssistant, cmd_type: str, param: str, value: int = 0):
    """Send a command to kotel via MQTT."""
    config = hass.data[DOMAIN]
    control_topic = f"{config['topic_prefix']}/control"

    payload = {
        "cmd_type": cmd_type,
        "param": param,
        "value": value
    }

    try:
        await mqtt.async_publish(
            hass,
            control_topic,
            json.dumps(payload)
        )
        _LOGGER.debug("MQTT command sent: %s %s=%s", cmd_type, param, value)
        return True  # noqa: TRY300
    except Exception as e:  # noqa: BLE001
        _LOGGER.error("Error sending MQTT command: %s", e)
        return False
