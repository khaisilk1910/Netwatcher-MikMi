/* Netwatcher MikMi Lovelace Card v0.4.0-beta.1 (no dependencies, no credentials).
 * All device-provided strings are inserted with textContent, never innerHTML.
 * Backend WebSocket checks administrator privileges on every request.
 */
const CARD_TAG = 'netwatcher-mikmi-card';
const STORAGE_STYLES = `
/* Dashboard: compact, responsive, uses native HA themes and state accents. */
:host{--nwm-teal:#06d6a0;--nwm-amber:#ffb45c;--nwm-red:#fb7185}
ha-card{border-radius:22px!important;overflow:hidden;box-shadow:0 14px 48px rgba(4,20,37,.14);border:1px solid var(--divider-color)}
.header{background:linear-gradient(120deg,#102235,#132f46 58%,#0a4d4c);color:#f4fbff;position:relative;margin:-16px -16px 12px;padding:22px 22px 18px;overflow:hidden}
.header:after{content:'';position:absolute;pointer-events:none;right:-30px;top:-65px;width:235px;height:235px;border-radius:100%;background:radial-gradient(circle,rgba(14,223,192,.21),transparent 70%)}
.header .title{font-size:22px;letter-spacing:.3px;font-weight:750;z-index:1}
.header .hint{color:#a2dbd1;z-index:1;display:inline-flex;gap:6px;align-items:center}
.tabs{margin:14px 0 20px;overflow-x:auto;padding-bottom:5px;scrollbar-width:thin}
.tabs button{border-radius:13px;padding:11px 14px;white-space:nowrap;transition:background .2s,border-color .2s}
.tabs button.active{background:color-mix(in srgb,var(--primary-color,#09b9ab) 14%,var(--card-background-color));border-color:var(--primary-color,#09b9ab);font-weight:750}
.hw-cover{padding:4px 0 16px}
.hw-title{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}
.hw-model{font-size:21px;font-weight:800;letter-spacing:-.3px}
.hw-sub{color:var(--secondary-text-color);font-size:12px;line-height:1.8}
.hw-badge{border-radius:999px;padding:7px 11px;font-size:11px;font-weight:800;letter-spacing:.5px;background:rgba(16,185,129,.10);color:#0e9f73;border:1px solid rgba(16,185,129,.26)}
.hw-badge.warn{background:rgba(245,158,11,.12);color:#d18b1b;border-color:rgba(245,158,11,.35)}
.hw-badge.danger{background:rgba(244,63,94,.10);color:#ef4064;border-color:rgba(244,63,94,.30)}
.hw-badge.muted{background:var(--secondary-background-color);color:var(--secondary-text-color);border-color:var(--divider-color)}
.gauges{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}
.gauge-card{background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:18px;min-width:0;padding:15px 10px;display:grid;justify-items:center;gap:8px}
.gauge-title{font-size:12px;color:var(--secondary-text-color);font-weight:650;letter-spacing:.5px}
.gauge-dial{width:min(130px,100%);aspect-ratio:1;border-radius:50%;display:grid;place-items:center;position:relative;filter:drop-shadow(0 4px 12px rgba(0,0,0,.06));transition:background .5s}
.gauge-hole{width:78%;height:78%;border-radius:50%;background:var(--secondary-background-color);display:flex;align-items:center;justify-content:center;flex-direction:column}
.gauge-value{font-size:clamp(20px,4.5vw,30px);font-weight:850;letter-spacing:-1px;font-variant-numeric:tabular-nums}
.gauge-unit{font-size:11px;color:var(--secondary-text-color)}
.gauge-state{font-size:11px;letter-spacing:.4px;font-weight:800}
.gauge-state.ok{color:#0baa80}.gauge-state.warn{color:#df971b}.gauge-state.danger{color:#f43f5e}.gauge-state.muted{color:var(--secondary-text-color)}
.hw-extras{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:9px;margin:10px 0 14px}
.hw-tile{border:1px solid var(--divider-color);background:var(--card-background-color);border-radius:14px;padding:12px;min-width:0;overflow:hidden}
.hw-tile .icon{font-size:17px}.hw-tile .key{font-size:11px;color:var(--secondary-text-color);margin:7px 0 5px}.hw-tile .value{font-size:16px;font-weight:750;overflow-wrap:anywhere}
.sensor-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:8px 0 12px}
.sensor-row{display:flex;justify-content:space-between;gap:9px;align-items:center;padding:10px 12px;border-radius:11px;background:var(--secondary-background-color);font-size:12px}
.sensor-row .sensor-name{color:var(--secondary-text-color);overflow-wrap:anywhere}
.sensor-row .sensor-reading{font-variant-numeric:tabular-nums;font-weight:750;text-align:right}
.hw-foot{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;font-size:11px;color:var(--secondary-text-color)}
.netwatch-row{border:1px solid var(--divider-color);border-radius:14px;padding:14px;margin:8px 0;display:flex;align-items:center;justify-content:space-between;gap:12px}
.netwatch-row .host{font-weight:750;overflow-wrap:anywhere}.netwatch-row .sub{font-size:12px;color:var(--secondary-text-color);margin-top:5px}
@media(max-width:600px){.header{margin:-10px -10px 10px;padding:17px}.gauges{gap:6px}.gauge-card{padding:13px 4px}.gauge-value{font-size:20px}.gauge-title{font-size:11px}.hw-extras{grid-template-columns:repeat(2,minmax(0,1fr))}}

[hidden]{display:none!important}
.tabs{display:flex;gap:8px;margin:8px 0 14px}.tabs button{border:1px solid var(--divider-color);border-radius:9px;background:var(--card-background-color);color:var(--primary-text-color);padding:8px 12px;cursor:pointer}.tabs button.active{background:var(--secondary-background-color);font-weight:700}

:host{display:block;color:var(--primary-text-color)}
ha-card{padding:16px;display:block}
.header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.title{font-size:20px;font-weight:650}.hint{color:var(--secondary-text-color);font-size:12px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:8px;margin:14px 0}
.stat{background:var(--secondary-background-color);border-radius:10px;padding:12px}
.stat strong{display:block;font-size:24px}.stat span{font-size:12px;color:var(--secondary-text-color)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.toolbar input,.toolbar select,
.toolbar button,.footer button{color:var(--primary-text-color);background:var(--card-background-color);
border:1px solid var(--divider-color);border-radius:8px;padding:8px;min-height:36px}
.toolbar input{flex:1;min-width:145px}.toolbar button,.footer button{cursor:pointer}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--divider-color);white-space:nowrap}
th{font-weight:600;color:var(--secondary-text-color)}.name{font-weight:600;max-width:200px;overflow:hidden;text-overflow:ellipsis}
.pill{border:1px solid var(--divider-color);border-radius:20px;padding:3px 8px;display:inline-block}
.pill.online{color:var(--success-color,#38a169)}.pill.dynamic{color:var(--error-color,#e53e3e)}
.footer{display:flex;align-items:center;justify-content:space-between;margin-top:12px;gap:8px}
.small{font-size:12px;color:var(--secondary-text-color)}.error{color:var(--error-color,#e53e3e);padding:12px 0}
.approve{border:1px solid var(--divider-color);background:transparent;color:var(--primary-text-color);
border-radius:7px;padding:5px 8px;cursor:pointer;white-space:nowrap}
@media(max-width:600px){ha-card{padding:10px}th,td{padding:8px 5px}.stat strong{font-size:20px}}
`;
function elt(tag, parent, text, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (parent) parent.appendChild(node);
  return node;
}

