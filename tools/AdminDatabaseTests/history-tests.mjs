import assert from 'node:assert/strict';
export async function historyTests(db) {
 let n=0;const check=(value,message)=>{assert.ok(value,message);n++;};
 const q=async(sql,args=[]) => (await db.query(sql,args)).rows;
 const a='41000000-0000-0000-0000-000000000001',b='41000000-0000-0000-0000-000000000002',c='41000000-0000-0000-0000-000000000003';
 const instance='42000000-0000-0000-0000-000000000001';
 await db.exec('reset role');
 for(const [id,name] of [[a,'historya'],[b,'historyb'],[c,'historyc']]){
  await q(`insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values($1,$2,now(),$3::jsonb)`,[id,name+'@example.test',JSON.stringify({nickname:name,display_name:name})]);
  await q('insert into auth.sessions(id,user_id) values($1,$1)',[id]);
  await q('insert into paw_private.launcher_sessions values($1,$1,now(),$2,false)',[id,instance]);
 }
 const login=async(id,inst=instance)=>{await db.exec('reset role');await q("select set_config('request.jwt.claims',$1,false),set_config('request.headers',$2,false)",[JSON.stringify({sub:id,session_id:id}),JSON.stringify({'x-paw-launcher':inst})]);await db.exec('set role authenticated');};
 const rpc=async(name,args=[]) => (await q(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) result`,args))[0].result;
 await login(a);check((await rpc('paw_admin_resources')).status==='admin_required','non-admin resource denial');
 check((await rpc('paw_read_message_page',[b,null,null])).status==='friend_required','private history guard');
 await db.exec('reset role');
 for(const target of [b,c])await q('insert into public.paw_friendships(low_id,high_id,requester,accepted) values(least($1::uuid,$2::uuid),greatest($1::uuid,$2::uuid),$1,true)',[a,target]);
 // Bulk fixtures only: skip the production trigger while seeding 9,999 old rows.
 await db.exec('alter table public.paw_messages disable trigger paw_message_history_retention');
 await q(`insert into public.paw_messages(sender_id,recipient_id,message_id,body,kind,created_at)
 select case when g%2=0 then $1::uuid else $2::uuid end,case when g%2=0 then $2::uuid else $1::uuid end,
 gen_random_uuid(),'history '||g,'text',now()-interval '2 days' from generate_series(1,9999) g`,[a,b]);
 const oldest=(await q('select * from public.paw_messages where least(sender_id,recipient_id)=$1 and greatest(sender_id,recipient_id)=$2 order by ordinal limit 2',[a,b]));
 await q(`insert into paw_private.social_offers(id,sender_id,recipient_id,kind,configuration,state,expires_at,storage_cleaned)
 values($1,$2,$3,'config','fixture','pending',now()+interval '10 minutes',true)`,[oldest[0].message_id,oldest[0].sender_id,oldest[0].recipient_id]);
 await q(`insert into paw_private.social_offers(id,sender_id,recipient_id,kind,file_name,file_size,sha256,state,storage_cleaned)
 values($1,$2,$3,'save','test.rsg',16,repeat('a',64),'accepted',false)`,[oldest[1].message_id,oldest[1].sender_id,oldest[1].recipient_id]);
 await db.exec('alter table public.paw_messages enable trigger paw_message_history_retention');
 await login(a);
 const sent=await rpc('paw_send_message',[b,'43000000-0000-0000-0000-000000000001','threshold','text']);
 check(sent.status==='ok','10,000th message is accepted');
 await db.exec('reset role');
 check(Number((await q('select count(*) n from public.paw_messages where least(sender_id,recipient_id)=$1 and greatest(sender_id,recipient_id)=$2',[a,b]))[0].n)===5000,'shared dialog retains 5,000');
 check((await q('select 1 from public.paw_messages where message_id=$1',[oldest[0].message_id])).length===1,'active offer message protected');
 check((await q('select 1 from public.paw_messages where message_id=$1',[oldest[1].message_id])).length===0,'completed save message retired');
 check((await q('select 1 from paw_private.social_offers where id=$1',[oldest[1].message_id])).length===1,'save metadata retained until physical cleanup');
 await q('select public.paw_transfer_cleaned($1::text[])',[[oldest[1].sender_id+'/'+oldest[1].message_id+'.rsg']]);
 check((await q('select 1 from paw_private.social_offers where id=$1',[oldest[1].message_id])).length===0,'cleaned orphan metadata removed');
 await login(a);
 const duplicate=await rpc('paw_send_message',[b,'43000000-0000-0000-0000-000000000001','threshold','text']);
 check(duplicate.message.ordinal===sent.message.ordinal,'retry after trim remains idempotent');
 let page=await rpc('paw_read_message_page',[b,null,null]);
 check(page.trimmed&&page.history_revision===1&&page.more&&page.messages.length===50,'first page trim metadata');
 const ids=new Set();let pages=0,activeCard=false;
 do{
  for(const m of page.messages){check(!ids.has(m.ordinal),'same timestamp pages never duplicate');ids.add(m.ordinal);}
  activeCard||=page.offers.some(o=>o.id===oldest[0].message_id);
  pages++;if(!page.more)break;
  const cursor=page.messages[0];page=await rpc('paw_read_message_page',[b,cursor.created_at,cursor.ordinal]);
 }while(pages<105);
 check(ids.size===5000&&pages===100,'full retained history reachable across identical timestamps');
 check(activeCard,'old active card accompanies its history page');
 const states=await rpc('paw_read_offer_states',[b,[oldest[0].message_id]]);
 check(states.status==='ok'&&states.offers.length===1&&states.offers[0].id===oldest[0].message_id,'refresh protected old offer without downloading text');
 check((await rpc('paw_read_offer_states',[b,[]])).status==='invalid_offer','bounded old offer refresh');
 check((await rpc('paw_read_offer_states',[c,[oldest[0].message_id]])).offers.length===0,'offer ids cannot cross dialogs');
 await login(b);check((await rpc('paw_read_message_page',[a,null,null])).history_revision===1,'both participants share deletion revision');
 check((await rpc('paw_read_message_page',[a,new Date().toISOString(),null])).status==='invalid_message','reject incomplete cursor');
 await login(a,'42000000-0000-0000-0000-000000000099');check((await rpc('paw_read_message_page',[b,null,null])).status==='session_expired','stale launcher cannot read cached-session page');
 await db.exec('reset role');
 await q('update public.paw_profiles set admin_level=1 where id=$1',[a]);
 await login(a);const resources=await rpc('paw_admin_resources');
 check(resources.status==='ok'&&resources.database_bytes>0&&resources.messages_count>=5000,'admin gets real sizes');
 check(resources.provider_metrics.length===0,'unconnected provider usage is not fabricated zero');
 check(resources.dialog_limit===10000&&resources.cleanup_batch===5000&&resources.removed_messages===5000,'admin retention policy / deletion count');
 let denied=false;try{await q('select * from paw_private.resource_usage');}catch{denied=true;}check(denied,'even client admin cannot directly access provider table');
 await db.exec('reset role');
 await db.exec('alter table public.paw_messages disable trigger paw_message_history_retention');
 await q(`insert into public.paw_messages(sender_id,recipient_id,message_id,body,kind,created_at)
 select $1,$2,gen_random_uuid(),'other dialog','text',now()-interval '1 day' from generate_series(1,8000)`,[a,c]);
 await db.exec('alter table public.paw_messages enable trigger paw_message_history_retention');
 await login(a);check((await rpc('paw_send_message',[c,'43000000-0000-0000-0000-000000000002','not a lifetime quota','text'])).status==='ok','over 10k sent globally does not block another dialog');
 await db.exec('reset role');
 check(Number((await q('select count(*) n from public.paw_messages where least(sender_id,recipient_id)=$1 and greatest(sender_id,recipient_id)=$2',[a,c]))[0].n)===8001,'separate dialog not trimmed early');
 // A later cleanup must advance the shared revision and also retire a formerly active card.
 await q("update paw_private.social_offers set expires_at=now()-interval '1 minute' where id=$1",[oldest[0].message_id]);
 await db.exec('alter table public.paw_messages disable trigger paw_message_history_retention');
 await q(`insert into public.paw_messages(sender_id,recipient_id,message_id,body,kind,created_at)
 select $1,$2,gen_random_uuid(),'second cycle','text',now()-interval '1 day' from generate_series(1,4999)`,[a,b]);
 await db.exec('alter table public.paw_messages enable trigger paw_message_history_retention');
 await login(a);
 check((await rpc('paw_send_message',[b,'43000000-0000-0000-0000-000000000003','second threshold','text'])).status==='ok','second retention cycle accepts send');
 page=await rpc('paw_read_message_page',[b,null,null]);
 check(page.history_revision===2&&page.trimmed,'retention revision advances');
 await db.exec('reset role');
 check(Number((await q('select count(*) n from public.paw_messages where least(sender_id,recipient_id)=$1 and greatest(sender_id,recipient_id)=$2',[a,b]))[0].n)===5000,'second cycle is still per-dialog');
 check((await q('select 1 from paw_private.social_offers where id=$1',[oldest[0].message_id])).length===0,'expired config metadata retires with old card');
 for(const signature of ['public.paw_read_message_page(uuid,timestamptz,bigint)','public.paw_read_offer_states(uuid,uuid[])','public.paw_admin_resources()']){
  check(!(await q("select has_function_privilege('anon',$1,'EXECUTE') allowed",[signature]))[0].allowed,'anonymous denied '+signature);
 }
 await login(a);check((await rpc('paw_admin_resources')).removed_messages===10000,'resources counts both cleanup batches');
 await db.exec('reset role');
 console.log('HISTORY / RESOURCES DATABASE CHECKS:',n,'PASS; isolated fake rows only');
 return n;
}
