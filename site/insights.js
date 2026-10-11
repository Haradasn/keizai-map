/* トップのインサイト・カルーセル。数値は pref-map-data.js(県別)と、ページに差し込まれた data 属性・文字から計算する。 */
(function(){
var root=document.getElementById('ins'); if(!root)return;
var slides=[].slice.call(root.querySelectorAll('.ins-slide')), layers=[].slice.call(root.querySelectorAll('.ins-v')), dots=[].slice.call(root.querySelectorAll('.ins-dot')),
    n=slides.length, cur=0, timer=null, userPause=false, hold=false, MS=7000,
    reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches,
    live=document.getElementById('ins-live'), count=document.getElementById('ins-count'), pauseBtn=document.getElementById('ins-pause');
function num(s){return parseFloat(String(s).replace(/[−–]/g,'-').replace(/,/g,''));}
// 1) 地域: 輸送機械(35)の特化係数が最大の県(その産業が県の総産出額の0.5%以上のもの)
function region(){
  var D=window.PREF_MAP; if(!D)return; var best=null;
  Object.keys(D.prefs).forEach(function(id){var p=D.prefs[id],s=p.s['35'];if(s&&s[1]!=null&&p.t>0&&s[0]/p.t>=0.005&&(!best||s[1]>best.lq))best={n:p.n,lq:s[1]};});
  if(!best)return; var el=slides[0];
  el.querySelector('.ins-lead').textContent=best.n+'の'+D.inds['35']+'は、全国平均の';
  el.querySelector('[data-f=big]').innerHTML=best.lq.toFixed(1)+'<small>倍</small>';
  el.querySelector('[data-f=tail]').textContent='集中している（特化係数）';
}
// 2) 棒グラフ: 棒の長さは数値に比例
function bars(){
  [].forEach.call(root.querySelectorAll('svg[data-vals],svg[data-q]'),function(svg){
    var vals=svg.dataset.vals?svg.dataset.vals.split(',').map(num):[100+num(svg.dataset.q),num(svg.dataset.p)*100], ref=svg.dataset.ref?num(svg.dataset.ref):0,
        mx=Math.max.apply(null,vals.concat([ref])), rects=svg.querySelectorAll('rect.b'), lbl=svg.querySelectorAll('.bl');
    if(svg.dataset.dir==='h'){var W=230;vals.forEach(function(v,i){var w=W*v/mx;rects[i].setAttribute('width',w.toFixed(1));lbl[i].setAttribute('x',(90+w+10).toFixed(1));});return;}
    var base=num(svg.dataset.base),H=num(svg.dataset.maxh);
    vals.forEach(function(v,i){var h=H*v/mx;rects[i].setAttribute('y',(base-h).toFixed(1));rects[i].setAttribute('height',h.toFixed(1));lbl[i].setAttribute('y',(base-h-10).toFixed(1));});
    var rf=svg.querySelector('.rf');if(rf){var y=base-H*ref/mx;rf.setAttribute('y1',y);rf.setAttribute('y2',y);svg.querySelector('.rt').setAttribute('y',y-8);}
  });
}
function show(k,manual){
  cur=(k+n)%n;
  slides.forEach(function(s,i){s.classList.toggle('is-on',i===cur);s.setAttribute('aria-hidden',i===cur?'false':'true');});
  layers.forEach(function(l,i){l.classList.toggle('is-on',i===cur);});
  dots.forEach(function(d,i){d.setAttribute('aria-current',i===cur?'true':'false');});
  if(count)count.textContent=(cur+1)+' / '+n;
  if(manual&&live)live.textContent=slides[cur].querySelector('h2').textContent;
  schedule();
}
function schedule(){
  clearTimeout(timer); root.classList.remove('ins-run');
  if(reduce||userPause||hold||document.hidden)return;
  void root.offsetWidth; root.classList.add('ins-run');
  timer=setTimeout(function(){show(cur+1,true)},MS);
}
root.classList.add('ins-js'); region(); bars(); show(0,false);
document.getElementById('ins-prev').addEventListener('click',function(){show(cur-1,true)});
document.getElementById('ins-next').addEventListener('click',function(){show(cur+1,true)});
dots.forEach(function(d,i){d.addEventListener('click',function(){show(i,true)})});
if(pauseBtn){if(reduce)pauseBtn.style.display='none';pauseBtn.addEventListener('click',function(){userPause=!userPause;pauseBtn.setAttribute('aria-pressed',userPause?'true':'false');pauseBtn.setAttribute('aria-label',userPause?'自動切り替えを再開する':'自動切り替えを止める');pauseBtn.querySelector('.pp').setAttribute('d',userPause?'M8 5v14l11-7z':'M7 5h3.5v14H7zM13.5 5H17v14h-3.5z');schedule();});}
root.addEventListener('pointerenter',function(e){if(e.pointerType==='mouse'){hold=true;schedule()}});
root.addEventListener('pointerleave',function(e){if(e.pointerType==='mouse'){hold=false;schedule()}});
root.addEventListener('focusin',function(e){if(e.target.matches&&e.target.matches(':focus-visible')){hold=true;schedule()}});
root.addEventListener('focusout',function(){hold=false;schedule()});
document.addEventListener('visibilitychange',schedule);
root.addEventListener('keydown',function(e){if(e.key==='ArrowLeft'){show(cur-1,true)}else if(e.key==='ArrowRight'){show(cur+1,true)}});
var sx=null,sy=0,st=document.getElementById('ins-stack');
st.addEventListener('touchstart',function(e){sx=e.touches[0].clientX;sy=e.touches[0].clientY},{passive:true});
st.addEventListener('touchend',function(e){if(sx===null)return;var dx=e.changedTouches[0].clientX-sx,dy=e.changedTouches[0].clientY-sy;sx=null;if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)*1.5)show(cur+(dx<0?1:-1),true)},{passive:true});
})();
