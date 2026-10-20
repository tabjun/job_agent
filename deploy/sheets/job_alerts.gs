/**
 * Google Apps Script for the job alert sheet (owner's own Google account).
 *
 * Setup: open the target Google Sheet → Extensions → Apps Script, paste this
 * file, then Project Settings → Script properties → add SHEET_TOKEN (32+ random
 * characters, same value as ALERT_SHEET_TOKEN in the local .env).
 * Deploy → New deployment → Web app: Execute as "Me", access "Anyone".
 * Put the /exec URL in ALERT_SHEET_URL. The token, not the URL, guards writes.
 *
 * Rows are upserted by posting URL: new postings are appended, known ones get
 * their check time/period refreshed and keep the first mailed date.
 */
const SHEET_NAME = "공고";
const HEADERS = {
  checked_at: "확인 시각", alert: "알림", platform: "플랫폼", company: "회사",
  role: "직무", location: "근무지", experience: "경력", period: "마감·기간",
  apply_button: "지원 버튼", mailed: "메일 발송일", url: "원문 URL",
};

function respond(body) {
  return ContentService.createTextOutput(JSON.stringify(body))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  let request;
  try { request = JSON.parse(e.postData.contents); } catch (error) { return respond({ok: false, error: "json"}); }
  const expected = PropertiesService.getScriptProperties().getProperty("SHEET_TOKEN");
  if (!expected || expected.length < 32 || request.token !== expected) return respond({ok: false, error: "token"});
  const columns = request.columns;
  const rows = request.rows;
  if (!Array.isArray(columns) || !Array.isArray(rows) || rows.length > 5000 || columns.indexOf("url") < 0) {
    return respond({ok: false, error: "shape"});
  }
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const book = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = book.getSheetByName(SHEET_NAME) || book.insertSheet(SHEET_NAME);
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(columns.map(key => HEADERS[key] || key));
      sheet.setFrozenRows(1);
    }
    const urlColumn = columns.indexOf("url");
    const mailedColumn = columns.indexOf("mailed");
    const existing = sheet.getLastRow() > 1
      ? sheet.getRange(2, 1, sheet.getLastRow() - 1, columns.length).getValues() : [];
    const index = new Map(existing.map((row, i) => [String(row[urlColumn]), i]));
    const added = [];
    let updated = 0;
    for (const item of rows) {
      // Keep cells as text so a value starting with '=' is never a formula.
      const values = columns.map(key => {
        const value = String(item[key] === undefined ? "" : item[key]).slice(0, 1000);
        return /^[=+\-@]/.test(value) ? "'" + value : value;
      });
      const at = index.get(values[urlColumn]);
      if (at === undefined) {
        index.set(values[urlColumn], existing.length + added.length);
        added.push(values);
      } else if (at < existing.length) {
        if (mailedColumn >= 0 && existing[at][mailedColumn]) values[mailedColumn] = existing[at][mailedColumn];
        existing[at] = values;
        updated += 1;
      }
    }
    if (existing.length) sheet.getRange(2, 1, existing.length, columns.length).setValues(existing);
    if (added.length) sheet.getRange(sheet.getLastRow() + 1, 1, added.length, columns.length).setValues(added);
    return respond({ok: true, added: added.length, updated: updated});
  } finally {
    lock.releaseLock();
  }
}
