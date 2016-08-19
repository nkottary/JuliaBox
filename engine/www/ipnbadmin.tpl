<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>JuliaBox &mdash; {{d["user_id"]}}</title>
    <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
    <link rel="stylesheet" type="text/css" href="/assets/css/frames.css">

    <script type="text/javascript" src="//use.typekit.net/cpz5ogz.js"></script>
    <script type="text/javascript">try{Typekit.load();}catch(e){}</script>

	<script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
	<script type="text/javascript">
		var disp_timer;
		function secs_to_str(secs) {
			if(secs <= 60) return "0 Minutes";

		    var days = Math.floor(secs / 60 / (60 * 24));
		    var hours = Math.floor((secs - days * 24 * 60 * 60) / (60 * 60));
		    var mins = Math.floor((secs - days * 24 * 60 * 60 - hours * 60 * 60) / 60);

		    var out_str = "";
		    if(days > 0) out_str = (days + " Days ");
		    if(hours > 0) out_str = out_str + (hours + " Hours ");
		    if((hours == 0) || (mins > 0)) out_str = out_str + (mins + " Minutes ");
		    return out_str;
		};
		function show_time_remaining() {
		    var datetime = new Date('{{d["allowed_till"]}}').getTime();
		    var now = new Date().getTime();
		    var remain_secs = Math.floor((datetime - now)/1000);
		    var expire = {{d["expire"]}};
		    if(remain_secs > expire) remain_secs = expire;
		    var remain = secs_to_str(remain_secs);
		    
		    if(expire > 0) {
			    total = secs_to_str({{d["expire"]}});
			    if(remain_secs >= expire) remain = total;
			    
			    $('#disp_time_remaining').html(remain + " (of allotted " + total + ")");
			    
			    if(remain_secs < 5 * 60) {		    
				    if (remain_secs <= 0) {
				    	clearInterval(disp_timer);
				    	parent.JuliaBox.inform_logged_out();
				    }
				    else {
			    		parent.JuliaBox.inpage_alert('info', 'Your session has only ' + remain + ' of allotted time remaining.');			    	
				    }
			    }		    	
		    }
		    else {
		    	$('#disp_date_allowed_till').html("unlimited");
		    	$('#disp_time_remaining').html("unlimited");
		    	clearInterval(disp_timer);
		    }
		};

		function size_with_suffix(sz) {
	    	var suffix = "";
	    	if(sz >= 1000000000) {
	    		sz = (sz * 1.0 / 1000000000);
	    		suffix = " GB";
	    	}
	    	else {
	    		sz = (sz * 1.0 / 1000000);
	    		suffix = " MB";
	    	}
	    	return ((Math.round(sz) === sz) ? Math.round(sz).toFixed(0) : sz.toFixed(2)) + suffix;
		};
		
	    $(document).ready(function() {
	    	$('#showsshkey').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_ssh_key();
	    	});

            $('.showpackages').click(function(event) {
            	tid = event.target.id;
            	ver = tid.split('-')[1]
	    		parent.JuliaBox.show_packages(ver);
            });

            $('#delpackages').click(function(event) {
	    		parent.JuliaBox.del_packages_confirm();
            });

	    	$('#websocktest').click(function(event){
	    	    event.preventDefault();
	    	    parent.JuliaBox.websocktest();
	    	});

	    	$('#openport').click(function(event){
	    	    event.preventDefault();
	    		parent.JuliaBox.open_port();
	    	});

	    	$('#openedports').click(function(event){
	    	    event.preventDefault();
	    	    parent.JuliaBox.show_opened_ports();
	    	});

{% if (d["manage_containers"] or d["show_report"]) %}
	    	$('#showuserstats').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_stats('stat_users', 'Users');
	    	});

	    	$('#showsessionstats').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_stats('stat_sessions', 'Sessions');
	    	});

	    	$('#showvolumestats').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_stats('stat_volmgr', 'Volumes');
	    	});
{% end %}

