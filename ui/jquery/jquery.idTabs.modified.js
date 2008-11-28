/* idTabs ~ Sean Catchpole - Version 1.0 */ 
 
/* Options (in any order): 
 
 start (number|string) 
    Index number of default tab. ex: idTabs(0) 
    String of id of default tab. ex: idTabs("#tab1") 
    default: class "selected" or index 0 
 
 return (boolean) 
    True - Url will change. ex: idTabs(true) 
    False - Url will not change. ex: idTabs(false) 
    default: false 
 
 click (function) 
    Function will be called when a tab is clicked. ex: idTabs(foo) 
    If the function returns true, idTabs will show/hide content (as usual). 
    If the function returns false, idTabs will not take any action. 
    The function is passed three variables: 
      The id of the element to be shown 
      an array of all id's that can be shown 
      and the element containing the tabs 
*/ 
(function($){ 
  $.fn.idTabs = function(){ 
    //Defaults 
    var s = { "start":null, 
              "return":false, 
              "click":null }; 
 
    //Loop Arguments matching options 
    for(var i=0; i<arguments.length; ++i) { 
      var n = {}, a=arguments[i]; 
      switch(typeof a){ 
        case "object": $.extend(n,a); break; 
        case "number": 
        case "string": n.start = a; break; 
        case "boolean": n["return"] = a; break; 
        case "function": n.click = a; break; 
      }; $.extend(s,n); 
    } 
     
    //Setup Tabs 
    var self = this; //Save scope 
    var list = $("a[@href^='#']",this).click(function(){ 
      if($("a.selected",self)[0]==this) 
        return s["return"]; //return if already selected 
      var id = "#"+this.href.split('#')[1]; 
      var aList = []; //save tabs 
      var idList = []; //save possible elements 
      $("a",self).each(function(){ 
        if(this.href.match(/#/)) { 
          aList[aList.length]=this; 
          idList[idList.length]="#"+this.href.split('#')[1]; 
        } 
      }); 
      if(s.click && !s.click(id,idList,self)) return s["return"]; 
      //Clear tabs, and hide all 
      for(i in aList) $(aList[i]).removeClass("selected"); 
      for(i in idList) {
	      $(idList[i]).addClass('block_hidden_only_for_screen');
      }
      //Select clicked tab and show content 
      $(this).addClass("selected"); 
      $(id).removeClass('block_hidden_only_for_screen');
      return s["return"]; //Option for changing url 
    }); 
 
    //Select default tab 
    var test; 
    if(typeof s.start == "number" && (test=list.filter(":eq("+s.start+")")).length) 
      test.click(); //Select num tab 
    else if(typeof s.start == "string" && (test=list.filter("[@href='#"+s.start+"']")).length) 
      test.click(); //Select tab linking to id 
    else if((test=list.filter(".selected")).length) 
      test.removeClass("selected").click(); //Select tab with class 'selected' 
    else list.filter(":first").click(); //Select first tab 
 
    return this; //Chainable 
  }; 
  $(function(){ $(".idTabs").each(function(){ $(this).idTabs(); }); }); 
})(jQuery)
