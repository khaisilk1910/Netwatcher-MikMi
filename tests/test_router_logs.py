"""Conservative MikroTik WAN log detection and restart/debounce behavior."""
from __future__ import annotations
import importlib
import time

monitor = importlib.import_module('custom_components.netwatcher_mikmi.log_monitor')


def mk(message, topics='system,error,critical', ident='*1', stamp='13:00:00'):
    return {'.id':ident, 'time':stamp, 'topics':topics, 'message':message}


def test_routeros_v7_login_failure_topic_without_account():
    # Official RouterOS 7 log format uses 'system,error,critical' for failures.
    assert monitor.classify_log('system,error,critical', 'login failure for user admin from 8.8.8.8 via ssh') == ('failed_admin_login','8.8.8.8')
    assert monitor.classify_log('system,info,account', 'user admin logged in from 9.9.9.9 via winbox') == ('external_admin_login','9.9.9.9')
    assert monitor.classify_log('system,info,account', 'user admin logged out from 9.9.9.9 via winbox') == (None,None)


def test_ignore_private_and_reserved_and_unmarked_firewall():
    for src in ('192.168.88.19','10.1.1.8','172.16.1.2','127.0.0.1','203.0.113.2','100.64.1.1'):
        assert monitor.classify_log('system,error,critical', f'login failure for user admin from {src} via ssh') == (None,None)
    assert monitor.classify_log('firewall,info', 'input: in:pppoe-out1, proto TCP 8.8.8.8:555->1.1.1.1:22') == (None,None)
    assert monitor.classify_log('firewall,info', 'NWMIKMI-WAN input: in:pppoe-out1, proto TCP 8.8.8.8:555->1.1.1.1:22') == ('wan_management_probe','8.8.8.8')
    assert monitor.classify_log('dhcp,info', 'login failed from 8.8.8.8') == (None,None)


def test_baseline_silent_and_restart_dedup():
    m = monitor.RouterLogMonitor()
    rows = [mk('login failure for user admin from 8.8.8.8 via ssh', ident=f'*{i}') for i in range(3)]
    assert m.ingest(rows,timestamp=1700000000) == []
    assert m.baselined
    other = monitor.RouterLogMonitor(m.dump())
    assert other.ingest(rows,timestamp=1700000020) == []
    assert other.rows()[1] == 3
    assert 'password=<redacted>' == monitor.safe_text('password=top-secret')


def test_threshold_per_ip_and_cooldown_and_distinct_rows():
    m = monitor.RouterLogMonitor()
    assert m.ingest([],timestamp=1700000000) == []
    def failures(start, count, ip):
        return [mk(f'login failure for user guest from {ip} via ssh',ident=f'*{start+i}',stamp=f'13:00:{start+i:02d}') for i in range(count)]
    f1=failures(1,2,'8.8.8.8')
    assert m.ingest(f1,timestamp=1700000030, login_failures=3) == []
    f2=f1+failures(3,1,'8.8.8.8')
    incidents=m.ingest(f2,timestamp=1700000060,login_failures=3)
    assert len(incidents)==1 and incidents[0]['count']==3
    assert m.ingest(f2,timestamp=1700000100)==[]
    more=f2+failures(4,3,'8.8.8.8')
    assert m.ingest(more,timestamp=1700000120)==[]  # 30 minute cooldown
    # Reconnected after 10min -> baseline, suppress catch-up flood.
    assert m.ingest(more+failures(7,3,'8.8.8.8'),timestamp=1700002000)==[]


def test_successful_public_admin_login_immediate_alert_and_no_dup():
    m=monitor.RouterLogMonitor()
    m.ingest([],timestamp=1700000000)
    row=mk('user admin logged in from 9.9.9.9 via winbox','system,info,account')
    assert len(m.ingest([row],timestamp=1700000030))==1
    assert m.ingest([row],timestamp=1700000050)==[]


def test_firewall_threshold_and_view_filters():
    m=monitor.RouterLogMonitor();m.ingest([],timestamp=1700000000)
    rows=[mk(f'NWMIKMI-WAN input: in:pppoe-out1, proto TCP 8.8.8.8:{40000+i}->1.1.1.1:8291',
             topics='firewall,info',ident=f'*{i}',stamp=f'13:00:{i:02d}') for i in range(10)]
    incidents=m.ingest(rows,timestamp=1700000060)
    assert len(incidents)==1 and incidents[0]['category']=='wan_management_probe'
    records,count=m.rows(category='security',search='8.8.8.8',limit=5)
    assert count==10 and len(records)==5 and 'NWMIKMI-WAN' in records[0]['message']
    assert m.rows(category='warning')[1]==0
    assert all('message' not in v for v in m.dump().values() if isinstance(v, dict))
