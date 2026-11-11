# Zani Digjital

Portal statik me robot Python. Nisjet periodike kontrollohen nga cron-job i jashtëm, i cili thërret `repository_dispatch` (`ndiz_motorin`) ose `workflow_dispatch` të GitHub Actions.

Ndryshimet dhe kufijtë e verifikimit janë te [CHANGES.md](CHANGES.md); auditi fillestar te [AUDIT.md](AUDIT.md).

Portali nuk kërkon redaksi ditore: roboti klasifikon lajmet, grupon përsëritjet, etiketon komunat dhe rendit automatikisht pesë lajmet kryesore. Rregullat janë te `news_policy.py` dhe `municipalities.py`. Chatbot-i publik është hequr.

Admin → **Shëndeti i robotit** lexon `bot-status.json`, i cili përditësohet nga roboti dhe ruhet nga workflow. Para nisjes së parë të versionit të ri shfaqet “Ende nuk ka raport”. Skedari nuk përmban çelësa ose të dhëna private; në hosting statik është publik.

Lajmet sipas komunës përdorin `?komuna=Pejë` dhe mund të kombinohen me `kategoria`/`q`. Ndryshimet e lajmeve manuale shfaqen pas ekzekutimit të robotit, sepse ballina nuk pret më Supabase për t'i ngarkuar.

## Zhvillimi dhe kontrolli

Kërkohen Python 3.11+, Node.js dhe Chrome për testet e shfletuesit.

```sh
pip install -r requirements.txt
python -m unittest discover -p 'test_*.py'
npm ci
npm run test:sql
npm run test:ui
```

Testet nuk përdorin sekrete dhe nuk shkruajnë në shërbimet reale. Testet UI përdorin përgjigje të simuluara për databazën/AI; testi SQL krijon një PostgreSQL të përkohshëm në PGlite.

Për pamje lokale:

```sh
python -m http.server 8000
```

Hape `http://localhost:8000`. Kjo pamje përdor leximet publike të Supabase; mos voto apo dërgo formularë realë për provë.

Për rigjenerim vetëm nga arkivi lokal, pa robot dhe pa publikim:

```sh
python tools/prepare_site.py
```

## Publikimi

1. Apliko `supabase/vote_in_poll.sql` në projektin e duhur Supabase **para** UI-së së re. Kontrollo veçmas politikat e adminit dhe Storage. SQL është testuar lokalisht, por nuk është zbatuar online nga kjo kopje.
2. Vendos skedarët e përditësuar dhe asetet e reja në repository-n ekzistues; përfshi artikujt e rigjeneruar, `news-index.json`, `robots.txt`, RSS dhe sitemap. Mos publiko pamjet `preview-*.png`, `audit-*.png` ose mjetet e përkohshme.
3. Ruaj sekretet ekzistuese `GROQ_API_KEY`, çelësat rezervë opsionalë dhe `FACEBOOK_PAGE_TOKEN` në GitHub Secrets. Mos vendos tokenë në HTML ose në Git.
4. Ruaj endpoint-in/autorizimin e cron-job-it të jashtëm. Workflow nuk ka më cron të brendshëm; emri `ndiz_motorin` nuk ndryshon.
5. Provo një nisje të kontrolluar dhe kontrollo log-et, publikimin e faqes dhe Facebook. Robotin real mos e përdor për testim lokal: përgatit lajme dhe workflow mund t'i publikojë automatikisht.

Publikimi i Git ndodh një herë, në workflow. Facebook merr radhën e përgatitur në folderin e përkohshëm të runner-it dhe ekzekutohet vetëm pas push-it të suksesshëm. Token-i, lejet dhe versioni i API-së Facebook duhet të kontrollohen në projektin real; këtu nuk u dërgua postim prove.

Ora e Kosovës përdor `Europe/Belgrade`. `published_at` ruan offset-in për lajmet e reja; orët historike pa zonë nuk zhvendosen në masë.
