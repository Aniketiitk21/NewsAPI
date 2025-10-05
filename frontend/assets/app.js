/* ------------------ helpers & constants ------------------ */
const API = (p, params={}) => {
  const base = ""; // same-origin
  const q = new URLSearchParams(params);
  return `${base}${p}${q.toString() ? "?" + q.toString() : ""}`;
};
const STATES = ["Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal","Delhi","Jammu and Kashmir","Ladakh","Puducherry","Chandigarh"];
const capitalize = s => s ? s[0].toUpperCase()+s.slice(1) : s;

/* ------------------ login gate ------------------ */
const LOGIN_USER = "sandhanar21";
const LOGIN_PASS = "Bharat@1947";
function showLogin(show){
  document.getElementById("login-overlay").classList.toggle("hidden", !show);
}
(function bootLogin(){
  const token = localStorage.getItem("nl_token");
  if(!token){ showLogin(true); }
  document.getElementById("lg-btn").onclick = ()=>{
    const u = document.getElementById("lg-user").value.trim();
    const p = document.getElementById("lg-pass").value;
    if(u===LOGIN_USER && p===LOGIN_PASS){
      localStorage.setItem("nl_token", String(Date.now()));
      showLogin(false);
    }else{
      document.getElementById("lg-msg").textContent = "Invalid credentials";
    }
  };
})();

/* ------------------ tabs/nav ------------------ */
const tabs = document.querySelectorAll(".tab");
const views = document.querySelectorAll(".view");
function setActiveTab(name){
  tabs.forEach(t=>t.classList.toggle("active", t.dataset.tab===name));
  views.forEach(v=>v.classList.toggle("active", v.id===name));
}
tabs.forEach(t=>{
  t.addEventListener("click", ()=>{
    setActiveTab(t.dataset.tab);
    if(t.dataset.tab==="home"){ loadTop5(); }
    if(t.dataset.tab==="digest"){ renderFollowChips(); loadDigest(); }
    if(t.dataset.tab==="habits"){ refreshHabitSelect(); renderHabitsUI(); }
    if(t.dataset.tab==="finance"){ loadCurated("finance","grid-fin","empty-fin"); }
    if(t.dataset.tab==="startup"){ loadCurated("startup","grid-biz","empty-biz"); }
    if(t.dataset.tab==="ai"){ loadCurated("ai","grid-ai","empty-ai"); }
  });
});

/* ------------------ HOME: top5 ------------------ */
const signalsRow = document.getElementById("signals");
function showSkeletonRow(el, n=5){
  el.innerHTML="";
  for(let i=0;i<n;i++){
    const d=document.createElement("div");
    d.className="signal-card skel";
    d.innerHTML=`<div class="bar w"></div><div class="bar w2"></div><div class="bar w3"></div>`;
    el.appendChild(d);
  }
}
async function loadTop5(){
  if(!signalsRow) return;
  showSkeletonRow(signalsRow, 5);
  try{
    const res = await fetch(API("/api/signals/top5",{days:"2"}));
    const data = await res.json();
    signalsRow.innerHTML="";
    (data.items||[]).forEach(it=>{
      const div=document.createElement("div");
      const date = it.published_at ? new Date(it.published_at).toLocaleString() : "—";
      const chips = [
        it.category && it.category!=="all" ? `<span class="chip">${it.category}</span>` : "",
        it.source ? `<span class="chip">${it.source}</span>` : ""
      ].join(" ");
      div.className="signal-card";
      div.innerHTML=`
        <h3>${it.title||"(untitled)"}</h3>
        <div class="chips">${chips}</div>
        <p>${it.summary||""}</p>
        <div class="row-ends">
          <small class="muted">${date}</small>
          <a class="btn" href="${it.url}" target="_blank" rel="noopener">Open</a>
        </div>`;
      signalsRow.appendChild(div);
    });
  }catch{
    signalsRow.innerHTML = `<div class="empty">Failed to load signals.</div>`;
  }
}

