"""Hardware parsing and threshold-state tests. No Home Assistant required."""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'custom_components' / 'netwatcher_mikmi'
namespace = types.ModuleType('custom_components'); namespace.__path__ = [str(ROOT / 'custom_components')]
sys.modules.setdefault('custom_components', namespace)
pkg = types.ModuleType('custom_components.netwatcher_mikmi'); pkg.__path__ = [str(PKG)]
sys.modules.setdefault('custom_components.netwatcher_mikmi', pkg)
hw = importlib.import_module('custom_components.netwatcher_mikmi.hardware')
const = importlib.import_module('custom_components.netwatcher_mikmi.const')


def raw():
    return {
        'resource': [{'cpu-load': '66', 'total-memory': '256.0MiB', 'free-memory': '64MiB',
                      'total-hdd-space': '1024MiB', 'free-hdd-space': '512MiB',
                      'uptime': '1w2d03:04:05', 'board-name': 'hAP ax3',
                      'architecture-name': 'arm64', 'cpu-count': '4',
                      'cpu-frequency': '1800', 'version': '7.24.4 (stable)'}],
        'health': [{'name': 'cpu-temperature', 'value': '58', 'type': 'C'},
                   {'name': 'temperature', 'value': '44', 'type': 'C'},
                   {'name': 'voltage', 'value': '23.7', 'type': 'V'},
                   {'name': 'fan1-speed', 'value': '2212', 'type': 'RPM'}],
        'routerboard': [{'model': 'C53UiG+5HPaxD2HPaxD', 'current-firmware': '7.24.4'}],
    }


def settings(**kw):
    return {const.CONF_HARDWARE_ALERTS: True,
            const.CONF_HARDWARE_CPU_ENABLED: True,
            const.CONF_HARDWARE_RAM_ENABLED: True,
            const.CONF_HARDWARE_TEMP_ENABLED: True,
            const.CONF_HARDWARE_SAMPLES: 3,
            const.CONF_HARDWARE_COOLDOWN: 30,
            **kw}


def test_bytes_percent_and_routeros_uptime():
    assert hw.byte_count('256.0MiB') == 268435456
    assert hw.byte_count('64MiB') == 67108864
    assert hw.byte_count('4096') == 4096
    assert hw.byte_count('bad') is None
    assert hw.percent(-3, 100) is None
    assert hw.percent(110, 100) is None
    assert hw.uptime_seconds('1w2d03:04:05') == 9*86400+3*3600+4*60+5
    assert hw.uptime_seconds('2w3d4h5m6s') == 17*86400 + 4*3600 + 5*60+6
    assert hw.uptime_seconds('21:00:30') == 75630
    assert hw.uptime_seconds('bad') is None


def test_health_routeros_v7_all_metrics():
    snap = hw.normalize_hardware(raw())
    r = snap['readings']
    assert r['cpu'] == 66
    assert r['ram'] == 75
    assert r['storage'] == 50
    assert r['cpu_temperature'] == 58
    assert r['board_temperature'] == 44
    assert r['temperature'] == 58  # Prefer CPU sensor for the main gauge.
    assert r['fan_rpm'] == 2212
    assert r['voltage'] == 23.7
    assert r['total_ram_mib'] == 256
    assert r['cpu_count'] == 4
    assert snap['board']['model'] == 'C53UiG+5HPaxD2HPaxD'
    assert snap['board']['routeros_version'] == '7.24.4 (stable)'
    assert 'serial' not in repr(snap).lower()


def test_routeros_v6_flat_health_and_missing_chr_sensors():
    src=raw();src['health']=[{'temperature':'49C','cpu-temperature':'58C', 'voltage':'24V'}]
    result=hw.normalize_hardware(src)
    assert result['readings']['temperature']==58
    assert result['readings']['voltage']==24
    src['health']=[]
    result=hw.normalize_hardware(src)
    assert result['readings']['temperature'] is None
    assert result['health_supported'] is False


def test_slow_sensors_reuse_cached_values_only_if_not_queried():
    before=hw.normalize_hardware(raw())
    updated={'resource':raw()['resource']}
    updated['resource'][0]['cpu-load']='81'
    result=hw.normalize_hardware(updated,before)
    assert result['readings']['cpu']==81
    assert result['readings']['temperature']==58
    updated['health']=[]
    result=hw.normalize_hardware(updated,before)
    assert result['readings']['temperature'] is None


