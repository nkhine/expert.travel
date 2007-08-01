/*
 * XMLHttpRequest
 */
function getHTTPObject() {
  if (window.XMLHttpRequest) {
    var xhr = new XMLHttpRequest();
    // Évite un bug du navigateur Safari :
    if (xhr.overrideMimeType) {
      xhr.overrideMimeType("text/xml");
    }
  } else {
    // essaie de charger l'objet pour IE
    if (window.ActiveXObject) {
      try {
        var xhr = new ActiveXObject("Msxml2.XMLHTTP");
      } catch (e) {
        // essaie de charger l'objet pour une autre version IE
        try {
          var xhr = new ActiveXObject("Microsoft.XMLHTTP");
        } catch (e) {
          var xhr = null;
        }
      }
    }
  }
  return xhr;
}


function get_regions(url, to){
  var xhr = getHTTPObject()
  if (!xhr) {
    alert("Votre navigateur ne prend pas en charge Ajax.");
    return false;
  }

  xhr.onreadystatechange=function() {
    // 4 : état "complete"
    if (xhr.readyState == 4) {
      if (xhr.status == 200) {
        element = document.getElementById(to);
        element.innerHTML =  xhr.responseText

      }else{
        alert("Error !" +  xhr.status + ") :\n" + xhr.responseText);
      }
    }
  }
  xhr.open('GET', url, true)
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
  xhr.send("");

}
