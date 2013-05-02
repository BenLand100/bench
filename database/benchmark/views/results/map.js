function(doc){
    if(doc.type=='macro'){
        commitHash = null;
        if(doc.commitHash){
            commitHast = doc.commitHash;    
        }
        if(doc.info){
            for(var name in doc.info){
                if(doc.info[name].state=="completed" || doc.info[name].state=="failed"){

                    emit([doc.ratVersion,doc.descr,name,commitHash],doc.info[name]);
                }
            }
        }
    }
}