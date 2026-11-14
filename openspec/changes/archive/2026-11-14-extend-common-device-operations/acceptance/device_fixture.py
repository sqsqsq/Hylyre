"""Loopback-only, ephemeral browser fixture; no device files or settings change."""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import time


PAGE = r'''<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Hylyre device fixture</title>
<style>
body{font:14px system-ui;margin:12px;color:#17243d;background:#f4f7fb}h1{font-size:18px;margin:4px 0}nav{display:flex;gap:20px;margin:6px 0}button,input,textarea{font:16px system-ui}button{padding:6px}#status{white-space:pre-wrap;background:white;padding:6px;border:1px solid #aab;height:36px;overflow:auto;margin:8px 0}#pad{height:min(320px,50vh);border:3px solid #268;background:#dfedff;position:relative;touch-action:none;user-select:none;overflow:hidden}#box{position:absolute;left:30px;top:80px;width:70px;height:70px;background:#e38940;text-align:center;line-height:70px;border-radius:8px}#scroll{height:min(350px,55vh);overflow:auto;background:white;border:3px solid #268;touch-action:pan-y}.row{height:70px;border-bottom:1px solid #abc;padding:10px;box-sizing:border-box}input[type=text],textarea{display:block;width:90%;padding:6px;margin:6px 0}input[type=checkbox]{width:30px;height:30px;vertical-align:middle}label{display:block;margin:6px 0}.hidden{display:none}
</style>
<style>header{position:sticky;top:0;z-index:5;background:#f4f7fb}</style>
<header>
<h1>Hylyre fixed device fixture</h1>
<nav><a href="/?view=gestures">Gestures</a><a href="/?view=scroll">Scroll</a><a href="/?view=edit">Edit</a></nav>
<button id="reset">Reset fixture</button>
<button id="fullscreen">Toggle fullscreen</button>
<p id="status" role="status">Fixture ready</p>
</header>
<main id="gestures" class="hidden"><div id="pad" role="button" tabindex="0" aria-label="Gesture pad"><span>Gesture pad — orange box can be dragged</span><div id="box">Drag</div><span id="long-menu" class="hidden">Long press menu</span></div><p>Events record simultaneous contacts, start/end points, elapsed time, path and pinch ratio.</p></main>
<main id="scrollview" class="hidden"><div id="scroll" role="region" aria-label="Fling list"></div></main>
<main id="edit" class="hidden"><label for="entry">Fixture text</label><input id="entry" type="text" aria-label="Fixture text" value="ABCD"><label for="multiline">Fixture multiline</label><textarea id="multiline" aria-label="Fixture multiline" rows="3">first line
second line</textarea><label><input id="fixture-check" type="checkbox"> Fixture checkbox</label><button id="plain">Not checkable</button><p id="edit-state">Checkbox false; changes 0</p></main>
<script>
const view=new URLSearchParams(location.search).get('view')||'gestures';
const clientId=crypto.randomUUID();
document.querySelector(view==='scroll'?'#scrollview':view==='edit'?'#edit':'#gestures').classList.remove('hidden');
const status=document.querySelector('#status'), pad=document.querySelector('#pad'), box=document.querySelector('#box');
let seq=0, touches=new Map(), contacts=[], maximum=0, startTime=0, startDistance=null, endDistance=null, changes=0, dragged=false, boxStart=null,lastTap=null;
let queue=Promise.resolve();
function emit(type,data={}){const event={type,seq:++seq,clientId,userAgent:navigator.userAgent,view,at:Date.now(),...data};if(type!=='page-state')status.textContent=type+' '+JSON.stringify(data).slice(0,220);queue=queue.then(()=>fetch('/event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(event)})).catch(e=>{status.textContent='Telemetry failed '+e});}
function rect(el){const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};}
function layout(){return {fixtureVersion:2,visible:document.visibilityState==='visible',fullscreen:!!document.fullscreenElement,viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},screen:{width:screen.width,height:screen.height},rects:Object.fromEntries(Array.from(document.querySelectorAll('#reset,#pad,#box,#scroll,#entry,#multiline,#fixture-check,#plain,nav a'),el=>[el.id||el.textContent.toLowerCase(),rect(el)])),values:{entry:document.querySelector('#entry').value,multiline:document.querySelector('#multiline').value,checked:document.querySelector('#fixture-check').checked,changes,selectionStart:document.querySelector('#entry').selectionStart,selectionEnd:document.querySelector('#entry').selectionEnd,focused:document.activeElement.id},userAgent:navigator.userAgent};}
function point(t){return {id:t.identifier,x:Math.round(t.clientX),y:Math.round(t.clientY),screenX:Math.round(t.screenX),screenY:Math.round(t.screenY),pageX:Math.round(t.pageX),pageY:Math.round(t.pageY),at:Math.round(performance.now()),padTop:pad.getBoundingClientRect().top,viewportHeight:innerHeight,scrollY:window.scrollY,visualOffsetTop:visualViewport?.offsetTop||0}}
function distance(ts){return ts.length<2?null:Math.hypot(ts[0].clientX-ts[1].clientX,ts[0].clientY-ts[1].clientY)}
pad.addEventListener('touchstart',e=>{e.preventDefault();if(!touches.size){contacts=[];maximum=0;startTime=performance.now();startDistance=null;endDistance=null;dragged=e.target===box;boxStart={x:box.offsetLeft,y:box.offsetTop,p:point(e.changedTouches[0])};}for(const t of e.changedTouches){const p=point(t);touches.set(t.identifier,{start:p,path:[p]});}maximum=Math.max(maximum,e.touches.length);if(e.touches.length>=2&&!startDistance)startDistance=distance(e.touches);emit('touch-start',{active:e.touches.length,points:Array.from(e.touches,point)});},{passive:false});
pad.addEventListener('touchmove',e=>{e.preventDefault();for(const t of e.changedTouches){const c=touches.get(t.identifier);if(c)c.path.push(point(t));}if(e.touches.length>=2)endDistance=distance(e.touches);if(dragged&&e.touches.length===1){box.style.left=boxStart.x+e.touches[0].clientX-boxStart.p.x+'px';box.style.top=boxStart.y+e.touches[0].clientY-boxStart.p.y+'px';}},{passive:false});
pad.addEventListener('touchend',e=>{e.preventDefault();for(const t of e.changedTouches){const c=touches.get(t.identifier);if(c){c.release=point(t);contacts.push(c);touches.delete(t.identifier);}}if(!touches.size){const durationMs=Math.round(performance.now()-startTime);emit('gesture-end',{maximumContacts:maximum,durationMs,contacts,pinchRatio:startDistance&&endDistance?endDistance/startDistance:null,box:{x:box.offsetLeft,y:box.offsetTop}});const stationary=maximum===1&&contacts[0].path.every(p=>Math.hypot(p.x-contacts[0].start.x,p.y-contacts[0].start.y)<20);if(stationary&&durationMs>=2800){document.querySelector('#long-menu').classList.remove('hidden');emit('long-menu',{durationMs});}if(stationary&&durationMs<500){const now=performance.now(),p=contacts[0].start;if(lastTap&&now-lastTap.at<500&&Math.hypot(p.x-lastTap.x,p.y-lastTap.y)<20){emit('double-tap',{gapMs:Math.round(now-lastTap.at)});lastTap=null;}else lastTap={at:now,...p};}}},{passive:false});
pad.addEventListener('touchcancel',e=>{emit('touch-cancel',{active:e.touches.length});touches.clear();});
const pointers=new Map();pad.addEventListener('pointerdown',e=>{const p={...point(e),id:e.pointerId};pointers.set(e.pointerId,{start:p,path:[p]});});pad.addEventListener('pointermove',e=>{const c=pointers.get(e.pointerId);if(c)c.path.push({...point(e),id:e.pointerId});});pad.addEventListener('pointerup',e=>{const c=pointers.get(e.pointerId);if(c){emit('pointer-end',{...c,release:{...point(e),id:e.pointerId}});pointers.delete(e.pointerId);}});
pad.addEventListener('dblclick',e=>{e.preventDefault();emit('double-click');});
const list=document.querySelector('#scroll');for(let i=0;i<40;i++){const row=document.createElement('div');row.className='row';row.textContent='Fixture row '+i;list.append(row);}
let scrollTimer;list.addEventListener('scroll',()=>{clearTimeout(scrollTimer);scrollTimer=setTimeout(()=>emit('scroll-settled',{scrollTop:list.scrollTop}),120);});list.addEventListener('touchend',()=>{const atRelease=list.scrollTop;for(const ms of [0,200,600])setTimeout(()=>emit('scroll-sample',{afterReleaseMs:ms,atRelease,scrollTop:list.scrollTop}),ms);});
for(const el of document.querySelectorAll('input[type=text],textarea')){el.addEventListener('input',()=>emit('input',{id:el.id,value:el.value,start:el.selectionStart,end:el.selectionEnd}));el.addEventListener('keydown',e=>emit('key',{key:e.key,code:e.code,ctrl:e.ctrlKey,alt:e.altKey,shift:e.shiftKey,meta:e.metaKey}));el.addEventListener('keyup',()=>emit('selection',{id:el.id,value:el.value,start:el.selectionStart,end:el.selectionEnd}));}
document.querySelector('#fixture-check').addEventListener('change',e=>{changes++;document.querySelector('#edit-state').textContent='Checkbox '+e.target.checked+'; changes '+changes;emit('checked',{checked:e.target.checked,changes});});
document.querySelector('#plain').addEventListener('click',()=>emit('plain-click'));
document.querySelector('#reset').addEventListener('click',()=>{document.activeElement.blur();window.scrollTo(0,0);document.querySelector('#entry').value='ABCD';document.querySelector('#multiline').value='first line\nsecond line';document.querySelector('#fixture-check').checked=false;changes=0;document.querySelector('#edit-state').textContent='Checkbox false; changes 0';box.style.left='30px';box.style.top='80px';list.scrollTop=0;document.querySelector('#long-menu').classList.add('hidden');lastTap=null;emit('reset');emit('page-state',layout());});
emit('page-ready',layout());setInterval(()=>{if(document.visibilityState==='visible')emit('page-state',layout());},3000);
document.querySelector('#fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen({navigationUI:'hide'});}catch(e){emit('fullscreen-error',{message:String(e)});}});document.addEventListener('fullscreenchange',()=>{emit('fullscreen-state',{active:!!document.fullscreenElement});emit('page-state',layout());});
</script>'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=18765)
    parser.add_argument('--events', type=Path, required=True)
    args = parser.parse_args()
    args.events.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    state: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == '/state':
                with lock:
                    payload = json.dumps(state, ensure_ascii=False).encode()
                content_type = 'application/json'
            else:
                payload = PAGE.encode()
                content_type = 'text/html; charset=utf-8'
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            size = int(self.headers.get('Content-Length', '0'))
            if self.path != '/event' or not 0 < size <= 131072:
                self.send_error(400)
                return
            try:
                event = json.loads(self.rfile.read(size))
                if not isinstance(event, dict) or not isinstance(event.get('type'), str):
                    raise ValueError('event must have a type')
            except (ValueError, UnicodeError):
                self.send_error(400)
                return
            event['receivedAt'] = time()
            with lock:
                state.append(event)
                with args.events.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(event, ensure_ascii=False) + '\n')
            self.send_response(204)
            self.end_headers()

    print(f'Fixture http://127.0.0.1:{args.port}/; events {args.events.resolve()}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
