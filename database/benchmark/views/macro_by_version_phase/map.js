function(doc) {
    if(doc.type == 'macro') {
        commitHash = null;
        if(doc.commitHash) {
            commitHash = doc.commitHash;    
        }
        emit([doc.ratVersion, doc.descriptor, commitHash], doc.name);
    }
}
