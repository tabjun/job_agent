"use strict";
const $ = (selector) => document.querySelector(selector);
const titles = {guide: "처음 사용하기", search: "공고 탐색", resume: "이력서 정리", prepare: "플랫폼 이력서 전환·저장", connection: "자체 LLM 연결", examples: "사용 예시", platforms: "플랫폼 연결"};
let config, currentRun, currentResult = "baseline", view = "guide", working = false;
let profile, profileDirty = false;
let organizedProfile = null;
let syncPreview = null;
let exampleTopic = "search";
const icons = () => window.lucide?.createIcons();
const notice = (text) => { $("#notice").textContent = text; $("#notice").hidden = !text; };
const organizedActions = document.createElement("div"); organizedActions.className = "output-actions"; organizedActions.hidden = true;
organizedActions.id = "organized-actions";
for (const [id, icon, caption] of [["organized-download", "file-down", "정리 이력서 다운로드"], ["use-organized", "arrow-right", "정리 결과로 플랫폼 전환"]]) {
  const button = document.createElement("button"); button.type = "button"; button.id = id; button.className = "text-button";
  const symbol = document.createElement("i"); symbol.dataset.lucide = icon; button.append(symbol, document.createTextNode(caption)); organizedActions.append(button);
}
$("#result-body").append(organizedActions);
$("#organized-download").addEventListener("click", () => { try { ResumeFiles.download(currentRun.result.organized_profile, $("#profile-format").value); } catch (error) { notice(error.message); } });
$("#use-organized").addEventListener("click", () => {
  if (profileDirty) { notice("공통 이력서 변경사항을 먼저 반영·검수하세요."); return; }
  if (!confirm("이 정리 결과의 내용과 순서를 검수했으며 플랫폼 이력서 전환에 사용하시겠습니까? 공통 원본은 변경하지 않습니다.")) return;
  organizedProfile = structuredClone(currentRun.result.organized_profile);
  $("#conversion-source option[value=organized]").disabled = false; $("#conversion-source").value = "organized";
  switchView("prepare");
});
for (const [key, icon] of [["connection", "plug"], ["platforms", "monitor-check"], ["examples", "book-open"]]) {
  const button = document.createElement("button"); button.className = "nav"; button.dataset.view = key;
  if (key === "connection") button.classList.add("operator-only");
  const symbol = document.createElement("i"); symbol.dataset.lucide = icon;
  button.append(symbol, document.createTextNode(titles[key])); $("nav").append(button);
}

