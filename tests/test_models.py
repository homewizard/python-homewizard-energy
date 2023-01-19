"""Test for HomeWizard Energy Models."""

import json
from datetime import datetime

from homewizard_energy import Data, Decryption, Device, ExternalDevice, State, System

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


def test_data_p1_full():
    """TODO."""
    # pylint: disable=too-many-statements

    data: Data = Data.from_dict(json.loads(load_fixtures("data_p1_full.json")))

    assert data
    assert data.wifi_ssid == "My Wi-Fi"
    assert data.wifi_strength == 100
    assert data.smr_version == 50
    assert data.meter_model == "ISKRA  2M550T-101"
    assert data.unique_meter_id == "00112233445566778899AABBCCDDEEFF"
    assert data.active_tariff == 2
    assert data.total_power_import_kwh == 13779.338
    assert data.total_power_import_t1_kwh == 10830.511
    assert data.total_power_import_t2_kwh == 2948.827
    assert data.total_power_export_kwh == 0
    assert data.total_power_export_t1_kwh == 0
    assert data.total_power_export_t2_kwh == 0
    assert data.active_power_w == -543
    assert data.active_power_l1_w == -676
    assert data.active_power_l2_w == 133
    assert data.active_power_l3_w == 0
    assert data.active_current_l1_a == -4
    assert data.active_current_l2_a == 2
    assert data.active_current_l3_a == 0
    assert data.active_frequency_hz == 50
    assert data.voltage_sag_l1_count == 1
    assert data.voltage_sag_l2_count == 1
    assert data.voltage_sag_l3_count == 0
    assert data.voltage_swell_l1_count == 0
    assert data.voltage_swell_l2_count == 0
    assert data.voltage_swell_l3_count == 0
    assert data.any_power_fail_count == 4
    assert data.long_power_fail_count == 5
    assert data.total_gas_m3 == 2569.646
    assert data.gas_timestamp == datetime(2021, 6, 6, 14, 0, 10)
    assert data.gas_unique_id == "01FFEEDDCCBBAA99887766554433221100"
    assert data.active_power_average_w == 123.000
    assert data.monthly_power_peak_w == 1111.000
    assert data.monthly_power_peak_timestamp == datetime(2023, 1, 1, 8, 0, 10)

    assert len(data.external_devices) == 5

    device = data.external_devices[0]
    assert device.unique_id == "01FFEEDDCCBBAA99887766554433221100"
    assert device.meter_type == ExternalDevice.DeviceType.GAS_METER
    assert device.value == 111.111
    assert device.unit == "m3"
    assert device.timestamp == datetime(2021, 6, 6, 14, 0, 10)

    device = data.external_devices[1]
    assert device.unique_id == "02FFEEDDCCBBAA99887766554433221100"
    assert device.meter_type == ExternalDevice.DeviceType.HEAT_METER
    assert device.value == 222.222
    assert device.unit == "m3"
    assert device.timestamp == datetime(2021, 6, 6, 14, 0, 10)

    device = data.external_devices[2]
    assert device.unique_id == "03FFEEDDCCBBAA99887766554433221100"
    assert device.meter_type == ExternalDevice.DeviceType.WARM_WATER_METER
    assert device.value == 333.333
    assert device.unit == "m3"
    assert device.timestamp == datetime(2021, 6, 6, 14, 0, 10)

    device = data.external_devices[3]
    assert device.unique_id == "04FFEEDDCCBBAA99887766554433221100"
    assert device.meter_type == ExternalDevice.DeviceType.WATER_METER
    assert device.value == 444.444
    assert device.unit == "m3"
    assert device.timestamp == datetime(2021, 6, 6, 14, 0, 10)

    device = data.external_devices[4]
    assert device.unique_id == "05FFEEDDCCBBAA99887766554433221100"
    assert device.meter_type == ExternalDevice.DeviceType.INLET_HEAT_METER
    assert device.value == 555.555
    assert device.unit == "m3"
    assert device.timestamp == datetime(2021, 6, 6, 14, 0, 10)


def test_data_watermeter():
    """TODO."""
    data: Data = Data.from_dict(json.loads(load_fixtures("data_watermeter.json")))

    assert data
    assert data.wifi_ssid == "My Wi-Fi"
    assert data.wifi_strength == 100
    assert data.active_liter_lpm == 13.12
    assert data.total_liter_m3 == 8129.123


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


def test_system():
    """TODO."""
    system: System = System.from_dict(
        json.loads(load_fixtures("system_cloud_enabled.json"))
    )

    assert system
    assert system.cloud_enabled

    system: System = System.from_dict(
        json.loads(load_fixtures("system_cloud_disabled.json"))
    )

    assert system
    assert not system.cloud_enabled


def test_decryption():
    """TODO."""
    decryption: Decryption = Decryption.from_dict(
        json.loads(load_fixtures("decryption.json"))
    )

    assert decryption
    assert decryption.key_set
    assert decryption.aad_set