/* ------------------ Global search ------------------ */
const qInput = document.getElementById("q");
const qBtn = document.getElementById("qbtn");
qBtn?.addEventListener("click", doSearch);
qInput?.addEventListener("keydown", e=>{ if(e.key==="Enter") doSearch(); });
async function doSearch(){
  const q = (qInput.value||"").trim();
  if(!q) return;
  setActiveTab("feed");
  scopeSel.value="national"; catSel.value=""; daysSel.value="7"; setStepEnabled(5); updateHeadline();
  grid.innerHTML=""; showSkeleton(grid, 9);
  try{
    const res = await fetch(API("/api/search",{q,days:"7"}));
    const data = await res.json();
    renderItemsToGrid(data.items||[], grid, empty);
    headline.textContent = `Results for “${q}”`;
  }catch{
    grid.innerHTML=""; empty.style.display="block"; empty.textContent="Search failed.";
  }
}

/* ------------------ DIGEST ------------------ */
const digestGrid = document.getElementById("digest-grid");
const digestEmpty = document.getElementById("digest-empty");
const followInput = document.getElementById("follow-input");
const followAdd = document.getElementById("follow-add");
const followChips = document.getElementById("follow-chips");
const FOLLOW_KEY = "nl_follow_terms";
const getFollows = ()=>{ try{const x=JSON.parse(localStorage.getItem(FOLLOW_KEY)||"[]");return Array.isArray(x)?x:[];}catch{return[];} };
const saveFollows = a => { localStorage.setItem(FOLLOW_KEY, JSON.stringify(a)); renderFollowChips(); };
function renderFollowChips(){
  const arr=getFollows(); followChips.innerHTML="";
  if(arr.length===0){ followChips.innerHTML=`<span class="muted">No terms followed yet.</span>`; return; }
  arr.forEach(t=>{
    const s=document.createElement("span"); s.className="chip removable"; s.innerHTML=`${t} <b>&times;</b>`;
    s.querySelector("b").onclick=()=>{ saveFollows(getFollows().filter(x=>x!==t)); loadDigest(); };
    followChips.appendChild(s);
  });
}
async function loadDigest(){
  digestGrid.innerHTML=""; showSkeleton(digestGrid,6);
  const terms=getFollows();
  try{
    const res=await fetch(API("/api/digest",{follow:terms.join(","),days:"2"}));
    const data=await res.json();
    renderItemsToGrid(data.items||[], digestGrid, digestEmpty);
  }catch{ digestGrid.innerHTML=`<div class="empty">Digest error.</div>`; }
}
followAdd?.addEventListener("click", ()=>{
  const t=(followInput.value||"").trim(); if(!t) return;
  const cur=getFollows(); if(!cur.includes(t)) cur.push(t);
  saveFollows(cur); followInput.value=""; loadDigest();
});

/* ------------------ FEED (kept) ------------------ */
const scopeSel=document.getElementById("scope");
const stateSel=document.getElementById("state");
const catSel=document.getElementById("category");
const daysSel=document.getElementById("days");
const modeSel=document.getElementById("mode");
const refreshBtn=document.getElementById("refresh");
const grid=document.getElementById("grid");
const empty=document.getElementById("empty");
const headline=document.getElementById("headline");

