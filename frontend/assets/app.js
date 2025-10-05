// ========= Core helpers =========
const API = (path, params={}) => {
  const usp = new URLSearchParams(params);
  return `${path}${usp.toString() ? "?" + usp.toString() : ""}`;
};
const STATES = [
  "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
  "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
  "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan",
  "Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
  "Delhi","Jammu and Kashmir","Ladakh","Puducherry","Chandigarh"
];
function capitalize(s){ return s ? s[0].toUpperCase() + s.slice(1) : s; }
function fmtDate(d){ return d.toISOString().slice(0,10); }

// ========= Tabs & nav =========
const tabs = document.querySelectorAll(".tab");
const views = document.querySelectorAll(".view");
function setActiveTab(name){
  tabs.forEach(t=>t.classList.toggle("active", t.dataset.tab===name));
  views.forEach(v=>v.classList.toggle("active", v.id===name));
}

// ========= Home (Top 5) =========
const signalsRow = document.getElementById("signals");
function showSkeletonRow(el, n=5){
  el.innerHTML = "";
  for(let i=0;i<n;i++){
    const d = document.createElement("div");
    d.className = "signal-card skel";
    d.innerHTML = `<div class="bar w"></div><div class="bar w2"></div><div class="bar w3"></div>`;
    el.appendChild(d);
  }
}
async function loadTop5(){
  signalsRow && showSkeletonRow(signalsRow, 5);
  try{
    const res = await fetch(API("/api/signals/top5",{days:"2"}));
    const data = await res.json();
    signalsRow.innerHTML = "";
    (data.items||[]).forEach(item=>{
      const div = document.createElement("div");
      div.className = "signal-card";
      const date = item.published_at ? new Date(item.published_at).toLocaleString() : "—";
      const chips = [
        item.category && item.category!=="all" ? `<span class="chip">${item.category}</span>` : "",
        item.source ? `<span class="chip">${item.source}</span>` : ""
      ].join(" ");
      div.innerHTML = `
        <h3>${item.title || "(untitled)"}</h3>
        <div class="chips">${chips}</div>
        <p>${item.summary || ""}</p>
        <div class="row-ends">
          <small>${date}</small>
          <a class="btn" href="${item.url}" target="_blank" rel="noopener">Open</a>
        </div>`;
      signalsRow.appendChild(div);
    });
  }catch{
    signalsRow.innerHTML = `<div class="empty">Failed to load signals.</div>`;
  }
}

// ========= Global Search =========
const qInput = document.getElementById("q");
const qBtn = document.getElementById("qbtn");
qBtn?.addEventListener("click", doSearch);
qInput?.addEventListener("keydown",(e)=>{ if(e.key==="Enter") doSearch(); });

async function doSearch(){
  const q = qInput.value.trim();
  if(!q) return;
  setActiveTab("feed");
  scopeSel.value = "national"; catSel.value = ""; daysSel.value = "7";
  setStepEnabled(5); updateHeadline();

  grid.innerHTML = ""; showSkeleton(grid, 9);
  try{
    const res = await fetch(API("/api/search",{q,days:"7",deep:"0"}));
    const data = await res.json();
    renderItemsToGrid(data.items || [], grid, empty);
    headline.textContent = `Results for “${q}”`;
  }catch{
    grid.innerHTML = ""; empty.style.display="block";
    empty.textContent="Search failed.";
  }
}

// ========= Digest (follow terms) =========
const digestGrid = document.getElementById("digest-grid");
const digestEmpty = document.getElementById("digest-empty");
const followInput = document.getElementById("follow-input");
const followAdd = document.getElementById("follow-add");
const followChips = document.getElementById("follow-chips");
const FOLLOW_KEY="nl_follow_terms";
function getFollows(){ try{ const x=JSON.parse(localStorage.getItem(FOLLOW_KEY)||"[]"); return Array.isArray(x)?x:[]; }catch{return[];} }
function saveFollows(a){ localStorage.setItem(FOLLOW_KEY, JSON.stringify(a)); renderFollowChips(); }
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
followAdd?.addEventListener("click",()=>{ const t=(followInput.value||"").trim(); if(!t) return; const cur=getFollows(); if(!cur.includes(t)) cur.push(t); saveFollows(cur); followInput.value=""; loadDigest(); });

