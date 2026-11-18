"""Personal Zalo Bot messaging unit tests; no actual Home Assistant or Zalo calls."""
from __future__ import annotations
import asyncio
import importlib
import sys
import types
from unittest.mock import AsyncMock

homeassistant = types.ModuleType('homeassistant'); homeassistant.__path__ = []
core = types.ModuleType('homeassistant.core'); core.HomeAssistant = object
util = types.ModuleType('homeassistant.util'); util.__path__ = []
dt = types.ModuleType('homeassistant.util.dt')
from datetime import datetime
dt.now = lambda: datetime(2026,11,18,13,30,0)
for name, module in [('homeassistant',homeassistant),('homeassistant.core',core),('homeassistant.util',util),('homeassistant.util.dt',dt)]:
    sys.modules.setdefault(name,module)

zalo=importlib.import_module('custom_components.netwatcher_mikmi.zalo')
const=importlib.import_module('custom_components.netwatcher_mikmi.const')

def settings():
    return {
        const.CONF_ZALO_BOT_ENABLED: True,
        const.CONF_ZALO_BOT_ACCOUNT: '+84123456789',
        const.CONF_ZALO_BOT_USERS: '2036121378794772276,5841349563795164131',
        const.CONF_ZALO_BOT_GROUPS: '9876543210123456789',
        const.CONF_ZALO_NOTIFY_DYNAMIC: True,
        const.CONF_ZALO_NOTIFY_ONLINE: False,
        const.CONF_ZALO_NOTIFY_OFFLINE: False,
        const.CONF_ZALO_INCLUDE_MAC: True,
    }

class Services:
    def __init__(self, present=True):
        self.present = present
        self.async_call = AsyncMock(return_value={'success': True})
    def has_service(self, domain, name):
        assert (domain,name)==('zalo_bot','send_message')
        return self.present

class Hass:
    def __init__(self,present=True): self.services=Services(present)

def test_format_all_types_sanitizes_comment_and_hides_missing_ap():
    rec={'mac':'AA:BB:CC:DD:EE:01','ip':'192.168.88.105','comment':'Phone\n\nFAKE URGENT',
         'connection':'wifi','dhcp_dynamic':True,'wifi_band':'5GHz'}
    msg=zalo.format_alert('new_dynamic',rec,'18/11/2026 13:30')
    assert '🚨' in msg and 'D - Dynamic' in msg
    assert 'Phone FAKE URGENT' in msg and 'Phone\n\nFAKE' not in msg
    assert 'Chưa xác định' in msg and 'AA:BB:CC:DD:EE:01' in msg
    assert 'AA:BB:CC:DD:EE:01' not in zalo.format_alert('new_dynamic',rec,'now',False)
    assert '🟢' in zalo.format_alert('connected',rec,'now')
    assert '🔴' in zalo.format_alert('disconnected',rec,'now')

def test_sends_to_users_and_groups_as_strings_no_oa_token():
    async def main():
        hass=Hass()
        sender=zalo.ZaloNotifier(hass,settings())
        assert sender.wants('new_dynamic') and not sender.wants('connected')
        out=await sender.send_event('new_dynamic',{'mac':'AA:BB:CC:DD:EE:01'})
        assert out=={'submitted':3,'failed':0,'rate_limited':0}
        calls=hass.services.async_call.call_args_list
        assert len(calls)==3
        assert [c.args[2]['type'] for c in calls]==['0','0','1']
        assert [c.args[2]['thread_id'] for c in calls]==[
            'zalo:2036121378794772276', 'zalo:5841349563795164131','zalo:9876543210123456789']
        for c in calls:
            assert c.args[:2]==('zalo_bot','send_message')
            assert c.kwargs=={'blocking':True,'return_response':True}
            assert c.args[2]['account_selection']=='+84123456789'
            assert 'access_token' not in c.args[2]
        assert (await sender.send_event('connected',{}))['submitted']==0
    asyncio.run(main())

def test_no_legacy_oa_migration_or_send_without_new_opt_in():
    async def main():
        cfg={'zalo_enabled':True,'zalo_user_ids':'123456789','zalo_access_token':'secret',
             const.CONF_ZALO_NOTIFY_DYNAMIC:True}
        sender=zalo.ZaloNotifier(Hass(),cfg)
        assert not sender.enabled
        assert (await sender.send_event('new_dynamic',{}))['submitted']==0
    asyncio.run(main())

def test_test_cooldown_rate_limit_and_missing_service():
    async def main():
        sender=zalo.ZaloNotifier(Hass(),settings())
        assert (await sender.send_test())['submitted']==3
        assert (await sender.send_test())['cooldown'] is True
        sender._last_test=0
        sender._used.extend([1e50]*60)
        out=await sender.send_test()
        assert out['rate_limited']==3
        absent=zalo.ZaloNotifier(Hass(False),settings())
        out=await absent.send_event('new_dynamic',{})
        assert out['service_missing'] is True and out['failed']==3
    asyncio.run(main())

def test_service_errors_do_not_leak_identifiers():
    async def main():
        hass=Hass()
        hass.services.async_call=AsyncMock(side_effect=RuntimeError('private uid, account and message'))
        sender=zalo.ZaloNotifier(hass,settings())
        out=await sender.send_event('new_dynamic',{})
        assert out['failed']==3 and out['submitted']==0
    asyncio.run(main())


def test_wan_alert_uses_existing_zalo_bot_action_without_oa():
    async def main():
        hass=Hass()
        sender=zalo.ZaloNotifier(hass,settings())
        res=await sender.send_security_alert({'category':'failed_admin_login','source_ip':'8.8.8.8',
                         'count':3,'time':'13:21:01','topics':'system,error,critical'})
        assert res['submitted']==3
        payload=hass.services.async_call.call_args.args[2]
        assert payload['thread_id'].startswith('zalo:')
        assert 'CẢNH BÁO WAN' in payload['message']
        assert '8.8.8.8' in payload['message']
        assert 'access_token' not in payload
    asyncio.run(main())