function populateStates(){ stateSel.innerHTML=""; STATES.forEach(s=>{ const o=document.createElement("option"); o.value=s; o.textContent=s; stateSel.appendChild(o); }); }
function setStepEnabled(step){
  scopeSel.disabled= step<2;
  stateSel.disabled= !(step>=3 && scopeSel.value==="state");
  catSel.disabled  = step<4; modeSel.disabled= step<5; refreshBtn.disabled= step<5;
}
function updateHeadline(){
  const sc=scopeSel.value; const cat=catSel.value||"All";
  const days = daysSel.value ? `${daysSel.options[daysSel.selectedIndex].text}` : "Pick timeline";
  if(!daysSel.value){ headline.textContent="Pick a timeline to start"; return; }
  headline.textContent = sc==="national" ? `Top ${capitalize(cat)} News — ${days}` : `${stateSel.value} — ${capitalize(cat)} News — ${days}`;
}
function showSkeleton(el,n=8){ el.innerHTML=""; empty.style.display="none"; for(let i=0;i<n;i++){ const d=document.createElement("div"); d.className="skel"; d.innerHTML=`<div class="bar w"></div><div class="bar w2"></div><div class="bar w3"></div><div class="bar w2"></div>`; el.appendChild(d); } }
async function fetchNews(){
  if(!daysSel.value) return; updateHeadline(); showSkeleton(grid,9);
  const scope=scopeSel.value; const state= scope==="state"? stateSel.value : ""; const category=catSel.value;
  const params={scope,days:daysSel.value,limit:"60",fetch_mode:(modeSel.value||"light")};
  if(state) params.state=state; if(category) params.category=category;
  try{
    const res=await fetch(API("/api/news",params)); if(!res.ok) throw 0; const data=await res.json();
    renderItemsToGrid(data.items||[], grid, empty);
  }catch{ grid.innerHTML=""; empty.style.display="block"; empty.textContent="Failed to load news."; }
}
function renderItemsToGrid(items, targetGrid, targetEmpty){
  targetGrid.innerHTML="";
  if(!items || items.length===0){ targetEmpty.style.display="block"; targetEmpty.textContent="No news found for your filters."; return; }
  targetEmpty.style.display="none";
  items.forEach(it=>{
    const d=document.createElement("div"); d.className="card";
    const chips=[]; if(it.category && it.category!=="all") chips.push(`<span class="chip">${it.category}</span>`); if(it.state) chips.push(`<span class="chip">${it.state}</span>`); if(it.source) chips.push(`<span class="chip">${it.source}</span>`);
    const date= it.published_at? new Date(it.published_at).toLocaleString() : "—";
    d.innerHTML = `
      <h3><a href="${it.url}" target="_blank" rel="noopener">${it.title || "(untitled)"}</a></h3>
      <div class="chips">${chips.join(" ")}</div>
      <p>${it.summary || ""}</p>
      <div class="meta muted">${date}</div>`;
    targetGrid.appendChild(d);
  });
}
daysSel?.addEventListener("change", ()=>{ setStepEnabled(daysSel.value?2:1); updateHeadline(); if(daysSel.value) fetchNews(); });
scopeSel?.addEventListener("change", ()=>{ setStepEnabled(scopeSel.value==="state"?3:4); if(scopeSel.value!=="state") fetchNews(); });
stateSel?.addEventListener("change", ()=>{ setStepEnabled(4); fetchNews(); });
catSel?.addEventListener("change", ()=>{ setStepEnabled(5); fetchNews(); });
modeSel?.addEventListener("change", fetchNews);
refreshBtn?.addEventListener("click", fetchNews);

/* ------------------ HABITS (incl Shloka) ------------------ */
const HAB_KEY="nl_habits";
const $ = id => document.getElementById(id);

const habitNameEl=$("habit-name"), habitColorEl=$("habit-color"), habitAddBtn=$("habit-add");
const habitSelect=$("habit-select"), habitGoalEl=$("habit-goal");
const habitRemTime=$("habit-rem-time"), habitRemToggle=$("habit-rem-toggle");
const habitRenameBtn=$("habit-rename"), habitDeleteBtn=$("habit-delete");

const statCurrent=$("stat-current"), statBest=$("stat-best"), statWeek=$("stat-week");
const ring=$("goal-ring"), ringVal=$("ring-val");

const calTitle=$("cal-title"), calGrid=$("cal-grid"), calPrev=$("cal-prev"), calNext=$("cal-next");
const chartCanvas=$("habit-chart"); const ctx=chartCanvas.getContext("2d");

let calCursor = new Date();

function loadHabits(){ try{const x=JSON.parse(localStorage.getItem(HAB_KEY)||"[]"); return Array.isArray(x)?x:[];}catch{return[];} }
function saveHabits(a){ localStorage.setItem(HAB_KEY, JSON.stringify(a)); }
function uid(){ return Math.random().toString(36).slice(2,9); }
function refreshHabitSelect(){
  const arr=loadHabits();
  habitSelect.innerHTML="";
  arr.forEach(h=>{ const o=document.createElement("option"); o.value=h.id; o.textContent=h.name; habitSelect.appendChild(o); });
}
function ensureHabitSelected(){
  const arr=loadHabits(); if(arr.length===0) return null;
  if(!habitSelect.value) habitSelect.value=arr[0].id;
  return arr.find(h=>h.id===habitSelect.value) || arr[0];
}

