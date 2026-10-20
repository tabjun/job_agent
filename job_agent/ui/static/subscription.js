"use strict";
(() => {
  const $ = selector => document.querySelector(selector);
  const sites = {catch:"캐치", jobkorea:"잡코리아", saramin:"사람인", wanted:"원티드", incruit:"인크루트"};
  let token = "", editing = null, state = null, busy = false, ready = false;
  function notice(value) { $("#notice").textContent = value; }
  function node(tag, text) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; }
  async function call(payload) {
    const response = await fetch("/api/subscribe", {method:"POST", credentials:"omit", cache:"no-store",
      headers:{"Content-Type":"application/json", ...(token ? {Authorization:`Bearer ${token}`} : {})},body:JSON.stringify(payload)});
    const result = await response.json(); if (!response.ok) throw new Error(result.error || "서버 연결에 실패했습니다."); return result;
  }
  async function action(work) {
    if (busy || !ready) return; busy = true; document.querySelectorAll("button").forEach(b=>{b.disabled=true;}); notice("");
    try { await work(); } catch(error) { notice(error.message); }
    finally { busy=false; document.querySelectorAll("button").forEach(b=>{b.disabled=!ready;}); }
  }
  function fill(alert) {
    editing = alert?.id || null;
    if (!alert) { $("#subscription-form").reset(); for (const box of $("#platforms").querySelectorAll("input")) box.checked=true; return; }
    $("#name").value = alert.name;
    const rule = Object.values(alert.platforms)[0];
    for (const key of ["role","location","keywords","exclude"]) $(`#${key}`).value = rule[key] || "";
    $("#experience").value = rule.experience === null ? "all" : "early";
    for (const input of $("#platforms").querySelectorAll("input")) input.checked = Boolean(alert.platforms[input.value]);
    $("#frequency").value = alert.schedule.frequency; $("#hour").value = String(alert.schedule.hour);
    $("#max-results").value = alert.max_results; $("#search-consent").checked = false; $("#storage-consent").checked = false;
  }
  async function refresh() {
    state = await call({action:"status"}); $("#conditions").hidden = false; $("#subscriptions").hidden = false;
    const list = $("#subscription-list"); list.replaceChildren();
    if (!state.alerts.length) list.append(node("p","등록된 구독이 없습니다."));
    for (const alert of state.alerts) {
      const row = node("article"); row.className = "subscription-row";
      row.append(node("strong",alert.name),node("p",`${state.email} · ${Object.keys(alert.platforms).map(s=>sites[s]).join(" · ")} · ${alert.enabled ? "발송 예정" : "중지"}`));
      row.append(node("p",`한국 시간 ${alert.schedule.hour}시 이후 · 메일당 최대 ${alert.max_results}건 · 최근 상태: ${alert.last_status || "예약 대기"}`));
      for (const [caption,work] of [["수정",()=>{fill(alert);$("#conditions").scrollIntoView({behavior:"smooth"});}],
        ["구독 삭제",async()=>{if(confirm("이 구독 조건과 발송 기록을 삭제할까요?")){await call({action:"delete",id:alert.id});await refresh();}}]]) {
        const button=node("button",caption);button.type="button";button.className="secondary";button.addEventListener("click",()=>action(work));row.append(button);
      }
      list.append(row);
    }
  }
  for (const [key,caption] of Object.entries(sites)) {
    const label=node("label");const box=node("input");box.type="checkbox";box.value=key;box.checked=true;
    label.append(box,document.createTextNode(caption));$("#platforms").append(label);
  }
  $("#code-form").addEventListener("submit",event=>{event.preventDefault();action(async()=>{await call({action:"request_code",email:$("#email").value.trim(),auth_consent:$("#auth-consent").checked});notice("메일로 인증 코드를 보냈습니다. 코드를 입력해주세요.");});});
  $("#verify-form").addEventListener("submit",event=>{event.preventDefault();action(async()=>{const result=await call({action:"verify",email:$("#email").value.trim(),code:$("#code").value.trim()});token=result.access_token;$("#code").value="";await refresh();notice("이메일 인증 완료. 조건을 저장하면 서버에서 예약 발송합니다.");});});
  $("#subscription-form").addEventListener("submit",event=>{event.preventDefault();action(async()=>{
    const rule={};for(const key of ["role","location","keywords","exclude"])rule[key]=$(`#${key}`).value.trim();
    rule.experience=$("#experience").value==="all"?null:{entry:true,any:true,min_years:1,max_years:5};
    const platforms={};for(const input of $("#platforms").querySelectorAll("input:checked"))platforms[input.value]={...rule};
    await call({action:"save",id:editing,name:$("#name").value.trim(),platforms,
      schedule:{frequency:$("#frequency").value,hour:Number($("#hour").value),weekday:0},max_results:Number($("#max-results").value),
      search_consent:$("#search-consent").checked,storage_consent:$("#storage-consent").checked});
    await refresh();fill(null);notice("서버 저장 완료. PC가 꺼져 있어도 예약 발송합니다.");
  });});
  $("#reset").addEventListener("click",()=>fill(null));
  const fragment=new URLSearchParams(location.hash.slice(1));const unsubscribe=fragment.get("unsubscribe");
  if (unsubscribe) { $("#unsubscribe").hidden=false;history.replaceState(null,"",location.pathname); }
  $("#unsubscribe-confirm").addEventListener("click",()=>action(async()=>{await call({action:"unsubscribe",token:unsubscribe});notice("수신 해지가 완료됐습니다.");$("#unsubscribe").hidden=true;}));
  $("#delete-account").addEventListener("click",()=>action(async()=>{
    if(!confirm("인증 계정, 모든 구독 조건과 서비스 내 발송 기록을 삭제할까요?"))return;
    await call({action:"delete_account"});token="";state=null;$("#conditions").hidden=true;$("#subscriptions").hidden=true;notice("계정과 구독 정보를 삭제했습니다.");
  }));
  document.querySelectorAll("button").forEach(b=>{b.disabled=true;});
  fetch("/api/subscribe",{cache:"no-store",credentials:"omit"}).then(r=>r.json()).then(result=>{
    ready=result.ready===true;$("#service-state").textContent=result.message;document.querySelectorAll("button").forEach(b=>{b.disabled=!ready;});
  }).catch(()=>{$("#service-state").textContent="서버 연결을 확인하지 못했습니다. 잠시 후 다시 접속해주세요.";});
  if (window.lucide) window.lucide.createIcons();
})();