def test_threshold_debounces_and_recovers_with_hysteresis():
    engine=hw.HardwareAlertEngine()
    options=settings()
    for when in (1000,1015):
        events,status=engine.process({'cpu':94,'ram':30,'temperature':40},options,now=when)
        assert not events and not status['cpu']['active']
    events,status=engine.process({'cpu':94,'ram':30,'temperature':40},options,now=1030)
    assert [(e['metric'],e['kind']) for e in events]==[('cpu','high')]
    assert status['cpu']['active']
    # Values inside hysteresis band should not clear the active alarm.
    for when in (1045,1060,1075):
        events,_=engine.process({'cpu':83},options,now=when)
        assert not events
    for when in (1090,1105):
        events,_=engine.process({'cpu':77},options,now=when)
        assert not events
    events,status=engine.process({'cpu':77},options,now=1120)
    assert [(e['metric'],e['kind']) for e in events]==[('cpu','recovered')]
    assert not status['cpu']['active']


def test_threshold_persistence_across_restart_and_cooldown():
    engine=hw.HardwareAlertEngine()
    options=settings(**{const.CONF_HARDWARE_SAMPLES:2})
    engine.process({'ram':99},options,now=1000)
    events,_=engine.process({'ram':99},options,now=1010)
    assert len(events)==1
    restarted=hw.HardwareAlertEngine(engine.dump())
    for when in (1020,1030):
        events,_=restarted.process({'ram':99},options,now=when)
        assert not events
    restarted.process({'ram':79},options,now=1040)
    events,_=restarted.process({'ram':79},options,now=1050)
    assert len(events)==1 and events[0]['kind']=='recovered'
    restarted.process({'ram':99},options,now=1060)
    events,status=restarted.process({'ram':99},options,now=1070)
    assert not events and status['ram']['active'] # within 30 minute cooldown


def test_missing_temperature_never_produces_alert():
    engine=hw.HardwareAlertEngine()
    for t in (1000,1015,1030,1045):
        events,status=engine.process({'temperature':None},settings(),now=t)
        assert not events and status['temperature']['value'] is None


def test_disabled_notifications_cannot_emit_but_still_show_gauge():
    engine=hw.HardwareAlertEngine()
    cfg=settings(**{const.CONF_HARDWARE_ALERTS:False,const.CONF_HARDWARE_SAMPLES:2})
    engine.process({'cpu':99},cfg,now=1000)
    events,status=engine.process({'cpu':99},cfg,now=1015)
    assert not events and status['cpu']['active'] and not status['cpu']['enabled']


def test_multi_metric_transitions_have_only_enabled_flags():
    engine=hw.HardwareAlertEngine()
    cfg=settings(**{const.CONF_HARDWARE_SAMPLES:1, const.CONF_HARDWARE_RAM_ENABLED:False})
    events,status=engine.process({'cpu':98,'ram':99,'temperature':86},cfg,now=5000)
    assert {e['metric'] for e in events}=={'cpu','temperature'}
    assert status['ram']['active'] and not status['ram']['enabled']


def test_hardware_command_allowlist_does_not_modify_router():
    router=importlib.import_module('custom_components.netwatcher_mikmi.routeros')
    assert all(command.endswith('/print') for command, _ in router.COMMANDS.values())
    seen=[]
    instance=object.__new__(router.RouterOSReader)
    instance._connect_and_read=lambda commands: seen.extend(cmd for cmd,_,_ in commands.values()) or {
        k:[] for k in commands
    }
    instance.fetch_hardware(True,True)
    instance.fetch_netwatch()
    assert '/system/resource/print' in seen
    assert '/system/health/print' in seen
    assert '/system/routerboard/print' in seen
    assert '/tool/netwatch/print' in seen
    assert all(cmd.endswith('/print') for cmd in seen)


def test_temperature_cached_values_do_not_count_as_new_samples():
    engine=hw.HardwareAlertEngine()
    cfg=settings(**{const.CONF_HARDWARE_SAMPLES:3})
    for t in (0,15,30,45,55,59):
        events,_=engine.process({'temperature':92,'cpu':20},cfg,now=t,observed={'cpu'})
        assert not events
    engine.process({'temperature':92},cfg,now=60,observed={'temperature'})
    for t in (75,90,105):
        events,_=engine.process({'temperature':92},cfg,now=t,observed={'cpu'})
        assert not events
    engine.process({'temperature':92},cfg,now=120,observed={'temperature'})
    events,_=engine.process({'temperature':92},cfg,now=180,observed={'temperature'})
    assert len(events)==1 and events[0]['metric']=='temperature'