/* Shloka from backend (authentic source proxy) */
async function renderShloka(){
  try{
    const r = await fetch(API("/api/shloka/daily"));
    const s = await r.json();
    $("sh-ref").textContent = `Gita ${s.ref || ""}`;
    $("sh-dev").textContent = s.dev || "";
    $("sh-trans").textContent = s.tr || "";
  }catch{
    $("sh-ref").textContent = "Gita";
    $("sh-dev").textContent = "—";
    $("sh-trans").textContent = "—";
  }
}

/* Habit CRUD */
habitAddBtn?.addEventListener("click", ()=>{
  const name=(habitNameEl.value||"").trim(); if(!name) return;
  const color=habitColorEl.value||"#7c3aed";
  const arr=loadHabits(); arr.push({id:uid(), name, color, goal:5, remTime:null, remOn:false, history:{}});
  saveHabits(arr); habitNameEl.value=""; refreshHabitSelect(); renderHabitsUI();
});
habitRenameBtn?.addEventListener("click", ()=>{
  const arr=loadHabits(); if(arr.length===0) return;
  const h=ensureHabitSelected(); if(!h) return;
  const next = prompt("New name", h.name); if(!next) return;
  h.name = next; saveHabits(arr); refreshHabitSelect(); habitSelect.value=h.id; renderHabitsUI();
});
habitDeleteBtn?.addEventListener("click", ()=>{
  const arr=loadHabits(); if(arr.length===0) return;
  const h=ensureHabitSelected(); if(!h) return;
  if(!confirm(`Delete habit “${h.name}”?`)) return;
  saveHabits(arr.filter(x=>x.id!==h.id)); refreshHabitSelect(); renderHabitsUI();
});
habitSelect?.addEventListener("change", renderHabitsUI);

habitGoalEl?.addEventListener("change", ()=>{
  let v=Number(habitGoalEl.value||5); v=Math.min(7, Math.max(1,v));
  const arr=loadHabits(); const h=ensureHabitSelected(); if(!h) return;
  h.goal=v; saveHabits(arr); renderHabitsUI();
});

/* Reminder */
habitRemToggle?.addEventListener("click", async ()=>{
  const arr=loadHabits(); const h=ensureHabitSelected(); if(!h) return;
  const t = habitRemTime.value;
  if(!h.remOn){
    if(Notification && Notification.permission!=="granted"){ await Notification.requestPermission(); }
    h.remTime = t || "20:00"; h.remOn = true;
  }else{ h.remOn = false; }
  saveHabits(arr); renderHabitsUI();
});
setInterval(()=>{
  const arr=loadHabits();
  const now = new Date();
  const hh = String(now.getHours()).padStart(2,"0");
  const mm = String(now.getMinutes()).padStart(2,"0");
  const cur = `${hh}:${mm}`;
  arr.forEach(h=>{
    if(h.remOn && h.remTime===cur){
      try{ new Notification("Habit reminder", { body:`${h.name} — time to check in!` }); }catch{}
    }
  });
}, 60*1000);

