/* Run with Playwright available on NODE_PATH. All service mutations are mocked. */
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg' };
const server = http.createServer((request, response) => {
    let file;
    try { file = path.resolve(root, '.' + decodeURIComponent(new URL(request.url, 'http://localhost').pathname)); }
    catch { response.writeHead(400).end(); return; }
    if (!file.startsWith(root + path.sep) && file !== root) { response.writeHead(403).end(); return; }
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
    if (!fs.existsSync(file)) { response.writeHead(404).end(); return; }
    response.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' }); fs.createReadStream(file).pipe(response);
});

(async () => {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    const browser = await chromium.launch({ channel: 'chrome', headless: true });
    try {
        const context = await browser.newContext({ serviceWorkers: 'block' });
        await context.addInitScript(()=>document.addEventListener('DOMContentLoaded',()=>{
            window.serverHero=document.querySelector('#bento-grid>a img');
            window.serverLatest=document.querySelector('#te-fundit-grid>a');
        },{once:true}));
        await context.route('https://qqgkhioaqsbzygwconbh.supabase.co/**', route => route.fulfill({ contentType: 'application/json', body: '[]' }));
        const page = await context.newPage(); const errors = []; page.on('pageerror', error => errors.push(error.message));
        const newsRequests=[]; page.on('request',request=>{const url=new URL(request.url());if(url.origin===base)newsRequests.push(url.pathname);});
        await page.setViewportSize({ width: 1440, height: 1000 });
        await page.goto(base, { waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelectorAll('#te-fundit-grid a').length === 16).catch(async error=>{console.error({errors,status:await page.locator('#news-status').textContent()});throw error;});
        assert.equal(await page.locator('#bento-grid > a').count(), 5);
        assert.equal(await page.evaluate(()=>window.serverHero===document.querySelector('#bento-grid>a img')),true);
        assert.ok(await page.locator('#main-content').evaluate(el => el.getBoundingClientRect().width) >= 1050);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        await page.screenshot({ path: path.join(root, 'preview-desktop.png'), fullPage: true });
        await page.locator('#news-more').click();
        await page.waitForFunction(() => document.querySelectorAll('#te-fundit-grid a').length === 32);
        assert.equal(await page.evaluate(()=>window.serverLatest===document.querySelector('#te-fundit-grid>a')),true);
        assert.equal(newsRequests.includes('/news-catalog.json'),false);
        assert.equal(newsRequests.includes('/news-index.json'),false);
        await page.locator('#news-search').fill('Kosove');
        await page.locator('#news-search-form button').click();
        await page.waitForFunction(() => document.getElementById('section-title').textContent === 'Rezultatet e kërkimit');
        assert.ok(await page.locator('#bento-grid > a').count() > 0);
        const titles = await page.locator('#bento-grid h3, #te-fundit-grid h3').allTextContents();
        assert.ok(titles.every(t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().includes('kosove')));
        assert.equal(newsRequests.includes('/news-index.json'),false);
        assert.ok(newsRequests.some(url=>url.startsWith('/news-archive/')));
        await page.goto(base + '/?kategoria=Sport', { waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelectorAll('#te-fundit-grid a').length > 0);
        const labels = await page.locator('#te-fundit-grid a > div > span').allTextContents();
        assert.ok(labels.every(label => label === 'Sport'));
        await page.route('**/news-catalog.json',route=>route.fulfill({status:404,body:'Not generated yet'}));
        await page.goto(base+'/?kategoria=Sport',{waitUntil:'networkidle'});
        await page.waitForFunction(()=>document.getElementById('news-status').textContent.includes('lajme')&&!document.getElementById('news-status').textContent.includes('nuk u ngarkuan'));
        assert.ok((await page.locator('#te-fundit-grid a > div > span').allTextContents()).every(label=>label==='Sport'));
        assert.ok(await page.locator('#te-fundit-grid a').count()>0);
        await page.unroute('**/news-catalog.json');
        const fallOrder = await page.evaluate(() => sortNews([
            {titulli:'Before',koha:'25/10/2026 02:45',published_at:'2026-10-25T02:45:00+02:00'},
            {titulli:'After',koha:'25/10/2026 02:15',published_at:'2026-10-25T02:15:00+01:00'}
        ]).map(n=>n.titulli));
        assert.deepEqual(fallOrder,['After','Before']);
        await page.goto(base+'/?komuna='+encodeURIComponent('Pejë'),{waitUntil:'networkidle'});
        await page.waitForFunction(()=>document.querySelectorAll('#bento-grid > a').length>0);
        assert.equal(await page.locator('#municipality-select').inputValue(),'Pejë');
        const municipalityMatches=await page.evaluate(()=>[...document.querySelectorAll('#bento-grid>a,#te-fundit-grid>a')].every(link=>window.allNewsData.some(n=>link.getAttribute('href')===newsPath(n)&&n.komunat?.includes('Pejë'))));
        assert.equal(municipalityMatches,true);
        await page.locator('#municipality-remember').check();
        await page.goto(base,{waitUntil:'networkidle'});
        await page.waitForFunction(()=>document.getElementById('municipality-select').value==='Pejë');
        assert.equal(await page.locator('#municipality-remember').isChecked(),true);
        await page.locator('#municipality-remember').uncheck();
        assert.equal(await page.evaluate(()=>localStorage.getItem('zani-municipality')),null);
        await page.setViewportSize({ width: 390, height: 844 });
        await page.goto(base, { waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelectorAll('#bento-grid > a').length === 5);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        assert.ok(await page.locator('.featured-small').first().evaluate(el => el.getBoundingClientRect().height) < 160);
        await page.screenshot({ path: path.join(root, 'preview-mobile.png'), fullPage: true });
        const services = {
            weather: {status:'ok',updated_at:new Date().toISOString(),forecasts:[{
                title:'Parashikimi <img src=x onerror="window.serviceXSS=1">',date:'2020-01-01',
                excerpt:'Mot me shi.',url:'https://www.meteokosova.com/parashikimi/'
            }]},
            keds: {status:'error',updated_at:new Date().toISOString(),regions:['Prishtinë','Pejë'],dates:['2099-01-01','2099-01-02'],notices:[
                {region:'Prishtinë',date:'2099-01-01',status:'notice',text:'Vendet: <img src=x onerror="window.serviceXSS=1">\nOra 09:00–12:00'},
                {region:'Pejë',date:'2099-01-01',status:'none',text:''},
                {region:'Pejë',date:'2099-01-02',status:'notice',text:'Vendet: Qendra\nOra 10:00–13:00'}
            ]}
        };
        await page.route('**/daily-services.json',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(services)}));
        await page.goto(base,{waitUntil:'networkidle'});
        await page.waitForFunction(()=>!document.getElementById('keds-region').disabled);
        assert.equal(await page.locator('#keds-status').isVisible(),false);
        assert.match(await page.locator('#weather-content').textContent(),/Çfarë moti na pret/);
        assert.doesNotMatch(await page.locator('#daily-services').textContent(),/Përditësuar|21:30|datë të kaluar|Pritet parashikimi/);
        assert.equal(await page.locator('#weather-content time').count(),0);
        assert.equal(await page.locator('#weather-source').getAttribute('href'),'https://www.meteokosova.com/');
        services.weather.forecasts[0].date = await page.evaluate(()=>{
            const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Belgrade',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).map(part=>[part.type,part.value]));
            return `${p.year}-${p.month}-${p.day}`;
        });
        await page.goto(base,{waitUntil:'networkidle'});
        await page.waitForFunction(()=>!!document.querySelector('#weather-content time'));
        assert.match(await page.locator('#weather-content h4').textContent(),/<img/);
        assert.equal(await page.locator('#weather-source').getAttribute('href'),'https://www.meteokosova.com/parashikimi/');
        await page.locator('.keds-details summary').click();
        assert.match(await page.locator('.keds-notice').textContent(),/09:00–12:00/);
        assert.equal(await page.locator('#daily-services img').count(),0);
        assert.equal(await page.evaluate(()=>window.serviceXSS || 0),0);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
        await page.locator('#keds-region').selectOption('Pejë');
        assert.match(await page.locator('#keds-content').textContent(),/Nuk ka njoftim/);
        await page.locator('#keds-date').selectOption('2099-01-02');
        assert.match(await page.locator('.keds-notice').textContent(),/10:00–13:00/);
        await page.screenshot({path:path.join(root,'preview-services.png'),fullPage:true});
        await page.unroute('**/daily-services.json');
        await page.route('**/daily-services.json',route=>route.fulfill({status:503,body:'Unavailable'}));
        await page.goto(base,{waitUntil:'networkidle'});
        await page.waitForFunction(()=>document.querySelector('.service-filters').hidden);
        assert.equal(await page.locator('#weather-status').isVisible(),false);
        assert.match(await page.locator('#weather-content').textContent(),/Çfarë moti na pret/);
        assert.equal(await page.locator('#weather-source').getAttribute('href'),'https://www.meteokosova.com/');
        await page.unroute('**/daily-services.json');
        const first = JSON.parse(fs.readFileSync(path.join(root, 'ballina.json'), 'utf8'))[0];
        await page.goto(base + '/lajme/' + first.slug + '/', { waitUntil: 'networkidle' });
        assert.equal(await page.locator('h1').textContent(), first.titulli);
        assert.equal(await page.locator('.article-source').count(), 1);
        assert.equal(await page.locator('.article-meta').getByText(/min lexim/).count(),1);
        assert.equal(await page.locator('.article-hero').getAttribute('fetchpriority'),'high');
        assert.ok((await page.locator('.article-hero').getAttribute('srcset')).includes('480w'));
        await page.evaluate(()=>{window.testCopied='';Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async value=>{window.testCopied=value;}}});});
        await page.locator('#copy-article-link').click();
        assert.match(await page.locator('#article-share-status').textContent(),/u kopjua/);
        assert.equal(await page.evaluate(()=>window.testCopied),`https://zanidigjital.com/lajme/${first.slug}/`);
        await page.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw new Error('Denied');}}});});
        await page.locator('#copy-article-link').click();
        assert.match(await page.locator('#article-share-status').textContent(),/adresa e shfletuesit/);
        await page.locator('.permbajtja').scrollIntoViewIfNeeded();
        await page.waitForTimeout(50);
        assert.match(await page.locator('#reading-progress').getAttribute('style'),/scaleX/);
        assert.equal(await page.locator('.article-related .related-card').count(),4);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        await page.screenshot({ path: path.join(root, 'preview-article.png'), fullPage: true });
        await page.goto(base+'/artikulli.html?lajmi='+first.slug,{waitUntil:'networkidle'});
        await page.waitForURL('**/lajme/'+first.slug+'/');
        await page.route('**/ballina.json', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify([{ ...first, titulli: '<img src=x onerror="window.xss=1">', imazhi: 'javascript:alert(1)' }]) }));
        await page.goto(base, { waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelector('#bento-grid h3'));
        assert.equal(await page.evaluate(() => window.xss || 0), 0);
        assert.equal(await page.locator('#bento-grid h3 img').count(), 0);
        assert.match(await page.locator('#bento-grid h3').textContent(), /<img/);
        await page.unroute('**/ballina.json');
        await page.route('**/ballina.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
        await page.route('**/news-index.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
        await page.goto(base, { waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.getElementById('news-status').textContent.includes('Provo përsëri'));
        assert.equal(await page.locator('#news-more').textContent(), 'Provo përsëri');
        await page.unroute('**/ballina.json'); await page.unroute('**/news-index.json');
        let voteCalls = 0;
        const pollId = '00000000-0000-0000-0000-000000000001';
        await page.route('https://qqgkhioaqsbzygwconbh.supabase.co/**', async route => {
            const url = route.request().url();
            let body = [];
            if (url.includes('/rpc/vote_in_poll')) { voteCalls++; body = null; }
            else if (url.includes('/poll_options')) body = [{id:'00000000-0000-0000-0000-000000000002',poll_id:pollId,option_text:'Po',votes:voteCalls}];
            else if (url.includes('/polls')) body = [{id:pollId,question:'Sondazh prove',total_votes:voteCalls}];
            await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
        });
        await page.goto(base, {waitUntil:'networkidle'});
        await page.getByRole('button',{name:'Po',exact:true}).click();
        await page.waitForFunction(() => document.getElementById('poll-container').textContent.includes('100%'));
        assert.equal(voteCalls,1);
        assert.equal(await page.locator('#zani-ai-chatbot').count(),0);
        // A fake admin client exercises errors without credentials or service writes.
        await page.route('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2', route => route.fulfill({contentType:'application/javascript',body:`
            window.supabase={createClient(){return {
              auth:{getUser:async()=>({data:{user:{email:'test@example.com'}}}),onAuthStateChange:callback=>{window.testAuthEvent=callback;return {data:{subscription:{unsubscribe(){}}}};}},
              rpc:async()=>({data:window.testAdminAllowed!==false,error:window.testAdminRpcError?{message:'RPC unavailable'}:null}),
              from(table){let write=false;let proxy;proxy=new Proxy({}, {get(_,key){if(key==='then')return resolve=>resolve(write?{data:null,error:{message:'Test write failure'}}:{data:table==='manual_news'?[{id:'test-id',title:'<img src=x onerror="window.adminXss=1">',category:'Lajme',image_url:'javascript:alert(1)',created_at:'2026-11-10T12:00:00Z'}]:[],error:null});return()=>{if(['insert','update','delete'].includes(key))write=true;return proxy;};}});return proxy;}
            };}};
        `}));
        const dialogs=[];page.on('dialog',async dialog=>{dialogs.push(dialog.message());await dialog.accept();});
        await page.goto(base+'/admin.html',{waitUntil:'networkidle'});
        await page.waitForFunction(()=>!document.getElementById('admin-dashboard').classList.contains('hidden'));
        await page.evaluate(async()=>{window.testAdminAllowed=false;await checkSession();});
        assert.equal(await page.locator('#admin-dashboard').isVisible(),false);
        assert.match(await page.locator('#login-error').textContent(),/nuk ka leje/);
        await page.evaluate(async()=>{window.testAdminAllowed=true;window.testAdminRpcError=true;await checkSession();});
        assert.equal(await page.locator('#admin-dashboard').isVisible(),false);
        assert.match(await page.locator('#login-error').textContent(),/nuk u verifikuan/);
        await page.evaluate(async()=>{window.testAdminRpcError=false;await checkSession();window.testAuthEvent('SIGNED_OUT');});
        assert.equal(await page.locator('#admin-dashboard').isVisible(),false);
        await page.evaluate(()=>checkSession());
        assert.equal(await page.evaluate(()=>window.adminXss||0),0);
        assert.equal(await page.locator('#news-table-body p img').count(),0);
        await page.evaluate(()=>{document.getElementById('job-position').value='test';document.getElementById('job-company').value='test';document.getElementById('job-form').dispatchEvent(new Event('submit',{cancelable:true}));});
        await page.waitForTimeout(100);
        assert.ok(dialogs.some(text=>text.includes('Veprimi nuk u ruajt')));
        assert.equal(await page.evaluate(()=>kosovoInputToISO('2026-07-15T14:00')),'2026-07-15T12:00:00.000Z');
        assert.equal(await page.evaluate(()=>kosovoInputToISO('2026-01-15T13:00')),'2026-01-15T12:00:00.000Z');
        assert.equal(await page.evaluate(()=>{try{kosovoInputToISO('2026-03-29T02:30');return false}catch{return true}}),true);
        await page.locator('#nav-robot').click();
        await page.waitForFunction(()=>document.getElementById('robot-status').textContent.includes('Ende nuk ka raport'));
        await page.route('**/bot-status.json',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({
            status:'degraded',finished_at:new Date().toISOString(),counts:{discovered:10,prepared:5,rejected:1,merged:2,skipped:2},
            sources:[{url:'https://example.com/feed',status:'ok',candidates:10}],featured:[],history:[],
            events:[{titulli:'<img src=x onerror="window.reportXss=1">',url:'https://example.com/story',reason:'missing_image',outcome:'rejected'}]
        })}));
        await page.getByRole('button',{name:'Rifresko raportin'}).click();
        await page.waitForFunction(()=>document.getElementById('robot-status').textContent.includes('probleme'));
        assert.equal(await page.locator('#robot-events img').count(),0);
        await page.locator('#robot-filter').selectOption('missing_image');
        assert.match(await page.locator('#robot-events').textContent(),/Mungon fotografia/);
        await page.setViewportSize({width:1440,height:1000});
        await page.screenshot({path:path.join(root,'preview-robot.png'),fullPage:true});
        assert.deepEqual(errors, []);
        const fast=await context.newPage();
        let release;const gate=new Promise(resolve=>release=resolve);
        await fast.route('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2',async route=>{await gate;await route.abort().catch(()=>{});});
        await fast.goto(base,{waitUntil:'domcontentloaded'});
        await fast.waitForFunction(()=>document.querySelectorAll('#te-fundit-grid a').length===16);
        assert.equal(await fast.evaluate(()=>!!window.supabase),false);
        release();await fast.close();
        const articleFast=await context.newPage();
        let articleRelease;const articleGate=new Promise(resolve=>articleRelease=resolve);
        await articleFast.route('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2',async route=>{await articleGate;await route.abort().catch(()=>{});});
        await articleFast.goto(base+'/lajme/'+first.slug+'/',{waitUntil:'domcontentloaded'});
        assert.equal(await articleFast.locator('h1').textContent(),first.titulli);
        assert.equal(await articleFast.evaluate(()=>!!window.supabase),false);
        articleRelease();await articleFast.close();
        console.log('Browser: desktop/mobile, municipality, article, search/paging, safe voting, chatbot removal, robot report, admin errors, DST, and immediate rendering with Supabase stalled OK.');
        await context.close();
        const staticContext=await browser.newContext({javaScriptEnabled:false,serviceWorkers:'block'});
        const staticPage=await staticContext.newPage();
        await staticPage.route('https://**',route=>route.abort());
        await staticPage.goto(base,{waitUntil:'load'});
        assert.equal(await staticPage.locator('#bento-grid>a').count(),5);
        assert.equal(await staticPage.locator('#te-fundit-grid>a').count(),16);
        assert.ok(await staticPage.locator('#bento-grid h3').first().textContent());
        assert.equal(await staticPage.locator('script[src*="cdn.tailwindcss.com"]').count(),0);
        await staticContext.close();
        const offlineContext = await browser.newContext();
        await offlineContext.route('https://qqgkhioaqsbzygwconbh.supabase.co/**',route=>route.fulfill({contentType:'application/json',body:'[]'}));
        const offlinePage=await offlineContext.newPage();
        await offlinePage.goto(base,{waitUntil:'networkidle'});
        await offlinePage.waitForFunction(()=>!!navigator.serviceWorker.controller,{timeout:20000});
        await offlinePage.reload({waitUntil:'networkidle'});
        await offlineContext.setOffline(true);
        await offlinePage.goto(base+'/never-visited-offline/',{waitUntil:'domcontentloaded'});
        assert.match(await offlinePage.locator('h1').textContent(),/Nuk ka lidhje/);
        await offlineContext.close();
        console.log('Service worker: an unvisited page shows the offline fallback correctly.');
    } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
