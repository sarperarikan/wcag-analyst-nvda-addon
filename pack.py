# -*- coding: utf-8 -*-
"""Simple script to create NVDA addon package."""
import zipfile
import os

addon_dir = "addon"
output_file = "wcagReporter-1.0.0.nvda-addon"

# Remove old file if exists
if os.path.exists(output_file):
    os.remove(output_file)

# Create new zip
with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(addon_dir):
        # Skip pycache
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                continue
            
            full_path = os.path.join(root, file)
            arc_name = os.path.relpath(full_path, addon_dir)
            zf.write(full_path, arc_name)

print(f"Created: {output_file}")
print(f"Size: {os.path.getsize(output_file)} bytes")

# Verify
with zipfile.ZipFile(output_file, 'r') as zf:
    print(f"Files in archive: {len(zf.namelist())}")
    for name in zf.namelist()[:15]:
        print(f"  {name}")
