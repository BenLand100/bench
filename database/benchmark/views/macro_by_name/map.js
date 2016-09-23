function(doc){
    if(doc.type=='macro'){
        commitHash = null;
        if(doc.commitHash){
            commitHash = doc.commitHash;    
        }
        emit([doc.name, doc.ratVersion, commitHash], 1);
    }
}
