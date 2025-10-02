// frontend/assets/app.js

// Same-origin (served by FastAPI). If you split later, set full origin.
const API_BASE = "";
const API = (path, params={}) => {
  const usp = new URLSearchParams(params);
  return `${API_BASE}${path}${usp.toString() ? "?" + usp.toString() : ""}`;
};

const STATES = [
  "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
  "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
  "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan",
  "Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
  "Delhi","Jammu and Kashmir","Ladakh","Puducherry","Chandigarh"
];

// ===== DOM =====
const tabs = document.querySelectorAll(".tab");
const views = document.querySelectorAll(".view");
const gotoTrendingBtn = document.getElementById("goto-trending");

const qInput = document.getElementById("q");
const qBtn = document.getElementById("qbtn");

const signalsRow = document.getElementById("signals");
const trendPreview = document.getElementById("trend-cloud");
const trendCloudFull = document.getElementById("trend-cloud-full");
const trendList = document.getElementById("trend-list");
const trendDaysSel = document.getElementById("trendDays");
const reloadTrendingBtn = document.getElementById("reload-trending");

const digestGrid = document.getElementById("digest-grid");
const digestEmpty = document.getElementById("digest-empty");
const followInput = document.getElementById("follow-input");
const followAdd = document.getElementById("follow-add");
const followChips = document.getElementById("follow-chips");

// Existing feed controls
const scopeSel = document.getElementById("scope");
const stateSel = document.getElementById("state");
const catSel = document.getElementById("category");
const daysSel = document.getElementById("days");
const modeSel = document.getElementById("mode");
const refreshBtn = document.getElementById("refresh");
const grid = document.getElementById("grid");
const empty = document.getElementById("empty");
const headline = document.getElementById("headline");

// ===== Helpers =====
function setActiveTab(name){
  tabs.forEach(t=>t.classList.toggle("active", t.dataset.tab===name));
  views.forEach(v=>v.classList.toggle("active", v.id===name));
}
function capitalize(s){ return s ? s[0].toUpperCase() + s.slice(1) : s; }

function showSkeletonGrid(el, n=8){
  el.innerHTML = "";
  for(let i=0;i<n;i++){
    const d = document.createElement("div");
    d.className = "skel";
    d.innerHTML = `<div class="bar w"></div><div class="bar w2"></div><div class="bar w3"></div>`;
    el.appendChild(d);
  }
}
function chip(text, cls="chip"){ return `<span class="${cls}">${text}</span>`; }

// ===== Home: Top 5 Signals =====
async function loadTop5(){
  signalsRow.innerHTML = "";
  showSkeletonGrid(signalsRow, 5);
  try{
    const res = await fetch(API("/api/signals/top5", {days:"2"}));
    const data = await res.json();
    signalsRow.innerHTML = "";
    (data.items || []).forEach(addSignalCard);
  }catch(e){
    signalsRow.innerHTML = `<div class="empty">Failed to load signals.</div>`;
  }
}
function addSignalCard(item){
  const div = document.createElement("div");
  div.className = "signal-card";
  const date = item.published_at ? new Date(item.published_at).toLocaleString() : "—";
  const chipsHTML = [
    item.category && item.category!=="all" ? chip(item.category) : "",
    item.source ? chip(item.source) : ""
  ].join(" ");
  div.innerHTML = `
    <h3>${item.title || "(untitled)"}</h3>
    <div class="meta">${chipsHTML}</div>
    <p>${item.summary || ""}</p>
    <div class="row-ends">
      <small>${date}</small>
      <a class="btn" href="${item.url}" target="_blank" rel="noopener">Open</a>
    </div>
  `;
  div.addEventListener("click", (e)=>{
    if(e.target.tagName.toLowerCase()==="a") return;
    openEntityFromItem(item);
  });
  signalsRow.appendChild(div);
}

// ===== Trending (preview + full) =====
async function loadTrendingPreview(){
  try{
    const res = await fetch(API("/api/trending",{days:"2"}));
    const data = await res.json();
    trendPreview.innerHTML = "";
    (data.terms||[]).slice(0,12).forEach(t=>{
      const a = document.createElement("button");
      a.className = "bubble";
      a.textContent = t.term;
      a.title = `${t.count} mentions`;
      a.onclick = ()=> openEntity(t.term);
      trendPreview.appendChild(a);
    });
  }catch(e){
    trendPreview.innerHTML = `<div class="empty">Trend error.</div>`;
  }
}
async function loadTrendingFull(){
  trendCloudFull.innerHTML = "";
  trendList.innerHTML = "";
  try{
    const res = await fetch(API("/api/trending",{days: trendDaysSel.value || "2"}));
    const data = await res.json();
    (data.terms||[]).forEach((t,i)=>{
      const b = document.createElement("button");
      b.className = "bubble";
      b.textContent = t.term;
      b.title = `${t.count} mentions`;
      b.onclick = ()=> openEntity(t.term);
      trendCloudFull.appendChild(b);

      const li = document.createElement("li");
      li.innerHTML = `<span>${i+1}.</span> <a href="#" class="linklike">${t.term}</a> <em>${t.count}</em>`;
      li.querySelector("a").onclick = (e)=>{ e.preventDefault(); openEntity(t.term); };
      trendList.appendChild(li);
    });
  }catch(e){
    trendCloudFull.innerHTML = `<div class="empty">Trend error.</div>`;
  }
}

