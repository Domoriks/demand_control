# Demand Control

Home Assistant custom integration for dynamic EV charging control based on home power and demand budget.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=domoriks&repository=demand_control&category=integration)
<!-- [![Open your Home Assistant instance and start setting up Demand Control.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=demand_control) -->

## Disclaimer

- It is built and maintained by a single developer with a personal setup.
- Use this integration at your own risk. The developer is not responsible for any damage, charging issues, data loss, or other consequences.

## Features

- UI-based setup with entity selectors (no YAML required).
- Dynamic charging control from live home power and optional demand sensors.
- Two EV actuator modes: current (`A`) or power (`kW`) using a Home Assistant `number` entity.
- 15-minute demand guard with Current Projected Demand tracking.
- Resume lockout logic to avoid rapid resume while demand remains high.
- 11 diagnostic/runtime sensors and 3 configurable number entities.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository if needed:
   - URL: `https://github.com/domoriks/demand_control`
   - Category: `Integration`
3. Install **Demand Control** from HACS.
4. Restart Home Assistant.

### Manual installation

1. Copy `custom_components/demand_control` into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.

## Configuration

### Recommended meter integration

For the following sensor inputs, using entities from the DSMR integration is recommended:

- Home power sensor
- Current average demand sensor
- Maximum demand current month sensor

DSMR integration: https://www.home-assistant.io/integrations/dsmr

1. Go to `Settings -> Devices & Services`.
2. Click `Add Integration`.
3. Search for `Demand Control`.
4. Select `Home power sensor` (recommended source: DSMR integration).
5. Select `EV actuator mode` (`Current` or `Power`).
6. Select EV actuator entity:
   - `EV current actuator entity` when mode is `Current`
   - `EV power actuator entity` when mode is `Power`
7. Optional but recommended:
   - `Current average demand sensor` (recommended source: DSMR integration)
   - `Maximum demand current month sensor` (recommended source: DSMR integration)
8. Configure limits and tuning values (scan interval, max home demand, phase count, voltage, min/max and step values).

## Entities

This integration currently creates these platforms:

Platform | Description
-- | --
`sensor` | Status, home power, current average demand, current month max demand, Current Projected Demand, target current/power limits, resume lockout state/timestamp, EV actuator mode/entity
`number` | Config entities for max home demand, max charge current, and max charge power

## Blueprints

### Reset max home demand monthly

[![Open your Home Assistant instance and import this blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/domoriks/demand_control/blob/main/blueprints/automation/demand_control/reset_max_home_demand_monthly.yaml)

### Sync max home demand daily from monthly demand

[![Open your Home Assistant instance and import this blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/domoriks/demand_control/blob/main/blueprints/automation/demand_control/sync_max_home_demand_daily_from_month_max.yaml)

## Troubleshooting

- `missing_current_actuator`: Current mode selected but no EV current actuator entity set.
- `missing_power_actuator`: Power mode selected but no EV power actuator entity set.
- `home_power_unavailable`: Verify the selected home power sensor has valid numeric state.
- `current_average_demand_unavailable`: Optional demand sensor selected but unavailable.

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.demand_control: debug
```

## Repository structure

```text
custom_components/demand_control/
  __init__.py
  config_flow.py
  const.py
  coordinator.py
  manifest.json
  number.py
  sensor.py
  strings.json
  brand/
  translations/
blueprints/automation/demand_control/
```

## HACS publishing notes

- `hacs.json` is included in the repository root.
- Integration files are under `custom_components/demand_control`.
- `manifest.json` includes required HACS keys and a version.
- Brand assets exist in `custom_components/demand_control/brand`.

Before requesting inclusion in default HACS repositories, make sure your GitHub repository metadata is set:

- Add a clear repository description.
- Add relevant topics like `home-assistant`, `hacs`, `homeassistant-integration`.
- Publish GitHub releases for versioned installs.

## License

This project is open source and licensed under the MIT License.
See `LICENSE` for full text.