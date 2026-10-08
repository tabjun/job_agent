"use strict";
window.ResumeFiles = (() => {
  const W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
  const signature = "표준 이력서 양식 1";
  const text = node => [...node.getElementsByTagNameNS(W, "p")].map(p => {
    const walker = document.createTreeWalker(p, NodeFilter.SHOW_ELEMENT); const parts = []; let child;
    while ((child = walker.nextNode())) {
      if (child.namespaceURI === W && child.localName === "t") parts.push(child.textContent);
      else if (child.namespaceURI === W && child.localName === "br") parts.push("\n");
      else if (child.namespaceURI === W && child.localName === "tab") parts.push("\t");
    }
    return parts.join("");
  }).join("\n");
  function records(profile, blank = false) {
    const schema = ResumeForms.schema;
    const basicOrder = ["name", "email", "phone", "headline", "summary", "department", "employment_type", "cover_letter"];
    const basic = profile.fields.filter(row => !schema[row.id] && (row.id !== "award_certification_description" || row.value));
    basic.sort((a, b) => (basicOrder.indexOf(a.id) < 0 ? 99 : basicOrder.indexOf(a.id)) - (basicOrder.indexOf(b.id) < 0 ? 99 : basicOrder.indexOf(b.id)));
    const result = [{title: "기본 정보", values: basic.map(row => [row.label, row.value])}];
    for (const row of profile.fields.filter(row => schema[row.id])) {
      const definition = schema[row.id];
      if (!row.items && row.value) result.push({title: `${definition.label} 원문`, values: [["내용", row.value]]});
      const items = blank ? [ResumeForms.empty(row.id)] : (row.items || []).filter(item => Object.values(item).some(Boolean));
      items.forEach((item, index) => result.push({title: `${definition.label} ${index + 1}`, values: definition.fields.map(field => [field.label, field.type === "checkbox" ? (item[field.key] ? "예" : "아니오") : item[field.key]])}));
    }
    return result;
  }
  function markdown(profile, blank = false) {
    return `# 공통 이력서\n\n${signature}\n\n한 항목당 한 표를 사용합니다. 날짜는 2024-01 또는 2024-01-15로 작성하고, 해당 없는 칸은 비워 둡니다. 여러 경력·자격은 해당 묶음을 복사해 번호를 늘려 작성합니다.\n\n` + records(profile, blank).map(record => `## ${record.title}\n\n` + record.values.map(([key, value]) => `- ${key}: ${value.replace(/\r\n?/g, "\n").split("\n").join("\n  ")}`).join("\n") + "\n").join("\n");
  }
  function documentBytes(profile, blank = false) {
    const xml = document.implementation.createDocument(W, "w:document");
    xml.documentElement.setAttribute("xmlns:w", W);
    const element = (name, attrs = {}) => { const node = xml.createElementNS(W, `w:${name}`); for (const [key, value] of Object.entries(attrs)) node.setAttributeNS(W, `w:${key}`, value); return node; };
    const body = element("body"); xml.documentElement.append(body);
    function paragraph(value, style) {
      const p = element("p");
      if (style) { const props = element("pPr"); props.append(element("pStyle", {val: style})); p.append(props); }
      const lines = value.replace(/\r\n?/g, "\n").split("\n");
      lines.forEach((line, index) => { const run = element("r"); if (index) run.append(element("br")); const t = element("t"); t.setAttribute("xml:space", "preserve"); t.textContent = line; run.append(t); p.append(run); });
      return p;
    }
    body.append(paragraph("공통 이력서", "Title"), paragraph(signature), paragraph("본인의 사실만 작성하세요. 해당 없는 칸은 비워 두고, 여러 경력·프로젝트·자격은 해당 제목과 표를 함께 복사하세요. 날짜는 2024-01 또는 2024-01-15, 진행 중 여부는 예 또는 아니오로 작성합니다."));
    for (const record of records(profile, blank)) {
      body.append(paragraph(record.title, "Heading1"));
      const table = element("tbl");
      const properties = element("tblPr"); properties.append(element("tblW", {w: "9360", type: "dxa"}));
      const margins = element("tblCellMar"); for (const side of ["top", "left", "bottom", "right"]) margins.append(element(side, {w: "90", type: "dxa"})); properties.append(margins);
      const borders = element("tblBorders"); for (const side of ["top", "left", "bottom", "right", "insideH", "insideV"]) borders.append(element(side, {val: "single", sz: "4", color: "D6DDDA"})); properties.append(borders); table.append(properties);
      const grid = element("tblGrid"); grid.append(element("gridCol", {w: "2400"}), element("gridCol", {w: "6960"})); table.append(grid);
      for (const [rowIndex, pair] of record.values.entries()) {
        const tr = element("tr"); const trProperties = element("trPr"); trProperties.append(element("cantSplit")); tr.append(trProperties);
        pair.forEach((value, index) => { const cell = element("tc"); const props = element("tcPr"); props.append(element("tcW", {w: index ? "6960" : "2400", type: "dxa"})); if (!index) props.append(element("shd", {fill: "F1F5F3"})); const p = paragraph(value); if (rowIndex < record.values.length - 1) { const pPr = element("pPr"); pPr.append(element("keepNext")); p.prepend(pPr); } cell.append(props, p); tr.append(cell); });
        table.append(tr);
      }
      body.append(table, paragraph(""));
    }
    const section = element("sectPr"); section.append(element("pgSz", {w: "11906", h: "16838"}), element("pgMar", {top: "1100", right: "1273", bottom: "1100", left: "1273"})); body.append(section);
    const serialize = node => new XMLSerializer().serializeToString(node);
    const styles = `<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="${W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="Malgun Gothic"/><w:sz w:val="20"/><w:color w:val="222222"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="34"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:keepNext/><w:spacing w:before="160" w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>`;
    const files = {
      "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
      "_rels/.rels": '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
      "word/document.xml": '<?xml version="1.0" encoding="UTF-8"?>' + serialize(xml),
      "word/styles.xml": styles,
      "word/_rels/document.xml.rels": '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
    };
    return fflate.zipSync(Object.fromEntries(Object.entries(files).map(([key, value]) => [key, fflate.strToU8(value)])));
  }
  function imported(records, template, source) {
    const result = structuredClone(template); const schema = ResumeForms.schema;
    const byLabel = new Map(result.fields.map(row => [row.label, row]));
    const bySection = new Map(Object.entries(schema).map(([key, definition]) => [definition.label, key]));
    const observed = new Set();
    for (const record of records) {
      if (record.title === "기본 정보") {
        for (const [label, value] of record.values) {
          const row = byLabel.get(label); if (!row || schema[row.id]) throw new Error(`지원하지 않는 기본 항목: ${label}`);
          if (observed.has(row.id)) throw new Error("기본 항목이 중복되었습니다."); observed.add(row.id); row.value = value;
        }
        continue;
      }
      const title = record.title.replace(/\s+(?:\d+|원문)$/, ""); const key = bySection.get(title);
      if (!key) throw new Error(`지원하지 않는 제목: ${record.title}`);
      const row = result.fields.find(field => field.id === key);
      if (record.title.endsWith(" 원문")) { if (row.items || row.value) throw new Error("원문과 정형 항목을 한 섹션에 함께 넣을 수 없습니다."); row.value = record.values.map(pair => pair[1]).join("\n"); continue; }
      if (row.value && !row.items) throw new Error("원문과 정형 항목을 한 섹션에 함께 넣을 수 없습니다.");
      const item = ResumeForms.empty(key); const keys = new Map(schema[key].fields.map(field => [field.label, field])); const seen = new Set();
      for (const [label, value] of record.values) {
        const field = keys.get(label); if (!field || seen.has(label)) throw new Error("표의 항목명 또는 중복 값을 확인하세요."); seen.add(label);
        if (field.type === "checkbox") {
          if (!["", "예", "아니오"].includes(value.trim())) throw new Error("진행 중 여부는 예 또는 아니오로 입력하세요.");
          item[field.key] = value.trim() === "예";
        } else item[field.key] = value;
      }
      row.items ||= []; if (Object.values(item).some(Boolean)) row.items.push(item);
      ResumeForms.validateItems(key, row.items); row.value = ResumeForms.renderItems(key, row.items);
    }
    for (const row of result.fields) {
      row.reviewed = false;
      row.evidence = row.value ? [{source_id: source.slice(0, 200), paragraph_index: 0, text: row.value}] : [];
    }
    return result;
  }
  function parseMarkdown(content, template, source) {
    if (!content.split(/\r?\n/).includes(signature)) throw new Error("빈 표준 Markdown 양식을 받아 작성해 주세요. 일반 문서는 DOCX 원문 가져오기를 사용하세요.");
    const records = []; let current, last;
    for (const line of content.replace(/\r\n?/g, "\n").split("\n")) {
      if (line.startsWith("## ")) { current = {title: line.slice(3), values: []}; records.push(current); last = null; }
      else if (current && line.startsWith("- ")) { const index = line.indexOf(": "); if (index < 0) throw new Error("항목명 뒤의 콜론과 공백을 유지해 주세요."); last = [line.slice(2, index), line.slice(index + 2)]; current.values.push(last); }
      else if (current && last && line.startsWith("  ")) last[1] += "\n" + line.slice(2);
      else if (current && line.trim()) throw new Error("Markdown 양식의 제목·항목명·들여쓰기를 확인하세요.");
    }
    return imported(records, template, source);
  }
  async function read(file, template) {
    if (file.size > 2_000_000) throw new Error("이력서 파일은 2MB 이하여야 합니다.");
    const extension = file.name.split(".").pop().toLowerCase();
    if (extension === "json") return {document: JSON.parse(await file.text())};
    if (extension === "md") return {document: parseMarkdown(await file.text(), template, file.name)};
    if (extension !== "docx") throw new Error("DOCX, Markdown 또는 JSON 파일을 선택하세요.");
    const bytes = new Uint8Array(await file.arrayBuffer());
    let oversized = false;
    const files = fflate.unzipSync(bytes, {filter: entry => {
      if (entry.name !== "word/document.xml") return false;
      if (entry.originalSize > 2_000_000) { oversized = true; return false; } return true;
    }});
    if (oversized || !files["word/document.xml"]) throw new Error("DOCX 본문이 없거나 크기 제한을 초과합니다.");
    const raw = fflate.strFromU8(files["word/document.xml"]);
    if (/<!DOCTYPE|<!ENTITY/i.test(raw)) throw new Error("지원하지 않는 DOCX XML입니다.");
    const xml = new DOMParser().parseFromString(raw, "application/xml");
    if (xml.querySelector("parsererror")) throw new Error("DOCX 본문을 읽을 수 없습니다.");
    const body = xml.getElementsByTagNameNS(W, "body")[0]; if (!body) throw new Error("DOCX 본문이 없습니다.");
    const nodes = [...body.children];
    // A free-form document is retained verbatim, never guessed into structured facts.
    if (!nodes.some(node => node.localName === "p" && [...node.getElementsByTagNameNS(W, "t")].map(t => t.textContent).join("") === signature)) {
      const original = text(body); if (Array.from(original).length > 30000) throw new Error("원문은 최대 30000자입니다. 필요한 부분을 나누어 가져오세요.");
      const document = structuredClone(template); const row = document.fields.find(field => field.id === "summary");
      row.value = original; row.reviewed = false; row.evidence = [{source_id: file.name.slice(0, 200), paragraph_index: 0, text: original}];
      return {document, unstructured: true};
    }
    const records = []; let title;
    for (const node of nodes) {
      if (node.localName === "p") title = [...node.getElementsByTagNameNS(W, "t")].map(t => t.textContent).join("");
      else if (node.localName === "tbl") {
        const values = [...node.children].filter(child => child.localName === "tr").map(tr => {
          const cells = [...tr.children].filter(child => child.localName === "tc"); if (cells.length !== 2) throw new Error("표는 항목명·값 두 열을 유지해 주세요."); return cells.map(text);
        }); records.push({title, values});
      }
    }
    if (!records.length) throw new Error("표준 양식의 표를 찾을 수 없습니다.");
    return {document: imported(records, template, file.name)};
  }
  function download(profile, format, blank = false) {
    let data, type;
    if (format === "docx") { data = documentBytes(profile, blank); type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"; }
    else if (format === "md") { data = markdown(profile, blank); type = "text/markdown;charset=utf-8"; }
    else { data = JSON.stringify(profile, null, 2); type = "application/json"; }
    const url = URL.createObjectURL(new Blob([data], {type})); const link = document.createElement("a"); link.href = url; link.download = `${blank ? "resume-template" : "resume-profile"}-v1.${format}`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return {read, download, documentBytes, markdown, parseMarkdown};
})();
