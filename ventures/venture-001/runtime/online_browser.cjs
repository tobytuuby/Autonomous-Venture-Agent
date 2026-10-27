"use strict";
// Trusted browser journey. No worker-provided browser program is executed.
const { chromium } = require("playwright");
const port = Number(process.argv[2]);
if (!Number.isInteger(port) || port < 1 || port > 65535 ||
    !process.env.VENTURE_CHROMIUM_EXECUTABLE) process.exit(2);
const origin = "http://127.0.0.1:" + port;
(async () => {
  let browser;
  const denied = [];
  const errors = [];
  const contexts = [];
  try {
    browser = await chromium.launch({
      headless: true, executablePath: process.env.VENTURE_CHROMIUM_EXECUTABLE,
      args: ["--no-sandbox", "--disable-dev-shm-usage"]
    });
    const page = async () => {
      const context = await browser.newContext({ serviceWorkers: "block" });
      contexts.push(context);
      await context.route("**/*", route => {
        if (new URL(route.request().url()).origin === origin) return route.continue();
        denied.push("non-origin request"); return route.abort();
      });
      const p = await context.newPage();
      p.on("pageerror", () => errors.push("page error"));
      await p.goto(origin + "/", { waitUntil: "domcontentloaded" });
      return p;
    };
    const login = async (p, register=false, username="browser-alpha") => {
      await p.locator("#username").fill(username);
      await p.locator("#password").fill("Synthetic-browser-only-924!");
      await p.locator(register ? "#register" : "#login").click();
      await p.locator("#logout").waitFor({ state: "visible" });
    };
    const first = await page();
    if (!(await first.title()).includes("Studio Restock Kit")) throw Error("title");
    await login(first, true);
    for (const [id, value] of Object.entries({
      "item-name": "Browser server item", "on-hand": "10", "inbound": "0",
      "reorder-point": "10", "target": "20", "pack-size": "5", "pack-price": "3"
    })) await first.locator("#" + id).fill(value);
    await first.locator("#save-item").click();
    await first.getByText("Browser server item", { exact: true }).first().waitFor();
    await first.locator("#logout").click();
    await first.locator("#login").waitFor({ state: "visible" });
    await contexts[0].close(); // second browser has no first-context storage
    const second = await page();
    await login(second);
    await second.getByText("Browser server item", { exact: true }).first().waitFor();
    const download = second.waitForEvent("download");
    await second.locator("#export-csv").click();
    await download;
    const other = await page();
    await login(other, true, "browser-beta");
    if ((await other.locator("#inventory").innerText()).includes("Browser server item"))
      throw Error("browser tenant leak");
    if (denied.length || errors.length) throw Error("non-origin requests or runtime errors");
    console.log("PASS: real Chromium UI create, logout, second-context login/server continuity, CSV download, tenant isolation");
    console.log("SUMMARY: browser local online journey passed; no remote staging proof");
  } catch (e) {
    // Never print input values, cookies, full HTML or browser traces.
    console.error("FAIL: browser online journey (" + e.name + ")");
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
  }
})();
