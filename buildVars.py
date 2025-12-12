# -*- coding: utf-8 -*-
# WCAG Analyst Add-on Build Variables
# This file contains the build configuration for the NVDA add-on.

# Define translation function (used during build, actual translation happens at runtime)
def _(x):
    return x

# Add-on information
addon_info = {
    # Internal name, should not contain spaces or special characters
    "addon_name": "wcagAnalyst",
    # Human-readable name
    "addon_summary": "WCAG Analyst",
    # Detailed description
    "addon_description": "Analyzes focused web elements for WCAG accessibility using Ollama AI.",
    # Version
    "addon_version": "1.0.0",
    # Author
    "addon_author": "Sarper Arikan <sarperarikan@gmail.com>",
    # URL for documentation
    "addon_url": "https://sarperarikan.com",
    # Documentation file name
    "addon_docFileName": "index.html",
    # Minimum NVDA version
    "addon_minimumNVDAVersion": "2023.1",
    # Last tested NVDA version
    "addon_lastTestedNVDAVersion": "2024.4",
    # Update channel
    "addon_updateChannel": None,
}

# Define the python files that are the sources of your add-on.
pythonSources = [
    "addon/globalPlugins/wcagAnalyst.py",
    "addon/globalPlugins/wcagAnalyst/*.py",
]

# Files that contain strings for translation. Usually this is the list of sources.
i18nSources = pythonSources + ["buildVars.py"]

# Files excluded from the add-on package
excludedFiles = []

# Base language for the addon
# This defaults to English if not defined
# baseLanguage = "en"

# Markdown extensions for additional documentation
# markdownExtensions = []
