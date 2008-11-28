//update display of the large image
function displayImage(domAAroundImgThumb)
{
	if (!domAAroundImgThumb.hasClass('shown'))
	{
		if (domAAroundImgThumb.attr('href'))
		{
			var newSrc = domAAroundImgThumb.attr('href').replace('thickbox','large');
			$('#bigpic').fadeOut('fast', function(){
				$(this).attr('src', newSrc);
				$(this).fadeIn('fast');
			});
			$('#views_block li a').removeClass('shown');
			$(domAAroundImgThumb).addClass('shown');
		}
	}
}

//To do after loading HTML
$(document).ready(function(){
	
	//init the serialScroll for thumbs
	$('#thumbs_list').serialScroll({
		items:'li',
		prev:'a#view_scroll_left',
		next:'a#view_scroll_right',
		axis:'x',
		offset:0,
		start:0,
		stop:true,
		duration:700,
		step: 2,
		lock: false,
		force:false,
		cycle:false
	});

	//hover 'other views' images management
	$('#views_block li a').hover(
		function(){displayImage($(this));},
		function(){}
	);

	//add a link on the span 'view full size' and on the big image
	$('span#view_full_size, div#image-block img').click(function(){
		$('#views_block li a.shown').click();
	});

	//catch the click on the "more infos" button at the top of the page
	$('div#short_description_block p a.button').click(function(){
		$('#more_info_tab_more_info').click();
		$.scrollTo( '#more_info_tabs', 1200 );
	});
});
