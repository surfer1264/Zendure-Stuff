let CONFIG = {
  // ------------------------------------------------------------------
  // GERAETEBLOCK - 1:1 aus zerooutput_multi_kvs.js kopieren, gleiche
  // Reihenfolge (Index i == zdmc_dev{i}_... in der KVS). Alle Felder des
  // Regel-Scripts duerfen stehen bleiben; dieses Script nutzt sie zum Teil
  // nur als Grenzwerte fuer die Dashboard-Regler.
  // ------------------------------------------------------------------
  devices: [
    {
      ip: "192.168.178.143",
      label: "SF2400",
      minSoc: 15,
      maxSoc: 100,
      dischargeAllowed: true,
      reverse: true,
      maxInputPower: 1000,
      maxOutput: 800,
      inputLimit: 0,
      dryRun: false
    },
    {
      ip: "192.168.178.150",
      label: "SF800",
      minSoc: 15,
      maxSoc: 100,
      dischargeAllowed: true,
      reverse: true,
      maxInputPower: 2000,
      maxOutput: 2000,
      inputLimit: 0,
      dryRun: false
    }
  ],

  // ------------------------------------------------------------------
  // WO LIEGT DIE KVS?
  //   "local"  - dieses Script laeuft auf demselben Geraet wie das
  //              Regel-Script und greift direkt zu (Shelly.call).
  //   "<IP>"   - dieses Script laeuft auf einem EIGENEN Shelly; die KVS
  //              wird per nativer RPC ueber HTTP gelesen und geschrieben:
  //              http://<IP>/rpc/KVS.GetMany bzw. /rpc/KVS.Set
  //
  // Bei getrenntem Betrieb ausserdem gridSource auf "remote" stellen und
  // gridSourceIp auf den Shelly mit der EM-Messung zeigen lassen.
  // Voraussetzung: auf dem KVS-Geraet ist keine Authentifizierung aktiv.
  // ------------------------------------------------------------------
  kvsHost: "192.168.178.117",

  hysteresis: 12,

  // ------------------------------------------------------------------
  // SMARTMETER SECTION - 1:1 Struktur/Feldnamen wie in zerooutput_multi_kvs.js
  gridSource: "remote", // "local", "remote", "http_json"
  // ------------------------------------------------------------------
  // ONLY required/used when gridSource = "remote".
  // IP address of the Shelly Pro 3EM providing the grid measurement.
  gridSourceIp: "192.168.178.117",
  // EM channel id to read (usually 0). Only used when gridSource = "remote".
  gridSourceEmId: 0,
  // ------------------------------------------------------------------
  // ONLY requested when gridSource = "http_json". Example is made for the Zendure Smart Meter 3CT, read the DOC for other devices.
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  // Name of the JSON field in that response which holds the total grid power in watts.
  // Kann auch ein Array sein fuer verschachtelte Pfade, z.B. ["StatusSNS","SML","Watt_Summe"].
  gridSourceField: "total_power",
  // Set to true if the sign of gridSourceField is inverted 
  gridSourceInvert: false,

  httpTimeout: 5,

  // Bewusst langsamer als die Dashboard-Seite (4 s). 
  // Die Anzeige wird dadurch bis zu 8 s alt
  pollIntervalSec: 8
};

