# -*- coding: utf-8 -*-
"""Quick script to create NVDA addon package."""
import zipfile
import os

addon_dir = "addon"
output_file = "WCAGAnalyst-1.0.0.nvda-addon"

# Remove old file if exists
if os.path.exists(output_file):
    os.remove(output_file)
    print(f"Removed old {output_file}")

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
            print(f"Added: {arc_name}")

print(f"\nCreated: {output_file}")
print(f"Size: {os.path.getsize(output_file)} bytes")

# Verify
print("\nVerifying ZIP contents:")
with zipfile.ZipFile(output_file, 'r') as zf:
    for name in zf.namelist()[:10]:
        print(f"  {name}")
    print(f"  ... and {len(zf.namelist())} files total")
