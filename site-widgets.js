/* Public widgets. Never write vote counters directly from the browser. */
let widgetAdClosed = false;
let activePoll = null;
let pollOptions = [];
let votePending = false;
let publicWidgetsStarted = false;

function initPublicWidgets() {
    if (!window.supabase || publicWidgetsStarted) return;
    publicWidgetsStarted = true;
    if (!window.sb) window.sb = window.supabase.createClient('https://qqgkhioaqsbzygwconbh.supabase.co', 'sb_publishable_2LH0wWF2qnbrWZjwZWBlyg_6-4sSYai');
    loadBanners(); initMobileAds();
    if (document.getElementById('poll-container')) {
        setupNewsletter(); loadJobs(); loadPoll();
        const jobs = document.getElementById('jobs-carousel');
        document.getElementById('btn-jobs-left').onclick = () => jobs.scrollBy({left:-300,behavior:'smooth'});
        document.getElementById('btn-jobs-right').onclick = () => jobs.scrollBy({left:300,behavior:'smooth'});
    }
}
window.addEventListener('supabase-ready', initPublicWidgets);
function publicWidgetsUnavailable() {
    if (publicWidgetsStarted) return;
    const poll=document.getElementById('poll-container'),jobs=document.getElementById('jobs-carousel');
    if(poll)poll.textContent='Sondazhi nuk është i disponueshëm për momentin.';
    if(jobs)jobs.textContent='Vendet e punës nuk janë të disponueshme për momentin.';
}
window.addEventListener('supabase-failed',publicWidgetsUnavailable);
document.addEventListener('DOMContentLoaded',()=>{setupNewsletter();initPublicWidgets();setTimeout(publicWidgetsUnavailable,8000);});

async function loadBanners() {
    if (!window.sb) return;
    try {
        const { data, error } = await window.sb.from('banners').select('*').eq('status', 'active').order('created_at', { ascending: false });
        if (error) throw error;
        const slots = document.getElementById('banner-top-container') ? {
            homepage_top: 'banner-top-container', homepage_middle: 'banner-middle-container',
            sidebar_left: 'sidebar-left-container', sidebar_right: 'sidebar-right-container'
        } : {
            article_top: 'banner-article-top', article_bottom: 'banner-article-bottom',
            sidebar_left: 'sidebar-left-container', sidebar_right: 'sidebar-right-container'
        };
        for (const [position, id] of Object.entries(slots)) {
            const container = document.getElementById(id);
            const banner = (data || []).find(b => b.position === position);
            if (!container || !banner || !safeURL(banner.image_url, '')) continue;
            const link = document.createElement('a');
            link.href = safeURL(banner.link_url); link.target = '_blank'; link.rel = 'noopener noreferrer sponsored';
            link.className = 'block rounded-xl overflow-hidden shadow-sm';
            const label = document.createElement('span'); label.textContent = 'Sponsorizuar'; label.className = 'text-xs text-gray-500 block mb-2';
            const img = document.createElement('img'); img.src = safeURL(banner.image_url); img.alt = 'Reklamë e sponsorizuar'; img.loading = 'lazy'; img.className = 'w-full h-auto rounded-xl';
            link.append(label, img); container.replaceChildren(link);
        }
    } catch (error) { console.warn('Reklamat nuk u ngarkuan:', error); }
}

function mbyllMobileAd() {
    widgetAdClosed = true;
    try { sessionStorage.setItem('zani-ad-closed', '1'); } catch {}
    const popup = document.getElementById('mobile-popup');
    if (popup) popup.style.display = 'none';
}

