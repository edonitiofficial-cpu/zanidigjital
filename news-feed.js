/* Homepage: a small initial payload, an explicit archive, search and pagination. */
let newsCache;
let archivePromise;
let newsVisible = 16;
let newsQuery = new URLSearchParams(location.search).get('q') || '';
let newsLoadVersion = 0;
let newsMunicipality = new URLSearchParams(location.search).get('komuna') || '';

async function fetchNewsJSON(path) {
    const response = await fetch(path, { cache: 'no-cache', signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error('Lajmet nuk u ngarkuan.');
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('Lista e lajmeve nuk është e vlefshme.');
    return data;
}

function normalizeSearch(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('sq').trim();
}

function sortNews(items) {
    const timestamp = n => {
        const explicit = Date.parse(n.published_at);
        if (Number.isFinite(explicit)) return explicit;
        const civil = String(n.koha || '').replace(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/, '$3-$2-$1T$4:$5');
        return kosovoCivilTimestamp(civil) || 0;
    };
    return items.map(n => ({ n, time: timestamp(n) })).sort((a,b) => b.time-a.time).map(item => item.n);
}

async function initialNews() {
    if (newsCache) return newsCache;
    let automatic;
    try { automatic = await fetchNewsJSON('/ballina.json'); }
    catch { automatic = await fetchNewsJSON('/news-index.json'); }
    // Manual news is included by the bot. Rendering never waits for Supabase.
    newsCache = sortNews([...new Map(automatic.filter(n => !n.duplicate_of).map(n => [n.slug || krijoSlug(n.titulli), n])).values()]);
    window.allNewsData = newsCache;
    return newsCache;
}

async function loadArchive() {
    if (!archivePromise) {
        archivePromise = fetchNewsJSON('/news-index.json').then(items => {
            newsCache = sortNews([...new Map([...items, ...newsCache].filter(n => !n.duplicate_of).map(n => [n.slug || krijoSlug(n.titulli), n])).values()]);
            window.allNewsData = newsCache;
            return newsCache;
        }).catch(error => { archivePromise = null; throw error; });
    }
    return archivePromise;
}

function newsImage(n, large, lazy = true) {
    const original = safeURL(n.imazhi, '/zanidigjitalfavicon.png');
    return `<img src="${escapeHTML(optimizePhoto(original, large))}" data-original="${escapeHTML(original)}" onerror="imageFallback(this)" alt="" ${lazy ? 'loading="lazy"' : 'fetchpriority="high"'} decoding="async" width="${large ? 800 : 400}" height="${large ? 500 : 250}" class="w-full ${large ? 'h-full' : 'h-40'} object-cover">`;
}

function optimizePhoto(url, large) {
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=${large ? 1000 : 480}&output=webp&q=80`;
}

function featuredCard(n, i) {
    const [bg] = getCatStyles(n.kategoria);
    return `<a href="${newsPath(n)}" class="${i === 0 ? 'featured-main md:col-span-2 md:row-span-2' : 'featured-small h-48 md:h-auto'} group relative rounded-xl overflow-hidden shadow-sm bg-white">
        ${newsImage(n, true, i !== 0)}<div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent"></div>
        <div class="absolute bottom-0 ${i === 0 ? 'p-6' : 'p-4'}"><span class="${bg} text-white text-[10px] font-bold px-2 py-1 rounded uppercase">${escapeHTML(n.kategoria)}</span>
        <h3 class="text-white ${i === 0 ? 'text-2xl md:text-3xl' : 'text-base'} font-bold mt-2 group-hover:underline">${escapeHTML(n.titulli)}</h3>
        ${Number(n.source_count)>1 ? `<p class="text-xs mt-2 text-gray-200 source-count">Nga ${Number(n.source_count)} burime</p>` : ''}
        ${i === 0 ? `<p class="text-gray-200 text-xs mt-3">${escapeHTML(n.koha)}</p>` : ''}</div></a>`;
}

async function loadNews() {
    const version = ++newsLoadVersion;
    const status = document.getElementById('news-status');
    const more = document.getElementById('news-more');
    const category = new URLSearchParams(location.search).get('kategoria');
    try {
        status.textContent = 'Duke ngarkuar lajmet…';
        let all = await initialNews();
        if (category || newsQuery || newsMunicipality) all = await loadArchive();
        if (version !== newsLoadVersion) return;
        if (category) {
            document.getElementById('link-ballina').className = 'hover:text-black transition pb-1';
            const active = document.getElementById(`link-${category}`);
            if (active) { active.className = 'text-black border-b-2 border-black pb-1'; active.setAttribute('aria-current', 'page'); }
        } else document.getElementById('link-ballina').setAttribute('aria-current', 'page');
        let filtered = category ? all.filter(n => n.kategoria === category || (category === 'Teknologji' && n.kategoria === 'Tech')) : all;
        if (newsMunicipality) filtered = filtered.filter(n => Array.isArray(n.komunat) && n.komunat.includes(newsMunicipality));
        const words = normalizeSearch(newsQuery).split(/\s+/).filter(Boolean);
        if (words.length) filtered = filtered.filter(n => words.every(word => normalizeSearch(n.titulli).includes(word)));
        document.getElementById('section-title').textContent = newsQuery ? 'Rezultatet e kërkimit' : newsMunicipality || category || 'Në vëmendje';
        const ranked = filtered.filter(n => Number.isInteger(n.featured_rank)).sort((a,b) => a.featured_rank-b.featured_rank);
        const featured = category || newsQuery || newsMunicipality ? filtered.slice(0,5) : [...ranked, ...filtered.filter(n => !ranked.includes(n))].slice(0,5);
        const featuredSlugs = new Set(featured.map(n => n.slug));
        const remaining = filtered.filter(n => !featuredSlugs.has(n.slug));
        const bento = document.getElementById('bento-grid');
        bento.style.height = featured.length ? '' : 'auto';
        bento.innerHTML = featured.length ? featured.map(featuredCard).join('') : '<p class="md:col-span-4 py-8 text-gray-600">Nuk u gjet asnjë lajm. Provo një kërkim ose kategori tjetër.</p>';
        document.getElementById('te-fundit-grid').innerHTML = remaining.slice(0, newsVisible).map(n => {
            const [, color] = getCatStyles(n.kategoria);
            return `<a href="${newsPath(n)}" class="news-card bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition flex flex-col">${newsImage(n, false)}<div class="p-4 flex-grow flex flex-col"><span class="${color} font-bold text-xs uppercase mb-2">${escapeHTML(n.kategoria)}</span><h3 class="font-bold text-lg leading-snug mb-3">${escapeHTML(n.titulli)}</h3><p class="text-gray-500 text-xs mt-auto">${escapeHTML(n.koha)}</p></div></a>`;
        }).join('');
        document.getElementById('ticker-content').innerHTML = all.slice(0, 10).map(n => `<span class="inline-block mr-10"><a href="${newsPath(n)}">${escapeHTML(n.titulli)}</a></span>`).join('');
        const shown = Math.min(newsVisible, remaining.length) + featured.length;
        status.textContent = `${shown} nga ${filtered.length} lajme${archivePromise ? '' : ' të fundit'}.`;
        more.hidden = newsVisible >= remaining.length && !!archivePromise;
        more.disabled = false;
        more.textContent = 'Lexo më shumë';
    } catch (error) {
        console.error(error);
        status.textContent = 'Lajmet nuk u ngarkuan. Provo përsëri.';
        document.getElementById('bento-grid').innerHTML = '';
        document.getElementById('bento-grid').style.height = 'auto';
        document.getElementById('te-fundit-grid').innerHTML = '';
        document.getElementById('ticker-content').textContent = 'Lajmet nuk u ngarkuan.';
        more.hidden = false; more.disabled = false; more.textContent = 'Provo përsëri';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const municipalities = document.getElementById('municipality-select');
    if (newsMunicipality) {
        const current = new Option(newsMunicipality, newsMunicipality); municipalities.add(current); municipalities.value = newsMunicipality;
    }
    fetch('/municipalities.json').then(response => { if (!response.ok) throw new Error(); return response.json(); }).then(names => {
        municipalities.replaceChildren(new Option('Të gjitha komunat', ''));
        names.forEach(name => municipalities.add(new Option(name, name)));
        municipalities.value = newsMunicipality;
    }).catch(() => { document.getElementById('municipality-note').textContent = 'Lista e komunave nuk u ngarkua. Rifresko faqen për ta provuar përsëri.'; });
    municipalities.addEventListener('change', () => {
        newsMunicipality = municipalities.value; newsVisible = 16;
        const url = new URL(location.href);
        if (newsMunicipality) url.searchParams.set('komuna', newsMunicipality); else url.searchParams.delete('komuna');
        history.replaceState(null, '', url); loadNews();
    });
    const search = document.getElementById('news-search');
    search.value = newsQuery;
    document.getElementById('news-search-form').addEventListener('submit', event => {
        event.preventDefault(); newsQuery = search.value.trim(); newsVisible = 16;
        const url = new URL(location.href);
        if (newsQuery) url.searchParams.set('q', newsQuery); else url.searchParams.delete('q');
        history.replaceState(null, '', url); loadNews();
    });
    document.getElementById('news-more').addEventListener('click', async event => {
        const button = event.currentTarget;
        button.disabled = true; button.textContent = 'Duke ngarkuar…';
        try { await initialNews(); await loadArchive(); newsVisible += 16; await loadNews(); }
        catch { document.getElementById('news-status').textContent = 'Arkivi nuk u ngarkua. Provo përsëri.'; button.disabled = false; button.textContent = 'Provo përsëri'; }
    });
    document.getElementById('ticker-pause').addEventListener('click', event => {
        const paused = event.currentTarget.getAttribute('aria-pressed') !== 'true';
        event.currentTarget.setAttribute('aria-pressed', String(paused));
        event.currentTarget.textContent = paused ? 'Vazhdo' : 'Pauzë';
        document.getElementById('ticker-content').style.animationPlayState = paused ? 'paused' : 'running';
    });
});
