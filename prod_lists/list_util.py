def class_from_mac(fname):
    class_name = fname[:-4] # remove .mac suffix
    return caps(class_name)

def caps(fname):
    fbits = fname.split('_')
    class_name = fbits[0].capitalize()
    for i in fbits[1:]:
        class_name = '%s_%s'%(class_name, i.capitalize())
    return class_name

