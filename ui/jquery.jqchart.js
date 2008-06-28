//
//jquery.jQchart
//
//@charset utf-8
//(Public Domain)
//

(function($) { 

  ////body書き忘れ対策 IEはbody無いとcanvas動かない 使う?
  if($.browser.msie)document.body||document.write('<body>');
  //http://allabout.co.jp/internet/javascript/closeup/CU20060228A/index2.htm

$.jQchart={
	version  : '0.02-beta-1.7',
	charset  : 'utf-8',
	doc      : 'http://plugins.jquery.com/project/jQchart',
	demo     : 'http://jsgt.org/lib/jquery/plugin/jqchart/nightly/nightly.htm',
	blog     : 'http://jsgt.org/mt/01/',
	author   : 'Toshiro Takahashi',
	lisence  : 'Public Domain'
}

$.fn.jQchart = {};
if (window.attachEvent) {
	if($.browser.msie)
		window.attachEvent("onload",function(){$.fn.jQchart.winloaded=true});
}
$.fn.jQchart= function(cfg){ 

	var that=this,its;
	
	//Adjustment for canvas on IE
	if($.browser.msie && !$.fn.jQchart.winloaded)$(window).load(function (){ini()})
	else ini();

	$.fn.jQchart.global_zIndex=1000;
	
	function ini(){
		switch( typeof cfg ){
			case 'string' : ajaxload(cfg)   ;break;
			case 'object' : drawChart(cfg) ;break;
		};
	}
	
	//XHR for case 'string' 
	function ajaxload(cfg){
		$.post(cfg, function(res){
			eval("var _option = "+res);
			drawChart(_option);
		});
	}
	
	//Arguments for case 'object' 
	function drawChart(_option){
	
		jQuery.extend( $.fn.jQchart,{
		
			draw : function (op){
				return this.wrtGraph(op);
			},
			
			//初期設定
			init :	function (op){ 
		
				if(!op)op={}
				if(!op.config)op.config={scaleY:{}};
				if(!op.config.scaleY)op.config.scaleY={};
				if(!op.config.line)op.config.line={};
				
				this.op=jQuery.extend({
					
					type		: op.config.type	|| 'line',
				
					//キャンバスのID名
					id	:	$(that).get(0).id||op.config.id || "canvasChart_"+(new Date()).getTime(),
					
					//キャンバスの幅と高さ
					width		: op.config.width	|| $("#"+that.get(0).id).attr('width')	||300,
					height		: op.config.height	|| $("#"+that.get(0).id).attr('height') ||150,
		
					//canvas property //あとでlineや軸別にconfig設定可能にする
					fillStyle	: op.config.fillStyle	|| "rgba(255,0,0,0.5)",
					strokeStyle	: op.config.strokeStyle	|| "rgba(180,180,180,0.5)",
					lineWidth	: op.config.lineWidth	||	1,
					
					line_strokeStyle : op.config.line.strokeStyle ||['red','#FF9114','#3CB000','#00A8A2','#0036C0','#C328FF','#FF34C0'],
					line_lineWidth   : op.config.line.lineWidth	|| 1,
		
					//フォントサイズ
					scaleFontSize	: op.config.scaleFontSize || op.fontSize ||	10,
					dataFontSize	: op.config.dataFontSize	|| op.fontSize ||10,
					
					//チャート領域のパディング
					paddingL	: op.config.paddingL	|| 40,
					paddingT	: op.config.paddingT	|| 30,
					paddingR	: op.config.paddingR	|| 10,
					paddingB	: op.config.paddingB	|| 30,
					
					//Title
					title		: op.config.title		|| '<a href="http://jsgt.org/mt/archives/01/001827.html">jquery.jQchart</a>',
					titleTop	: op.config.titleTop	|| 5,
					titleLeft	: op.config.titleLeft	|| 70,
					
	
					//Y目盛
					dataYmin	: op.config.scaleY.min || 0,
					dataYmax	: op.config.scaleY.max || 1000,
					dataYgap	: op.config.scaleY.gap || 100,
					scaleYLeft	: op.config.scaleYLeft || 4,
					
					//X軸ラベル配列
					labelX		: op.config.labelX || null,
	
					//チャート領域のデータ表示
					labelDataShow	: op.config.labelDataShow || true,
					labelDataOffsetY: op.config.labelDataOffsetY || 10,
					labelDataOffsetX: op.config.labelDataOffsetX || 0,
					
					data		: op.data ||{},
					
					draggable	: op.config.draggable || true
					
				},op||{});

				this.op.xGapPaddingR	= op.config.xGapPaddingR	|| 0,
				this.op.grid	= {
						col:(this.op.labelX)?
							this.op.labelX.length+this.op.xGapPaddingR: 
							this.op.data[0].length+this.op.xGapPaddingR||50,//暫定
						row:this.op.dataYmax/this.op.dataYgap
				};
				this.op.scaleXTop
					=this.op.scaleYBottom
					=this.op.height-this.op.paddingB;
				this.op.scaleXRight	=this.op.width-this.op.paddingR;
				this.op.chartWidth		=this.op.width -this.op.paddingL-this.op.paddingR;
				this.op.chartHeight		=this.op.height-this.op.paddingT-this.op.paddingB;
				this.op.scaleYTop		=this.op.paddingT;
				this.op.scaleXLeft		=this.op.paddingL;
				this.op.yGap			=this.op.dataYgap*this.op.chartHeight/this.op.dataYmax
				this.op.xGap			=this.op.chartWidth/this.op.grid.col
		
				this.op.xGapPaddingL	= this.op.xGap*op.config.xGapPaddingL	|| 0,
					
				this.resetBox(this.op.id);
				this.mkCanvas(this.op);
			},
			//リセット
			resetBox : function(id){
				$("#jQchart-title-T-"+id).remove();
				$("#jQchart-scale-Y-"+id).remove();
				$("#jQchart-scale-X-"+id).remove();
				$("#jQchart-data-D-"+id).remove();
			},
			//キャンバスセット
			mkCanvas : function (op){
			
				its=this;
			
				//for Opera Bug
				if(jQuery.browser.opera && eval(jQuery.browser.version,10)<9.5)
					$("#"+that.get(0).id).get(0).outerHTML=('<canvas id="'+this.op.id+'"></canvas>');
				//Canvas要素
				this.canvas = $("#"+that.get(0).id)
								.attr('width'	,this.op.width)
								.attr('height' ,this.op.height)
								.get(0)
			
				//メインCanvasDIV作成
				this.jQcanvasBox =this.mkBox4Canvas(this.canvas);
				this.canvasBox =$(this.jQcanvasBox).get(0);
					
				if (this.canvas.getContext){
		
					this.ctx=this.canvas.getContext('2d'); 
					
					//キャンバスプロパティ設定
					this.ctx.fillStyle   =this.op.fillStyle;
					this.ctx.strokeStyle =this.op.strokeStyle;
					this.ctx.lineWidth   =this.op.lineWidth;
	
					this.ctx.shadowBlur = 10;
					this.ctx.shadowOffsetX = 10;
	
	
	
					//XY軸描画
					this.setXline(this.op);
					this.setYline(this.op);
					
	
					
					//各DIV作成
					this.titleBox//Title
						=this.mkBoxElement('T',
							this.op.titleLeft,this.op.titleTop
						).appendTo(this.jQcanvasBox)
						.css('width',this.op.width-this.op.titleLeft)//fix for safari3 2007.12.4
						.get(0);
					this.scaleYBox//Y軸スケール
						=this.mkBoxElement('Y',
							this.op.scaleYLeft,this.op.scaleYTop
						).appendTo(this.jQcanvasBox).get(0);
					this.scaleXBox//X軸スケール
						=this.mkBoxElement('X',
							this.op.scaleXLeft,this.op.scaleXTop
					).appendTo(this.jQcanvasBox).get(0);
					
					this.dataBox  //チャート上のデータ
						=this.mkBoxElement('D',
							this.op.paddingL+ 'px',this.op.paddingT+ 'px'
						).appendTo(this.jQcanvasBox)
						.get(0);
					//チャート上のデータ表示/非表示
					if(this.op.labelDataShow){ $(this.dataBox).show() } else { $(this.dataBox).hide() }
	
					//ダブルクリックで位置のドラッグ移動が可能になります
					if(jQuery)if(jQuery.ui)if(jQuery.ui.draggable && this.op.draggable){
	
						var _cnt=0;_cnt++;if(_cnt>1)return;/*for fix unbind*/
					
						this.jQcanvasBox.unbind('dblclick');
						this.jQcanvasBox.dblclick(function(e){  
							
							if(!$(this).hasClass("ui-draggable")){
								draggingon(this);
							}
	
						})	.mousedown(function(){_cnt=0/*fix unbind*/})
							.click(function(e){
								if(e.target.id!=$(this).get(0).id) draggingoff(this);
							})
					}
				
					function draggingon(oj){
	
						//var jclen=$(".jQchart").length;
							
						$(oj).draggable({opacity:0.5 })
								.addClass("ui-draggable")
								.removeClass("ui-draggable-disabled")
								.css('border','2px dotted cyan')
								.css("zIndex",$.fn.jQchart.global_zIndex++)
								/*.append($('<div id="jQchart-close-'+oj.id+'" \
									style="font-size:0.9em;\
									width:300px;\
									color:#333;\
									padding:0px">[X]-close</div>').one('click',function(){
										$(_cbox).replaceWith('<canvas id="'+its.canvas.id+'"></canvas>')
									}))
								*/
								.append('<div id="jQchart-drgmsg-M-'+oj.id+'" class="jQchart-drgmsg-M">draggable-ドラッグできます</div>')
								
					}
					function draggingoff(oj){
						$(oj).draggableDisable()
							.css('border','0px')
							.removeClass("ui-draggable")
							.addClass("ui-draggable-disabled")
						$("#jQchart-drgmsg-M-"+oj.id).remove();
					}
			     //========dbug========
			     //this._debugShowPos4();
				}
			},
			
			mkBox4Canvas:function(canvas){
		
				if(!document.getElementById("jQchart-" +this.op.id))
					return $('<div></div>')
						.attr('id','jQchart-'+this.op.id)
						.attr('class','jQchart')
						.css({
									position : 'relative',
									margin	 :'0px',
									padding	 :'0px',
									width	 : this.op.width+'px',
									height	 : this.op.height+'px'
						})
						.insertBefore(canvas)
						.append(canvas)
						
				else return $("#jQchart-" +this.op.id)
			},
			mkBoxElement:function(type,x,y){
		
				var typeName='';
				switch(type){
					case 'T' : typeName='title';break;
					case 'Y' : typeName='scale';break;
					case 'X' : typeName='scale';break;
					case 'D' : typeName='data' ;break;
				};
		
				if($("'#jQchart-scale-" +type+'-'+this.op.id+"'" ).length==0)
					return $('<div></div>')
						.attr('id'	 ,'jQchart-'+typeName+'-'+type+'-'+this.op.id)
						.attr('class','jQchart-'+typeName+'-'+type)
						.css({
										position : this.op.position	||'absolute',
										left		: x 		 ||'10px',
										top			: y 		 ||'10px'
						})
						.appendTo(document.body)
		
			},
		
			//Title
			wrtTitle :	function(op){
				op.subclass = 'title' ;
					this.wrtText(0+ 'px',0+ 'px',
						this.op.title,
						op,
						"#jQchart-title-T-"+this.op.id
					);
			},
		
			//X軸ラベル
			wrtXscale	: function(op){
				op.subclass = 'labelX' ;
				op.color		= '#333'	 ;
				op.start = this.util.getBasePoint(this.op);
		
				var x=0//op.start.x ,
					y=10//op.start.y  ;

				x += op.xGapPaddingL;
				
				for (var i = 0, currP=0; i < op.grid.col;i++) {
	
					this.wrtText(x+ 'px',y+ 'px',
						op.labelX[currP]+" ",
						op,
						"#jQchart-scale-X-"+this.op.id
					);
					x	+=this.op.xGap;
					currP ++;
					this.util.setNextX(op); 
				}
				
			},
		
			//Y軸ラベル
			wrtYscale	: function(op){
				op.subclass = 'labelY' ;
				op.color		= '#333'	 ;
				op.start = this.util.getBasePoint(this.op);
		
				var x=this.op.scaleYLeft ,
					y=this.op.chartHeight - this.op.scaleFontSize ;
						
				for (var i = 0, currP=0; i <= op.grid.row;i++) {
				
					currP = Math.round((currP*100))/100;//丸め
				
					this.wrtText(x+ 'px',y+ 'px',
						currP+" ",
						op,
						"#jQchart-scale-Y-"+this.op.id
					);
					y	-=this.op.yGap;
					currP +=this.op.dataYgap;
					this.util.setNextY(op); 
				}
				
			},
		
			//水平線軸
			setXline : function(op){
				
				this.op.begin = this.util.getBasePoint(this.op);
				this.op.end	={ 
								x	: this.op.scaleXRight,
								y	: this.op.begin.y 
				}
					
				for (var i = 0; i <= this.op.grid.row; i++) { 
					this.drawLine(this.op);
					this.util.setNextY(this.op); 
				}
				
				this.op.setXline=true;
			},
		
			//垂直線軸
			setYline : function(op){
				this.op.begin = this.util.getBasePoint(this.op);
				this.op.end	={ 
								x	: this.op.begin.x,
								y	: this.op.scaleYTop
				};
				 for (var i = 0; i <= this.op.grid.col ; i++) {
						this.drawLine(this.op);
						this.util.setNextX(this.op);
				}
		
				this.op.setYline=true;
		
			},
		
			//軸描画
			drawLine : function(op){
					this.ctx.beginPath();
					this.ctx.moveTo(op.begin.x,op.begin.y);
					this.ctx.lineTo(op.end.x	,op.end.y );
					this.ctx.stroke();
					this.ctx.save();
			},
			
			//折れ線描画
			wrtGraph : function(op){	//200:y=700:100
			
				if(typeof op =='object')this.op =  op ;
				this.init(this.op);
				var op =this.op;
				var it =this ;
				//if(!its.ctx)return
				
				$.each(op.data,function(index,value){
				
					op.rows=op.data[index];
					op.subclass = 'labelData';
					op.color		= 'orange'	;
		
					var strokeStyle=op.line_strokeStyle[index]||'#777';//とりあえず7color
					its.ctx.strokeStyle=strokeStyle;//折れ線色 あとでoption指定に
					its.ctx.lineWidth=op.line_lineWidth[index]||1;
					 var x = op.paddingL,
							y = - op.rows[0]*op.height/op.dataYmax ; 

					x += op.xGapPaddingL;
						
					its.ctx.beginPath();
					
					for (var i = 0; i < op.rows.length; i++) {	
						y = op.paddingT+ op.chartHeight
								-op.rows[i]*op.chartHeight/op.dataYmax ;
			
						if(i==0) its.ctx.moveTo(x,y);
						else		 its.ctx.lineTo(x,y);
			
						//データ
						if( x <= op.width){
							var dx=x-op.paddingL,dy=y-op.paddingT;
							it.wrtText(
								dx+op.labelDataOffsetX+ 'px',
								dy+op.labelDataOffsetY+ 'px',
								op.rows[i],op,
								"#jQchart-data-D-"+op.id
							).css('color',(op.data.length==1)?'#333':strokeStyle);
						}//alert(op.rows[i],it.op)

						x += op.xGap;
						
					}
					
					its.ctx.stroke();
				});
				
				//タイトルへ
				this.wrtTitle(this.op);
				//Xラベルへ
				if(this.op.labelX)this.wrtXscale(this.op);
				//Yラベルへ
				this.wrtYscale(this.op);
		
				return $("#"+this.op.id);
				
			},
		
			//文字出力
			wrtText : function(x,y,text,op,scope){
		
				var op=op||this.op;
				if(op.subclass)var subclass= op.subclass;
		
				return $('<div class="jQchart-'+subclass+'-'+op.id+' jQchart-'+subclass+'"></div>')
					.append(text)
					.css({
						position	: op.position	||'absolute',
						left		: x 		||'10px',
						top			: y 		||'10px'
					})
						
					.appendTo(scope||document.body)
		
			},
			 hoverDataEffect : function(){
			
				$(".jQchart-labelData-"+this.op.id).hover(hover,unhover)
				
					function hover(){$(this).css("font-size","2em")}
					function unhover(){$(this).css("font-size",1+"em")}
			},
			
			//デバッグ用
			_debugShowPos4 : function(){
				var htm='Properties of<br>'
							 +'<font color="orange">$("#'+this.op.id+'").jQchart.op</font><hr>'
				for(var i in this.op)htm+=i+" : "+this.op[i]+"<br>"
				$("<div></div>").html(htm)
				.appendTo(document.body)
				.draggable({opacity:0.5 })
					.css({
						position		: 'absolute',
						top				: '10px',
						left			: '70%',
						margin			: '10px',
						padding			: '10px',
						backgroundColor	: '#eee'
					})
			},
			
			util : new function(){
				return {
					cpAry     : function(ary){
						for (var i = 0,_ary=[]; i < ary.length; i++)_ary.push(ary[i]);
						return _ary;
					},
					getMinMax : function(ary){
						//$.fn.jQchart.util.getMinMax(op.data[0]).max() 
						
						var _ary=$.fn.jQchart.util.cpAry(ary);
						return { 
							min:function(){return _ary.sort(function(a,b){return a-b})[0]},
							max:function(){return _ary.sort(function(a,b){return b-a})[0]}
						}
					},
					getBasePoint : function(op){
						return { 
							x	: op.scaleXLeft,
							y	: op.scaleYBottom
						}
					},
					setNextX	: function(op){op.begin.x = op.end.x += op.xGap;},
					setNextY	: function(op){op.begin.y = op.end.y -= op.yGap;}
				}
			}
		
		});
	
		$(that).jQchart.draw(_option);//描画
		return $(this);
	}
	
	return $(this);
}})(jQuery);

