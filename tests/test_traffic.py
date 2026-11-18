"""Counter deltas must respect measured monotonic elapsed time."""
import importlib
import sys
import types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ns=types.ModuleType('custom_components');ns.__path__=[str(ROOT/'custom_components')]
sys.modules.setdefault('custom_components',ns)
pkg=types.ModuleType('custom_components.netwatcher_mikmi');pkg.__path__=[str(ROOT/'custom_components/netwatcher_mikmi')]
sys.modules.setdefault('custom_components.netwatcher_mikmi',pkg)
impl=importlib.import_module('custom_components.netwatcher_mikmi.traffic')
InterfaceRateTracker=impl.InterfaceRateTracker
choose_wan=impl.choose_wan


def test_bitrate_and_counter_reset():
    tracker = InterfaceRateTracker()
    make=lambda rx,tx: [{'name':'pppoe-out1','type':'pppoe-out','rx-byte':str(rx),'tx-byte':str(tx),'running':'true'}]
    assert tracker.ingest(make(1000,1000),now=1000)['pppoe-out1']['rx_bps'] is None
    snap=tracker.ingest(make(2000,1500),now=1010)['pppoe-out1']
    assert snap['rx_bps']==800 and snap['tx_bps']==400
    snap=tracker.ingest(make(10,12),now=1020)['pppoe-out1']
    assert snap['rx_bps'] is None and snap['tx_bps'] is None
    snap=tracker.ingest(make(15,20),now=1025)['pppoe-out1']
    assert snap['rx_bps']==8 and snap['tx_bps']==12.8


def test_wan_select_never_guesses_if_explicit_missing():
    rows=[{'name':'ether1','type':'ether'}, {'name':'pppoe-fpt','type':'pppoe-out'}]
    assert choose_wan(rows)=='pppoe-fpt'
    assert choose_wan(rows,'pppoe-fpt')=='pppoe-fpt'
    assert choose_wan(rows,'missing') is None
    assert choose_wan([{'name':'ether1','type':'ether'}]) is None
