def load(self, *args):
    PREPARE = [
    ]
    FINISH = [
    ]

    def load(name):
        try:
            mod = __import__(
                name,
                globals(),
                locals(),
                [],
                -1
            )
        except ImportError:
            #print 'NO CONFIG %s'%name
            return
        for i in name.split('.')[1:]:
            mod = getattr(mod, i)
        prepare = getattr(mod, 'prepare', None)

        #print mod, "prepare", prepare, dir(mod)
        if prepare:
            PREPARE.append(prepare)

        finish = getattr(mod, 'finish', None)
        if finish:
            FINISH.append(finish)
    for i in args:
        load(i)
    funclist = PREPARE+list(reversed(FINISH))
    for _ in funclist:
        _(self)

    return self
