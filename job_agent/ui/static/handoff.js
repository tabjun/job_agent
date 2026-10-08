"use strict";
(() => {
  let pending = null, popup = null, offer = null, localOrigin = "", timer;
  const status = text => { $("#device-status").textContent = text; };
  function route() {
    const name = $("#platform-site").selectedOptions[0]?.textContent || "사이트";
    $("#platform-route").textContent = `${name}: 전용 브라우저 로그인 → 2차 인증 완료 → 이력서 관리에서 기존 이력서 수정 → 필드 검수·저장`;
  }
  window.addEventListener("workspace-ready", () => {
    $("#platform-site").replaceChildren(...[...$("#sync-site").options].map(option => option.cloneNode(true)));
    route();
    $("#device-command").textContent = `uv sync --extra browser\nuv run job-agent ui --port 8780 --handoff-origin '${location.origin}'`;
    $("#device-setup").hidden = config.local_owner;
    $("#device-local").hidden = !config.local_owner;
    $("#device-connect-step").hidden = config.local_owner;
    $("#platform-start").hidden = !config.local_owner;
    if (config.local_owner && config.handoff_origin && window.opener) {
      window.opener.postMessage({type: "resume-workspace.ready"}, config.handoff_origin);
    }
  });
  $("#platform-site").addEventListener("change", route);
  $("#platform-start").addEventListener("click", () => {
    if (!config.local_owner) return;
    $("#sync-site").value = $("#platform-site").value;
    $("#sync-site").dispatchEvent(new Event("change"));
    switchView("prepare"); $("#sync-panel").scrollIntoView({behavior: "smooth"});
  });
  $("#device-command-copy").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($("#device-command").textContent); notice("실행 명령을 복사했습니다."); }
    catch { notice("클립보드 권한을 확인하세요."); }
  });
  $("#local-kit-download").addEventListener("click", async () => {
    try {
      const response = await fetch(config.local_kit_url || "/api/local-kit", {headers: config.local_kit_url ? {} : {"X-Session-Token": config.token}});
      if (!response.ok) throw new Error("연결 도구 다운로드 실패");
      const files = window.fflate.unzipSync(new Uint8Array(await response.arrayBuffer()));
      files["connector.json"] = new TextEncoder().encode(JSON.stringify({origin: location.origin}));
      const url = URL.createObjectURL(new Blob([window.fflate.zipSync(files)], {type: "application/zip"}));
      const link = document.createElement("a"); link.href = url; link.download = "resume-local-connector.zip"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { notice(error.message); }
  });
  $("#device-open").addEventListener("click", () => {
    try {
      if (working || config.local_owner) return;
      if (!$("#device-consent").checked) throw new Error("본인 PC로 이력서 전달에 동의하세요.");
      if (profileDirty) throw new Error("공통 이력서 변경사항을 먼저 임시 반영·검수하세요.");
      const address = new URL($("#device-url").value);
      if (address.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(address.hostname) || !address.port || address.username || address.password || address.search || address.hash || !["", "/"].includes(address.pathname)) throw new Error("본인 PC의 http://127.0.0.1:포트 주소만 연결할 수 있습니다.");
      localOrigin = address.origin;
      const selection = window.PortalWorkflow.offer();
      offer = {type: "resume-workspace.offer", request_id: crypto.randomUUID(), site: selection.sites[0], sites: selection.sites, profile: selection.profile};
      if (JSON.stringify(offer.profile).length > 2_000_000) throw new Error("연결할 이력서는 2MB 이하여야 합니다. 다운로드 후 로컬에서 직접 업로드하세요.");
      notice("");
      popup = window.open(`${localOrigin}/#platforms`, "_blank");
      if (!popup) throw new Error("팝업을 허용한 뒤 다시 연결하세요.");
      status("로컬 창 연결 대기");
      clearTimeout(timer); timer = setTimeout(() => status("연결 미확인 · 본인 PC의 실행 주소·허용 웹 주소·팝업을 확인하세요"), 12000);
    } catch (error) { notice(error.message); }
  });
  window.addEventListener("message", event => {
    const data = event.data;
    if (!data || typeof data !== "object") return;
    if (popup && event.source === popup && event.origin === localOrigin && offer) {
      if (data.type === "resume-workspace.ready") {
        clearTimeout(timer); popup.postMessage(offer, localOrigin); status("내 PC에서 가져오기 승인 대기");
      } else if (data.type === "resume-workspace.accepted" && data.request_id === offer.request_id) {
        status("이력서 전달 완료 · 로그인은 로컬 창에서 진행"); notice(""); offer = null;
      } else if (data.type === "resume-workspace.rejected" && data.request_id === offer.request_id) {
        status("본인 PC에서 가져오기를 거절했습니다"); offer = null;
      }
      return;
    }
    if (!config?.local_owner || !config.handoff_origin || !window.opener || event.source !== window.opener || event.origin !== config.handoff_origin || data.type !== "resume-workspace.offer") return;
    try {
      if (!/^[0-9a-f-]{36}$/.test(data.request_id) || !config.sites.includes(data.site) || data.profile?.format !== "job-agent.resume/v1" || !Array.isArray(data.profile.fields) || JSON.stringify(data.profile).length > 2_000_000) return;
      const sites = data.sites === undefined ? [data.site] : data.sites;
      if (!Array.isArray(sites) || !sites.length || sites.length > 5 || new Set(sites).size !== sites.length || !sites.every(site => config.sites.includes(site)) || data.site !== sites[0]) return;
      pending = structuredClone({...data, sites});
      $("#handoff-origin").textContent = `요청한 웹사이트: ${event.origin}`;
      $("#handoff-preview").textContent = `선택한 플랫폼: ${sites.join(", ")}\n\n` + data.profile.fields.map(row => `${row.label}: ${String(row.value || "").slice(0, 500)}`).join("\n\n");
      $("#handoff-allow").checked = false; $("#handoff-accept").disabled = true;
      $("#handoff-approval").hidden = false;
    } catch { /* Malformed offers have no effect on local data or browser sessions. */ }
  });
  $("#handoff-allow").addEventListener("change", () => { $("#handoff-accept").disabled = !$("#handoff-allow").checked; });
  $("#handoff-reject").addEventListener("click", () => {
    if (pending) window.opener.postMessage({type: "resume-workspace.rejected", request_id: pending.request_id}, config.handoff_origin);
    pending = null; $("#handoff-preview").textContent = ""; $("#handoff-approval").hidden = true;
  });
  $("#handoff-accept").addEventListener("click", async () => {
    if (working || !pending || !$("#handoff-allow").checked) return;
    const incoming = pending; setWorking(true); $("#handoff-accept").disabled = true;
    try {
      renderProfile(await api("/api/profile/import", {document: incoming.profile})); markProfileDirty();
      window.PortalWorkflow.receive(incoming.sites);
      $("#sync-site").value = incoming.site; $("#sync-site").dispatchEvent(new Event("change"));
      window.opener.postMessage({type: "resume-workspace.accepted", request_id: incoming.request_id}, config.handoff_origin);
      pending = null; $("#handoff-preview").textContent = ""; $("#handoff-approval").hidden = true;
      setWorking(false); switchView("prepare"); $("#profile-panel").open = true;
      notice("이력서를 가져왔습니다. 내용을 다시 검수·반영한 뒤 선택한 플랫폼으로 진행을 누르세요. 로그인 세션은 이 PC에서만 재사용하며 아직 사이트에 입력·저장하지 않았습니다.");
    } catch (error) { notice(error.message); }
    finally { setWorking(false); $("#handoff-accept").disabled = !pending || !$("#handoff-allow").checked; }
  });
})();
