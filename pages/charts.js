/* 共通グラフ。KA.pal はビルド時にpalette.jsonから注入される。 */
KA.nice=function(mx){var q=Math.pow(10,Math.floor(Math.log10(mx/4))),c=[1,2,2.5,5,10];for(var i=0;i<c.length;i++){if(mx/(c[i]*q)<=5)return c[i]*q}return 10*q};
/* 折れ線: ser=[{n,v,c,w}] / o={labels,xlabel(i,label),W,H,L,R,T,B,zero,ref,fmt,aria} */
KA.line=function(el,ser,o){o=o||{};
 var M=o.labels,W=o.W||720,H=o.H||300,L=o.L||44,R=o.R||165,T=o.T||12,B=o.B||28,all=[];
 ser.forEach(function(s){all=all.concat(s.v.filter(function(x){return x!=null}))});
 var mn=Math.min.apply(null,all),mx=Math.max.apply(null,all)*1.05,lo=o.zero?0:Math.floor(mn*0.95/10)*10,st=KA.nice(mx-lo),lo2=Math.floor(lo/st)*st,hi2=Math.ceil(mx/st)*st,fmt=o.fmt||function(v){return Math.round(v*10)/10};
 function X(i){return L+(W-L-R)*i/(M.length-1)}function Y(v){return T+(H-T-B)*(1-(v-lo2)/(hi2-lo2))}
 var s='<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" aria-label="'+(o.aria||"推移グラフ")+'" style="font-size:11px">';
 for(var v=lo2;v<=hi2+1e-9;v+=st){s+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="currentColor" opacity=".15"/><text x="'+(L-6)+'" y="'+(Y(v)+4)+'" text-anchor="end" fill="currentColor" opacity=".7">'+fmt(v)+'</text>'}
 M.forEach(function(m,i){var t=o.xlabel?o.xlabel(i,m):m;if(t!=null)s+='<text x="'+X(i)+'" y="'+(H-8)+'" text-anchor="middle" fill="currentColor" opacity=".7">'+t+'</text>'});
 var ends=ser.map(function(x){var l=x.v.length-1;while(x.v[l]==null)l--;return [x,x.v[l],l]}).sort(function(a,b){return b[1]-a[1]}),ly={},last=-99;
 ends.forEach(function(e){var y=Y(e[1]);if(last>-99&&y-last<14)y=last+14;ly[e[0].n]=y;last=y});
 if(o.ref!=null)s+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(o.ref)+'" y2="'+Y(o.ref)+'" stroke="currentColor" opacity=".35" stroke-dasharray="4 4"/>';
 ser.slice().reverse().forEach(function(x){var pts=[];x.v.forEach(function(v,i){if(v!=null)pts.push(X(i)+","+Y(v))});
  s+='<polyline points="'+pts.join(" ")+'" fill="none" stroke="'+x.c+'" stroke-width="'+(x.w||2)+'" stroke-linejoin="round" stroke-linecap="round"/>';
  var e=ends.filter(function(q){return q[0]===x})[0];
  s+='<circle cx="'+X(e[2])+'" cy="'+Y(e[1])+'" r="'+((x.w||2)>2?4:3)+'" fill="'+x.c+'"/><text x="'+(W-R+8)+'" y="'+(ly[x.n]+4)+'" fill="'+x.c+'" font-weight="'+((x.w||2)>2?700:500)+'">'+x.n+" "+e[1]+'</text>'});
 el.innerHTML=s+'</svg>'};
