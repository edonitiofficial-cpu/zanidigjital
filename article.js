document.addEventListener('DOMContentLoaded',()=>{
    const article=document.querySelector('.article-body');
    if(!article)return;
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
