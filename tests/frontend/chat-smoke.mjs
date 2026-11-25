import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
const dist = path.resolve('frontend/dist');
const ts = new Date().toISOString();
const session = {id: 1, title: '测试会话', created_at: ts, updated_at: ts};
const source = {type:'resume', id:1, label:'合成人才 A', path:'/resumes'};
const stored = {id:1, question:'查找有 Python 技能的人才',answer:'合成测试回答',status:'success',source_refs:[source],created_at:ts};
let sends = 0;
let created = false;
const server = http.createServer((req,res) => {
  const url = new URL(req.url, 'http://localhost');
  const json = data => {res.setHeader('content-type','application/json');res.end(JSON.stringify({code:0,message:'success',data}));};
  if (url.pathname === '/api/auth/me') return json({ user:{id:1,username:'fixture',real_name:'测试 HR',department_name:'测试部门',roles:['hr']}, menus:[],permissions:['resume:view'] });
  if (url.pathname === '/api/chat/sessions') {if(req.method==='POST'){created=true;return json(session);}return json(created?[session]:[]);}
  if (url.pathname === '/api/chat/sessions/1') return json({session,conversations:[stored]});
  if (url.pathname === '/api/chat/sessions/1/messages') {
    sends++;
    res.writeHead(200,{'content-type':'text/event-stream'});
    const emit = data => res.write('data: '+JSON.stringify(data)+'\n\n');
    emit({type:'meta',conversation_id:1,session_id:1});emit({type:'delta',text:'合成测试回答'});emit({type:'sources',source_refs:[source]});emit({type:'done',status:'success'});return res.end();
  }
  if (url.pathname.startsWith('/api/')) {res.writeHead(404);return res.end();}
  const asset = path.resolve(dist, '.'+url.pathname);
  if (asset.startsWith(dist+path.sep) && fs.existsSync(asset) && fs.statSync(asset).isFile()) {
    res.setHeader('content-type',asset.endsWith('.js')?'text/javascript':asset.endsWith('.css')?'text/css':'application/octet-stream');return res.end(fs.readFileSync(asset));
  }
  res.setHeader('content-type','text/html');res.end(fs.readFileSync(path.join(dist,'index.html'),'utf8').replace('<head>','<head><script>localStorage.setItem("tl.token","fixture-token")</script>'));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
try {
  const url = 'http://127.0.0.1:'+server.address().port+'/chat';
  const screenshot = path.join(os.tmpdir(),'talent-chat-smoke.png');
  const child=spawn(process.execPath,['tests/frontend/shot.mjs',url,'1440','900',screenshot,'--theme','light','--evalFile','tests/frontend/chat-flow.js'],{stdio:['ignore','pipe','pipe']});
  let output='';child.stdout.on('data',b=>{output+=b;process.stdout.write(b)});child.stderr.on('data',b=>process.stderr.write(b));
  const code=await new Promise(resolve=>child.on('exit',resolve));
  if(code!==0 || !output.includes('"passed":true') || sends!==2) throw new Error('Chat browser test failed: sends='+sends);
  console.log('Browser smoke passed; sends='+sends+'; screenshot='+screenshot);
} finally {server.close();}
