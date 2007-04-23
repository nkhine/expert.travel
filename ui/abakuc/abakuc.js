
function select_country(value) {
  /* Hide */
  var groups = document.getElementsByTagName('optgroup');
  var group;
  for (var i=0; i<groups.length; i++) {
    group = groups[i];
    group.style.display = 'none';
  }

  /* Show */
  var element = document.getElementById(value);
  element.style.display = 'inherit';
}

function select_region(value) {
  /* Hide */
  var groups = document.getElementsByTagName('optgroup');
  var group;
  for (var i=0; i<groups.length; i++) {
    group = groups[i];
    if (group.id.substr(0, 7) == "region_") {
      group.style.display = 'none';
    }
  }

  /* Show */
  var element = document.getElementById(value);
  element.style.display = 'inherit';
}
