#!/usr/bin/env node
/**
 * verify.mjs —— 太阳系 3D 作品的独立数值校验（不依赖浏览器、不依赖 Three.js）
 *
 *   node verify.mjs             默认：数值自检 + 与本地独立星历（PyEphem/VSOP87）同刻误差表
 *   node verify.mjs --online    改用 JPL Horizons 在线对照；先做可达性预检，不通则降级回本地
 *   node verify.mjs --json      以 JSON 输出全部结果
 *
 * 默认对照读 reference.json（golden file），不需要 Python、不需要网络。
 * reference.json 由 reference_ephem.py 生成，重跑可复核；来源见 SOURCES.md §4.2。
 * --online 的判据：ssd.jpl.nasa.gov/api/horizons.api 返回 HTTP 200 且响应含 $$SOE 块。
 *
 * 数据与公式与《太阳系八大行星动态运转.html》的 CONFIG / TABLES / stateOf 逐式一致。
 * 来源与已知取舍见 SOURCES.md。
 */
import {readFileSync} from 'node:fs';

const CONFIG = Object.freeze({
  AU_KM: 149597870.7,
  J2000_JD: 2451545.0,
  TT_MINUS_TAI_S: 32.184,
  LEAP_SECONDS_UTC_TAI: 37,
  KEP_TOL_DEG: 1e-6,
  KEP_MAX_ITER: 100,
  TROPICAL_YEAR_DAYS: 365.256363,
  LON_TOL_DEG: 1.0
});

/* Standish / JPL SSD, 1800-2050 AD 表（数值来源见 SOURCES.md）
   列：name,a0,e0,I0,L0,W0,O0,at,et,It,Lt,Wt,Ot,b,c,s,f */
const ELEMENTS = [
  ['Mercury',0.38709927,0.20563593,7.00497902,252.25032350,77.45779628,48.33076593,0.00000037,0.00001906,-0.00594749,149472.67411175,0.16047689,-0.12534081,0,0,0,0],
  ['Venus',  0.72333566,0.00677672,3.39467605,181.97909950,131.60246718,76.67984255,0.00000390,-0.00004107,-0.00078890,58517.81538729,0.00268329,-0.27769418,0,0,0,0],
  ['Earth',  1.00000261,0.01671123,-0.00001531,100.46457166,102.93768193,0.0,0.00000562,-0.00004392,-0.01294668,35999.37244981,0.32327364,0.0,0,0,0,0],
  ['Mars',   1.52371034,0.09339410,1.84969142,-4.55343205,-23.94362959,49.55953891,0.00001847,-0.00007882,-0.00813131,19140.30268499,0.44441088,-0.29257343,0,0,0,0],
  ['Jupiter',5.20288700,0.04838624,1.30439695,34.39644051,14.72847983,100.47390909,-0.00011607,-0.00013253,-0.00183714,3034.74612775,0.21252668,0.20469106,0,0,0,0],
  ['Saturn', 9.53667594,0.05386179,2.48599187,49.95424423,92.59887831,113.66242448,-0.00125060,-0.00050991,0.00193609,1222.49362201,-0.41897216,-0.28867794,0,0,0,0],
  ['Uranus',19.18916464,0.04725744,0.77263783,313.23810451,170.95427630,74.01692503,-0.00196176,-0.00004397,-0.00242939,428.48202785,0.40805281,0.04240589,0,0,0,0],
  ['Neptune',30.06992276,0.00859048,1.77004347,-55.12002969,44.96476227,131.78422574,0.00026291,0.00005105,0.00035372,218.45945325,-0.32241464,-0.00508664,0,0,0,0]
];

/* NASA/NSSDCA Planetary Fact Sheet - Metric（2025-03-18）
   D=Diameter km, rot=Rotation Period h（负=逆行）, obl=Obliquity deg,
   period=Orbital Period days —— 独立来源，用于检验 T²/a³，不是由 a 反算。 */
const BODIES = [
  {cn:'水星',D:4879,   rot:1407.6,  obl:0.034,  period:88.0,   horizons:'199'},
  {cn:'金星',D:12104,  rot:-5832.5, obl:177.4,  period:224.7,  horizons:'299'},
  {cn:'地球',D:12756,  rot:23.9,    obl:23.4,   period:365.2,  horizons:'3'},
  {cn:'火星',D:6792,   rot:24.6,    obl:25.2,   period:687.0,  horizons:'499'},
  {cn:'木星',D:142984, rot:9.9,     obl:3.1,    period:4331,   horizons:'599'},
  {cn:'土星',D:120536, rot:10.7,    obl:26.7,   period:10747,  horizons:'699'},
  {cn:'天王星',D:51118,rot:-17.2,   obl:97.8,   period:30589,  horizons:'799'},
  {cn:'海王星',D:49528,rot:16.1,    obl:28.3,   period:59800,  horizons:'899'}
];

