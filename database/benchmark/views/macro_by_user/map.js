function(doc){
    if(doc.type=='macro'){
        if(doc.email){
            for(var name in doc._attachments){
                if(doc.info[name].state=="complete"){
                    emit(doc.email,[doc.info[name].state,doc.info[name].results.event_size,doc.info[name].results.event_time,doc.info[name].results.memory_max]);
                }
                else if(doc.info[name].state=="waiting"){
                    emit(doc.email,[doc.info[name].state,0,0,0]);  
                } 
                else if(doc.state[name]=="failed"){
                    emit(doc.email,[doc.info[name].state,doc.info[name].reason,0,0]);
                }
            }
        }
    }
}