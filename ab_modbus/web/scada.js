/* SPDX-License-Identifier: MIT · Copyright (c) 2026 MS ROBOTIKA */
"use strict";
const $ = id => document.getElementById(id);
const rawToken = new URLSearchParams(location.hash.slice(1)).get("token");
const token = rawToken || sessionStorage.getItem("ab-session") || "";
if (rawToken) sessionStorage.setItem("ab-session", rawToken);
history.replaceState(null, "", location.pathname);
const fieldIds = ["host","port","unit","function","address","count"];
let running = false, busy = false, cycle = null, samples = [], logs = [], alarms = [], currentAlarms = new Map();
let last = null, successful = 0, profiles = [], simulatorPort = null, isClosed = false;
const limits = new Map();
const MAX_SAMPLES = 1000, MAX_EVENTS = 150;
const now = () => new Date().toISOString();
function status(message, bad=false){ $("notice").textContent=message; $("notice").classList.toggle("error",bad); }
function eventLog(message) { logs.unshift({at:now(),message:String(message)}); if(logs.length>MAX_EVENTS) logs.length=MAX_EVENTS; renderEvents(); }
async function api(path, data) {
  const response = await fetch(path,{method:data===undefined?"GET":"POST",cache:"no-store",
    headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},
    body:data===undefined?undefined:JSON.stringify(data)});
  const json=await response.json();
  if(!response.ok)throw Error(json.error||"Error HTTP "+response.status);
  return json;
}
function setBadge(value,bad=false){$("state-pill").textContent=value;$("state-pill").classList.toggle("active",value==="MONITORIZANDO");$("state-pill").classList.toggle("error",bad);}
function profile() {
 return {name:"SCADA",host:$("host").value.trim(),port:Number($("port").value),
 unit:Number($("unit").value),function:Number($("function").value),
 address:Number($("address").value),count:Number($("count").value),timeout_ms:1500};
}
function currentPoint() { return Number($("selected-point").value||"0"); }
function bindPointSelectors() {
 const n=last?last.values.length:Number($("count").value)||8;
 for(const id of ["selected-point","alarm-channel"]){
  const element=$(id),old=element.value;
  element.replaceChildren();
  for(let i=0;i<n;i++){const opt=document.createElement("option");opt.value=String(i);opt.textContent="Canal "+(i+1)+" · PDU "+(Number($("address").value)+i);element.append(opt);}
  if([...element.options].some(opt=>opt.value===old)) element.value=old;
 }
 restoreLimits();
}
function restoreLimits(){
 const data=limits.get(Number($("alarm-channel").value));
 $("low").value=data&&data.low!==null?data.low:"";
 $("high").value=data&&data.high!==null?data.high:"";
}
function stop(message){
 running=false;clearTimeout(cycle);cycle=null;$("start").textContent="▶ Iniciar supervisión";
 if(message)eventLog(message);
 setBadge("DETENIDO");
}
function evaluate(value,index) {
 const threshold=limits.get(index); if(!threshold)return "";
 if(threshold.low!==null&&value<threshold.low)return "LOW";
 if(threshold.high!==null&&value>threshold.high)return "HIGH";
 return "";
}
function alarmEvent(index,level,value) {
 const label=index<0?"Comunicación":"Canal "+(index+1);
 alarms.unshift({at:now(),label,level,value,ack:false});
 if(alarms.length>MAX_EVENTS)alarms.length=MAX_EVENTS;
 renderAlarms();
}
function inspectAlarms(values){
 let active=0;
 values.forEach((value,index)=>{
  const next=evaluate(value,index),prior=currentAlarms.get(index)||"";
  if(next!==prior) {
   if(next)alarmEvent(index,next,value);
   else if(prior)alarmEvent(index,"NORMAL",value);
   currentAlarms.set(index,next);
  }
  if(next) active++;
 });
 $("kpi-alarms").textContent=String(active);
}
function renderAlarms(){
 const container=$("alarms-list");container.replaceChildren();
 if(!alarms.length){const empty=document.createElement("div");empty.className="empty-note";empty.textContent="Sin alarmas ni recuperaciones.";container.append(empty);return;}
 for(const item of alarms.slice(0,60)){
  const row=document.createElement("div");row.className="alarm-event"+(item.ack?" ack":"");
  const time=document.createElement("time");time.textContent=new Date(item.at).toLocaleTimeString("es-ES");
  const label=document.createElement("div");label.className="level";label.textContent=item.level+(item.ack?" · RECONOCIDA":"");
  const desc=document.createElement("div");desc.textContent=item.label+" · "+(item.value===null?"Fallo de lectura":"valor "+item.value);
  row.append(time,label,desc);container.append(row);
 }
}
function renderEvents(){
 const target=$("log");target.replaceChildren();
 if(!logs.length){const n=document.createElement("div");n.className="empty-note";n.textContent="Aún no hay eventos.";target.append(n);return;}
 for(const item of logs.slice(0,60)){
  const row=document.createElement("div"),time=document.createElement("time"),text=document.createElement("span");
  row.className="sc-event";time.textContent=new Date(item.at).toLocaleTimeString("es-ES");text.textContent=item.message;
  row.append(time,text);target.append(row);
 }
}
function renderPoints(values){
 const container=$("points");container.replaceChildren();
 values.forEach((value,index)=>{
  const card=document.createElement("div"),label=document.createElement("div"),number=document.createElement("strong"),footer=document.createElement("small");
  card.className="sc-point";const level=evaluate(value,index);if(level)card.classList.add("alarm-"+level.toLowerCase());
  label.className="label";label.textContent="REGISTRO "+(Number($("address").value)+index);
  number.textContent=String(value);footer.textContent=level?("ALERTA "+level):("Canal "+(index+1)+" · sin escala");
  card.append(label,number,footer);container.append(card);
 });
}
function svgEl(tag,attrs={},label=null){
 const elem=document.createElementNS("http://www.w3.org/2000/svg",tag);
 for(const [k,v] of Object.entries(attrs))elem.setAttribute(k,String(v));
 if(label!==null)elem.textContent=String(label);
 return elem;
}
function renderTrend(){
 const svg=$("trend");svg.replaceChildren();
 const idx=currentPoint(),data=samples.filter(s=>idx<s.values.length);
 if(!data.length){svg.append(svgEl("text",{x:450,y:145,fill:"#8b9aaa","text-anchor":"middle"},"Sin datos todavía"));return;}
 const vals=data.map(s=>s.values[idx]),minimum=Math.min(...vals),maximum=Math.max(...vals);
 const pad=Math.max(1,(maximum-minimum)*0.12),lo=minimum-pad,hi=maximum+pad;
 for(let i=0;i<5;i++){const y=34+i*53;svg.append(svgEl("line",{x1:50,x2:870,y1:y,y2:y,stroke:"#e7edf1"}));const tick=hi-(hi-lo)*i/4;svg.append(svgEl("text",{x:43,y:y+4,"text-anchor":"end",fill:"#758896","font-size":12},tick.toFixed(1)));}
 const x=i=>data.length===1?460:50+820*i/(data.length-1);
 const y=v=>246-212*(v-lo)/(hi-lo);
 const pts=data.map((s,i)=>x(i).toFixed(2)+","+y(s.values[idx]).toFixed(2)).join(" ");
 svg.append(svgEl("polyline",{points:pts,fill:"none",stroke:"#15977c","stroke-width":3,"stroke-linejoin":"round","stroke-linecap":"round"}));
 const lastVal=vals[vals.length-1];svg.append(svgEl("circle",{cx:x(vals.length-1),cy:y(lastVal),r:5,fill:"#126d59"}));
 svg.append(svgEl("text",{x:55,y:279,fill:"#81939c","font-size":12},new Date(data[0].at).toLocaleTimeString("es-ES")));
 svg.append(svgEl("text",{x:865,y:279,fill:"#81939c","font-size":12,"text-anchor":"end"},new Date(data[data.length-1].at).toLocaleTimeString("es-ES")));
 $("chart-meta").textContent=data.length+" muestras · bruto "+lastVal;
}
async function readOnce(){
 if(busy||isClosed)return false;
 if(!$("config-form").reportValidity())return false;
 busy=true;$("once").disabled=true;
 try{
  const result=await api("/api/read",{profile:profile(),allow_lan:$("allow-lan").checked});
  last=result;successful++;
  samples.push({at:now(),values:result.values.slice(),elapsed_ms:result.elapsed_ms});
  if(samples.length>MAX_SAMPLES)samples.shift();
  $("kpi-reads").textContent=String(successful);$("kpi-points").textContent=String(result.values.length);
  $("kpi-delay").textContent=result.elapsed_ms+" ms";
  $("last-read").textContent=new Date().toLocaleTimeString("es-ES");
  bindPointSelectors();inspectAlarms(result.values);renderPoints(result.values);renderTrend();
  status("Lectura correcta. "+result.values.length+" valores recibidos sin escrituras.");
  setBadge(running?"MONITORIZANDO":"LECTURA CORRECTA");
  if(currentAlarms.get(-1)==="COMM"){currentAlarms.delete(-1);alarmEvent(-1,"RECUPERADA",null);}
  return true;
 }catch(error){
  status("Error de comunicación: "+error.message,true);setBadge("FALLO DE COMUNICACIÓN",true);
  if(currentAlarms.get(-1)!=="COMM"){currentAlarms.set(-1,"COMM");alarmEvent(-1,"COMM",null);}
  eventLog("Error de adquisición: "+error.message);return false;
 }finally{
  busy=false;$("once").disabled=false;
 }
}
async function cycleRead(){
 const ok=await readOnce();
 if(!ok){stop("Supervisión detenida tras un error de adquisición.");setBadge("FALLO DE COMUNICACIÓN",true);return;}
 if(running)cycle=setTimeout(cycleRead,Number($("interval").value));
}
function csvDownload(){
 if(!samples.length){status("No hay muestras que exportar.",true);return;}
 const cols=Math.max(...samples.map(s=>s.values.length));
 const escapeCell=v=>'"'+String(v).replaceAll('"','""')+'"';
 const rows=[["timestamp_utc","elapsed_ms",...Array.from({length:cols},(_,i)=>"raw_"+i)].map(escapeCell).join(",")];
 for(const s of samples)rows.push([s.at,s.elapsed_ms,...Array.from({length:cols},(_,i)=>s.values[i]??"")].map(escapeCell).join(","));
 const blob=new Blob([rows.join("\r\n")+"\r\n"],{type:"text/csv;charset=utf-8"});
 const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="AB-Modbus-SCADA-historico.csv";
 document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 eventLog("Exportadas "+samples.length+" muestras CSV.");
}
function configChanged(event) {
 if(running)stop("Supervisión detenida por cambio de configuración.");
 if(["host","port","unit","profile"].includes(event?.target?.id))$("allow-lan").checked=false;
 samples=[];last=null;currentAlarms.clear();$("kpi-alarms").textContent="0";
 $("kpi-points").textContent="—";$("kpi-delay").textContent="—";
 bindPointSelectors();renderTrend();$("points").replaceChildren();
}
$("config-form").addEventListener("submit",async e=>{
 e.preventDefault();
 if(running){stop("Supervisión detenida por el usuario.");return;}
 if(!$("config-form").reportValidity())return;
 running=true;$("start").textContent="■ Detener supervisión";eventLog("Supervisión iniciada por el usuario.");await cycleRead();
});
$("once").addEventListener("click",()=>{if(!running)readOnce();});
$("demo").addEventListener("click",async()=>{
 if(running)stop();
 try{
  const s=await api("/api/state");simulatorPort=s.simulator_port;
  if(simulatorPort===null){await api("/api/simulator/start",{port:15020,unit:1});simulatorPort=15020;}
  $("host").value="127.0.0.1";$("port").value=String(simulatorPort);$("unit").value="1";
  $("function").value="3";$("address").value="0";$("count").value="8";$("allow-lan").checked=false;
  configChanged();status("Laboratorio local activo. Realizando lectura...");
  await readOnce();eventLog("Laboratorio Modbus TCP local utilizado.");
 }catch(err){status(err.message,true);}
});
$("export-csv").addEventListener("click",csvDownload);
$("clear").addEventListener("click",()=>{samples=[];logs=[];alarms=[];currentAlarms.clear();renderEvents();renderAlarms();renderTrend();$("kpi-alarms").textContent="0";eventLog("Histórico y eventos de la pestaña limpiados.");});
$("selected-point").addEventListener("change",renderTrend);
$("alarm-channel").addEventListener("change",restoreLimits);
$("apply-alarm").addEventListener("click",()=>{
 const idx=Number($("alarm-channel").value),lo=$("low").value,hi=$("high").value;
 const low=lo===""?null:Number(lo),high=hi===""?null:Number(hi);
 if((low!==null&&!Number.isFinite(low))||(high!==null&&!Number.isFinite(high))||(low!==null&&high!==null&&low>=high)){
  status("Los umbrales deben ser números válidos y el bajo debe ser menor que el alto.",true);return;
 }
 limits.set(idx,{low,high});currentAlarms.delete(idx);
 if(last)inspectAlarms(last.values);renderPoints(last?.values||[]);eventLog("Umbrales actualizados del canal "+(idx+1)+".");
});
$("ack").addEventListener("click",()=>{for(const a of alarms)a.ack=true;renderAlarms();eventLog("Eventos reconocidos. Alarmas activas permanecen vigentes.");});
for(const id of fieldIds.concat(["interval"]))$(id).addEventListener("change",configChanged);
$("profile").addEventListener("change",()=>{
 const p=profiles.find(x=>x.name===$("profile").value);if(!p)return;
 $("host").value=p.host;$("port").value=p.port;
 let option=[...$("unit").options].find(x=>x.value===String(p.unit));if(!option){option=new Option(String(p.unit),String(p.unit));$("unit").add(option);}
 $("unit").value=String(p.unit);$("function").value=p.function;
 $("address").value=p.address;$("count").value=Math.min(p.count,16);configChanged({target:{id:"profile"}});status("Perfil cargado. Permiso LAN desactivado.");
});
document.addEventListener("visibilitychange",()=>{if(document.hidden&&running)stop("Supervisión detenida al ocultar la pestaña.");});
window.addEventListener("pagehide",()=>{isClosed=true;clearTimeout(cycle);running=false;});
(async()=>{
 try{
  const s=await api("/api/state");simulatorPort=s.simulator_port;profiles=s.profiles.profiles;
  $("profile").replaceChildren();
  for(const p of profiles){const option=new Option(p.name,p.name);$("profile").add(option);}
  $("profile").value=profiles[0].name;bindPointSelectors();renderAlarms();renderEvents();renderTrend();
  status("Sesión autenticada. No hay conexión activa: pulsa «Laboratorio local».");
 }catch(error){status("No hay sesión válida: abre primero la URL de inicio de AB-Modbus Studio. "+error.message,true);setBadge("SIN SESIÓN",true);}
})();
