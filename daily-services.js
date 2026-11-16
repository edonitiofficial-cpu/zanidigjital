/* Render source text with DOM nodes; never interpret remote markup as HTML. */
(() => {
    const zone = 'Europe/Belgrade';
    const today = () => {
        const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {timeZone:zone, year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(new Date()).map(part=>[part.type,part.value]));
        return `${p.year}-${p.month}-${p.day}`;
    };
    const months = ['janar','shkurt','mars','prill','maj','qershor','korrik','gusht','shtator','tetor','nëntor','dhjetor'];
    const regions=['Prishtinë','Pejë','Prizren','Ferizaj','Mitrovicë','Gjakovë','Gjilan'];
    let selectMunicipality=null;
    let userSelectedRegion=false;
    window.addEventListener('municipality-changed',event=>selectMunicipality?.(event.detail));
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
        const availableDates=futureDates.length?futureDates:Array.from({length:5},(_,offset)=>{
            const day=new Date(today()+'T12:00:00Z');day.setUTCDate(day.getUTCDate()+offset);return day.toISOString().slice(0,10);
        });
        const availableRegions=source.regions?.length?source.regions:regions;
        filters.hidden = false;
        const previousRegion=region.value,previousDate=date.value;
        region.replaceChildren(...availableRegions.map(value => new Option(value, value)));
        if(availableRegions.includes(previousRegion))region.value=previousRegion;
        // Only identical region names are selected automatically; no village mapping is guessed.
        const municipality = document.getElementById('municipality-select')?.value;
        if (!userSelectedRegion && availableRegions.includes(municipality)) region.value = municipality;
        date.replaceChildren(...availableDates.map(value => new Option(dateLabel(value), value)));
        if(availableDates.includes(previousDate))date.value=previousDate;
        region.disabled = date.disabled = false;
        function showNotice() {
            content.replaceChildren();
            const notice = source.notices?.find(item => item.region === region.value && item.date === date.value);
            if (!notice) {
                content.append(node('p','Zgjidh rajonin dhe ditën. Njoftimin për këtë përzgjedhje mund ta kontrollosh edhe te KEDS.','service-empty'));
                return;
            }
            if (notice.status === 'none') {
                content.append(node('span','S’ka njoftim për punime','keds-state keds-state-clear'));
                content.append(node('p',`Për ${region.value}, më ${dateLabel(date.value)}, nuk ka njoftim të publikuar për punime të planifikuara në të dhënat e KEDS-it.`, 'service-empty'));
                return;
            }
            content.append(node('span','Ka ndërprerje të planifikuara','keds-state'));
            const outages=Array.isArray(notice.outages)?notice.outages:[];
            if(outages.length){
                const list=node('div','','keds-outages');
                outages.forEach(outage=>{
                    const card=node('div','','keds-outage');
                    card.append(node('p',`${outage.start} – ${outage.end}`,'outage-time'));
                    card.append(node('p',outage.locations?`Vendbanimet: ${outage.locations}`:'Vendbanimet janë në njoftimin e plotë.','outage-places'));
                    if(outage.reason)card.append(node('p',`Arsyeja: ${outage.reason}`,'outage-reason'));
                    list.append(card);
                });
                content.append(list);
            }
            const details = node('details', '', 'keds-details');
            details.open=!outages.length;
            details.append(node('summary', `Njoftimi i plotë · ${region.value}`));
            details.append(node('div', notice.text, 'keds-notice'));
            content.append(details);
            content.append(node('p','Njoftime për punime të planifikuara; defektet e papritura nuk përfshihen.','service-note'));
            if (source.status === 'error' || !source.updated_at || Date.now() - Date.parse(source.updated_at) > 30 * 3600000) {
                content.append(node('p', 'Konfirmo njoftimin për këtë datë te KEDS.', 'service-note'));
            }
        }
        region.onchange=()=>{userSelectedRegion=true;showNotice();};date.onchange=showNotice;showNotice();
        selectMunicipality=value=>{if(availableRegions.includes(value)){region.value=value;showNotice();}};
    }
    document.addEventListener('DOMContentLoaded', async () => {
        if (!document.getElementById('daily-services')) return;
        renderWeather({});renderKeds({});
        async function load(attempt=0){
            try {
                const response=await fetch('/daily-services.json',{cache:'no-store',signal:AbortSignal.timeout(12000)});
                if(!response.ok)throw new Error('Snapshot unavailable');
                const data=await response.json();
                try{renderWeather(data.weather||{});}catch{renderWeather({});}
                try{renderKeds(data.keds||{});}catch{renderKeds({});}
                if((!data.weather?.forecasts?.length||!data.keds?.notices?.length)&&attempt<4)setTimeout(()=>load(attempt+1),15000*Math.min(attempt+1,2));
            }catch{
                if(attempt<4)setTimeout(()=>load(attempt+1),15000*Math.min(attempt+1,2));
            }
        }
        await load();
    });
})();
