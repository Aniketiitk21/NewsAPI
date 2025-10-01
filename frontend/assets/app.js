// frontend/assets/app.js

// If you're serving the UI and API from the SAME host (local FastAPI or 1 Render service),
// we can use a blank base and hit absolute path /api/news to avoid CORS entirely.
// If you host API separately, set API_BASE to that full origin (e.g., "https://your-api.onrender.com")
const API_BASE =
  (location.hostname === "localhost" || location.hostname === "127.0.0.1")
    ? ""                  // same-origin in local dev (served by FastAPI)
    : "";                 // same-origin in prod (served by FastAPI). Change to "https://<your-backend-host>" if split.

// Always use the canonical API path
const API_PATH = "/api/news";

const STATES = [
  "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
  "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
  "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan",
  "Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
  "Delhi","Jammu and Kashmir","Ladakh","Puducherry","Chandigarh"
];

const scopeSel = document.getElementById("scope");
const stateSel = document.getElementById("state");
const catSel = document.getElementById("category");
const daysSel = document.getElementById("days");
const modeSel = document.getElementById("mode");
const refreshBtn = document.getElementById("refresh");
const grid = document.getElementById("grid");
const empty = document.getElementById("empty");
const headline = document.getElementById("headline");

function populateStates(){
  stateSel.innerHTML = "";
  STATES.forEach(s=>{
    const opt = document.createElement("option");
    opt.value = s; opt.textContent = s;
    stateSel.appendChild(opt);
  });
}

function setStepEnabled(step) {
  // step: 1 timeline, 2 scope, 3 state, 4 category, 5 mode + refresh
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

function capitalize(s){ return s ? s[0].toUpperCase() + s.slice(1) : s; }

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

  const params = new URLSearchParams({ scope, days, limit: "60", fetch_mode: mode });
  if(state) params.set("state", state);
  if(category) params.set("category", category);

  // Build final URL (absolute path avoids accidental '/news' or stale bases)
  const url = `${API_BASE}${API_PATH}?${params.toString()}`;
  // console.log("Hitting:", url);

  try{
    const res = await fetch(url, { credentials: "omit" });
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
      try {
        renderCard(it);
        ok++;
      } catch (e) {
        console.warn("Card render failed for item:", it, e);
      }
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

  const stanceLabel = (item && item.stance) ? String(item.stance).toUpperCase() : "";
  let stanceHTML = "";
  if (stanceLabel) {
    const conf = Number(item.confidence);
    const confTxt = Number.isFinite(conf) ? ` (${Math.round(conf*100)}%)` : "";
    stanceHTML = `<span class="stance ${item.stance}">${stanceLabel}${confTxt}</span>`;
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
    <div class="meta">${dateText}</div>
    <div class="chips">${chips.join(" ")}</div>
    <p>${summary}</p>
    ${stanceHTML}
  `;
  grid.appendChild(div);
}

/* === Events === */
daysSel.addEventListener("change", ()=>{
  setStepEnabled(daysSel.value ? 2 : 1);
  updateHeadline();
  if(daysSel.value) fetchNews();
});

scopeSel.addEventListener("change", ()=>{
  setStepEnabled(scopeSel.value === "state" ? 3 : 4);
  if(scopeSel.value !== "state"){ fetchNews(); }
});

stateSel.addEventListener("change", ()=>{ setStepEnabled(4); fetchNews(); });
catSel.addEventListener("change", ()=>{ setStepEnabled(5); fetchNews(); });
modeSel.addEventListener("change", fetchNews);
refreshBtn.addEventListener("click", fetchNews);

function init(){
  populateStates();
  setStepEnabled(1); // only timeline active at start
  updateHeadline();
}
init();