const D2R=Math.PI/180, R2D=180/Math.PI;
const jdUTC=ms=>ms/86400000+2440587.5;
const jdTDB=ms=>jdUTC(ms)+(CONFIG.TT_MINUS_TAI_S+CONFIG.LEAP_SECONDS_UTC_TAI)/86400;

function elementsAt(row,T){
  const [,a0,e0,I0,L0,W0,O0,at,et,It,Lt,Wt,Ot,b,c,s,f]=row;
  return {a:a0+at*T,e:e0+et*T,I:I0+It*T,L:L0+Lt*T,W:W0+Wt*T,O:O0+Ot*T,b,c,s,f};
}
function solveKepler(Mdeg,e,stat){
  const estar=R2D*e;
  let E=Mdeg+estar*Math.sin(Mdeg*D2R),iter=0,last=Infinity;
  for(;iter<CONFIG.KEP_MAX_ITER;iter++){
    const dM=Mdeg-(E-estar*Math.sin(E*D2R));
    const dE=dM/(1-e*Math.cos(E*D2R));
    E+=dE;last=Math.abs(dE);
    if(last<=CONFIG.KEP_TOL_DEG)break;
  }
  if(stat){stat.iter=iter+1;stat.residual=last;}
  return E;
}
function eclFromE(Edeg,el){
  const w=el.W-el.O,a=el.a,e=el.e;
  const x1=a*(Math.cos(Edeg*D2R)-e);
  const y1=a*Math.sqrt(1-e*e)*Math.sin(Edeg*D2R);
  const cw=Math.cos(w*D2R),sw=Math.sin(w*D2R),cO=Math.cos(el.O*D2R),sO=Math.sin(el.O*D2R);
  const cI=Math.cos(el.I*D2R),sI=Math.sin(el.I*D2R);
  return {
    X:(cw*cO-sw*sO*cI)*x1+(-sw*cO-cw*sO*cI)*y1,
    Y:(cw*sO+sw*cO*cI)*x1+(-sw*sO+cw*cO*cI)*y1,
    Z:(sw*sI)*x1+(cw*sI)*y1
  };
}
function trueAnomaly(Edeg,e){
  const t=Math.tan(Edeg*D2R/2)*Math.sqrt((1+e)/(1-e));
  const nu=2*Math.atan(t)*R2D;
  return ((nu%360)+360)%360;      // 归一化，避免跨 180° 时 atan 分支跳变
}
function stateOf(i,jd){
  const T=(jd-CONFIG.J2000_JD)/36525;
  const el=elementsAt(ELEMENTS[i],T);
  let M=el.L-el.W+el.b*T*T+el.c*Math.cos(el.f*T*D2R)+el.s*Math.sin(el.f*T*D2R);
  M=((M+180)%360+360)%360-180;
  const stat={};const E=solveKepler(M,el.e,stat);
  const p=eclFromE(E,el);
  return {p,el,M,E,T,r:Math.hypot(p.X,p.Y,p.Z),
    lon:((Math.atan2(p.Y,p.X)*R2D)%360+360)%360,stat};
}

/* --------------------------- 数值自检 --------------------------- */
const T0=CONFIG.J2000_JD;                                  // 2000-01-01 12:00 TDB
const T1=jdTDB(Date.parse('2026-01-01T00:00:00Z'));       // 2026-01-01 00:00 UTC
const EPOCHS=[{label:'2000-01-01 12:00 TDB',jd:T0},{label:'2026-01-01 00:00 UTC',jd:T1}];

