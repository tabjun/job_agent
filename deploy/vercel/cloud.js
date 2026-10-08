"use strict";
(() => {
  const copy = value => structuredClone(value);
  const settings = fetch("/workspace-config.json", {cache: "no-store"}).then(response => {
    if (!response.ok) throw new Error("공개 설정을 불러오지 못했습니다.");
    return response.json();
  });
  let storedProfile = null;
  const keysEqual = (value, keys) => value && typeof value === "object" && !Array.isArray(value) && Object.keys(value).sort().join() === [...keys].sort().join();
  const length = value => Array.from(value).length;

  function validate(document) {
    if (!keysEqual(document, ["format", "fields"]) || document.format !== "job-agent.resume/v1" || !Array.isArray(document.fields) || document.fields.length > 200) throw new Error("공통 이력서의 format/fields를 확인하세요.");
    const seen = new Set();
    for (const row of document.fields) {
      if (!keysEqual(row, "items" in row ? ["id", "label", "value", "reviewed", "evidence", "items"] : ["id", "label", "value", "reviewed", "evidence"]) || typeof row.id !== "string" || !/^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*$/.test(row.id) || length(row.id) > 120 || seen.has(row.id)) throw new Error("고유한 영문 필드 ID가 필요합니다.");
      if ("items" in row) {
        window.ResumeForms.validateItems(row.id, row.items);
        if (row.value !== window.ResumeForms.renderItems(row.id, row.items)) throw new Error("정형 항목과 표시 내용이 일치하지 않습니다.");
      }
      seen.add(row.id);
      for (const [name, limit] of [["label", 120], ["value", 30000]]) if (typeof row[name] !== "string" || length(row[name]) > limit) throw new Error("필드 문자열 또는 길이가 잘못되었습니다.");
      if (typeof row.reviewed !== "boolean" || !Array.isArray(row.evidence) || row.evidence.length > 500) throw new Error("검수 여부와 근거 배열이 필요합니다.");
      for (const ref of row.evidence) {
        if (!keysEqual(ref, ["source_id", "paragraph_index", "text"]) || typeof ref.source_id !== "string" || !ref.source_id || length(ref.source_id) > 200 || !Number.isSafeInteger(ref.paragraph_index) || ref.paragraph_index < 0 || typeof ref.text !== "string" || !ref.text.trim() || length(ref.text) > 30000) throw new Error("근거 출처·문단 번호·원문을 확인하세요.");
      }
      if (row.reviewed && row.value.trim() && !row.evidence.length) throw new Error("검수된 값에는 근거가 필요합니다.");
    }
    if (new TextEncoder().encode(JSON.stringify(document)).length > 2_000_000) throw new Error("이력서 JSON은 2MB 이하여야 합니다.");
    return copy(document);
  }

  async function imported(document, template) {
    if (!document || typeof document !== "object" || Array.isArray(document)) throw new Error("이력서 JSON 객체가 필요합니다.");
    if (document.format) {
      const profile = validate(document);
      for (const row of profile.fields) row.reviewed = false;
      return profile;
    }
    const source = document.package || document;
    if (!source.field_values || typeof source.field_values !== "object" || Array.isArray(source.field_values)) throw new Error("기존 마스터의 field_values가 필요합니다.");
    const known = new Map(template.fields.map(row => [row.id, row.label]));
    const ids = [...new Set([...Object.keys(source.field_values), ...known.keys()])];
    return validate({format: template.format, fields: ids.map(id => ({id, label: known.get(id) || id, value: source.field_values[id] ?? "", reviewed: false, evidence: source.source_evidence?.[id] || []}))});
  }

  window.workspaceTransport = async (path, payload) => {
    const options = await settings;
    const template = options.template;
    if (path === "/api/config" && payload === undefined) return {
      token: "", local_owner: false, public_demo: true, data_retention: "browser_memory",
      allowed_providers: ["none"], providers: {}, models: {}, web_search: false,
      sites: ["catch", "jobkorea", "saramin", "wanted", "incruit"],
      privacy_contact: options.privacy_contact || "", handoff_origin: "",
      local_kit_url: "/resume-local-connector.zip", cloud_hosted: true,
    };
    if (path === "/api/profile/template" && payload === undefined) return copy(template);
    if (path === "/api/profile/schema" && payload === undefined) return copy(options.schema);
    if (path === "/api/profile") {
      if (payload === undefined) return copy(storedProfile || template);
      const next = validate(payload.profile);
      const previous = new Map((storedProfile || template).fields.map(row => [row.id, row]));
      for (const row of next.fields) {
        const old = previous.get(row.id);
        if (!old || row.value !== old.value || JSON.stringify(row.evidence) !== JSON.stringify(old.evidence) || JSON.stringify(row.items) !== JSON.stringify(old.items)) row.reviewed = false;
      }
      storedProfile = validate(next);
      return copy(storedProfile);
    }
    if (path === "/api/profile/import" && payload !== undefined) return imported(payload.document, template);
    if (path === "/api/session/clear" && payload !== undefined) { storedProfile = null; return {ok: true}; }
    if (path === "/api/run" && payload !== undefined) {
      if (payload.provider !== "none" || (payload.source || "manual") !== "manual") throw new Error("공개 웹에서 허용되지 않는 작업입니다.");
      const body = JSON.stringify(payload);
      if (new TextEncoder().encode(body).length > 2_000_000) throw new Error("실행 자료는 2MB 이하여야 합니다.");
      const response = await fetch("/api/run", {method: "POST", headers: {"Content-Type": "application/json"}, body, cache: "no-store", credentials: "omit"});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "처리 실패");
      return result;
    }
    throw new Error("이 작업은 본인 PC의 연결 도구에서 수행하세요.");
  };

  window.addEventListener("workspace-ready", () => {
    document.querySelector(".local-badge").lastChild.textContent = "WEB";

  });
})();