async function api(path, payload) {
  if (window.workspaceTransport) return window.workspaceTransport(path, payload);
  const headers = {"X-Session-Token": config?.token || ""};
  if (config?.admin_token) headers["X-Admin-Token"] = config.admin_token;
  if (payload !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {method: payload === undefined ? "GET" : "POST", headers, body: payload === undefined ? undefined : JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "요청 실패");
  return result;
}

function modelChanged(reset = true) {
  const provider = $("#provider").value;
  const enabled = provider !== "none";
  $("#model-label").hidden = !enabled;
  $("#ai-consent-label").hidden = !enabled;
  if (reset) { $("#model").value = config?.models[provider] || ""; $("#ai-consent").checked = false; }
  $("#key-status").textContent = provider === "custom" ? (config?.providers.custom ? "자체 LLM 연결됨 · 실행 자료 전송 동의 필요" : "자체 LLM 연결 필요") : enabled ? (config?.providers[provider] ? "API 키 설정됨 · 모델 접근 권한 미검증" : "API 키 없음") : "LLM 호출 없음 · 웹 검색 API는 별도";
}

function switchView(next) {
  if (working) return;
  view = Object.hasOwn(titles, next) && (next !== "connection" || config?.local_owner) ? next : "guide";
  document.querySelectorAll(".view").forEach(node => { node.hidden = node.id !== `${view}-view`; });
  document.querySelectorAll(".nav").forEach(node => node.classList.toggle("active", node.dataset.view === view));
  $("#page-title").textContent = titles[view];
  $("#breadcrumb").textContent = `작업 공간 / ${titles[view]}`;
  $(".model-bar").hidden = !config?.local_owner || ["guide", "prepare", "connection", "examples", "platforms"].includes(view);
  $("#profile-panel").hidden = ["guide", "search", "connection", "examples", "platforms"].includes(view);
  $("#output").hidden = ["guide", "connection", "examples", "platforms"].includes(view);
  $("#sync-panel").hidden = view !== "prepare" || (config?.public_demo && !config.local_owner);
  $("#examples-help").hidden = ["guide", "examples", "connection"].includes(view);
  window.history.replaceState(null, "", view === "examples" ? `#examples/${exampleTopic}` : `#${view}`);
  notice("");
}

function showExample(topic) {
  if (working) return;
  exampleTopic = ["profile", "search", "resume", "prepare", "platforms", "sync"].includes(topic) ? topic : "search";
  switchView("examples");
  document.querySelectorAll(".example-topic").forEach(article => { article.hidden = article.id !== `example-${exampleTopic}`; });
  document.querySelectorAll("[data-example]").forEach(button => {
    const selected = button.dataset.example === exampleTopic;
    button.setAttribute("aria-selected", String(selected)); button.tabIndex = selected ? 0 : -1;
  });
}
$("#examples-help").addEventListener("click", () => showExample(view));
document.querySelectorAll("[data-example]").forEach(button => {
  button.addEventListener("click", () => showExample(button.dataset.example));
  button.addEventListener("keydown", event => {
    const tabs = [...document.querySelectorAll("[data-example]")]; let index = tabs.indexOf(button);
    if (event.key === "ArrowRight") index = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") index = (index + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") index = 0;
    else if (event.key === "End") index = tabs.length - 1;
    else return;
    event.preventDefault(); showExample(tabs[index].dataset.example); tabs[index].focus();
  });
});
for (const [topic, selector] of [["profile", "#profile-panel .output-actions"], ["sync", "#sync-panel .section-title"]]) {
  const button = document.createElement("button"); button.type = "button"; button.className = "icon-button";
  button.title = topic === "profile" ? "공통 이력서 사용 예시" : "사이트 저장 사용 예시";
  button.setAttribute("aria-label", button.title);
  const icon = document.createElement("i"); icon.dataset.lucide = "circle-help"; button.append(icon);
  button.addEventListener("click", () => showExample(topic)); $(selector).append(button);
}
document.querySelectorAll("[data-example-action]").forEach(button => button.addEventListener("click", () => {
  if (working) return;
  const action = button.dataset.exampleAction;
  if (action === "template") { $("#template-download").click(); return; }
  if (action === "profile") { switchView("resume"); $("#profile-panel").open = true; $("#profile-panel summary").focus(); return; }
  switchView(action === "sync" ? "prepare" : action);
  if (action === "search") { $("#provider").value = "none"; modelChanged(); $("#sample").click(); $("#search-form [name=keywords]").focus(); }
  if (action === "resume") {
    $("#resume-form [name=jd]").value = "[가상 예시] Python과 SQL로 제품 데이터를 분석하고 정기 보고서를 작성하는 데이터 분석가를 찾습니다.";
    $("#resume-form [name=keywords]").value = "Python, SQL";
    notice("가상 JD만 입력했습니다. 공통 이력서는 변경하지 않았습니다.");
  }
  if (action === "sync") $("#sync-site").focus();
}));

function sourceChanged() {
  const web = $("#source").value === "web";
  $("#site-list").hidden = !web;
  $("#search-consent-label").hidden = !web;
  $("#postings-label").hidden = web;
  $("#search-form [name=search_consent]").checked = false;
  if (web && !config?.web_search) notice("TAVILY_API_KEY가 설정되어 있지 않습니다. 직접 입력을 사용할 수 있습니다.");
  else notice("");
}

function setWorking(state) {
  working = state;
  document.querySelectorAll("form button, .nav, #provider, #model, #docx, #sample, #profile-file, #profile-fields textarea, #profile-fields input, #profile-fields select, #visitor-clear").forEach(node => {
    if (state) { node.dataset.busyDisabled = String(node.disabled); node.disabled = true; }
    else if (node.dataset.busyDisabled !== undefined) { node.disabled = node.dataset.busyDisabled === "true"; delete node.dataset.busyDisabled; }
  });
  document.querySelectorAll("form").forEach(node => node.classList.toggle("busy", state));
  $("#result-status").textContent = state ? "처리 중" : currentRun ? "검수 필요" : "대기";
  $("#sync-apply").disabled = state || !syncPreview;
  $("#sync-site").disabled = state;
}

function renderReport() {
  document.querySelectorAll("[data-result]").forEach(button => {
    const selected = button.dataset.result === currentResult;
    button.classList.toggle("selected", selected); button.setAttribute("aria-selected", selected);
  });
  let text;
  if (currentResult === "json") text = JSON.stringify(currentRun, null, 2);
  else if (currentResult === "ai") text = currentRun.ai?.text || currentRun.ai?.error || "AI 결과 없음";
  else text = currentRun.result.report ?? JSON.stringify(currentRun.result, null, 2);
  $("#report").textContent = text;
}

