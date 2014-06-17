function(doc){
    if(doc.type=='macro'){
        commitHash = null;
        if(doc.commitHash){
            commitHash = doc.commitHash;    
        }
        if(doc.info){
            for(var name in doc.info){
                if(doc.info[name].state=="completed" || doc.info[name].state=="failed"){

                    emit([name,doc.descr,doc.ratVersion,commitHash],doc.info[name]);
                }
            }
        }
    }
}
