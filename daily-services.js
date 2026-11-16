/* Render source text with DOM nodes; never interpret remote markup as HTML. */
(() => {
    const zone = 'Europe/Belgrade';
    const today = () => {
        const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {timeZone:zone, year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(new Date()).map(part=>[part.type,part.value]));
        return `${p.year}-${p.month}-${p.day}`;
    };
    const months = ['janar','shkurt','mars','prill','maj','qershor','korrik','gusht','shtator','tetor','nëntor','dhjetor'];
    const dateLabel = value => { const [year, month, day] = value.split('-'); return `${Number(day)} ${months[Number(month)-1]} ${year}`; };
    function node(tag, text, cls) {
        const el = document.createElement(tag);
        if (text) el.textContent = text;
        if (cls) el.className = cls;
        return el;
    }
    function status(id, text = '') {
        const el = document.getElementById(id);
        el.textContent = text;
        el.hidden = !text;
    }
    function renderWeather(source) {
        status('weather-status');
        const content = document.getElementById('weather-content');
        content.replaceChildren();
        const forecast = source.forecasts?.find(item => /^\d{4}-\d{2}-\d{2}$/.test(item.date) && item.date >= today());
        const sourceLink = document.getElementById('weather-source');
        sourceLink.href = 'https://www.meteokosova.com/';
        sourceLink.textContent = 'Shiko parashikimin te Meteo Kosova ↗';
        if (!forecast) {
            content.append(node('h4', 'Çfarë moti na pret?'), node('p', 'Parashikimet ditore dhe zhvillimet e motit në Kosovë, nga Meteo Kosova.', 'weather-excerpt'));
            return;
        }
        const date = node('time', dateLabel(forecast.date), 'weather-date');
        date.dateTime = forecast.date;
        const title = node('h4', forecast.title);
        content.append(date, title, node('p', forecast.excerpt, 'weather-excerpt'));
        try {
            const url = new URL(forecast.url);
            if (url.protocol !== 'https:' || !['www.meteokosova.com','meteokosova.com'].includes(url.hostname)) return;
            sourceLink.href = url.href;
            sourceLink.textContent = 'Lexo parashikimin e plotë ↗';
        } catch {}
    }
    function renderKeds(source) {
        status('keds-status');
        const content = document.getElementById('keds-content');
        const region = document.getElementById('keds-region');
        const date = document.getElementById('keds-date');
        const filters = document.querySelector('#daily-services .service-filters');
        const futureDates = source.dates?.filter(value => value >= today()) || [];
        if (!source.notices?.length || !source.regions?.length || !futureDates.length) {
            filters.hidden = true;
            content.textContent = 'Shiko njoftimet për vendbanimin tënd dhe oraret e punimeve te KEDS.'; return;
        }
        filters.hidden = false;
        region.replaceChildren(...source.regions.map(value => new Option(value, value)));
        // Only identical region names are selected automatically; no village mapping is guessed.
        const municipality = document.getElementById('municipality-select')?.value;
        if (source.regions.includes(municipality)) region.value = municipality;
        date.replaceChildren(...futureDates.map(value => new Option(dateLabel(value), value)));
        region.disabled = date.disabled = false;
        function showNotice() {
            content.replaceChildren();
            const notice = source.notices.find(item => item.region === region.value && item.date === date.value);
            if (!notice) { content.append(node('p', 'Shiko njoftimin për këtë rajon dhe datë te KEDS.')); return; }
            if (notice.status === 'none') {
                content.append(node('p', 'Nuk ka njoftim të publikuar për këtë rajon dhe datë në të dhënat e marra nga KEDS.', 'service-empty'));
                return;
            }
            const details = node('details', '', 'keds-details');
            details.append(node('summary', `Shiko vendbanimet dhe oraret · ${region.value}`));
            details.append(node('div', notice.text, 'keds-notice'));
            content.append(details);
            if (source.status === 'error' || !source.updated_at || Date.now() - Date.parse(source.updated_at) > 30 * 3600000) {
                content.append(node('p', 'Konfirmo njoftimin për këtë datë te KEDS.', 'service-note'));
            }
        }
        region.addEventListener('change', showNotice); date.addEventListener('change', showNotice); showNotice();
        window.addEventListener('municipality-changed', event => {
            if (source.regions.includes(event.detail)) { region.value = event.detail; showNotice(); }
        });
    }
    document.addEventListener('DOMContentLoaded', async () => {
        if (!document.getElementById('daily-services')) return;
        try {
            const response = await fetch('/daily-services.json', {cache:'no-store', signal:AbortSignal.timeout(12000)});
            if (!response.ok) throw new Error('Snapshot unavailable');
            const data = await response.json();
            renderWeather(data.weather || {}); renderKeds(data.keds || {});
        } catch {
            renderWeather({}); renderKeds({});
        }
    });
})();
