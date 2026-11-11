# Audit — Zani Digjital

> Ky është auditi fillestar. Shumë gjetje më poshtë janë adresuar. Gjendja pas ndryshimeve dhe çfarë mbetet për publikim përshkruhen te [CHANGES.md](CHANGES.md). Nisjet periodike vijnë nga cron-job i jashtëm, sipas sqarimit të pronarit.

Data: 10 nëntor 2026. U kontrolluan kodi lokal, ballina online në Chrome desktop (1440 px) dhe telefon (390 px), si dhe një artikull online. Nuk u ndryshua databaza dhe nuk u publikua në Facebook apo në hosting.

## Ndreqja e implementuar: ora

- `bot.py` përdorte `datetime.now() + timedelta(hours=2)`. Kjo supozonte server UTC dhe kohë verore gjatë gjithë vitit.
- `news_time.py` përdor `Europe/Belgrade`, zonën IANA që mbulon Kosovën, me kalim automatik verë/dimër.
- Lajmet manuale ruajnë tani offset-in e plotë të `created_at` nga Supabase dhe konvertohen në orën lokale. Më parë offset-i hiqej para formatimit.
- Ballina i formaton lajmet manuale në të njëjtën zonë, pavarësisht ku ndodhet lexuesi.
- `tzdata` u shtua te varësitë për Windows; workflow instalon `requirements.txt`.
- Datat historike në JSON dhe HTML nuk janë zhvendosur: nuk përmbajnë offset dhe nuk ka provë të mjaftueshme për t'i korrigjuar në masë. Ndreqja zbatohet për lajmet e reja dhe rigjenerimin e lajmeve manuale.
- Verifikim: 3 teste Python me disa raste për dimër/verë, offset eksplicit dhe dy kalimet DST; 4 raste të formatuesit real JavaScript; sintaksa e Python dhe JavaScript në tri faqet kryesore kaloi.

## Si funksionon roboti

Workflow `.github/workflows/update.yml` ka cron `17,47 * * * *`: dy nisje në orë. Ka edhe `repository_dispatch` dhe nisje manuale; një shërbim i jashtëm mund të shkaktojë nisje shtesë, por kjo nuk provohet nga skedarët lokalë. Kufiri është 5 lajme për ekzekutim, gjithsej për të gjitha burimet.

Burimet lexohen me radhë: Telegrafi, Indeksonline, Gazeta Express, Klan Kosova. Lajmet filtrohen për lidhje të lexuara, ngjashmëri titulli, fotografi dhe tekst së paku 200 karaktere. AI zgjedh kategori dhe hashtags; kodi i tanishëm nuk e rishkruan artikullin. Teksti pastrohet dhe publikohet bashkë me HTML, JSON, RSS dhe sitemap. Deri dy lajme për ekzekutim mund të shkojnë në Facebook.

## Gjetjet sipas përparësisë

### Të larta

1. **Votat nuk ruhen në mënyrë atomike.** `submitOptionVote` dhe `submitSliderVote` shkruajnë numrin e vjetër + 1 nga shfletuesi. Dy votues mund të mbishkruajnë njëri-tjetrin. `localStorage` nuk ndalon votimin e përsëritur nga pajisje apo sesione tjera. Duhet funksion serveri/RPC me transaksion dhe kontroll kundër abuzimit.
2. **HTML i jashtëm futet pa escaping.** Tituj, tekste dhe fusha Supabase futen në template/`innerHTML`. Duhet escaping për tekst/atribute dhe kontroll i protokollit të URL-ve; nëse lejohet HTML redaktorial, duhet sanitizim. Nuk u provua sulm në faqen publike.
3. **Autorizimi i databazës nuk mund të vërtetohet nga ky projekt.** Admini kontrollon sesionin në shfletues; mbrojtja reale duhet të jetë në politikat RLS dhe Storage të Supabase. Skedarët e politikave mungojnë. Çelësi `sb_publishable` në frontend është çelës publik, jo provë e rrjedhjes së sekretit. Duhet kontroll i roleve dhe politikave në backend para përfundimit të auditit të sigurisë.
4. **Roboti mund të dominohet nga burimi i parë.** Pasi gjen 5 lajme, ndalet pa lexuar burimet tjera. Në 150 lajmet më të reja të kopjes lokale: 114 Telegrafi, 36 Indeksonline, asnjë nga dy të tjerat. Propozim: mblidh kandidatët nga të katër burimet, renditi sipas datës/rëndësisë dhe zbato shpërndarje të arsyeshme.
5. **Gabimet mund të duken si sukses.** Ka `except: pass`, `catch {}` dhe ruajtje admini pa kontroll të `error`. `load_news` kthen listë bosh edhe kur JSON është i dëmtuar, me rrezik zëvendësimi të arkivit gjatë ruajtjes pasuese. Duhet ndalim në gabim të databazës, shkrim atomik dhe logim i qartë.

### Mesatare

