"""Tests for HAEntity synthetic/availability behavior. """

from zendure_bridge.homeassistant.ha_entity import HAEntity
from zendure_bridge.device import ZendureState
from .bridge_mock import BridgeMock


def test_override_is_synthetic_property_in_subclass_affects_availability() -> None:
    class Derived(HAEntity):
        @property
        def ha_component_type(self) -> str:
            return "test"

        @property
        def is_synthetic(self) -> bool:
            return True

    d = Derived("Derived", "master_switch")
    state = ZendureState()
    mock = BridgeMock()

    # Since the subclass reports itself synthetic, availability should be True
    # even though the underlying state field is None/uninitialized.
    assert d.is_synthetic is True
    assert d.is_available(state, mock.bc) is True


def test_default_is_synthetic_false() -> None:
    class Minimal(HAEntity):
        @property
        def ha_component_type(self) -> str:
            return "test"

    # use an actual ZendureState field name so get_value() can safely access it
    m = Minimal("m", "master_switch")
    state = ZendureState()
    mock = BridgeMock()
    assert m.is_synthetic is False
    # with no underlying state value, availability should be False
    assert m.is_available(state, mock.bc) is False


def test_get_value_display_and_has_changed_behavior() -> None:
    class Derived(HAEntity):
        @property
        def ha_component_type(self) -> str:
            return "test"

    d = Derived("Derived", "solar_input_power")
    state = ZendureState()

    # initial value not set -> get_value returns None and has_changed is False
    assert d.get_value(state) is None
    assert d.get_display_value(state) is None
    assert d.has_changed(state) is False

    # update underlying state and expect has_changed True on first observation
    state.solar_input_power = 10
    assert d.get_value(state) == 10
    assert d.get_display_value(state) == 10
    assert d.has_changed(state) is True

    # subsequent call with same value should report no change
    assert d.has_changed(state) is False


def test_has_availability_changed_transitions() -> None:
    class Derived(HAEntity):
        @property
        def ha_component_type(self) -> str:
            return "test"

    d = Derived("Derived", "solar_input_power")
    state = ZendureState()
    mock = BridgeMock()

    # default _last_availability is True; with unset state availability False,
    # so first has_availability_changed should be True (transition True -> False)
    assert d.is_available(state, mock.bc) is False
    assert d.has_availability_changed(state, mock.bc) is True

    # subsequent call without state change should be False
    assert d.has_availability_changed(state, mock.bc) is False

