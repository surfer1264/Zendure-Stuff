let VERSION="2.0";
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
      dryRun: false
    },
    {
      ip: "192.168.178.150",
      label: "SF800",
      minSoc: 15,
      maxSoc: 100,
      dischargeAllowed: true,
      reverse: true,
      maxInputPower: 1000,
      maxOutput: 800,
      dryRun: false
    }
  ],

  // Hysterese ist im Regel-Script NICHT ueber die KVS veraenderbar. Der Wert
  // wird hier nur gespiegelt, damit das Dashboard ihn anzeigen kann (gleicher
  // Wert wie CONFIG.hysteresis im Regel-Script eintragen).
  hysteresis: 12,

  // ------------------------------------------------------------------
  // SMARTMETER SECTION - 1:1 Struktur/Feldnamen wie in zerooutput_multi_kvs.js
  // Where to read the household grid power from, there are three options
  gridSource: "local", // "local", "remote", "http_json"
  // ------------------------------------------------------------------
  // ONLY required/used when gridSource = "remote".
  // IP address of the Shelly Pro 3EM providing the grid measurement.
  gridSourceIp: "<IP_OF_YOUR_3EM_PRO_SHELLY>",
  // EM channel id to read (usually 0). Only used when gridSource = "remote".
  gridSourceEmId: 0,
  // ------------------------------------------------------------------
  // ONLY requested when gridSource = "http_json". Example is made for the Zendure Smart Meter 3CT, read the DOC for other devices.
  // Full URL of a generic JSON grid meter. Only used when gridSource = "http_json".
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  // Name of the JSON field in that response which holds the total grid power in watts.
  // Kann auch ein Array sein fuer verschachtelte Pfade, z.B. ["StatusSNS","SML","Watt_Summe"].
  gridSourceField: "total_power",
  // Set to true if the sign of gridSourceField is inverted compared to what
  // this script expects (positive = importing from grid).
  gridSourceInvert: false,

  httpTimeout: 5,
  pollIntervalSec: 5,

  // Ringpuffer fuer den Dashboard-Chart: so viele Messpunkte werden im
  // Script vorgehalten. Zeitfenster = historySize * pollIntervalSec.
  // 30 * 5 s = 150 s. Groesser = laengeres Fenster, aber mehr Heap.
  historySize: 30
};