async function initMobileAds() {
    if (innerWidth > 767 || !window.sb || widgetAdClosed) return;
    try {
        if (sessionStorage.getItem('zani-ad-closed')) return;
        const { data, error } = await window.sb.from('banners').select('image_url,link_url').eq('status', 'active').eq('position', 'mobile_popup').order('created_at', { ascending: false }).limit(1);
        if (error || !data?.length || !safeURL(data[0].image_url, '')) return;
        const popup = document.getElementById('mobile-popup');
        if (!popup) return;
        document.getElementById('mobile-popup-img').src = safeURL(data[0].image_url);
        const link = document.getElementById('mobile-popup-link'); link.href = safeURL(data[0].link_url); link.rel = 'noopener noreferrer sponsored';
        setTimeout(() => {
            if (widgetAdClosed || innerWidth > 767) return;
            popup.classList.remove('translate-y-[150%]', 'opacity-0');
            popup.classList.add('translate-y-0', 'opacity-100');
        }, 10000);
    } catch (error) { console.warn('Reklama mobile nuk u ngarkua:', error); }
}

async function loadJobs() {
    const carousel = document.getElementById('jobs-carousel');
    if (!carousel) return;
    try {
        if (!window.sb) throw new Error('Shërbimi nuk është i disponueshëm.');
        const { data, error } = await window.sb.from('jobs').select('position,company,location,apply_link').eq('status', 'published').order('created_at', { ascending: false });
        if (error) throw error;
        const section = carousel.closest('section');
        if (!data?.length) { section.hidden = true; return; }
        section.hidden = false;
        carousel.innerHTML = data.map(job => `<a href="${escapeHTML(safeURL(job.apply_link))}" target="_blank" rel="noopener noreferrer" class="min-w-[260px] md:min-w-[320px] snap-start bg-white border border-gray-200 p-6 rounded-2xl shadow-sm"><h3 class="font-bold text-lg">${escapeHTML(job.position)}</h3><p class="text-gray-600 text-sm mt-2">${escapeHTML(job.company)} ${escapeHTML(job.location)}</p><span class="inline-block mt-6 bg-black text-white text-xs font-bold px-4 py-2 rounded-lg">Apliko</span></a>`).join('');
    } catch (error) { carousel.textContent = 'Vendet e punës nuk u ngarkuan.'; console.warn(error); }
}

function votedInPoll(id) {
    try { return localStorage.getItem('voted_' + id) === 'true'; } catch { return false; }
}

function renderPoll() {
    const container = document.getElementById('poll-container');
    if (!container || !activePoll) return;
    const slider = pollOptions.length === 1 && pollOptions[0].option_text === 'SLIDER_SUM';
    const heading = `<h3 class="text-xl font-bold mb-5">${escapeHTML(activePoll.question)}</h3>`;
    if (votedInPoll(activePoll.id)) {
        const total = Number(activePoll.total_votes) || 0;
        if (slider) {
            const average = total ? Math.round(Number(pollOptions[0].votes) / total) : 0;
            container.innerHTML = heading + `<p class="text-gray-600 mb-2">Mesatarja e votuesve</p><p class="text-3xl font-black">${average}%</p><p class="text-sm text-gray-500 mt-3">${total} vota</p>`;
        } else {
            const sum = pollOptions.reduce((n, o) => n + (Number(o.votes) || 0), 0);
            container.innerHTML = heading + pollOptions.map(o => {
                const percent = sum ? Math.round((Number(o.votes) || 0) / sum * 100) : 0;
                return `<div class="mb-4"><div class="flex justify-between gap-3 text-sm mb-1"><span>${escapeHTML(o.option_text)}</span><strong>${percent}%</strong></div><div class="bg-gray-100 rounded-full h-3 overflow-hidden"><div class="bg-blue-700 h-full" style="width:${percent}%"></div></div></div>`;
            }).join('') + `<p class="text-sm text-gray-500">${sum} vota</p>`;
        }
        return;
    }
    container.innerHTML = heading;
    if (slider) {
        const label = document.createElement('label'); label.htmlFor = 'poll-slider'; label.className = 'block font-bold mb-4'; label.textContent = 'Vlerësimi yt: 50%';
        const input = document.createElement('input'); input.type = 'range'; input.id = 'poll-slider'; input.min = '0'; input.max = '100'; input.value = '50'; input.className = 'w-full';
        input.addEventListener('input', () => label.textContent = `Vlerësimi yt: ${input.value}%`);
        const button = document.createElement('button'); button.type = 'button'; button.textContent = 'Voto'; button.className = 'w-full mt-5 bg-black text-white font-bold py-3 rounded-xl';
        button.addEventListener('click', () => submitPollVote(pollOptions[0].id, Number(input.value)));
        container.append(label, input, button);
    } else {
        pollOptions.forEach(option => {
            const button = document.createElement('button'); button.type = 'button'; button.textContent = option.option_text;
            button.className = 'block w-full text-left font-bold px-5 py-3 mb-3 rounded-xl border-2 border-gray-200 hover:border-blue-700';
            button.addEventListener('click', () => submitPollVote(option.id, 1)); container.append(button);
        });
    }
}