let VERSION="2.1";for(let i=0;i<CONFIG.devices.length;i++){let d=CONFIG.devices[i];d.minSoc=Math.max(10,Math.min(99,d.minSoc));d.maxSoc=Math.max(d.minSoc+1,Math.min(100,d.maxSoc));if(typeof d.inputLimit!=="number")d.inputLimit=0;d.inputLimit=Math.max(0,Math.min(d.maxInputPower,d.inputLimit))}let KVS_MATCH="zdmc_*";let LATEST_STATUS={grid:{power:0,online:false},hubs:[]};let STATUS_BODY=JSON.stringify(LATEST_STATUS);let lastRequestAt=0;let IDLE_MS=15e3;let busyCount=0;let busySince=0;let bgRunning=false;let BUSY_TIMEOUT_MS=(CONFIG.devices.length+1)*CONFIG.httpTimeout*1e3+5e3;let CONFIG_WAIT_MS=200;let CONFIG_WAIT_MAX=10;function busyNow(){if(busyCount>0&&Date.now()-busySince>BUSY_TIMEOUT_MS){print("Ueberlappungsschutz haengt seit ueber "+BUSY_TIMEOUT_MS/1e3+" s - zurueckgesetzt");busyCount=0;bgRunning=false}return busyCount>0}function busyEnter(){busyCount++;busySince=Date.now()}function busyLeave(){if(busyCount>0)busyCount--}function kvsItemsToMap(rawItems){let map={};if(!rawItems)return map;if(Array.isArray(rawItems)){for(let i=0;i<rawItems.length;i++){let entry=rawItems[i];if(entry&&entry.key!==undefined){map[entry.key]=entry.value}}}else{for(let k in rawItems){map[k]=rawItems[k].value!==undefined?rawItems[k].value:rawItems[k]}}return map}function kvsIsRemote(){return CONFIG.kvsHost!=="local"&&CONFIG.kvsHost!==""}function kvsGetAll(callback){if(!kvsIsRemote()){Shelly.call("KVS.GetMany",{match:KVS_MATCH},function(result,error_code){if(error_code!==0||!result||!result.items){callback(null);return}callback(kvsItemsToMap(result.items))});return}Shelly.call("HTTP.GET",{url:"http://"+CONFIG.kvsHost+"/rpc/KVS.GetMany?match="+KVS_MATCH,timeout:CONFIG.httpTimeout},function(res,error_code){if(error_code!==0||!res||res.code!==200){callback(null);return}let body=res.body;res=null;callback(body)})}function kvsValue(store,key){if(store===null||store===undefined)return undefined;if(typeof store==="string"){let i=store.indexOf('"'+key+'"');if(i<0)return undefined;let v=jsonNum(store,"value",i);return v===null?undefined:v}return store[key]}function kvsSafeNumber(value){let str=String(value);if(str.length===0||str.length>12)return null;for(let i=0;i<str.length;i++){let c=str.charAt(i);if((c<"0"||c>"9")&&c!=="-"&&c!==".")return null}return str}function kvsSetOne(key,value,callback){let str=kvsSafeNumber(value);if(str===null){callback(false);return}if(!kvsIsRemote()){Shelly.call("KVS.Set",{key:key,value:str},function(result,error_code){callback(error_code===0)});return}Shelly.call("HTTP.GET",{url:"http://"+CONFIG.kvsHost+"/rpc/KVS.Set?key="+key+"&value="+str,timeout:CONFIG.httpTimeout},function(res,error_code){callback(error_code===0&&!!res&&res.code===200)})}function percentDecode(s){let out="";let i=0;let n=s.length;while(i<n){let c=s.charAt(i);if(c==="%"&&i+2<n){let hex=s.charAt(i+1)+s.charAt(i+2);out+=String.fromCharCode(parseInt(hex,16));i+=3}else if(c==="+"){out+=" ";i+=1}else{out+=c;i+=1}}return out}function getQueryParam(query,name){if(!query)return undefined;let pairs=query.split("&");for(let i=0;i<pairs.length;i++){let eq=pairs[i].indexOf("=");if(eq<0)continue;let k=percentDecode(pairs[i].slice(0,eq));if(k===name){return percentDecode(pairs[i].slice(eq+1))}}return undefined}function jsonNum(s,key,from){let tag='"'+key+'"';let i=s.indexOf(tag,from||0);if(i<0)return null;i=s.indexOf(":",i+tag.length);if(i<0)return null;let j=i+1;while(j<s.length&&s.charAt(j)===" ")j++;if(s.charAt(j)==='"')j++;let start=j;while(j<s.length){let c=s.charAt(j);if(c>="0"&&c<="9"||c==="-"||c==="+"||c==="."||c==="e"||c==="E")j++;else break}if(j===start)return null;let v=Number(s.slice(start,j));return v!==v?null:v}function jsonMin(s,key){let tag='"'+key+'"';let best=null;let from=0;while(true){let i=s.indexOf(tag,from);if(i<0)break;from=i+tag.length;let v=jsonNum(s,key,i);if(v!==null&&v>0&&(best===null||v<best))best=v}return best}function readFieldPath(data,field){if(typeof field==="string"){return data[field]}let current=data;for(let i=0;i<field.length;i++){if(current===undefined||current===null)return undefined;current=current[field[i]]}return current}function updateGridPowerStatus(callback){if(CONFIG.gridSource==="local"){let em=Shelly.getComponentStatus("em:"+CONFIG.gridSourceEmId);if(!em){callback({power:0,online:false});return}let power=em.total_act_power;if(power===undefined){power=(em.a_act_power||0)+(em.b_act_power||0)+(em.c_act_power||0)}callback({power:Math.round(power),online:true});return}if(CONFIG.gridSource==="remote"){Shelly.call("HTTP.GET",{url:"http://"+CONFIG.gridSourceIp+"/rpc/EM.GetStatus?id="+CONFIG.gridSourceEmId,timeout:CONFIG.httpTimeout},function(res,error_code){if(error_code!==0||!res||res.code!==200){callback({power:0,online:false});return}let power=jsonNum(res.body,"total_act_power");res=null;if(power===null){callback({power:0,online:false});return}callback({power:Math.round(power),online:true})});return}if(CONFIG.gridSource==="http_json"){Shelly.call("HTTP.GET",{url:CONFIG.gridSourceUrl,timeout:CONFIG.httpTimeout},function(res,error_code){if(error_code!==0||!res||res.code!==200){callback({power:0,online:false});return}let data;try{data=JSON.parse(res.body)}catch(e){callback({power:0,online:false});return}res=null;let value=readFieldPath(data,CONFIG.gridSourceField);if(value===undefined){callback({power:0,online:false});return}let power=CONFIG.gridSourceInvert?value*-1:value;callback({power:Math.round(power),online:true})});return}callback({power:0,online:false})}function offlineHub(index){return{id:index,soc:null,power:0,acMode:null,socLimit:null,gridReverse:null,pv:null,minVol:null,online:false}}function updateHubStatus(index,callback){let cfg=CONFIG.devices[index];Shelly.call("HTTP.GET",{url:"http://"+cfg.ip+"/properties/report",timeout:CONFIG.httpTimeout},function(res,error_code){if(error_code!==0||!res||res.code!==200){callback(offlineHub(index));return}let body=res.body;res=null;let soc=jsonNum(body,"electricLevel");if(soc===null){callback(offlineHub(index));return}let acMode=jsonNum(body,"acMode");let power=0;if(acMode===2)power=jsonNum(body,"outputHomePower")||0;else if(acMode===1)power=(jsonNum(body,"gridInputPower")||0)*-1;let hub={id:index,soc:soc,power:Math.round(power),acMode:acMode,socLimit:jsonNum(body,"socLimit"),gridReverse:jsonNum(body,"gridReverse"),pv:jsonNum(body,"solarInputPower"),minVol:jsonMin(body,"minVol"),online:true};body=null;callback(hub)})}function updateAllHubsStatus(index,results,callback){if(index>=CONFIG.devices.length){callback(results);return}updateHubStatus(index,function(r){results[results.length]=r;updateAllHubsStatus(index+1,results,callback)})}function backgroundPoll(){if(Date.now()-lastRequestAt>IDLE_MS){return}if(bgRunning)return;if(busyNow())return;bgRunning=true;busyEnter();updateGridPowerStatus(function(grid){LATEST_STATUS.grid=grid;updateAllHubsStatus(0,[],function(hubs){LATEST_STATUS.hubs=hubs;STATUS_BODY=JSON.stringify(LATEST_STATUS);bgRunning=false;busyLeave()})})}Timer.set(CONFIG.pollIntervalSec*1e3,true,backgroundPoll);backgroundPoll();function buildDeviceDefaults(){let arr=[];for(let i=0;i<CONFIG.devices.length;i++){let d=CONFIG.devices[i];arr[i]={id:i,ip:d.ip,label:d.label,minSoc:d.minSoc,maxSoc:d.maxSoc,maxOutput:d.maxOutput,maxInputPower:d.maxInputPower,inputLimit:d.inputLimit,dischargeAllowed:d.dischargeAllowed!==false,reverse:!!d.reverse}}return arr}function handlePreflight(req,res){if(req.method!=="OPTIONS")return false;res.code=200;res.headers=[["Access-Control-Allow-Origin","*"],["Access-Control-Allow-Private-Network","true"],["Access-Control-Allow-Methods","GET, OPTIONS"],["Access-Control-Allow-Headers","*"]];res.body="";res.send();return true}let configPending=false;let configWaiters=[];function sendConfigBody(res,body){res.code=200;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=body;res.send()}function answerConfigWaiters(body){for(let i=0;i<configWaiters.length;i++){sendConfigBody(configWaiters[i],body)}configWaiters=[]}function serveConfig(res,attempt){if(attempt===0){if(configPending){configWaiters[configWaiters.length]=res;return}configPending=true}if(busyNow()&&attempt<CONFIG_WAIT_MAX){Timer.set(CONFIG_WAIT_MS,false,function(){serveConfig(res,attempt+1)});return}busyEnter();let devices=buildDeviceDefaults();let setpoint=0;kvsGetAll(function(store){let v=kvsValue(store,"zdmc_setpoint");if(v!==undefined)setpoint=Number(v);for(let i=0;i<devices.length;i++){let d=kvsValue(store,"zdmc_dev"+i+"_dischargeAllowed");let r=kvsValue(store,"zdmc_dev"+i+"_reverse");let m=kvsValue(store,"zdmc_dev"+i+"_minSoc");let l=kvsValue(store,"zdmc_dev"+i+"_inputLimit");if(d!==undefined)devices[i].dischargeAllowed=Number(d)!==0;if(r!==undefined)devices[i].reverse=Number(r)!==0;if(m!==undefined)devices[i].minSoc=Number(m);if(l!==undefined)devices[i].inputLimit=Number(l)}let body=JSON.stringify({version:VERSION,setpoint:setpoint,hysteresis:CONFIG.hysteresis,devices:devices});busyLeave();configPending=false;sendConfigBody(res,body);answerConfigWaiters(body)})}HTTPServer.registerEndpoint("config_api",function(req,res){if(handlePreflight(req,res))return;lastRequestAt=Date.now();serveConfig(res,0)});HTTPServer.registerEndpoint("status_api",function(req,res){if(handlePreflight(req,res))return;lastRequestAt=Date.now();res.code=200;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=STATUS_BODY;res.send()});HTTPServer.registerEndpoint("kvs_set_api",function(req,res){if(handlePreflight(req,res))return;lastRequestAt=Date.now();let dataParam=getQueryParam(req.query,"data");if(dataParam===undefined){res.code=400;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({success:false,error:"missing data param"});res.send();return}let data=null;try{data=JSON.parse(dataParam)}catch(e){data=null}if(!data||typeof data!=="object"){res.code=400;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({success:false,error:"invalid json"});res.send();return}let keys=Object.keys(data);let allowedKeys=[];for(let i=0;i<keys.length;i++){if(keys[i].indexOf("zdmc_")===0)allowedKeys[allowedKeys.length]=keys[i]}if(allowedKeys.length===0){res.code=200;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({success:true,written:0});res.send();return}writeKeys(res,data,allowedKeys,0,true)});function writeKeys(res,data,keys,index,allOk){if(index>=keys.length){res.code=allOk?200:500;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({success:allOk,written:keys.length});res.send();return}let k=keys[index];kvsSetOne(k,data[k],function(ok){writeKeys(res,data,keys,index+1,allOk&&ok)})}print("Zendure Dashboard API v"+VERSION+" gestartet (nur JSON-Endpunkte, kein HTML).");print("config_api / status_api / kvs_set_api unter "+CONFIG.kvsHost);
