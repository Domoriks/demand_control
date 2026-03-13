"""Constants for the Demand Control integration."""

from homeassistant.const import Platform

DOMAIN = "demand_control"
NAME = "Demand Control"

CONF_HOME_POWER_SENSOR = "home_power_sensor"
CONF_CURRENT_AVERAGE_DEMAND_SENSOR = "current_average_demand_sensor"
CONF_MAXIMUM_DEMAND_CURRENT_MONTH_SENSOR = "maximum_demand_current_month_sensor"
# These keys are persisted in config entries; keep names stable for compatibility.
# In this integration, "actuator" refers to the EV charger control entity.
CONF_ACTUATOR_MODE = "actuator_mode"
CONF_CURRENT_ACTUATOR_ENTITY = "current_actuator_entity"
CONF_POWER_ACTUATOR_ENTITY = "power_actuator_entity"
CONF_EV_POWER_SENSOR = "ev_power_sensor"
CONF_EV_CURRENT_SENSOR = "ev_current_sensor"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MAX_HOME_DEMAND_KW = "max_home_demand_kw"
CONF_PHASE_COUNT = "phase_count"
CONF_LINE_VOLTAGE_V = "line_voltage_v"
CONF_MIN_CHARGE_CURRENT_A = "min_charge_current_a"
CONF_MAX_CHARGE_CURRENT_A = "max_charge_current_a"
CONF_MAX_CHARGE_POWER_KW = "max_charge_power_kw"
CONF_CURRENT_STEP_A = "current_step_a"
CONF_POWER_STEP_KW = "power_step_kw"

ACTUATOR_MODE_CURRENT = "current"
ACTUATOR_MODE_POWER = "power"

DEFAULT_SCAN_INTERVAL = 3
DEFAULT_MAX_HOME_DEMAND_KW = 11.0
DEFAULT_PHASE_COUNT = 1
DEFAULT_LINE_VOLTAGE_V = 230.0
DEFAULT_MIN_CHARGE_CURRENT_A = 6.0
DEFAULT_MAX_CHARGE_CURRENT_A = 20.0
DEFAULT_MAX_CHARGE_POWER_KW = 11.0
DEFAULT_CURRENT_STEP_A = 0.05
DEFAULT_POWER_STEP_KW = 0.1

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]
