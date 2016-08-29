# -*- coding: utf-8 -*-

if __name__ == '__main__':
    # とりあえず動く
    import sys
    import os
    if len(sys.argv) < 2:
        sys.exit('Usage: ' + sys.argv[0] + ' ram.raw (startaddr)')
    if len(sys.argv) < 3:
        addr = 0x5000
    else:
        addr = int(sys.argv[2], 16)
    
    f = open(sys.argv[1], 'rb')
    f.seek(addr)
    
    while 1:
        if f.read(4) == '\x4E\x80\x00\x20':
            print '0x' + hex(f.tell()).lstrip('0x').rstrip('L').upper()