# zider Extension Installation & Keybindings Guide

---

## 🛠️ Loading the Extension

1. Open **Google Chrome**, **Microsoft Edge**, **Brave**, or **Arc**.
2. Navigate to `chrome://extensions/` (or `edge://extensions/`).
3. Toggle on **Developer mode** in the upper right corner.
4. Click **Load unpacked** (or **Load Unpacked Extension**).
5. Select the folder:
   `/home/cvsz/zworkforce/packages/zider/extension`
6. Pin the **zider** icon to your browser toolbar.

---

## ⌨️ Default Keyboard Shortcuts

| Shortcut (Windows/Linux) | Shortcut (macOS) | Action |
| :--- | :--- | :--- |
| `Ctrl+M` | `Cmd+M` | **Toggle zider Sidebar** (Open / Close) |
| `Ctrl+Shift+E` | `Cmd+Shift+E` | **Explain Selected Text** |
| `Ctrl+Shift+S` | `Cmd+Shift+S` | **Summarize Active Page / Video** |
| `Ctrl+Shift+T` | `Cmd+Shift+T` | **Translate Selection / Page** |
| `Esc` | `Esc` | **Dismiss Selection Toolbar / Close Panel** |

---

## ⚙️ Configuration & Options

Click the zider extension icon in the toolbar to open the quick settings popup:
- **Gateway Endpoint**: Default `http://127.0.0.1:8085` (can be configured to remote zWorkforce URL).
- **Default AI Model**: Select between `gpt-4o`, `claude-3-5-sonnet`, `gemini-2.0-flash`, `deepseek-r1`, `spawn-hermes-free`.
- **Selection Quick Bar**: Toggle whether the floating toolbar appears automatically when text is highlighted.
