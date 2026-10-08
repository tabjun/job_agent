"use strict";
window.ResumeForms = (() => {
  let schema;
  const empty = key => Object.fromEntries(schema[key].fields.map(field => [field.key, field.type === "checkbox" ? false : ""]));
  function renderItems(key, items) {
    return items.map(item => schema[key].fields.map(field => {
      const value = field.type === "checkbox" ? (item[field.key] ? "예" : "") : item[field.key];
      return value ? `${field.label}: ${value}` : "";
    }).filter(Boolean).join("\n")).filter(Boolean).join("\n\n");
  }
  function validateItems(key, items) {
    const definition = schema[key];
    if (!definition || !Array.isArray(items) || items.length > 50) throw new Error("정형 항목은 종류별 최대 50개입니다.");
    const keys = definition.fields.map(field => field.key).sort().join();
    for (const item of items) {
      if (!item || typeof item !== "object" || Object.keys(item).sort().join() !== keys) throw new Error("세부 항목 구조가 잘못되었습니다.");
      for (const field of definition.fields) {
        const value = item[field.key];
        if (field.type === "checkbox") { if (typeof value !== "boolean") throw new Error("진행 중 여부를 확인하세요."); continue; }
        if (typeof value !== "string" || Array.from(value).length > 5000) throw new Error("세부 항목은 최대 5000자입니다.");
        if (value && ["month", "date"].includes(field.type)) {
          const pattern = field.type === "month" ? /^\d{4}-\d{2}$/ : /^\d{4}-\d{2}-\d{2}$/;
          const full = field.type === "month" ? `${value}-01` : value;
          const parsed = new Date(`${full}T00:00:00Z`);
          if (!pattern.test(value) || !Number.isFinite(+parsed) || parsed.toISOString().slice(0, 10) !== full) throw new Error("날짜를 확인하세요.");
        }
        if (value && field.type === "select" && !field.options.includes(value)) throw new Error("선택 항목을 확인하세요.");
        if (value && field.type === "url" && !/^https?:\/\/[^\s]+$/.test(value)) throw new Error("http 또는 https 주소를 입력하세요.");
      }
      if (item.current && item.end) throw new Error("진행 중인 항목에는 종료일을 입력하지 않습니다.");
      for (const [start, end] of [["start", "end"], ["acquired", "expires"], ["date", "expires"]]) if (item[start] && item[end] && item[start] > item[end]) throw new Error("종료일은 시작일보다 빠를 수 없습니다.");
    }
  }
  function button(icon, name, action, compact = false) {
    const node = document.createElement("button"); node.type = "button";
    node.className = compact ? "icon-button" : "text-button"; node.title = name; node.setAttribute("aria-label", name);
    const symbol = document.createElement("i"); symbol.dataset.lucide = icon; node.append(symbol);
    if (!compact) node.append(document.createTextNode(name));
    node.addEventListener("click", action); return node;
  }
  function render(row, block, changed) {
    const definition = schema[row.id];
    if (!definition) return false;
    const header = document.createElement("div"); header.className = "entry-heading";
    const title = document.createElement("h3"); title.textContent = definition.label;
    const list = document.createElement("div"); list.className = "entry-list";
    const commit = () => { row.value = renderItems(row.id, row.items); row.reviewed = false; changed(); };
    if (!row.value && !row.items) row.items = [];
    const add = button("plus", `${definition.label} 추가`, () => {
      if (!row.items) {
        const initial = empty(row.id);
        const destination = definition.fields.find(field => field.type === "textarea")?.key;
        if (!destination) { alert("기존 원문을 먼저 다운로드하고 항목별로 옮겨 주세요. 원문을 자동 분해하지 않습니다."); return; }
        if (!confirm(`기존 원문을 첫 항목의 '${definition.fields.find(field => field.key === destination).label}'에 보존합니다. 나머지 칸을 직접 나누어 입력하시겠습니까?`)) return;
        initial[destination] = row.value; row.items = [initial];
      } else {
        if (row.items.length >= 50) { alert("최대 50개까지 추가할 수 있습니다."); return; }
        row.items.push(empty(row.id));
      }
      commit(); draw(); list.lastElementChild?.querySelector("input,textarea,select")?.focus();
    });
    header.append(title, add); block.append(header, list);
    function draw() {
      list.replaceChildren();
      if (!row.items) {
        const label = document.createElement("label"); label.textContent = "기존 원문";
        const raw = document.createElement("textarea"); raw.rows = 4; raw.value = row.value;
        raw.addEventListener("input", () => { row.value = raw.value; row.reviewed = false; changed(); });
        label.append(raw); list.append(label);
      } else if (!row.items.length) {
        const state = document.createElement("p"); state.className = "entry-empty"; state.textContent = `등록된 ${definition.label} 없음`; list.append(state);
      } else row.items.forEach((item, index) => {
        const entry = document.createElement("article"); entry.className = "resume-entry"; entry.dataset.index = index;
        const top = document.createElement("div"); top.className = "entry-heading";
        const caption = document.createElement("strong"); caption.textContent = `${definition.label} ${index + 1}`;
        top.append(caption, button("trash-2", `${definition.label} ${index + 1} 삭제`, () => {
          if (Object.values(item).some(Boolean) && !confirm("이 항목을 삭제하시겠습니까?")) return;
          row.items.splice(index, 1); commit(); draw();
        }, true));
        const grid = document.createElement("div"); grid.className = "entry-grid";
        for (const field of definition.fields) {
          const label = document.createElement("label"); label.textContent = field.key === "current" && row.id === "experience_description" ? "재직 중" : field.label;
          label.className = field.type === "textarea" ? "entry-wide" : "";
          let input;
          if (field.type === "select") {
            input = document.createElement("select");
            for (const value of ["", ...field.options]) { const option = document.createElement("option"); option.value = value; option.textContent = value || "선택 안 함"; input.append(option); }
          } else if (field.type === "textarea") { input = document.createElement("textarea"); input.rows = 3; }
          else { input = document.createElement("input"); input.type = field.type; }
          input.dataset.key = field.key; input.setAttribute("aria-label", `${definition.label} ${index + 1} ${field.label}`);
          if (field.type === "checkbox") { label.className = "consent"; input.checked = item[field.key]; label.prepend(input); }
          else { input.value = item[field.key]; input.maxLength = 5000; label.append(input); }
          if (field.key === "end") input.disabled = Boolean(item.current);
          input.addEventListener(field.type === "checkbox" || field.type === "select" ? "change" : "input", () => {
            item[field.key] = field.type === "checkbox" ? input.checked : input.value;
            if (field.key === "current") {
              item.end = ""; const end = grid.querySelector('[data-key="end"]'); end.value = ""; end.disabled = input.checked;
            }
            commit();
          });
          grid.append(label);
        }
        entry.append(top, grid); list.append(entry);
      });
      window.lucide?.createIcons();
    }
    draw(); return true;
  }
  return {setSchema: value => { schema = value; }, get schema() { return schema; }, empty, renderItems, validateItems, render};
})();
