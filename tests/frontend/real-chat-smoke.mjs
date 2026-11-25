import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
const base = 'http://127.0.0.1:18080';
const health = await fetch(base+'/api/health').then(r=>r.json());
if (health.data?.env !== 'test') throw Error('Isolated acceptance API required');
const dist = path.resolve('frontend/dist');
const server = http.createServer((req,res)=>{
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname.startsWith('/api/')) {
    const upstream = http.request(base+req.url, {method:req.method,headers:{...req.headers,host:'127.0.0.1:18080'}}, r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res)});
    upstream.on('error',()=>{if(!res.headersSent)res.writeHead(502);res.end()});
    res.on('close',()=>{if(!res.writableEnded)upstream.destroy()});
    req.pipe(upstream);return;
  }
  const asset=path.resolve(dist,'.'+url.pathname);
  if(asset.startsWith(dist+path.sep) && fs.existsSync(asset) && fs.statSync(asset).isFile()){
    res.setHeader('content-type',asset.endsWith('.js')?'text/javascript':asset.endsWith('.css')?'text/css':'application/octet-stream');return res.end(fs.readFileSync(asset));
  }
  res.setHeader('content-type','text/html');res.end(fs.readFileSync(path.join(dist,'index.html')));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
try {
  const screenshot=path.join(os.tmpdir(),'talent-chat-real.png');
  const child=spawn(process.execPath,['tests/frontend/shot.mjs','http://127.0.0.1:'+server.address().port+'/login','1440','900',screenshot,'--theme','light','--evalFile','tests/frontend/real-chat-flow.js'],{stdio:['ignore','pipe','pipe']});
  let output='';child.stdout.on('data',b=>{output+=b;process.stdout.write(b)});child.stderr.on('data',b=>process.stderr.write(b));
  const code=await new Promise(resolve=>child.on('exit',resolve));
  if(code!==0 || !output.includes('"passed":true') || !output.includes('"overflow":false')) throw Error('Real browser acceptance failed');
  console.log('PASS real browser login, chat, history and stop; screenshot='+screenshot);
} finally {server.close();}