function renderRun(run) {
  currentRun = run; currentResult = "baseline";
  $("#organized-actions").hidden = run.task !== "resume" || !run.result.organized_profile;
  $("#empty").hidden = true; $("#result-body").hidden = false;
  $("#download").disabled = false; $("#ai-tab").disabled = !run.ai;
  $("#result-status").textContent = "검수 필요";
  $("#output h2").textContent = `${titles[run.task] || run.task} 결과`;
  const metrics = $("#metrics"); metrics.replaceChildren();
  const entries = config.local_owner ? [["기본 처리", `${run.baseline_seconds}초`], ["전체", `${run.elapsed_seconds}초`], ["모드", run.provider === "none" ? "LLM 없음" : run.provider]] : [["처리 시간", `${run.elapsed_seconds}초`]];
  if (config.local_owner && run.ai?.seconds !== undefined) entries.push(["AI 처리", `${run.ai.seconds}초`]);
  if (config.local_owner && run.ai?.usage?.total_tokens !== undefined) entries.push(["토큰", run.ai.usage.total_tokens]);
  if (run.result.jobs) entries.push(["공고", `${run.result.jobs.length}개`]);
  for (const [label, value] of entries) { const span = document.createElement("span"); span.textContent = `${label}  `; const strong = document.createElement("strong"); strong.textContent = value; span.append(strong); metrics.append(span); }
  $("#jobs").replaceChildren();
  for (const [index, job] of (run.result.jobs || []).entries()) {
    const row = document.createElement("article"); row.className = "job-row";
    const number = document.createElement("span"); number.className = "job-number"; number.textContent = String(index + 1).padStart(2, "0");
    const content = document.createElement("div"); content.className = "job-content";
    const heading = document.createElement(job.url ? "a" : "strong"); heading.textContent = job.title || "제목 없음";
    if (job.url) { heading.href = job.url; heading.target = "_blank"; heading.rel = "noopener noreferrer"; }
    const excerpt = document.createElement("p"); excerpt.textContent = job.content.slice(0, 250);
    const meta = document.createElement("div"); meta.className = "job-meta"; meta.textContent = `${job.status_reason} · 일치 키워드: ${job.matched_keywords.join(", ") || "없음"}`;
    content.append(heading, excerpt, meta); row.append(number, content); $("#jobs").append(row);
  }
  $("#review-note").textContent = (run.result.notes || ["양식 변환 초안 · 입력·저장·지원 미실행"]).join(" / ");
  renderReport();
  if (run.ai?.error) notice(run.ai.error);
}

async function submit(event, task) {
  event.preventDefault(); if (working) return;
  notice(""); setWorking(true);
  try {
    const form = event.target;
    const payload = {task, provider: task === "prepare" ? "none" : $("#provider").value, model: $("#model").value, ai_consent: $("#ai-consent").checked};
    if (["resume", "prepare"].includes(task)) {
      if (profileDirty) throw new Error("공통 이력서 변경사항을 먼저 저장·검수하세요.");
      payload.profile = task === "prepare" && $("#conversion-source").value === "organized" ? organizedProfile : profile;
      if (!payload.profile) throw new Error("정리 결과를 먼저 검수하세요.");
    }
    if (task === "prepare") {
      for (const name of ["target", "form_map", "bindings"]) {
        const file = form.elements[name].files[0];
        if (file) { if (file.size > 2_000_000) throw new Error("JSON 파일은 2MB 이하여야 합니다."); payload[name] = JSON.parse(await file.text()); }
      }
    } else {
      for (const [key, value] of new FormData(form)) if (!["sites", "search_consent"].includes(key)) payload[key] = value;
      if (task === "search") { payload.sites = [...form.querySelectorAll("[name=sites]:checked")].map(node => node.value); payload.search_consent = form.elements.search_consent.checked; }
    }
    renderRun(await api("/api/run", payload));
  } catch (error) { notice(error.message); }
  finally { setWorking(false); }
}

