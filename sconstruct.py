# -*- coding: utf-8 -*-
# NVDA Add-on SCons Build Script
# Based on the official NVDA add-on template

import codecs
import os
import zipfile

# Get the addon build variables
import buildVars

# Fix for translation function
def _(x):
    return x

# Re-evaluate buildVars with the _ function available
exec(open("buildVars.py", encoding="utf-8").read())

def createAddonBundle(outputPath, addonPath):
    """Create the add-on bundle (.nvda-addon file)."""
    with zipfile.ZipFile(outputPath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addonPath):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                # Skip compiled Python files
                if file.endswith(('.pyc', '.pyo')):
                    continue
                
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, addonPath)
                zf.write(filepath, arcname)
    
    return outputPath

def createManifest(manifestPath, addon_info):
    """Create the manifest.ini file from addon_info."""
    content = f"""name = {addon_info['addon_name']}
summary = {addon_info['addon_summary']}
description = {addon_info['addon_description'].split(chr(10))[0]}
author = {addon_info['addon_author']}
url = {addon_info['addon_url']}
version = {addon_info['addon_version']}
docFileName = {addon_info['addon_docFileName']}
minimumNVDAVersion = {addon_info['addon_minimumNVDAVersion']}
lastTestedNVDAVersion = {addon_info['addon_lastTestedNVDAVersion']}
"""
    with codecs.open(manifestPath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return manifestPath

def build():
    """Build the add-on package."""
    addon_info = buildVars.addon_info
    addon_name = addon_info['addon_name']
    addon_version = addon_info['addon_version']
    
    addon_path = os.path.join(os.path.dirname(__file__), 'addon')
    manifest_path = os.path.join(addon_path, 'manifest.ini')
    output_path = os.path.join(os.path.dirname(__file__), f'{addon_name}-{addon_version}.nvda-addon')
    
    print(f"Building {addon_name} version {addon_version}...")
    
    # Create/update manifest
    print("Creating manifest.ini...")
    createManifest(manifest_path, addon_info)
    
    # Create the bundle
    print("Creating add-on bundle...")
    createAddonBundle(output_path, addon_path)
    
    print(f"\nBuild complete!")
    print(f"Output: {output_path}")
    print(f"Size: {os.path.getsize(output_path) / 1024:.1f} KB")
    
    # Verify
    print("\nVerifying package contents:")
    with zipfile.ZipFile(output_path, 'r') as zf:
        names = zf.namelist()
        print(f"  Total files: {len(names)}")
        # Check for manifest
        if 'manifest.ini' in names:
            print("  ✓ manifest.ini found")
        else:
            print("  ✗ manifest.ini MISSING!")
        # Check for globalPlugins
        gp_files = [n for n in names if n.startswith('globalPlugins/')]
        print(f"  ✓ {len(gp_files)} files in globalPlugins/")

if __name__ == '__main__':
    build()
