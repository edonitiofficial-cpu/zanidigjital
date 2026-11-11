/* Preserve old ?lajmi / ?link / ?id URLs while using static article pages. */
document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(location.search);
    const slug = params.get('lajmi');
    const message = document.getElementById('legacy-status');
    if (slug) {
        if (/^[a-z0-9-]+$/.test(slug)) location.replace('/lajme/' + encodeURIComponent(slug) + '/');
        else message.textContent = 'Lidhja e lajmit nuk është e vlefshme.';
        return;
    }
    const link = params.get('link');
    const id = params.get('id') ?? params.get('index');
    if (!link && id === null) { message.textContent = 'Zgjedh një lajm nga ballina.'; return; }
    try {
        // Numeric legacy IDs refer to positions in the original full archive.
        const response = await fetch('/lajmet.json', { cache: 'no-cache' });
        if (!response.ok) throw new Error();
        const data = await response.json();
        const news = link ? data.find(item => item.link_origjinal === link) : /^\d+$/.test(id) ? data[Number(id)] : null;
        if (!news?.slug) { message.textContent = 'Lajmi nuk u gjet.'; return; }
        location.replace('/lajme/' + encodeURIComponent(news.slug) + '/');
    } catch { message.textContent = 'Lajmi nuk u ngarkua. Provo përsëri më vonë.'; }
});
