function(doc){
    if(doc.type=='macro'){
        emit(doc.state, doc.name);
    }
}

