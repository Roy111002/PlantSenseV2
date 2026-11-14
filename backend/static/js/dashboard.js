const $ = (id) => document.getElementById(id);
const state = { history: [], latest: null, refreshMs: 10000, timer: null };
const metrics = [
  {key:"temperature_c", label:"Temperature", icon:"♨", unit:"°C", digits:1},
  {key:"humidity_pct", label:"Humidity", icon:"◌", unit:"%", digits:1},
  {key:"soil_moisture_pct", label:"Soil moisture", icon:"♧", unit:"%", digits:1},
  {key:"light_lux", label:"Light intensity", icon:"☼", unit:"lux", digits:0}
];
function deviceId(){ return ($("deviceId").value.trim() || "plantsense-01"); }
function fmtTime(value){
  if(!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString([], {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
}
function ageLabel(value){
  if(!value) return "No timestamp";
  const ms = Date.now() - new Date(value).getTime();
  if(!Number.isFinite(ms) || ms < 0) return fmtTime(value);
  const mins = Math.floor(ms/60000);
  if(mins < 1) return "Just now";
  if(mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins/60);
  if(hrs < 24) return `${hrs} hr ago`;
  return `${Math.floor(hrs/24)} day(s) ago`;
}
async function getJSON(url){
  const res = await fetch(url, {cache:"no-store"});
  if(!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}
function setConnection(ok, message){
  $("connection").classList.toggle("offline", !ok);
  $("connectionText").textContent = message;
}
function renderMetrics(telemetry){
  const container = $("metrics");
  const data = telemetry?.sensor_data || {};
  const timestamp = telemetry?.created_at;
  const age = timestamp ? Date.now() - new Date(timestamp).getTime() : Infinity;
  const stale = age > 2 * 60 * 1000;
  const cards = metrics.filter(m => data[m.key] !== undefined && data[m.key] !== null);
  if(!cards.length){
    container.innerHTML = '<div class="empty-state">No sensor readings are available yet. Connect a sensor and wait for the next device update.</div>';
    return;
  }
  container.innerHTML = cards.map(m => metricCard(m, data[m.key], timestamp, stale)).join("");
}
function metricCard(m, value, timestamp, stale){
  const n = Number(value);
  const shown = Number.isFinite(n) ? n.toFixed(m.digits) : String(value);
  return `<article class="metric-card"><div class="metric-top"><span>${m.label}</span><span class="metric-icon">${m.icon}</span></div><div class="metric-value">${shown}<span class="metric-unit"> ${m.unit}</span></div><div class="metric-time">${stale ? "STALE · " : ""}${ageLabel(timestamp)}</div></article>`;
}
function statePill(id, value){
  const v = String(value || "UNKNOWN").toUpperCase();
  const on = ["ON","RUNNING","ACTIVE","1","TRUE"].includes(v);
  const off = ["OFF","STOPPED","INACTIVE","0","FALSE"].includes(v);
  const el = $(id);
  el.textContent = on ? "ON" : off ? "OFF" : "Unknown";
  el.className = `state-pill ${on ? "on" : off ? "off" : "unknown"}`;
}
function unwrapAnalysis(latest){
  const root = latest?.result?.analysis || {};
  return root.vlm || root.classifier || root;
}
function toArray(v){ return Array.isArray(v) ? v : (v ? [v] : []); }
function renderDiagnosis(latest){
  const result = latest?.result;
  if(!result){ $("diagnosisContent").innerHTML = '<div class="empty-diagnosis">Plant analysis will appear here after the first image is processed.</div>'; $("aiStatus").textContent="NOT RUN"; $("aiStatus").className="ai-status"; return; }
  $("analysisTimestamp").textContent = `Analysis received ${fmtTime(latest.created_at)}`;
  const status = String(latest.ai_status || "unknown").toLowerCase();
  $("aiStatus").textContent = status.replaceAll("_"," ").toUpperCase();
  $("aiStatus").className = `ai-status ${status === "completed" ? "done" : ""}`;
  const a = unwrapAnalysis(latest);
  if(!a || typeof a !== "object"){
    $("diagnosisContent").innerHTML = `<div class="empty-diagnosis">${escapeHTML(String(a || "No structured diagnosis returned."))}</div>`;
    return;
  }
  const diagnosis = a.diagnosis || a.prediction || a.disease || a.condition || a.label || a.status || "Analysis received";
  const summary = a.summary || a.explanation || a.description || a.reasoning || a.message || "";
  const symptoms = toArray(a.symptoms || a.visible_symptoms || a.observations || a.findings);
  const recs = toArray(a.recommendations || a.recommendation || a.actions || a.treatment);
  const confidence = a.confidence ?? a.confidence_score;
  const confidenceHTML = confidence !== undefined ? `<div class="confidence">Confidence: ${escapeHTML(String(confidence))}</div>` : "";
  const symptomsHTML = symptoms.length ? `<strong>Observed signs</strong><ul class="insight-list">${symptoms.map(x=>`<li>${escapeHTML(typeof x==="string"?x:JSON.stringify(x))}</li>`).join("")}</ul>` : "";
  const recHTML = recs.length ? `<div class="recommendation"><strong>Suggested next steps</strong>${recs.map(x=>`<div>• ${escapeHTML(typeof x==="string"?x:JSON.stringify(x))}</div>`).join("")}</div>` : "";
  $("diagnosisContent").innerHTML = `<div class="diagnosis-title">${escapeHTML(String(diagnosis))}</div>${confidenceHTML}<p class="diagnosis-summary">${escapeHTML(String(summary))}</p>${symptomsHTML}${recHTML}<p class="metric-time">AI output is advisory and may be uncertain. Confirm with visual inspection.</p>`;
}
function escapeHTML(s){
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function renderImage(device){
  const wrap = $("plantImageWrap");
  const url = `/api/plant/latest-image?device_id=${encodeURIComponent(device)}&t=${Date.now()}`;
  const img = new Image();
  img.onload = () => { wrap.innerHTML=""; img.alt="Latest plant image"; wrap.appendChild(img); };
  img.onerror = () => { wrap.innerHTML='<div class="image-placeholder"><span>✿</span><strong>No plant image available</strong><small>The latest ESP32-CAM image will appear here.</small></div>'; };
  img.src = url;
}
function drawChart(){
  const canvas = $("historyChart"), ctx = canvas.getContext("2d");
  const key = $("historyMetric").value;
  const meta = metrics.find(m=>m.key===key);
  $("chartUnit").textContent = meta?.unit || "";
  const rows = [...state.history].reverse().filter(r => r[key] !== undefined && r[key] !== null && Number.isFinite(Number(r[key])));
  const empty = $("chartEmpty");
  const rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width*dpr));
  canvas.height = Math.max(1, Math.floor(rect.height*dpr));
  ctx.scale(dpr,dpr);
  const w=rect.width,h=rect.height,p={l:38,r:10,t:12,b:25};
  ctx.clearRect(0,0,w,h);
  if(rows.length<2){ empty.style.display="grid"; return; }
  empty.style.display="none";
  const vals=rows.map(r=>Number(r[key]));
  let min=Math.min(...vals), max=Math.max(...vals);
  if(min===max){min-=1;max+=1;}
  const pad=(max-min)*.15; min-=pad; max+=pad;
  const x=i=>p.l+(w-p.l-p.r)*(i/(rows.length-1));
  const y=v=>p.t+(h-p.t-p.b)*(1-(v-min)/(max-min));
  ctx.font='10px DM Sans, sans-serif'; ctx.fillStyle="#9aa69e";ctx.strokeStyle="#edf1ed";ctx.lineWidth=1;
  for(let i=0;i<4;i++){const yy=p.t+(h-p.t-p.b)*i/3;ctx.beginPath();ctx.moveTo(p.l,yy);ctx.lineTo(w-p.r,yy);ctx.stroke();const v=max-(max-min)*i/3;ctx.fillText(v.toFixed(meta?.digits ?? 0),2,yy+3);}
  ctx.beginPath(); rows.forEach((r,i)=>i?ctx.lineTo(x(i),y(Number(r[key]))):ctx.moveTo(x(i),y(Number(r[key]))));
  ctx.strokeStyle="#39845a";ctx.lineWidth=2.3;ctx.lineJoin="round";ctx.stroke();
  const last=rows[rows.length-1];ctx.beginPath();ctx.arc(x(rows.length-1),y(Number(last[key])),4,0,Math.PI*2);ctx.fillStyle="#39845a";ctx.fill();
  ctx.fillStyle="#9aa69e";ctx.fillText(fmtTime(rows[0].created_at),p.l,h-5);
  const label=fmtTime(last.created_at);ctx.fillText(label,Math.max(p.l,w-p.r-ctx.measureText(label).width),h-5);
}
async function refresh(){
  const device=deviceId();
  try{
    const [health, history, telemetry] = await Promise.all([
      getJSON("/api/health"),
      getJSON(`/api/plant/history?device_id=${encodeURIComponent(device)}&limit=50`),
      getJSON(`/api/plant/latest-data?device_id=${encodeURIComponent(device)}`).catch(e => {
        if(e.message.startsWith("404")) return null;
        throw e;
      })
    ]);
    state.history = history.items || [];
    let latest = null;
    try { latest = await getJSON(`/api/plant/latest?device_id=${encodeURIComponent(device)}`); }
    catch(e){ if(e.message.startsWith("404")) latest=null; else throw e; }
    state.latest = latest;
    setConnection(true, "API connected");
    const stamp = telemetry?.created_at;
    $("lastUpdated").textContent = ageLabel(stamp);
    renderMetrics(telemetry);
    const act = telemetry?.actuator_state || {};
    statePill("pumpState",act.pump);
    statePill("lightState",act.grow_light);
    const stale = !stamp || Date.now()-new Date(stamp).getTime()>2*60*1000;
    for(const id of ["pumpState","lightState"]){
      $(id).textContent += stale ? " (stale)" : "";
      $(id).title = stale ? "No recent device report; this is not a live output state." : "Reported GPIO output level";
    }
    renderDiagnosis(latest);
    renderImage(device);
    drawChart();
  }catch(e){
    setConnection(false,"API unavailable");
    $("lastUpdated").textContent="—";
    if(!state.history.length) $("metrics").innerHTML='<div class="empty-state">Cannot load dashboard data. Check that the Flask backend is running.</div>';
  }
}
$("historyMetric").addEventListener("change",drawChart);
$("deviceId").addEventListener("change",refresh);
window.addEventListener("resize",drawChart);
refresh();
state.timer=setInterval(refresh,state.refreshMs);