function ephemerisTable(){
  return EPOCHS.map(ep=>({
    label:ep.label,jd:ep.jd,
    rows:BODIES.map((b,i)=>{
      const s=stateOf(i,ep.jd);
      return {planet:b.cn,lon:s.lon,r:s.r,iter:s.stat.iter,residual:s.stat.residual};
    })
  }));
}
function kepler3Table(){
  return BODIES.map((b,i)=>{
    const a=elementsAt(ELEMENTS[i],0).a;
    const T=b.period/CONFIG.TROPICAL_YEAR_DAYS;   // 独立来源的周期，年
    const ratio=T*T/(a*a*a);
    return {planet:b.cn,a,T,ratio,dev:Math.abs(ratio-1)};
  });
}
function areaSpeedTable(){
  return [0,3].map(i=>{
    const el=elementsAt(ELEMENTS[i],0);
    const nu=(M)=>trueAnomaly(solveKepler(M,el.e),el.e);
    const peri=angDiff(nu(1),nu(0));
    const aph=angDiff(nu(181),nu(180));
    return {planet:BODIES[i].cn,peri,aph,pass:peri>aph};
  });
}
function spinTable(){
  return BODIES.map(b=>({planet:b.cn,rot:b.rot,obl:b.obl,
    retrograde:b.rot<0||b.obl>90,pass:(b.rot<0||b.obl>90)===((b.cn==='金星'||b.cn==='天王星'))}));
}
function iterationTable(){
  return EPOCHS.flatMap((ep,k)=>stateOf(0,ep.jd).stat?[{
    epoch:ep.label,iter:stateOf(0,ep.jd).stat.iter,residual:stateOf(0,ep.jd).stat.residual,
    pass:stateOf(0,ep.jd).stat.residual<=CONFIG.KEP_TOL_DEG}]:[]);
}

/* ------------------- 本地独立星历参照（默认，无网络依赖） -------------------
   reference.json 由 reference_ephem.py 生成：PyEphem 4.2.1 / VSOP87 解析理论，
   与本模型的 JPL SSD 根数外推不同源、不同算法，用于第三方判卷而非自证。 */
const REFERENCE_FILE='reference.json';
function loadReference(){
  try{
    const j=JSON.parse(readFileSync(new URL(REFERENCE_FILE,import.meta.url),'utf8'));
    if(!Array.isArray(j.epochs)||j.epochs.length!==EPOCHS.length)
      throw new Error('参照时刻数与本脚本 EPOCHS 不一致');
    return {data:j};
  }catch(e){return {error:e.message};}
}
function localCompare(ephemerides,ref){
  const out=[];
  for(let k=0;k<EPOCHS.length;k++){
    const ep=EPOCHS[k],row=ref.epochs[k];
    if(!row||!Array.isArray(row.planets)||row.planets.length!==BODIES.length){
      for(const b of BODIES)out.push({epoch:ep.label,planet:b.cn,error:'参照时刻缺失或行星数不匹配'});
      continue;
    }
    for(let i=0;i<BODIES.length;i++){
      const mine=ephemerides[k].rows[i],r=row.planets[i];
      const dl=angDiff(mine.lon,r.lonJ2000);
      out.push({epoch:ep.label,planet:BODIES[i].cn,mineLon:mine.lon,refLon:r.lonJ2000,
        dLon:dl,mineR:mine.r,refR:r.rAU,dR:Math.abs(mine.r-r.rAU),
        pass:dl<ref.meta.toleranceDeg,lonDate:r.lonDate,pDeg:row.precessionDeg});
    }
  }
  return out;
}

