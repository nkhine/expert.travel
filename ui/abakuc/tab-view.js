//Gets the browser specific XmlHttpRequest Object
function getXmlHttpRequestObject() {
  if (window.XMLHttpRequest) {
    return new XMLHttpRequest(); //Not IE
  } else if(window.ActiveXObject) {
    return new ActiveXObject("Microsoft.XMLHTTP"); //IE
  } else {
    //Display your error message here. 
    //and inform the user they might want to upgrade
    //their browser.
    alert("Your browser doesn't support the XmlHttpRequest object.  Better upgrade to Firefox.");
  }
}			
//Get our browser specific XmlHttpRequest object.
var receiveReq = getXmlHttpRequestObject();		
//Initiate the asyncronous request.
function sayHello() {
  //If our XmlHttpRequest object is not in the middle of a request, start the new asyncronous call.
  if (receiveReq.readyState == 4 || receiveReq.readyState == 0) {
    //Setup the connection as a GET call to SayHello.html.
    //True explicity sets the request to asyncronous (default).
    receiveReq.open("GET", 'tt.html.txt.en', true);
    //Set the function that will be called when the XmlHttpRequest objects state changes.
    receiveReq.onreadystatechange = handleSayHello; 
    //Make the actual request.
    receiveReq.send(null);
  }			
}
//Called every time our XmlHttpRequest objects state changes.
function handleSayHello() {
  //Check to see if the XmlHttpRequests state is finished.
  if (receiveReq.readyState == 4) {
    //Set the contents of our span element to the result of the asyncronous call.
    document.getElementById('span_result').innerHTML = receiveReq.responseText;
  }
}

