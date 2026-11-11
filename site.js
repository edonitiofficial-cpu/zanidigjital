/* Shared rendering helpers. Values from feeds, the database and AI are text. */
function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
}

function safeURL(value, fallback = '#') {
    if (!String(value || '').trim()) return fallback;
    try {
        const url = new URL(String(value || ''), window.location.origin);
        return ['http:', 'https:'].includes(url.protocol) ? url.href : fallback;
    } catch { return fallback; }
}

function newsPath(news) {
    return '/lajme/' + encodeURIComponent(news.slug || krijoSlug(news.titulli));
}

const civilTimeCache = new Map();
const kosovoClock = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Belgrade', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
});

function kosovoCivilTimestamp(value) {
    if (civilTimeCache.has(value)) return civilTimeCache.get(value);
    const parts = String(value).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/);
    if (!parts) return NaN;
    const target = Date.UTC(+parts[1], +parts[2]-1, +parts[3], +parts[4], +parts[5]);
    // Earlier instant in autumn's repeated hour, matching the admin date input.
    for (const offset of [2, 1]) {
        const instant = target - offset * 3600000;
        const p = Object.fromEntries(kosovoClock.formatToParts(instant).map(p => [p.type, p.value]));
        if (Date.UTC(+p.year, +p.month-1, +p.day, +p.hour, +p.minute) === target) {
            civilTimeCache.set(value, instant); return instant;
        }
    }
    return NaN;
}

function imageFallback(img) {
    if (img.dataset.fallbackUsed) {
        img.onerror = null;
        img.src = '/zanidigjitalfavicon.png';
    } else {
        img.dataset.fallbackUsed = 'true';
        img.src = safeURL(img.dataset.original, '/zanidigjitalfavicon.png');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if ('serviceWorker' in navigator && location.pathname !== '/admin.html') {
        navigator.serviceWorker.register('/sw.js').catch(error => console.warn('Offline cache unavailable:', error.name));
    }
    document.querySelectorAll('nav').forEach(nav => nav.setAttribute('aria-label', 'Kategoritë e lajmeve'));
    document.querySelectorAll('a[target="_blank"]').forEach(a => a.rel = 'noopener noreferrer');
    const email = document.getElementById('nl-email');
    if (email) email.setAttribute('aria-label', 'Emaili për abonim');
    for (const [id, label] of [['btn-jobs-left', 'Punët e mëparshme'], ['btn-jobs-right', 'Punët e ardhshme']]) {
        document.getElementById(id)?.setAttribute('aria-label', label);
    }
});
