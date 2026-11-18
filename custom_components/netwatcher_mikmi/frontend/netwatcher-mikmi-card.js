/* Netwatcher MikMi Lovelace Card v0.4.1-beta.7 (no dependencies, no credentials).
 * All device-provided strings are inserted with textContent, never innerHTML.
 * Backend WebSocket checks administrator privileges on every request.
 */
const CARD_TAG = 'netwatcher-mikmi-card';
const DEVICE_COLUMNS = Object.freeze([
  ['device','Device'], ['ip','IP'], ['state','State'], ['link','Link'],
  ['port','AP / port'], ['dhcp','DHCP'], ['approved','Approved'],
]);

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
th{font-weight:600;color:var(--secondary-text-color)}
.sort-button{display:inline-flex;align-items:center;gap:7px;padding:5px 2px;border:0;background:transparent;color:inherit;font:inherit;font-weight:inherit;cursor:pointer;white-space:nowrap}
.sort-button:hover,.sort-button:focus-visible,th[aria-sort=ascending] .sort-button,th[aria-sort=descending] .sort-button{color:var(--primary-color,#38bdf8)}
.sort-button:focus-visible{outline:2px solid var(--primary-color,#38bdf8);outline-offset:2px;border-radius:4px}
.sort-arrow{display:inline-block;min-width:13px;text-align:center;opacity:.55;font-size:14px}
th[aria-sort=ascending] .sort-arrow,th[aria-sort=descending] .sort-arrow{opacity:1}
.name{font-weight:600;max-width:200px;overflow:hidden;text-overflow:ellipsis}
.pill{border:1px solid var(--divider-color);border-radius:20px;padding:3px 8px;display:inline-block}
.pill.online{color:var(--success-color,#38a169)}.pill.dynamic{color:var(--error-color,#e53e3e)}
.footer{display:flex;align-items:center;justify-content:space-between;margin-top:12px;gap:8px}
.small{font-size:12px;color:var(--secondary-text-color)}.error{color:var(--error-color,#e53e3e);padding:12px 0}
.approve{border:1px solid var(--divider-color);background:transparent;color:var(--primary-text-color);
border-radius:7px;padding:5px 8px;cursor:pointer;white-space:nowrap}
@media(max-width:600px){ha-card{padding:10px}th,td{padding:8px 5px}.stat strong{font-size:20px}}

/* Netwatcher MikMi v0.4.1 icon system. SVG assets are local and DOM-only. */
:host{--nwm-cyan:#22d3ee;--nwm-violet:#a78bfa;--nwm-good:#10b981;--nwm-bad:#fb7185}
.header{min-height:78px;background:linear-gradient(118deg,#081b33 0%,#112a49 49%,#263067 100%);padding:18px 23px;margin:-16px -16px 15px;border-bottom:1px solid rgba(123,192,255,.25)}
.brand-head,.model-line,.device-label,.connection-pill,.stat-caption,.gauge-top,.log-level{display:flex;align-items:center;gap:9px;min-width:0}
.brand-head{gap:14px;position:relative;z-index:1}.brand-avatar{width:53px;height:53px;object-fit:contain;filter:drop-shadow(0 0 12px rgba(34,211,238,.20))}
.brand-title-group{min-width:0}.brand-title-group .title{font-size:20px;line-height:1.25;color:#edf8ff;font-weight:850;letter-spacing:.1px}
.brand-subtitle{font-size:9px;font-weight:700;letter-spacing:1.25px;color:#9bb8dd;margin-top:5px}
.header .hint{color:#b3c9e4;font-size:11px;font-weight:600}
.mi-icon{width:19px;height:19px;flex:none;display:inline-block;vertical-align:middle;stroke:currentColor}
.icon-chip{display:inline-grid;place-items:center;width:34px;height:34px;border-radius:11px;color:#25dcf5;background:linear-gradient(145deg,rgba(27,202,225,.21),rgba(61,99,229,.16));border:1px solid rgba(47,210,242,.20);box-shadow:inset 0 1px 0 rgba(255,255,255,.10)}
.icon-chip .mi-icon{width:19px;height:19px}.tone-green{color:#10b981;background:rgba(16,185,129,.12);border-color:rgba(16,185,129,.20)}
.tone-blue{color:#2ea8ef;background:rgba(59,130,246,.13);border-color:rgba(59,130,246,.19)}
.tone-cyan{color:#0ac4dd;background:rgba(34,211,238,.13)}
.tone-red{color:#f43f5e;background:rgba(244,63,94,.13);border-color:rgba(244,63,94,.22)}
.tone-amber{color:#f59e0b;background:rgba(245,158,11,.13);border-color:rgba(245,158,11,.22)}
.tone-purple{color:#a78bfa;background:rgba(139,92,246,.14);border-color:rgba(139,92,246,.20)}
.tone-muted{color:#94a3b8;background:rgba(148,163,184,.10);border-color:rgba(148,163,184,.18)}
.tabs{display:flex;gap:8px;overflow-x:auto;margin:8px 0 17px;padding:4px 0 7px}
.tabs button{display:inline-flex;align-items:center;gap:8px;border-radius:13px;padding:10px 14px;transition:background .2s,transform .2s,border-color .2s}
.tabs button.active{background:linear-gradient(135deg,rgba(14,165,233,.18),rgba(139,92,246,.12));border-color:rgba(56,189,248,.48);box-shadow:0 2px 12px rgba(51,148,237,.08)}
.tabs .tab-icon{width:17px;height:17px;color:#38bdf8}.tabs button.active .tab-icon{color:#05c5e9}
.gauge-top{justify-content:center;gap:8px}.gauge-symbol{color:#38bdf8;width:17px;height:17px}
.gauge-top.gauge-warn .gauge-symbol{color:#f59e0b}.gauge-top.gauge-danger .gauge-symbol{color:#fb7185}.gauge-top.gauge-muted .gauge-symbol{color:#94a3b8}
.hw-tile{background:linear-gradient(145deg,var(--card-background-color),var(--secondary-background-color));border-radius:15px;transition:border-color .2s}
.hw-tile .icon-chip{width:32px;height:32px}.hw-tile .key{font-weight:600;margin-top:8px}
.model-line{gap:9px}.hw-model{font-size:19px}.model-line .icon-chip{width:35px;height:35px}
.stat{border:1px solid var(--divider-color);border-radius:16px;background:linear-gradient(140deg,var(--secondary-background-color),var(--card-background-color));padding:13px}
.stat-caption{justify-content:flex-start;gap:8px}.stat .icon-chip{width:29px;height:29px;border-radius:9px}.stat .icon-chip .mi-icon{width:16px;height:16px}
.stat-caption span:last-child{font-size:11px;color:var(--secondary-text-color);font-weight:650}
.stat strong{font-size:26px;margin:8px 0 0;font-variant-numeric:tabular-nums}
.stat-online strong{color:#10b981}.stat-offline strong{color:#fb7185}.stat-dynamic strong{color:#f59e0b}.stat-unapproved strong{color:#a78bfa}
.device-label .mi-icon{width:17px;height:17px;color:#0ea5e9}.device-label span{overflow:hidden;text-overflow:ellipsis}
.connection-pill .mi-icon{width:16px;height:16px;color:#38bdf8}
.connection-pill.link-wifi .mi-icon,.device-label.link-wifi .mi-icon{color:#10b981}
.connection-pill.link-lan .mi-icon,.device-label.link-lan .mi-icon{color:#0ea5e9}
.zalo-hint{margin:7px 0 12px;padding:9px 12px;border-left:3px solid var(--divider-color);background:var(--secondary-background-color);border-radius:7px;line-height:1.6;font-size:12px;color:var(--secondary-text-color)}
.zalo-hint.warning{border-left-color:var(--nwm-amber)}
.state-pill,.log-level{display:inline-flex;align-items:center;gap:5px;font-weight:750;padding:5px 9px}
.state-pill .mi-icon,.pill .mi-icon,.log-level .mi-icon{width:14px;height:14px;vertical-align:middle}
.state-pill.online{border-color:rgba(16,185,129,.35);background:rgba(16,185,129,.09);color:#0eaf82}
.state-pill.offline{border-color:rgba(244,63,94,.35);background:rgba(244,63,94,.09);color:#e75a78}
.pill.dynamic{color:#d98b0c;background:rgba(245,158,11,.10);border-color:rgba(245,158,11,.30);display:inline-flex;gap:5px;align-items:center}
.log-level{border-radius:8px;background:rgba(14,165,233,.09);color:var(--secondary-text-color);font-size:11px}
.log-level.warn{background:rgba(245,158,11,.13);color:#d98b0c}
.toolbar button{display:inline-flex;align-items:center;gap:7px}.button-icon{width:16px;height:16px;color:#0ea5e9}
.nwm-theme-mono .icon-chip{background:var(--secondary-background-color);border-color:var(--divider-color);color:var(--primary-text-color);box-shadow:none}
.nwm-theme-mono .tabs .tab-icon,.nwm-theme-mono .gauge-symbol{color:var(--secondary-text-color)}
@media(max-width:600px){.header{margin:-10px -10px 12px;padding:16px 12px}.brand-avatar{width:42px;height:42px}.brand-title-group .title{font-size:16px}.brand-subtitle{font-size:8px;letter-spacing:.5px}.header .hint{font-size:10px}.tabs button{padding:9px}.tabs button .mi-icon{width:16px;height:16px}.stat-caption span:last-child{font-size:10px}}
/* Beta.5 responsive density. Prefer container width over viewport width. */
:host{container-type:inline-size;min-width:0}
ha-card{border-radius:14px!important;padding:12px;box-shadow:var(--ha-card-box-shadow,none);max-width:100%;box-sizing:border-box}
.header{min-height:0;margin:-12px -12px 10px;padding:12px 14px;border-radius:14px 14px 0 0}
.brand-avatar{width:37px;height:37px}.brand-head{gap:9px}
.brand-title-group .title{font-size:17px}.brand-subtitle{letter-spacing:.4px;font-size:9px;margin-top:2px}
.tabs{gap:5px;margin:6px 0 10px;padding:2px 0 4px}
.tabs button{padding:7px 9px;gap:5px;font-size:12px;border-radius:9px}
.stats{grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin:8px 0 10px}
.stat{padding:8px 9px;border-radius:11px;min-width:0}
.stat strong{font-size:clamp(17px,2.2vw,23px);margin:4px 0 0}
.stat-caption{gap:5px}.stat-caption span:last-child{font-size:10px;overflow-wrap:anywhere}
.stat .icon-chip{width:23px;height:23px;border-radius:7px}.stat .icon-chip .mi-icon{width:14px;height:14px}
.toolbar{align-items:center;gap:6px;margin:7px 0}.toolbar input,.toolbar select,.toolbar button,.footer button{min-height:32px;padding:6px 9px;border-radius:8px;font-size:12px}
.toolbar input{min-width:90px}.sort-select{max-width:130px}
.column-panel{position:relative;flex:none;z-index:3;font-size:12px}
.column-panel summary{cursor:pointer;list-style:none;border:1px solid var(--divider-color);border-radius:8px;padding:7px 10px;background:var(--card-background-color);user-select:none}
.column-panel summary::before{content:'☷ ';color:var(--primary-color)}
.column-panel[open] summary{border-color:var(--primary-color)}
.column-choices{position:absolute;top:calc(100% + 4px);right:0;width:max-content;min-width:150px;max-width:calc(100vw - 40px);max-height:70vh;overflow:auto;padding:8px;border:1px solid var(--divider-color);border-radius:10px;background:var(--card-background-color);box-shadow:0 10px 28px rgba(0,0,0,.21);display:grid;gap:3px}
.column-choice{display:flex;align-items:center;gap:8px;padding:6px 7px;cursor:pointer;border-radius:7px}
.column-choice:focus-within,.column-choice:hover{background:var(--secondary-background-color)}
.column-choice input{accent-color:var(--primary-color);width:16px;height:16px;margin:0}
.table-wrap{width:100%;overflow-x:auto}table{table-layout:auto;font-size:12px}
th,td{padding:7px 6px}.name{max-width:230px}.ip-address{font-variant-numeric:tabular-nums}
.state-pill{padding:3px 6px;font-size:11px}.approve{padding:4px 6px;font-size:11px}
.zalo-hint{padding:6px 8px;font-size:11px;margin:6px 0}
.gauges{gap:8px;margin:10px 0}.gauge-card{padding:9px 6px;border-radius:12px;gap:5px}
.gauge-dial{width:min(95px,100%)}.gauge-title{font-size:11px}.gauge-state{font-size:10px}
.hw-extras{grid-template-columns:repeat(auto-fit,minmax(115px,1fr));gap:6px;margin:8px 0}
.hw-tile{padding:9px;border-radius:11px}.hw-tile .key{margin:4px 0 3px}.hw-tile .value{font-size:13px}

@container (max-width:680px){
  .header{gap:4px}.header .hint{width:100%;padding-left:45px;font-size:10px}
  .stats{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}
  .stat{padding:6px 7px}.stat strong{font-size:19px}
  .stat .icon-chip{width:20px;height:20px}.stat .icon-chip .mi-icon{width:12px;height:12px}
  .tabs{gap:4px}.tabs button{flex:1 1 auto;justify-content:center;padding:7px 6px;font-size:11px}
  .tabs button .mi-icon{width:14px;height:14px}
  .toolbar{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:5px}
  .toolbar>input{grid-column:1/-1;min-width:0;width:100%;box-sizing:border-box}
  .toolbar>select:first-child{min-width:0;width:100%}
  .toolbar>.sort-select{max-width:none;width:100%}
  .column-panel{justify-self:end}
  .device-table-wrap{overflow-x:visible}
  .devices-table,.devices-table tbody{display:block;width:100%}.devices-table thead{display:none}
  .devices-table tbody{display:grid;gap:5px}
  .devices-table tbody tr{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:4px 7px;align-items:center;border:1px solid var(--divider-color);border-radius:10px;padding:7px 9px;min-width:0}
  .devices-table tbody td{display:flex;align-items:center;min-width:0;white-space:normal;padding:1px 0;border:0;font-size:11px;overflow-wrap:anywhere}
  .devices-table tbody td[data-col=device]{grid-column:1/3;grid-row:1;font-size:12px}
  .devices-table tbody td[data-col=state]{grid-column:3;grid-row:1;justify-self:end}
  .devices-table tbody td[data-col=ip]{font-size:11px;min-width:0;grid-column:1/2}
  .devices-table tbody td[data-col=link]{grid-column:2/3}
  .devices-table tbody td[data-col=approved]{justify-self:end}
  .devices-table tbody td[data-col=port],.devices-table tbody td[data-col=dhcp]{color:var(--secondary-text-color)}
  .devices-table tbody td[data-col=port]::before{content:'Port: ';margin-right:3px}
  .name{max-width:none}.device-label span{overflow-wrap:anywhere;word-break:break-word}
  .device-label{gap:5px}.device-label .mi-icon{width:14px;height:14px}
  .connection-pill{gap:4px}.connection-pill .mi-icon{width:13px;height:13px}
  .gauges{gap:5px}.gauge-card{padding:7px 3px;border-radius:9px}
  .gauge-dial{width:min(70px,100%)}.gauge-value{font-size:19px}
  .gauge-title{font-size:10px}.gauge-state{font-size:9px;letter-spacing:0}
  .hw-extras{grid-template-columns:repeat(2,minmax(0,1fr))}
  .hw-model{font-size:16px}.hw-badge{padding:5px 7px;font-size:9px}
}
@container (max-width:350px){
 .tabs button{font-size:10px;padding:6px 4px}.tabs .tab-icon{display:none}
 .stats{grid-template-columns:repeat(3,minmax(0,1fr))}
 .stat-caption .icon-chip{display:none}.stat strong{font-size:18px}
 .toolbar{grid-template-columns:minmax(0,1fr) auto}.toolbar>.sort-select{grid-column:1}
 .gauges .gauge-state{display:none}
}
/* beta.6: values sit precisely at the geometric center of each circular dial.
   Keep the unit independent of the number's centering, with a 2-3px gap. */
.gauge-card{--nwm-gauge-number-size:23px;--nwm-gauge-unit-offset:15px}
.gauge-hole{position:relative;display:block}
.gauge-value{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:var(--nwm-gauge-number-size);line-height:1;margin:0;white-space:nowrap;letter-spacing:-.55px}
.gauge-unit{position:absolute;left:50%;top:calc(50% + var(--nwm-gauge-unit-offset));transform:translateX(-50%);font-size:10px;line-height:1;white-space:nowrap;margin:0}
/* Icon | (label over reading) makes every extra metric denser on phones. */
.hw-tile{display:grid;grid-template-columns:36px minmax(0,1fr);align-items:center;gap:10px;min-height:62px;padding:10px 12px}
.hw-tile .icon-chip{width:36px;height:36px}
.hw-tile-copy{display:flex;flex-direction:column;justify-content:center;gap:4px;min-width:0}
.hw-tile .key{margin:0;font-size:11px;line-height:1.2}
.hw-tile .value{margin:0;font-size:15px;line-height:1.23;overflow-wrap:anywhere;min-width:0;font-variant-numeric:tabular-nums}
.hw-extras{grid-template-columns:repeat(auto-fit,minmax(185px,1fr))}
@container (max-width:680px){
  .gauge-card{--nwm-gauge-number-size:20px;--nwm-gauge-unit-offset:13px}
  .hw-extras{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  .hw-tile{grid-template-columns:30px minmax(0,1fr);gap:8px;padding:9px;min-height:56px}
  .hw-tile .icon-chip{width:30px;height:30px}
  .hw-tile .icon-chip .mi-icon{width:18px;height:18px}
  .hw-tile .key{font-size:10px}
  .hw-tile .value{font-size:13px}
}
@container (max-width:330px){.hw-extras{grid-template-columns:1fr}}


/* beta.7: model and status always share the first row on narrow cards. */
.hw-title{display:grid;grid-template-columns:minmax(0,1fr) max-content;align-items:center;gap:5px 8px}
.hw-title>.model-line{min-width:0;gap:8px}
.hw-title>.hw-sub{grid-column:1/-1;min-width:0;line-height:1.45}
.hw-title>.hw-badge{white-space:nowrap;justify-self:end;max-width:100%}
.hw-model{min-width:0;overflow-wrap:anywhere}
/* Larger labels and readings, closer to the curved tile edge, with a clear icon/text gutter. */
.hw-tile{grid-template-columns:46px minmax(0,1fr);gap:15px;min-height:72px;padding:8px 10px;border-radius:12px}
.hw-tile .icon-chip{width:46px;height:46px;border-radius:12px}
.hw-tile .icon-chip .mi-icon{width:26px;height:26px}
.hw-tile-copy{gap:5px}
.hw-tile .key{font-size:13px;line-height:1.23;font-weight:600}
.hw-tile .value{font-size:18px;line-height:1.2;font-weight:800;overflow-wrap:anywhere}
.hw-extras{grid-template-columns:repeat(auto-fit,minmax(218px,1fr));gap:8px}
@container (max-width:680px){
 .hw-title{gap:5px 6px}
 .hw-title>.model-line{gap:6px}
 .hw-title .icon-chip{width:30px;height:30px}
 .hw-title .icon-chip .mi-icon{width:18px;height:18px}
 .hw-model{font-size:16px}
 .hw-title .hw-badge{font-size:9px;letter-spacing:0;padding:5px 6px}
 .hw-extras{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
 .hw-tile{grid-template-columns:40px minmax(0,1fr);gap:12px;min-height:76px;padding:7px 8px;border-radius:11px}
 .hw-tile .icon-chip{width:40px;height:40px;border-radius:10px}
 .hw-tile .icon-chip .mi-icon{width:23px;height:23px}
 .hw-tile .key{font-size:12px;line-height:1.2}
 .hw-tile .value{font-size:16px;line-height:1.2}
}
@container (max-width:345px){
 .hw-extras{grid-template-columns:repeat(2,minmax(0,1fr))}
 .hw-tile{grid-template-columns:33px minmax(0,1fr);gap:12px;min-height:74px;padding:6px 7px}
 .hw-tile .icon-chip{width:33px;height:33px}
 .hw-tile .icon-chip .mi-icon{width:20px;height:20px}
 .hw-tile .key{font-size:11px}
 .hw-tile .value{font-size:14px}
 .hw-title .hw-badge{font-size:8px;padding:4px 5px}
 .hw-title .hw-model{font-size:14px}
}

`;
function elt(tag, parent, text, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (parent) parent.appendChild(node);
  return node;
}

const ICON_PATHS = Object.freeze({"brand":"M12 2 20.5 6.5V12c0 5.1-3.4 8.5-8.5 10-5.1-1.5-8.5-4.9-8.5-10V6.5L12 2ZM7.5 13.8l2.4 2.4 6.7-6.7 M9 8.7c1.6-1.5 4.4-1.5 6 0","router":"M4 10V6 M8 10V4 M3 11h18v8H3z M7.4 15.5h.01 M11.4 15.5h.01 M15.4 15.5h.01 M19 15.5h.01","mesh":"M12 2.8v3.4 M7 7.6l5-1.4 5 1.4 M7 7.6l-3.8 8.8 M17 7.6l3.8 8.8 M3.2 16.4l8.8 4 8.8-4 M9 6.2a3 3 0 1 0 6 0a3 3 0 1 0-6 0 M1.2 16.5a2 2 0 1 0 4 0a2 2 0 1 0-4 0 M18.8 16.5a2 2 0 1 0 4 0a2 2 0 1 0-4 0","shield":"M12 2 20.5 6.5V12c0 5.1-3.4 8.5-8.5 10-5.1-1.5-8.5-4.9-8.5-10V6.5z M8.5 12.5l2.3 2.3 4.8-5","cpu":"M6 6h12v12H6z M9 9h6v6H9z M9 2v4 M15 2v4 M9 18v4 M15 18v4 M2 9h4 M2 15h4 M18 9h4 M18 15h4","ram":"M3 7h18v10H3z M7 7v4 M11 7v4 M15 7v4 M19 7v4 M7 17v2 M17 17v2 M7 13h.01 M11 13h.01 M15 13h.01","thermometer":"M10 13.5V5a2 2 0 0 1 4 0v8.5a4 4 0 1 1-4 0Z M12 8v9 M12 18h.01","warning":"M12 3 2.7 20h18.6L12 3z M12 9v5 M12 17h.01","devices":"M4 5h13v10H4z M9 20h13v-9h-4 M7 18h7 M10.5 15v3","online":"M12 21a9 9 0 1 0 0-18 9 9 0 1 0 0 18z M7.5 12.2l3.1 3.1 6.1-6.5","offline":"M12 21a9 9 0 1 0 0-18 9 9 0 1 0 0 18z M8 8l8 8 M16 8l-8 8","unknown":"M12 21a9 9 0 1 0 0-18 9 9 0 1 0 0 18z M9.7 9.5a2.4 2.4 0 1 1 3.6 2.1c-.8.5-1.3 1-1.3 2 M12 17h.01","dynamic":"M7 3h10l4 4v14H3V7z M7 12h10 M12 8v8 M7 17h10","wifi":"M2 9a15 15 0 0 1 20 0 M5 12.5a10.5 10.5 0 0 1 14 0 M8.5 16a5.5 5.5 0 0 1 7 0 M12 20h.01","lan":"M12 3v6 M5 21v-7h14v7 M5 14h14 M5 21h.01 M12 21h.01 M19 21h.01 M12 9h-7v5 M12 9h7v5","logs":"M8 3h10v18H6a2 2 0 0 1-2-2V7h3 M9 8h6 M9 12h6 M9 16h4","firewall":"M3 4h18v16H3z M3 9h18 M3 15h18 M9 4v5 M15 9v6 M9 15v5 M7 9v6","download":"M12 3v13 M7 11l5 5 5-5 M4 18v3h16v-3","upload":"M12 17V4 M7 9l5-5 5 5 M4 18v3h16v-3","storage":"M4 7h16v10H4z M7 12h.01 M10 12h.01 M13 12h5","voltage":"M13 2 5 13h6l-1 9 9-12h-6z","fan":"M12 12c2.5-1.9 3.2-7.2.9-8-2.6-1-3.9 2.4-3.8 5.6 M12 12c1.9 2.5 7.2 3.2 8 .9 1-2.6-2.4-3.9-5.6-3.8 M12 12c-2.5 1.9-3.2 7.2-.9 8 2.6 1 3.9-2.4 3.8-5.6 M12 15a3 3 0 1 0 0-6 3 3 0 1 0 0 6","clock":"M12 21a9 9 0 1 0 0-18 9 9 0 1 0 0 18z M12 7v5l4 2","firmware":"M5 8h14v8H5z M9 4v4 M15 4v4 M9 16v4 M15 16v4 M2 11h3 M19 11h3","hardware":"M4 12h16 M12 4v16 M8 8h8v8H8z M5 5h.01 M19 5h.01 M5 19h.01 M19 19h.01","approved":"M12 21a9 9 0 1 0 0-18 9 9 0 1 0 0 18z M7.5 12l3.3 3.4 6-6.8","unapproved":"M12 3v12 M12 18h.01 M4 21h16l-8-18z","search":"M11 18a7 7 0 1 0 0-14 7 7 0 1 0 0 14z M16 16l5 5","refresh":"M20 11a8 8 0 0 0-14-5L3 9 M3 3v6h6 M4 13a8 8 0 0 0 14 5l3-3 M21 21v-6h-6","info":"M12 21a9 9 0 1 0 0-18 9 9 0 1 0 0 18z M12 11v6 M12 7h.01","lock":"M5 11h14v10H5z M8 11V8a4 4 0 0 1 8 0v3 M12 15v2","alert":"M12 3 2.7 20h18.6z M12 9v5 M12 17h.01"});
const XMLNS = 'http://www.w3.org/2000/svg';
function miIcon(parent, name, className = 'mi-icon') {
  const svg = document.createElementNS(XMLNS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.8');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('focusable', 'false');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('class', className);
  const path = document.createElementNS(XMLNS, 'path');
  path.setAttribute('d', ICON_PATHS[name] || ICON_PATHS.unknown);
  svg.appendChild(path);
  parent.appendChild(svg);
  return svg;
}
function miBadge(parent,name,tone='cyan') {
  const wrapper=elt('span',parent,null,`icon-chip tone-${tone}`);
  miIcon(wrapper,name);
  return wrapper;
}

class NetwatcherMikMiCard extends HTMLElement {
  static getStubConfig() { return {type: `custom:${CARD_TAG}`, title: 'Netwatcher MikMi', page_size: 25, show_ap: true, show_dhcp: true, show_logs: true, show_hardware: true, show_traffic: true, show_brand: true, icon_style: 'cyber', default_view:'hardware'}; }
  static getConfigElement() { return document.createElement('netwatcher-mikmi-card-editor'); }
  getCardSize() { return 5; }
  // Sections layout: allow width resizing, keep height content-driven.
  getGridOptions() { return {columns: 12, min_columns: 3}; }
  setConfig(config) {
    if (!config || typeof config !== 'object') throw new Error('Netwatcher MikMi requires a card configuration');
    this._config = {...NetwatcherMikMiCard.getStubConfig(), ...config};
    // Keep the selected sort across frontend re-renders; default stays recent-first.
    if (!['name','ip'].includes(this._sortBy)) this._sortBy = 'recent';
    if (!['asc','desc'].includes(this._sortDir)) this._sortDir = 'desc';
    this._columnsLoaded = false;
    this._visibleColumns = null;
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
    this._card.classList.add(this._config.icon_style === 'mono' ? 'nwm-theme-mono' : 'nwm-theme-cyber');
    const header = elt('div', this._card, null, 'header');
    const brand=elt('div',header,null,'brand-head');
    if (this._config.show_brand !== false) {
      const badge=elt('img',brand,null,'brand-avatar');
      badge.alt='Netwatcher MikMi';
      badge.width=50;badge.height=50;
      const preview=window.location.pathname.endsWith('/router_health_demo.html');
      badge.src=preview ? '../custom_components/netwatcher_mikmi/frontend/assets/netwatcher-brand-icon.png' : '/netwatcher-mikmi/assets/netwatcher-brand-icon.png';
    } else { miBadge(brand,'shield','cyan'); }
    const brandTitles=elt('div',brand,null,'brand-title-group');
    elt('div',brandTitles,this._config.title || 'Netwatcher MikMi','title');
    elt('div',brandTitles,'NETWORK INTELLIGENCE · MIKROTIK · ROUTEROS','brand-subtitle');
    this._health = elt('div', header, 'Connecting...', 'hint');
    this._stats = elt('div', this._card, null, 'stats');
    const views = ['hardware','devices','logs'];
    this._view = views.includes(this._config.default_view) ? this._config.default_view : 'hardware';
    if (this._view === 'hardware' && this._config.show_hardware === false) this._view = 'devices';
    if (this._view === 'logs' && this._config.show_logs === false) this._view = 'devices';
    this._tabs = elt('div', this._card, null, 'tabs');
    this._stats.hidden=this._view!=='devices';
    const tabButtons = {};
    const tabSpecs = [
      ['hardware','Router Health','cpu',this._config.show_hardware!==false],
      ['devices','Thiết bị','devices',true],
      ['logs','Nhật ký WAN','firewall',this._config.show_logs!==false],
    ];
    for (const [key,label,glyph,visible] of tabSpecs) {
      const btn = elt('button',this._tabs);
      miIcon(btn,glyph,'mi-icon tab-icon');
      elt('span',btn,label);
      if (!visible) btn.hidden=true;
      btn.classList.toggle('active',key===this._view);
      tabButtons[key]=btn;
      btn.addEventListener('click',()=>{
        this._view=key;
        this._stats.hidden=key!=='devices';
        this._hardwareView.hidden = key!=='hardware';
        this._deviceView.hidden = key!=='devices';
        this._logView.hidden = key!=='logs';
        for (const [k,b] of Object.entries(tabButtons)) b.classList.toggle('active',k===key);
        this._offset=0;this._lastFetch=0;this._refresh(true);
      });
    }
    this._hardwareView=elt('div',this._card,null,'hw-cover');
    this._hardwareView.hidden=this._view!=='hardware';
    this._hwMessage=elt('div',this._hardwareView,'Đang lấy dữ liệu phần cứng…','small');
    this._hwContent=elt('div',this._hardwareView);
    this._deviceView = elt('div', this._card);
    this._deviceView.hidden=this._view!=='devices';
    const toolbar = elt('div', this._deviceView, null, 'toolbar');
    this._filter = elt('select', toolbar);
    [['all','All'],['online','Online'],['offline','Offline'],['dynamic','DHCP dynamic'],['unapproved','Unapproved']].forEach(([value,label]) => {
      const opt = elt('option', this._filter, label); opt.value = value;
    });
    this._filter.value = ['all','online','offline','dynamic','unapproved'].includes(this._config.default_filter) ? this._config.default_filter : 'all';
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
    // Mobile-friendly sort control; desktop users can still click column headers.
    this._sortSelect = elt('select', toolbar, null, 'sort-select');
    this._sortSelect.setAttribute('aria-label', 'Sắp xếp thiết bị');
    [['recent:desc','Gần đây'],['name:asc','Tên A → Z'],['name:desc','Tên Z → A'],
     ['ip:asc','IP tăng dần'],['ip:desc','IP giảm dần']].forEach(([value,label]) => {
      const option=elt('option',this._sortSelect,label);option.value=value;
    });
    this._sortSelect.value = `${this._sortBy}:${this._sortDir}`;
    this._sortSelect.addEventListener('change', () => {
      [this._sortBy,this._sortDir] = this._sortSelect.value.split(':');
      this._offset=0;this._refresh(true);
    });

    // Preferences are stored per HA account and integration entry in HA Store.
    this._columnsPanel = elt('details',toolbar,null,'column-panel');
    const summary=elt('summary',this._columnsPanel,'Cột hiển thị');
    summary.setAttribute('aria-label','Chọn cột thiết bị cần hiển thị');
    this._columnChoices=elt('div',this._columnsPanel,null,'column-choices');
    for(const [key,label] of DEVICE_COLUMNS){
      const holder=elt('label',this._columnChoices,null,'column-choice');
      const check=elt('input',holder);check.type='checkbox';check.value=key;
      elt('span',holder,label);
      check.addEventListener('change',async()=>{
        const previous=[...(this._visibleColumns||DEVICE_COLUMNS.map(x=>x[0]))];
        const proposed=DEVICE_COLUMNS.filter(([id])=>
          id===key ? check.checked : previous.includes(id)).map(x=>x[0]);
        if(!proposed.length){check.checked=true;return;}
        this._visibleColumns=proposed;
        this._syncColumnControls();
        if(this._cachedDevices)this._show(this._cachedDevices);
        try{
          if(!this._entryId)throw new Error('No config entry');
          await this._hass.callWS({type:'netwatcher_mikmi/columns',
            entry_id:this._entryId,columns:proposed});
        }catch(_error){
          this._visibleColumns=previous;this._syncColumnControls();
          if(this._cachedDevices)this._show(this._cachedDevices);
          this._message.textContent='Không lưu được lựa chọn cột. Kiểm tra quyền quản trị/nhật ký HA.';
        }
      });
    }
    const testZalo = elt('button', toolbar, 'Test Zalo');
    miIcon(testZalo,'alert','mi-icon button-icon');
    testZalo.title = 'Send a test message via personal-account Zalo Bot to configured recipients (unofficial API).';
    testZalo.addEventListener('click', async () => {
      if (!this._hass || !window.confirm('Send a test message to every configured Zalo recipient?')) return;
      testZalo.disabled = true;
      try {
        if (!this._entryId) await this._refresh(true);
        const result = await this._hass.callWS({type:'netwatcher_mikmi/test_zalo',entry_id:this._entryId});
        this._testMessage.textContent = result.disabled ? 'Zalo Bot đang tắt trong Options.' :
          result.cooldown ? 'Vui lòng đợi 60 giây trước khi gửi tin thử tiếp theo.' :
          result.service_missing ? 'Chưa tìm thấy action zalo_bot.send_message.' :
          result.missing_configuration ? 'Còn thiếu tài khoản gửi hoặc ID người nhận Zalo.' :
          result.invalid_recipients ? 'Danh sách ID người nhận Zalo không hợp lệ.' :
          `Tin thử Zalo: ${result.submitted || 0} lượt được service chấp nhận, ${result.failed || 0} lỗi, ${result.rate_limited || 0} bị giới hạn. (Chưa xác nhận đã đến máy nhận.)`;
      } catch (_error) { this._testMessage.textContent = 'Không gửi được tin thử. Kiểm tra Options và Home Assistant logs.'; }
      finally { testZalo.disabled = false; }
    });
    const refresh = elt('button', toolbar, 'Làm mới');
    miIcon(refresh,'refresh','mi-icon button-icon');
    refresh.addEventListener('click', () => this._refresh(true));
    this._message = elt('div', this._deviceView, '', 'small');
    this._zaloHint = elt('div',this._deviceView,'','zalo-hint');
    this._testMessage = elt('div',this._deviceView,'','small');
    const wrap = elt('div', this._deviceView, null, 'table-wrap device-table-wrap');
    this._table = elt('table', wrap, null, 'devices-table');
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
    miIcon(logRefresh,'refresh','mi-icon button-icon');
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
          sort_by:this._sortBy||'recent',sort_dir:this._sortDir||'desc',
        });
        this._entryId = data.entry_id;
        this._show(data);
      }
    } catch (error) {
      const out=this._view==='hardware'?this._hwMessage:this._view==='logs'?this._logMessage:this._message;
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
    const titleLine=elt('div',top,null,'model-line');
    miBadge(titleLine,'router','cyan');
    const model=elt('div',titleLine,b.model || 'MikroTik Router','hw-model');
    const active=available&&Object.entries(a).some(([key,v])=>v&&r[key]!=null&&Number(r[key])>=Number(v.threshold));
    const warning=available&&Object.entries(a).some(([k,v])=>v?.enabled&&r[k]!=null&&r[k]>=v.threshold*.85);
    const badge=elt('span',top,!available?'● KHÔNG CÓ DỮ LIỆU':active?'● CẢNH BÁO QUÁ NGƯỠNG':warning?'● CẦN THEO DÕI':'● THIẾT BỊ ỔN ĐỊNH',
      `hw-badge ${!available?'muted':active?'danger':warning?'warn':''}`);
    badge.setAttribute('role','status');
    elt('div',top,`RouterOS ${b.routeros_version || '—'} · ${b.architecture || '—'} · ${b.cpu_count||r.cpu_count||'—'} core(s)`,'hw-sub');
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
        ['download','WAN Download',bpsToMbps(wan.rx_bps),'green'],
        ['upload','WAN Upload',bpsToMbps(wan.tx_bps),'purple'],
      ]),
      ['storage','Lưu trữ',fmt(r.storage,'%'),'blue'],
      ['voltage','Điện áp',fmt(r.voltage,' V'),'amber'],
      ['fan','Quạt',fmt(r.fan_rpm,' RPM'),'green'],
      ['ram','RAM tổng',fmt(r.total_ram_mib,' MiB'),'purple'],
      ['cpu','Xung CPU',fmt(r.cpu_frequency_mhz,' MHz'),'blue'],
      ['clock','Uptime',uptime,'muted'],
      ['hardware','CPU',b.cpu_name||'—','cyan'],
      ['firmware','Firmware',b.firmware||'—','purple'],
    ];
    for(const [symbol,key,val,tone] of values){
      const tile=elt('div',extras,null,'hw-tile');
      miBadge(tile,symbol,tone);
      const copy=elt('div',tile,null,'hw-tile-copy');
      elt('div',copy,key,'key');
      elt('div',copy,val,'value');
    }
  }
  _gauge(parent,title,value,max,alert,unit){
    const box=elt('div',parent,null,'gauge-card');
    const gaugeHead=elt('div',box,null,'gauge-top');
    miIcon(gaugeHead,title==='CPU'?'cpu':title==='RAM'?'ram':'thermometer','mi-icon gauge-symbol');
    elt('div',gaugeHead,title,'gauge-title');
    const dial=elt('div',box,null,'gauge-dial');
    const valid=Number.isFinite(Number(value)) && value!==null && value!==undefined;
    const current=valid?Number(value):0;
    const threshold=Number.isFinite(Number(alert?.threshold))?Number(alert.threshold):(unit==='°C'?75:title==='RAM'?90:85);
    const high=valid&&current>=threshold;
    const near=valid&&current>=threshold*0.85;
    const state=!valid?'muted':high?'danger':near?'warn':'ok';
    gaugeHead.classList.add(`gauge-${state}`);
    const color=state==='danger'?'var(--nwm-red)':state==='warn'?'var(--nwm-amber)':state==='ok'?'var(--nwm-teal)':'var(--divider-color)';
    const deg=Math.max(0,Math.min(360,(current/max)*360));
    dial.style.background=`conic-gradient(${color} 0deg ${deg}deg,var(--divider-color) ${deg}deg 360deg)`;
    const hole=elt('div',dial,null,'gauge-hole');
    elt('div',hole,valid?String(Math.round(current*10)/10):'—','gauge-value');
    elt('div',hole,unit,'gauge-unit');
    elt('div',box,!valid?'KHÔNG HỖ TRỢ':high?'QUÁ NGƯỠNG':near?'CẦN THEO DÕI':'BÌNH THƯỜNG',`gauge-state ${state}`);
    elt('div',box,`Ngưỡng: ${alert?.threshold??threshold}${unit}`,'hw-sub');
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
      const level=elt('td',row);
      const levelPill=elt('span',level,null,`log-level ${item.category==='normal'?'': 'warn'}`);
      miIcon(levelPill,item.category==='normal'?'info':'warning');
      elt('span',levelPill,item.category==='normal'?'info':item.category);
      const cell=elt('td',row,item.message||'-');
      cell.style.whiteSpace='normal';cell.style.minWidth='280px';
    }
    if(!data.logs?.length){const row=elt('tr',body),cell=elt('td',row,'Chưa có log phù hợp.');cell.colSpan=4;}
    this._logPrev.disabled=this._offset<=0;
    this._logNext.disabled=this._offset+50>=data.count;
    this._logCount.textContent=`${data.count?this._offset+1:0}-${Math.min(this._offset+(data.logs||[]).length,data.count)} / ${data.count} log`;
  }
  _syncColumnControls(){
    const visible=this._visibleColumns||DEVICE_COLUMNS.map(x=>x[0]);
    for(const input of this._columnChoices?.querySelectorAll('input')||[])
      input.checked=visible.includes(input.value);
  }
  _show(data) {
    this._cachedDevices=data;
    if(!this._columnsLoaded){
      const allowed=DEVICE_COLUMNS.map(x=>x[0]);
      const saved=Array.isArray(data.column_preferences)?
        data.column_preferences.filter(id=>allowed.includes(id)):[];
      this._visibleColumns=saved.length?saved:allowed.filter(id=>
        (id!=='port'||this._config.show_ap!==false) &&
        (id!=='dhcp'||this._config.show_dhcp!==false));
      this._columnsLoaded=true;
      this._syncColumnControls();
    }
    const visible=this._visibleColumns||DEVICE_COLUMNS.map(x=>x[0]);
    this._message.className='small';
    this._message.textContent = data.baseline_complete ? '' : 'Đang chờ dữ liệu MikroTik lần đầu. Chưa phát cảnh báo thiết bị.';
    const sources = data.source_health || {};
    this._health.textContent = sources.mikrotik?.ok ? '● MikroTik: OK' :
      `● MikroTik: Mất dữ liệu (${sources.mikrotik?.error||'chưa cập nhật'})`;
    const zalo = data.zalo || {};
    const reasons=[];
    if (!zalo.enabled) reasons.push('Zalo Bot đang tắt');
    else {
      if(!zalo.account_configured || !zalo.recipient_count || zalo.recipients_valid===false)
        reasons.push('Chưa cấu hình tài khoản/ID người nhận hợp lệ');
      if(!zalo.service_available) reasons.push('Không có action zalo_bot.send_message');
      if(!zalo.offline_alerts || !zalo.online_alerts)
        reasons.push(`Cảnh báo Offline: ${zalo.offline_alerts?'BẬT':'TẮT'}, Online: ${zalo.online_alerts?'BẬT':'TẮT'}`);
    }
    if(!sources.mikrotik?.ok)
      reasons.push('Nguồn RouterOS mất kết nối: không gửi sự kiện Online/Offline giả');
    const delivery=zalo.last_delivery;
    if(delivery)
      reasons.push(`Zalo gần nhất (${delivery.type}): ${delivery.submitted||0} được service chấp nhận, ${delivery.failed||0} lỗi`);
    this._zaloHint.hidden=!reasons.length;
    this._zaloHint.className=`zalo-hint ${reasons.length?'warning':''}`;
    this._zaloHint.textContent=`Quét ${data.poll_interval||30}s / xác nhận mất ${data.offline_after||120}s. ${reasons.join(' · ')}`;
    this._stats.replaceChildren();
    [['total','Tổng','devices','cyan'],['online','Online','online','green'],
      ['offline','Offline','offline','red'],['dynamic','DHCP động','dynamic','amber'],
      ['unapproved','Chưa duyệt','unapproved','purple']].forEach(([key,label,glyph,tone]) => {
      const box = elt('div',this._stats,null,`stat stat-${key}`);
      const info=elt('div',box,null,'stat-caption');
      miBadge(info,glyph,tone);elt('span',info,label);
      elt('strong',box,data.statistics?.[key]||0);
    });
    this._table.replaceChildren();
    const head=elt('thead',this._table), tr=elt('tr',head);
    for(const [field,label] of DEVICE_COLUMNS.filter(([id])=>visible.includes(id))){
      const th=elt('th',tr);th.dataset.col=field;
      if(field!=='device'&&field!=='ip'){th.textContent=label;continue;}
      const sortKey=field==='device'?'name':'ip';
      const active=this._sortBy===sortKey;
      th.setAttribute('aria-sort',active?(this._sortDir==='asc'?'ascending':'descending'):'none');
      const btn=elt('button',th,null,'sort-button');btn.type='button';
      const nextDir=active&&this._sortDir==='asc'?'desc':'asc';
      btn.setAttribute('aria-label',`Sắp xếp ${label} ${nextDir==='asc'?'tăng':'giảm'} dần`);
      elt('span',btn,label);
      const arrow=elt('span',btn,active?(this._sortDir==='asc'?'↑':'↓'):'↕','sort-arrow');
      arrow.setAttribute('aria-hidden','true');
      btn.addEventListener('click',()=>{
        this._sortDir=this._sortBy===sortKey&&this._sortDir==='asc'?'desc':'asc';
        this._sortBy=sortKey;
        this._sortSelect.value=`${this._sortBy}:${this._sortDir}`;
        this._offset=0;this._refresh(true);
      });
    }
    const body=elt('tbody',this._table);
    for (const d of data.devices||[]) {
      const row=elt('tr',body);
      for(const [field,label] of DEVICE_COLUMNS.filter(([id])=>visible.includes(id))){
        const cell=elt('td',row);cell.dataset.col=field;cell.dataset.label=label;
        if(field==='device'){
          cell.classList.add('name');cell.title=d.mac;
          const link=d.connection==='wifi'?'wifi':d.connection==='lan'?'lan':'none';
          const devLine=elt('div',cell,null,`device-label link-${link}`);
          miIcon(devLine,link==='none'?'devices':link);
          elt('span',devLine,d.name||d.mac);
        }else if(field==='ip'){
          elt('span',cell,d.ip||'—','ip-address');
        }else if(field==='state'){
          const state=d.online==='online'?'online':'offline';
          const pill=elt('span',cell,null,`pill state-pill ${state}`);
          miIcon(pill,state);elt('span',pill,state);
        }else if(field==='link'){
          const link=d.connection==='wifi'?'wifi':d.connection==='lan'?'lan':'none';
          const conn=elt('div',cell,null,`connection-pill link-${link}`);
          miIcon(conn,link==='none'?'devices':link);
          elt('span',conn,link==='wifi'?'Wi-Fi':link==='lan'?'LAN':'—');
          conn.title=link==='wifi'?'Được xác thực qua bảng đăng ký Wi-Fi MikroTik':
            link==='lan'?`Port LAN được xác thực: ${d.port||'—'}`:
            'RouterOS không có bằng chứng xác định LAN/Wi-Fi; không tự suy đoán từ ARP/DHCP.';
        }else if(field==='port'){
          elt('span',cell,d.ap_name||d.port||'—');
        }else if(field==='dhcp'){
          const tag=elt('span',cell,null,d.dhcp_dynamic===true?'pill dynamic':'pill');
          if(d.dhcp_dynamic===true)miIcon(tag,'dynamic');
          elt('span',tag,d.dhcp_dynamic===true?'Dynamic':d.dhcp_dynamic===false?'Static':'—');
        }else if(field==='approved'){
          const approve=elt('button',cell,d.approved?'Approved':'Approve','approve');
          approve.title=d.approved?'Bỏ đánh dấu thiết bị':'Đánh dấu thiết bị đã biết (không đổi quyền mạng)';
          approve.addEventListener('click',async()=>{
            approve.disabled=true;
            try{
              await this._hass.callWS({type:'netwatcher_mikmi/approve',entry_id:this._entryId,
                mac:d.mac,approved:!d.approved});
              d.approved=!d.approved;
              approve.textContent=d.approved?'Approved':'Approve';
              this._refresh(true);
            }catch(_error){this._message.textContent='Không lưu được Approved.';}
            finally{approve.disabled=false;}
          });
        }
      }
    }
    if(!data.devices?.length){
      const tr=elt('tr',body),td=elt('td',tr,'Không có thiết bị phù hợp.');
      td.colSpan=visible.length;
    }
    this._prev.disabled=this._offset<=0;
    this._next.disabled=this._offset+this._pageSize()>=data.count;
    const start=data.count?this._offset+1:0;
    this._count.textContent=`${start}–${Math.min(this._offset+(data.devices||[]).length,data.count)} / ${data.count}`;
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
      ['show_hardware','Show Router Health','checkbox'],['show_traffic','Show WAN RX/TX throughput','checkbox'],
      ['show_brand','Show integration brand icon','checkbox'],['icon_style','Icon appearance','select_icons'],
      ['show_search','Show search','checkbox'],['show_ap','Show AP / port','checkbox'],['show_dhcp','Show DHCP','checkbox'],['show_logs','Show MikroTik log viewer (admins only)','checkbox'],
    ];
    fields.forEach(([key,label,type])=>{
      const holder=elt('label',root,label),input=elt('input',holder);input.type=type;
      if(type==='checkbox')input.checked=this._config[key]!==false;
      else if(type==='select_icons'){
        [['cyber','Cyber gradient'],['mono','Minimal / monochrome']].forEach(([v,l])=>{
          const opt=elt('option',input,l);opt.value=v;
        });
        input.value=this._config[key]==='mono'?'mono':'cyber';
      }
      else if(type==='select'){
        ['hardware','devices','logs'].forEach(value=>{
          const option=elt('option',input,value==='hardware'?'Router Health':value==='devices'?'Thiết bị':'MikroTik Logs');
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
if(!window.customCards.some(c=>c.type===CARD_TAG))window.customCards.push({type:CARD_TAG,name:'Netwatcher MikMi',icon:'mdi:shield-home',description:'MikroTik RouterOS health, device inventory, WAN logs and Zalo Bot alerts',preview:false,configurable:true});
