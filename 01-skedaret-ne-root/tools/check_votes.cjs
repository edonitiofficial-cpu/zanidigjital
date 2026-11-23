const { PGlite } = require('@electric-sql/pglite');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
    const db = new PGlite();
    try {
        await db.exec(`create role anon; create role authenticated;
            create table public.polls(id uuid primary key, question text, status text, start_date timestamptz, total_votes integer default 0);
            create table public.poll_options(id uuid primary key, poll_id uuid references polls(id), option_text text, votes integer default 0);
            grant usage on schema public to anon, authenticated;
            grant select, update on public.polls, public.poll_options to anon;
            create policy legacy_public on public.polls for all to anon using (true) with check (true);
            create policy legacy_public on public.poll_options for all to anon using (true) with check (true);`);
        const migration = fs.readFileSync(path.join(__dirname, '../supabase/vote_in_poll.sql'), 'utf8');
        await db.exec(migration); await db.exec(migration); // rerunnable
        const poll='00000000-0000-0000-0000-000000000001';
        const option='00000000-0000-0000-0000-000000000002';
        await db.query("insert into polls(id,question,status,start_date) values($1,'Test','active',now()-interval '1 day')",[poll]);
        await db.query("insert into poll_options(id,poll_id,option_text) values($1,$2,'Po')",[option,poll]);
        await db.exec('set role anon');
        const voter=i=>`10000000-0000-0000-0000-${String(i).padStart(12,'0')}`;
        await Promise.all(Array.from({length:20},(_,i)=>db.query('select public.vote_in_poll($1,$2,$3,1)',[poll,option,voter(i)])));
        await db.query('select public.vote_in_poll($1,$2,$3,1)',[poll,option,voter(0)]);
        assert.equal((await db.query('select total_votes from polls')).rows[0].total_votes,20);
        assert.equal((await db.query('select votes from poll_options')).rows[0].votes,20);
        await db.query('update polls set total_votes=999 where id=$1',[poll]);
        assert.equal((await db.query('select total_votes from polls')).rows[0].total_votes,20);
        await assert.rejects(db.query('select public.vote_in_poll($1,$2,$3,99)',[poll,option,voter(30)]));
        await assert.rejects(db.query('select public.vote_in_poll($1,$2,$3,1)',[poll,voter(99),voter(31)]));
        await assert.rejects(db.query('select * from public.poll_vote_receipts'));
        await db.exec('reset role');
        await db.query("update poll_options set option_text='SLIDER_SUM',votes=0 where id=$1",[option]);
        await db.query('update polls set total_votes=0 where id=$1',[poll]);
        await db.exec('set role anon');
        await db.query('select public.vote_in_poll($1,$2,$3,75)',[poll,option,voter(40)]);
        await db.query('select public.vote_in_poll($1,$2,$3,25)',[poll,option,voter(41)]);
        assert.equal((await db.query('select votes from poll_options')).rows[0].votes,100);
        assert.equal((await db.query('select total_votes from polls')).rows[0].total_votes,2);
        await assert.rejects(db.query('select public.vote_in_poll($1,$2,$3,101)',[poll,option,voter(42)]));
        await db.exec('reset role');
        await db.query("update polls set start_date=now()+interval '1 day' where id=$1",[poll]);
        await db.exec('set role anon');
        await assert.rejects(db.query('select public.vote_in_poll($1,$2,$3,10)',[poll,option,voter(43)]));
        console.log('SQL: idempotent migration, 20 distinct votes, retry deduplication, atomic counters, anonymous write denial, invalid options, slider and scheduled-poll checks OK.');
    } finally { await db.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