/* Calendar + stats */
function renderHabitsUI(){
  renderShloka();

  const arr=loadHabits();
  if(arr.length===0){
    calTitle.textContent="Create a habit to start";
    calGrid.innerHTML = `<div class="empty">No habits yet. Add one above.</div>`;
    statCurrent.textContent="0"; statBest.textContent="0"; statWeek.textContent="0/7"; updateRing(0); drawChart([]);
    return;
  }
  const h=ensureHabitSelected(); if(!h) return;
  habitGoalEl.value = h.goal||5;
  habitRemTime.value = h.remTime||"";
  habitRemToggle.textContent = h.remOn ? "Disable" : "Enable";

  renderCalendar(h);
  const stats = computeStats(h);
  statCurrent.textContent=String(stats.currentStreak);
  statBest.textContent=String(stats.bestStreak);
  statWeek.textContent=`${stats.thisWeek}/${h.goal||5}`;
  const pct = Math.min(100, Math.round((stats.thisWeek / (h.goal||5))*100));
  updateRing(pct); drawChart(stats.weekly);
}
function renderCalendar(h){
  const y=calCursor.getFullYear(), m=calCursor.getMonth();
  const first=new Date(y,m,1), last=new Date(y,m+1,0);
  const start=((first.getDay()+6)%7); const days=last.getDate();
  calTitle.textContent = `${first.toLocaleString("default",{month:"long"})} ${y}`;
  calGrid.innerHTML = `
    <div class="cal-wd">Mon</div><div class="cal-wd">Tue</div><div class="cal-wd">Wed</div>
    <div class="cal-wd">Thu</div><div class="cal-wd">Fri</div><div class="cal-wd">Sat</div><div class="cal-wd">Sun</div>
  `;
  for(let i=0;i<start;i++){ const pad=document.createElement("div"); pad.className="cal-cell pad"; calGrid.appendChild(pad); }
  for(let d=1; d<=days; d++){
    const date=new Date(y,m,d), key=date.toISOString().slice(0,10);
    const cell=document.createElement("button"); cell.className="cal-cell day";
    cell.innerHTML=`<span class="num">${d}</span>`;
    if(h.history && h.history[key]) cell.classList.add("done");
    cell.onclick=()=>{
      const arr=loadHabits(); const me=arr.find(x=>x.id===h.id);
      if(!me.history) me.history={}; me.history[key]=!me.history[key];
      saveHabits(arr); renderHabitsUI();
    };
    calGrid.appendChild(cell);
  }
}
function computeStats(h){
  const today=new Date(); today.setHours(0,0,0,0);
  let streak=0; const p=new Date(today);
  while(true){ const k=p.toISOString().slice(0,10); if(h.history&&h.history[k]){ streak++; p.setDate(p.getDate()-1);} else break; }
  let best=0, cur=0; const back=new Date(today); back.setDate(back.getDate()-180);
  for(let d=new Date(back); d<=today; d.setDate(d.getDate()+1)){ const k=d.toISOString().slice(0,10); if(h.history&&h.history[k]){cur++;best=Math.max(best,cur);} else cur=0; }
  const dow=(today.getDay()+6)%7; const mon=new Date(today); mon.setDate(today.getDate()-dow);
  let w=0; for(let d=new Date(mon); d<=today; d.setDate(d.getDate()+1)){ const k=d.toISOString().slice(0,10); if(h.history&&h.history[k]) w++; }
  const weekly=[]; const end=new Date(today);
  for(let i=7;i>=0;i--){ const start=new Date(end); start.setDate(end.getDate() - (i*7 + 6)); const stop=new Date(end); stop.setDate(end.getDate() - (i*7)); let c=0; for(let d=new Date(start); d<=stop; d.setDate(d.getDate()+1)){ if(h.history&&h.history[d.toISOString().slice(0,10)]) c++; } weekly.push(c); }
  return { currentStreak:streak, bestStreak:best, thisWeek:w, weekly };
}
function updateRing(pct){
  const C=2*Math.PI*16;
  ring.style.strokeDasharray = `${C}`;
  ring.style.strokeDashoffset = `${C*(1-pct/100)}`;
  ringVal.textContent = `${pct}%`;
}
function drawChart(weekly){
  const W=chartCanvas.width=chartCanvas.clientWidth; const H=chartCanvas.height=120;
  ctx.clearRect(0,0,W,H); if(!weekly || weekly.length===0) return;
  const max=Math.max(...weekly,7), stepX=W/(weekly.length-1), scaleY=(H-20)/max;
  ctx.lineWidth=2; ctx.strokeStyle="#7c3aed"; ctx.beginPath();
  weekly.forEach((v,i)=>{ const x=i*stepX, y=H-10-v*scaleY; if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); }); ctx.stroke();
  ctx.strokeStyle="#1f2937"; ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(0,H-10); ctx.lineTo(W,H-10); ctx.stroke();
  ctx.fillStyle="#7c3aed"; weekly.forEach((v,i)=>{ const x=i*stepX, y=H-10-v*scaleY; ctx.beginPath(); ctx.arc(x,y,3,0,Math.PI*2); ctx.fill(); });
}

