/* Netwatcher MikMi Lovelace Card v0.3.0-beta.1 (no dependencies, no credentials).
 * All device-provided strings are inserted with textContent, never innerHTML.
 * Backend WebSocket checks administrator privileges on every request.
 */
const CARD_TAG = 'netwatcher-mikmi-card';
const STORAGE_STYLES = `
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
  static getStubConfig() { return {type: `custom:${CARD_TAG}`, title: 'Netwatcher MikMi', page_size: 25, show_ap: true, show_dhcp: true, show_logs: true}; }
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
    this._view = 'devices';
    this._tabs = elt('div', this._card, null, 'tabs');
    const devTab = elt('button', this._tabs, '📱 Thiết bị');
    devTab.classList.add('active');
    const logTab = elt('button', this._tabs, '📋 MikroTik Logs');
    if (this._config.show_logs === false) logTab.hidden = true;
    const toggle = (view) => {
      this._view = view;
      this._deviceView.hidden = view !== 'devices';
      this._logView.hidden = view !== 'logs';
      devTab.classList.toggle('active', view === 'devices');
      logTab.classList.toggle('active', view === 'logs');
      this._offset = 0; this._refresh(true);
    };
    devTab.addEventListener('click', () => toggle('devices'));
    logTab.addEventListener('click', () => toggle('logs'));
    this._deviceView = elt('div', this._card);
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
    this._logView.hidden = true;
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
    if (!force && this._lastFetch && Date.now()-this._lastFetch < 20000) return;
    this._busy=true; this._lastFetch=Date.now();
    try {
      if (this._view === 'logs') {
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
      const out=this._view==='logs'?this._logMessage:this._message;
      out.className='error';
      out.textContent='Cannot read Netwatcher data. Administrator permission and active integration are required.';
    } finally {this._busy=false;}
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
      ['show_search','Show search','checkbox'],['show_ap','Show AP / port','checkbox'],['show_dhcp','Show DHCP','checkbox'],['show_logs','Show MikroTik log viewer (admins only)','checkbox'],
    ];
    fields.forEach(([key,label,type])=>{
      const holder=elt('label',root,label),input=elt('input',holder);input.type=type;
      if(type==='checkbox')input.checked=this._config[key]!==false;
      else input.value=this._config[key]??'';
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
if(!window.customCards.some(c=>c.type===CARD_TAG))window.customCards.push({type:CARD_TAG,name:'Netwatcher MikMi',description:'LAN/Wi-Fi inventory, RouterOS log viewer, WAN access alerts and Zalo Bot actions',preview:false,configurable:true});
