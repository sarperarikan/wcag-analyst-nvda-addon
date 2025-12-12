# -*- coding: utf-8 -*-
# WCAG Analyst Add-on Build Script
# Copyright (C) 2024 Sarper Arikan

"""
Build script for WCAG Analyst NVDA add-on.
Creates a .nvda-addon file ready for installation.
"""

import os
import sys
import zipfile
import subprocess
import shutil
from pathlib import Path


def get_addon_version():
    """Extract version from manifest.ini."""
    manifest_path = Path(__file__).parent / "addon" / "manifest.ini"
    version = "1.0.0"
    
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("version"):
                    version = line.split("=")[1].strip()
                    break
    
    return version


def compile_po_files():
    """Compile .po files to .mo files using Python's msgfmt module."""
    addon_path = Path(__file__).parent / "addon"
    locale_path = addon_path / "locale"
    
    if not locale_path.exists():
        print("No locale directory found, skipping translation compilation.")
        return True
    
    success = True
    
    for lang_dir in locale_path.iterdir():
        if lang_dir.is_dir():
            messages_dir = lang_dir / "LC_MESSAGES"
            po_file = messages_dir / "nvda.po"
            mo_file = messages_dir / "nvda.mo"
            
            if po_file.exists():
                print(f"Compiling {po_file}...")
                
                try:
                    # Use Python's msgfmt module (part of standard library tools)
                    # This creates proper binary .mo files
                    import struct
                    
                    # Parse the .po file and create .mo file
                    messages = {}
                    current_msgid = None
                    current_msgstr = None
                    in_msgid = False
                    in_msgstr = False
                    
                    with open(po_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            
                            if line.startswith('msgid "'):
                                if current_msgid is not None and current_msgstr is not None:
                                    # Include header (empty msgid) - essential for charset!
                                    messages[current_msgid] = current_msgstr
                                current_msgid = line[7:-1]  # Remove 'msgid "' and trailing '"'
                                current_msgstr = None
                                in_msgid = True
                                in_msgstr = False
                            elif line.startswith('msgstr "'):
                                current_msgstr = line[8:-1]  # Remove 'msgstr "' and trailing '"'
                                in_msgid = False
                                in_msgstr = True
                            elif line.startswith('"') and line.endswith('"'):
                                # Continuation line
                                content = line[1:-1]
                                if in_msgid:
                                    current_msgid += content
                                elif in_msgstr:
                                    current_msgstr += content
                        
                        # Don't forget the last entry
                        if current_msgid is not None and current_msgstr is not None:
                            messages[current_msgid] = current_msgstr
                    
                    # Process escape sequences
                    def unescape(s):
                        return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
                    
                    messages = {unescape(k): unescape(v) for k, v in messages.items()}
                    
                    # Create .mo file (GNU gettext format)
                    # Sort keys for binary search
                    keys = sorted(messages.keys())
                    
                    # Header
                    MAGIC = 0x950412de
                    VERSION = 0
                    nstrings = len(keys)
                    
                    # Calculate offsets
                    keystart = 7 * 4  # Header size
                    valuestart = keystart + nstrings * 8
                    
                    # Build string tables
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
                    
                    # Calculate final offsets
                    kstrings_start = valuestart + nstrings * 8
                    vstrings_start = kstrings_start + len(kdata)
                    
                    # Write .mo file
                    with open(mo_file, 'wb') as out:
                        # Header
                        out.write(struct.pack('I', MAGIC))
                        out.write(struct.pack('I', VERSION))
                        out.write(struct.pack('I', nstrings))
                        out.write(struct.pack('I', keystart))
                        out.write(struct.pack('I', valuestart))
                        out.write(struct.pack('I', 0))  # hash table size
                        out.write(struct.pack('I', 0))  # hash table offset
                        
                        # Key offsets
                        for length, pos in koffsets:
                            out.write(struct.pack('I', length))
                            out.write(struct.pack('I', kstrings_start + pos))
                        
                        # Value offsets
                        for length, pos in voffsets:
                            out.write(struct.pack('I', length))
                            out.write(struct.pack('I', vstrings_start + pos))
                        
                        # String data
                        out.write(kdata)
                        out.write(vdata)
                    
                    print(f"  Created {mo_file} ({len(messages)} translations)")
                    
                except Exception as e:
                    print(f"  Error compiling {po_file}: {e}")
                    success = False
    
    return success


def build_addon():
    """Build the .nvda-addon package."""
    project_dir = Path(__file__).parent
    addon_dir = project_dir / "addon"
    
    if not addon_dir.exists():
        print("Error: addon directory not found!")
        return False
    
    # Get version for filename
    version = get_addon_version()
    output_filename = f"WCAGAnalyst-{version}.nvda-addon"
    output_path = project_dir / output_filename
    
    print(f"Building {output_filename}...")
    
    # Compile translations
    compile_po_files()
    
    # Create the zip file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                # Skip .pyc files and other unwanted files
                if file.endswith('.pyc') or file.endswith('.pyo'):
                    continue
                
                file_path = Path(root) / file
                arcname = file_path.relative_to(addon_dir)
                
                print(f"  Adding: {arcname}")
                zf.write(file_path, arcname)
    
    print(f"\nBuild complete: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    return True


def clean():
    """Clean build artifacts."""
    project_dir = Path(__file__).parent
    
    # Remove .nvda-addon files
    for addon_file in project_dir.glob("*.nvda-addon"):
        print(f"Removing: {addon_file}")
        addon_file.unlink()
    
    # Remove .mo files
    addon_dir = project_dir / "addon"
    for mo_file in addon_dir.rglob("*.mo"):
        print(f"Removing: {mo_file}")
        mo_file.unlink()
    
    # Remove __pycache__ directories
    for cache_dir in addon_dir.rglob("__pycache__"):
        print(f"Removing: {cache_dir}")
        shutil.rmtree(cache_dir)
    
    print("Clean complete.")


def show_help():
    """Show usage information."""
    print("""
WCAG Analyst Add-on Build Script

Usage: python build.py [command]

Commands:
  build   - Build the .nvda-addon package (default)
  clean   - Remove build artifacts
  help    - Show this help message

Examples:
  python build.py
  python build.py build
  python build.py clean
""")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "clean":
            clean()
        elif command == "help" or command == "--help" or command == "-h":
            show_help()
        elif command == "build":
            build_addon()
        else:
            print(f"Unknown command: {command}")
            show_help()
            sys.exit(1)
    else:
        # Default action is build
        build_addon()


if __name__ == "__main__":
    main()
