split_path = window.location.pathname.split('/')
var db_name = split_path[split_path.length-4]
$db = $.couch.db(db_name);
$("#header").load("header.html");

$(document).ready(function() {

	$("button#post_doc").click(function(event) { //search when search button is clicked
		$tgt = $(event.target);
		$form = $tgt.parents("form#macroform");
		$hiddenform = $tgt.parents("form#hiddenform");
	    var email = $form.find("input#email").val();
	    var descr = $form.find("input#descr").val();
        var ratVersion = $form.find("input#ratversion").val();
        var commitHash = $form.find("input#commit_hash").val();
        var attachment_list = '';
        
        var macroInfo = {}
        
        var x=document.getElementById("macroform");
        fileList = [];
        for (var i=0;i<x.length;i++)
        {
            if(x.elements[i].files){
                $attachment = x.elements[i]
                for(var j=0;j<x.elements[i].files.length;j++){
                    console.log(x.elements[i].files[j].name);
                    fileList.push(x.elements[i].files[j].name);
                    macroInfo[x.elements[i].files[j].name] = {}
                    macroInfo[x.elements[i].files[j].name]['state'] = 'waiting';
//                    attachment_list += x.elements[i].files[j].name) + ' ';
                }
            }
        }
        console.log(fileList);
        console.log(fileList.length);
        var badType=false;
        for(var i=0;i<fileList.length;i++){
            var attachmentType = fileList[i].split('.').pop()
            console.log(fileList[i] + ' ... '  + attachmentType);
            attachment_list = attachment_list + fileList[i] + '\n';
            if(attachmentType!='mac'){
                badType=true;
                console.log(attachmentType);
            }
        }
        console.log('here');
        if(fileList.length==0 || badType==true)
            alert("Must specify valid (.mac) attachments");
        else if(!email || email.length==0 || email.indexOf("@")==-1)
            alert("Must specify a valid email address");
        else if(!descr || descr.length==0 || descr.indexOf(" ")!=-1)
            alert("Descriptor must be a single word (e.g. folder name)");
        else if(!ratVersion || ratVersion.length==0 || ratVersion=="none")
            alert("Must specify a RAT version");
        else{
            
            console.log('else?');
            console.log($attachment.files);
            itemID = $.couch.newUUID();

            bench_doc = {"_id":itemID,
                         "email":email,
                         "descr":descr,
                         "ratVersion":ratVersion,                
                         "type":"macro",
                         "info":macroInfo}
            if(commitHash.length!=0)
                bench_doc["commitHash"]=commitHash;

            $.couch.db(db_name).saveDoc(bench_doc,{
                success: function(){      
                    
                    html = '<td><input type="hidden" name="_id"></td>' + 
                        '<td><input type="hidden" name="_rev"></td>';
                    $form.append(html);
                    
                    $.couch.db(db_name).openDoc(itemID, {        
                        success: function(doc){
                            // Get saved info, then add attachment to item
                            $form.find('input[name="_id"]').val(doc._id);
                            $form.find('input[name="_rev"]').val(doc._rev);
                            
                            var data = {};
                            $.each($form.find('input[type="hidden"]').serializeArray(), function(i, field) {
                                data[field.name] = field.value;
                            });
                            
                            $form.find('input[type="file"]').each(function() {
                                data[this.name] = this.value; // file inputs need special handling
                            });
                            
                            $form.ajaxSubmit({
                                url:  "/" + db_name + "/" + doc._id,
                                success: function(response){
                                    if(fileList.length<10)
                                        alert("Benchmarking request for:\n"+attachment_list+"has been made");
                                    else
                                        alert("Benchmarking request for "+fileList.length+" macros has been made");
//                                    $form.find('input[name="_attachment"]').val();
                                }
                            });
                        }
                    });
                }
            });
        }
    });
}); 