// ========= Feed (existing) =========
const scopeSel=document.getElementById("scope");
const stateSel=document.getElementById("state");
const catSel=document.getElementById("category");
const daysSel=document.getElementById("days");
const modeSel=document.getElementById("mode");
const refreshBtn=document.getElementById("refresh");
const grid=document.getElementById("grid");
const empty=document.getElementById("empty");
const headline=document.getElementById("headline");

function populateStates(){
  stateSel.innerHTML=""; STATES.forEach(s=>{ const o=document.createElement("option"); o.value=s; o.textContent=s; stateSel.appendChild(o); });
}
function setStepEnabled(step){
  scopeSel.disabled= step<2;
  stateSel.disabled= !(step>=3 && scopeSel.value==="state");
  catSel.disabled  = step<4; modeSel.disabled= step<5; refreshBtn.disabled= step<5;
}
function updateHeadline(){
  const sc=scopeSel.value; const cat=catSel.value||"All";
  const days= daysSel.value ? `${daysSel.options[daysSel.selectedIndex].text}` : "Pick timeline";
  if(!daysSel.value){ headline.textContent="Pick a timeline to start"; return; }
  headline.textContent = sc==="national" ? `Top ${capitalize(cat)} News — ${days}` : `${stateSel.value} — ${capitalize(cat)} News — ${days}`;
}
function showSkeleton(el, n=8){
  el.innerHTML=""; empty.style.display="none";
  for(let i=0;i<n;i++){ const d=document.createElement("div"); d.className="skel"; d.innerHTML=`<div class="bar w"></div><div class="bar w2"></div><div class="bar w3"></div><div class="bar w2"></div>`; el.appendChild(d); }
}
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
  targetGrid.innerHTML=""; if(!items || items.length===0){ targetEmpty.style.display="block"; targetEmpty.textContent="No news found for your filters."; return; }
  targetEmpty.style.display="none";
  items.forEach(it=>{
    const d=document.createElement("div"); d.className="card";
    const chips=[]; if(it.category && it.category!=="all") chips.push(`<span class="chip">${it.category}</span>`); if(it.state) chips.push(`<span class="chip">${it.state}</span>`); if(it.source) chips.push(`<span class="chip">${it.source}</span>`);
    const date= it.published_at? new Date(it.published_at).toLocaleString() : "—";
    d.innerHTML = `
      <h3><a href="${it.url}" target="_blank" rel="noopener">${it.title || "(untitled)"}</a></h3>
      <div class="chips">${chips.join(" ")}</div>
      <p>${it.summary || ""}</p>
      <div class="meta">${date}</div>`;
    targetGrid.appendChild(d);
  });
}
daysSel?.addEventListener("change", ()=>{ setStepEnabled(daysSel.value?2:1); updateHeadline(); if(daysSel.value) fetchNews(); });
scopeSel?.addEventListener("change", ()=>{ setStepEnabled(scopeSel.value==="state"?3:4); if(scopeSel.value!=="state") fetchNews(); });
stateSel?.addEventListener("change", ()=>{ setStepEnabled(4); fetchNews(); });
catSel?.addEventListener("change", ()=>{ setStepEnabled(5); fetchNews(); });
modeSel?.addEventListener("change", fetchNews);
refreshBtn?.addEventListener("click", fetchNews);

// ========= HABITS (NEW) =========
/*
Data model in localStorage:
nl_habits = [
 { id: "h1", name:"Read", color:"#2563eb", history: {"2025-10-05": true, ... } },
 ...
]
*/
const HAB_KEY="nl_habits";
const $ = (id)=>document.getElementById(id);

const habitNameEl = $("habit-name");
const habitColorEl = $("habit-color");
const habitAddBtn = $("habit-add");
const habitSelect = $("habit-select");
const habitRenameBtn = $("habit-rename");
const habitDeleteBtn = $("habit-delete");

const statCurrent = $("stat-current");
const statBest = $("stat-best");
const statMonth = $("stat-month");

