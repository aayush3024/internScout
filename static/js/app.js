const $ = id => document.getElementById(id);
let results = [], saved = JSON.parse(localStorage.getItem("internscout_saved") || "[]");
let currentItem = null, filter = "all";

function esc(s){return String(s ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function toast(s){const t=$("toast");t.textContent=s;t.classList.add("show");setTimeout(()=>t.classList.remove("show"),2800);}
function keyFor(item){return item.url || item.title;}
function persist(){localStorage.setItem("internscout_saved",JSON.stringify(saved));updateCounts();renderResults();}
function updateCounts(){$("savedCount").textContent=saved.length;$("savedTabCount").textContent=saved.length;$("allCount").textContent=results.length;$("exportBtn").disabled=!saved.length;}
function renderResults(){
 const shown=(filter==="saved"?saved:results).slice();
 if($("sortSelect").value==="title")shown.sort((a,b)=>(a.title||"").localeCompare(b.title||""));
 else shown.sort((a,b)=>(b.match_score||0)-(a.match_score||0));
 $("resultsState").classList.toggle("hidden",shown.length>0);
 $("resultsList").innerHTML=shown.map((item)=>{
  const isSaved=saved.some(x=>keyFor(x)===keyFor(item));
  return `<article class="result-card">
   <div><div class="result-source">${esc(item.site||"Web result")} · ${esc(item.source||"TinyFish Search")}</div>
   <h3>${esc(item.title)}</h3><p>${esc(item.snippet||"Open the original listing to review the role details and eligibility.")}</p>
   ${item.url?`<a class="result-url" href="${esc(item.url)}" target="_blank" rel="noopener">View original source ↗</a>`:""}
   </div><div class="result-actions"><span class="score">${item.match_score||0}% MATCH</span>
   <button class="save-btn ${isSaved?"saved":""}" data-save="${esc(keyFor(item))}" title="Save">${isSaved?"♥":"♡"}</button>
   <button class="inspect-btn" data-inspect="${esc(keyFor(item))}">Research ↗</button></div></article>`;
 }).join("");
 $("resultsList").querySelectorAll("[data-save]").forEach(btn=>btn.addEventListener("click",()=>{
  const item=results.find(x=>keyFor(x)===btn.dataset.save)||saved.find(x=>keyFor(x)===btn.dataset.save);
  if(!item)return; const exists=saved.some(x=>keyFor(x)===keyFor(item));
  saved=exists?saved.filter(x=>keyFor(x)!==keyFor(item)):[...saved,item];persist();toast(exists?"Removed from shortlist":"Saved to your shortlist");
 }));
 $("resultsList").querySelectorAll("[data-inspect]").forEach(btn=>btn.addEventListener("click",()=>{
  currentItem=results.find(x=>keyFor(x)===btn.dataset.inspect)||saved.find(x=>keyFor(x)===btn.dataset.inspect);
  if(!currentItem?.url){toast("This result does not include a source URL.");return;}
  $("modalTitle").textContent=currentItem.title;$("modalSubtitle").textContent=currentItem.url;
  $("detailOutput").textContent="Choose Fetch or AI Web Agent to inspect the original listing.";
  $("detailModal").classList.remove("hidden");
 }));
}
function profile(){return {name:$("name").value,role:$("role").value,skills:$("skills").value,location:$("location").value,level:$("level").value,work_mode:$("workMode").value};}
$("profileForm").addEventListener("submit",async e=>{
 e.preventDefault();const btn=$("searchBtn");btn.disabled=true;btn.innerHTML="Searching the live web… <b>✳</b>";
 $("resultsState").classList.remove("hidden");$("resultsState").querySelector("h3").textContent="TinyFish is searching the web…";$("resultsState").querySelector("p").textContent="Searching across internship listings and ranking results against your skills. This may take a few seconds.";
 $("resultsList").innerHTML="";
 try{
  const r=await fetch("/api/search",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(profile())});
  const data=await r.json();if(!r.ok)throw new Error(data.error||"Search failed.");
  results=data.results||[];filter="all";document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active",t.dataset.filter==="all"));
  updateCounts();renderResults();
  if(results.length)toast(`Found ${results.length} opportunities from TinyFish Search.`);
  else{$("resultsState").querySelector("h3").textContent="No matching listings surfaced yet."; $("resultsState").querySelector("p").textContent="Try a broader role title, add more skills, or change the location and search again.";}
  $("opportunities").scrollIntoView({behavior:"smooth"});
 }catch(err){$("resultsState").querySelector("h3").textContent="We couldn't complete the search."; $("resultsState").querySelector("p").textContent=err.message;toast(err.message);}
 finally{btn.disabled=false;btn.innerHTML='Find my internships <b>→</b>';}
});
document.querySelectorAll(".tab").forEach(t=>t.addEventListener("click",()=>{
 filter=t.dataset.filter;document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===t));renderResults();
}));
$("sortSelect").addEventListener("change",renderResults);
$("exportBtn").addEventListener("click",async()=>{
 const r=await fetch("/api/export",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({results:saved})});
 const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="internscout-shortlist.csv";a.click();URL.revokeObjectURL(url);
});
$("closeModal").addEventListener("click",()=>$("detailModal").classList.add("hidden"));
$("detailModal").addEventListener("click",e=>{if(e.target===$("detailModal"))$("detailModal").classList.add("hidden");});
async function inspect(mode){
 if(!currentItem?.url)return;const button=mode==="fetch"?$("fetchBtn"):$("agentBtn");
 button.disabled=true;$("agentProgress").classList.remove("hidden");$("agentProgress").textContent=mode==="fetch"?"TinyFish Fetch is reading the source page…":"TinyFish Web Agent is navigating the page and extracting structured role details…";
 $("detailOutput").textContent="Working…";
 try{
  const endpoint=mode==="fetch"?"/api/research":"/api/agent";
  const r=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:currentItem.url})});
  const data=await r.json();if(!r.ok)throw new Error(data.error||"Research failed.");
  $("detailOutput").textContent=JSON.stringify(data,null,2);
  $("agentProgress").textContent=mode==="fetch"?"Page fetch completed. Review the extracted source content below.":"Agent run completed. Review the extracted details below and verify on the original listing.";
 }catch(err){$("detailOutput").textContent=err.message;$("agentProgress").textContent="Research could not be completed.";}
 finally{button.disabled=false;}
}
$("fetchBtn").addEventListener("click",()=>inspect("fetch"));
$("agentBtn").addEventListener("click",()=>inspect("agent"));
fetch("/api/status").then(r=>r.json()).then(d=>{
 $("statusText").textContent=d.tinyfish_configured?"TinyFish connected":"API key needed";
 if(d.tinyfish_configured)$("statusDot").classList.add("ok");
}).catch(()=>{$("statusText").textContent="Backend offline";});
updateCounts();renderResults();
