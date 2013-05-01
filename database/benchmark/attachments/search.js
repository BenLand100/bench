split_path = window.location.pathname.split('/')
var db_name = split_path[split_path.length-4]
$db = $.couch.db(db_name);
$("#header").load("header.html");

function run_search(ratv){
        html = "<table class=\"small_table\"><thead><tr><th>RAT V</th><th>Commit hash</th><th>Descriptor</th><th>Macro</th>"+
            "<th>Mem (MB)</th><th>Time (s)</th><th>Ev (kB)</th><th>Est. ev/24hr</th><th>Est. 10k (GB)</th>"+
            "</tr></thead><tbody>";
		$("#results").append(html);
    var start_key = [ratv,null,null,null];
    var end_key   = [ratv,"zzz","zzz","zzz"];
    view_name = "benchmark/results?startkey=[";
    for(var i_key=0;i_key<start_key.length;i_key++){
        view_name += "\""+start_key[i_key]+"\"";
        if ((i_key+1)<start_key.length)
            view_name += ",";
    }
    view_name += "]&endkey=[";
    for(var i_key=0;i_key<end_key.length;i_key++){
        view_name += "\""+end_key[i_key]+"\""
        if ((i_key+1)<end_key.length)
            view_name += ",";
    }
    view_name += "]";
    $db.view(view_name, {
	    success: function(data){
		    for (i in data.rows) {
                row = data.rows[i]
                var ratv = row.key[0];
                var desc = row.key[1];
                var name = row.key[2];
                var hash = row.key[3];
                html = "<tr><td>"+ratv+"</td>";
                if (hash!=null)
                    html+= "<td>"+hash+"<td>";
                else
                    html+= "<td></td>";
                html+= "<td>"+desc+"</td>";
                html+= "<td>"+name+"</td>";
                if (row.value=={}){
                    //failed!
                    html+= "<td colspan=5 background-color=#ee3000></td>";
                }
                else{
                    //success!
                    var ev_per_day = 86400.0 / row.value["event_time"]["Total"];
                    var ev_kb = row.value["event_size"]/1024;
                    var ev_mb = ev_kb/1024.0;
                    var ev_gb = ev_mb/1024.0;
                    var mem_mb = row.value["memory_max"]/(1048576);
                    html+= "<td>"+mem_mb.toFixed(2)+"</td>";
                    html+= "<td>"+row.value["event_time"]["Total"].toFixed(2)+"</td>";
                    html+= "<td>"+ev_kb.toFixed(2)+"</td>";
                    html+= "<td>"+ev_per_day.toFixed(0)+"</td>";
                    html+= "<td>"+(ev_gb*10000.0).toFixed(2)+"</td>";
                }
                html += "</tr>";                
		        $("#results").append(html);
                console.log('append '+ratv);
            }
        },        
		error: function(e) {
		    alert('Error loading from database: ' + e + ' DB: '+db_name);
	    }
    });
        html = "</tbody></table>";
		$("#results").append(html)
    console.log('end '+ratv);
}
        


$(document).ready(function() {

	$("button#runsearch").click(function(event) { //search when search button is clicked
		$tgt = $(event.target);
		$form = $tgt.parents("form#searchform");
		$hiddenform = $tgt.parents("form#searchform");
        var ratVersion = $form.find("select#ratversion").val();

        $("#results").empty(); //empty previous search records

        for(var i in ratVersion){
            run_search(ratVersion[i]);
        }

    });

});