const calTitle = $("cal-title");
const calGrid = $("cal-grid");
const calPrev = $("cal-prev");
const calNext = $("cal-next");
const chartCanvas = $("habit-chart");
let chartCtx = chartCanvas.getContext("2d");

let calCursor = new Date(); // month being shown

function loadHabits(){
  try{ const x=JSON.parse(localStorage.getItem(HAB_KEY)||"[]"); return Array.isArray(x)?x:[]; }catch{return[];}
}
function saveHabits(arr){ localStorage.setItem(HAB_KEY, JSON.stringify(arr)); }
function ensureHabitSelected(){
  const habits=loadHabits();
  if(habits.length===0){ habitSelect.innerHTML=""; return null; }
  if(!habitSelect.value){ habitSelect.value = habits[0].id; }
  return habits.find(h=>h.id===habitSelect.value) || habits[0];
}
function uid(){ return Math.random().toString(36).slice(2,9); }

function refreshHabitSelect(){
  const habits=loadHabits();
  habitSelect.innerHTML="";
  habits.forEach(h=>{
    const opt=document.createElement("option");
    opt.value=h.id; opt.textContent=h.name;
    habitSelect.appendChild(opt);
  });
}

habitAddBtn?.addEventListener("click", ()=>{
  const name=(habitNameEl.value||"").trim(); if(!name) return;
  const color=habitColorEl.value || "#2563eb";
  const arr=loadHabits(); arr.push({id:uid(), name, color, history:{}});
  saveHabits(arr); habitNameEl.value=""; refreshHabitSelect(); renderHabitsUI();
});
habitRenameBtn?.addEventListener("click", ()=>{
  const habits=loadHabits(); if(habits.length===0) return;
  const h = ensureHabitSelected(); if(!h) return;
  const next = prompt("New name", h.name); if(!next) return;
  h.name = next; saveHabits(habits); refreshHabitSelect(); habitSelect.value=h.id; renderHabitsUI();
});
habitDeleteBtn?.addEventListener("click", ()=>{
  const habits=loadHabits(); if(habits.length===0) return;
  const h=ensureHabitSelected(); if(!h) return;
  if(!confirm(`Delete habit “${h.name}”?`)) return;
  saveHabits(habits.filter(x=>x.id!==h.id));
  refreshHabitSelect(); renderHabitsUI();
});
habitSelect?.addEventListener("change", renderHabitsUI);
calPrev?.addEventListener("click", ()=>{ calCursor.setMonth(calCursor.getMonth()-1); renderCalendar(); });
calNext?.addEventListener("click", ()=>{ calCursor.setMonth(calCursor.getMonth()+1); renderCalendar(); });

function renderHabitsUI(){
  const h = ensureHabitSelected();
  if(!h){
    calTitle.textContent="Create a habit to start";
    calGrid.innerHTML=`<div class="empty">No habits yet. Add one above.</div>`;
    statCurrent.textContent="0"; statBest.textContent="0"; statMonth.textContent="0%";
    drawChart([]); return;
  }
  renderCalendar();
  const stats = computeStats(h);
  statCurrent.textContent = String(stats.currentStreak);
  statBest.textContent = String(stats.bestStreak);
  statMonth.textContent = `${Math.round(stats.monthPercent)}%`;
  drawChart(stats.weekly);
}

function renderCalendar(){
  const h = ensureHabitSelected();
  if(!h){ return; }
  const year = calCursor.getFullYear();
  const month = calCursor.getMonth();
  const first = new Date(year, month, 1);
  const last = new Date(year, month+1, 0);
  const startWeekday = (first.getDay()+6)%7; // Mon=0
  const daysCount = last.getDate();

  calTitle.textContent = `${first.toLocaleString("default",{month:"long"})} ${year}`;
  calGrid.innerHTML = `
    <div class="cal-wd">Mon</div><div class="cal-wd">Tue</div><div class="cal-wd">Wed</div>
    <div class="cal-wd">Thu</div><div class="cal-wd">Fri</div><div class="cal-wd">Sat</div><div class="cal-wd">Sun</div>
  `;
  for(let i=0;i<startWeekday;i++){
    const pad=document.createElement("div"); pad.className="cal-cell pad"; calGrid.appendChild(pad);
  }
  for(let d=1; d<=daysCount; d++){
    const date = new Date(year, month, d);
    const key = fmtDate(date);
    const cell = document.createElement("button");
    cell.className = "cal-cell day";
    const done = !!(h.history && h.history[key]);
    cell.innerHTML = `<span class="num">${d}</span>`;
    if(done) cell.classList.add("done");
    cell.style.setProperty("--accent", h.color || "#2563eb");
    cell.onclick = ()=>{
      const habits=loadHabits();
      const me = habits.find(x=>x.id===h.id);
      if(!me.history) me.history={};
      me.history[key] = !me.history[key];
      saveHabits(habits);
      renderHabitsUI();
    };
    calGrid.appendChild(cell);
  }
}

