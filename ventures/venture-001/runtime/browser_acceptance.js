"use strict";
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const appArg = process.argv[2];
const outputArg = process.argv[3];
const appDir = path.resolve(appArg || "");
const outputDir = path.resolve(outputArg || "");
const executablePath = process.env.VENTURE_CHROMIUM_EXECUTABLE;
const required = ["index.html", "app.js", "styles.css"];
if (!appArg || !outputArg || !executablePath || !required.every(name => fs.existsSync(path.join(appDir, name)))) {
  console.error("FAIL: browser harness inputs/runtime missing");
  process.exit(2);
}
fs.mkdirSync(outputDir, { recursive: true });
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8" };
const server = http.createServer((req, res) => {
  if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405).end(); return; }
  let name;
  try { name = decodeURIComponent(new URL(req.url, "http://127.0.0.1").pathname); }
  catch { res.writeHead(400).end(); return; }
  name = name === "/" ? "index.html" : name.slice(1);
  if (!required.includes(name)) { res.writeHead(404).end(); return; }
  const body = fs.readFileSync(path.join(appDir, name));
  res.writeHead(200, { "Content-Type": mime[path.extname(name)], "X-Content-Type-Options": "nosniff" });
  res.end(req.method === "HEAD" ? undefined : body);
});

(async () => {
  let browser;
  let origin;
  const failures = [];
  const externalRequests = [];
  const errors = [];
  let passed = 0;
  const check = async (name, fn) => {
    try { await fn(); passed++; console.log("PASS: " + name); }
    catch (error) { failures.push(name + ": " + error.message); console.log("FAIL: " + failures.at(-1)); }
  };
  try {
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });
    origin = `http://127.0.0.1:${server.address().port}`;
    browser = await chromium.launch({ headless: true, executablePath, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
    const page = await browser.newPage({ acceptDownloads: true });
    await page.route("**/*", async route => {
      const url = route.request().url();
      if (url.startsWith(origin + "/")) return route.continue();
      externalRequests.push(url);
      return route.abort();
    });
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("dialog", dialog => dialog.accept());
    await page.goto(origin + "/", { waitUntil: "domcontentloaded" });

    await check("hosted static page opens with product title and planning notice", async () => {
      if (!(await page.title()).includes("Studio Restock Kit")) throw new Error("wrong title");
      if (!(await page.locator("#planning-title").innerText()).includes("Planning aid only")) throw new Error("planning notice absent");
      if (await page.locator("#rows tr").count() < 1) throw new Error("worksheet rows absent");
    });
    await check("invalid blank worksheet blocks results export", async () => {
      await page.locator("#reset").click();
      await page.locator("#export-results").click();
      const status = await page.locator("#action-status").innerText();
      if (!status || status.toLowerCase().includes("prepared")) throw new Error("invalid row was not rejected");
    });
    await check("entering stock recalculates order boundary and total", async () => {
      const values = { Item: "Browser test item", Unit: "piece", Supplier: "Example supplier", Location: "Shelf A",
        "On hand": "10", Inbound: "0", "Reorder point": "10", Target: "20", "Pack size": "5", "Pack price": "3" };
      for (const [label, value] of Object.entries(values)) await page.getByLabel(label, { exact: true }).first().fill(value);
      const cells = await page.locator("#rows tr").first().locator("[data-result]").allTextContents();
      if (cells.join("|") !== "10|2|10|6.00|REVIEW ORDER") throw new Error("unexpected results: " + cells.join("|"));
      if (!(await page.locator("#summary").innerText()).includes("6.00")) throw new Error("summary total did not update");
    });
    await page.waitForTimeout(350);
    await check("saved inventory survives browser reload", async () => {
      await page.reload({ waitUntil: "networkidle" });
      if (await page.getByLabel("Item", { exact: true }).first().inputValue() !== "Browser test item") throw new Error("saved item missing after reload");
    });
    await check("results CSV downloads with computed output", async () => {
      const [download] = await Promise.all([page.waitForEvent("download"), page.locator("#export-results").click()]);
      const target = path.join(outputDir, download.suggestedFilename());
      await download.saveAs(target);
      const text = fs.readFileSync(target, "utf8");
      if (!text.includes("Browser test item") || !text.includes("6.00")) throw new Error("CSV omitted entered/calculated values");
    });
    await check("input CSV export reimports after reset", async () => {
      const [download] = await Promise.all([page.waitForEvent("download"), page.locator("#export-inputs").click()]);
      const target = path.join(outputDir, download.suggestedFilename());
      await download.saveAs(target);
      await page.locator("#reset").click();
      await page.locator("#csv-file").setInputFiles(target);
      await page.waitForTimeout(100);
      if (await page.getByLabel("Item", { exact: true }).first().inputValue() !== "Browser test item") throw new Error("CSV import did not restore item");
    });
    await check("row add and remove controls work", async () => {
      await page.locator("#add").click();
      if (await page.locator("#rows tr").count() !== 2) throw new Error("add row failed");
      await page.getByRole("button", { name: "Remove row 2" }).click();
      if (await page.locator("#rows tr").count() !== 1) throw new Error("remove row failed");
    });
    await check("browser journey stays on loopback with no runtime errors", async () => {
      if (externalRequests.length) throw new Error("external requests: " + externalRequests.join(", "));
      if (errors.length) throw new Error("browser errors: " + errors.join("; "));
    });
    console.log(`SUMMARY: ${passed} passed; ${failures.length} failed; browser=Chromium headless; host=127.0.0.1`);
    if (failures.length) process.exitCode = 1;
  } catch (error) {
    console.error("BROWSER HARNESS ERROR: " + error.stack);
    process.exitCode = 2;
  } finally {
    if (browser) await browser.close();
    if (server.listening) await new Promise(resolve => server.close(resolve));
  }
})();
