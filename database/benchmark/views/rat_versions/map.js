function(doc){
    if(doc.type=="tags"){
        for(var i in doc.versions){
            emit(doc.versions[i], null);
        }
    }
}
