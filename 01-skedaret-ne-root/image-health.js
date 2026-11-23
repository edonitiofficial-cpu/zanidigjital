/* Read-only report; external values are inserted as text, never HTML. */
const photoLabels = {ok:'Në rregull',fallback:'Origjinali punon · varianti dështoi',broken:'Fotografi e pavlefshme',unverified:'Nuk u verifikua · provohet përsëri'};
const reasons = {not_found:'Burimi ktheu 404/410.',invalid_image:'Adresa nuk ktheu fotografi të lexueshme.',too_small:'Pamja është tepër e vogël për fotografi lajmi.',source_unavailable:'Burimi nuk lejoi ose nuk përfundoi kontrollin.',size_limit:'Fotografia tejkalon kufirin e kontrollit.',optimized_ok:'Varianti i fotografisë u lexua.',original_ok:'Fotografia origjinale u lexua; portali mund ta përdorë si rezervë.'};
let photoReport;
function photoLink(url, label) {
    try {
        const parsed=new URL(url,location.origin);
        if (!['https:','http:'].includes(parsed.protocol)) return document.createTextNode('');
        const a=document.createElement('a');a.href=parsed.href;a.textContent=label;a.target='_blank';a.rel='noopener noreferrer';return a;
    } catch { return document.createTextNode(''); }
}
function renderPhotoReport() {
    const root=document.getElementById('photo-results');root.replaceChildren();
    const items=(photoReport.images||[]).filter(item=>document.getElementById('photo-filter').value==='all'||item.status!=='ok');
    for (const item of items) {
        const card=document.createElement('article'),title=document.createElement('h2'),badge=document.createElement('span'),reason=document.createElement('p'),links=document.createElement('div');
        title.textContent=item.title;badge.className='badge '+(item.status==='broken'?'broken':item.status==='ok'?'ok':'');badge.textContent=photoLabels[item.status]||'Pa klasifikim';
        reason.textContent=(item.role==='inline'?'Fotografi brenda artikullit. ':'Fotografia kryesore. ')+(reasons[item.reason]||'')+' '+new Date(item.checked_at).toLocaleString('sq-AL');
        links.className='links';links.append(photoLink('/lajme/'+encodeURIComponent(item.slug)+'/','Hap lajmin'),photoLink(item.url,'Hap fotografinë origjinale'));
        card.append(title,badge,reason,links);root.append(card);
    }
    if (!items.length) {const p=document.createElement('p');p.textContent='Nuk ka fotografi për këtë filtër në raportin aktual.';root.append(p);}
}
fetch('/image-health.json',{cache:'no-store'}).then(response=>{if(!response.ok)throw Error();return response.json();}).then(report=>{
    photoReport=report;
    document.getElementById('photo-status').textContent=`Të kontrolluara: ${(report.images||[]).length} · Në pritje: ${report.pending||0} · ${new Date(report.updated_at).toLocaleString('sq-AL')}`;
    document.getElementById('photo-filter').addEventListener('change',renderPhotoReport);renderPhotoReport();
}).catch(()=>{document.getElementById('photo-status').textContent='Raporti ende nuk është krijuar. Gjenerohet kur punon roboti ose veprimi “Kontrollo fotografitë dhe fontet” në Actions.';});
