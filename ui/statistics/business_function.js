// JavaScript Document
    YAHOO.widget.Chart.SWFURL = "/ui/abakuc/yui/charts/assets/charts.swf";
//--- data

	YAHOO.example.publicOpinion =
	[
		{ title: "MultipleX", n: 8 },
		{ title: "Independent", n: 82 },
		{ title: "Homeworker", n: 24 },
		{ title: "Call Centre", n: 14 },
		{ title: "Other", n: 5 }
	]

	var opinionData = new YAHOO.util.DataSource( YAHOO.example.publicOpinion );
	opinionData.responseType = YAHOO.util.DataSource.TYPE_JSARRAY;
	opinionData.responseSchema = { fields: [ "title", "n" ] };

//--- chart

	var mychart = new YAHOO.widget.PieChart( "chart", opinionData,
	{
		dataField: "n",
		categoryField: "title",
		style:
		{
			padding: 20,
			legend:
			{
				display: "right",
				padding: 10,
				spacing: 5,
				font:
				{
					family: "Arial",
					size: 13
				}
			}
		},
		//only needed for flash player express install
		expressInstall: "assets/expressinstall.swf"
	});
