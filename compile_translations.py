#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compile .po files to .mo files for NVDA add-on.
This script uses pure Python to create proper binary .mo files.
"""

import os
import struct
from pathlib import Path


def compile_po_to_mo(po_path, mo_path):
    """Compile a .po file to .mo format."""
    messages = {}
    current_msgid = None
    current_msgstr = None
    in_msgid = False
    in_msgstr = False
    header_collected = False
    
    with open(po_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            if line.startswith('msgid "'):
                # Save previous entry
                if current_msgid is not None and current_msgstr is not None:
                    # Include header (empty msgid) - this is essential for charset!
                    messages[current_msgid] = current_msgstr
                current_msgid = line[7:-1]
                current_msgstr = None
                in_msgid = True
                in_msgstr = False
            elif line.startswith('msgstr "'):
                current_msgstr = line[8:-1]
                in_msgid = False
                in_msgstr = True
            elif line.startswith('"') and line.endswith('"'):
                content = line[1:-1]
                if in_msgid and current_msgid is not None:
                    current_msgid += content
                elif in_msgstr and current_msgstr is not None:
                    current_msgstr += content
        
        # Last entry
        if current_msgid is not None and current_msgstr is not None:
            messages[current_msgid] = current_msgstr
    
    # Process escape sequences
    def unescape(s):
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                next_char = s[i + 1]
                if next_char == 'n':
                    result.append('\n')
                elif next_char == 't':
                    result.append('\t')
                elif next_char == '"':
                    result.append('"')
                elif next_char == '\\':
                    result.append('\\')
                else:
                    result.append(s[i:i+2])
                i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result)
    
    messages = {unescape(k): unescape(v) for k, v in messages.items()}
    
    # Sort keys for binary search
    keys = sorted(messages.keys())
    
    # Build .mo file
    MAGIC = 0x950412de
    VERSION = 0
    nstrings = len(keys)
    
    keystart = 7 * 4
    valuestart = keystart + nstrings * 8
    
    koffsets = []
    voffsets = []
    kdata = b''
    vdata = b''
    
    for key in keys:
        kbytes = key.encode('utf-8')
        vbytes = messages[key].encode('utf-8')
        
        koffsets.append((len(kbytes), len(kdata)))
        voffsets.append((len(vbytes), len(vdata)))
        
        kdata += kbytes + b'\x00'
        vdata += vbytes + b'\x00'
    
    kstrings_start = valuestart + nstrings * 8
    vstrings_start = kstrings_start + len(kdata)
    
    with open(mo_path, 'wb') as out:
        out.write(struct.pack('I', MAGIC))
        out.write(struct.pack('I', VERSION))
        out.write(struct.pack('I', nstrings))
        out.write(struct.pack('I', keystart))
        out.write(struct.pack('I', valuestart))
        out.write(struct.pack('I', 0))
        out.write(struct.pack('I', 0))
        
        for length, pos in koffsets:
            out.write(struct.pack('I', length))
            out.write(struct.pack('I', kstrings_start + pos))
        
        for length, pos in voffsets:
            out.write(struct.pack('I', length))
            out.write(struct.pack('I', vstrings_start + pos))
        
        out.write(kdata)
        out.write(vdata)
    
    return len(messages)


if __name__ == '__main__':
    base = Path(__file__).parent / 'addon' / 'locale'
    
    for lang_dir in base.iterdir():
        if lang_dir.is_dir():
            po_file = lang_dir / 'LC_MESSAGES' / 'nvda.po'
            mo_file = lang_dir / 'LC_MESSAGES' / 'nvda.mo'
            
            if po_file.exists():
                count = compile_po_to_mo(str(po_file), str(mo_file))
                print(f"Compiled {po_file.name} -> {mo_file.name}: {count} translations")
                print(f"  Size: {mo_file.stat().st_size} bytes")