class NetwatcherMikMiCard extends HTMLElement {
  static getStubConfig() { return {type: `custom:${CARD_TAG}`, title: 'Netwatcher MikMi', page_size: 25, show_ap: true, show_dhcp: true, show_logs: true, show_hardware: true, show_netwatch: true, show_traffic: true, show_sensors: true, default_view:'hardware'}; }
  static getConfigElement() { return document.createElement('netwatcher-mikmi-card-editor'); }
  getCardSize() { return 5; }
  setConfig(config) {
    this._config = {...NetwatcherMikMiCard.getStubConfig(), ...config};
    if (!this.shadowRoot) this.attachShadow({mode: 'open'});
    this._renderBase();
    if (this._hass) this._refresh(true);
  }
  set hass(hass) {
    this._hass = hass;
    if (this.isConnected && this._config) this._refresh(false);
  }
  connectedCallback() { if (this._hass && this._config) this._refresh(true); }
  disconnectedCallback() { if (this._timer) clearTimeout(this._timer); }
  _renderBase() {
    const root = this.shadowRoot;
    root.replaceChildren();
    elt('style', root, STORAGE_STYLES);
    this._card = elt('ha-card', root);
    const header = elt('div', this._card, null, 'header');
    elt('div', header, this._config.title || 'Netwatcher MikMi', 'title');
    this._health = elt('div', header, 'Connecting...', 'hint');
    this._stats = elt('div', this._card, null, 'stats');
    const views = ['hardware','devices','netwatch','logs'];
    this._view = views.includes(this._config.default_view) ? this._config.default_view : 'hardware';
    if (this._view === 'hardware' && this._config.show_hardware === false) this._view = 'devices';
    if (this._view === 'netwatch' && this._config.show_netwatch === false) this._view = 'devices';
    if (this._view === 'logs' && this._config.show_logs === false) this._view = 'devices';
    this._tabs = elt('div', this._card, null, 'tabs');
    this._stats.hidden=this._view!=='devices';
    const tabButtons = {};
    const tabSpecs = [
      ['hardware','🛡️ Router Health',this._config.show_hardware!==false],
      ['devices','📱 Thiết bị',true],
      ['netwatch','📡 Netwatch',this._config.show_netwatch!==false],
      ['logs','📋 Nhật ký WAN',this._config.show_logs!==false],
    ];
    for (const [key,label,visible] of tabSpecs) {
      const btn = elt('button',this._tabs,label);
      if (!visible) btn.hidden=true;
      btn.classList.toggle('active',key===this._view);
      tabButtons[key]=btn;
      btn.addEventListener('click',()=>{
        this._view=key;
        this._stats.hidden=key!=='devices';
        this._hardwareView.hidden = key!=='hardware';
        this._deviceView.hidden = key!=='devices';
        this._netwatchView.hidden = key!=='netwatch';
        this._logView.hidden = key!=='logs';
        for (const [k,b] of Object.entries(tabButtons)) b.classList.toggle('active',k===key);
        this._offset=0;this._lastFetch=0;this._refresh(true);
      });
    }
    this._hardwareView=elt('div',this._card,null,'hw-cover');
    this._hardwareView.hidden=this._view!=='hardware';
    this._hwMessage=elt('div',this._hardwareView,'Đang lấy dữ liệu phần cứng…','small');
    this._hwContent=elt('div',this._hardwareView);
    this._netwatchView=elt('div',this._card);
    this._netwatchView.hidden=this._view!=='netwatch';
    this._nwMessage=elt('div',this._netwatchView,'Đang đọc Netwatch…','small');
    this._nwContent=elt('div',this._netwatchView);
    this._deviceView = elt('div', this._card);
    this._deviceView.hidden=this._view!=='devices';
    const toolbar = elt('div', this._deviceView, null, 'toolbar');
    this._filter = elt('select', toolbar);
    [['all','All'],['online','Online'],['offline','Offline'],['unknown','Unknown'],['dynamic','DHCP dynamic'],['unapproved','Unapproved']].forEach(([value,label]) => {
      const opt = elt('option', this._filter, label); opt.value = value;
    });
    this._filter.value = this._config.default_filter || 'all';
    this._filter.addEventListener('change', () => {this._offset = 0; this._refresh(true);});
    if (this._config.show_search !== false) {
      this._search = elt('input', toolbar);
      this._search.placeholder = 'Search MAC / IP / comment / AP';
      this._search.setAttribute('aria-label','Search devices');
      this._search.addEventListener('input', () => {
        if (this._timer) clearTimeout(this._timer);
        this._timer = setTimeout(() => {this._offset=0;this._refresh(true);},350);
      });
    }
    const testZalo = elt('button', toolbar, 'Test Zalo Bot');
    testZalo.title = 'Send a test message via personal-account Zalo Bot to configured recipients (unofficial API).';
    testZalo.addEventListener('click', async () => {
      if (!this._hass || !window.confirm('Send a test message to every configured Zalo recipient?')) return;
      testZalo.disabled = true;
      try {
        if (!this._entryId) await this._refresh(true);
        const result = await this._hass.callWS({type:'netwatcher_mikmi/test_zalo',entry_id:this._entryId});
        this._message.textContent = `Zalo Bot test: ${result.submitted || 0} accepted by service, ${result.failed || 0} failed, ${result.rate_limited || 0} rate-limited.`;
      } catch (_error) { this._message.textContent = 'Zalo test failed. Check configuration and safe HA logs.'; }
      finally { testZalo.disabled = false; }
    });
    const refresh = elt('button', toolbar, 'Refresh');
    refresh.addEventListener('click', () => this._refresh(true));
    this._message = elt('div', this._deviceView, '', 'small');
    const wrap = elt('div', this._deviceView, null, 'table-wrap');
    this._table = elt('table', wrap);
    const footer = elt('div', this._deviceView, null, 'footer');
    this._prev = elt('button', footer, 'Previous');
    this._count = elt('span', footer, '', 'small');
    this._next = elt('button', footer, 'Next');
    this._prev.addEventListener('click', () => {this._offset=Math.max(0,(this._offset||0)-this._pageSize());this._refresh(true);});
    this._next.addEventListener('click', () => {this._offset=(this._offset||0)+this._pageSize();this._refresh(true);});
    this._logView = elt('div', this._card);
    this._logView.hidden = this._view!=='logs';
    const logsToolbar = elt('div', this._logView, null, 'toolbar');
    this._logFilter = elt('select', logsToolbar);
    [['all','Tất cả'],['security','Bảo mật'],['warning','Warning / Error']].forEach(([value,label]) => {
      const option = elt('option', this._logFilter, label); option.value = value;
    });
    this._logFilter.addEventListener('change', () => {this._offset=0;this._refresh(true);});
    this._logSearch = elt('input', logsToolbar);
    this._logSearch.placeholder = 'Tìm log theo topic hoặc nội dung';
    this._logSearch.addEventListener('change', () => {this._offset=0;this._refresh(true);});
    const logRefresh = elt('button', logsToolbar, 'Làm mới');
    logRefresh.addEventListener('click', () => this._refresh(true));
    this._logMessage = elt('div', this._logView, '', 'small');
    const logWrap = elt('div', this._logView, null, 'table-wrap');
    this._logTable = elt('table', logWrap);
    const logFooter = elt('div', this._logView, null, 'footer');
    this._logPrev = elt('button', logFooter, 'Trước');
    this._logCount = elt('span', logFooter, '', 'small');
    this._logNext = elt('button', logFooter, 'Sau');
    this._logPrev.addEventListener('click', () => {this._offset=Math.max(0,(this._offset||0)-50);this._refresh(true);});
    this._logNext.addEventListener('click', () => {this._offset=(this._offset||0)+50;this._refresh(true);});
    this._offset=0;
  }
  _pageSize() { return Math.max(5,Math.min(100,Number(this._config.page_size)||25)); }
  async _refresh(force) {
    if (!this._hass || !this._config || this._busy) return;
    if (!force && this._lastFetch && Date.now()-this._lastFetch < (this._view==='hardware'?12000:20000)) return;
    this._busy=true; this._lastFetch=Date.now();
    try {
      if (this._view === 'hardware') {
        const data=await this._hass.callWS({type:'netwatcher_mikmi/router_hardware',entry_id:this._config.entry_id||''});
        this._entryId=data.entry_id;
        this._showHardware(data);
      } else if (this._view === 'netwatch') {
        const data=await this._hass.callWS({type:'netwatcher_mikmi/router_netwatch',entry_id:this._config.entry_id||''});
        this._entryId=data.entry_id;
        this._showNetwatch(data);
      } else if (this._view === 'logs') {
        const data = await this._hass.callWS({
          type:'netwatcher_mikmi/router_logs',entry_id:this._config.entry_id||'',
          category:this._logFilter.value,search:this._logSearch.value,
          offset:this._offset||0,limit:50,
        });
        this._entryId=data.entry_id;
        this._showLogs(data);
      } else {
        const data = await this._hass.callWS({
          type: 'netwatcher_mikmi/inventory',entry_id:this._config.entry_id||'',
          status:this._filter?.value||'all',search:this._search?.value||'',
          offset:this._offset||0,limit:this._pageSize(),
        });
        this._entryId = data.entry_id;
        this._show(data);
      }
    } catch (error) {
      const out=this._view==='hardware'?this._hwMessage:
        this._view==='netwatch'?this._nwMessage:this._view==='logs'?this._logMessage:this._message;
      out.className='error';
      out.textContent='Cannot read Netwatcher data. Administrator permission and active integration are required.';
    } finally {this._busy=false;}
  }
  _showHardware(data) {
    const r=data.readings||{},b=data.board||{},a=data.alerts||{};
    this._hwContent.replaceChildren();
    const available=!!data.available;
    this._health.textContent=available?'● RouterOS API-SSL · ONLINE':'● RouterOS · UNAVAILABLE';
    this._hwMessage.className='small';
    this._hwMessage.textContent=available ? '' :
      `Không có dữ liệu mới từ RouterOS (${data.source_error || 'chưa cập nhật'}). Không hiển thị số liệu cũ như số liệu hiện tại.`;
    const top=elt('div',this._hwContent,null,'hw-title');
    const left=elt('div',top),model=elt('div',left,b.model || 'MikroTik Router','hw-model');
    elt('div',left,`RouterOS ${b.routeros_version || '—'} · ${b.architecture || '—'} · ${b.cpu_count||r.cpu_count||'—'} core(s)`,'hw-sub');
    const active=available&&Object.entries(a).some(([key,v])=>v&&r[key]!=null&&Number(r[key])>=Number(v.threshold));
    const warning=available&&Object.entries(a).some(([k,v])=>v?.enabled&&r[k]!=null&&r[k]>=v.threshold*.85);
    const badge=elt('span',top,!available?'● KHÔNG CÓ DỮ LIỆU':active?'● CẢNH BÁO QUÁ NGƯỠNG':warning?'● CẦN THEO DÕI':'● THIẾT BỊ ỔN ĐỊNH',
      `hw-badge ${!available?'muted':active?'danger':warning?'warn':''}`);
    badge.setAttribute('role','status');
    const gauges=elt('div',this._hwContent,null,'gauges');
    this._gauge(gauges,'CPU',available?r.cpu:null,100,a.cpu,'%');
    this._gauge(gauges,'RAM',available?r.ram:null,100,a.ram,'%');
    this._gauge(gauges,'NHIỆT ĐỘ',available?r.temperature:null,120,a.temperature,'°C');
    const extras=elt('div',this._hwContent,null,'hw-extras');
    const wan=data.wan_traffic||{};
    const bpsToMbps=(v)=>Number.isFinite(Number(v))&&v!==null&&v!==undefined ? (Number(v)/1000000).toFixed(2)+' Mb/s' : '—';
    const fmt=(x,unit='')=>(available&&x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x)))?`${x}${unit}`:'Không hỗ trợ';
    const uptime=available&&Number.isFinite(Number(r.uptime_seconds))?
      `${Math.floor(r.uptime_seconds/86400)}d ${Math.floor(r.uptime_seconds%86400/3600)}h ${Math.floor(r.uptime_seconds%3600/60)}m`:'—';
    const values=[
      ...(this._config.show_traffic===false ? [] : [
        ['⬇️','WAN Download',bpsToMbps(wan.rx_bps)],
        ['⬆️','WAN Upload',bpsToMbps(wan.tx_bps)],
      ]),
      ['💽','Lưu trữ',fmt(r.storage,'%')],
      ['⚡','Điện áp',fmt(r.voltage,' V')],
      ['🌀','Quạt',fmt(r.fan_rpm,' RPM')],
      ['🧠','RAM tổng',fmt(r.total_ram_mib,' MiB')],
      ['💻','Xung CPU',fmt(r.cpu_frequency_mhz,' MHz')],
      ['⏳','Uptime',uptime],
      ['🧩','CPU',b.cpu_name||'—'],
      ['🔩','Firmware',b.firmware||'—'],
    ];
    for(const [symbol,key,val] of values){
      const tile=elt('div',extras,null,'hw-tile');
      elt('div',tile,symbol,'icon');elt('div',tile,key,'key');elt('div',tile,val,'value');
    }
    if (this._config.show_sensors!==false && available && Object.keys(data.sensors||{}).length){
      elt('div',this._hwContent,'⚙️ Chi tiết cảm biến RouterOS','hw-model');
      const sensors=elt('div',this._hwContent,null,'sensor-list');
      for(const [name,record] of Object.entries(data.sensors).slice(0,64)){
        const line=elt('div',sensors,null,'sensor-row');
        elt('span',line,name,'sensor-name');
        const raw=record?.raw||'—';
        const unit=record?.unit||'';
        const value=record?.value===null||record?.value===undefined?raw:`${record.value}${unit?` ${unit}`:''}`;
        const reading=elt('span',line,value,'sensor-reading');
        if(['fail','not-present','error'].includes(String(raw).toLowerCase()))reading.style.color='var(--nwm-red)';
      }
    }
    const footer=elt('div',this._hwContent,null,'hw-foot');
    elt('span',footer,`● Đọc CPU/RAM ${data.poll_intervals?.resource||'—'}s · Cảm biến ${data.poll_intervals?.sensors||'—'}s · WAN ${wan.name||'chưa chọn'}`);
    const when= data.last_success?new Date(data.last_success*1000).toLocaleString('vi-VN'):'—';
    elt('span',footer,`Cập nhật cuối: ${when}`);
    elt('div',this._hwContent,'Các ngưỡng được thiết lập trong Settings → Devices & Services → Netwatcher MikMi → Configure. Cảm biến không hỗ trợ sẽ hiện “—”.','small');
  }
  _gauge(parent,title,value,max,alert,unit){
    const box=elt('div',parent,null,'gauge-card');
    elt('div',box,title,'gauge-title');
    const dial=elt('div',box,null,'gauge-dial');
    const valid=Number.isFinite(Number(value)) && value!==null && value!==undefined;
    const current=valid?Number(value):0;
    const threshold=Number.isFinite(Number(alert?.threshold))?Number(alert.threshold):(unit==='°C'?75:title==='RAM'?90:85);
    const high=valid&&current>=threshold;
    const near=valid&&current>=threshold*0.85;
    const state=!valid?'muted':high?'danger':near?'warn':'ok';
    const color=state==='danger'?'var(--nwm-red)':state==='warn'?'var(--nwm-amber)':state==='ok'?'var(--nwm-teal)':'var(--divider-color)';
    const deg=Math.max(0,Math.min(360,(current/max)*360));
    dial.style.background=`conic-gradient(${color} 0deg ${deg}deg,var(--divider-color) ${deg}deg 360deg)`;
    const hole=elt('div',dial,null,'gauge-hole');
    elt('div',hole,valid?String(Math.round(current*10)/10):'—','gauge-value');
    elt('div',hole,unit,'gauge-unit');
    elt('div',box,!valid?'KHÔNG HỖ TRỢ':high?'QUÁ NGƯỠNG':near?'CẦN THEO DÕI':'BÌNH THƯỜNG',`gauge-state ${state}`);
    elt('div',box,`Ngưỡng: ${alert?.threshold??threshold}${unit}`,'hw-sub');
  }
  _showNetwatch(data){
    this._nwContent.replaceChildren();
    this._nwMessage.className='small';
    this._nwMessage.textContent=!data.enabled?'Netwatch đang tắt trong Options. Không tự tạo probe.':
      !data.available?'Chưa đọc được dữ liệu Netwatch: kiểm tra RouterOS và quyền read.':
      `Đang đọc ${(data.probes||[]).length} phép thử RouterOS Netwatch có sẵn.`;
    for(const p of data.probes||[]){
      const row=elt('div',this._nwContent,null,'netwatch-row');
      const left=elt('div',row),label=elt('div',left,p.comment||p.name||p.host||'Netwatch','host');
      label.title=p.host||'';
      elt('div',left,`Đích: ${p.host||'—'} · RTT: ${p['rtt-avg']||'—'} · Loss: ${p['loss-percent']||'—'}`,'sub');
      const state=p.disabled==='true'?'disabled':p.status||'unknown';
      elt('span',row,state.toUpperCase(),`hw-badge ${state==='down'?'danger':state==='up'?'':'muted'}`);
    }
    if (!data.probes?.length)elt('div',this._nwContent,'Không có mục Netwatch hoặc chưa có dữ liệu.','small');
  }
  _showLogs(data) {
    this._logMessage.className='small';
    this._logMessage.textContent=!data.enabled ? 'Đọc log đang tắt trong Options.' :
       !data.baselined ? 'Đang chờ bản log đầu tiên (không gửi cảnh báo lịch sử).' :
       data.source_health?.ok ? 'Log MikroTik: OK. Chỉ quản trị viên HA được xem.' :
       `Log MikroTik hiện không khả dụng (${data.source_health?.error || 'unknown'}).`;
    this._logTable.replaceChildren();
    const head=elt('thead',this._logTable), tr=elt('tr',head);
    ['Thời gian RouterOS','Topics','Mức độ','Nội dung log'].forEach(x=>elt('th',tr,x));
    const body=elt('tbody',this._logTable);
    for(const item of data.logs || []) {
      const row=elt('tr',body);
      elt('td',row,item.time||'-');
      elt('td',row,item.topics||'-');
      elt('td',row,item.category==='normal'?'info':'⚠️ '+item.category);
      const cell=elt('td',row,item.message||'-');
      cell.style.whiteSpace='normal';cell.style.minWidth='280px';
    }
    if(!data.logs?.length){const row=elt('tr',body),cell=elt('td',row,'Chưa có log phù hợp.');cell.colSpan=4;}
    this._logPrev.disabled=this._offset<=0;
    this._logNext.disabled=this._offset+50>=data.count;
    this._logCount.textContent=`${data.count?this._offset+1:0}-${Math.min(this._offset+(data.logs||[]).length,data.count)} / ${data.count} log`;
  }
  _show(data) {
    this._message.className='small';
    this._message.textContent = data.baseline_complete ? '' : 'Waiting for initial MikroTik snapshot; alerts will be baselined.';
    const sources = data.source_health || {};
    this._health.textContent = `MikroTik: ${sources.mikrotik?.ok ? 'OK':'Unavailable'} | Xiaomi: ${sources.xiaomi?.ok ? 'OK':'Unavailable'}`;
    this._stats.replaceChildren();
    [['total','Total'],['online','Online'],['offline','Offline'],['unknown','Unknown'],['dynamic','DHCP dynamic'],['unapproved','Unapproved']].forEach(([key,label]) => {
      const box = elt('div',this._stats,null,'stat');
      elt('strong',box,data.statistics[key]||0);
      elt('span',box,label);
    });
    this._table.replaceChildren();
    const headers = ['Device','IP','State','Link',...(this._config.show_ap===false?[]:['AP / port']),...(this._config.show_dhcp===false?[]:['DHCP']),'Approved'];
    const head=elt('thead',this._table), tr=elt('tr',head);
    headers.forEach(h=>elt('th',tr,h));
    const body=elt('tbody',this._table);
    for (const d of data.devices) {
      const row=elt('tr',body);
      const name=elt('td',row,d.name||d.mac,'name'); name.title=d.mac;
      elt('td',row,d.ip||'-');
      elt('td',row,d.online||'unknown',`pill ${d.online||''}`);
      elt('td',row,d.connection==='wifi' ? `Wi-Fi ${d.wifi_band||''}` : (d.connection||'unknown'));
      if (this._config.show_ap!==false) elt('td',row,d.ap_name||d.port||'-');
      if (this._config.show_dhcp!==false) elt('td',row,d.dhcp_dynamic===true?'Dynamic':d.dhcp_dynamic===false?'Static':'Unmanaged',d.dhcp_dynamic?'pill dynamic':'');
      const td=elt('td',row);
      const approve=elt('button',td,d.approved?'Approved':'Approve','approve');
      approve.title = d.approved ? 'Unapprove device locally' : 'Mark device as approved locally (does not change MikroTik)';
      approve.addEventListener('click', async () => {
        if (!window.confirm(`${d.approved ? 'Remove approval from' : 'Approve'} ${d.name || d.mac}?`)) return;
        approve.disabled=true;
        try {
          await this._hass.callWS({type:'netwatcher_mikmi/approve',entry_id:this._entryId,mac:d.mac,approved:!d.approved});
          this._refresh(true);
        } catch(_error) { this._message.textContent='Cannot change local approval.'; }
        finally {approve.disabled=false;}
      });
    }
    this._prev.disabled=this._offset<=0;
    this._next.disabled=(this._offset+this._pageSize())>=data.count;
    const start=data.count?this._offset+1:0;
    this._count.textContent=`${start}-${Math.min(this._offset+data.devices.length,data.count)} of ${data.count}`;
  }
}