/* ------------------- JPL Horizons 在线对照 ------------------- */
const NUM='([-+]?\\d*\\.?\\d+(?:[Ee][-+]?\\d+)?)';
async function horizonsVector(id,timeStr){
  const stop=new Date(Date.parse(timeStr.replace(' ','T')+'Z')+60000)
    .toISOString().slice(0,16).replace('T',' ');
  const q=new URLSearchParams({
    format:'text',COMMAND:`'${id}'`,OBJ_DATA:'NO',MAKE_EPHEM:'YES',
    EPHEM_TYPE:'VECTORS',CENTER:'500@10',REF_PLANE:'ECLIPTIC',VEC_TABLE:'2',
    START_TIME:`'${timeStr}'`,STOP_TIME:`'${stop}'`,STEP_SIZE:'1 m',OUT_UNITS:'AU-D'
  });
  const url='https://ssd.jpl.nasa.gov/api/horizons.api?'+q.toString();
  const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),20000);
  let text;
  try{
    const res=await fetch(url,{signal:ctl.signal});
    if(!res.ok)throw new Error('HTTP '+res.status);
    text=await res.text();
  }finally{clearTimeout(timer);}
  const soe=text.match(/\$\$SOE([\s\S]*?)\$\$EOE/);
  if(!soe)throw new Error('无 $$SOE 数据块（Horizons 可能返回错误说明）');
  const m=soe[1].match(new RegExp('X\\s*=\\s*'+NUM+'\\s+Y\\s*=\\s*'+NUM+'\\s+Z\\s*=\\s*'+NUM,'i'));
  if(!m)throw new Error('无法解析状态向量');
  const X=parseFloat(m[1]),Y=parseFloat(m[2]),Z=parseFloat(m[3]);
  return {r:Math.hypot(X,Y,Z),lon:((Math.atan2(Y,X)*R2D)%360+360)%360,url};
}
function angDiff(a,b){let d=Math.abs(a-b)%360;return d>180?360-d:d;}
/* 具体判据：能访问该端点、返回 200 且响应含 $$SOE 数据块；失败时给出可核对的原因。 */
async function horizonsPreflight(){
  const url='https://ssd.jpl.nasa.gov/api/horizons.api?format=text&COMMAND=%27199%27';
  const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),8000);
  try{
    const res=await fetch(url,{signal:ctl.signal});
    if(!res.ok)return 'HTTP '+res.status;
    const txt=await res.text();
    return txt.includes('$$SOE')?null:'响应不含 $$SOE 数据块';
  }catch(e){
    const code=(e.cause&&e.cause.code)?e.cause.code:e.name;
    return '目标域名不可达（'+code+'）';
  }finally{clearTimeout(timer);}
}
async function horizonsCompare(ephemerides){
  const out=[];
  for(let k=0;k<EPOCHS.length;k++){
    const ep=EPOCHS[k];
    const t=ep.label.replace(' 12:00 TDB','').replace(' 00:00 UTC','')+
      (k===0?' 12:00':' 00:00');
    for(let i=0;i<BODIES.length;i++){
      const b=BODIES[i];
      let h;
      try{h=await horizonsVector(b.horizons,t);}
      catch(e){out.push({epoch:ep.label,planet:b.cn,error:e.message});continue;}
      const mine=ephemerides[k].rows[i];
      const dl=angDiff(mine.lon,h.lon);
      out.push({epoch:ep.label,planet:b.cn,mineLon:mine.lon,refLon:h.lon,
        dLon:dl,mineR:mine.r,refR:h.r,dR:Math.abs(mine.r-h.r),
        pass:dl<CONFIG.LON_TOL_DEG,url:h.url});
    }
  }
  return out;
}

