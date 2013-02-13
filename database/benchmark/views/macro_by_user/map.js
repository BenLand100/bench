function(doc){
    if(doc.type=='macro'){
        if(doc.email){
            for(var mname in doc.info){
                if(doc.info[mname].state){
                    if(doc.info[mname].state=="completed"){
                        emit(doc.email,[doc.info[mname].state,[doc.info[mname].memory_max,doc.info[mname].event_size,doc.info[mname].event_time.Total]]);
                    }
                    else{
                        emit(doc.email,[doc.info[mname].state,0]);
                    }
                }
                else{
                    emit(doc.email,["no state!",0,0,0]);
                }
            }
        }
    }
}