// JavaScript Document
    YAHOO.widget.Chart.SWFURL = "/ui/abakuc/yui/charts/assets/charts.swf";
//--- data

	YAHOO.example.publicOpinion =
	[
		{ response: "Multiple", count: 564815 },
		{ response: "Independent", count: 664182 },
		{ response: "Homeworker", count: 248124 },
		{ response: "Call Centre", count: 271214 },
		{ response: "Other", count: 81845 }
	]

	var opinionData = new YAHOO.util.DataSource( YAHOO.example.publicOpinion );
	opinionData.responseType = YAHOO.util.DataSource.TYPE_JSARRAY;
	opinionData.responseSchema = { fields: [ "response", "count" ] };

//--- chart

	var mychart = new YAHOO.widget.PieChart( "chart", opinionData,
	{
		dataField: "count",
		categoryField: "response",
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
