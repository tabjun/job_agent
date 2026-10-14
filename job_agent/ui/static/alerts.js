"use strict";
(() => {
  const frequencies = {daily: "매일", weekdays: "평일", weekly: "매주"};
  const days = "월화수목금토일";
  let state = null, editing = null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function button(icon, caption, handler, primary = false) {
    const node = element("button", primary ? "primary" : "text-button"); node.type = "button";
    const symbol = element("i"); symbol.dataset.lucide = icon; node.append(symbol, document.createTextNode(caption));
    node.addEventListener("click", handler); return node;
  }
  async function call(payload, done) {
    if (working) return;
    setWorking(true); notice("");
    try { const result = await api("/api/alerts", payload); await done(result); }
    catch (error) { notice(error.message); }
    finally { setWorking(false); }
  }

  function buildPlatforms() {
    const holder = $("#alert-platforms"); holder.replaceChildren();
    for (const {key, name} of state.platforms) {
      const row = element("div", "alert-platform"); row.dataset.site = key;
      const toggle = element("label", "alert-site"); const box = element("input"); box.type = "checkbox"; box.id = `alert-site-${key}`;
      toggle.append(box, document.createTextNode(name));
      const grid = element("div", "form-grid");
      for (const [field, caption, hint] of [["role", "직무", "데이터 분석가"], ["location", "지역 (여러 곳은 쉼표)", "서울, 경기"], ["keywords", "키워드", "Python, SQL"], ["exclude", "제외 키워드", "인턴, 계약직"]]) {
        const label = element("label", "", caption); const input = element("input"); input.id = `alert-${key}-${field}`; input.dataset.field = field; input.maxLength = field === "role" || field === "location" ? 100 : 300; input.placeholder = hint;
        label.append(input); grid.append(label);
      }
      box.addEventListener("change", () => { grid.setAttribute("aria-disabled", String(!box.checked)); grid.querySelectorAll("input").forEach(input => { input.disabled = !box.checked; }); });
      row.append(toggle, grid); holder.append(row);
      box.dispatchEvent(new Event("change"));
    }
  }

  function fillForm(alert) {
    editing = alert?.id || null;
    $("#alert-name").value = alert?.name || "";
    if (alert) $("#alert-target").value = alert.email;
    for (const row of document.querySelectorAll(".alert-platform")) {
      const rule = alert?.platforms[row.dataset.site];
      const box = row.querySelector("input[type=checkbox]"); box.checked = Boolean(rule); box.dispatchEvent(new Event("change"));
      row.querySelectorAll("input[data-field]").forEach(input => { input.value = rule?.[input.dataset.field] || ""; });
    }
    $("#alert-frequency").value = alert?.schedule.frequency || "weekdays";
    $("#alert-hour").value = String(alert?.schedule.hour ?? 8);
    $("#alert-weekday").value = String(alert?.schedule.weekday ?? 0);
    $("#alert-max").value = alert?.max_results || 10;
    $("#alert-enabled").checked = alert ? alert.enabled : true;
    $("#alert-consent").checked = Boolean(alert);
    $("#alert-weekday-label").hidden = $("#alert-frequency").value !== "weekly";
    $("#alert-form button[type=submit]").lastChild.textContent = editing ? "알림 수정 저장" : "알림 저장";
  }

  function scheduleText(alert) {
    const {frequency, hour, weekday} = alert.schedule;
    return `${frequency === "weekly" ? `매주 ${days[weekday]}요일` : frequencies[frequency]} ${String(hour).padStart(2, "0")}:00`;
  }

  function render(next) {
    state = next;
    const missing = [];
    if (!state.mail_configured) missing.push("메일 발송 설정(.env의 ALERT_SMTP_HOST·ALERT_SMTP_USER·ALERT_SMTP_PASSWORD)");
    if (!state.web_search) missing.push("공고 검색 키(TAVILY_API_KEY)");
    $("#alert-setup").hidden = !missing.length;
    $("#alert-setup").textContent = missing.length ? `먼저 ${missing.join("와 ")}를 설정한 뒤 작업 공간을 다시 실행하세요. 설정 방법은 docs/job_alerts.md에 있습니다.` : "";
    if (!$("#alert-platforms").children.length) { buildPlatforms(); fillForm(null); }
    const target = $("#alert-target"); const chosen = target.value; target.replaceChildren();
    for (const email of state.emails) { const option = element("option", "", email); option.value = email; target.append(option); }
    if (!state.emails.length) { const option = element("option", "", "먼저 이메일을 인증하세요"); option.value = ""; target.append(option); }
    if (state.emails.includes(chosen)) target.value = chosen;
    $("#alert-email-state").textContent = state.emails.length ? `인증 완료 ${state.emails.length}개 · 다른 주소도 추가로 인증할 수 있습니다.` : "인증한 이메일만 알림을 받을 수 있습니다. 코드는 10분간 유효합니다.";
    const emails = $("#alert-emails"); emails.replaceChildren();
    for (const email of state.emails) {
      const row = element("div", "alert-email-row"); row.append(element("span", "", `✓ ${email}`));
      row.append(button("trash-2", "인증 해제·관련 알림 삭제", () => {
        if (!confirm(`${email}의 인증과 이 주소로 가는 알림을 모두 삭제할까요?`)) return;
        call({action: "forget_email", email}, async () => { await refresh(); notice(`${email} 인증과 관련 알림을 삭제했습니다.`); });
      }));
      emails.append(row);
    }
    const list = $("#alert-list"); list.replaceChildren();
    if (!state.alerts.length) list.append(element("p", "alert-empty", "아직 등록한 알림이 없습니다."));
    for (const alert of state.alerts) {
      const row = element("article", "alert-row"); row.dataset.id = alert.id;
      const info = element("div"); const title = element("strong", "", alert.name);
      title.append(element("span", `alert-pill ${alert.enabled ? "on" : "off"}`, alert.enabled ? "켜짐" : "꺼짐"));
      const sites = Object.keys(alert.platforms).map(key => state.platforms.find(p => p.key === key)?.name || key).join(" · ");
      info.append(title, element("p", "", `${alert.email} · ${scheduleText(alert)} · ${sites} · 최대 ${alert.max_results}건`));
      info.append(element("p", "", `다음 발송 ${alert.next_run.replace("T", " ")} · 지금까지 보낸 공고 ${alert.sent_count}건${alert.last_status ? ` · 최근: ${alert.last_status}` : ""}`));
      const actions = element("div", "alert-actions");
      actions.append(
        button("pencil", "수정", () => { fillForm(alert); $("#alert-form").scrollIntoView({behavior: "smooth"}); }),
        button("eye", "미리보기", () => call({action: "run", id: alert.id, send: false}, result => { showPreview(row, result); })),
        button("send", "지금 보내기", () => {
          if (!confirm(`${alert.email}로 새 공고를 지금 보낼까요?`)) return;
          call({action: "run", id: alert.id}, async result => { await refresh(); notice(result.status); });
        }),
        button("trash-2", "삭제", () => {
          if (!confirm(`'${alert.name}' 알림을 삭제할까요?`)) return;
          call({action: "delete", id: alert.id}, result => { if (editing === alert.id) fillForm(null); render(result); notice("알림을 삭제했습니다."); });
        }),
      );
      row.append(info, actions); list.append(row);
    }
    icons();
  }

  function showPreview(row, result) {
    row.querySelector(".alert-preview")?.remove();
    notice(result.status);
    if (!result.jobs.length) return;
    const listing = element("ol", "alert-preview");
    for (const job of result.jobs) {
      const item = element("li"); const link = element("a", "", job.title); link.href = job.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      item.append(link, document.createTextNode(job.matched_keywords.length ? ` · ${job.matched_keywords.join(", ")}` : ""));
      listing.append(item);
    }
    row.append(listing);
  }

  async function refresh() { render(await api("/api/alerts")); }

  function collect() {
    const platforms = {};
    for (const row of document.querySelectorAll(".alert-platform")) {
      if (!row.querySelector("input[type=checkbox]").checked) continue;
      const rule = {}; row.querySelectorAll("input[data-field]").forEach(input => { rule[input.dataset.field] = input.value.trim(); });
      platforms[row.dataset.site] = rule;
    }
    return {
      action: "save", id: editing, name: $("#alert-name").value.trim(), email: $("#alert-target").value, platforms,
      schedule: {frequency: $("#alert-frequency").value, hour: Number($("#alert-hour").value), weekday: Number($("#alert-weekday").value)},
      max_results: Number($("#alert-max").value), enabled: $("#alert-enabled").checked, search_consent: $("#alert-consent").checked,
    };
  }

  $("#alert-send-code").addEventListener("click", () => {
    const email = $("#alert-email").value.trim();
    call({action: "request_code", email}, () => { notice(`${email}로 인증 코드를 보냈습니다. 10분 안에 입력하세요.`); $("#alert-code").focus(); });
  });
  $("#alert-email-form").addEventListener("submit", event => {
    event.preventDefault();
    call({action: "verify", email: $("#alert-email").value.trim(), code: $("#alert-code").value.trim()}, async result => {
      $("#alert-code").value = ""; await refresh(); $("#alert-target").value = result.email; notice(`${result.email} 인증을 완료했습니다. 이제 알림 조건을 저장할 수 있습니다.`);
    });
  });
  $("#alert-form").addEventListener("submit", event => {
    event.preventDefault();
    const payload = collect();
    call(payload, result => {
      const saved = payload.id ? result.alerts.find(a => a.id === payload.id) : result.alerts.at(-1);
      render(result); fillForm(null);
      notice(saved ? `'${saved.name}' 알림을 저장했습니다. 다음 발송: ${saved.next_run.replace("T", " ")}` : "알림을 저장했습니다.");
    });
  });
  $("#alert-frequency").addEventListener("change", () => { $("#alert-weekday-label").hidden = $("#alert-frequency").value !== "weekly"; });
  $("#alert-reset").addEventListener("click", () => fillForm(null));
  $("#alert-copy").addEventListener("click", () => {
    const rows = [...document.querySelectorAll(".alert-platform")].filter(row => row.querySelector("input[type=checkbox]").checked);
    const values = row => [...row.querySelectorAll("input[data-field]")].map(input => input.value);
    const origin = rows.find(row => values(row).some(Boolean));
    if (rows.length < 2 || !origin) { notice("조건을 입력한 플랫폼과 복사할 플랫폼을 함께 선택하세요."); return; }
    const source = values(origin);
    for (const row of rows) if (row !== origin) row.querySelectorAll("input[data-field]").forEach((input, index) => { input.value = source[index]; });
    notice(`${origin.querySelector(".alert-site").textContent} 조건을 복사했습니다. 플랫폼마다 다르게 고칠 수 있습니다.`);
  });
  window.addEventListener("view-changed", event => {
    if (event.detail === "alerts" && config?.local_owner) refresh().catch(error => notice(error.message));
  });
})();
