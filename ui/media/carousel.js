(function () {
    var carousel;
            
    YAHOO.util.Event.onDOMReady(function (ev) {
        var carousel    = new YAHOO.widget.Carousel("container", {
                    revealAmount: 35, isCircular: true, numVisible: 1
            });

        carousel.render(); // get ready for rendering the widget
        carousel.show();   // display the widget
    });
})();
