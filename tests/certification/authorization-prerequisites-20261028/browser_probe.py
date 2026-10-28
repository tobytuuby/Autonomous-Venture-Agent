"""Real loopback browser inspection of historical product, never AI acceptance."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading

ROOT = Path("/home/epsilon/venture-control-workspace")
if Path.cwd().resolve() != ROOT:
    raise SystemExit("Approved project root required")
class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

# Short project-local path keeps Chromium Unix sockets below the OS path limit.
scratch = ROOT / "artifacts/b28"
scratch.mkdir(parents=True, exist_ok=True, mode=0o700)
handler = partial(Handler, directory=str(ROOT / "ventures/venture-001/product"))
server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TMPDIR": str(scratch), "HOME": str(scratch),
       "NODE_PATH": str(ROOT / "artifacts/venture-001-browser/node_modules"),
       "VENTURE_CHROMIUM_EXECUTABLE": str(ROOT / "artifacts/venture-001-browser/browsers/chromium-1248/chrome-linux64/chrome"),
       "PROBE_ORIGIN": "http://127.0.0.1:" + str(server.server_port)}
program = """
const {chromium} = require('playwright');
(async () => {
 let browser;
 try {
  browser = await chromium.launch({headless:true,
   executablePath:process.env.VENTURE_CHROMIUM_EXECUTABLE,
   args:['--no-sandbox','--disable-dev-shm-usage']});
  const context = await browser.newContext({serviceWorkers:'block'});
  let blocked=0;
  await context.route('**/*', route => {
   if(new URL(route.request().url()).origin===process.env.PROBE_ORIGIN) return route.continue();
   blocked++; return route.abort();
  });
  const page=await context.newPage();
  const response=await page.goto(process.env.PROBE_ORIGIN+'/restock.html',
   {waitUntil:'domcontentloaded',timeout:15000});
  const selectors=['#username','#password','#register','#login','#logout'];
  const counts={};
  for(const selector of selectors) counts[selector]=await page.locator(selector).count();
  console.log(JSON.stringify({evidence_class:'actual_chromium_loopback_historical_product_probe',
   http_status:response.status(),title:await page.title(),online_selector_counts:counts,
   online_ui_preconditions_met:Object.values(counts).every(x=>x>0),
   blocked_non_origin_requests:blocked,provider_requests:0,
   real_provider_cycle_complete:false,product_acceptance:false}));
 } finally {if(browser) await browser.close();}
})().catch(err => {console.log(JSON.stringify({browser_probe:'FAILED',error_class:err.name,diagnostic:err.message,product_acceptance:false}));process.exitCode=1});
"""
try:
    result = subprocess.run(["/usr/bin/node", "-e", program], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=45)
    print(result.stdout, end="")
    if result.returncode:
        print(json.dumps({"browser_exit": result.returncode, "stderr_suppressed": True}))
    raise SystemExit(result.returncode)
finally:
    server.shutdown()
    server.server_close()
    thread.join()
