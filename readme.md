# WCAG Analyst - NVDA Add-on

WCAG Analyst is a powerful NVDA add-on that analyzes focused web elements for WCAG accessibility compliance using Ollama AI models. It provides detailed reports with improvement suggestions in English and Turkish.

## Features

- **AI-Powered Analysis**: Uses local Ollama AI models for intelligent WCAG analysis
- **WCAG 2.0, 2.1, 2.2 Support**: Configurable WCAG version and conformance level (A, AA, AAA)
- **Bilingual Output**: Full support for English and Turkish analysis reports
- **Detailed Reports**: 
  - Element summary
  - Screen reader experience description
  - Issues with severity ratings (Critical, Serious, Moderate, Minor)
  - WCAG criteria references
  - Code improvement suggestions
- **Accessible Interface**: Fully compatible with screen readers
- **Easy to Use**: Simple keyboard shortcut to analyze any focused element

## Requirements

- NVDA 2023.1 or later
- [Ollama](https://ollama.ai) installed and running
- At least one Ollama model (e.g., `llama3.2`, `mistral`)

## Installation

### From Source

1. Clone this repository:
   ```bash
   git clone https://github.com/sarperarikan/wcag-analyst-nvda.git
   cd wcag-analyst-nvda
   ```

2. Build the add-on:
   ```bash
   python build.py
   ```

3. Install the generated `.nvda-addon` file by opening it with NVDA

### Manual Installation

1. Download the `.nvda-addon` file from releases
2. Open the file with NVDA to install

## Usage

### Quick Start

1. Ensure Ollama is running on your computer
2. Navigate to any web page element
3. Press **NVDA + Shift + W** to analyze the focused element
4. View the detailed WCAG analysis report

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| NVDA + Shift + W | Analyze current focused element |

### Configuration

Access settings via: **NVDA Menu → Preferences → Settings → WCAG Analyst**

#### Ollama Server Settings
- **Server URL**: Ollama server address (default: http://localhost:11434)
- **Model**: AI model to use for analysis

#### WCAG Settings
- **WCAG Version**: 2.0, 2.1, or 2.2 (default: 2.2)
- **Conformance Level**: A, AA, or AAA (default: AA)
- **Include code suggestions**: Show corrected HTML examples
- **Include severity ratings**: Show issue severity levels

#### Output Settings
- **Output Language**: Auto (uses NVDA language), English, or Turkish
- **Request Timeout**: Maximum wait time for analysis (default: 120 seconds)

#### Advanced
- **Custom System Prompt**: Override the default WCAG expert prompt

## Setting Up Ollama

1. Download and install [Ollama](https://ollama.ai)

2. Download a model:
   ```bash
   ollama pull llama3.2
   ```

3. Start Ollama (if not running as a service):
   ```bash
   ollama serve
   ```

4. Verify it's working:
   ```bash
   curl http://localhost:11434/api/tags
   ```

## Troubleshooting

### Connection Error
- Ensure Ollama is running: `ollama serve`
- Check the server URL in settings
- Use "Test Connection" button in settings

### No Models Available  
- Install a model: `ollama pull llama3.2`
- Click "Refresh Models" in settings

### Analysis Takes Too Long
- Use a smaller/faster model
- Increase timeout in settings
- Analyze simpler elements

## Project Structure

```
wcag-analyst-nvda-project/
├── addon/
│   ├── manifest.ini
│   ├── globalPlugins/
│   │   ├── wcagAnalyst.py          # Main GlobalPlugin
│   │   └── wcagAnalyst/            # Package
│   │       ├── __init__.py
│   │       ├── ollamaClient.py     # Ollama API client
│   │       ├── wcagPrompts.py      # WCAG expert prompts
│   │       ├── settingsPanel.py    # Settings UI
│   │       ├── resultDialog.py     # Result display
│   │       └── config.py           # Configuration
│   ├── locale/
│   │   ├── en/LC_MESSAGES/nvda.po
│   │   └── tr/LC_MESSAGES/nvda.po
│   └── doc/
│       ├── en/index.html
│       └── tr/index.html
├── build.py
└── readme.md
```

## Author

**Sarper Arikan**
- Email: sarperarikan@gmail.com
- Website: [sarperarikan.com](https://sarperarikan.com)

## License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [NVDA](https://www.nvaccess.org/) - The free screen reader
- [Ollama](https://ollama.ai/) - Local AI model runtime
- [W3C WCAG](https://www.w3.org/WAI/WCAG22/quickref/) - Web Content Accessibility Guidelines