for(let i=0;i<CONFIG.devices.length;i++){let d=CONFIG.devices[i];d.minSoc=Math.max(10,Math.min(99,d.minSoc));d.maxSoc=Math.max(d.minSoc+1,Math.min(100,d.maxSoc));if(typeof d.inputLimit!=="number")d.inputLimit=0;d.inputLimit=Math.max(0,Math.min(d.maxInputPower,d.inputLimit))}let KVS_MATCH="zdmc_*";let LATEST_STATUS={grid:{power:0,online:false},hubs:[]};let lastRequestAt=0;let IDLE_MS=15e3;let busy=false;let busySince=0;let BUSY_TIMEOUT_MS=15e3;let CONFIG_WAIT_MS=200;let CONFIG_WAIT_MAX=5;function busyNow(){if(busy&&Date.now()-busySince>BUSY_TIMEOUT_MS){print("busy-Flag haengt seit ueber "+BUSY_TIMEOUT_MS/1e3+" s - zurueckgesetzt");busy=false}return busy}function busyLock(){busy=true;busySince=Date.now()}function busyRelease(){busy=false}function whenFree(attempt,run){if(busyNow()&&attempt<CONFIG_WAIT_MAX){Timer.set(CONFIG_WAIT_MS,false,function(){whenFree(attempt+1,run)});return}busyLock();run()}function safeCall(method,params,cb){try{Shelly.call(method,params,cb)}catch(e){print("Shelly.call abgewiesen: "+method);Timer.set(1,false,function(){cb(null,-1)})}}function kvsItemsToMap(rawItems){let map={};if(!rawItems)return map;if(Array.isArray(rawItems)){for(let i=0;i<rawItems.length;i++){let entry=rawItems[i];if(entry&&entry.key!==undefined){map[entry.key]=entry.value}}}else{for(let k in rawItems){map[k]=rawItems[k].value!==undefined?rawItems[k].value:rawItems[k]}}return map}function percentDecode(s){let out="";let i=0;let n=s.length;while(i<n){let c=s.charAt(i);if(c==="%"&&i+2<n){let hex=s.charAt(i+1)+s.charAt(i+2);out+=String.fromCharCode(parseInt(hex,16));i+=3}else if(c==="+"){out+=" ";i+=1}else{out+=c;i+=1}}return out}function getQueryParam(query,name){if(!query)return undefined;let pairs=query.split("&");for(let i=0;i<pairs.length;i++){let eq=pairs[i].indexOf("=");if(eq<0)continue;let k=percentDecode(pairs[i].slice(0,eq));if(k===name){return percentDecode(pairs[i].slice(eq+1))}}return undefined}function readFieldPath(data,field){if(typeof field==="string"){return data[field]}let current=data;for(let i=0;i<field.length;i++){if(current===undefined||current===null)return undefined;current=current[field[i]]}return current}function updateGridPowerStatus(callback){if(CONFIG.gridSource==="local"){let em=Shelly.getComponentStatus("em:"+CONFIG.gridSourceEmId);if(!em){callback({power:0,online:false});return}let power=em.total_act_power;if(power===undefined){power=(em.a_act_power||0)+(em.b_act_power||0)+(em.c_act_power||0)}callback({power:Math.round(power),online:true});return}if(CONFIG.gridSource==="remote"){safeCall("HTTP.GET",{url:"http://"+CONFIG.gridSourceIp+"/rpc/EM.GetStatus?id="+CONFIG.gridSourceEmId,timeout:CONFIG.httpTimeout},function(res,error_code){if(error_code!==0||!res||res.code!==200){callback({power:0,online:false});return}let data;try{data=JSON.parse(res.body)}catch(e){callback({power:0,online:false});return}res=null;if(data.total_act_power===undefined){callback({power:0,online:false});return}callback({power:Math.round(data.total_act_power),online:true})});return}if(CONFIG.gridSource==="http_json"){safeCall("HTTP.GET",{url:CONFIG.gridSourceUrl,timeout:CONFIG.httpTimeout},function(res,error_code){if(error_code!==0||!res||res.code!==200){callback({power:0,online:false});return}let data;try{data=JSON.parse(res.body)}catch(e){callback({power:0,online:false});return}res=null;let value=readFieldPath(data,CONFIG.gridSourceField);if(value===undefined){callback({power:0,online:false});return}let power=CONFIG.gridSourceInvert?value*-1:value;callback({power:Math.round(power),online:true})});return}callback({power:0,online:false})}function offlineHub(index){return{id:index,soc:null,power:0,acMode:null,socLimit:null,gridReverse:null,pv:null,minVol:null,online:false}}function updateHubStatus(index,callback){let cfg=CONFIG.devices[index];safeCall("HTTP.GET",{url:"http://"+cfg.ip+"/properties/report",timeout:CONFIG.httpTimeout},function(res,error_code){if(error_code!==0||!res||res.code!==200){callback(offlineHub(index));return}let data;try{data=JSON.parse(res.body)}catch(e){callback(offlineHub(index));return}res=null;if(!data.properties){callback(offlineHub(index));return}let p=data.properties;let minVol=null;let packs=data.packData;if(packs&&packs.length){for(let k=0;k<packs.length;k++){let v=packs[k]?packs[k].minVol:undefined;if(typeof v==="number"&&v>0){if(minVol===null||v<minVol)minVol=v}}}data=null;let power=0;if(p.acMode===2){power=p.outputHomePower||0}else if(p.acMode===1){power=(p.gridInputPower||0)*-1}callback({id:index,soc:p.electricLevel,power:Math.round(power),acMode:p.acMode!==undefined?p.acMode:null,socLimit:p.socLimit!==undefined?p.socLimit:null,gridReverse:p.gridReverse!==undefined?p.gridReverse:null,pv:p.solarInputPower!==undefined?p.solarInputPower:null,minVol:minVol,online:true})})}function updateAllHubsStatus(index,results,callback){if(index>=CONFIG.devices.length){callback(results);return}updateHubStatus(index,function(r){results[results.length]=r;updateAllHubsStatus(index+1,results,callback)})}function backgroundPoll(){if(Date.now()-lastRequestAt>IDLE_MS){return}if(busyNow())return;busyLock();updateGridPowerStatus(function(grid){LATEST_STATUS.grid=grid;updateAllHubsStatus(0,[],function(hubs){LATEST_STATUS.hubs=hubs;busyRelease()})})}Timer.set(CONFIG.pollIntervalSec*1e3,true,backgroundPoll);backgroundPoll();function buildDeviceDefaults(){let arr=[];for(let i=0;i<CONFIG.devices.length;i++){let d=CONFIG.devices[i];arr[i]={id:i,ip:d.ip,label:d.label,minSoc:d.minSoc,maxSoc:d.maxSoc,maxOutput:d.maxOutput,maxInputPower:d.maxInputPower,inputLimit:d.inputLimit,dischargeAllowed:d.dischargeAllowed!==false,reverse:!!d.reverse}}return arr}function handlePreflight(req,res){if(req.method!=="OPTIONS")return false;res.code=200;res.headers=[["Access-Control-Allow-Origin","*"],["Access-Control-Allow-Private-Network","true"],["Access-Control-Allow-Methods","GET, OPTIONS"],["Access-Control-Allow-Headers","*"]];res.body="";res.send();return true}function serveConfig(res){whenFree(0,function(){let devices=buildDeviceDefaults();let setpoint=0;safeCall("KVS.GetMany",{match:KVS_MATCH},function(result,error_code){if(error_code===0&&result&&result.items){let items=kvsItemsToMap(result.items);if(items["zdmc_setpoint"]!==undefined)setpoint=Number(items["zdmc_setpoint"]);for(let i=0;i<devices.length;i++){let dKey="zdmc_dev"+i+"_dischargeAllowed";let rKey="zdmc_dev"+i+"_reverse";let mKey="zdmc_dev"+i+"_minSoc";let lKey="zdmc_dev"+i+"_inputLimit";if(items[dKey]!==undefined)devices[i].dischargeAllowed=Number(items[dKey])!==0;if(items[rKey]!==undefined)devices[i].reverse=Number(items[rKey])!==0;if(items[mKey]!==undefined)devices[i].minSoc=Number(items[mKey]);if(items[lKey]!==undefined)devices[i].inputLimit=Number(items[lKey])}}res.code=200;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({version:VERSION,setpoint:setpoint,hysteresis:CONFIG.hysteresis,devices:devices});busyRelease();res.send()})})}HTTPServer.registerEndpoint("config_api",function(req,res){if(handlePreflight(req,res))return;lastRequestAt=Date.now();serveConfig(res)});HTTPServer.registerEndpoint("status_api",function(req,res){if(handlePreflight(req,res))return;lastRequestAt=Date.now();res.code=200;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify(LATEST_STATUS);res.send()});HTTPServer.registerEndpoint("kvs_set_api",function(req,res){if(handlePreflight(req,res))return;lastRequestAt=Date.now();let dataParam=getQueryParam(req.query,"data");if(dataParam===undefined){res.code=400;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({success:false,error:"missing data param"});res.send();return}let data=null;try{data=JSON.parse(dataParam)}catch(e){data=null}if(!data||typeof data!=="object"){res.code=400;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({success:false,error:"invalid json"});res.send();return}let keys=Object.keys(data);let allowedKeys=[];for(let i=0;i<keys.length;i++){if(keys[i].indexOf("zdmc_")===0)allowedKeys[allowedKeys.length]=keys[i]}if(allowedKeys.length===0){res.code=200;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({success:true,written:0});res.send();return}writeKeysSequential(res,data,allowedKeys,0,true)});function writeKeysSequential(res,data,keys,index,allOk){if(index>=keys.length){res.code=allOk?200:500;res.headers=[["Content-Type","application/json"],["Access-Control-Allow-Origin","*"]];res.body=JSON.stringify({success:allOk,written:keys.length});res.send();return}let k=keys[index];safeCall("KVS.Set",{key:k,value:String(data[k])},function(result,error_code){writeKeysSequential(res,data,keys,index+1,allOk&&error_code===0)})}print("Zendure Dashboard API v"+VERSION+" gestartet (nur JSON-Endpunkte, kein HTML).");print("config_api / status_api / kvs_set_api unter http://<shelly-ip>/script/<id>/<name>");
