"use strict";
(() => {
  const names = {catch: "캐치", jobkorea: "잡코리아", saramin: "사람인", wanted: "원티드", incruit: "인크루트"};
  let queue = [], selectedProfile = null;
  const row = site => $("#portal-queue").querySelector(`[data-site="${site}"]`);
  function update(site, text) { const node = row(site); if (node) node.querySelector("p").textContent = text; }
  function getProfile() {
    const source = $("#conversion-source").value === "organized" ? organizedProfile : profile;
    if (profileDirty) throw new Error("이력서 변경사항을 먼저 반영·검수하세요.");
    if (!source || !source.fields.some(field => field.value.trim())) throw new Error("먼저 공통 이력서를 작성하세요.");
    if (source.fields.some(field => field.value.trim() && (!field.reviewed || !field.evidence.length))) throw new Error("작성한 이력서의 원문·사실 검수를 완료하세요.");
    return structuredClone(source);
  }
  function checkedSites() { return [...document.querySelectorAll("#portal-sites input:checked")].map(input => input.value); }
  function choose(sites) {
    queue = [...sites];
    document.querySelectorAll("#portal-sites input").forEach(input => { input.checked = sites.includes(input.value); });
    $("#portal-queue").replaceChildren();
    for (const site of sites) {
      const article = document.createElement("article"); article.className = "portal-row"; article.dataset.site = site;
      const title = document.createElement("strong"); title.textContent = names[site];
      const state = document.createElement("p"); state.textContent = "연결 대기 · 아직 입력·저장하지 않았습니다";
      const button = document.createElement("button"); button.type = "button"; button.className = "text-button";
      const icon = document.createElement("i"); icon.dataset.lucide = "scan-text"; button.append(icon, document.createTextNode("직접 검수"));
      button.hidden = !config.local_owner;
      button.addEventListener("click", () => preview(site));
      article.append(title, state, button); $("#portal-queue").append(article);
    }
    icons();
  }
  async function connect(sites) {
    if (working || !config.local_owner) return;
    try {
      selectedProfile = getProfile();
      choose(sites); $("#profile-panel").open = false; setWorking(true);
      let opened = 0;
      for (const site of sites) {
        try {
          await api("/api/sync", {operation: "open", site});
          opened += 1;
          const result = await api("/api/sync", {operation: "status", site});
          update(site, result.message);
        } catch (error) { update(site, error.message); }
      }
      $("#portal-status").textContent = `${opened}/${sites.length}개 사이트의 전용 브라우저를 열었습니다. 각 창에서 로그인·2차 인증만 하면 나머지(항목 연결·입력·저장·다시 읽어 확인)는 자동으로 진행합니다. 결과는 result/site_sync/auto-report.md에 남고, 나중에 보고 고치면 됩니다.`;
    } catch (error) { notice(error.message); return; }
    finally { setWorking(false); }
    await autoSave(sites);
  }
  // Retry each site until the person has logged in there; save once per site.
  async function autoSave(sites) {
    const pending = new Set(sites);
    const started = Date.now();
    while (pending.size && Date.now() - started < 20 * 60 * 1000) {
      for (const site of [...pending]) {
        if (working) break;
        try {
          setWorking(true);
          const result = await api("/api/sync", {operation: "auto", site, profile: selectedProfile});
          if (result.status === "waiting_for_person") { update(site, `로그인 대기 · ${result.message}`); continue; }
          pending.delete(site);
          update(site, result.status === "saved_verified"
            ? `자동 저장·확인 완료 · ${result.changed_fields.join(", ")}${result.not_mapped.length ? ` · 연결 못 한 항목 ${result.not_mapped.length}개` : ""}`
            : `확인 필요 · ${result.message}`);
        } catch (error) { pending.delete(site); update(site, `확인 필요 · ${error.message}`); }
        finally { setWorking(false); }
      }
      if (pending.size) await new Promise(resolve => setTimeout(resolve, 4000));
    }
    for (const site of pending) update(site, "로그인을 기다리다 멈췄습니다 · 다시 진행하면 이어서 저장합니다");
    $("#portal-status").textContent = "자동 저장을 마쳤습니다. 사이트별 결과는 result/site_sync/auto-report.md에서 확인하고 필요한 부분만 사이트에서 고치세요.";
  }
  async function preview(site) {
    if (working) return;
    try {
      selectedProfile = getProfile(); setWorking(true);
      $("#sync-site").value = site; $("#sync-site").dispatchEvent(new Event("change"));
      const result = await api("/api/sync", {operation: "capture", site, profile: selectedProfile});
      renderSync(result);
      update(site, "변환 미리보기 준비 · 제안된 연결과 저장 동작을 검수하고 승인하세요");
      $("#sync-panel").scrollIntoView({behavior: "smooth"});
    } catch (error) { update(site, error.message); notice(error.message); }
    finally { setWorking(false); }
  }
  $("#portal-setup").addEventListener("click", () => {
    choose(checkedSites());
    if (queue.length) $("#platform-site").value = queue[0];
    switchView("platforms");
  });
  $("#portal-proceed").addEventListener("click", () => {
    try {
      if (working) return;
      const sites = checkedSites();
      if (!sites.length) throw new Error("진행할 플랫폼을 하나 이상 선택하세요.");
      if (!$("#portal-consent").checked) throw new Error("본인 PC 연결·자동 입력·저장에 동의하세요. 로그인·2차 인증은 직접 합니다.");
      selectedProfile = getProfile(); choose(sites);
      if (config.local_owner) { connect(sites); return; }
      $("#platform-site").value = sites[0];
      $("#platform-site").dispatchEvent(new Event("change"));
      $("#device-consent").checked = true;
      switchView("platforms");
      $("#device-open").click();
    } catch (error) { notice(error.message); }
  });
  window.PortalWorkflow = {
    offer: () => ({sites: queue.length ? [...queue] : [$("#platform-site").value], profile: queue.length ? getProfile() : structuredClone(profile)}),
    receive(sites) { selectedProfile = null; choose(sites); $("#portal-consent").checked = false; },
  };
  window.addEventListener("portal-saved", event => {
    const result = event.detail;
    update(result.site, result.status === "saved_verified" ? "선택 항목 저장·재접속 확인 완료" : result.message);
  });
  window.addEventListener("portal-closed", event => update(event.detail.site, "브라우저 닫힘 · 세션 파일은 본인 PC에 남을 수 있습니다"));
})();