/* Exporters */
document.getElementById("csv-export")?.addEventListener("click", ()=>{
  const arr=loadHabits(); const rows=[["habit_id","habit_name","date","done"]];
  arr.forEach(h=>{ Object.keys(h.history||{}).forEach(k=>{ rows.push([h.id,h.name,k,String(!!h.history[k])]); }); });
  const csv = rows.map(r=>r.map(x=>`"${String(x).replace(/"/g,'""')}"`).join(",")).join("\n");
  const blob=new Blob([csv],{type:"text/csv"}); const url=URL.createObjectURL(blob);
  const a=document.createElement("a"); a.href=url; a.download="habits.csv"; a.click(); URL.revokeObjectURL(url);
});
document.getElementById("ics-export")?.addEventListener("click", ()=>{
  const h=ensureHabitSelected(); if(!h){ alert("Add a habit first"); return; }
  const tm=h.remTime||"20:00"; const [hh,mm]=tm.split(":").map(Number);
  const lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//NewsLens//Habits//EN"];
  const now=new Date();
  for(let i=0;i<30;i++){
    const d=new Date(now); d.setDate(now.getDate()+i); d.setHours(hh||20, mm||0, 0, 0);
    const dt = d.toISOString().replace(/[-:]/g,"").split(".")[0]+"Z";
    const uid = `nl-${h.id}-${i}@newslens`;
    lines.push("BEGIN:VEVENT",`UID:${uid}`,`DTSTAMP:${dt}`,`DTSTART:${dt}`,`SUMMARY:${h.name} – Habit Reminder`,"END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  const blob=new Blob([lines.join("\r\n")],{type:"text/calendar"}); const url=URL.createObjectURL(blob);
  const a=document.createElement("a"); a.href=url; a.download=`${h.name}-reminders.ics`; a.click(); URL.revokeObjectURL(url);
});

/* ------------------ Curated tabs ------------------ */
async function loadCurated(topic, gridId, emptyId){
  const gridEl=document.getElementById(gridId), emptyEl=document.getElementById(emptyId);
  showSkeleton(gridEl,9);
  try{
    const res = await fetch(API("/api/curated",{topic, days:"3"}));
    const data = await res.json();
    renderItemsToGrid(data.items||[], gridEl, emptyEl);
  }catch{
    gridEl.innerHTML=""; emptyEl.style.display="block"; emptyEl.textContent="Failed to load.";
  }
}

/* ------------------ Chat (Gemini) ------------------ */
const chatLog = document.getElementById("chat-log");
const chatText = document.getElementById("chat-text");
document.getElementById("chat-send")?.addEventListener("click", sendChat);
chatText?.addEventListener("keydown", e=>{ if(e.key==="Enter") sendChat(); });
async function sendChat(){
  const text=(chatText.value||"").trim(); if(!text) return;
  appendMsg("user", text); chatText.value="";
  appendMsg("bot", "…");
  try{
    const res = await fetch(API("/api/chat"), {method:"POST", headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text})});
    const data = await res.json();
    updateLastBot(data.text || "Sorry, I couldn't respond.");
  }catch{
    updateLastBot("Network error.");
  }
}
function appendMsg(role, text){
  const m=document.createElement("div"); m.className=`chat-msg ${role}`; m.textContent=text; chatLog.appendChild(m); chatLog.scrollTop=chatLog.scrollHeight;
}
function updateLastBot(text){
  const msgs=[...chatLog.querySelectorAll(".chat-msg.bot")]; if(msgs.length) msgs[msgs.length-1].textContent=text; chatLog.scrollTop=chatLog.scrollHeight;
}

/* ------------------ init ------------------ */
function init(){
  loadTop5();
  populateStates(); setStepEnabled(1); updateHeadline();
}
init();
