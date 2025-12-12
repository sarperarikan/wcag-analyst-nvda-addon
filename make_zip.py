# -*- coding: utf-8 -*-
import zipfile
import os
import sys

addon_dir = "addon"
output_file = "WCAGAnalyst-FIXED.nvda-addon"

try:
    # Remove old file if exists
    if os.path.exists(output_file):
        os.remove(output_file)
    
    # Create new zip
    zf = zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED)
    
    for root, dirs, files in os.walk(addon_dir):
        # Skip pycache
        if '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                continue
            
            full_path = os.path.join(root, file)
            arc_name = os.path.relpath(full_path, addon_dir)
            zf.write(full_path, arc_name)
    
    zf.close()
    
    # Write result to file
    with open("result.txt", "w") as f:
        f.write(f"Created: {output_file}\n")
        f.write(f"Size: {os.path.getsize(output_file)} bytes\n")
        
        # Verify
        zf2 = zipfile.ZipFile(output_file, 'r')
        f.write(f"Files in archive: {len(zf2.namelist())}\n")
        for name in zf2.namelist():
            f.write(f"  {name}\n")
        zf2.close()
        
except Exception as e:
    with open("result.txt", "w") as f:
        f.write(f"ERROR: {str(e)}\n")
