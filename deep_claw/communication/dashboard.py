"""
Deep Claw Glass Box — immersive real-time dashboard.

Single-page terminal-style web UI at GET /
Live state pushed via Server-Sent Events at GET /api/stream every 2 seconds.
All data sourced from the orchestrator (read-only, no auth needed in Phase 1).

No external CDN — works on Replit, localhost, or any server.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

log = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, StreamingResponse
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

# ── Embedded single-page app ──────────────────────────────────────────────────

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DEEP CLAW — Glass Box</title>
<style>
:root{
  --bg:#05050f;--panel:#090914;--panel2:#0d0d1e;
  --border:#16163a;--border2:#1e1e40;
  --text:#b8b8d8;--dim:#404068;--dim2:#2a2a50;
  --green:#00e87a;--red:#ff3355;--amber:#ffaa00;
  --blue:#3388ff;--purple:#9944ff;--cyan:#00ccee;
  --mono:'JetBrains Mono','Fira Code','Courier New',monospace;
}
*{margin:0;padding:0;box-sizing:border-box;}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--mono);font-size:13px;}

/* TOP BAR */
#topbar{
  display:flex;align-items:center;gap:14px;
  padding:9px 20px;background:var(--panel);
  border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;
}
.logo{color:var(--cyan);font-size:15px;font-weight:bold;letter-spacing:3px;}
.badge{padding:2px 8px;border-radius:3px;font-size:11px;font-weight:bold;}
.b-demo{background:#0a0a28;color:var(--blue);border:1px solid #2244aa;}
.b-live{background:#1a0010;color:var(--red);border:1px solid var(--red);}
.b-run{background:#001a0a;color:var(--green);border:1px solid #006633;}
.b-pause{background:#1a0e00;color:var(--amber);border:1px solid #664400;}
.b-tf{background:#080820;color:#6688ff;border:1px solid #2244aa;}
#tb-right{margin-left:auto;display:flex;gap:16px;color:var(--dim);font-size:11px;align-items:center;}
.pulse{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);
  animation:pulse 2s infinite;margin-right:4px;}
@keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 5px var(--green);}50%{opacity:.3;box-shadow:none;}}

/* LAYOUT */
#main{padding:14px;display:flex;flex-direction:column;gap:16px;}
.sym-block{background:var(--panel);border:1px solid var(--border);border-radius:6px;overflow:hidden;}

/* SYMBOL HEADER */
.sym-hdr{
  display:flex;align-items:center;gap:10px;
  padding:9px 16px;background:var(--panel2);border-bottom:1px solid var(--border);
}
.sym-name{color:var(--cyan);font-size:14px;font-weight:bold;letter-spacing:1px;}
.sym-tf{color:var(--dim);font-size:11px;}
.sym-sess{margin-left:auto;padding:2px 8px;border-radius:3px;font-size:11px;
  background:#001624;color:var(--blue);}
.atr-hi{background:#1a0e00;color:var(--amber);}
.atr-lo{background:#001a0a;color:var(--green);}

/* 4-PANEL ROW */
.row4{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);}
.panel{background:var(--panel);padding:14px 16px;min-height:140px;}
.ptitle{color:var(--dim);font-size:10px;letter-spacing:2px;margin-bottom:10px;}

/* MARKET STATE */
.price{color:var(--text);font-size:21px;font-weight:bold;letter-spacing:.5px;margin-bottom:8px;}
.pmeta{color:var(--dim);font-size:11px;line-height:2.0;}
.up{color:var(--green);}.dn{color:var(--red);}.nu{color:var(--dim);}

/* CHAIN */
.vbadge{font-size:13px;font-weight:bold;padding:3px 8px;border-radius:3px;
  display:inline-block;margin-bottom:10px;}
.v-s4{background:#002a10;color:var(--green);}
.v-ct{background:#2a0010;color:var(--red);}
.v-lo{background:#1a1200;color:var(--amber);}
.v-rj{background:#10101a;color:var(--dim);}
.layer{display:flex;gap:8px;align-items:center;font-size:11px;color:var(--dim);margin:3px 0;}

/* CONFIDENCE */
.crow{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:12px;}
.clabel{width:38px;}
.ctrack{flex:1;background:var(--border);border-radius:2px;height:7px;overflow:hidden;}
.cbar{height:100%;border-radius:2px;transition:width .6s ease;}
.cbull{background:var(--green);}.cbear{background:var(--red);}
.cpct{width:34px;text-align:right;font-weight:bold;}
.ccomp{font-size:11px;color:var(--dim);display:flex;justify-content:space-between;margin:2px 0;}
.cval{color:var(--text);}

/* POSITION */
.pnone{color:var(--dim);font-style:italic;margin-top:6px;font-size:12px;}
.plong{color:var(--green);font-size:13px;font-weight:bold;margin-bottom:8px;}
.pshort{color:var(--red);font-size:13px;font-weight:bold;margin-bottom:8px;}
.prow{display:flex;justify-content:space-between;font-size:11px;color:var(--dim);margin:3px 0;}
.pval{color:var(--text);}
.pslval{color:var(--red);}
.ptpval{color:var(--green);}

/* REASONING */
.reason-wrap{padding:12px 16px;border-top:1px solid var(--border2);}
.rtitle{color:var(--purple);font-size:10px;letter-spacing:2px;margin-bottom:8px;}
.rtext{color:var(--text);font-size:12px;line-height:1.7;white-space:pre-wrap;
  max-height:110px;overflow-y:auto;}
.rempty{color:var(--dim);font-style:italic;font-size:12px;}

/* EPISODE STREAM */
.stream-wrap{padding:12px 16px;border-top:1px solid var(--border2);}
.stitle{color:var(--dim);font-size:10px;letter-spacing:2px;margin-bottom:8px;}
.ep{display:flex;gap:10px;align-items:baseline;
  padding:4px 0;border-bottom:1px solid var(--dim2);font-size:11px;}
.ets{color:var(--dim);min-width:40px;flex-shrink:0;}
.etype{min-width:155px;flex-shrink:0;font-weight:bold;}
.e-acc{color:var(--green);}.e-rej{color:var(--red);}
.e-bos{color:var(--blue);}.e-cho{color:var(--cyan);}
.e-sl{color:var(--red);}.e-tp{color:var(--green);}
.e-ses{color:var(--dim);}.e-oth{color:var(--amber);}
.esum{color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}

/* STATS BAR */
.sbar{
  display:flex;gap:20px;padding:9px 16px;
  background:#070710;border-top:1px solid var(--border);
  font-size:12px;flex-wrap:wrap;
}
.si{display:flex;gap:5px;}
.sl{color:var(--dim);}.sv{color:var(--text);font-weight:bold;}
.sg{color:var(--green);font-weight:bold;}
.sr{color:var(--red);font-weight:bold;}
.sa{color:var(--amber);font-weight:bold;}

/* NO DATA */
.nodata{color:var(--dim);font-style:italic;padding:30px;text-align:center;}

/* SCROLLBAR */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}
</style>
</head>
<body>

<div id="topbar">
  <span class="logo">▣ DEEP CLAW</span>
  <span id="mode" class="badge b-demo">DEMO</span>
  <span id="state" class="badge b-run"><span class="pulse"></span>RUNNING</span>
  <span id="xtf" class="badge b-tf">M5 EXEC</span>
  <div id="tb-right">
    <span>↑ <b id="uptime">—</b></span>
    <span>⬡ <b id="bars">0</b> bars</span>
    <span>⚡ <b id="openp">0</b> open</span>
    <span id="tick" style="color:var(--dim2)">—</span>
  </div>
</div>

<div id="main">
  <div id="syms"><div class="nodata">Connecting to Deep Claw…</div></div>
</div>

<script>
const VCLASS={SYNC4:'v-s4',COUNTER_TREND:'v-ct',LOCAL:'v-lo',REJECTED:'v-rj'};
const ECLASS={
  SIGNAL_ACCEPTED:'e-acc',SIGNAL_REJECTED:'e-rej',
  BOS_UP:'e-bos',BOS_DOWN:'e-bos',CHOCH_UP:'e-cho',CHOCH_DOWN:'e-cho',
  SL_HIT:'e-sl',TRADE_CLOSED:'e-tp',SESSION_CHANGE:'e-ses'
};

function arrow(v){
  if(!v)return'<span class="nu">—</span>';
  const u=v.toUpperCase();
  if(u.includes('BULL')||u==='UP')return'<span class="up">↑</span>';
  if(u.includes('BEAR')||u==='DOWN')return'<span class="dn">↓</span>';
  return'<span class="nu">→</span>';
}
function trendStr(v){
  if(!v)return'<span class="nu">—</span>';
  const u=v.toUpperCase();
  if(u.includes('BULL')||u==='UP')return`<span class="up">↑ ${v}</span>`;
  if(u.includes('BEAR')||u==='DOWN')return`<span class="dn">↓ ${v}</span>`;
  return`<span class="nu">${v}</span>`;
}
function bar(pct,cls){
  const w=Math.min(100,Math.max(0,pct||0));
  return`<div class="ctrack"><div class="cbar ${cls}" style="width:${w}%"></div></div>`;
}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function fmt(n,d=5){return(n||0).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}

function buildBlock(sym,d,execTf){
  const m=d.market||{},c=d.chain||{},cf=d.confidence||{};
  const pos=d.position,stats=d.stats||{},eps=d.episodes||[],rsn=d.reasoning||'';

  // Session badge
  const atrUp=(m.atr_regime||'').toUpperCase()==='HIGH';
  const atrDn=(m.atr_regime||'').toUpperCase()==='LOW';
  const sessClass=atrUp?'sym-sess atr-hi':atrDn?'sym-sess atr-lo':'sym-sess';

  // ── Panel 1: Market State ──
  const p1=`<div class="panel">
    <div class="ptitle">MARKET STATE</div>
    <div class="price">${m.close?fmt(m.close,2):'—'}</div>
    <div class="pmeta">
      ATR &nbsp;${m.atr_val?(m.atr_val).toFixed(3):'—'}<br>
      Regime &nbsp;${m.atr_regime||'—'}<br>
      Trend &nbsp;${trendStr(m.trend)}<br>
      <span style="color:var(--dim2)">${m.ts||''}</span>
    </div>
  </div>`;

  // ── Panel 2: Chain ──
  const vc=VCLASS[c.verdict]||'v-rj';
  const p2=`<div class="panel">
    <div class="ptitle">CHAIN VERDICT</div>
    <div class="vbadge ${vc}">${c.verdict||'—'}</div>
    <div style="margin-top:8px">
      <div class="layer">${arrow(c.sovereign)}<span style="color:var(--dim)">D &nbsp; Sovereign</span></div>
      <div class="layer">${arrow(c.anchor)}<span style="color:var(--dim)">H4 Anchor</span></div>
      <div class="layer">${arrow(c.filter_bias)}<span style="color:var(--dim)">H1 Filter</span></div>
      <div class="layer">${arrow(c.exec_bias)}<span style="color:var(--dim)">${execTf||'M5'} Exec</span></div>
    </div>
    ${c.causal_trace?`<div style="margin-top:8px;font-size:10px;color:var(--dim);line-height:1.6">${esc(c.causal_trace).substring(0,120)}</div>`:''}
  </div>`;

  // ── Panel 3: Confidence ──
  const bull=cf.bull||0, bear=cf.bear||0;
  const comps=cf.components||{};
  let compH='';
  Object.entries(comps).slice(0,5).forEach(([k,v])=>{
    compH+=`<div class="ccomp"><span>${k}</span><span class="cval">${(+v).toFixed(2)}</span></div>`;
  });
  const p3=`<div class="panel">
    <div class="ptitle">CONFIDENCE</div>
    <div class="crow">
      <span class="clabel up">BULL</span>${bar(bull,'cbull')}<span class="cpct up">${Math.round(bull)}%</span>
    </div>
    <div class="crow">
      <span class="clabel dn">BEAR</span>${bar(bear,'cbear')}<span class="cpct dn">${Math.round(bear)}%</span>
    </div>
    <div style="margin-top:8px">${compH}</div>
  </div>`;

  // ── Panel 4: Position ──
  let posH;
  if(pos){
    const isLong=(pos.direction||'').toUpperCase()==='LONG';
    posH=`<div class="${isLong?'plong':'pshort'}">${isLong?'▲ LONG':'▼ SHORT'}</div>
      <div class="prow"><span class="sl">Entry</span><span class="pval">${fmt(pos.entry)}</span></div>
      <div class="prow"><span class="sl">SL</span><span class="pslval">${fmt(pos.sl)}</span></div>
      <div class="prow"><span class="sl">TP1</span><span class="ptpval">${fmt(pos.tp1)}</span></div>
      <div class="prow"><span class="sl">Risk</span><span class="pval">$${(pos.size_usd||0).toFixed(2)}</span></div>
      <div style="margin-top:6px;font-size:10px;color:var(--dim)">${esc(pos.trade_id||'')}</div>`;
  } else {
    posH='<div class="pnone">No open position</div>';
  }
  const p4=`<div class="panel"><div class="ptitle">POSITION</div>${posH}</div>`;

  // ── Reasoning ──
  const reasonH=rsn
    ?`<div class="rtext">${esc(rsn)}</div>`
    :`<div class="rempty">Waiting for first signal evaluation…</div>`;

  // ── Episode stream ──
  let epH='';
  eps.slice(0,18).forEach(ep=>{
    const ec=ECLASS[ep.type]||'e-oth';
    epH+=`<div class="ep">
      <span class="ets">${ep.ts}</span>
      <span class="etype ${ec}">${ep.type}</span>
      <span class="esum">${esc(ep.summary)}</span>
    </div>`;
  });
  if(!epH)epH='<div class="ep"><span class="nu">Waiting for bar closes…</span></div>';

  // ── Stats bar ──
  const nr=stats.net_r||0;
  const nrc=nr>0?'sg':nr<0?'sr':'sv';
  const pf=stats.profit_factor;
  const pfStr=pf===Infinity||pf>999?'∞':(pf||0).toFixed(2);
  const sbarH=`<div class="sbar">
    <div class="si"><span class="sl">Fired</span><span class="sv">${stats.signals_fired||0}</span></div>
    <div class="si"><span class="sl">Blocked</span><span class="sv">${stats.signals_blocked||0}</span></div>
    <div class="si"><span class="sl">TP</span><span class="sg">${stats.tp_hits||0}</span></div>
    <div class="si"><span class="sl">SL</span><span class="sr">${stats.sl_hits||0}</span></div>
    <div class="si"><span class="sl">WR</span><span class="sv">${(stats.win_rate||0).toFixed(0)}%</span></div>
    <div class="si"><span class="sl">Net&nbsp;R</span><span class="${nrc}">${nr>0?'+':''}${nr.toFixed(2)}R</span></div>
    <div class="si"><span class="sl">PF</span><span class="sa">${pfStr}</span></div>
    <div class="si"><span class="sl">London</span><span class="sv">${stats.london||0}</span></div>
    <div class="si"><span class="sl">NY</span><span class="sv">${stats.ny||0}</span></div>
  </div>`;

  return`<div class="sym-block" id="sb-${sym}">
    <div class="sym-hdr">
      <span class="sym-name">${sym}</span>
      <span class="sym-tf">exec: ${execTf||'M5'}</span>
      <span class="${sessClass}">${m.session||'—'} · ATR ${m.atr_regime||'—'}</span>
    </div>
    <div class="row4">${p1}${p2}${p3}${p4}</div>
    <div class="reason-wrap">
      <div class="rtitle">🧠 CLAUDE REASONING</div>
      ${reasonH}
    </div>
    <div class="stream-wrap">
      <div class="stitle">EPISODE STREAM</div>
      ${epH}
    </div>
    ${sbarH}
  </div>`;
}

function render(state){
  const sys=state.system||{};
  const xtf=state.exec_tf||'M5';

  // top bar
  const stEl=document.getElementById('state');
  if(sys.paused){
    stEl.className='badge b-pause';stEl.innerHTML='⏸ PAUSED';
  } else {
    stEl.className='badge b-run';stEl.innerHTML='<span class="pulse"></span>RUNNING';
  }
  document.getElementById('xtf').textContent=xtf+' EXEC';
  document.getElementById('uptime').textContent=sys.uptime||'—';
  document.getElementById('bars').textContent=sys.bars_processed||0;
  document.getElementById('openp').textContent=sys.open_positions||0;
  document.getElementById('tick').textContent=new Date().toLocaleTimeString();

  const syms=state.symbols||{};
  const container=document.getElementById('syms');
  if(!Object.keys(syms).length){
    container.innerHTML='<div class="nodata">No symbols active — waiting for first bar close</div>';
    return;
  }
  // Clear "connecting" placeholder on first real data
  const nd=container.querySelector('.nodata');
  if(nd)nd.remove();

  for(const[sym,d]of Object.entries(syms)){
    const html=buildBlock(sym,d,xtf);
    const existing=document.getElementById(`sb-${sym}`);
    if(existing){
      // replace in-place to avoid scroll jump
      const tmp=document.createElement('div');
      tmp.innerHTML=html;
      existing.replaceWith(tmp.firstElementChild);
    } else {
      container.insertAdjacentHTML('beforeend',html);
    }
  }
}

// SSE with auto-reconnect
let delay=2000;
function connect(){
  const es=new EventSource('/api/stream');
  es.onmessage=e=>{
    try{render(JSON.parse(e.data));delay=2000;}
    catch(err){console.warn(err);}
  };
  es.onerror=()=>{
    es.close();
    document.getElementById('tick').textContent='reconnecting…';
    setTimeout(connect,delay);
    delay=Math.min(delay*2,30000);
  };
}
connect();
</script>
</body>
</html>"""


# ── FastAPI app ───────────────────────────────────────────────────────────────

def build_app(orchestrator: Any) -> Any:
    """
    Build the glass box dashboard app.
    Accepts the Orchestrator instance — all data pulled from it via get_dashboard_state().
    """
    if not _FASTAPI_AVAILABLE:
        raise RuntimeError("pip install 'fastapi>=0.111' 'uvicorn[standard]>=0.29'")

    app = FastAPI(title="Deep Claw Glass Box", version="2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse(content=_HTML)

    @app.get("/api/stream")
    async def sse_stream(request: Request):
        async def gen():
            while True:
                if await request.is_disconnected():
                    break
                try:
                    state = orchestrator.get_dashboard_state()
                    payload = json.dumps(state, default=str)
                    yield f"data: {payload}\n\n"
                except Exception as exc:
                    log.warning("Dashboard state error: %s", exc)
                    yield "data: {}\n\n"
                await asyncio.sleep(2)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/state")
    async def snapshot():
        return orchestrator.get_dashboard_state()

    @app.get("/health")
    async def health():
        return {"status": "ok", **orchestrator.get_status()}

    return app
