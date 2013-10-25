split_path = window.location.pathname.split('/')
var db_name = split_path[split_path.length-4]
$db = $.couch.db(db_name);
$("#header").load("header.html");

// some guideline levels
var warn_size = 1024; //GB
var error_size = 5 * 1024; //GB
var warn_time = 1800; //CPU hours, approx 100 runs
var error_time = 9000; //CPU hours, approx 500 runs

function run_search_versions(){

    var ratVersion = $main_form.find("select#ratversion").val();
    var success = $main_form.find("input#success")[0].checked;
    var failed = $main_form.find("input#failed")[0].checked;        

    $("#results").empty(); //empty previous search records
    html = "<tr><th>RAT V</th><th>Commit hash</th><th>Descriptor</th><th>Macro</th>"+
        "<th>Mem (MB)</th><th>Time (s)</th><th>Ev (kB)</th><th>Events/run (20hr)</th>"+
        "<th>Requested events</th><th>Total runs</th><th>CPU hours</th><th>Expected data (GB)</th>"+
        "<th>Amend event request</th></tr></thead>";
	$("#results").append(html);
    
    run_search(ratVersion,success,failed);
    
}

function run_search(ratv,show_s,show_f){

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
                html = "";
                if (row.value["state"]=="failed"){
                    if (show_f != true)
                        continue;
                    html += "<tr class=\"failed\">";
                }
                else{
                    if (show_s != true)
                        continue;
                    html += "<tr class=\"success\">";
                }
                html += "<td>"+ratv+"</td>";
                if (hash!=null)
                    html+= "<td>"+hash+"</td>";
                else
                    html+= "<td></td>";
                html+= "<td>"+desc+"</td>";
                html+= "<td><a href=\"macro.html?macro="+name+"&phase="+desc+"\">"+name+"</a></td>";
                if (row.value["state"]=="failed"){
                    //failed!
                    html+= "<td colspan=10 background=#ee3000>macro failed</td>";
                }
                else{
                    //success!
                    var ev_kb = row.value["event_size"]/1024;
                    var mem_mb = row.value["memory_max"]/(1048576);
                    var event_time = row.value["event_time"]["Total"];
                    //expect 20hr runs
                    var ev_per_run = 72000.0 / event_time;
                    var n_run = "N/A";
                    var cpu_hours = "N/A";
                    var data_size_gb = "N/A";                    
                    var requested = "";
                    //check if there is a known requested amount                    
                    if("requested" in row.value){
                        //yes, fill table with results from requested values
                        requested = row.value["requested"].toExponential(2);
                        n_run = (requested / ev_per_run).toFixed(1);
                        cpu_hours = (event_time * requested / 3600).toFixed(1);
                        data_size_gb = (ev_kb * requested / (1024.0*1024.0)).toFixed(2);
                    }
                    var state = "success";
                    if(cpu_hours > error_time || data_size_gb > error_size)
                        state = "noway";
                    else if(cpu_hours > warn_time || data_size_gb > warn_size)
                        state = "doublecheck"
                    html+= "<td class="+state+">"+mem_mb.toFixed(2)+"</td>";
                    html+= "<td class="+state+">"+row.value["event_time"]["Total"].toFixed(2)+"</td>";
                    html+= "<td class="+state+">"+ev_kb.toFixed(2)+"</td>";
                    html+= "<td class="+state+">"+ev_per_run.toFixed(0)+"</td>";
                    html+= "<td class="+state+">"+requested+"</td>";
                    html+= "<td class="+state+">"+n_run+"</td>";
                    html+= "<td class="+state+">"+cpu_hours+"</td>";
                    html+= "<td class="+state+">"+data_size_gb+"</td>";
                    //input textbox with id of docid._.infokey
                    textbox_id = row.id+"._."+row.key[2]
                    html+= "<td class="+state+"><input type=\"text\" name=\"event_request_box\" id=\""+textbox_id+"\"><td class="+state+">";
                    html+= "<td class="+state+"><button type=\"button\" id=run_request onClick=\"submit_event_request()\">Amend</button></td>"
                    //on enter key doesn't work yet
                    /*$(textbox_id).keyup(function(event){
                        if(event.keyCode == 13){
                            console.log("HELLO from textbox "+textbox_id);
                        }
                    });*/
                }
                html += "</tr>";                
		        $("#results").append(html);
            }
        },        
		error: function(e) {
		    alert('Error loading from database: ' + e + ' DB: '+db_name);
	    }
    });
}

function submit_event_request(){    
    var to_update_list = {};//dict of dicts
    var $requestform = document.getElementById("requestform");
    var event_requests = $requestform.getElementsByTagName("input");
    for(var i=0;i<event_requests.length;i++){
        if(!event_requests[i].value)
            continue
        else{
            var doc_id = event_requests[i].id.split("._.")[0];
            var sub_id = event_requests[i].id.split("._.")[1];
            if(doc_id in to_update_list){
            }
            else{
                to_update_list[doc_id] = {};
            }
            if(!isNumber(event_requests[i].value))
                alert("Value for "+doc_id+" "+sub_id+": "+event_requests[i].value+" is not a number");
            else
                to_update_list[doc_id][sub_id] = parseFloat(event_requests[i].value);
        }
    }
    //bulk fetch not possible, run a get and submit on each doc
    console.log(to_update_list);
    var n_update = 0;
    for(var doc_id in to_update_list){
        if(to_update_list[doc_id]=={})
            continue;
        n_update++;
        $db.openDoc(doc_id , {
            success: function(data){
                //ammend the requirements field
                for(var macro in to_update_list[doc_id]){
                    data['info'][macro]['requested'] = to_update_list[doc_id][macro];
                }
                $db.saveDoc(data , {
                    success: function(data){
                        //do nothing, for now
                    }
                });
            }
        });
    }
    //finally, reload the document (using same search parameters)
    if(n_update!=0)
        run_search_versions();
}

function isNumber(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}

$(document).ready(function() {

    $("button#runsearch").click(function(event) { //search when search button is clicked
	    $tgt = $(event.target);
        $main_form = $tgt.parents("form#searchform");
        console.log($main_form);
        run_search_versions();
    });

});