async function loadPoll() {
    const container = document.getElementById('poll-container');
    if (!container) return;
    try {
        if (!window.sb) throw new Error('Sondazhi nuk është i disponueshëm.');
        const { data, error } = await window.sb.from('polls').select('*').eq('status', 'active').lte('start_date', new Date().toISOString()).order('start_date', { ascending: false }).limit(1);
        if (error) throw error;
        if (!data?.length) { container.textContent = 'Për momentin nuk ka sondazh aktiv.'; return; }
        activePoll = data[0];
        const result = await window.sb.from('poll_options').select('*').eq('poll_id', activePoll.id).order('id', { ascending: true });
        if (result.error) throw result.error;
        pollOptions = result.data || [];
        if (!pollOptions.length) { container.textContent = 'Sondazhi po përgatitet.'; return; }
        renderPoll();
    } catch (error) { container.textContent = 'Sondazhi nuk u ngarkua. Provo më vonë.'; console.warn(error); }
}

async function submitPollVote(optionId, value) {
    if (votePending || !activePoll || votedInPoll(activePoll.id)) return;
    votePending = true;
    const container = document.getElementById('poll-container');
    container.querySelectorAll('button').forEach(b => b.disabled = true);
    try {
        let voter = localStorage.getItem('zani-voter-id');
        if (!voter) { voter = crypto.randomUUID(); localStorage.setItem('zani-voter-id', voter); }
        const { error } = await window.sb.rpc('vote_in_poll', {
            p_poll_id: String(activePoll.id), p_option_id: String(optionId), p_voter_id: voter, p_value: value
        });
        if (error) throw error;
        localStorage.setItem('voted_' + activePoll.id, 'true');
        await loadPoll();
    } catch (error) {
        renderPoll();
        const message = document.createElement('p'); message.className = 'vote-error'; message.setAttribute('role', 'alert');
        message.textContent = 'Vota nuk u ruajt. Provo përsëri më vonë.'; container.append(message); console.warn('Votimi dështoi:', error.code || 'network');
    } finally { votePending = false; }
}

function setupNewsletter() {
    const form = document.getElementById('newsletter-form');
    if (!form || form.dataset.bound) return;
    form.dataset.bound = 'true';
    const message = document.createElement('p'); message.className = 'text-sm mt-3'; message.setAttribute('role', 'status'); form.after(message);
    form.addEventListener('submit', async event => {
        event.preventDefault(); const button = document.getElementById('nl-btn'); button.disabled = true; button.textContent = 'Duke ruajtur…';
        try {
            if (!window.sb) throw new Error('Shërbimi nuk është i disponueshëm.');
            const { error } = await window.sb.from('newsletter_subscribers').insert([{ email: document.getElementById('nl-email').value.trim().toLowerCase() }]);
            if (error) throw error;
            message.textContent = 'Faleminderit për abonimin!'; form.reset();
        } catch { message.textContent = 'Abonimi nuk u ruajt ose emaili është tashmë i abonuar. Provo më vonë.'; }
        finally { button.disabled = false; button.textContent = 'Abonohu'; }
    });
}