class NetwatcherMikMiCardEditor extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});}
  setConfig(config){this._config={...config};this._render();}
  set hass(hass){this._hass=hass;}
  _render(){
    const root=this.shadowRoot;root.replaceChildren();
    elt('style',root,`:host{display:grid;gap:12px;padding:12px}label{display:grid;gap:5px;font-size:14px}
input,select{padding:8px;border:1px solid var(--divider-color);border-radius:7px;background:var(--card-background-color);color:var(--primary-text-color)}`);
    const fields=[
      ['title','Card title','text'],['entry_id','Config entry ID (optional)','text'],
      ['page_size','Page size (5-100)','number'],
      ['default_view','Default tab','select'],
      ['show_hardware','Show Router Health','checkbox'],['show_netwatch','Show Netwatch','checkbox'],['show_traffic','Show WAN RX/TX throughput','checkbox'],['show_sensors','Show detailed RouterOS health sensors','checkbox'],
      ['show_search','Show search','checkbox'],['show_ap','Show AP / port','checkbox'],['show_dhcp','Show DHCP','checkbox'],['show_logs','Show MikroTik log viewer (admins only)','checkbox'],
    ];
    fields.forEach(([key,label,type])=>{
      const holder=elt('label',root,label),input=elt('input',holder);input.type=type;
      if(type==='checkbox')input.checked=this._config[key]!==false;
      else if(type==='select'){
        ['hardware','devices','netwatch','logs'].forEach(value=>{
          const option=elt('option',input,value==='hardware'?'Router Health':value==='devices'?'Thiết bị':value==='netwatch'?'Netwatch':'MikroTik Logs');
          option.value=value;
        });
        input.value=this._config[key]||'hardware';
      } else input.value=this._config[key]??'';
      input.addEventListener('change',()=>{
        const value=type==='checkbox'?input.checked:type==='number'?Math.max(5,Math.min(100,Number(input.value)||25)):input.value;
        this._config={...this._config,[key]:value};
        this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this._config},bubbles:true,composed:true}));
      });
    });
  }
}
if(!customElements.get(CARD_TAG))customElements.define(CARD_TAG,NetwatcherMikMiCard);
if(!customElements.get('netwatcher-mikmi-card-editor'))customElements.define('netwatcher-mikmi-card-editor',NetwatcherMikMiCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type===CARD_TAG))window.customCards.push({type:CARD_TAG,name:'Netwatcher MikMi',description:'MikroTik hardware gauges, DHCP/Wi-Fi inventory, Netwatch, WAN log and Zalo Bot alerts',preview:false,configurable:true});
