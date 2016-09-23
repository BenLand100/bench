function(doc){
    if(doc.type=="templates"){
        for(var key in doc.templates){
            emit(key, doc.templates[key]);
        }
    }
}
