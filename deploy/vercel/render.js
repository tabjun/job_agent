import { timingSafeEqual } from "node:crypto";
import { readFileSync } from "node:fs";
import chromium from "@sparticuz/chromium-min";
import { chromium as playwright } from "playwright-core";

export function allowedDetail(value) {
  try {
    const u = new URL(value);
    const paths = {"www.jobkorea.co.kr":/^\/Recruit\/GI_Read\/\d+$/i,"www.saramin.co.kr":/^\/zf_user\/jobs\/relay\/view$/,
      "www.wanted.co.kr":/^\/wd\/\d+$/,"www.catch.co.kr":/^\/NCS\/RecruitInfoDetails\/\d+$/i,"job.incruit.com":/^\/jobdb_info\/jobpost\.asp$/i};
    if (u.protocol!=="https:" || u.username || u.password || u.port || !paths[u.hostname]?.test(u.pathname)) return "";
    if (u.hostname==="www.saramin.co.kr" && !/^\?rec_idx=\d+$/.test(u.search)) return "";
    if (u.hostname==="job.incruit.com" && !/^\?job=\d+$/.test(u.search)) return "";
    return u.href;
  } catch { return ""; }
}
export default async function handler(req,res) {
  res.setHeader("Cache-Control","no-store");
  const expected = process.env.ALERT_SERVER_SECRET || "";
  const provided = String(req.headers.authorization || "");
  const expectedHeader = `Bearer ${expected}`;
  if (expected.length<32 || provided.length!==expectedHeader.length || !timingSafeEqual(Buffer.from(provided),Buffer.from(expectedHeader))) return res.status(401).json({error:"unauthorized"});
  if (req.method!=="POST") return res.status(405).json({error:"POST required"});
  const url = allowedDetail(req.body?.url);
  if (!url) return res.status(400).json({error:"unsupported_url"});
  let browser;
  try {
    browser = await playwright.launch({args:chromium.args,executablePath:await chromium.executablePath("https://github.com/Sparticuz/chromium/releases/download/v153.0.0/chromium-v153.0.0-pack.x64.tar"),headless:true});
    const context = await browser.newContext({serviceWorkers:"block"});
    const domains=["jobkorea.co.kr","saramin.co.kr","wanted.co.kr","catch.co.kr","incruit.com"];
    await context.route("**/*",async route=>{
      const request=route.request(); const u=new URL(request.url());
      if (u.protocol!=="https:" || !domains.some(d=>u.hostname===d || u.hostname.endsWith(`.${d}`)) || ["image","font","media"].includes(request.resourceType())) return route.abort();
      const headers={...request.headers()};delete headers.cookie;return route.continue({headers});
    });
    const page=await context.newPage();await page.goto(url,{waitUntil:"domcontentloaded",timeout:20000});
    await page.waitForLoadState("networkidle",{timeout:5000}).catch(()=>{});
    if (allowedDetail(page.url())!==url) return res.status(200).json({html:""});
    const snapshot=readFileSync(new URL("../job_agent/browser/public_snapshot.js",import.meta.url),"utf8");
    const html=await page.evaluate(snapshot);
    if (Buffer.byteLength(html)>3_000_000) return res.status(413).json({error:"page_too_large"});
    return res.status(200).json({html});
  } catch {return res.status(503).json({error:"render_unavailable"});}
  finally {if(browser) await browser.close();}
}
