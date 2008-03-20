
function show_element(id) {
  document.getElementById(id).style.visibility = 'visible';
}

function hide_element(id) {
  document.getElementById(id).style.visibility = 'hidden';
}


function pause(milliseconds) {
  var now = new Date();
  var exitTime = now.getTime() + milliseconds;
  while (true) {
    now = new Date();
    if (now.getTime() > exitTime)
      return;
  }
}

