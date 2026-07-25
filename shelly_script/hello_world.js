HTTPServer.registerEndpoint("hello", function(req, res) {

  function htmlEscape(value) {
    value = String(value);
    value = value.split("&").join("&amp;");
    value = value.split("<").join("&lt;");
    value = value.split(">").join("&gt;");
    value = value.split("\"").join("&quot;");
    return value;
  }

  function sendPage(value) {
    res.code = 200;
    res.headers = [
      ["Content-Type", "text/html; charset=utf-8"]
    ];

    res.body =
      "<!DOCTYPE html>" +
      "<html>" +
      "<head><title>Shelly KVS</title></head>" +
      "<body>" +
      "<h1>Shelly KVS</h1>" +
      "<p>Current value of <b>foo</b>:" + htmlEscape(value) + "</p>" +
      "<form method='GET'>" +
      "<input type='text' name='foo' value='" + htmlEscape(value) + "'>" +
      "<input type='submit' value='Save'>" +
      "</form>" +
      "</body>" +
      "</html>";

    res.send();
  }

  let newValue = null;

  if (req.query) {
    let params = req.query.split("&");

    for (let i = 0; i < params.length; i++) {
      let pair = params[i].split("=");

      if (pair[0] === "foo") {
        newValue = pair[1] || "";
      }
    }
  }

  if (newValue !== null) {

    Shelly.call(
      "KVS.Set",
      {
        key: "foo",
        value: newValue
      },
      function(result, error_code, error_message) {

        if (error_code !== 0) {
          sendPage("ERROR: " + error_message);
        } else {
          sendPage(newValue);
        }

      }
    );

  } else {

    Shelly.call(
      "KVS.Get",
      {
        key: "foo"
      },
      function(result, error_code, error_message) {

        let value = "";

        if (error_code === 0) {
          value = result.value;
        }

        sendPage(value);

      }
    );

  }

});
