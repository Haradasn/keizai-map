/* 県別の立体地図(MapLibre GL JS)。/prefecture-map とトップページで共通。データは pref-map-data.js の window.PREF_MAP。
   使い方: <div id="pm-map" data-prefmap="page|hero"> と <select id="pm-ind">。hero はトップ用(ゆっくり回転・押し出しアニメ・操作は協調ジェスチャー)。 */
(function(){
var root=document.querySelector('[data-prefmap]'); if(!root||!window.PREF_MAP)return;
var HERO=root.getAttribute('data-prefmap')==='hero', DATA=window.PREF_MAP, INDS=DATA.inds, P=DATA.prefs;
var sel=document.getElementById('pm-ind'), box=root, list=document.getElementById('pm-list'), note=document.getElementById('pm-note'), cap=document.getElementById('pm-cap');
var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
function ok(){try{var c=document.createElement('canvas');return !!(c.getContext('webgl2')||c.getContext('webgl'))}catch(e){return false}}
function lerp(a,b,t){return Math.round(a+(b-a)*t)}
function col(lq){if(lq==null)return '#cbd5e1';var t=Math.max(0,Math.min(1,(lq-0.5)/3.5)),A=[203,213,225],B=[14,116,144];return 'rgb('+lerp(A[0],B[0],t)+','+lerp(A[1],B[1],t)+','+lerp(A[2],B[2],t)+')';}
function values(k){var out={};Object.keys(P).forEach(function(id){var p=P[id],v=null,lq=null;if(k==='all'){v=p.t}else{var s=p.s[k];if(s){v=s[0];lq=s[1];}}out[id]={name:p.n,slug:p.g,v:v,lq:lq,va:p.va};});return out;}
var map=null,geo=null,grow=HERO&&!reduce?0:1,pending=false;
function render(){
  if(!geo)return; var k=sel.value,V=values(k),mx=0,rows=[];
  Object.keys(V).forEach(function(i){if(V[i].v>mx)mx=V[i].v;});
  geo.features.forEach(function(f){var d=V[f.properties.id],has=d&&d.v!=null;
    f.properties.h=has?Math.sqrt(d.v/mx)*260000*grow+2000:2000;
    f.properties.c=has?(k==='all'?col(1+(d.va-0.4)*12):col(d.lq)):'#e2e8f0'; if(d&&has)rows.push(d);});
  if(map&&map.getSource&&map.getSource('pref'))map.getSource('pref').setData(geo);
  rows.sort(function(a,b){return b.v-a.v});
  var nm=k==='all'?'すべての産業':INDS[k];
  if(list){list.innerHTML='<caption class="text-left text-sm font-bold pb-2">'+(k==='all'?'総産出額':nm)+'（産出額の大きい順）</caption><thead><tr><th>都道府県</th><th class="text-right">産出額（兆円）</th><th class="text-right">'+(k==='all'?'付加価値率':'特化係数')+'</th></tr></thead><tbody>'+rows.map(function(d){return '<tr><td><a class="link" href="prefecture/'+d.slug+'.html">'+d.name+'</a></td><td class="text-right">'+d.v.toFixed(2)+'</td><td class="text-right">'+(k==='all'?(d.va*100).toFixed(1)+'%':(d.lq==null?'−':d.lq.toFixed(2)))+'</td></tr>'}).join('')+'</tbody>';}
  if(note)note.textContent=k==='all'?'高さ＝総産出額、色＝付加価値率（濃いほど高い）。':'高さ＝その産業の産出額、色＝特化係数（濃いほど全国平均より集中）。灰色はデータなし、または部門を合算していて比べられない県です。';
  if(cap){var top=rows.slice(0,3).map(function(d){return d.name}).join('・');cap.textContent='表示中：'+nm+'　産出額が大きい県：'+top+'（データのある'+Object.keys(P).length+'都道府県のうち）';}
  document.querySelectorAll('.pm-chip').forEach(function(b){b.classList.toggle('btn-primary',b.getAttribute('data-k')===k);b.classList.toggle('btn-outline',b.getAttribute('data-k')!==k);});
}
function loadLib(cb){if(window.maplibregl)return cb();var l=document.createElement('link');l.rel='stylesheet';l.href='vendor/maplibre-gl.css';document.head.appendChild(l);var s=document.createElement('script');s.src='vendor/maplibre-gl.js';s.onload=cb;document.head.appendChild(s);}
function rgb(){var cv=document.createElement('canvas');cv.width=cv.height=1;var cx=cv.getContext('2d');cx.fillStyle=getComputedStyle(document.body).backgroundColor;cx.fillRect(0,0,1,1);var p=cx.getImageData(0,0,1,1).data;return 'rgb('+p[0]+','+p[1]+','+p[2]+')';}   // oklch等はMapLibreが読めない
function init(){
  var small=window.innerWidth<640;
  map=new maplibregl.Map({container:box,style:{version:8,sources:{},layers:[{id:'bg',type:'background',paint:{'background-color':rgb()}}]},
    center:[137.5,37.2],zoom:HERO?(small?3.4:4.4):(small?3.6:4.6),pitch:HERO?52:45,bearing:-12,minZoom:2.5,maxZoom:8,
    cooperativeGestures:HERO,attributionControl:{compact:true,customAttribution:'境界: 地球地図日本(国土地理院)'}});
  if(!HERO)map.addControl(new maplibregl.NavigationControl({visualizePitch:true}),'top-right');
  if(HERO){var c=document.getElementById('hero-card'),bt=document.getElementById('hero-bottom');map.setPadding(small?{top:(c?c.offsetHeight:340)+50,left:0,right:0,bottom:(bt?bt.offsetHeight:150)+10}:{top:20,left:window.innerWidth>=1024?360:0,right:0,bottom:60});}
  map.on('load',function(){
    map.addSource('pref',{type:'geojson',data:geo});
    map.addLayer({id:'ext',type:'fill-extrusion',source:'pref',paint:{'fill-extrusion-color':['get','c'],'fill-extrusion-height':['get','h'],'fill-extrusion-base':0,'fill-extrusion-opacity':0.92}});
    var pop=new maplibregl.Popup({closeButton:false,closeOnClick:false});
    map.on('mousemove','ext',function(e){var f=e.features[0],V=values(sel.value)[f.properties.id];if(!V)return;map.getCanvas().style.cursor='pointer';pop.setLngLat(e.lngLat).setHTML('<b>'+f.properties.name+'</b><br>'+(V.v==null?'データなし':'産出額 '+V.v.toFixed(2)+'兆円'+(V.lq!=null?'<br>特化係数 '+V.lq.toFixed(2):''))).addTo(map);});
    map.on('mouseleave','ext',function(){map.getCanvas().style.cursor='';pop.remove();});
    map.on('click','ext',function(e){var V=values(sel.value)[e.features[0].properties.id];if(V)location.href='prefecture/'+V.slug+'.html';});
    render();
    if(HERO&&!reduce){ // 押し出し(1.2秒)のあと、ゆっくり回転。触れたら止める
      var t0=null,spin=false;
      (function rise(ts){if(t0===null)t0=ts;var t=Math.min(1,(ts-t0)/1200);grow=1-Math.pow(1-t,3);render();if(t<1)requestAnimationFrame(rise);else spin=true;})(performance.now());
      var b0=-12,last=null,stop=false;['mousedown','touchstart','wheel','keydown'].forEach(function(ev){box.addEventListener(ev,function(){stop=true},{passive:true});});
      document.addEventListener('visibilitychange',function(){last=null});
      (function turn(ts){if(stop)return;if(spin&&!document.hidden){if(last!==null){b0+=(ts-last)*0.004;map.setBearing(-12+Math.sin(b0/12)*14);}last=ts;}requestAnimationFrame(turn);})(0);
    }
  });
}
function start(){
  fetch('vendor/japan-pref.json').then(function(r){return r.json()}).then(function(g){
    geo=g;render();
    if(!ok()){if(!HERO)box.innerHTML='<p class="p-6 text-sm">この環境では3D地図を表示できません。下の一覧をご覧ください。</p>';return;}
    loadLib(init);
  });
}
sel.addEventListener('change',render);
document.querySelectorAll('.pm-chip').forEach(function(b){b.addEventListener('click',function(){sel.value=b.getAttribute('data-k');render();});});
var fl=document.getElementById('pm-flat'),tl=document.getElementById('pm-tilt');
if(fl)fl.addEventListener('click',function(){if(map)map.easeTo({pitch:0,bearing:0,duration:600});});
if(tl)tl.addEventListener('click',function(){if(map)map.easeTo({pitch:45,bearing:-12,duration:600});});
if(HERO){ // トップは表示を邪魔しないよう、ページの読み込み後に始める
  var go=function(){(window.requestIdleCallback||function(f){setTimeout(f,300)})(start)};
  if(document.readyState==='complete')go();else window.addEventListener('load',go);
}else start();
})();