$("#search-form").addEventListener("submit", event => submit(event, "search"));
$("#resume-form").addEventListener("submit", event => submit(event, "resume"));
$("#prepare-form").addEventListener("submit", event => submit(event, "prepare"));
document.querySelectorAll(".nav").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));
document.querySelectorAll("[data-guide-action]").forEach(button => button.addEventListener("click", () => {
  const action = button.dataset.guideAction;
  if (action === "examples") { showExample("profile"); return; }
  switchView(action === "profile" ? "resume" : action);
  if (action === "profile") { $("#profile-panel").open = true; $("#profile-panel summary").focus(); }
}));
document.querySelectorAll("[data-result]").forEach(button => button.addEventListener("click", () => { currentResult = button.dataset.result; renderReport(); }));
$("#provider").addEventListener("change", () => modelChanged());
$("#source").addEventListener("change", sourceChanged);
$("#copy").addEventListener("click", async () => { try { await navigator.clipboard.writeText($("#report").textContent); notice("결과를 복사했습니다."); } catch { notice("복사 실패. 브라우저 권한을 확인하세요."); } });
$("#download").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(currentRun, null, 2)], {type: "application/json"}));
  const link = document.createElement("a"); link.href = url; link.download = `${currentRun.task}-${currentRun.id}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
$("#sample").addEventListener("click", () => {
  $("#source").value = "manual"; sourceChanged();
  $("#search-form [name=keywords]").value = "Python, SQL";
  $("#search-form [name=postings]").value = JSON.stringify([
    {title: "[가상 예시] 데이터 분석가", url: "https://example.com/analyst", content: "가상 테스트 공고. Python과 SQL로 제품 데이터를 분석합니다. 마감일은 원문에서 확인합니다."},
    {title: "[가상 예시] 운영 담당자", url: "https://example.com/operations", content: "가상 테스트 공고. 운영 프로세스 개선 및 리포트 작성."}
  ], null, 2);
  notice("가상의 예시 공고입니다. 실제 채용정보가 아닙니다.");
});
$("#docx").addEventListener("change", async event => {
  const file = event.target.files[0]; if (!file) return;
  setWorking(true); notice("");
  try {
    if (file.size > 5_000_000) throw new Error("DOCX 파일은 5MB 이하여야 합니다.");
    const data = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(",")[1]); reader.onerror = reject; reader.readAsDataURL(file); });
    const result = await api("/api/extract", {data});
    const row = profile.fields.find(field => field.id === $("#docx-field").value);
    row.value = result.text; row.reviewed = false;
    delete row.items;
    row.evidence = result.paragraphs.map(p => ({source_id: result.source_id, paragraph_index: p.paragraph_index, text: p.text}));
    renderProfile(profile); markProfileDirty();
    notice(`${result.paragraphs.length}개 문단을 가져왔습니다. 항목과 내용을 검수하세요.`);
  } catch (error) { notice(error.message); }
  finally { setWorking(false); event.target.value = ""; }
});

function markProfileDirty() { profileDirty = true; organizedProfile = null; $("#conversion-source option[value=organized]").disabled = true; $("#conversion-source").value = "profile"; $("#profile-status").textContent = "저장 전 변경 있음"; syncPreview = null; $("#sync-apply").disabled = true; $("#sync-consent").checked = false; }

function renderProfile(data) {
  profile = data; profileDirty = false;
  for (const [id, definition] of Object.entries(ResumeForms.schema)) if (!data.fields.some(row => row.id === id)) data.fields.push({id, label: definition.label, value: "", reviewed: false, evidence: []});
  const populated = data.fields.filter(row => row.value.trim());
  $("#profile-status").textContent = `${populated.length}개 항목 · 미검수 ${populated.filter(row => !row.reviewed).length}개`;
  $("#profile-fields").replaceChildren(); $("#docx-field").replaceChildren();
  const basicOrder = ["name", "email", "phone", "headline", "summary", "department", "employment_type", "cover_letter"];
  const displayFields = [...data.fields].sort((a, b) => {
    const rank = row => ResumeForms.schema[row.id] ? 100 : basicOrder.includes(row.id) ? basicOrder.indexOf(row.id) : 99;
    return rank(a) - rank(b);
  });
  for (const row of displayFields) {
    const option = document.createElement("option"); option.value = row.id; option.textContent = row.label; $("#docx-field").append(option);
    if (row.id === "award_certification_description" && !row.value) continue;
    const block = document.createElement("div"); block.className = "profile-field"; block.dataset.field = row.id;
    const label = document.createElement("label"); label.textContent = row.label;
    const text = document.createElement(["summary", "cover_letter", "award_certification_description"].includes(row.id) ? "textarea" : "input"); text.rows = row.value ? 5 : 2; text.value = row.value;
    if (row.id === "email") text.type = "email";
    else if (row.id === "phone") text.type = "tel";
    const review = document.createElement("label"); review.className = "consent";
    const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.checked = row.reviewed;
    checkbox.addEventListener("change", () => {
      row.reviewed = checkbox.checked;
      if (row.reviewed && row.value.trim() && !row.evidence.length) row.evidence = [{source_id: "user-confirmed", paragraph_index: 0, text: row.value}];
      markProfileDirty();
    });
    text.addEventListener("input", () => { row.value = text.value; row.reviewed = false; checkbox.checked = false; markProfileDirty(); });
    const structured = ResumeForms.render(row, block, () => { checkbox.checked = false; markProfileDirty(); });
    label.append(text); review.append(checkbox, document.createTextNode("원문·사실 검수 완료"));
    const sources = document.createElement("details"); const summary = document.createElement("summary"); summary.textContent = `출처 근거 ${row.evidence.length}개`;
    const evidence = document.createElement("pre"); evidence.textContent = row.evidence.map(ref => `[${ref.source_id}:${ref.paragraph_index}] ${ref.text}`).join("\n\n");
    sources.append(summary, evidence); if (!structured) block.append(label); block.append(review, sources); $("#profile-fields").append(block);
  }
  $("#docx-field").value = data.fields.some(row => row.id === "experience_description") ? "experience_description" : data.fields[0]?.id || "";
  icons();
}

$("#profile-form").addEventListener("submit", async event => {
  event.preventDefault(); if (working) return; setWorking(true);
  try {
    for (const row of profile.fields) if (row.value.trim() && !row.evidence.length) row.evidence = [{source_id: "user-entered", paragraph_index: 0, text: row.value}];
    renderProfile(await api("/api/profile", {profile}));
    $("#profile-feedback").textContent = ["memory", "browser_memory"].includes(config.data_retention) ? "임시 반영 완료 · 변경된 항목은 재검수 필요" : "저장 완료 · 변경된 항목은 재검수 필요";
    notice("");
  } catch (error) { notice(error.message); } finally { setWorking(false); }
});

$("#profile-file").addEventListener("change", async event => {
  const file = event.target.files[0]; if (!file || working) return;
  setWorking(true);
  try {
    if (profileDirty && !confirm("현재 변경사항을 가져온 파일로 바꾸시겠습니까? 보관이 필요하면 먼저 다운로드하세요.")) return;
    const imported = await ResumeFiles.read(file, await api("/api/profile/template"));
    renderProfile(await api("/api/profile/import", {document: imported.document})); markProfileDirty();
    notice(imported.unstructured ? "일반 DOCX 원문을 소개 칸에 보존했습니다. 항목별로 옮겨 작성하고 검수하세요." : "표준 이력서를 가져왔습니다. 검수 후 반영하세요.");
  } catch (error) { notice(error.message); } finally { setWorking(false); event.target.value = ""; }
});

$("#profile-download").addEventListener("click", () => {
  if (!profile) return;
  try { ResumeFiles.download(profile, $("#profile-format").value); } catch (error) { notice(error.message); }
});

$("#template-download").addEventListener("click", async () => {
  try {
    const template = await api("/api/profile/template");
    ResumeFiles.download(template, $("#profile-format").value, true);
  } catch (error) { notice(error.message); }
});

function renderSync(preview) {
  syncPreview = preview; $("#sync-consent").checked = false;
  $("#sync-url").textContent = preview.url; $("#sync-fields").replaceChildren();
  for (const row of preview.profile_fields) {
    const block = document.createElement("div"); block.className = "sync-field";
    const label = document.createElement("label"); label.textContent = profile.fields.find(f => f.id === row.id)?.label || row.id;
    const select = document.createElement("select"); select.dataset.fieldId = row.id;
    const none = document.createElement("option"); none.value = ""; none.textContent = "업데이트하지 않음"; select.append(none);
    preview.fields.forEach((target, index) => {
      const option = document.createElement("option"); option.value = index;
      option.textContent = `${(target.labels || []).join(" · ") || target.placeholder || target.name || target.selector} (${target.selector})`; select.append(option);
    });
    const saved = preview.saved_mappings.find(mapping => mapping.field_id === row.id) || (preview.suggested_mappings || []).find(mapping => mapping.field_id === row.id && !preview.saved_mappings.some(existing => existing.target_index === mapping.target_index));
    if (saved) select.value = saved.target_index;
    const details = document.createElement("details"); const summary = document.createElement("summary"); summary.textContent = `전송할 내용 · ${row.value.length}자`;
    const text = document.createElement("pre"); text.textContent = row.value; details.append(summary, text); label.append(select); block.append(label, details); $("#sync-fields").append(block);
  }
  $("#sync-save").replaceChildren();
  const placeholder = document.createElement("option"); placeholder.value = ""; placeholder.textContent = "저장 동작 선택"; $("#sync-save").append(placeholder);
  if (preview.autosave_available) { const option = document.createElement("option"); option.value = "autosave"; option.textContent = "원티드 자동저장 · 재접속 확인"; $("#sync-save").append(option); }
  preview.buttons.forEach((button, index) => { const option = document.createElement("option"); option.value = index; option.textContent = `${button.label} (${button.selector})`; $("#sync-save").append(option); });
  if (preview.saved_save_index !== null) $("#sync-save").value = preview.saved_save_index;
  else if (preview.suggested_save_index != null) $("#sync-save").value = preview.suggested_save_index;
  $("#sync-result").hidden = true;
}

async function syncOperation(operation) {
  if (working) return; setWorking(true); notice("");
  try {
    if (profileDirty && ["capture", "apply"].includes(operation)) throw new Error("공통 이력서 변경사항을 먼저 저장·검수하세요.");
    const payload = {operation, site: $("#sync-site").value};
    if (["capture", "apply"].includes(operation)) payload.profile = $("#conversion-source").value === "organized" ? organizedProfile : profile;
    if (operation === "apply") {
      if (!syncPreview || !$("#sync-consent").checked) throw new Error("미리보기와 입력·저장 동의를 확인하세요.");
      if (!$("#sync-save").value) throw new Error("저장 동작을 선택하세요.");
      payload.nonce = syncPreview.nonce; payload.consent = true;
      payload.mappings = [...document.querySelectorAll("#sync-fields select")].filter(select => select.value !== "").map(select => ({field_id: select.dataset.fieldId, target_index: Number(select.value)}));
      payload.autosave = $("#sync-save").value === "autosave";
      payload.save_index = payload.autosave ? null : Number($("#sync-save").value);
      syncPreview = null; $("#sync-consent").checked = false;
    }
    const result = await api("/api/sync", payload);
    if (operation === "capture") renderSync(result);
    else if (operation === "apply") {
      $("#sync-result").hidden = false; $("#sync-result").textContent = `${result.site}: ${result.status === "saved_verified" ? "저장 확인 완료" : "저장 확인 필요"}\n${result.message}\n항목: ${result.changed_fields.join(", ")}`;
      window.dispatchEvent(new CustomEvent("portal-saved", {detail: result}));
    } else { syncPreview = null; $("#sync-auth-status").textContent = result.message || "전용 브라우저를 닫았습니다. 재접속하면 인증 상태를 다시 확인하세요."; notice(result.message || "브라우저를 닫았습니다."); if (operation === "close_site") window.dispatchEvent(new CustomEvent("portal-closed", {detail: result})); }
  } catch (error) { notice(error.message); }
  finally { setWorking(false); }
}

$("#sync-open").addEventListener("click", () => syncOperation("open"));
$("#sync-capture").addEventListener("click", () => syncOperation("capture"));
$("#sync-status").addEventListener("click", async () => {
  if (working) return; setWorking(true);
  try { const result = await api("/api/sync", {operation: "status", site: $("#sync-site").value}); $("#sync-auth-status").textContent = result.message; }
  catch (error) { notice(error.message); }
  finally { setWorking(false); }
});
$("#sync-close").addEventListener("click", () => syncOperation("close_site"));
$("#sync-form").addEventListener("submit", event => { event.preventDefault(); syncOperation("apply"); });
$("#sync-site").addEventListener("change", () => { syncPreview = null; $("#sync-fields").replaceChildren(); $("#sync-url").textContent = ""; $("#sync-save").replaceChildren(); $("#sync-consent").checked = false; $("#sync-apply").disabled = true; $("#sync-result").hidden = true; $("#sync-auth-status").textContent = "선택한 사이트의 전용 브라우저에서 로그인·2차 인증을 직접 완료하세요."; });

$("#connection-preset").addEventListener("change", event => {
  const urls = {ollama: "http://127.0.0.1:11434/v1", lmstudio: "http://127.0.0.1:1234/v1", vllm: "http://127.0.0.1:8000/v1"};
  if (urls[event.target.value]) $("#connection-url").value = urls[event.target.value];
  $("#connection-consent").checked = false;
});
$("#connection-form").addEventListener("submit", async event => {
  event.preventDefault(); if (working) return; setWorking(true);
  try {
    await api("/api/model-connection", {base_url: $("#connection-url").value, model: $("#connection-model").value, api_key: $("#connection-key").value, connection_consent: $("#connection-consent").checked});
    $("#connection-key").value = ""; config = await api("/api/config");
    $("#connection-status").textContent = "연결 설정 적용됨 · 서버 응답은 모델 목록에서 확인";
    $("#provider").value = "custom"; modelChanged(); notice("자체 LLM 연결을 적용했습니다. 키는 서버 메모리에만 보관됩니다.");
  } catch (error) { notice(error.message); }
  finally { setWorking(false); }
});
$("#model-list").addEventListener("click", async () => {
  try {
    const result = await api("/api/model-list", {}); $("#available-models").replaceChildren();
    for (const name of result.models) { const option = document.createElement("option"); option.value = name; $("#available-models").append(option); }
    $("#connection-status").textContent = `서버 연결 확인 · 모델 ${result.models.length}개`;
  } catch (error) { notice(error.message); }
});
const providerNames = {none: "기본 · LLM 없음", custom: "AI · 자체 LLM", openai: "AI · OpenAI", gemini: "AI · Gemini"};
function applyProviderOptions() {
  const selected = $("#provider").value;
  $("#provider").replaceChildren(...config.allowed_providers.map(value => {
    const option = document.createElement("option"); option.value = value; option.textContent = providerNames[value]; return option;
  }));
  $("#provider").value = config.allowed_providers.includes(selected) ? selected : "none";
  modelChanged($("#provider").value !== selected);
}
$("#visitor-clear").addEventListener("click", async () => {
  if (working || !window.confirm("이력서·결과·작성 중인 입력을 삭제할까요? 다운로드한 파일은 삭제되지 않습니다.")) return;
  setWorking(true);
  try {
    await api("/api/session/clear", {});
    document.querySelectorAll("form").forEach(form => form.reset());
    currentRun = null; profile = null;
    for (const id of ["profile-fields", "report", "jobs"]) $(`#${id}`).replaceChildren();
    location.reload();
  } catch (error) { notice(error.message); setWorking(false); }
});

