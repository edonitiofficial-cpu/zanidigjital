document.addEventListener('DOMContentLoaded',()=>{
    const article=document.querySelector('.article-body');
    if(!article)return;
    // Existing published HTML can be cleaned without replacing it with a local archive.
    const bodyParagraphs=[...document.querySelectorAll('.permbajtja>p')];
    const text=el=>el.textContent.replace(/\u200b/g,'').trim().toLocaleLowerCase('sq');
    const nav=new Set(['top lajme','jobs','real estate','të fundit','te fundit']);
    const relative=value=>/^\d+\s+(sekond(?:a|[eë])?|minut(?:a|[eë])?|or[eë]|dit[eë]|jav[eë]|muaj|vit(?:e|esh)?)\s+m[eë]\s+par[eë]$/i.test(value);
    for(let index=Math.max(0,bodyParagraphs.length-18);index<bodyParagraphs.length;index++){
        const marker=bodyParagraphs.slice(index).some(el=>text(el)==='top lajme')||bodyParagraphs.slice(Math.max(0,index-3),index).some(el=>relative(text(el)));
        if(marker&&nav.has(text(bodyParagraphs[index]))&&bodyParagraphs.slice(index).filter(el=>nav.has(text(el))).length>=2){
            let start=index;
            while(start>0&&(['nga','telegrafi'].includes(text(bodyParagraphs[start-1]))||relative(text(bodyParagraphs[start-1]))))start--;
            bodyParagraphs.slice(start).forEach(el=>el.remove());break;
        }
    }
    const canonical=document.querySelector('link[rel="canonical"]')?.href||location.href;
    const status=document.getElementById('article-share-status');
    const copy=document.getElementById('copy-article-link');
    copy?.addEventListener('click',async()=>{
        try {
            if(!navigator.clipboard?.writeText)throw new Error();
            await navigator.clipboard.writeText(canonical);
            status.textContent='Lidhja u kopjua.';
        } catch {status.textContent='Kopjo lidhjen nga adresa e shfletuesit.';}
    });
    const share=document.getElementById('share-article');
    if(share&&navigator.share){
        share.hidden=false;
        share.addEventListener('click',async()=>{
            try {await navigator.share({title:document.querySelector('h1').textContent,url:canonical});}
            catch(error){if(error.name!=='AbortError')status.textContent='Përdor njërin nga butonat e shpërndarjes.';}
        });
    }
    const progress=document.getElementById('reading-progress'),body=document.querySelector('.permbajtja');
    let pending=false;
    function draw(){
        pending=false;
        if(!body||!progress)return;
        const rect=body.getBoundingClientRect();
        const range=rect.height-innerHeight*.5;
        const fraction=range>0?(innerHeight*.3-rect.top)/range:(rect.top<innerHeight*.5?1:0);
        progress.style.transform=`scaleX(${Math.max(0,Math.min(1,fraction))})`;
    }
    function update(){if(!pending){pending=true;requestAnimationFrame(draw);}}
    addEventListener('scroll',update,{passive:true});addEventListener('resize',update,{passive:true});draw();
});
