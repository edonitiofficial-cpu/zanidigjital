const robotReasons = {
    accepted:'U përgatit për publikim', same_event:'U bashkua me të njëjtën ngjarje', known_url:'Lidhje e përpunuar më parë',
    invalid_entry:'Titull ose lidhje e pavlefshme', excluded_region:'Jashtë rajonit të përcaktuar', stale_source:'Burim më i vjetër se 72 orë',
    missing_image:'Mungon fotografia e vlefshme', insufficient_text:'Tekst i pamjaftueshëm ose nxjerrja dështoi',
    classification_failed:'Klasifikimi AI dështoi', excluded_topic:'Temë jashtë kategorive të lejuara', insufficient_clean_text:'Tekst i pamjaftueshëm pas pastrimit'
};
let robotLastReport;
function robotTime(value) {
    const date = new Date(value);
    return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat('sq-AL',{timeZone:'Europe/Belgrade',dateStyle:'medium',timeStyle:'short'}).format(date) : '—';
}
function renderRobotEvents() {
    const events = (robotLastReport?.recent_events || robotLastReport?.events || []).filter(event => !document.getElementById('robot-filter').value || event.reason === document.getElementById('robot-filter').value);
    document.getElementById('robot-events').innerHTML = events.length ? `<table class="w-full text-sm bg-white rounded-xl"><thead><tr class="text-left border-b"><th class="p-3">Lajmi</th><th class="p-3">Arsyeja</th></tr></thead><tbody>${events.map(event => `<tr class="border-b"><td class="p-3"><a href="${escapeHTML(safeURL(event.url))}" target="_blank" rel="noopener noreferrer" class="font-semibold hover:underline">${escapeHTML(event.titulli || 'Pa titull')}</a>${event.target_slug ? `<p class="mt-1"><a class="text-blue-700" href="/lajme/${encodeURIComponent(event.target_slug)}/" target="_blank" rel="noopener">Artikulli ku u bashkua</a></p>` : ''}</td><td class="p-3">${escapeHTML(robotReasons[event.reason] || event.reason)}</td></tr>`).join('')}</tbody></table>` : '<p class="text-gray-500">Nuk ka raste për këtë filtër.</p>';
}
async function loadRobotStatus() {
    if (!document.getElementById('login-screen').classList.contains('hidden')) return;
    const status = document.getElementById('robot-status'); status.textContent = 'Duke ngarkuar raportin…';
    try {
        const response = await fetch('/bot-status.json', {cache:'no-cache',signal:AbortSignal.timeout(10000)});
        if (!response.ok) throw new Error();
        const report = await response.json(); robotLastReport = report;
        if (report.status === 'not_run') { status.textContent = 'Ende nuk ka raport nga roboti i përditësuar. Shfaqet automatikisht pas nisjes së ardhshme nga cron-job.'; return; }
        const labels = {ok:'Përfundoi',degraded:'Përfundoi me probleme në përpunim',error:'Dështoi'};
        const stale = Date.now()-Date.parse(report.finished_at)>45*60000;
        status.textContent = `${labels[report.status] || report.status} · ${robotTime(report.finished_at)}${stale ? ' · Nuk ka raport të ri prej më shumë se 45 minutash.' : ''}${report.error_type ? ' · Gabimi: '+report.error_type : ''}`;
        if (report.workflow_url && safeURL(report.workflow_url,'')) {
            const link=document.createElement('a');link.href=safeURL(report.workflow_url);link.target='_blank';link.rel='noopener noreferrer';link.className='text-blue-700 underline ml-3';link.textContent='Hap ekzekutimin në GitHub';status.append(link);
        }
        const counts = report.counts || {};
        document.getElementById('robot-summary').innerHTML = [['discovered','Kandidatë'],['prepared','Të përgatitura'],['merged','Të bashkuara'],['rejected','Të refuzuara'],['skipped','Të lexuara më parë'],['unprocessed','Mbetën për nisjen tjetër']].map(([key,label]) => `<div class="bg-white border rounded-xl p-5"><p class="text-sm text-gray-500">${label}</p><strong class="text-3xl">${Number(counts[key]) || 0}</strong></div>`).join('');
        document.getElementById('robot-sources').innerHTML = (report.sources || []).map(source=>`<p class="bg-white border rounded-lg p-3 mb-2"><strong>${escapeHTML(new URL(safeURL(source.url)).hostname)}</strong> · ${source.status==='ok'?'U lexua':'Dështoi'} · ${Number(source.candidates)||0} kandidatë${source.error_type ? ' · '+escapeHTML(source.error_type) : ''}</p>`).join('');
        document.getElementById('robot-featured').innerHTML = (report.featured || []).map((news,index)=>`<div class="bg-white border rounded-xl p-4 mb-3"><a class="font-bold hover:underline" href="/lajme/${encodeURIComponent(news.slug)}/" target="_blank" rel="noopener">${index+1}. ${escapeHTML(news.titulli)}</a><p class="text-sm text-gray-600 mt-2">${(news.reasons||[]).map(escapeHTML).join(' · ')}</p></div>`).join('') || '<p>Nuk u zgjodhën lajme kryesore në këtë ekzekutim.</p>';
        const select = document.getElementById('robot-filter'); select.replaceChildren(new Option('Të gjitha arsyet',''));
        [...new Set((report.recent_events||report.events||[]).map(event=>event.reason))].forEach(reason=>select.add(new Option(robotReasons[reason]||reason,reason)));
        select.onchange = renderRobotEvents; renderRobotEvents();
        document.getElementById('robot-history').innerHTML = (report.history||[]).map(run=>`<p class="border-b py-3 text-sm">${robotTime(run.finished_at)} · ${escapeHTML(labels[run.status]||run.status)} · ${Number(run.counts?.prepared)||0} të përgatitura · ${Number(run.counts?.rejected)||0} të refuzuara</p>`).join('');
    } catch { status.textContent = 'Raporti nuk u ngarkua. Kontrollo që bot-status.json është përfshirë në upload dhe provo përsëri.'; }
}
