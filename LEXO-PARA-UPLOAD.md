# Përditësimi i fotografive dhe korrigjimi i 9 gabimeve

Kjo paketë përfshin edhe rregullimet e KEDS-it, motit dhe artikujve nga paketa 04. Për këtë publikim përdor vetëm paketën 05. Admini/Supabase nuk përfshihen.

1. Ngarko përmbajtjen e `01-skedaret-ne-root` në rrënjën e repository-t ekzistues. Përfshi nënfolderët tools/ dhe fonts/. Mos krijo folder me emrin 01-skedaret-ne-root në GitHub.
2. Ngarko fajllat YML brenda `02-workflows-ne-dotgithub-workflows` te `.github/workflows/` në main.
3. Te Actions nise **Kontrollo fotografitë dhe fontet**. Ky veprim riparon vetëm mbetjen e gabuar të fontit në HTML-të aktuale të repository-t dhe kontrollon deri 30 fotografi. Nuk ndryshon tekstin, datat ose URL-të e lajmeve dhe nuk poston në Facebook.
4. Raporti hapet te `https://zanidigjital.com/image-health.html` pasi të përfundojë publikimi Pages. Roboti e përditëson edhe gjatë punës normale: deri 5 fotografi për nisje, me cache 6 orë; burimet e bllokuara/timeout provohen përsëri pas 1 ore. Kontrolli përfshin kryesoren dhe deri 2 fotografi të brendshme për lajm, te 150 artikujt e parë të grupit të kontrollit. Raporti është publik por i përjashtuar nga indeksimi; përmban vetëm të dhëna publike të lajmeve.
5. Opsionale: nise **Përgatit pamjen nga lajmet aktuale** për ta plotësuar HTML-në statike me lajmet që janë tash në repository. Për KEDS/motin nise **KEDS dhe moti në mbrëmje**, refresh=true. Për rimarrjen/pastrimin e artikujve ekzistues përdor **Pastro artikujt ekzistues nga burimi**.

Nuk përfshihen `lajmet.json`, `ballina.json`, `news-index.json`, `daily-services.json`, `image-health.json`, folderi `lajme/` ose arkivi lokal. Index-i i paketës i lexon lajmet aktuale nga JSON-i online. Mos ngarko index.html ose lajme/ direkt nga projekti lokal në vend të paketës.

Kontrolli dallon fotografinë e pavlefshme (404/410, përmbajtje jo-fotografi, pamje tepër e vogël) nga burimi përkohësisht i bllokuar. Nëse varianti dështon por origjinali punon, kjo raportohet si rezervë funksionale. Raporti nuk fshin ose zëvendëson vetë fotografinë e lajmit; faqja provon origjinalin dhe në dështim shfaq një pamje neutrale shpjeguese. Nuk gjenerohen fotografi artificiale.

Ndryshimet janë lokale derisa t'i ngarkosh. Pas publikimit bëj Ctrl+F5. Nëntë gabimet e editorit vinin nga mbetja `500;700;800;900&display=swap` në fillim të CSS-së; parseri i njëjtë me VS Code tani raporton 0 gabime te index.html. `npm ci` dhe `npm run test:markup` e përsërisin kontrollin.