function computeStats(h){
  const today = new Date();
  const todayKey = fmtDate(today);

  // current streak (walk back from today)
  let streak = 0;
  let ptr = new Date(today);
  while(true){
    const k = fmtDate(ptr);
    if(h.history && h.history[k]) { streak++; ptr.setDate(ptr.getDate()-1); }
    else break;
  }

  // best streak in last 180 days
  let best = 0, cur=0;
  const back = new Date(); back.setDate(back.getDate()-180);
  for(let d=new Date(back); d<=today; d.setDate(d.getDate()+1)){
    const k=fmtDate(d);
    if(h.history && h.history[k]) { cur++; best=Math.max(best,cur); }
    else cur=0;
  }

  // this month % complete
  const year = calCursor.getFullYear();
  const month = calCursor.getMonth();
  const last = new Date(year, month+1, 0);
  let have=0, total=last.getDate();
  for(let i=1;i<=total;i++){
    const k=fmtDate(new Date(year,month,i));
    if(h.history && h.history[k]) have++;
  }
  const monthPercent = total? (have*100/total) : 0;

  // weekly completion counts for last 8 weeks
  const weekly=[];
  const end = new Date(today); end.setHours(0,0,0,0);
  for(let w=7; w>=0; w--){
    const start = new Date(end); start.setDate(end.getDate() - (w*7 + 6));
    const stop  = new Date(end); stop.setDate(end.getDate() - (w*7));
    let count=0;
    for(let d=new Date(start); d<=stop; d.setDate(d.getDate()+1)){
      const k=fmtDate(d);
      if(h.history && h.history[k]) count++;
    }
    weekly.push(count);
  }

  return { currentStreak: streak, bestStreak: best, monthPercent, weekly };
}

function drawChart(weekly){
  // minimalist line chart
  const ctx=chartCtx; const W=chartCanvas.width=chartCanvas.clientWidth; const H=chartCanvas.height=120;
  ctx.clearRect(0,0,W,H);
  if(!weekly || weekly.length===0){ return; }
  const max = Math.max(...weekly, 7);
  const stepX = W/(weekly.length-1);
  const scaleY = (H-20)/max;

  ctx.lineWidth=2; ctx.strokeStyle="#4f46e5";
  ctx.beginPath();
  weekly.forEach((v,i)=>{
    const x = i*stepX;
    const y = H - 10 - v*scaleY;
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();

  // baseline + dots
  ctx.strokeStyle="#e5e7eb"; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(0,H-10); ctx.lineTo(W,H-10); ctx.stroke();

  ctx.fillStyle="#4f46e5";
  weekly.forEach((v,i)=>{
    const x=i*stepX, y=H-10-v*scaleY;
    ctx.beginPath(); ctx.arc(x,y,3,0,Math.PI*2); ctx.fill();
  });
}

// ========= Boot & tab wiring =========
tabs.forEach(t=>{
  t.addEventListener("click", ()=>{
    setActiveTab(t.dataset.tab);
    if(t.dataset.tab==="home"){ loadTop5(); }
    if(t.dataset.tab==="digest"){ renderFollowChips(); loadDigest(); }
    if(t.dataset.tab==="habits"){ refreshHabitSelect(); renderHabitsUI(); }
  });
});

function init(){
  // home
  loadTop5();
  // feed
  populateStates(); setStepEnabled(1); updateHeadline();
}
init();