// ===== Entity view (re-uses /api/entity) =====
async function openEntity(term){
  // switch to Feed for now with search results drawer
  setActiveTab("feed");
  await searchAndRender(term);
}
function openEntityFromItem(item){
  // best-effort: pick a prominent term from title
  const t = (item.title || "").split(" ").slice(0,3).join(" ");
  openEntity(t);
}

// ===== Global Search (Home top bar) =====
async function doSearch(){
  const q = qInput.value.trim();
  if(!q) return;
  setActiveTab("feed");
  await searchAndRender(q);
}
async function searchAndRender(q){
  headline.textContent = `Results for “${q}”`;
  grid.innerHTML = "";
  showSkeletonGrid(grid, 9);
  try{
    const res = await fetch(API("/api/search", { q, days:"7" }));
    const data = await res.json();
    renderItemsToGrid(data.items || [], grid, empty);
  }catch(e){
    grid.innerHTML = "";
    empty.style.display = "block";
    empty.textContent = "Search failed.";
  }
}

// ===== My Digest (followed entities; client-side list → backend via query) =====
const FOLLOW_KEY = "nl_follow_terms";
function getFollows(){
  try{
    const raw = localStorage.getItem(FOLLOW_KEY) || "[]";
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  }catch{ return []; }
}
function saveFollows(arr){
  localStorage.setItem(FOLLOW_KEY, JSON.stringify(arr));
  renderFollowChips();
}
function renderFollowChips(){
  const arr = getFollows();
  followChips.innerHTML = "";
  if(arr.length===0){
    followChips.innerHTML = `<span class="muted">No terms followed yet.</span>`;
    return;
  }
  arr.forEach((t,i)=>{
    const b = document.createElement("span");
    b.className = "chip removable";
    b.innerHTML = `${t} <b>&times;</b>`;
    b.querySelector("b").onclick = ()=> {
      const next = getFollows().filter(x=>x!==t);
      saveFollows(next);
      loadDigest();
    };
    followChips.appendChild(b);
  });
}
async function loadDigest(){
  const terms = getFollows();
  digestGrid.innerHTML = "";
  showSkeletonGrid(digestGrid, 6);
  try{
    const res = await fetch(API("/api/digest", { follow: terms.join(","), days:"2" }));
    const data = await res.json();
    renderItemsToGrid(data.items || [], digestGrid, digestEmpty);
  }catch(e){
    digestGrid.innerHTML = `<div class="empty">Digest error.</div>`;
  }
}
followAdd?.addEventListener("click", ()=>{
  const t = (followInput.value || "").trim();
  if(!t) return;
  const cur = getFollows();
  if(!cur.includes(t)) cur.push(t);
  saveFollows(cur);
  followInput.value = "";
  loadDigest();
});

