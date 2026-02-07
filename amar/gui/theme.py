"""Theme system with dark/light mode toggle.

Neutral gray palette with Apple Music-inspired red accent:
  - Dark: neutral grays (#1e1e1e) with soft red accent (#e8555d)
  - Light: clean whites (#f8f8f8) with bold red accent (#dc3545)
  - Tabs use accent-colored TEXT on neutral backgrounds (not red bg)
  - Tree selection uses subtle gray highlight (not red)
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ThemeColors:
    # Core surface colors
    bg: str                # Main window / frame background
    bg_secondary: str      # Secondary panels, cards
    bg_input: str          # Entry / input fields background
    fg: str                # Primary text
    fg_secondary: str      # Secondary / muted text
    fg_disabled: str       # Disabled text

    # Accent - Apple Music gradient
    accent: str            # Primary accent (Apple Music red/pink)
    accent_hover: str      # Accent hover state
    accent_fg: str         # Text on accent background

    # Semantic colors
    success: str
    warning: str
    error: str

    # Borders / separators
    border: str
    border_focus: str

    # Treeview / list
    tree_bg: str
    tree_fg: str
    tree_select_bg: str
    tree_select_fg: str
    tree_stripe: str       # Alternating row color

    # Log panel
    log_bg: str
    log_fg: str
    log_success: str
    log_warning: str
    log_error: str

    # Progress bar
    progress_bg: str
    progress_fill: str

    # Tab
    tab_bg: str
    tab_selected_bg: str
    tab_fg: str
    tab_selected_fg: str


DARK_THEME = ThemeColors(
    bg="#1e1e1e",
    bg_secondary="#252526",
    bg_input="#2d2d2d",
    fg="#d4d4d4",
    fg_secondary="#858585",
    fg_disabled="#4a4a4a",

    accent="#e8555d",
    accent_hover="#f06e75",
    accent_fg="#ffffff",

    success="#3ddc84",
    warning="#ffb74d",
    error="#ef5350",

    border="#3c3c3c",
    border_focus="#e8555d",

    tree_bg="#1e1e1e",
    tree_fg="#d4d4d4",
    tree_select_bg="#3c3c3c",
    tree_select_fg="#ffffff",
    tree_stripe="#232323",

    log_bg="#181818",
    log_fg="#c0c0c0",
    log_success="#3ddc84",
    log_warning="#ffb74d",
    log_error="#ef5350",

    progress_bg="#2d2d2d",
    progress_fill="#e8555d",

    tab_bg="#252526",
    tab_selected_bg="#1e1e1e",
    tab_fg="#858585",
    tab_selected_fg="#e8555d",
)

LIGHT_THEME = ThemeColors(
    bg="#f8f8f8",
    bg_secondary="#ffffff",
    bg_input="#ffffff",
    fg="#1a1a1a",
    fg_secondary="#71717a",
    fg_disabled="#a1a1aa",

    accent="#dc3545",
    accent_hover="#c82333",
    accent_fg="#ffffff",

    success="#198754",
    warning="#cc7a00",
    error="#dc3545",

    border="#e4e4e7",
    border_focus="#dc3545",

    tree_bg="#ffffff",
    tree_fg="#1a1a1a",
    tree_select_bg="#e4e4e7",
    tree_select_fg="#1a1a1a",
    tree_stripe="#fafafa",

    log_bg="#ffffff",
    log_fg="#1a1a1a",
    log_success="#198754",
    log_warning="#cc7a00",
    log_error="#dc3545",

    progress_bg="#e4e4e7",
    progress_fill="#dc3545",

    tab_bg="#f0f0f0",
    tab_selected_bg="#ffffff",
    tab_fg="#71717a",
    tab_selected_fg="#dc3545",
)

THEMES: Dict[str, ThemeColors] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}


def apply_theme(root, style, theme: ThemeColors) -> None:
    """Apply a ThemeColors to the root window and ttk Style."""
    import tkinter as tk

    # Root window
    root.configure(bg=theme.bg)

    # --- ttk Style configuration ---

    # TFrame
    style.configure("TFrame", background=theme.bg)
    style.configure("Secondary.TFrame", background=theme.bg_secondary)

    # TLabel
    style.configure("TLabel", background=theme.bg, foreground=theme.fg)
    style.configure("Secondary.TLabel", background=theme.bg, foreground=theme.fg_secondary)
    style.configure("Accent.TLabel", background=theme.accent, foreground=theme.accent_fg)

    # TLabelframe
    style.configure(
        "TLabelframe",
        background=theme.bg_secondary,
        foreground=theme.fg,
        bordercolor=theme.border,
    )
    style.configure(
        "TLabelframe.Label",
        background=theme.bg_secondary,
        foreground=theme.accent,
        font=("Segoe UI", 9, "bold"),
    )

    # TButton - Apple Music accent
    style.configure(
        "TButton",
        background=theme.accent,
        foreground=theme.accent_fg,
        bordercolor=theme.accent,
        focuscolor=theme.accent,
        font=("Segoe UI", 9, "bold"),
        padding=(12, 6),
    )
    style.map(
        "TButton",
        background=[
            ("active", theme.accent_hover),
            ("disabled", theme.fg_disabled),
        ],
        foreground=[
            ("disabled", theme.bg),
        ],
    )

    # Secondary button style (less prominent)
    style.configure(
        "Secondary.TButton",
        background=theme.bg_secondary,
        foreground=theme.fg,
        bordercolor=theme.border,
    )
    style.map(
        "Secondary.TButton",
        background=[("active", theme.border)],
    )

    # TEntry
    style.configure(
        "TEntry",
        fieldbackground=theme.bg_input,
        foreground=theme.fg,
        bordercolor=theme.border,
        insertcolor=theme.fg,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", theme.border_focus)],
        fieldbackground=[("readonly", theme.bg_secondary)],
    )

    # TCombobox
    style.configure(
        "TCombobox",
        fieldbackground=theme.bg_input,
        foreground=theme.fg,
        background=theme.bg_secondary,
        bordercolor=theme.border,
        arrowcolor=theme.fg_secondary,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", theme.bg_input)],
        bordercolor=[("focus", theme.border_focus)],
    )

    # TCheckbutton
    style.configure(
        "TCheckbutton",
        background=theme.bg_secondary,
        foreground=theme.fg,
        indicatorcolor=theme.bg_input,
    )
    style.map(
        "TCheckbutton",
        background=[("active", theme.bg_secondary)],
        indicatorcolor=[("selected", theme.accent)],
    )

    # TRadiobutton
    style.configure(
        "TRadiobutton",
        background=theme.bg_secondary,
        foreground=theme.fg,
        indicatorcolor=theme.bg_input,
    )
    style.map(
        "TRadiobutton",
        background=[("active", theme.bg_secondary)],
        indicatorcolor=[("selected", theme.accent)],
    )

    # TSpinbox
    style.configure(
        "TSpinbox",
        fieldbackground=theme.bg_input,
        foreground=theme.fg,
        bordercolor=theme.border,
        arrowcolor=theme.fg_secondary,
    )

    # TNotebook (tabs)
    style.configure(
        "TNotebook",
        background=theme.bg,
        bordercolor=theme.border,
        tabmargins=[2, 5, 2, 0],
    )
    style.configure(
        "TNotebook.Tab",
        background=theme.tab_bg,
        foreground=theme.tab_fg,
        padding=[14, 6],
        font=("Segoe UI", 9, "bold"),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", theme.tab_selected_bg)],
        foreground=[("selected", theme.tab_selected_fg)],
        expand=[("selected", [1, 1, 1, 0])],
    )

    # Treeview
    style.configure(
        "Treeview",
        background=theme.tree_bg,
        foreground=theme.tree_fg,
        fieldbackground=theme.tree_bg,
        bordercolor=theme.border,
        font=("Segoe UI", 9),
    )
    style.configure(
        "Treeview.Heading",
        background=theme.bg_secondary,
        foreground=theme.fg,
        bordercolor=theme.border,
        font=("Segoe UI", 9, "bold"),
    )
    style.map(
        "Treeview",
        background=[("selected", theme.tree_select_bg)],
        foreground=[("selected", theme.tree_select_fg)],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", theme.border)],
    )

    # Heading label (large bold accent text for section headers)
    style.configure(
        "Heading.TLabel",
        background=theme.bg,
        foreground=theme.accent,
        font=("Segoe UI", 14, "bold"),
    )

    # Card frame (raised secondary background for card-like sections)
    style.configure(
        "Card.TFrame",
        background=theme.bg_secondary,
        relief="flat",
    )

    # Danger button (for destructive actions like Cancel, Remove)
    style.configure(
        "Danger.TButton",
        background=theme.error,
        foreground="#ffffff",
        bordercolor=theme.error,
        focuscolor=theme.error,
        font=("Segoe UI", 9, "bold"),
        padding=(12, 6),
    )
    style.map(
        "Danger.TButton",
        background=[
            ("active", "#d32f2f"),
            ("disabled", theme.fg_disabled),
        ],
        foreground=[
            ("disabled", theme.bg),
        ],
    )

    # Horizontal.TProgressbar — thicker bar for better visibility
    style.configure(
        "Horizontal.TProgressbar",
        background=theme.progress_fill,
        troughcolor=theme.progress_bg,
        bordercolor=theme.border,
        thickness=14,
    )

    # Treeview row height
    style.configure("Treeview", rowheight=28)

    # TSeparator
    style.configure("TSeparator", background=theme.border)

    # TScrollbar
    style.configure(
        "Vertical.TScrollbar",
        background=theme.bg_secondary,
        troughcolor=theme.bg,
        bordercolor=theme.border,
        arrowcolor=theme.fg_secondary,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", theme.border)],
    )
