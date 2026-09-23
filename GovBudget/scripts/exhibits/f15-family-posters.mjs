#!/usr/bin/env node
// Reproducible stills from the exact same schematic used by the interactive scene.
// Run from the repository root: node scripts/exhibits/f15-family-posters.mjs
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const root=resolve(fileURLToPath(new URL('../..',import.meta.url)));
const publicDir=resolve(root,'site/public');
const require=createRequire(resolve(root,'site/package.json'));
const { chromium }=require('playwright');
const mime={'.js':'text/javascript','.mjs':'text/javascript','.png':'image/png'};
const server=createServer(async(req,res)=>{
  try{
    if(req.url==='/'){
      res.setHeader('Content-Type','text/html');
      res.end('<!doctype html><html><head><style>*{box-sizing:border-box}body{margin:0;background:transparent}f15-family-scene{display:block;width:1440px;height:500px}canvas{display:block}button{display:none}</style></head><body><f15-family-scene variant="EX" blueprint="true"></f15-family-scene><script type="module" src="/exhibits/f15-family/viewer.js"></script></body></html>');return;
    }
    const path=resolve(publicDir,`.${new URL(req.url,'http://localhost').pathname}`);
    if(!path.startsWith(`${publicDir}/`)){res.writeHead(403);res.end();return;}
    res.setHeader('Content-Type',mime[extname(path)]||'application/octet-stream');res.end(await readFile(path));
  }catch{res.writeHead(404);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({headless:true,args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
  const page=await browser.newPage({viewport:{width:1440,height:500},deviceScaleFactor:1});
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.waitForSelector('f15-family-scene[data-ready="true"]');
  for(const [variant,name] of [['C','single'],['EX','twin'],['E','strike']]){
    await page.locator('f15-family-scene').evaluate((el,v)=>el.setAttribute('variant',v),variant);
    await page.locator('canvas').screenshot({path:resolve(publicDir,`exhibits/f15-family/${name}.png`),omitBackground:true});
    process.stdout.write(`Rendered ${name}.png\n`);
  }
}finally{await browser.close();server.close();}
