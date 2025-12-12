# -*- coding: utf-8 -*-
# WCAG Reporter - NVDA Global Plugin
# Copyright (C) 2024 Sarper Arikan
# Single-file implementation with full localization support

"""
WCAG Reporter - Analyzes focused web elements for WCAG accessibility using Ollama AI.
Shortcut: NVDA+Shift+W
"""

import globalPluginHandler
import globalVars
import gui
import ui
import api
import config
import wx
import threading
import os
import re
import json
import urllib.request
import urllib.error
from scriptHandler import script
from logHandler import log
import addonHandler

# Initialize translation support
# IMPORTANT: This must be called before any _() usage
addonHandler.initTranslation()

log.info("WCAG Reporter: Loading...")

# ============== CONFIGURATION ==============
confspec = {
    "ollamaUrl": "string(default='http://localhost:11434')",
    "ollamaModel": "string(default='llama3.2')",
    "wcagVersion": "string(default='2.2')",
    "wcagLevel": "string(default='AA')",
    "language": "string(default='tr')",
    "timeout": "integer(default=120)",
}

config.conf.spec["wcagReporter"] = confspec

def get_config():
    return config.conf["wcagReporter"]


# ============== OLLAMA CLIENT ==============
class OllamaError(Exception):
    pass

def ollama_chat_with_retry(url, model, messages, system_prompt=None, timeout=120, max_retries=3):
    """Send chat request to Ollama API with retry logic."""
    endpoint = f"{url.rstrip('/')}/api/chat"
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_ctx": 4096,
        }
    }
    
    if system_prompt:
        payload["messages"] = [{"role": "system", "content": system_prompt}] + messages
    
    data = json.dumps(payload).encode('utf-8')
    
    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            current_timeout = timeout + (attempt * 30)
            with urllib.request.urlopen(req, timeout=current_timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("message", {}).get("content", "")
        except urllib.error.URLError as e:
            # Translators: Connection error message with attempt count
            last_error = _("Connection error (attempt {attempt}/{max}): {error}").format(
                attempt=attempt+1, max=max_retries, error=str(e))
            log.warning(f"WCAG Reporter: {last_error}")
            import time
            time.sleep(2)
        except Exception as e:
            # Translators: API error message
            last_error = _("API error: {error}").format(error=str(e))
            break
    
    # Translators: Unknown error message
    raise OllamaError(last_error or _("Unknown error"))

def ollama_chat(url, model, messages, system_prompt=None, timeout=120):
    return ollama_chat_with_retry(url, model, messages, system_prompt, timeout)

def get_ollama_models(url, timeout=10):
    """Get available models from Ollama."""
    try:
        endpoint = f"{url.rstrip('/')}/api/tags"
        req = urllib.request.Request(endpoint)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            return [m.get("name", "") for m in result.get("models", [])]
    except:
        return []


# ============== MARKDOWN CONVERTER ==============
def convert_markdown_to_text(text):
    """Convert Markdown syntax to readable plain text for screen readers."""
    import re
    
    if not text:
        return ""
    
    # Translators: Code block start marker
    code_start = _("--- Code Start ---")
    # Translators: Code block end marker
    code_end = _("--- Code End ---")
    
    # Remove code blocks with language specifier and replace with markers
    text = re.sub(r'```[\w]*\n(.*?)```', lambda m: f'\n{code_start}\n{m.group(1)}{code_end}\n', text, flags=re.DOTALL)
    text = re.sub(r'```', '', text)  # Remove any remaining backticks
    
    # Convert markdown tables to readable format
    def convert_table(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')
        result = []
        for line in lines:
            # Skip separator lines (|---|---|)
            if re.match(r'^\|?\s*[-:]+\s*\|', line):
                continue
            # Remove leading/trailing pipes and split by pipe
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            # Join cells with tab separator
            result.append('\t'.join(cells))
        return '\n'.join(result)
    
    # Match markdown tables (lines starting with | or containing |)
    text = re.sub(r'(?:^\|.+\|$\n?)+', convert_table, text, flags=re.MULTILINE)
    
    # Also handle tables without leading pipe
    def convert_simple_table_row(match):
        line = match.group(0)
        # Skip separator lines
        if re.match(r'^\s*[-:]+\s*\|', line):
            return ''
        cells = [cell.strip() for cell in line.split('|')]
        return '\t'.join(cells)
    
    # Convert headings to readable format
    text = re.sub(r'^######\s*(.+)$', r'\n\1\n', text, flags=re.MULTILINE)
    text = re.sub(r'^#####\s*(.+)$', r'\n\1\n', text, flags=re.MULTILINE)
    text = re.sub(r'^####\s*(.+)$', r'\n\1\n', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s*(.+)$', r'\n=== \1 ===\n', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s*(.+)$', r'\n== \1 ==\n', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s*(.+)$', r'\n= \1 =\n', text, flags=re.MULTILINE)
    
    # Remove bold/italic markers but keep the text
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)  # Bold italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)      # Bold
    text = re.sub(r'__(.+?)__', r'\1', text)          # Underline bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)          # Italic
    text = re.sub(r'_(.+?)_', r'\1', text)            # Underline italic
    
    # Convert unordered lists
    text = re.sub(r'^\s*[-*+]\s+', '  • ', text, flags=re.MULTILINE)
    
    # Convert ordered lists (keep numbering)
    text = re.sub(r'^\s*(\d+)\.\s+', r'  \1. ', text, flags=re.MULTILINE)
    
    # Convert inline code to bracketed text
    text = re.sub(r'`([^`]+)`', r'[\1]', text)
    
    # Convert links: [text](url) -> text (url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
    
    # Convert horizontal rules
    text = re.sub(r'^[-*_]{3,}$', '\n' + '='*40 + '\n', text, flags=re.MULTILINE)
    
    # Remove blockquotes markers
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    
    # Clean up any remaining pipe characters from incomplete tables
    text = re.sub(r'\s*\|\s*', '  ', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+\n', '\n', text)  # Trailing spaces
    
    return text.strip()


# ============== WCAG PROMPTS ==============
SYSTEM_PROMPT_TR = """Sen bir WCAG erişilebilirlik uzmanısın. Görevin, verilen HTML elementini WCAG {version} standartlarına göre {level} seviyesinde analiz etmektir.

Analiz sonucunda şunları belirt:
1. **Tespit Edilen Sorunlar**: Her sorun için WCAG kriterini ve açıklamasını yaz
2. **Önem Derecesi**: Kritik, Yüksek, Orta, Düşük
3. **Düzeltme Önerileri**: Her sorun için somut kod önerileri
4. **Genel Değerlendirme**: Elementin erişilebilirlik durumu

Yanıtını Türkçe olarak ver. Teknik terimleri açıkla."""

SYSTEM_PROMPT_EN = """You are a WCAG accessibility expert. Your task is to analyze the given HTML element according to WCAG {version} standards at {level} conformance level.

In your analysis, include:
1. **Issues Found**: For each issue, specify the WCAG criterion and explanation
2. **Severity**: Critical, High, Medium, Low
3. **Remediation**: Specific code suggestions for each issue
4. **Overall Assessment**: Accessibility status of the element

Provide your response in English. Explain technical terms."""

def get_system_prompt(language, wcag_version, wcag_level):
    template = SYSTEM_PROMPT_TR if language == "tr" else SYSTEM_PROMPT_EN
    return template.format(version=wcag_version, level=wcag_level)

def get_analysis_prompt(html_content, context, language):
    if language == "tr":
        return f"""Aşağıdaki HTML elementini WCAG erişilebilirlik açısından analiz et:

```html
{html_content}
```

Ek Bağlam: {context}

Lütfen detaylı bir WCAG analizi yap."""
    else:
        return f"""Analyze the following HTML element for WCAG accessibility:

```html
{html_content}
```

Additional Context: {context}

Please provide a detailed WCAG analysis."""


# ============== RESULT DIALOG ==============
class WCAGResultDialog(wx.Dialog):
    """Dialog to display WCAG analysis results."""
    
    def __init__(self, parent, result, element_html):
        # Translators: Title of the analysis result dialog
        super().__init__(parent, title=_("WCAG Reporter - Analysis Result"), size=(700, 500))
        self.result = result
        self.element_html = element_html
        self.conversation = []
        
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.resultText = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.resultText.SetValue(result)
        sizer.Add(self.resultText, 1, wx.EXPAND | wx.ALL, 10)
        
        questionSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.questionEdit = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        # Translators: Placeholder text for the question input field
        self.questionEdit.SetHint(_("Ask follow-up question..."))
        self.questionEdit.Bind(wx.EVT_TEXT_ENTER, self.onAskMore)
        questionSizer.Add(self.questionEdit, 1, wx.EXPAND | wx.RIGHT, 5)
        
        # Translators: Ask button label
        askButton = wx.Button(panel, label=_("&Ask"))
        askButton.Bind(wx.EVT_BUTTON, self.onAskMore)
        questionSizer.Add(askButton, 0)
        
        sizer.Add(questionSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Translators: Copy button label
        copyButton = wx.Button(panel, label=_("&Copy"))
        copyButton.Bind(wx.EVT_BUTTON, self.onCopy)
        buttonSizer.Add(copyButton, 0, wx.RIGHT, 5)
        
        # Translators: Close button label
        closeButton = wx.Button(panel, wx.ID_CLOSE, label=_("C&lose"))
        closeButton.Bind(wx.EVT_BUTTON, self.onClose)
        buttonSizer.Add(closeButton, 0)
        
        sizer.Add(buttonSizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)
        
        panel.SetSizer(sizer)
        self.resultText.SetFocus()
        
        self.conversation = [
            {"role": "user", "content": f"HTML: {element_html}"},
            {"role": "assistant", "content": result}
        ]
    
    def onCopy(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.result))
            wx.TheClipboard.Close()
            # Translators: Message spoken when content is copied to clipboard
            ui.message(_("Copied to clipboard"))
    
    def onAskMore(self, event):
        question = self.questionEdit.GetValue().strip()
        if not question:
            return
        
        self.questionEdit.SetValue("")
        # Translators: Message spoken when waiting for response
        ui.message(_("Waiting for response..."))
        
        self.conversation.append({"role": "user", "content": question})
        
        def ask_thread():
            try:
                conf = get_config()
                response = ollama_chat(
                    url=conf["ollamaUrl"],
                    model=conf["ollamaModel"],
                    messages=self.conversation,
                    timeout=conf["timeout"]
                )
                self.conversation.append({"role": "assistant", "content": response})
                formatted_response = convert_markdown_to_text(response)
                wx.CallAfter(self.showResponse, formatted_response, question)
            except Exception as e:
                wx.CallAfter(self.showError, str(e))
        
        thread = threading.Thread(target=ask_thread, daemon=True)
        thread.start()
    
    def showResponse(self, response, question):
        """Show the response, replacing previous content."""
        # Translators: Question prefix in result display
        self.result = _("--- Question: {question} ---").format(question=question) + f"\n\n{response}"
        self.resultText.SetValue(self.result)
        self.resultText.SetInsertionPoint(0)
        # Translators: Message spoken when response is ready
        ui.message(_("Response ready"))
    
    def showError(self, error):
        """Show error message."""
        # Translators: Error message prefix
        error_text = _("Error: {error}").format(error=error)
        self.resultText.SetValue(error_text)
        ui.message(error_text)
    
    def appendResult(self, text):
        current = self.resultText.GetValue()
        self.result = current + text
        self.resultText.SetValue(self.result)
        self.resultText.SetInsertionPointEnd()
        ui.message(_("Response ready"))
    
    def onClose(self, event):
        self.Destroy()


# ============== ANALYST DIALOG (New Interface) ==============
class WCAGAnalystDialog(wx.Dialog):
    """Main WCAG Analyst dialog with two-panel interface."""
    
    def __init__(self, parent):
        # Translators: Title of the HTML Analyst dialog
        super().__init__(parent, title=_("WCAG Analyst - HTML Analysis"), size=(900, 600))
        self.conversation = []
        self._analyzing = False
        
        panel = wx.Panel(self)
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        contentSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Left panel - HTML Input
        leftPanel = wx.Panel(panel)
        leftSizer = wx.BoxSizer(wx.VERTICAL)
        
        # Translators: Label for HTML content input field
        htmlLabel = wx.StaticText(leftPanel, label=_("&HTML Content:"))
        leftSizer.Add(htmlLabel, 0, wx.ALL, 5)
        
        self.htmlInput = wx.TextCtrl(leftPanel, style=wx.TE_MULTILINE | wx.TE_RICH2)
        # Translators: Placeholder for HTML input field
        self.htmlInput.SetHint(_("Paste the HTML content to analyze here..."))
        leftSizer.Add(self.htmlInput, 1, wx.EXPAND | wx.ALL, 5)
        
        # Translators: Analyze button label
        self.analyzeBtn = wx.Button(leftPanel, label=_("&Analyze"))
        self.analyzeBtn.Bind(wx.EVT_BUTTON, self.onAnalyze)
        leftSizer.Add(self.analyzeBtn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        leftPanel.SetSizer(leftSizer)
        contentSizer.Add(leftPanel, 1, wx.EXPAND | wx.ALL, 5)
        
        # Right panel - Results
        rightPanel = wx.Panel(panel)
        rightSizer = wx.BoxSizer(wx.VERTICAL)
        
        # Translators: Label for improvements and suggestions panel
        resultLabel = wx.StaticText(rightPanel, label=_("I&mprovements and Suggestions:"))
        rightSizer.Add(resultLabel, 0, wx.ALL, 5)
        
        self.resultOutput = wx.TextCtrl(rightPanel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        # Translators: Initial text in results panel
        self.resultOutput.SetValue(_("Enter HTML content and click 'Analyze' button."))
        rightSizer.Add(self.resultOutput, 1, wx.EXPAND | wx.ALL, 5)
        
        rightPanel.SetSizer(rightSizer)
        contentSizer.Add(rightPanel, 1, wx.EXPAND | wx.ALL, 5)
        
        mainSizer.Add(contentSizer, 1, wx.EXPAND)
        
        # Bottom section - Ask More
        bottomPanel = wx.Panel(panel)
        bottomSizer = wx.BoxSizer(wx.VERTICAL)
        
        bottomSizer.Add(wx.StaticLine(bottomPanel), 0, wx.EXPAND | wx.ALL, 5)
        
        # Translators: Label for ask more section
        questionLabel = wx.StaticText(bottomPanel, label=_("Ask &More:"))
        bottomSizer.Add(questionLabel, 0, wx.LEFT | wx.TOP, 10)
        
        questionRowSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.questionInput = wx.TextCtrl(bottomPanel, style=wx.TE_PROCESS_ENTER)
        # Translators: Placeholder for follow-up question field
        self.questionInput.SetHint(_("Ask follow-up question about WCAG..."))
        self.questionInput.Bind(wx.EVT_TEXT_ENTER, self.onAskMore)
        questionRowSizer.Add(self.questionInput, 1, wx.EXPAND | wx.ALL, 5)
        
        # Translators: Ask button label
        self.askBtn = wx.Button(bottomPanel, label=_("&Ask"))
        self.askBtn.Bind(wx.EVT_BUTTON, self.onAskMore)
        self.askBtn.Enable(False)
        questionRowSizer.Add(self.askBtn, 0, wx.ALL, 5)
        
        bottomSizer.Add(questionRowSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Translators: Copy button label
        self.copyBtn = wx.Button(bottomPanel, label=_("&Copy"))
        self.copyBtn.Bind(wx.EVT_BUTTON, self.onCopy)
        buttonSizer.Add(self.copyBtn, 0, wx.ALL, 5)
        
        # Translators: Close button label
        closeBtn = wx.Button(bottomPanel, wx.ID_CLOSE, label=_("Cl&ose"))
        closeBtn.Bind(wx.EVT_BUTTON, self.onClose)
        buttonSizer.Add(closeBtn, 0, wx.ALL, 5)
        
        bottomSizer.Add(buttonSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        bottomPanel.SetSizer(bottomSizer)
        mainSizer.Add(bottomPanel, 0, wx.EXPAND)
        
        panel.SetSizer(mainSizer)
        self.htmlInput.SetFocus()
        
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)
    
    def onKeyPress(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.onClose(event)
        else:
            event.Skip()
    
    def onAnalyze(self, event):
        html_content = self.htmlInput.GetValue().strip()
        if not html_content:
            # Translators: Message when HTML content is empty
            ui.message(_("Please enter HTML content first."))
            self.htmlInput.SetFocus()
            return
        
        if self._analyzing:
            # Translators: Message when analysis is already in progress
            ui.message(_("Analysis in progress, please wait."))
            return
        
        self._analyzing = True
        self.analyzeBtn.Enable(False)
        # Translators: Message shown while analyzing
        self.resultOutput.SetValue(_("Analyzing, please wait..."))
        # Translators: Message spoken when analysis starts
        ui.message(_("Starting WCAG analysis..."))
        
        def analyze_thread():
            try:
                conf = get_config()
                system_prompt = get_system_prompt(
                    conf["language"],
                    conf["wcagVersion"],
                    conf["wcagLevel"]
                )
                # Translators: Context text for user-entered HTML
                context = _("HTML entered by user")
                user_prompt = get_analysis_prompt(html_content, context, conf["language"])
                
                result = ollama_chat(
                    url=conf["ollamaUrl"],
                    model=conf["ollamaModel"],
                    messages=[{"role": "user", "content": user_prompt}],
                    system_prompt=system_prompt,
                    timeout=conf["timeout"]
                )
                
                self.conversation = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": result}
                ]
                
                formatted_result = convert_markdown_to_text(result)
                wx.CallAfter(self.showAnalysisResult, formatted_result)
            except Exception as e:
                wx.CallAfter(self.showError, str(e))
            finally:
                self._analyzing = False
                wx.CallAfter(lambda: self.analyzeBtn.Enable(True))
        
        thread = threading.Thread(target=analyze_thread, daemon=True)
        thread.start()
    
    def showAnalysisResult(self, result):
        self.resultOutput.SetValue(result)
        self.resultOutput.SetInsertionPoint(0)
        self.askBtn.Enable(True)
        # Translators: Message spoken when analysis is complete
        ui.message(_("Analysis complete."))
        self.resultOutput.SetFocus()
    
    def showError(self, error):
        error_text = _("Error: {error}").format(error=error)
        self.resultOutput.SetValue(error_text)
        ui.message(error_text)
    
    def onAskMore(self, event):
        question = self.questionInput.GetValue().strip()
        if not question:
            # Translators: Message when question is empty
            ui.message(_("Please enter a question."))
            self.questionInput.SetFocus()
            return
        
        if not self.conversation:
            # Translators: Message when trying to ask without analysis
            ui.message(_("You must analyze first."))
            return
        
        if self._analyzing:
            # Translators: Message when operation is in progress
            ui.message(_("Operation in progress, please wait."))
            return
        
        self._analyzing = True
        self.askBtn.Enable(False)
        self.questionInput.SetValue("")
        self.resultOutput.SetValue(_("Waiting for response..."))
        # Translators: Message when sending question
        ui.message(_("Sending question..."))
        
        self.conversation.append({"role": "user", "content": question})
        
        def ask_thread():
            try:
                conf = get_config()
                response = ollama_chat(
                    url=conf["ollamaUrl"],
                    model=conf["ollamaModel"],
                    messages=self.conversation,
                    timeout=conf["timeout"]
                )
                self.conversation.append({"role": "assistant", "content": response})
                formatted_response = convert_markdown_to_text(response)
                wx.CallAfter(self.showQuestionResponse, formatted_response, question)
            except Exception as e:
                wx.CallAfter(self.showError, str(e))
            finally:
                self._analyzing = False
                wx.CallAfter(lambda: self.askBtn.Enable(True))
        
        thread = threading.Thread(target=ask_thread, daemon=True)
        thread.start()
    
    def showQuestionResponse(self, response, question):
        display_text = _("--- Question: {question} ---").format(question=question) + f"\n\n{response}"
        self.resultOutput.SetValue(display_text)
        self.resultOutput.SetInsertionPoint(0)
        # Translators: Message spoken when response is ready
        ui.message(_("Response ready."))
        self.resultOutput.SetFocus()
    
    def onCopy(self, event):
        content = self.resultOutput.GetValue()
        if content and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(content))
            wx.TheClipboard.Close()
            ui.message(_("Copied to clipboard"))
    
    def onClose(self, event):
        self.Destroy()


# ============== SETTINGS PANEL ==============
from gui.settingsDialogs import SettingsPanel

class WCAGReporterSettingsPanel(SettingsPanel):
    """Settings panel for WCAG Reporter."""
    
    @property
    def title(self):
        # Translators: Settings panel title in NVDA Preferences
        return _("WCAG Reporter")
    
    def makeSettings(self, settingsSizer):
        from gui import guiHelper
        sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        
        # Translators: Label for Ollama URL setting
        self.urlEdit = sHelper.addLabeledControl(_("Ollama &URL:"), wx.TextCtrl)
        self.urlEdit.SetValue(get_config()["ollamaUrl"])
        
        # Translators: Label for model selection
        self.modelChoice = sHelper.addLabeledControl(_("&Model:"), wx.Choice, choices=[])
        
        # Translators: Refresh models button label
        refreshBtn = sHelper.addItem(wx.Button(self, label=_("&Refresh Models")))
        refreshBtn.Bind(wx.EVT_BUTTON, self.onRefresh)
        
        versions = ["2.0", "2.1", "2.2"]
        # Translators: Label for WCAG version selection
        self.versionChoice = sHelper.addLabeledControl(_("WCAG &Version:"), wx.Choice, choices=versions)
        current_version = get_config()["wcagVersion"]
        if current_version in versions:
            self.versionChoice.SetSelection(versions.index(current_version))
        
        levels = ["A", "AA", "AAA"]
        # Translators: Label for conformance level selection
        self.levelChoice = sHelper.addLabeledControl(_("&Level:"), wx.Choice, choices=levels)
        current_level = get_config()["wcagLevel"]
        if current_level in levels:
            self.levelChoice.SetSelection(levels.index(current_level))
        
        # Translators: Language choices
        languages = [_("Turkish"), _("English")]
        lang_keys = ["tr", "en"]
        # Translators: Label for language selection
        self.langChoice = sHelper.addLabeledControl(_("&Language:"), wx.Choice, choices=languages)
        current_lang = get_config()["language"]
        if current_lang in lang_keys:
            self.langChoice.SetSelection(lang_keys.index(current_lang))
        self._langKeys = lang_keys
        
        # Translators: Label for timeout setting
        self.timeoutSpin = sHelper.addLabeledControl(_("&Timeout (sec):"), wx.SpinCtrl, min=30, max=600)
        self.timeoutSpin.SetValue(get_config()["timeout"])
        
        self._loadModels()
    
    def _loadModels(self):
        def load_thread():
            models = get_ollama_models(self.urlEdit.GetValue())
            wx.CallAfter(self._updateModels, models)
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def _updateModels(self, models):
        self.modelChoice.Clear()
        if models:
            for m in models:
                self.modelChoice.Append(m)
            current = get_config()["ollamaModel"]
            if current in models:
                self.modelChoice.SetSelection(models.index(current))
            else:
                self.modelChoice.SetSelection(0)
        else:
            # Translators: Message when no models are found
            self.modelChoice.Append(_("(No model found)"))
            self.modelChoice.SetSelection(0)
    
    def onRefresh(self, event):
        self._loadModels()
        # Translators: Message when models are refreshed
        gui.messageBox(_("Model list refreshed."), _("WCAG Reporter"))
    
    def onSave(self):
        conf = get_config()
        conf["ollamaUrl"] = self.urlEdit.GetValue()
        
        idx = self.modelChoice.GetSelection()
        if idx >= 0:
            model = self.modelChoice.GetString(idx)
            if not model.startswith("("):
                conf["ollamaModel"] = model
        
        idx = self.versionChoice.GetSelection()
        if idx >= 0:
            conf["wcagVersion"] = ["2.0", "2.1", "2.2"][idx]
        
        idx = self.levelChoice.GetSelection()
        if idx >= 0:
            conf["wcagLevel"] = ["A", "AA", "AAA"][idx]
        
        idx = self.langChoice.GetSelection()
        if idx >= 0:
            conf["language"] = self._langKeys[idx]
        
        conf["timeout"] = self.timeoutSpin.GetValue()


# ============== GLOBAL PLUGIN ==============
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    """WCAG Reporter Global Plugin."""
    
    @property
    def scriptCategory(self):
        # Translators: Script category name in Input Gestures dialog
        return _("WCAG Reporter")
    
    def __init__(self):
        super().__init__()
        
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(WCAGReporterSettingsPanel)
        
        # Create submenu under Preferences menu
        self.prefsMenu = gui.mainFrame.sysTrayIcon.preferencesMenu
        
        # Translators: Main submenu name in Preferences menu (Turkish: WCAG Analizcisi)
        self.wcagMenu = wx.Menu()
        # Translators: Submenu title in Preferences
        self.wcagMenuItem = self.prefsMenu.AppendSubMenu(
            self.wcagMenu,
            _("WCAG Analyst")
        )
        
        # Translators: Menu item for HTML Analyst
        self.analystMenuItem = self.wcagMenu.Append(
            wx.ID_ANY,
            _("&HTML Analyst"),
            _("Analyze HTML content for WCAG")
        )
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onOpenAnalyst, self.analystMenuItem)
        
        # Translators: Menu item for element analysis with shortcut
        self.elementMenuItem = self.wcagMenu.Append(
            wx.ID_ANY,
            _("&Element Analysis (NVDA+Shift+W)"),
            _("Analyze focused element for WCAG")
        )
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onAnalyze, self.elementMenuItem)
        
        # Separator
        self.wcagMenu.AppendSeparator()
        
        # Translators: Menu item for settings
        self.settingsMenuItem = self.wcagMenu.Append(
            wx.ID_ANY,
            _("&Settings"),
            _("Open WCAG Analyst settings")
        )
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onOpenSettings, self.settingsMenuItem)
        
        # Translators: Menu item for documentation
        self.docMenuItem = self.wcagMenu.Append(
            wx.ID_ANY,
            _("&Documentation"),
            _("View documentation")
        )
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onOpenDocumentation, self.docMenuItem)
        
        self._analyzing = False
        log.info("WCAG Reporter: Initialized successfully")
    
    def terminate(self):
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(WCAGReporterSettingsPanel)
        except:
            pass
        try:
            self.prefsMenu.Remove(self.wcagMenuItem)
        except:
            pass
        super().terminate()
    
    def onOpenAnalyst(self, event):
        dlg = WCAGAnalystDialog(gui.mainFrame)
        dlg.Show()
    
    def onOpenSettings(self, event):
        wx.CallAfter(gui.mainFrame._popupSettingsDialog, gui.settingsDialogs.NVDASettingsDialog, WCAGReporterSettingsPanel)
    
    def onOpenDocumentation(self, event):
        try:
            addon_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            lang = get_config()["language"]
            doc_path = os.path.join(addon_path, "doc", lang, "index.html")
            
            if not os.path.exists(doc_path):
                doc_path = os.path.join(addon_path, "doc", "tr", "index.html")
            
            if not os.path.exists(doc_path):
                doc_path = os.path.join(addon_path, "doc", "en", "index.html")
            
            if os.path.exists(doc_path):
                os.startfile(doc_path)
            else:
                # Translators: Message when documentation is not found
                ui.message(_("Documentation file not found."))
        except Exception as e:
            log.error(f"WCAG Reporter: Error opening documentation: {e}")
            # Translators: Error message when opening documentation fails
            ui.message(_("Error opening documentation: {error}").format(error=str(e)))
    
    @script(
        # Translators: Description for analyze element script
        description=_("Analyze focused element for WCAG"),
        gesture="kb:NVDA+shift+w",
        category=scriptCategory
    )
    def script_analyzeElement(self, gesture):
        self._performAnalysis()
    
    def onAnalyze(self, event):
        self._performAnalysis()
    
    def _performAnalysis(self):
        if self._analyzing:
            ui.message(_("Analysis in progress, please wait."))
            return
        
        obj = api.getNavigatorObject()
        if not obj:
            obj = api.getFocusObject()
        if not obj:
            # Translators: Message when no element is focused
            ui.message(_("No element is currently focused."))
            return
        
        html = self._extractHTML(obj)
        if not html:
            # Translators: Message when element info cannot be extracted
            ui.message(_("Could not extract element information."))
            return
        
        context = self._getContext(obj)
        
        self._analyzing = True
        # Translators: Progress message at 0%
        ui.message(_("Starting WCAG analysis... 0 percent"))
        
        def analyze_thread():
            try:
                # Translators: Progress message at 10%
                wx.CallAfter(lambda: ui.message(_("Extracting element info... 10 percent")))
                
                conf = get_config()
                system_prompt = get_system_prompt(
                    conf["language"],
                    conf["wcagVersion"],
                    conf["wcagLevel"]
                )
                user_prompt = get_analysis_prompt(html, context, conf["language"])
                
                # Translators: Progress message at 30%
                wx.CallAfter(lambda: ui.message(_("Connecting to Ollama server... 30 percent")))
                
                result = ollama_chat(
                    url=conf["ollamaUrl"],
                    model=conf["ollamaModel"],
                    messages=[{"role": "user", "content": user_prompt}],
                    system_prompt=system_prompt,
                    timeout=conf["timeout"]
                )
                
                # Translators: Progress message at 90%
                wx.CallAfter(lambda: ui.message(_("Processing response... 90 percent")))
                
                wx.CallAfter(self._showResult, result, html)
            except Exception as e:
                wx.CallAfter(self._showError, str(e))
            finally:
                self._analyzing = False
        
        thread = threading.Thread(target=analyze_thread, daemon=True)
        thread.start()
    
    def _extractHTML(self, obj):
        """Extract detailed HTML-like representation from object."""
        import controlTypes
        
        try:
            role = getattr(obj, 'role', None)
            if role is not None:
                try:
                    role_name = role.displayString if hasattr(role, 'displayString') else None
                    if not role_name:
                        role_name = getattr(obj, 'roleText', '') or role.name if hasattr(role, 'name') else str(role)
                except:
                    role_name = getattr(obj, 'roleText', 'element')
            else:
                role_name = getattr(obj, 'roleText', 'element')
            
            name = getattr(obj, 'name', '') or ''
            description = getattr(obj, 'description', '') or ''
            value = getattr(obj, 'value', '') or ''
            
            ia2_attrs = {}
            if hasattr(obj, 'IA2Attributes') and obj.IA2Attributes:
                ia2_attrs = obj.IA2Attributes
            
            state_list = []
            if hasattr(obj, 'states'):
                for state in obj.states:
                    try:
                        state_name = state.displayString if hasattr(state, 'displayString') else state.name if hasattr(state, 'name') else str(state)
                        state_list.append(state_name)
                    except:
                        pass
            
            child_count = 0
            try:
                if hasattr(obj, 'childCount'):
                    child_count = obj.childCount
            except:
                pass
            
            tag = self._guessTag(obj)
            
            html_parts = []
            # Translators: HTML comment for element info
            html_parts.append(_('<!-- Element Info -->'))
            # Translators: HTML comment showing role
            html_parts.append(_('<!-- Role: {role} -->').format(role=role_name))
            if state_list:
                # Translators: HTML comment showing states
                html_parts.append(_('<!-- States: {states} -->').format(states=", ".join(state_list)))
            if ia2_attrs:
                html_parts.append(f'<!-- IA2 Attributes: {ia2_attrs} -->')
            
            attrs = []
            attrs.append(f'role="{role_name}"')
            if name:
                escaped_name = name.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
                attrs.append(f'aria-label="{escaped_name}"')
            if description:
                escaped_desc = description.replace('"', '&quot;')[:100]
                attrs.append(f'aria-describedby="[{escaped_desc}]"')
            
            for state in state_list:
                sl = state.lower()
                if 'checked' in sl or 'işaretli' in sl:
                    attrs.append('aria-checked="true"')
                elif 'selected' in sl or 'seçili' in sl:
                    attrs.append('aria-selected="true"')
                elif 'expanded' in sl or 'genişletilmiş' in sl:
                    attrs.append('aria-expanded="true"')
                elif 'collapsed' in sl or 'daraltılmış' in sl:
                    attrs.append('aria-expanded="false"')
                elif 'required' in sl or 'gerekli' in sl:
                    attrs.append('aria-required="true"')
                elif 'invalid' in sl or 'geçersiz' in sl:
                    attrs.append('aria-invalid="true"')
                elif 'disabled' in sl or 'devre dışı' in sl:
                    attrs.append('disabled')
                elif 'readonly' in sl or 'salt okunur' in sl:
                    attrs.append('readonly')
                elif 'focusable' in sl or 'odaklanabilir' in sl:
                    attrs.append('tabindex="0"')
            
            if 'tag' in ia2_attrs:
                tag = ia2_attrs['tag']
            if 'class' in ia2_attrs:
                attrs.append(f'class="{ia2_attrs["class"]}"')
            if 'id' in ia2_attrs:
                attrs.append(f'id="{ia2_attrs["id"]}"')
            
            attr_str = ' '.join(attrs)
            content = value or name or ''
            if len(content) > 200:
                content = content[:200] + '...'
            
            html_parts.append(f'<{tag} {attr_str}>{content}</{tag}>')
            
            if child_count > 0:
                # Translators: HTML comment showing child element count
                html_parts.append(_('<!-- Child element count: {count} -->').format(count=child_count))
            
            return '\n'.join(html_parts)
            
        except Exception as e:
            log.error(f"WCAG Reporter: Error extracting HTML: {e}")
            try:
                name = getattr(obj, 'name', 'unknown') or 'unknown'
                role_text = getattr(obj, 'roleText', 'element') or 'element'
                return f'<element role="{role_text}">{name}</element>'
            except:
                # Translators: Unknown element placeholder
                return _('<element>Unknown element</element>')
    
    def _guessTag(self, obj):
        """Guess HTML tag from role."""
        import controlTypes
        role = getattr(obj, 'role', None)
        
        mapping = {
            controlTypes.Role.BUTTON: "button",
            controlTypes.Role.LINK: "a",
            controlTypes.Role.EDITABLETEXT: "input",
            controlTypes.Role.CHECKBOX: "input",
            controlTypes.Role.RADIOBUTTON: "input",
            controlTypes.Role.COMBOBOX: "select",
            controlTypes.Role.LIST: "ul",
            controlTypes.Role.LISTITEM: "li",
            controlTypes.Role.TABLE: "table",
            controlTypes.Role.HEADING: "h2",
            controlTypes.Role.GRAPHIC: "img",
            controlTypes.Role.PARAGRAPH: "p",
        }
        return mapping.get(role, "div")
    
    def _getContext(self, obj):
        """Get context information about the element."""
        parts = []
        try:
            if hasattr(obj, 'roleText') and obj.roleText:
                # Translators: Context info showing role
                parts.append(_("Role: {role}").format(role=obj.roleText))
            if hasattr(obj, 'treeInterceptor') and obj.treeInterceptor:
                # Translators: Context info for web page
                parts.append(_("Web page (Browse Mode)"))
            if hasattr(obj, 'parent') and obj.parent:
                parent_name = getattr(obj.parent, 'name', '')
                if parent_name:
                    # Translators: Context info showing parent element
                    parts.append(_("Parent element: {name}").format(name=parent_name))
        except:
            pass
        # Translators: Unknown context
        return " | ".join(parts) if parts else _("Unknown")
    
    def _showResult(self, result, html):
        formatted_result = convert_markdown_to_text(result)
        ui.message(_("Analysis complete."))
        dlg = WCAGResultDialog(gui.mainFrame, formatted_result, html)
        dlg.Show()
    
    def _showError(self, error):
        error_msg = _("Error: {error}").format(error=error)
        ui.message(error_msg)
        # Translators: Error dialog title
        title = _("WCAG Reporter Error")
        # Translators: Error dialog message
        message = _("An error occurred during analysis:\n\n{error}").format(error=error)
        gui.messageBox(message, title, wx.OK | wx.ICON_ERROR)

log.info("WCAG Reporter: Module loaded successfully")
