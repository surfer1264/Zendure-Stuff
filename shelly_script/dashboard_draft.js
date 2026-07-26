let history = [];
let maxHistory = 60;


// =====================================================
// KVS helpers
// =====================================================

function getKvsValue(key, callback) {

  Shelly.call(
    "KVS.Get",
    {
      key: key
    },
    function(result, error_code) {

      if (error_code === 0 && result) {
        callback(result.value);
      } else {
        callback("");
      }

    }
  );

}


function setKvsValue(key, value, callback) {

  Shelly.call(
    "KVS.Set",
    {
      key: key,
      value: value
    },
    function(result, error_code) {

      callback(error_code === 0);

    }
  );

}



// =====================================================
// Power API
// =====================================================

HTTPServer.registerEndpoint("dashboard_api", function(req, res) {

  let em = Shelly.getComponentStatus("em:0");

  let power = 0;


  if (em) {

    if (em.total_act_power !== undefined) {

      power = em.total_act_power;

    } else {

      power =
        (em.a_act_power || 0) +
        (em.b_act_power || 0) +
        (em.c_act_power || 0);

    }

  }


  power = Math.round(power);


  history.push(power);

  if (history.length > maxHistory) {
    history.shift();
  }


  res.code = 200;

  res.headers = [
    ["Content-Type","application/json"],
    ["Access-Control-Allow-Origin","*"]
  ];


  res.body = JSON.stringify({
    power: power,
    history: history
  });


  res.send();

});




// =====================================================
// KVS API
// =====================================================

HTTPServer.registerEndpoint("kvs_api", function(req,res) {


  if (req.query && req.query.key !== undefined) {


    setKvsValue(
      req.query.key,
      req.query.value || "",
      function(ok){

        res.code = ok ? 200 : 500;

        res.headers=[
          ["Content-Type","application/json"]
        ];

        res.body=JSON.stringify({
          success:ok
        });

        res.send();

      }
    );


    return;

  }



  let keys=[
    "zdmc_setpoint",
    "zdmc_hysteresis"
  ];


  let result={};
  let remaining=keys.length;



  keys.forEach(function(key){


    getKvsValue(key,function(value){


      result[key]=value;

      remaining--;


      if(remaining===0){

        res.code=200;

        res.headers=[
          ["Content-Type","application/json"]
        ];

        res.body=JSON.stringify(result);

        res.send();

      }


    });


  });


});




// =====================================================
// Dashboard
// =====================================================

HTTPServer.registerEndpoint("dashboard", function(req,res){


res.code=200;

res.headers=[
 ["Content-Type","text/html; charset=utf-8"]
];



res.body=

"<!DOCTYPE html>"+
"<html>"+
"<head>"+
"<meta charset='utf-8'>"+
"<meta name='viewport' content='width=device-width,initial-scale=1'>"+

"<title>Shelly Energy Dashboard</title>"+


"<style>"+

"body{"+
"font-family:Arial;"+
"background:#0b1220;"+
"color:#eee;"+
"padding:20px"+
"}"+


".card{"+
"background:#141e33;"+
"padding:20px;"+
"border-radius:16px;"+
"margin-bottom:20px"+
"}"+


".value{"+
"font-size:42px;"+
"color:#4fd1c5;"+
"font-weight:bold"+
"}"+


"canvas{"+
"width:100%;"+
"height:260px"+
"}"+


"input{"+
"background:#0b1220;"+
"color:white;"+
"border:1px solid #555;"+
"padding:8px;"+
"width:150px"+
"}"+


"button{"+
"padding:10px 20px;"+
"background:#4fd1c5;"+
"border:0;"+
"border-radius:8px"+
"}"+

"</style>"+

"</head>"+



"<body>"+


"<h1>Shelly Pro 3PM</h1>"+


"<div class='card'>"+
"<div>Current Power</div>"+
"<div class='value' id='power'>-- W</div>"+
"</div>"+


"<div class='card'>"+
"<canvas id='chart'></canvas>"+
"</div>"+



"<div class='card'>"+

"<h2>KVS Settings</h2>"+


"zdmc_setpoint<br>"+
"<input id='setpoint'><br><br>"+


"zdmc_hysteresis<br>"+
"<input id='hysteresis'><br><br>"+


"<button onclick='saveKvs()'>Save</button>"+


"</div>"+



"<script>"+


"let canvas=document.getElementById('chart');"+
"let ctx=canvas.getContext('2d');"+



"function draw(v){"+

"let w=canvas.clientWidth;"+
"let h=canvas.clientHeight;"+

"canvas.width=w;"+
"canvas.height=h;"+

"ctx.clearRect(0,0,w,h);"+

"if(v.length<2)return;"+


"let max=100;"+
"v.forEach(x=>{if(Math.abs(x)>max)max=Math.abs(x)});"+
"max=Math.ceil(max/100)*100;"+


"ctx.strokeStyle='#4fd1c5';"+
"ctx.beginPath();"+


"v.forEach(function(x,i){"+

"let px=i*w/(v.length-1);"+
"let py=h/2-(x/max)*(h/2-20);"+

"if(i==0)ctx.moveTo(px,py);"+
"else ctx.lineTo(px,py);"+

"});"+


"ctx.stroke();"+

"}"+



"async function update(){"+

"let r=await fetch('dashboard_api');"+
"let d=await r.json();"+

"document.getElementById('power').innerHTML=d.power+' W';"+
"draw(d.history);"+

"}"+



"async function loadKvs(){"+

"let r=await fetch('kvs_api');"+
"let d=await r.json();"+

"document.getElementById('setpoint').value=d.zdmc_setpoint||'';"+
"document.getElementById('hysteresis').value=d.zdmc_hysteresis||'';"+

"}"+



"async function saveKvs(){"+

"await fetch('kvs_api?key=zdmc_setpoint&value='+encodeURIComponent(document.getElementById('setpoint').value));"+

"await fetch('kvs_api?key=zdmc_hysteresis&value='+encodeURIComponent(document.getElementById('hysteresis').value));"+

"}"+


"update();"+
"loadKvs();"+
"setInterval(update,5000);"+


"</script>"+


"</body>"+
"</html>";

res.send();

});
