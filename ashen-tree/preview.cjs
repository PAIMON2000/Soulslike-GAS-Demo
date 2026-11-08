const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, 'dist');
http.createServer((req,res)=>{
  const name = new URL(req.url,'http://localhost').pathname;
  const files = {'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css','/v2.js':'v2.js','/model.js':'model.js','/engine.js':'engine.js'};
  const file = files[name];
  if(!file){res.writeHead(404);return res.end('Not found');}
  res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':'text/html; charset=utf-8');
  fs.createReadStream(path.join(root,file)).pipe(res);
}).listen(4173,'127.0.0.1',()=>console.log('http://127.0.0.1:4173'));