{% if d["manage_containers"] %}
            $('#showcfg').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_config();
	    	});


	    	$('#showinstanceloads').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_instance_info('load', 'Instance Loads (percent)');
	    	});

	    	$('#showsessions').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_instance_info('sessions', 'Sessions');
	    	});

	    	$('#showapis').click(function(event){
	    		event.preventDefault();
	    		parent.JuliaBox.show_instance_info('apis', 'API Containers');
	    	});
{% end %}

	    	$('#disp_date_init').html((new Date('{{d["created"]}}')).toLocaleString());
	    	$('#disp_date_start').html((new Date('{{d["started"]}}')).toLocaleString());
	    	$('#disp_date_allowed_till').html((new Date('{{d["allowed_till"]}}')).toLocaleString());
	    	
	    	$('#disp_mem').html(size_with_suffix({{d["mem"]}}));
                $('#disp_disk').html(size_with_suffix({{d["disk"]}}));
                $('#disp_usage').html("{{d['usage']}}");
	    	show_time_remaining();
	    	disp_timer = setInterval(show_time_remaining, 60000);
	    });
	</script>
</head>
<body>

<h3>Profile &amp; session info:</h3>
<table class="table">
	<tr><td>Logged in as:</td><td>{{d["user_id"]}}</td></tr>
	<tr><td>Session initialized at:</td><td><span id='disp_date_init'></span></td></tr>
	<tr><td>Session last started at:</td><td><span id='disp_date_start'></span></td></tr>
	<tr><td>Session allowed till:</td><td><span id='disp_date_allowed_till'></span></td></tr>
	<tr><td>Time remaining:</td><td><span id='disp_time_remaining'> of {{d["expire"]}} secs</span></td></tr>	
	<tr><td>File Backup Quota:</td><td><span id='disp_disk'></span></td></tr>
	<tr><td>Disk usage:</td><td><span id='disp_usage'></span></td></tr>
	<tr><td>Allocated Memory:</td><td><span id='disp_mem'></span></td></tr>
	<tr><td>Allocated CPUs:</td><td>{{d["cpu"]}}</td></tr>
	<tr><td>SSH Public Key:</td><td><a href="#" id="showsshkey">View</a></td></tr>
	<tr><td>Network Connectivity Test:</td><td><a href="#" id="websocktest">Start</a></td></tr>
	<tr><td>Application Ports:</td><td><a href="#" id="openedports">View</a> | <a href="#" id="openport">Open Another</a></td></tr>
</table>

<h3>JuliaBox version:</h3>
JuliaBox version: {{d["juliaboxver"]}} <br/>
Julia versions and packages: <a href="#" class="showpackages" id="showpackages-0.3">0.3</a> | <a href="#" class="showpackages" id="showpackages-0.4">0.4</a> | <a href="#" class="showpackages" id="showpackages-0.5">0.5</a><br/>
<p>
	<br/>
	<b>Adding &amp; updating packages:</b>
	<p>
	Use Julia package manager from the terminal console (not IJulia) for package management. Since IJulia already loads
	certain packages for its working, updating those (or any package that depends on them) from within IJulia will fail.
	Packages installed by you override system installed packages.<br/>
	</p>

	<br/>
	<b>Kernel failing to initialise?</b>
	<p> 
	A conflict between system packages and those installed by you may cause errors and failures while starting notebooks.<br/>
	In such cases, you will need to reset conflicting packages to go back to using system installed packages only.<br/>
	</p>
	<a href="#" id="delpackages" class="btn btn-warning">Reset my packages <span class="glyphicon glyphicon-trash"></span></a>
</p>
<br/>

{% include "../../../www/admin_modules.tpl" %}

{% if (d["manage_containers"] or d["show_report"]) %}
    <hr/>
    <h3>System statistics{% if d["manage_containers"] %} &amp; administration{% end %}</h3>

    <table class="table">
        <tr><td>Session Statistics:</td><td><a href="#" id="showsessionstats">View</a></td></tr>
        <tr><td>Users Statistics:</td><td><a href="#" id="showuserstats">View</a></td></tr>
        <tr><td>Volume Statistics:</td><td><a href="#" id="showvolumestats">View</a></td></tr>
{% if d["manage_containers"] %}
        <tr><td>Configuration:</td><td><a href="#" id="showcfg">View</a></td></tr>
        <tr><td>Sessions:</td><td><a href="#" id="showsessions">View</a></td></tr>
        <tr><td>API Containers:</td><td><a href="#" id="showapis">View</a></td></tr>
        <tr><td>Instance Loads:</td><td><a href="#" id="showinstanceloads">View</a></td></tr>
{% end %}
    </table>
    <br/><br/>
{% end %}
</body>
</html>
