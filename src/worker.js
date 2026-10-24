// Authenticated development API. Static assets remain publicly accessible.
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"}});
const bytes=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-s.length%4)%4)),c=>c.charCodeAt(0));
function decode(s){return JSON.parse(new TextDecoder().decode(bytes(s)))}
async function authenticate(request,env){
 const auth=request.headers.get('authorization')||'';
 if(!auth.startsWith('Bearer '))return null;
 const token=auth.slice(7);const parts=token.split('.');
 if(parts.length!==3)return null;
 let header,payload;try{header=decode(parts[0]);payload=decode(parts[1])}catch{return null}
 if(header.alg!=='RS256'||!header.kid||typeof payload.sub!=='string')return null;
 const now=Math.floor(Date.now()/1000);
 if(payload.iss!==env.CLERK_ISSUER||!Number.isFinite(payload.exp)||payload.exp<=now||!Number.isFinite(payload.iat)||payload.iat>now+60||(payload.nbf!==undefined&&payload.nbf>now+60))return null;
 // Reject tokens issued to unexpected web origins when an authorized party is present.
 if(payload.azp&&!['https://test.bonch.fyi','https://bonch-dev.will-boncher.workers.dev'].includes(payload.azp))return null;
 const jwksUrl=new URL('/.well-known/jwks.json',env.CLERK_ISSUER);
 const jwksResponse=await fetch(jwksUrl.toString());
 if(!jwksResponse.ok)return null;
 const jwks=await jwksResponse.json();
 const jwk=jwks.keys?.find(k=>k.kid===header.kid&&k.kty==='RSA'&&(!k.use||k.use==='sig'));
 if(!jwk)return null;
 const key=await crypto.subtle.importKey('jwk',jwk,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
 const valid=await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,bytes(parts[2]),new TextEncoder().encode(parts[0]+'.'+parts[1]));
 return valid?payload:null;
}
async function handle(request,env){
 const url=new URL(request.url);
 if(!url.pathname.startsWith('/api/'))return env.ASSETS.fetch(request);
 if(request.method==='OPTIONS')return new Response(null,{status:204,headers:{'Access-Control-Allow-Methods':'GET, POST, DELETE, OPTIONS','Access-Control-Allow-Headers':'Authorization, Content-Type','Access-Control-Max-Age':'600'}});
 if(!['GET','POST','DELETE'].includes(request.method))return json({error:'Method not allowed'},405);
 if(request.method==='POST'&&!['/api/admin/notes/import'].includes(url.pathname)&&!/^\/api\/admin\/notes\/(?:0|[1-9][0-9]{0,3})$/.test(url.pathname))return json({error:'Method not allowed'},405);
 if(request.method==='DELETE'&&!/^\/api\/admin\/notes\/(?:0|[1-9][0-9]{0,3})$/.test(url.pathname))return json({error:'Method not allowed'},405);
 if(request.method==='GET'&&url.pathname==='/api/admin/notes/import')return json({error:'Method not allowed'},405);
 if(request.method==='GET'&&url.pathname==='/api/health')return json({ok:true,service:'bonch-dev',databaseConfigured:Boolean(env.DB)});
 let identity;try{identity=await authenticate(request,env)}catch(e){console.error('Token validation failed',e);return json({error:'Authentication unavailable'},503)}
 if(!identity)return json({error:'Sign in required'},401);
 if(identity.sub!==env.ADMIN_CLERK_USER_ID)return json({error:'Administrator access required'},403);
 if(request.method==='GET'&&url.pathname==='/api/admin/me')return json({admin:true,userId:identity.sub});
 const match=url.pathname.match(/^\/api\/admin\/notes\/(0|[1-9][0-9]{0,3})$/);
 if(match&&(request.method==='POST'||request.method==='DELETE')){
  const key=match[1];
  if(Number(key)>43)return json({error:'Unknown trip'},404);
  try{
   if(request.method==='DELETE'){
    const result=await env.DB.prepare('DELETE FROM trip_notes WHERE trip_key=?').bind(key).run();
    return json({deleted:true,changed:result.meta?.changes||0});
   }
   if(!(request.headers.get('content-type')||'').toLowerCase().startsWith('application/json'))return json({error:'JSON required'},415);
   const raw=await request.text();if(raw.length>10000)return json({error:'Note too long'},413);
   let data;try{data=JSON.parse(raw)}catch{return json({error:'Invalid JSON'},400)}
   if(typeof data.note!=='string'||data.note.length>5000||!data.note.trim())return json({error:'Note must contain 1–5000 characters'},400);
   await env.DB.prepare("INSERT INTO trip_notes(trip_key,note,updated_at) VALUES(?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now')) ON CONFLICT(trip_key) DO UPDATE SET note=excluded.note,updated_at=excluded.updated_at").bind(key,data.note).run();
   return json({saved:true,trip_key:key});
  }catch(e){console.error('Note edit failed',e);return json({error:'Database operation failed'},503)}
 }

 if(request.method==='POST'&&url.pathname==='/api/admin/notes/import'){
  const type=request.headers.get('content-type')||'';
  if(!type.toLowerCase().startsWith('application/json'))return json({error:'JSON required'},415);
  const size=Number(request.headers.get('content-length')||0);
  if(size>100000)return json({error:'Import too large'},413);
  let body;try{const raw=await request.text();if(raw.length>100000)return json({error:'Import too large'},413);body=JSON.parse(raw)}catch{return json({error:'Invalid JSON'},400)}
  if(!Array.isArray(body.notes)||body.notes.length>200)return json({error:'Expected up to 200 notes'},400);
  const keys=new Set();
  for(const row of body.notes){
   if(!row||typeof row.trip_key!=='string'||!/^(0|[1-9][0-9]{0,3})$/.test(row.trip_key)||Number(row.trip_key)>43||typeof row.note!=='string'||row.note.length>5000||keys.has(row.trip_key))return json({error:'Invalid or duplicate trip key/note'},400);
   keys.add(row.trip_key);
  }
  try{
   if(body.notes.length){
    const statements=body.notes.map(row=>env.DB.prepare("INSERT INTO trip_notes (trip_key,note,updated_at) VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now')) ON CONFLICT(trip_key) DO UPDATE SET note=excluded.note,updated_at=excluded.updated_at").bind(row.trip_key,row.note));
    await env.DB.batch(statements);
   }
   return json({imported:body.notes.length});
  }catch(e){console.error('Private import failed',e);return json({error:'Import failed'},503)}
 }
 if(request.method==='GET'&&url.pathname==='/api/admin/notes'){
  try{
   const result=await env.DB.prepare('SELECT trip_key, note, updated_at FROM trip_notes ORDER BY trip_key').all();
   return json({notes:result.results||[]});
  }catch(e){console.error('D1 notes query failed',e);return json({error:'Database not initialized'},503)}
 }
 return json({error:'Not found'},404);
}
const allowedOrigins=new Set(['https://test.bonch.fyi','https://bonch-dev.will-boncher.workers.dev']);
export default {async fetch(request,env){
 const origin=request.headers.get('Origin');
 const isApi=new URL(request.url).pathname.startsWith('/api/');
 if(isApi&&request.method==='OPTIONS'&&!allowedOrigins.has(origin))return new Response(null,{status:403});
 const response=await handle(request,env);
 if(!isApi||!allowedOrigins.has(origin))return response;
 const headers=new Headers(response.headers);
 headers.set('Access-Control-Allow-Origin',origin);
 headers.set('Vary','Origin');
 return new Response(response.body,{status:response.status,statusText:response.statusText,headers});
}};