function privacyNotice() {
  const memory = config.data_retention === "memory";
  const browserMemory = config.data_retention === "browser_memory";
  $("#visitor-clear").hidden = !memory && !browserMemory;
  if (browserMemory) {
    $("#privacy-summary").textContent = "이력서·결과는 이 탭의 임시 메모리에 보관합니다. 실행 자료는 서버에서 일시 처리하며 파일·DB로 저장하지 않습니다. 보관은 내 기기로 다운로드할 때만 합니다.";
    $("#privacy-storage").textContent = "공통 이력서 반영·가져오기는 브라우저 메모리에서 처리합니다. 실행할 때만 필요한 이력서·JD·양식을 서버에 전송하며 요청이 끝나면 앱의 메모리 참조를 정리합니다. 서버 파일·DB·내용 로그로 보관하지 않습니다. 새로고침하거나 임시 데이터 삭제를 누르면 이 탭의 입력·현재 결과가 초기화됩니다. 이전 실행 기록은 제공하지 않습니다.";
    $("#privacy-browser").textContent = "이력서·결과를 localStorage/IndexedDB에 자동 저장하거나 서비스 세션 쿠키를 설정하지 않습니다. 다른 탭·기기와 자동 공유하지 않습니다. 다운로드·클립보드·브라우저/OS 복원·스왑·덤프는 사용자 기기에서 관리해야 합니다.";
    $("#privacy-network").textContent = "공개 호스팅 제공자가 HTTPS 접속과 서버 요청을 처리합니다. IP·접속 정보 등 제공자 로그는 제공자 정책과 설정에 따릅니다. 앱의 내용 로그 미기록과 인프라 전체 무저장은 다릅니다. 자동 저장 연결은 사용자의 본인 PC에서 별도로 수행합니다.";
    $("#visitor-notice").textContent = "이 탭의 임시 작업 공간입니다 · 새로고침 전 다운로드 · 사이트 저장은 본인 PC 연결 필요";
    $("#review-note").textContent = "검수 필요 · 결과는 이 탭의 임시 메모리에만 보관";
    $("#profile-form button[type=submit]").lastChild.textContent = "공통 이력서 임시 반영";
  } else if (memory) {
    $("#privacy-summary").textContent = "이력서·결과는 서버 파일로 저장하지 않습니다. 임시 메모리 처리 후 삭제하며, 보관은 내 기기로 다운로드할 때만 합니다.";
    const minutes = Math.round(config.session_ttl_seconds / 60);
    $("#privacy-storage").textContent = `이력서·결과를 앱의 서버 파일·DB·내용 로그로 저장하지 않습니다. 임시 세션 메모리에만 보관하며, 세션 시작 후 ${minutes}분이 지나면 접근이 만료되고 60초 이내 정리됩니다. 임시 데이터 삭제 또는 서버 정상 종료 시에도 메모리 참조를 제거합니다. 탭을 닫는 것만으로 서버 데이터가 즉시 삭제되지는 않습니다.`;
    $("#privacy-browser").textContent = "브라우저에는 세션 식별 쿠키만 설정하며 이력서·결과를 localStorage/IndexedDB에 자동 보관하지 않습니다. 보관은 사용자가 내 기기로 다운로드할 때만 합니다. 쿠키 삭제는 접근만 끊으며 서버의 즉시 삭제와는 다릅니다. OS의 스왑·충돌 덤프나 Cloudflare 로그까지 앱이 통제하지는 못합니다.";
    $("#visitor-notice").textContent = `서버 파일로 저장하지 않는 임시 작업 공간입니다. 세션 시작 후 ${minutes}분 만료 · 보관은 내 기기로 다운로드 · 하단에서 임시 데이터 삭제 가능`;
    $("#review-note").textContent = "검수 필요 · 결과는 임시 메모리에만 보관";
    $("#profile-form button[type=submit]").lastChild.textContent = "공통 이력서 임시 반영";
  } else {
    $("#privacy-summary").textContent = "이 개인 작업 공간은 운영자의 로컬 파일 저장을 사용합니다. 공개 체험의 메모리 전용 처리와 다릅니다.";
    $("#privacy-storage").textContent = "이 개인 작업 공간의 이력서·결과는 운영자의 로컬 파일로 저장되며 자동 만료되지 않습니다. 선택한 모델/검색 서비스 사용 시 요청 자료가 해당 서비스로 전송될 수 있습니다. 공개 체험의 메모리 전용 처리와는 별개입니다.";
  }
  $("#privacy-contact").textContent = config.privacy_contact ? `운영자 문의처: ${config.privacy_contact}` : "운영자 문의처: 미등록";
}