6. **Publikimi Git bëhet në dy vende.** `bot.py` bën commit/pull/push dhe workflow e përsërit. `os.system` nuk ndërpret punën në dështim. Mbaje publikimin në workflow dhe ndaje dështimin e publikimit nga radha e Facebook.
7. **Ballina kufizon arkivin.** `ballina.json` ka vetëm 150 lajme; kategoritë përdorin po këtë listë. “LEXO MË SHUMË” hap vetëm kategorinë Lajme dhe nuk vazhdon listën e të gjitha lajmeve. Duhet faqëzim sipas kategorisë dhe arkiv i kërkueshëm.
8. **Fallback shumë i madh.** `lajmet.json` lokal është rreth 19.6 MB dhe ka 7000 artikuj. Ngarkohet i tëri kur dështon ballina, dhe faqja e vjetër `artikulli.html` e përdor për një artikull. Ndaje në faqe/indekse më të vogla.
9. **Slug-et nuk janë konsistente.** Python përdor `.replace(r'-+', '-')`, që nuk i bashkon vizat me regex; JavaScript përdor regex. Për lajme manuale kjo mund të krijojë lidhje të ndryshme. Duhet algoritëm i përbashkët dhe menaxhim i përplasjeve pa prishur lidhjet historike.
10. **Mungon atribuimi i dukshëm.** `link_origjinal` ruhet në JSON, por faqja e gjeneruar nuk e shfaq burimin. Shto emrin/lidhjen e burimit, kohën e publikimit dhe shënim për përpunimin automatik. Mos i hiq citimet e burimit me filtra të gjerë që mund të fshijnë edhe paragrafë me informacion.
11. **Service worker nuk krijon cache.** `sw.js` kërkon cache kur rrjeti dështon, por nuk ruan asnjë përgjigje. Premtimi i përvojës offline nuk mbështetet nga ky implementim.
12. **SEO varet shumë nga JavaScript në ballinë.** Artikujt kanë HTML statik, por ballina i merr lajmet vetëm me JS. Mungojnë structured data `NewsArticle`, `pubDate`/`guid` në RSS dhe sitemap për pjesën më të madhe të arkivit (kufizohet në 1000). Lajmet manuale nuk përfshihen në të njëjtin indeks si automatiket.

## UI/UX — vëzhgime nga shfletuesi

Baza është e pastër: logo e qartë, ngjyra diskrete, kategori me dallim vizual dhe artikull i lexueshëm në telefon. Në dy madhësitë e testuara, ballina ngarkoi 5 lajmet kryesore pa gabime JavaScript dhe pa overflow horizontal të dokumentit. Kjo nuk vërteton çdo ndërveprim apo çdo pajisje.

- **Desktop: hapësirë e tepërt anash.** Dy sidebar-e bosh rezervojnë nga 300 px edhe kur nuk ka reklama. Në 1440 px lajmet shtrydhen në mes dhe titujt bëhen shumë të gjatë vertikalisht. Shfaqi anësoret vetëm kur ka baner; syno përmbajtje 1100–1200 px kur mungojnë reklamat.
- **Kartat kryesore të vogla kanë tituj të ngjeshur.** Katër kartat anësore në grid me fotografi duhet të kenë tituj të kufizuar, kontrast të qëndrueshëm dhe lartësi të mjaftueshme; në desktopin e testuar teksti afrohet shumë me fundin e kartës.
- **Telefon: pesë lajme kryesore zënë shumë scroll.** Mbaj një kryesor të madh dhe katër tjerat si rreshta kompaktë me miniaturë; kështu “Të fundit” arrin më shpejt në ekran.
- **Navigimi mobil fsheh kategoritë në scroll horizontal.** Duhet tregues i qartë që lista vazhdon ose menu kategorish me buton të emërtuar.
- **Kërkimi duhet të jetë i dukshëm.** Shto fushë kërkimi në header/listë; asistenti AI është rrugë shtesë, por kërkimi i zakonshëm duhet të arrihet drejtpërdrejt.
- **FLASH lëviz vazhdimisht.** Shto pause të arritshme me tastierë dhe respekto `prefers-reduced-motion`. Edhe animacionet tjera duhen përshtatur.
- **Zoom është i bllokuar.** Hiq `maximum-scale=1.0, user-scalable=no` nga faqet dhe template-i; është pengesë për lexuesit me shikim të dobët.
- **Sekcionet bosh zënë hapësirë.** Puna dhe sondazhi pa përmbajtje mund të fshihen ose kompaktohen. Mungesa e sondazhit aktiv nuk duhet të mbetet pafund “Duke ngarkuar”.
- **Fotografitë:** cakto përmasa/aspect ratio, alt të përshtatshëm dhe fallback. Kartat e ballinës nuk kanë alt. Pamjet full-page u morën pa scroll në çdo imazh lazy; boshllëqet e imazheve në ato pamje nuk janë provë se fotografitë dështojnë.
- **Besueshmëria:** shto Rreth nesh, Kontakt, Privatësi dhe politikë korrigjimesh, si dhe identitet të qartë redaktorial. Abonimi mbledh email pa shpjegim pranë formularit se si përdoret.

## Hapat e propozuar

1. Publiko ndreqjen e orës nga kjo kopje në repository/hosting. Ky folder nuk ka `.git`, prandaj nuk mund të bëhet commit/push nga këtu pa lidhjen e repository-t.
2. Kontrollo RLS dhe rregullo votimin, escaping-un dhe raportimin e gabimeve.
3. Përmirëso shpërndarjen e burimeve dhe vendos orarin e dëshiruar. Cron-i nuk u ndryshua pa verifikuar nisjet e jashtme.
4. Rregullo hapësirën desktop, kartat mobile, kërkimin dhe faqëzimin; pastaj bëj matje performance dhe kontroll të plotë me tastierë.

Referencë teknike për DST: https://docs.python.org/3/library/zoneinfo.html
