const {PGlite} = require('@electric-sql/pglite');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async()=>{
    const db = new PGlite();
    try {
        const admin='11111111-1111-4111-8111-111111111111', user='22222222-2222-4222-8222-222222222222';
        await db.exec(`create role anon; create role authenticated;
            create schema auth; create schema storage;
            create table auth.users(id uuid primary key);
            create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('test.uid',true),'')::uuid$$;
            grant usage on schema public,storage,auth to anon,authenticated;
            insert into auth.users values ('${admin}'),('${user}');
            create table storage.objects(id integer primary key,bucket_id text);
            alter table storage.objects enable row level security;
            grant all on storage.objects to anon,authenticated;
            create policy old_storage on storage.objects for all to anon,authenticated using (true) with check (true);`);
        const tables=['manual_news','jobs','banners','polls','poll_options','newsletter_subscribers'];
        for (const table of tables) await db.exec(`create table public.${table}(id integer primary key,body text); grant all on public.${table} to anon,authenticated; create policy old_open on public.${table} for all to anon,authenticated using (true) with check (true); insert into public.${table} values(1,'existing');`);
        const migration=fs.readFileSync(path.join(__dirname,'../supabase/admin_access.sql'),'utf8');
        await db.exec(migration);await db.exec(migration);
        await db.exec(`insert into public.portal_admins(user_id) values('${admin}');`);
        async function as(role,uid,fn){
            await db.exec(`set role ${role}; set test.uid='${uid}';`);
            try {await fn();}finally{await db.exec('reset role;');}
        }
        for(const [role,uid] of [['anon',''],['authenticated',user]]) await as(role,uid,async()=>{
            assert.equal((await db.query('select public.is_portal_admin() as allowed')).rows[0].allowed,false);
            for(const table of tables){
                if(table!=='newsletter_subscribers') await assert.rejects(db.exec(`insert into public.${table} values(2,'blocked')`));
                assert.equal((await db.query(`update public.${table} set body='changed' where id=1 returning id`)).rows.length,0);
                assert.equal((await db.query(`delete from public.${table} where id=1 returning id`)).rows.length,0);
            }
            await assert.rejects(db.exec(`insert into public.portal_admins(user_id) values('${user}')`));
            assert.equal((await db.query('select * from public.newsletter_subscribers')).rows.length,0);
            await assert.rejects(db.exec("insert into storage.objects values(1,'media')"));
        });
        await as('anon','',async()=>{
            await db.exec("insert into public.newsletter_subscribers values(2,'new@example.com')");
            assert.equal((await db.query('select * from public.manual_news')).rows.length,1);
            // Unrelated Storage buckets retain their previous permissions.
            await db.exec("insert into storage.objects values(2,'unrelated')");
        });
        await as('authenticated',admin,async()=>{
            assert.equal((await db.query('select public.is_portal_admin() as allowed')).rows[0].allowed,true);
            for(const table of tables){
                await db.exec(`insert into public.${table} values(3,'admin')`);
                assert.equal((await db.query(`update public.${table} set body='edited' where id=3 returning id`)).rows.length,1);
                assert.equal((await db.query(`delete from public.${table} where id=3 returning id`)).rows.length,1);
            }
            await db.exec("insert into storage.objects values(3,'media')");
            assert.equal((await db.query("delete from storage.objects where id=3 returning id")).rows.length,1);
            await assert.rejects(db.exec(`insert into public.portal_admins(user_id) values('${user}')`));
        });
        await db.exec(`delete from public.portal_admins where user_id='${admin}';`);
        await as('authenticated',admin,async()=>assert.equal((await db.query('select public.is_portal_admin() as allowed')).rows[0].allowed,false));
        console.log('Admin SQL: repeatable migration, anonymous/member denial despite legacy policies, trusted admin CRUD, private subscribers, public signup, media guards, privilege escalation denial and revocation OK.');
    } finally {await db.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
