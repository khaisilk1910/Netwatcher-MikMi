"""Pure unit tests that run without a Home Assistant install."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / 'custom_components' / 'netwatcher_mikmi'
# Avoid importing custom integration __init__, which requires live HA.
ns = types.ModuleType('custom_components')
ns.__path__ = [str(ROOT / 'custom_components')]
sys.modules.setdefault('custom_components', ns)
mod = types.ModuleType('custom_components.netwatcher_mikmi')
mod.__path__ = [str(PKG_DIR)]
sys.modules.setdefault('custom_components.netwatcher_mikmi', mod)
inv_mod = importlib.import_module('custom_components.netwatcher_mikmi.inventory')
sec = importlib.import_module('custom_components.netwatcher_mikmi.security')
Inventory = inv_mod.Inventory


def snapshot(mac='AA:BB:CC:DD:EE:01', dynamic='true', status='bound', present=True):
    return {'leases': [{'mac-address': mac, 'address': '192.168.88.105', 'comment': 'Phone',
                        'dynamic': dynamic, 'status': status}],
            'arp': [{'mac-address': mac, 'address': '192.168.88.105', 'complete': 'true'}] if present else [],
            'bridge_hosts': []}


def ingest(inv, router, moment=1000, alert_existing=False, wifi=None, **kw):
    return inv.ingest(router, wifi, moment, 120, set(), set(),
                      alert_existing=alert_existing, xiaomi_configured=False, **kw)


def test_first_poll_baseline_silent_new_dynamic_alert_afterward():
    inv = Inventory()
    assert ingest(inv, snapshot(), 1000) == []
    assert inv.baseline_complete
    # New device after baseline -> alert exactly once.
    new = 'AA:BB:CC:DD:EE:02'
    data = snapshot(new)
    events = ingest(inv, data, 1030)
    assert [e['type'] for e in events] == ['new_dynamic']
    assert not any(e['type'] == 'new_dynamic' for e in ingest(inv, data, 1060))
    restarted = Inventory(inv.dump())
    assert not any(e['type'] == 'new_dynamic' for e in ingest(restarted, data, 1090))


def test_optional_existing_baseline_alert():
    inv = Inventory()
    assert [e['type'] for e in ingest(inv, snapshot(), 1000, alert_existing=True)] == ['new_dynamic']


def test_not_a_new_dynamic_without_presence_or_static():
    inv = Inventory()
    ingest(inv, {'leases': [], 'arp': [], 'bridge_hosts': []})
    assert not any(e['type'] == 'new_dynamic' for e in ingest(inv, snapshot(present=False), 1030))
    assert not any(e['type'] == 'new_dynamic' for e in ingest(inv, snapshot(dynamic='false'), 1060))


def test_online_offline_and_partial_source_failure():
    inv = Inventory()
    ingest(inv, snapshot(), 1000)
    assert inv.statistics()['online'] == 1
    # A temporarily failed router -> no mass offline event.
    assert ingest(inv, None, 1300) == []
    assert inv.statistics()['unknown'] == 1
    # No false offline event on recovery from unknown (unknown != online).
    assert ingest(inv, snapshot(present=False), 1350) == []
    assert inv.statistics()['offline'] == 1
    assert [e['type'] for e in ingest(inv, snapshot(), 1380)] == ['connected']
    assert ingest(inv, snapshot(present=False), 1410) == []
    assert inv.devices['AA:BB:CC:DD:EE:01']['online'] == 'online'
    assert ingest(inv, snapshot(present=False), 1470) == []
    assert [e['type'] for e in ingest(inv, snapshot(present=False), 1550)] == ['disconnected']


def test_mesh_aggregate_does_not_claim_ap():
    inv = Inventory()
    ingest(inv, {'leases': [], 'arp': [], 'bridge_hosts': []})
    mac = 'AA:BB:CC:DD:EE:04'
    wifi = [dict(mac=mac, online=True, signal=-60, band='5GHz', name='Phone',
                 source_host='192.168.88.2', source_name='AX7000')]
    inv.ingest(None, wifi, 1500, 120, set(), set(), xiaomi_configured=True)
    assert inv.devices[mac]['connection'] == 'wifi'
    assert inv.devices[mac]['ap_name'] is None
    # Only after explicitly verifying node returns DIRECT clients.
    inv.ingest(None, wifi, 1530, 120, {'192.168.88.2'}, set(), xiaomi_configured=True)
    assert inv.devices[mac]['ap_name'] == 'AX7000'
    wifi += [dict(wifi[0], source_host='192.168.88.3', source_name='AX6000')]
    inv.ingest(None, wifi, 1560, 120, {'192.168.88.2', '192.168.88.3'}, set(), xiaomi_configured=True)
    assert inv.devices[mac]['ap_name'] is None


def test_safe_recipient_and_lan_validation():
    assert sec.parse_recipients('1234567, abcdef_01\n1234567') == ['1234567', 'abcdef_01']
    for bad in ['http://127.0.0.1', 'abc\rInjected', 'abc', 'x '*100]:
        with pytest.raises(ValueError):
            sec.parse_recipients(bad)
    with pytest.raises(ValueError):
        sec.parse_recipients(','.join(str(i+10000000) for i in range(21)))
    for bad in ['router.local', '8.8.8.8', '127.0.0.1', '169.254.1.1']:
        with pytest.raises(ValueError):
            sec.private_ipv4(bad)
    assert sec.private_ipv4('192.168.88.1') == '192.168.88.1'
    with pytest.raises(ValueError):
        sec.validate_zalo_token('evil\naccess_token:x')
