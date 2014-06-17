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
            var time_headers = [];
            for(var i in data.rows){
                for(var t in data.rows[i].value['event_time']){
                    if(time_headers.indexOf(t)==-1 && t!="Total")
                        time_headers.push(t);
                }
            }
            time_headers.sort();
            time_headers.unshift("Total"); // always have the total first            
            html = "";
            html += "<tr><th>RAT V</th><th>Commit hash</th><th>Mem (MB)</th><th>Ev (kB)</th>";
            for(var t in time_headers){
                html += "<th>"+time_headers[t]+"</th>";
            }
            html += "</tr>";
            //now fill the table!
            for(var i in data.rows){                
                var vals = data.rows[i].value;
                html += "<tr>";
                if(vals["state"]=="failed"){
                    html += "<td>"+data.rows[i].key[2]+"</td>";
                    html += "<td>"+data.rows[i].key[3]+"</td>";
                    html += "<td></td><td></td>";
                    html += "<td colspan="+time_headers.length+">Macro failed</td>";
                }
                else{
                    var mem = vals["memory_max"] / _MB;
                    html += "<td>" + data.rows[i].key[2] + "</td>";
                    html += "<td>" + data.rows[i].key[3] + "</td>";
                    html += "<td>" + mem.toFixed(1) + "</td>";
                    html += "<td>" + vals["event_size"] + "</td>";
                    for(var t in time_headers){                   
                        if(time_headers[t] in vals["event_time"])
                            html += "<td>" + vals["event_time"][time_headers[t]].toPrecision(3) + "</td>";
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
        startkey: [macro, phase],
        endkey: [macro, phase, {}]
    });
    
});