async function initialize() {
  icons(); $("#today").textContent = new Date().toLocaleDateString("ko-KR");
  try { config = await api("/api/config");
    ResumeForms.setSchema(await api("/api/profile/schema"));
    document.body.classList.toggle("local-owner", config.local_owner);
    const visitor = config.public_demo && !config.local_owner;
    $("#visitor-notice").hidden = !visitor;
    $("#profile-panel .source-line").hidden = visitor;
    privacyNotice();
    $(".model-bar").hidden = !config.local_owner;
    if (!config.local_owner) {
      $("[data-result=baseline]").textContent = "결과";
      $("#ai-tab").textContent = "추가 분석";
      $("#ai-tab").hidden = true;
      $("[data-result=json]").hidden = true;
    }
    applyProviderOptions();
    if (config.web_search && !$("#source option[value=web]")) { const option = document.createElement("option"); option.value = "web"; option.textContent = "웹 검색 · Tavily API"; $("#source").append(option); }
    renderProfile(await api("/api/profile")); modelChanged(); if (config.web_search) $("#source").value = "web"; sourceChanged();
    $(".local-badge").lastChild.textContent = config.local_owner ? "LOCAL" : "REMOTE";
    $("#connection-form").hidden = !config.local_owner;
    $(".nav[data-view=connection]").hidden = !config.local_owner;
    if (config.local_owner) { const settings = await api("/api/model-connection"); $("#connection-url").value = settings.base_url; $("#connection-model").value = settings.model; }
    const requested = location.hash.slice(1).split("/");
    if (requested[0] === "examples") showExample(requested[1]);
    else switchView(requested[0] || "guide");
    window.dispatchEvent(new Event("workspace-ready"));
  }
  catch (error) { notice(`초기화 실패: ${error.message}`); }
}
initialize();
setInterval(async () => {
  if (!config || config.local_owner || working) return;
  try { config = await api("/api/config"); applyProviderOptions(); }
  catch { /* Requests remain server-guarded if the sharing session expires. */ }
}, 15000);
