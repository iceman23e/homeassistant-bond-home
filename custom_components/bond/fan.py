"""Bond Home Fan Integration"""
from homeassistant.components.fan import (
    SUPPORT_SET_SPEED,
    SUPPORT_DIRECTION,
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
    FanEntity
)

from bond import (DeviceTypes,
                  Actions,
                  Directions)

import logging
DOMAIN = 'bond'

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Bond Fan platform"""
    bond = hass.data[DOMAIN]['bond_hub']

    for deviceId in bond.getDeviceIds():
        device = bond.getDevice(deviceId)
        if device['type'] != DeviceTypes.CEILING_FAN:
            continue

        deviceProperties = bond.getProperties(deviceId)
        fan = BondFan(bond, deviceId, device, deviceProperties)
        add_entities([fan])


class BondFan(FanEntity):
    """Representation of an Bond Fan"""

    def __init__(self, bond, deviceId, device, properties):
        """Initialize a Bond Fan"""
        self._bond = bond
        self._deviceId = deviceId
        self._device = device
        self._properties = properties
        self._name = device['name']
        self._state = None
        self._speed_list = []
        self._speed_name_by_value = {}
        self._attributes = {}

        if Actions.SET_SPEED in self._device['actions']:
            if 'max_speed' in self._properties:
                self._speed_high = int(self._properties['max_speed'])
                self._speed_low = int(1)
                self._speed_list.append(SPEED_LOW)
                self._speed_name_by_value[self._speed_low] = SPEED_LOW
                if self._speed_high > 2:
                    self._speed_medium = (self._speed_high + 1) // 2
                    self._speed_list.append(SPEED_MEDIUM)
                    self._speed_name_by_value[self._speed_medium] = SPEED_MEDIUM
                self._speed_list.append(SPEED_HIGH)
                self._speed_name_by_value[self._speed_high] = SPEED_HIGH

    @property
    def name(self):
        """Return the display name of this fan"""
        return self._name

    @property
    def is_on(self):
        """Return true if fan is on"""
        return self._state

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return self._speed_list
    
    @property
    def device_state_attributes(self):
        """Return state attributes """
        """For now, the only attribute being tracked is 'current speed'.
        Since this is accessible via the 'speed' property, there is no
        need to return any attributes at this time.
        """
        # return self._attributes
        return None

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = 0

        if Actions.SET_SPEED in self._device['actions']:
            supported_features |= SUPPORT_SET_SPEED

        if Actions.SET_DIRECTION in self._device['actions']:
            supported_features |= SUPPORT_DIRECTION

        return supported_features

    def turn_on(self, speed=None, **kwargs):
        """Instruct the fan to turn on"""
        self._bond.turnOn(self._deviceId)
        if speed is not None:
            self.set_speed(speed)

    def turn_off(self, **kwargs):
        """Instruct the fan to turn off"""
        self._attributes['current_speed'] = SPEED_OFF
        self._bond.turnOff(self._deviceId)

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        if speed == SPEED_HIGH:
            self._bond.setSpeed(self._deviceId, self._speed_high)
        elif speed == SPEED_MEDIUM:
            self._bond.setSpeed(self._deviceId, self._speed_medium)
        elif speed == SPEED_LOW:
            self._bond.setSpeed(self._deviceId, self._speed_low)
        self._attributes['current_speed'] = speed

    def set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        if direction == "forward":
            self._bond.setDirection(self._deviceId, Directions.FORWARD)
        elif direction == "reverse":
            self._bond.setDirection(self._deviceId, Directions.REVERSE)
        self._attributes['current_direction'] = direction

    @property
    def current_direction(self):
        """Return the current direction of the fan."""
        return self._attributes.get("current_direction")

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._attributes.get("current_speed")

    def update(self):
        """Fetch new state data for this fan
        This is the only method that should fetch new data for Home Assistant
        """
        bondState = self._bond.getDeviceState(self._deviceId)
        if 'power' in bondState:
            self._state = True if bondState['power'] == 1 else False
            if self._state and bondState['speed'] in self._speed_name_by_value:
                self._attributes['current_speed'] = self._speed_name_by_value[bondState['speed']]
            else:
                self._attributes['current_speed'] = SPEED_OFF

        if 'direction' in bondState:
            if bondState['direction'] == Directions.REVERSE:
                self._attributes['current_direction'] = "reverse"
            else:
                self._attributes['current_direction'] = "forward"

    @property
    def unique_id(self):
        """Get the unique identifier of the device."""
        return self._deviceId

    @property
    def device_id(self):
        """Return the ID of this fan."""
        return self.unique_id