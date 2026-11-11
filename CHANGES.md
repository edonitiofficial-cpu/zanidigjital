# Përmirësimet e zbatuara

## Automatizimi pa redaksi ditore — përditësimi i fundit

- Chatbot-i publik, kërkesat ndaj backend-it të tij, ruajtja e bisedave dhe formularët “Baza e AI-së” në admin u hoqën. Klasifikuesi i lajmeve në robot mbetet; nuk ka bisedë me lexuesin.
- Pesë lajmet kryesore zgjidhen automatikisht nga deri 150 lajmet e fundit: freskia deri 40 pikë, paraqitja në ballinën e burimit +12, çdo burim shtesë i ndryshëm +8 deri +24, tema me interes publik +10. Preferohen lajmet brenda 24 orëve dhe larmi me jo më shumë se dy nga i njëjti burim/kategori kur ka alternativa. Nëse mungojnë alternativa, lista plotësohet. Nuk ka miratim ditor manual.
- Kur ekziston koha origjinale e RSS-së, freskia e përzgjedhjes përdor atë kohë. Arsyet e përzgjedhjes janë në admin.
- Bashkimi krahason titujt dhe hyrjet, URL-të pa tracking, numrat, emrat, vendet dhe mohimin. Brenda një dritareje 12-orëshe, përputhjet e forta grupohen me burimet e tyre; teksti nuk sintetizohet nga AI. Segmente të ndryshme interviste me hyrje të njëjtë nuk duhen bashkuar vetëm nga boilerplate-i. Filtrimi është konservativ dhe nuk garanton kapjen e çdo parafrazimi.
- Në arkivin lokal u grupuan 13 përsëritje. Të gjitha faqet dhe tekstet origjinale ruhen; përsëritjet përjashtohen nga listat/RSS dhe canonical-i tregon artikullin kryesor. Arkivi publik i indeksuar ka 6986 lajme të vlefshme.
- 38 komuna në filtrin publik `?komuna=...`, të kombinueshme me kategori dhe kërkim. 1120 lajme kishin përmendje të qartë të komunës në indeksimin e parë. Etiketimi përdor titullin dhe dy paragrafët hyrës, jo hamendësime për fshatra/persona. P.sh. mbiemri Vitia dhe “nga viti 2026” nuk duhen trajtuar si Viti; “Mitrovicë” pa përcaktim nuk caktohet arbitrarisht në njërën komunë. Lajmet e reja etiketohen në çdo nisje të robotit.
- Admin → Shëndeti i robotit: burimet, numrat e kandidatëve, përgatitjet, bashkimet, refuzimet, arsyet konkrete dhe lidhja e artikullit ku u bashkua lajmi. Ruhen deri 1000 raste të fundit dhe 20 përmbledhje ekzekutimesh.
- `bot-status.json` fillon me `not_run`: nuk janë shpikur log-e reale. Mbushen pas nisjes së parë të versionit të ri. Raporti është skedar statik publik dhe përmban vetëm të dhëna të lajmeve publike, pa sekrete. Gabimet fatale shkruajnë vetëm llojin e gabimit; workflow provon ta ruajë raportin edhe kur përpunimi dështon.
- Ballina nuk pret më leximin e lajmeve manuale nga Supabase. Bot-i i përfshin ato në JSON. Supabase për sondazhe/reklama ngarkohet asinkron dhe nuk pengon shfaqjen e lajmeve. Live Server injoron skedarët masivë të gjeneruar gjatë vëzhgimit të ndryshimeve; për një artikull të ndryshuar në atë folder mund të duhet F5.
- Verifikim: 16 teste Python; Chrome për komunën, grupimin në lista, heqjen e chatbot-it, raportin me filtrim, gabimet e adminit dhe shfaqjen e lajmeve ndërkohë që Supabase mbahet i bllokuar. Testohet edhe faqja offline.

Skedarë të rinj për upload: `municipalities.py`, `municipalities.json`, `news_policy.py`, `robot_report.py`, `bot-status.json`, `admin-robot.js`, bashkë me skedarët dhe artikujt e ndryshuar. Nuk kërkohet SQL shtesë për komunat apo raportin; SQL-ja e votimit nga përmirësimi i mëparshëm mbetet e nevojshme për sondazhet.

Pjesët më poshtë dokumentojnë përmirësimin e mëparshëm; pika e chatbot-it është zëvendësuar nga heqja e tij më sipër.

10 nëntor 2026. Të gjitha ndryshimet janë në kopjen lokale; nuk janë publikuar online.

## Ballina dhe artikujt

- Kërkim në titujt e arkivit, me trajtim të ë/ç dhe lidhje të ruajtshme me `?q=`.
- “Lexo më shumë” shton lajme në të njëjtën listë; kategoritë filtrohen saktë, përfshirë Lajme.
- Arkiv i lehtë `news-index.json`, rreth 2.5 MB me tituj/foto/datime, në vend të ngarkimit të 19.6 MB përmbajtje. Ballina fillon me vetëm 150 lajme.
- Desktop: sidebar-et bosh nuk rezervojnë më 600 px; reklamat anësore shfaqen vetëm në ekrane mjaft të gjera.
- Telefon: një lajm kryesor dhe katër rreshta kompaktë; listë më e lehtë për skanim, header më i vogël dhe buton AI më kompakt.
- Pauzë për FLASH, respektim i reduced motion, zoom i lejuar, fokus i dukshëm, emërtime për butonat dhe shkurtore për të kaluar te përmbajtja.
- 6999 artikuj të vlefshëm të indeksuar u rigjeneruan me burimin origjinal, metadata NewsArticle, WhatsApp, escaping të tekstit dhe asetet e përbashkëta. Një rekord bosh në arkiv u përjashtua nga indeksi publik pa ndryshuar databazën historike.
- 4849 faqe më të vjetra morën asetet e përbashkëta dhe lejimin e zoom-it. Nuk u ndryshua koha historike.
- Lidhjet e vjetra `artikulli.html?lajmi=...` ridrejtohen te faqja statike; vetëm ID-të numerike dhe lidhjet origjinale kërkojnë arkivin e plotë për pajtueshmëri.
- U rregulluan destinacionet e reklamave të ballinës; reklamat krijohen me DOM dhe URL të kontrolluara. Reklama mobile nuk rihapet vazhdimisht pasi mbyllet.
- Service worker tani ruan faqe/asete dhe jep një faqe të qartë kur mungon interneti. Cache-i kufizohet në 40 kërkesa për faqe/lajme plus asetet bazë; admini dhe kërkesat e databazës përjashtohen.