/* --------------------------- 输出 --------------------------- */
const pad=(s,n)=>String(s).padEnd(n,' ');
const padL=(s,n)=>String(s).padStart(n,' ');
async function main(){
  const online=process.argv.includes('--online');
  const json=process.argv.includes('--json');
  const ep=ephemerisTable(),k3=kepler3Table(),area=areaSpeedTable(),spin=spinTable(),iter=iterationTable();
  const k3max=Math.max(...k3.map(r=>r.dev));
  const allPass=k3max<0.02&&area.every(r=>r.pass)&&spin.every(r=>r.pass)&&iter.every(r=>r.pass);
  const ref=loadReference();
  let cmp=null,cmpSource=null,cmpNote=null,cmpPrecession=null;
  if(online){
    if(typeof fetch!=='function'){
      cmpNote='当前 Node 不支持 fetch（需 18+），已降级为本地独立星历对照。';
    }else{
      const pre=await horizonsPreflight();
      if(pre){
        cmpNote='JPL Horizons 预检未通过：'+pre+'。已降级为本地独立星历对照。';
      }else{
        console.log('JPL Horizons 预检通过，正在请求（16 次，串行）…');
        cmp=await horizonsCompare(ep);cmpSource='JPL Horizons';
      }
    }
    if(!cmp&&!ref.error){cmp=localCompare(ep,ref.data);cmpSource=ref.data.meta.source+'（降级）';}
  }else if(!ref.error){
    cmp=localCompare(ep,ref.data);cmpSource=ref.data.meta.source;
    cmpPrecession=ref.data.epochs.map(e=>e.precessionDeg);
  }else{
    cmpNote='本地参照文件不可用：'+ref.error+'；可运行 python3 reference_ephem.py 重新生成。';
  }
  if(!cmp&&!cmpNote)cmpNote='本地参照文件不可用：'+ref.error;
  const ok=cmp?cmp.filter(r=>!r.error):[];
  const errs=cmp?cmp.filter(r=>r.error):[];
  const cmpPass=ok.length===EPOCHS.length*BODIES.length&&ok.every(r=>r.pass);

  if(json){
    console.log(JSON.stringify({epochs:ep,kepler3:k3,kepler3MaxDev:k3max,area,spin,iter,
      comparison:{source:cmpSource,note:cmpNote,pass:cmpPass,rows:cmp}},null,2));
    return;
  }
  console.log('\n===== 太阳系 3D 作品 · 独立数值自检 =====');
  console.log('根数集：JPL SSD Approximate Positions of the Planets / 1800–2050 AD');
  console.log('历元：J2000.0 = JD 2451545.0 (TDB)；UTC→TDB 采用 32.184s + 37 闰秒近似');
  for(const e of ep){
    console.log('\n-- '+e.label+'  JD(TDB)='+e.jd.toFixed(6)+' --');
    console.log(pad('行星',8)+padL('日心黄经(°)',14)+padL('日距(AU)',12)+padL('迭代',7)+padL('残差(°)',12));
    e.rows.forEach(r=>console.log(pad(r.planet,8)+padL(r.lon.toFixed(4),14)+padL(r.r.toFixed(6),12)+
      padL(r.iter,7)+padL(r.residual.toExponential(1),12)));
  }
  console.log('\n① 开普勒第三定律 T²/a³（T 取自 NASA Fact Sheet 独立周期，非由 a 反算）');
  console.log(pad('行星',8)+padL('a(AU)',12)+padL('T(年)',12)+padL('T²/a³',12)+padL('偏差',12));
  k3.forEach(r=>console.log(pad(r.planet,8)+padL(r.a.toFixed(5),12)+padL(r.T.toFixed(5),12)+
    padL(r.ratio.toFixed(6),12)+padL(r.dev.toFixed(6),12)));
  console.log('最大偏差 '+k3max.toFixed(6)+' → '+(k3max<0.02?'PASS':'FAIL')+'（教学级阈值 0.02）');

  console.log('\n② 面积速度：近/远日点附近单日真近点角位移（°）');
  console.log(pad('行星',8)+padL('近日点',12)+padL('远日点',12)+padL('判定',8));
  area.forEach(r=>console.log(pad(r.planet,8)+padL(r.peri.toFixed(5),12)+padL(r.aph.toFixed(5),12)+
    padL(r.pass?'PASS':'FAIL',8)));

  console.log('\n③ 自转周期与轴倾角对照（IAU 逆行惯例：负周期 / >90° 轴倾）');
  console.log(pad('行星',8)+padL('自转(h)',12)+padL('轴倾(°)',12)+padL('逆行标记',12));
  spin.forEach(r=>console.log(pad(r.planet,8)+padL(r.rot,12)+padL(r.obl,12)+
    padL(r.retrograde?'是':'—',12)));

  console.log('\n④ 开普勒方程牛顿迭代（水星，tol 1e-6°）');
  iter.forEach(r=>console.log(r.epoch+'  iter='+r.iter+'  residual='+r.residual.toExponential(2)+'°  '+(r.pass?'PASS':'FAIL')));

  if(cmp&&ok.length){
    console.log('\n⑤ 与 '+cmpSource+' 同刻对照（教学级要求 |Δ黄经| < 1°）');
    console.log(pad('时刻',22)+pad('行星',8)+padL('本模型°',12)+padL('参照°',12)+padL('|Δ经|°',11)+padL('|Δr|AU',11)+padL('判定',7));
    ok.forEach(r=>console.log(pad(r.epoch,22)+pad(r.planet,8)+padL(r.mineLon.toFixed(4),12)+
      padL(r.refLon.toFixed(4),12)+padL(r.dLon.toFixed(4),11)+padL(r.dR.toFixed(6),11)+
      padL(r.pass?'PASS':'FAIL',7)));
    errs.forEach(r=>console.log('SKIP  '+r.epoch+'  '+r.planet+'  '+r.error));
    console.log('成功对照 '+ok.length+'/'+(EPOCHS.length*BODIES.length)+'；跳过 '+errs.length+
      '；最大 |Δ黄经| '+(ok.length?Math.max(...ok.map(r=>r.dLon)).toFixed(4):'—')+'° → '+(cmpPass?'PASS':'FAIL'));
    if(cmpSource.includes('VSOP87')&&!ref.error){
      console.log('  岁差修正 p（°）：'+ref.data.epochs.map((e,i)=>EPOCHS[i].label.slice(0,10)+' '+e.precessionDeg.toFixed(6)).join(' / ')+
        '；参照原始值为当日黄道，本模型为 J2000 黄道。');
    }
    if(cmpNote)console.log('  注：'+cmpNote);
  }else{
    console.log('\n⑤ 第三方星历逐项误差表：SKIP —— '+(cmpNote||'未知原因'));
  }
  console.log('\n离线自检总体：'+(allPass?'PASS':'FAIL'));
  console.log('含第三方对照总体：'+(allPass&&cmpPass?'PASS':'FAIL'));
  if(!allPass||!cmpPass)process.exitCode=1;
}
main().catch(e=>{console.error('校验脚本执行失败：',e.message);process.exitCode=2;});