// ===== Existing FEED (unchanged, but wrapped nicely) =====
function populateStates(){
  stateSel.innerHTML = "";
  STATES.forEach(s=>{
    const opt = document.createElement("option");
    opt.value = s; opt.textContent = s;
    stateSel.appendChild(opt);
  });
}
function setStepEnabled(step) {
  scopeSel.disabled   = step < 2;
  stateSel.disabled   = !(step >=3 && scopeSel.value === "state");
  catSel.disabled     = step < 4;
  modeSel.disabled    = step < 5;
  refreshBtn.disabled = step < 5;
}
function updateHeadline(){
  const sc = scopeSel.value;
  const cat = catSel.value || "All";
  const days = daysSel.value ? `${daysSel.options[daysSel.selectedIndex].text}` : "Pick timeline";
  if(!daysSel.value){
    headline.textContent = "Pick a timeline to start";
    return;
  }
  if(sc === "national"){
    headline.textContent = `Top ${capitalize(cat)} News — ${days}`;
  }else{
    headline.textContent = `${stateSel.value} — ${capitalize(cat)} News — ${days}`;
  }
}
function showSkeleton(n=8){
  grid.innerHTML = "";
  empty.style.display = "none";
  for(let i=0;i<n;i++){
    const div = document.createElement("div");
    div.className = "skel";
    div.innerHTML = `
      <div class="bar w"></div>
      <div class="bar w2"></div>
      <div class="bar w3"></div>
      <div class="bar w2"></div>`;
    grid.appendChild(div);
  }
}
async function fetchNews(){
  if(!daysSel.value){ return; }
  updateHeadline();
  showSkeleton(9);

  const scope = scopeSel.value;
  const state = scope === "state" ? stateSel.value : "";
  const category = catSel.value;
  const days = daysSel.value;
  const mode = modeSel.value || "light";

  const params = { scope, days, limit: "60", fetch_mode: mode };
  if(state) params.state = state;
  if(category) params.category = category;

  const url = API("/api/news", params);

  try{
    const res = await fetch(url);
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    grid.innerHTML = "";
    if(!data || !Array.isArray(data.items) || data.items.length === 0){
      empty.style.display = "block";
      empty.textContent = "No news found for your filters.";
      return;
    }

    let ok = 0;
    for (const it of data.items) {
      try { renderCard(it); ok++; }
      catch (e) { console.warn("Card render failed:", it, e); }
    }
    if (ok === 0) {
      empty.style.display = "block";
      empty.textContent = "No renderable items. (Check console for details.)";
    }
  }catch(e){
    console.error("Fetch/render error:", e);
    grid.innerHTML = "";
    empty.style.display = "block";
    empty.textContent = "Failed to load news. Check API_BASE or try again.";
  }
}
function renderCard(item){
  const title = (item && item.title) ? String(item.title) : "(untitled)";
  const url   = (item && item.url) ? String(item.url) : "#";
  const published = item && item.published_at ? String(item.published_at) : null;

  let dateText = "—";
  if (published) {
    const d = new Date(published);
    dateText = isNaN(d.getTime()) ? "—" : d.toLocaleString();
  }

  const chips = [];
  if (item && item.category && item.category !== "all") chips.push(`<span class="chip">${String(item.category)}</span>`);
  if (item && item.state) chips.push(`<span class="chip">${String(item.state)}</span>`);
  if (item && item.source) chips.push(`<span class="chip">${String(item.source)}</span>`);

  const summary = (item && item.summary) ? String(item.summary) : "";

  const div = document.createElement("div");
  div.className = "card";
  div.innerHTML = `
    <h3><a href="${url}" target="_blank" rel="noopener">${title}</a></h3>
    <div class="chips">${chips.join(" ")}</div>
    <p>${summary}</p>
    <div class="meta">${dateText}</div>
    <div class="actions">
      <button class="mini follow">Follow</button>
      <a class="mini" href="${url}" target="_blank" rel="noopener">Open</a>
    </div>
  `;
  // follow adds top 2 words of title as term
  div.querySelector(".follow").onclick = ()=>{
    const term = title.split(" ").slice(0,2).join(" ").trim();
    const arr = getFollows();
    if(term && !arr.includes(term)){ arr.push(term); saveFollows(arr); }
  };
  grid.appendChild(div);
}
function renderItemsToGrid(items, targetGrid, targetEmpty){
  targetGrid.innerHTML = "";
  if(!items || items.length===0){
    targetEmpty.style.display = "block";
    return;
  }
  targetEmpty.style.display = "none";
  items.forEach(it=>{
    const d = document.createElement("div");
    d.className = "card";
    const chips = [];
    if (it.category && it.category!=="all") chips.push(`<span class="chip">${it.category}</span>`);
    if (it.state) chips.push(`<span class="chip">${it.state}</span>`);
    if (it.source) chips.push(`<span class="chip">${it.source}</span>`);
    const date = it.published_at ? new Date(it.published_at).toLocaleString() : "—";
    d.innerHTML = `
      <h3><a href="${it.url}" target="_blank" rel="noopener">${it.title || "(untitled)"}</a></h3>
      <div class="chips">${chips.join(" ")}</div>
      <p>${it.summary || ""}</p>
      <div class="meta">${date}</div>
    `;
    targetGrid.appendChild(d);
  });
}

// ===== Events & boot =====
tabs.forEach(t=>{
  t.addEventListener("click", ()=>{
    setActiveTab(t.dataset.tab);
    if(t.dataset.tab==="home"){ loadTop5(); loadTrendingPreview(); }
    if(t.dataset.tab==="trending"){ loadTrendingFull(); }
    if(t.dataset.tab==="digest"){ renderFollowChips(); loadDigest(); }
  });
});
gotoTrendingBtn?.addEventListener("click", ()=>{ setActiveTab("trending"); loadTrendingFull(); });

qBtn?.addEventListener("click", doSearch);
qInput?.addEventListener("keydown", (e)=>{ if(e.key==="Enter") doSearch(); });

trendDaysSel?.addEventListener("change", loadTrendingFull);
reloadTrendingBtn?.addEventListener("click", loadTrendingFull);

// Feed controls
function setStepEnabledFeed(step) { setStepEnabled(step); }
daysSel?.addEventListener("change", ()=>{
  setStepEnabledFeed(daysSel.value ? 2 : 1);
  updateHeadline();
  if(daysSel.value) fetchNews();
});
scopeSel?.addEventListener("change", ()=>{
  setStepEnabledFeed( scopeSel.value === "state" ? 3 : 4 );
  if(scopeSel.value !== "state"){ fetchNews(); }
});
stateSel?.addEventListener("change", ()=>{ setStepEnabledFeed(4); fetchNews(); });
catSel?.addEventListener("change", ()=>{ setStepEnabledFeed(5); fetchNews(); });
modeSel?.addEventListener("change", fetchNews);
refreshBtn?.addEventListener("click", fetchNews);

// init
function init(){
  populateStates();
  setStepEnabledFeed(1);
  // default landing: Home
  setActiveTab("home");
  loadTop5();
  loadTrendingPreview();
}
init();
