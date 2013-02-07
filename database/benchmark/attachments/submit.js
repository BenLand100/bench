split_path = window.location.pathname.split('/')
var db_name = split_path[split_path.length-4]
$db = $.couch.db(db_name);
$("#header").load("header.html");

$(document).ready(function() {

	$("button#post_doc").click(function(event) { //search when search button is clicked
		$tgt = $(event.target);
		$form = $tgt.parents("form#macroform");
	    var email = $form.find("input#email").val();
        var ratVersion = $form.find("select#ratversion").val();
        var attachment = $form.find("input#_attachments").val();

        var attachmentType = attachment.split('.').pop()

        if(!attachment || attachment.length==0 || attachmentType!='mac')
            alert("Must specify a valid (.mac) attachment");
        else if(!email || email.length==0 || email.indexOf("@")==-1)
            alert("Must specify a valid email address");
        else if(!ratVersion || ratVersion.length==0 || ratVersion=="none")
            alert("Must specify a RAT version");
        else{

            itemID = $.couch.newUUID();

            $.couch.db(db_name).saveDoc({
                "_id": itemID,
                "email":email,
                "ratVersion":ratVersion,
                "type":"macro",
                "state":"waiting"
            }, {
                success: function(){      
                    
                    html = '<td><input type="hidden" name="_rev"/></td>' +
                        '<td><input type="hidden" name="_id"/></td>';
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
                                    alert("Benchmarking request for "+attachment+" has been made");
                                    $form.find('input[name="_attachment"]').val()
                                }
                            });
                        }
                    });
                }
            });
        }
    });
}); 
