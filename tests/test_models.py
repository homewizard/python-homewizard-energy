"""Test for HomeWizard Energy Models."""

import json
from datetime import datetime

from homewizard_energy import Data, Device, State

from . import load_fixtures


def test_device_with_expected_parameters():
    """TODO."""
    device: Device = Device.from_dict(json.loads(load_fixtures("device.json")))
    assert device
    assert device.product_type == "HWE-P1"
    assert device.product_name == "P1 Meter"
    assert device.serial == "3c39e7aabbcc"
    assert device.firmware_version == "2.11"
    assert device.api_version == "v1"


def test_device_with_new_api_version():
    """TODO."""
    device: Device = Device.from_dict(
        json.loads(load_fixtures("device_invalid_api.json"))
    )
    assert device
    assert device.product_type == "HWE-P1"
    assert device.product_name == "P1 Meter"
    assert device.serial == "3c39e7aabbcc"
    assert device.firmware_version == "2.11"
    assert device.api_version == "v2"


def test_device_with_unknown_datafields():
    """TODO."""
    device: Device = Device.from_dict(
        json.loads(load_fixtures("device_extra_parameters.json"))
    )
    assert device
    assert device.product_type == "HWE-P1"
    assert device.product_name == "P1 Meter"
    assert device.serial == "3c39e7aabbcc"
    assert device.firmware_version == "2.11"
    assert device.api_version == "v1"


def test_data_p1():
    """TODO."""
    data: Data = Data.from_dict(json.loads(load_fixtures("data_p1.json")))

    assert data
    assert data.smr_version == 50
    assert data.meter_model == "ISKRA  2M550T-101"
    assert data.wifi_ssid == "My Wi-Fi"
    assert data.wifi_strength == 100
    assert data.total_power_import_t1_kwh == 10830.511
    assert data.total_power_import_t2_kwh == 2948.827
    assert data.total_power_export_t1_kwh == 1285.951
    assert data.total_power_export_t2_kwh == 2876.51
    assert data.active_power_w == -543
    assert data.active_power_l1_w == -676
    assert data.active_power_l2_w == 133
    assert data.active_power_l3_w == 0
    assert data.total_gas_m3 == 2569.646
    assert data.gas_timestamp == datetime(2021, 6, 6, 14, 0, 10)


def test_data_p1_no_gas():
    """TODO."""
    data: Data = Data.from_dict(json.loads(load_fixtures("data_p1_no_gas.json")))

    assert data
    assert data.smr_version == 50
    assert data.meter_model == "ISKRA  2M550T-101"
    assert data.wifi_ssid == "My Wi-Fi"
    assert data.wifi_strength == 100
    assert data.total_power_import_t1_kwh == 10830.511
    assert data.total_power_import_t2_kwh == 2948.827
    assert data.total_power_export_t1_kwh == 1285.951
    assert data.total_power_export_t2_kwh == 2876.51
    assert data.active_power_w == -543
    assert data.active_power_l1_w == -676
    assert data.active_power_l2_w == 133
    assert data.active_power_l3_w == 0
    assert data.total_gas_m3 is None
    assert data.gas_timestamp is None


def test_data_p1_single_phase():
    """TODO."""
    data: Data = Data.from_dict(json.loads(load_fixtures("data_p1_single_phase.json")))

    assert data
    assert data.smr_version == 50
    assert data.meter_model == "ISKRA  2M550T-101"
    assert data.wifi_ssid == "My Wi-Fi"
    assert data.wifi_strength == 100
    assert data.total_power_import_t1_kwh == 10830.511
    assert data.total_power_import_t2_kwh == 2948.827
    assert data.total_power_export_t1_kwh == 1285.951
    assert data.total_power_export_t2_kwh == 2876.51
    assert data.active_power_w == -543
    assert data.active_power_l1_w == -676
    assert data.active_power_l2_w is None
    assert data.active_power_l3_w is None
    assert data.total_gas_m3 == 2569.646
    assert data.gas_timestamp == datetime(2021, 6, 6, 14, 0, 10)


def test_data_kwh_single_phase():
    """TODO."""

    data: Data = Data.from_dict(json.loads(load_fixtures("data_kwh_single_phase.json")))

    assert data
    assert data.smr_version is None
    assert data.meter_model is None
    assert data.wifi_ssid == "My Wi-Fi"
    assert data.wifi_strength == 100
    assert data.total_power_import_t1_kwh == 10830.511
    assert data.total_power_import_t2_kwh is None
    assert data.total_power_export_t1_kwh == 2948.827
    assert data.total_power_export_t2_kwh is None
    assert data.active_power_w == 640
    assert data.active_power_l1_w == 640
    assert data.active_power_l2_w is None
    assert data.active_power_l3_w is None
    assert data.total_gas_m3 is None
    assert data.gas_timestamp is None


def test_data_kwh_three_phase():
    """TODO."""
    data: Data = Data.from_dict(json.loads(load_fixtures("data_kwh_three_phase.json")))

    assert data
    assert data.smr_version is None
    assert data.meter_model is None
    assert data.wifi_ssid == "My Wi-Fi"
    assert data.wifi_strength == 100
    assert data.total_power_import_t1_kwh == 10830.511
    assert data.total_power_import_t2_kwh is None
    assert data.total_power_export_t1_kwh == 2948.827
    assert data.total_power_export_t2_kwh is None
    assert data.active_power_w == -543
    assert data.active_power_l1_w == -676
    assert data.active_power_l2_w == 133
    assert data.active_power_l3_w == 0
    assert data.total_gas_m3 is None
    assert data.gas_timestamp is None


def test_data_energysocket():
    """TODO."""
    data: Data = Data.from_dict(json.loads(load_fixtures("data_energysocket.json")))

    assert data
    assert data.smr_version is None
    assert data.meter_model is None
    assert data.wifi_ssid == "My Wi-Fi"
    assert data.wifi_strength == 100
    assert data.total_power_import_t1_kwh == 10830.511
    assert data.total_power_import_t2_kwh is None
    assert data.total_power_export_t1_kwh == 2948.827
    assert data.total_power_export_t2_kwh is None
    assert data.active_power_w == 123
    assert data.active_power_l1_w == 123
    assert data.active_power_l2_w is None
    assert data.active_power_l3_w is None
    assert data.total_gas_m3 is None
    assert data.gas_timestamp is None


def test_state():
    """TODO."""
    state: State = State.from_dict(json.loads(load_fixtures("state.json")))

    assert state
    assert not state.power_on
    assert not state.switch_lock
    assert state.brightness == 255

    state: State = State.from_dict(
        json.loads(load_fixtures("state_switch_lock_and_brightness.json"))
    )

    assert state
    assert state.power_on
    assert state.switch_lock
    assert state.brightness == 10