## Roboti dhe cron-job i jashtëm

- U hoq vetëm `schedule` i GitHub. `repository_dispatch` me `ndiz_motorin` dhe `workflow_dispatch` ruhen për cron-job-in e jashtëm.
- Të katër RSS-të kontrollohen para përzgjedhjes. Kandidatët ndërthuren sipas burimeve; kufiri mbetet 5 lajme gjithsej. Nuk garantohet nga një lajm për burim nëse një burim dështon ose kandidatët filtrohen.
- Ora përdor zonën e Kosovës dhe kalon automatikisht verë/dimër. Lajmet e reja ruajnë edhe `published_at` me offset.
- JSON i dëmtuar ndal procesin; nuk trajtohet më si arkiv bosh. Ruajtja e JSON bëhet me zëvendësim atomik.
- Slug-et e reja normalizohen saktë; përplasjet marrin prapashtesë pa ndryshuar URL-të e vjetra.
- U kufizua pastrimi i fundit të artikujve që të mos fshijë paragrafë vetëm pse përmendin Facebook apo kampionatin.
- Git commit/push bëhet vetëm në workflow. Facebook ekzekutohet pas push-it të suksesshëm dhe kontrollon që artikulli është i arritshëm.
- RSS përfshin GUID dhe datë me zonë kur ekziston. Sitemap përfshin të gjitha faqet e artikujve në folder, jo vetëm 1000 lajmet e fundit. U shtua robots.txt.

## Admini, asistenti dhe sondazhet

- Fushat e jashtme shfaqen si tekst, me kontroll të URL-ve.
- Admini kontrollon gabimet e shkrimit/fshirjes dhe rikthen butonat pas dështimit. Fotografitë kufizohen në JPG/PNG/WebP deri 8 MB.
- Planifikimi i sondazhit përdor orën e Kosovës, pavarësisht zonës së pajisjes së adminit. Ora që mungon gjatë kalimit pranveror refuzohet; ora e përsëritur në vjeshtë zgjedh paraqitjen e parë.
- Chatbot-i nuk interpreton tekstin e lexuesit apo përgjigjen AI si HTML; historia rikthehet nga mesazhe JSON dhe jo HTML i ruajtur. Ka timeout dhe pengim të dërgesave të njëkohshme.
- Votimi përdor `vote_in_poll`, me transaksion, numërues atomikë dhe kërkesa të përsëritura pa numërim të dyfishtë për të njëjtin ID shfletuesi.

## Çfarë kërkon qasje online

1. **Para publikimit të UI-së së re të votimit**, ekzekuto `supabase/vote_in_poll.sql` në projektin e duhur Supabase. Pa këtë funksion votimi tregon gabim dhe nuk shkruan numërues të pasigurt.
2. Verifiko politikat RLS për rolet e autentikuara, tabelat e adminit dhe Storage. Migrimi i përgatitur ndalon shkrimin anonim direkt në numërues, por nuk pretendon se auditoi politikat ekzistuese online.
3. Për mbrojtje nga abuzimi masiv në votim nevojitet identitet ose kontroll serveri/rate limit. ID-ja e shfletuesit nuk është provë e një personi unik.
4. Publiko skedarët në repository-n real. Ky folder nuk ka `.git` dhe lidhja e repository-t nuk dihet. Konfigurimi i cron-job-it të jashtëm nuk është ndryshuar.

Varësia Tailwind nga CDN mbetet; ndërtimi i CSS lokale është përmirësim i ardhshëm performance. Nuk u shpikën të dhëna kontakti apo politikë privatësie pa informacionin e pronarit.

## Verifikimi

- 9 teste Python: dimër/verë dhe kufijtë DST; arkiv i dëmtuar; ruajtje atomike; përmbajtje e jashtme; ndërthurje dhe rrjedhë e plotë e robotit me shërbime të simuluara.
- Chrome: desktop, telefon, artikull, kërkim, kategori, faqëzim, tituj me HTML, mungesë rrjeti, votim me RPC të simuluar, chatbot, gabime admini dhe orar DST.
- PostgreSQL lokal në PGlite: migrim i përsëritshëm, 20 vota të ndryshme, retry pa dyfishim, bllokim i shkrimit anonim, opsione të pavlefshme, slider dhe sondazh i planifikuar.
- Nuk u dërguan lajme, vota, abonime apo ndryshime reale në shërbimet online.

Pamjet: `preview-desktop.png`, `preview-mobile.png`, `preview-article.png`.

Referenca të SQL: [Supabase Database Functions](https://supabase.com/docs/guides/database/functions), [PostgreSQL CREATE POLICY](https://www.postgresql.org/docs/current/sql-createpolicy.html).
