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
const required = ["index.html"];
const appAssets = fs.existsSync(appDir) && fs.statSync(appDir).isDirectory()
  ? new Set(fs.readdirSync(appDir, { withFileTypes: true })
      .filter(entry => entry.isFile() && /\.(?:html|js|css)$/i.test(entry.name))
      .map(entry => entry.name))
  : new Set();
if (!appArg || !outputArg || !executablePath || !required.every(name => appAssets.has(name))) {
  console.error("FAIL: browser harness inputs/runtime missing");
  process.exit(2);
}
fs.mkdirSync(outputDir, { recursive: true });
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8" };
const server = http.createServer((req, res) => {
  if (!["GET", "HEAD"].includes(req.method)) { res.writeHead(405).end(); return; }
  let name;
  try { name = decodeURIComponent(new URL(req.url, "http://127.0.0.1").pathname); }
  catch { res.writeHead(400).end(); return; }
  name = name === "/" ? "index.html" : name.slice(1);
  if (!appAssets.has(name)) { res.writeHead(404).end(); return; }
  const body = fs.readFileSync(path.join(appDir, name));
  res.writeHead(200, { "Content-Type": mime[path.extname(name)], "X-Content-Type-Options": "nosniff" });
  res.end(req.method === "HEAD" ? undefined : body);
});

(async () => {
  let browser;
  const failures = [];
  const externalRequests = [];
  const failedResponses = [];
  const errors = [];
  let passed = 0;
  const check = async (name, fn) => {
    try { await fn(); passed++; console.log("PASS: " + name); }
    catch (error) { failures.push(name + ": " + error.message); console.log("FAIL: " + failures.at(-1)); }
  };
  const rows = page => page.locator("main tbody tr");
  const button = (page, pattern) => page.getByRole("button", { name: pattern }).first();
  const field = (page, label) => page.getByLabel(label, { exact: false }).first();
  const confirmInline = async page => {
    const confirmation = page.locator("#confirmation");
    if (await confirmation.count() && await confirmation.isVisible()) {
      await confirmation.locator("button").first().click();
    }
  };
  const startBlank = async page => {
    const reset = button(page, /start blank|reset(?: worksheet| saved data| inventory)?|clear worksheet/i);
    if (await reset.count()) {
      await reset.click();
      await confirmInline(page);
    } else {
      const removeButtons = page.getByRole("button", { name: /remove row/i });
      while (await rows(page).count() > 0 && await removeButtons.count() > 0) {
        await removeButtons.last().click();
      }
      await button(page, /add row/i).click();
    }
    if (await rows(page).count() === 0) await button(page, /add row/i).click();
  };
  const statusText = async page => (await page.locator("[role=status]").allTextContents()).join(" ");
  const totalText = async page => (await page.locator("#total").count())
    ? page.locator("#total").innerText() : (await page.locator(".summary").allTextContents()).join(" ");

  try {
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });
    const origin = "http://127.0.0.1:" + server.address().port;
    browser = await chromium.launch({ headless: true, executablePath, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
    const page = await browser.newPage({ acceptDownloads: true });
    await page.route("**/*", async route => {
      const url = route.request().url();
      if (url.startsWith(origin + "/")) return route.continue();
      externalRequests.push(url);
      return route.abort();
    });
    page.on("response", response => {
      if (response.status() >= 400) failedResponses.push(response.status() + " " + response.url());
    });
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    page.on("dialog", dialog => dialog.accept());
    await page.goto(origin + "/", { waitUntil: "domcontentloaded" });

    await check("hosted page has the product title, planning guidance, and worksheet", async () => {
      if (!(await page.title()).includes("Studio Restock Kit")) throw new Error("wrong title");
      if (!(await page.locator("h1").first().innerText()).includes("Studio Restock Kit")) throw new Error("product heading absent");
      const text = await page.locator("body").innerText();
      if (!/planning|review every suggestion/i.test(text) || !/purchas|order/i.test(text)) throw new Error("review-only planning guidance absent");
      if (await rows(page).count() < 1) throw new Error("worksheet rows absent");
    });

    await check("blank inventory cannot be exported as valid results", async () => {
      await startBlank(page);
      await button(page, /(?:export|download).*results/i).click();
      if (!/invalid|required|add at least|enter/i.test(await statusText(page))) throw new Error("blank row was not rejected");
    });

    await check("stock entry recalculates position, packs, quantity, estimate, and status", async () => {
      const values = { Item: "Browser test item", Unit: "piece", Supplier: "Example supplier", Location: "Shelf A",
        "On hand": "10", Inbound: "0", "Reorder point": "10", Target: "20", "Pack size": "5", "Pack price": "3" };
      for (const [label, value] of Object.entries(values)) await field(page, label).fill(value);
      const rowText = await rows(page).first().innerText();
      if (!rowText.includes("10") || !rowText.includes("2") || !/6[.,]00/.test(rowText) || !/review|order/i.test(rowText)) {
        throw new Error("unexpected calculated row: " + rowText.slice(0, 240));
      }
      if (!/6[.,]00/.test(await totalText(page))) throw new Error("summary total did not update");
    });

    await page.waitForTimeout(450);
    await check("saved inventory survives browser reload", async () => {
      await page.reload({ waitUntil: "load" });
      if (await field(page, "Item").inputValue() !== "Browser test item") throw new Error("saved item missing after reload");
    });

    await check("results CSV downloads with computed output", async () => {
      const [download] = await Promise.all([page.waitForEvent("download"), button(page, /(?:export|download).*results/i).click()]);
      const target = path.join(outputDir, download.suggestedFilename());
      await download.saveAs(target);
      const text = fs.readFileSync(target, "utf8");
      if (!text.includes("Browser test item") || !/6[.,]00/.test(text)) throw new Error("CSV omitted entered/calculated values");
    });

    await check("input CSV export can be reimported", async () => {
      const [download] = await Promise.all([page.waitForEvent("download"), button(page, /(?:export|download).*inputs/i).click()]);
      const target = path.join(outputDir, download.suggestedFilename());
      await download.saveAs(target);
      await startBlank(page);
      const fileInput = page.locator("input[type=file]").first();
      await fileInput.setInputFiles(target);
      await confirmInline(page);
      await page.waitForTimeout(150);
      if (await field(page, "Item").inputValue() !== "Browser test item") throw new Error("CSV import did not restore item");
    });

    await check("row add and remove controls work", async () => {
      const before = await rows(page).count();
      await button(page, /add row/i).click();
      if (await rows(page).count() !== before + 1) throw new Error("add row failed");
      await button(page, /remove/i).click();
      if (await rows(page).count() !== before) throw new Error("remove row failed");
    });

    await check("browser journey remains on loopback with no runtime errors", async () => {
      if (externalRequests.length) throw new Error("external requests: " + externalRequests.join(", "));
      if (failedResponses.length) throw new Error("failed HTTP responses: " + failedResponses.join("; "));
      if (errors.length) throw new Error("browser errors: " + errors.join("; "));
    });
    console.log("SUMMARY: " + passed + " passed; " + failures.length + " failed; browser=Chromium headless; host=127.0.0.1");
    if (failures.length) process.exitCode = 1;
  } catch (error) {
    console.error("BROWSER HARNESS ERROR: " + error.stack);
    process.exitCode = 2;
  } finally {
    if (browser) await browser.close();
    if (server.listening) await new Promise(resolve => server.close(resolve));
  }
})();
