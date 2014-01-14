split_path = window.location.pathname.split('/')
var db_name = split_path[split_path.length-4]
$db = $.couch.db(db_name);
$("#header").load("header.html");

/* read a query string parameter */
get_parameter_by_name = function(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regexS = "[\\?&]" + name + "=([^&#]*)";
    var regex = new RegExp(regexS);
    var results = regex.exec(window.location.href);
    if(results == null) return null;
    else return decodeURIComponent(results[1].replace(/\+/g, " "));
};

_MB = 1024.0*1024.0;

$(document).ready(function() {
    var macro = get_parameter_by_name('macro');
    var phase = get_parameter_by_name('phase');
    var view_name = "benchmark/results_by_macro";    
    $db.view(view_name, {
        success: function(data){     
            $("#macrohead").append("<h2>"+macro+"</h2>")
            $("#results").empty(); //empty previous search records
            // create the headers on the fly
            var time_headers = ["Total"]; // always have the total first            
            for(var i in data.rows){
                for(var t in data.rows[i].value[1]['event_time']){
                    if(time_headers.indexOf(t)==-1)
                        time_headers.push(t);
                }
            }
            html = "";
            html += "<tr><th>RAT V</th><th>Mem (MB)</th><th>Ev (kB)</th>";
            for(var t in time_headers){
                html += "<th>"+time_headers[t]+"</th>";
            }
            html += "</tr>";
            //now fill the table!
            for(var i in data.rows){                
                var vals = data.rows[i].value;
                html += "<tr>";
                if(vals[1]["state"]=="failed"){
                    html += "<td>"+vals[0]+"</td>";
                    html += "<td></td><td></td>";
                    html += "<td colspan="+time_headers.length+">Macro failed</td>";
                }
                else{
                    var mem = vals[1]["memory_max"] / _MB;
                    html += "<td>" + vals[0] + "</td>";
                    html += "<td>" + mem.toFixed(1) + "</td>";
                    html += "<td>" + vals[1]["event_size"] + "</td>";
                    for(var t in time_headers){                   
                        if(time_headers[t] in vals[1]["event_time"])
                            html += "<td>" + vals[1]["event_time"][time_headers[t]] + "</td>";
                        else
                            html += "<td>" + "N/A" + "</td>";
                    }
                }
                html += "</tr>";
            }
	        $("#results").append(html);
        },
        error: function(e){
            alert('Error loading from database: '+e);
        },
        key: [macro, phase]
    });
    
});