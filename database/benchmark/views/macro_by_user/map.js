function(doc){
    if(doc.type=='macro'){
        emit(doc.requestedBy, doc.name);
    }
}