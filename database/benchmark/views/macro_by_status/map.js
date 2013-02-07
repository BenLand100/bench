function(doc){
    if(doc.type=='macro'){
        if(doc._attachments){
            for(var name in doc._attachments){
                emit(doc.state,name);
            }
        }
    }
}

