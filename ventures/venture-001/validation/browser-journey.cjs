'use strict';
// Run from repository root. Only the delivered ZIP is opened, never product/ source.
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '../../..');
assert.equal(process.cwd(),root,'Run from repository root');
const base = path.join(root, 'artifacts/venture-001-browser');
process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(base, 'browsers');
process.env.TMPDIR = path.join(base, 'tmp');
fs.mkdirSync(process.env.TMPDIR, {recursive:true});
const {chromium} = require(path.join(base, 'node_modules/playwright'));
const {expect} = require(path.join(base, 'node_modules/playwright/test'));
const out = fs.mkdtempSync(path.join(base, 'acceptance-'));
const zip = 'ventures/venture-001/Studio-Restock-Kit-v1.0.zip';
const report = {zip, sha256: require('node:crypto').createHash('sha256').update(fs.readFileSync(zip)).digest('hex'), cases:[], out};
function csv(text) { // Independent reader for downloaded CSV, including quotes/newlines.
 const rows=[]; let row=[], value='', quoted=false;
 for(let i=0;i<text.length;i++) { const c=text[i];
 if(c==='"') { if(quoted && text[i+1]==='"'){value+='"';i++;}else quoted=!quoted; }
 else if(!quoted && c===','){row.push(value);value='';}
 else if(!quoted && (c==='\r'||c==='\n')){if(c==='\r'&&text[i+1]==='\n')i++;row.push(value);rows.push(row);row=[];value='';}
 else value+=c;
 } assert.equal(quoted,false); if(value||row.length)rows.push([...row,value]); return rows;
}
(async()=>{
 let browser, page; const errors=[], network=[];
 async function check(name, fn) {
  try {await fn();report.cases.push({name,status:'PASS'});}
  catch(e){report.cases.push({name,status:'FAIL',error:e.stack});}
  console.log(report.cases.at(-1).status, name, report.cases.at(-1).error || '');
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
 }
 try {
 execFileSync('python3',['-c', 'import sys,zipfile,pathlib; z=zipfile.ZipFile(sys.argv[1]); assert sorted(z.namelist())==["START-HERE.md","restock.html"]; z.extractall(sys.argv[2])',zip,out]);
 fs.copyFileSync(path.join(out,'START-HERE.md'),path.join(out,'guide-reviewed.md'));
 const guide=fs.readFileSync(path.join(out,'START-HERE.md'),'utf8');
 await check('START-HERE offline instructions and save/reimport limitations',async()=>{for(const s of ['no installation','Start blank','inputs CSV','Import','closing the tab loses'])assert.ok(guide.includes(s),s);});
 browser=await chromium.launch({headless:true,env:{...process.env,FONTCONFIG_FILE:path.join(base,'fonts.conf'),LD_LIBRARY_PATH:path.join(base,'libroot/usr/lib/x86_64-linux-gnu')},args:['--disable-dev-shm-usage']});
 report.chromium=browser.version();
 const context=await browser.newContext({acceptDownloads:true,offline:true,viewport:{width:1440,height:1000}});
 await context.route('**/*',route=>{if(/^https?:/.test(route.request().url())){network.push(route.request().url());return route.abort();}return route.continue();});
 page=await context.newPage();page.setDefaultTimeout(5000);
 await page.setContent('<input aria-label="Environment probe">');
 await page.getByRole('textbox').fill('typing works');
 assert.equal(await page.getByRole('textbox').inputValue(),'typing works','Browser cannot type: check workspace fonts.conf and fonts');
page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 page.on('dialog',d=>d.accept());
 const rows=page.locator('#rows tr'), msg=page.locator('#message');
 const cell=(i,label)=>{const loc=rows.nth(i).getByRole('textbox',{name:label,exact:true});return {inputValue:()=>loc.inputValue(),fill:async value=>{await loc.click();await loc.press('ControlOrMeta+a');await loc.press('Backspace');if(value)await loc.pressSequentially(value);}};};
 async function fill(i,values){const labels=['Item','Unit','Supplier','Location','On hand','Inbound','Reorder point','Target','Pack size','Pack price'];for(let j=0;j<values.length;j++)await cell(i,labels[j]).fill(String(values[j]));}
 async function result(i,expected){const actual=await rows.nth(i).locator('td').allTextContents();assert.deepEqual(actual.slice(10,15),expected, JSON.stringify({inputs:await rows.nth(i).locator('input').evaluateAll(xs=>xs.map(x=>x.value)),errors}));}
 async function download(button,name){const [d]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:button,exact:true}).click()]);assert.equal(d.suggestedFilename(),name);const dest=path.join(out,name);await d.saveAs(dest);assert.equal(await d.failure(),null);return dest;}
 await check('First file open offline: fictional examples and total 90.00',async()=>{await page.goto(pathToFileURL(path.join(out,'restock.html')).href);assert.equal(await rows.count(),4);await expect(msg).toContainText('90.00');await page.screenshot({path:path.join(out,'01-first-open.png'),fullPage:true});});
 await check('Start blank and validation blocks invalid CSV exports',async()=>{await page.getByRole('button',{name:'Start blank',exact:true}).click();assert.equal(await rows.count(),1);assert.equal(await cell(0,'Item').inputValue(),'');let downloads=0;const count=()=>downloads++;page.on('download',count);await page.getByRole('button',{name:'Download inputs CSV',exact:true}).click();await expect(msg).toContainText('Item and unit required');await page.waitForTimeout(250);page.off('download',count);assert.equal(downloads,0);});
 const item=['Clay, "white"','kg','Local supplier','Shelf A',12,0,15,40,12.5,22];
 await check('Enter buyer item: 3 packs, 37.5 kg, 66.00',async()=>{await fill(0,item);await result(0,['12','3','37.5','66.00','REVIEW ORDER']);});
 await check('Inclusive threshold and inbound suppress unnecessary orders',async()=>{await cell(0,'Inbound').fill('4');await result(0,['16','0','0','0.00','NO ORDER']);await cell(0,'Inbound').fill('3');await result(0,['15','2','25','44.00','REVIEW ORDER']);await cell(0,'Inbound').fill('0');});
 await check('Add row and combined money total',async()=>{await page.getByRole('button',{name:'Add row',exact:true}).click();await fill(1,['Boxes','piece','Box supplier','Cupboard',0,0,10,25,10,8]);await result(1,['0','3','30','24.00','REVIEW ORDER']);await expect(msg).toContainText('90.00');await page.screenshot({path:path.join(out,'02-entered.png'),fullPage:true});});
 let saved;
 await check('Inputs CSV download: exact entered values and escaping',async()=>{saved=await download('Download inputs CSV','restock-inputs.csv');const data=csv(fs.readFileSync(saved,'utf8'));assert.equal(data.length,3);assert.deepEqual(data[1],item.map(String));});
 await check('Results CSV download: exact quantities, costs, statuses',async()=>{const f=await download('Download results CSV','restock-results.csv');const data=csv(fs.readFileSync(f,'utf8'));assert.equal(data.length,3);assert.deepEqual(data[1],[...item.map(String),'12','3','37.5','66.00','REVIEW ORDER']);assert.deepEqual(data[2].slice(10),['0','3','30','24.00','REVIEW ORDER']);});
 await check('Reload then import downloaded inputs restores all buyer data',async()=>{await page.reload();assert.equal(await cell(0,'Item').inputValue(),'Stoneware clay');await page.locator('#file').setInputFiles(saved);await expect.poll(()=>cell(0,'Item').inputValue()).toBe(item[0]);assert.equal(await rows.count(),2);for(let i=0;i<10;i++)assert.equal(await rows.nth(0).locator('input').nth(i).inputValue(),String(item[i]));await result(0,['12','3','37.5','66.00','REVIEW ORDER']);});
 await check('Print button invokes native print; printed table fits page width',async()=>{
 const printed=page.waitForEvent('console',m=>m.text()==='ACCEPTANCE_BEFOREPRINT');
 await page.evaluate(()=>addEventListener('beforeprint',()=>console.log('ACCEPTANCE_BEFOREPRINT'),{once:true}));
 await page.getByRole('button',{name:'Print',exact:true}).click();await printed;
 await page.emulateMedia({media:'print'});await expect(page.locator('.controls')).toBeHidden();
 await page.setViewportSize({width:1047,height:740});
 const table=page.locator('#print-table').or(page.locator('.scroll table')).filter({visible:true});
 const box=await table.boundingBox();assert.ok(box.x+box.width<=1047,'Print table clipped: '+JSON.stringify(box));
 await expect(table).toContainText(item[0]);await expect(table).toContainText('66.00');
 await page.screenshot({path:path.join(out,'03-print.png'),fullPage:true});await page.pdf({path:path.join(out,'checklist.pdf'),format:'A4',landscape:true,preferCSSPageSize:true});
 await page.emulateMedia({media:'screen'});
 });
 await page.emulateMedia({media:'screen'});
 await check('Invalid negative, zero pack and target errors; recovery',async()=>{for(const [label,value,error] of [['On hand','-1','nonnegative'],['Pack size','0','exceed zero'],['Target','1','at least reorder point']]){const old=await cell(0,label).inputValue();await cell(0,label).fill(value);await expect(rows.nth(0)).toContainText(error);await cell(0,label).fill(old);}await result(0,['12','3','37.5','66.00','REVIEW ORDER']);});
 await check('Malformed import preserves existing rows and reports error',async()=>{await page.locator('#file').setInputFiles({name:'bad.csv',mimeType:'text/csv',buffer:Buffer.from('bad,header\n')});await expect(msg).toContainText('headers do not match');await expect.poll(()=>cell(0,'Item').inputValue()).toBe(item[0]);});
 await check('Decimal threshold: 0.1 + 0.2 at point 0.3 orders 2 packs',async()=>{await fill(0,['Glaze','litre','','',0.1,0.2,0.3,0.5,0.1,1]);await result(0,['0.3','2','0.2','2.00','REVIEW ORDER']);});
 await check('Decimal full packs: 0.07 target / 0.01 pack orders 7',async()=>{await fill(0,['Glaze','litre','','',0,0,0,0.07,0.01,1]);await result(0,['0','7','0.07','7.00','REVIEW ORDER']);});
 await check('Remove row and empty-table export validation',async()=>{while(await rows.count())await rows.first().getByRole('button',{name:'Remove',exact:true}).click();await page.getByRole('button',{name:'Download results CSV',exact:true}).click();await expect(msg).toContainText('Add a row first');});
 await check('No network requests or browser runtime errors during offline journey',async()=>{assert.deepEqual(network,[]);assert.deepEqual(errors,[]);});
 } catch(e){report.cases.push({name:browser?'Journey setup':'Chromium launch / setup',status:'BLOCKED',error:e.stack});}
 finally {if(page)await page.screenshot({path:path.join(out,'last-state.png'),fullPage:true}).catch(()=>{});if(browser)await browser.close();report.passed=report.cases.filter(c=>c.status==='PASS').length;report.failed=report.cases.filter(c=>c.status!=='PASS').length;fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({out,passed:report.passed,failed:report.failed,sha256:report.sha256}));process.exitCode=report.failed?1:0;}
})();
