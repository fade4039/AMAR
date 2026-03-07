"""Apple Human Interface Guidelines theme system.

Colors from Apple's HIG:
  - Dark: Elevated surfaces (#1C1C1E, #2C2C2E, #3A3A3C)
  - Light: Clean whites (#FFFFFF, #F2F2F7)
  - Accent: Apple Music red (#FC3C44)
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ThemeColors:
    bg: str
    bg_secondary: str
    bg_tertiary: str
    bg_input: str
    fg: str
    fg_secondary: str
    fg_tertiary: str
    fg_quaternary: str
    accent: str
    accent_hover: str
    accent_fg: str
    blue: str
    green: str
    orange: str
    red: str
    indigo: str
    separator: str
    separator_opaque: str
    fill: str
    fill_secondary: str
    fill_tertiary: str
    sidebar_bg: str
    sidebar_item_hover: str
    sidebar_item_selected: str
    sidebar_fg: str
    sidebar_fg_selected: str
    table_bg: str
    table_fg: str
    table_header_bg: str
    table_header_fg: str
    table_select_bg: str
    table_select_fg: str
    table_stripe: str
    log_bg: str
    log_fg: str
    progress_track: str
    progress_fill: str

    @property
    def border(self): return self.separator
    @property
    def border_focus(self): return self.accent
    @property
    def error(self): return self.red
    @property
    def success(self): return self.green
    @property
    def warning(self): return self.orange
    @property
    def tree_bg(self): return self.table_bg
    @property
    def tree_fg(self): return self.table_fg
    @property
    def tree_select_bg(self): return self.table_select_bg
    @property
    def tree_select_fg(self): return self.table_select_fg
    @property
    def log_success(self): return self.green
    @property
    def log_warning(self): return self.orange
    @property
    def log_error(self): return self.red
    @property
    def fg_disabled(self): return self.fg_quaternary
    @property
    def progress_bg(self): return self.progress_track


DARK_THEME = ThemeColors(
    bg="#1C1C1E", bg_secondary="#2C2C2E", bg_tertiary="#3A3A3C", bg_input="#1C1C1E",
    fg="#FFFFFF", fg_secondary="#98989D", fg_tertiary="#636366", fg_quaternary="#48484A",
    accent="#FC3C44", accent_hover="#FF6961", accent_fg="#FFFFFF",
    blue="#0A84FF", green="#30D158", orange="#FF9F0A", red="#FF453A", indigo="#5E5CE6",
    separator="#38383A", separator_opaque="#48484A",
    fill="#48484A", fill_secondary="#3A3A3C", fill_tertiary="#2C2C2E",
    sidebar_bg="#1C1C1E", sidebar_item_hover="#2C2C2E", sidebar_item_selected="#3A3A3C",
    sidebar_fg="#98989D", sidebar_fg_selected="#FC3C44",
    table_bg="#2C2C2E", table_fg="#FFFFFF", table_header_bg="#2C2C2E", table_header_fg="#98989D",
    table_select_bg="#3A3A3C", table_select_fg="#FFFFFF", table_stripe="#252527",
    log_bg="#161618", log_fg="#98989D",
    progress_track="#3A3A3C", progress_fill="#FC3C44",
)

LIGHT_THEME = ThemeColors(
    bg="#F2F2F7", bg_secondary="#FFFFFF", bg_tertiary="#E5E5EA", bg_input="#FFFFFF",
    fg="#000000", fg_secondary="#8E8E93", fg_tertiary="#AEAEB2", fg_quaternary="#C7C7CC",
    accent="#FC3C44", accent_hover="#E0353C", accent_fg="#FFFFFF",
    blue="#007AFF", green="#34C759", orange="#FF9500", red="#FF3B30", indigo="#5856D6",
    separator="#C6C6C8", separator_opaque="#D1D1D6",
    fill="#D1D1D6", fill_secondary="#E5E5EA", fill_tertiary="#F2F2F7",
    sidebar_bg="#F2F2F7", sidebar_item_hover="#E5E5EA", sidebar_item_selected="#DCDCE0",
    sidebar_fg="#8E8E93", sidebar_fg_selected="#FC3C44",
    table_bg="#FFFFFF", table_fg="#000000", table_header_bg="#F2F2F7", table_header_fg="#8E8E93",
    table_select_bg="#E5E5EA", table_select_fg="#000000", table_stripe="#F9F9FB",
    log_bg="#FFFFFF", log_fg="#8E8E93",
    progress_track="#E5E5EA", progress_fill="#FC3C44",
)

THEMES: Dict[str, ThemeColors] = {"dark": DARK_THEME, "light": LIGHT_THEME}

FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"
FONT_LARGE_TITLE = (FONT_FAMILY, 20, "bold")
FONT_TITLE1 = (FONT_FAMILY, 17, "bold")
FONT_TITLE2 = (FONT_FAMILY, 14, "bold")
FONT_HEADLINE = (FONT_FAMILY, 10, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_CAPTION1 = (FONT_FAMILY, 9)
FONT_CAPTION2 = (FONT_FAMILY, 8)
FONT_MONO_BODY = (FONT_MONO, 9)


def apply_theme(root, style, theme: ThemeColors) -> None:
    """Apply Apple HIG theme."""
    root.configure(bg=theme.bg)

    style.configure("TFrame", background=theme.bg)
    style.configure("Card.TFrame", background=theme.bg_secondary)
    style.configure("Secondary.TFrame", background=theme.bg_secondary)
    style.configure("Sidebar.TFrame", background=theme.sidebar_bg)

    style.configure("TLabel", background=theme.bg, foreground=theme.fg, font=FONT_BODY)
    style.configure("Secondary.TLabel", background=theme.bg, foreground=theme.fg_secondary, font=FONT_BODY)
    style.configure("Caption.TLabel", background=theme.bg, foreground=theme.fg_secondary, font=FONT_CAPTION1)
    style.configure("LargeTitle.TLabel", background=theme.bg, foreground=theme.fg, font=FONT_LARGE_TITLE)
    style.configure("Title1.TLabel", background=theme.bg, foreground=theme.fg, font=FONT_TITLE1)
    style.configure("Title2.TLabel", background=theme.bg, foreground=theme.fg, font=FONT_TITLE2)
    style.configure("Headline.TLabel", background=theme.bg, foreground=theme.fg, font=FONT_HEADLINE)
    style.configure("Accent.TLabel", background=theme.bg, foreground=theme.accent, font=FONT_HEADLINE)
    style.configure("Heading.TLabel", background=theme.bg, foreground=theme.fg, font=FONT_TITLE2)

    style.configure("Card.TLabel", background=theme.bg_secondary, foreground=theme.fg, font=FONT_BODY)
    style.configure("CardSecondary.TLabel", background=theme.bg_secondary, foreground=theme.fg_secondary, font=FONT_BODY)
    style.configure("CardHeadline.TLabel", background=theme.bg_secondary, foreground=theme.fg, font=FONT_HEADLINE)

    style.configure("Sidebar.TLabel", background=theme.sidebar_bg, foreground=theme.sidebar_fg, font=FONT_BODY)
    style.configure("SidebarSection.TLabel", background=theme.sidebar_bg, foreground=theme.fg_tertiary, font=(FONT_FAMILY, 9, "bold"))

    style.configure("TLabelframe", background=theme.bg_secondary, foreground=theme.fg, bordercolor=theme.separator)
    style.configure("TLabelframe.Label", background=theme.bg_secondary, foreground=theme.fg_secondary, font=(FONT_FAMILY, 9, "bold"))

    style.configure("TButton", background=theme.accent, foreground=theme.accent_fg, bordercolor=theme.accent, focuscolor=theme.accent, font=FONT_HEADLINE, padding=(16, 7))
    style.map("TButton", background=[("active", theme.accent_hover), ("disabled", theme.fill_secondary)], foreground=[("disabled", theme.fg_tertiary)])

    style.configure("Secondary.TButton", background=theme.bg_tertiary, foreground=theme.fg, bordercolor=theme.separator, font=FONT_BODY, padding=(14, 6))
    style.map("Secondary.TButton", background=[("active", theme.separator_opaque)])

    style.configure("Danger.TButton", background=theme.red, foreground="#FFFFFF", bordercolor=theme.red, focuscolor=theme.red, font=FONT_HEADLINE, padding=(16, 7))
    style.map("Danger.TButton", background=[("active", "#D63030"), ("disabled", theme.fill_secondary)], foreground=[("disabled", theme.fg_tertiary)])

    style.configure("SidebarItem.TButton", background=theme.sidebar_bg, foreground=theme.sidebar_fg, bordercolor=theme.sidebar_bg, focuscolor=theme.sidebar_bg, font=FONT_BODY, padding=(14, 9), anchor="w")
    style.map("SidebarItem.TButton", background=[("active", theme.sidebar_item_hover)])

    style.configure("SidebarItemActive.TButton", background=theme.sidebar_item_selected, foreground=theme.sidebar_fg_selected, bordercolor=theme.sidebar_item_selected, focuscolor=theme.sidebar_item_selected, font=(FONT_FAMILY, 10, "bold"), padding=(14, 9), anchor="w")
    style.map("SidebarItemActive.TButton", background=[("active", theme.sidebar_item_selected)])

    style.configure("TEntry", fieldbackground=theme.bg_input, foreground=theme.fg, bordercolor=theme.separator, insertcolor=theme.fg, font=FONT_BODY)
    style.map("TEntry", bordercolor=[("focus", theme.accent)], fieldbackground=[("readonly", theme.bg_secondary)])

    style.configure("TCombobox", fieldbackground=theme.bg_input, foreground=theme.fg, background=theme.bg_secondary, bordercolor=theme.separator, arrowcolor=theme.fg_secondary, font=FONT_BODY)
    style.map("TCombobox", fieldbackground=[("readonly", theme.bg_input)], bordercolor=[("focus", theme.accent)])

    style.configure("TCheckbutton", background=theme.bg_secondary, foreground=theme.fg, indicatorcolor=theme.fill, font=FONT_BODY)
    style.map("TCheckbutton", background=[("active", theme.bg_secondary)], indicatorcolor=[("selected", theme.accent)])
    style.configure("TRadiobutton", background=theme.bg_secondary, foreground=theme.fg, indicatorcolor=theme.fill, font=FONT_BODY)
    style.map("TRadiobutton", background=[("active", theme.bg_secondary)], indicatorcolor=[("selected", theme.accent)])

    style.configure("TSpinbox", fieldbackground=theme.bg_input, foreground=theme.fg, bordercolor=theme.separator, arrowcolor=theme.fg_secondary, font=FONT_BODY)

    style.configure("TNotebook", background=theme.bg, bordercolor=theme.separator)
    style.configure("TNotebook.Tab", background=theme.bg_tertiary, foreground=theme.fg_secondary, padding=[14, 6], font=FONT_HEADLINE)
    style.map("TNotebook.Tab", background=[("selected", theme.bg_secondary)], foreground=[("selected", theme.accent)])

    style.configure("Treeview", background=theme.table_bg, foreground=theme.table_fg, fieldbackground=theme.table_bg, bordercolor=theme.separator, font=FONT_BODY, rowheight=32)
    style.configure("Treeview.Heading", background=theme.table_header_bg, foreground=theme.table_header_fg, bordercolor=theme.separator, font=(FONT_FAMILY, 9, "bold"))
    style.map("Treeview", background=[("selected", theme.table_select_bg)], foreground=[("selected", theme.table_select_fg)])
    style.map("Treeview.Heading", background=[("active", theme.separator)])

    style.configure("Horizontal.TProgressbar", background=theme.progress_fill, troughcolor=theme.progress_track, bordercolor=theme.separator, thickness=6)

    style.configure("TSeparator", background=theme.separator)
    style.configure("Vertical.TScrollbar", background=theme.bg_secondary, troughcolor=theme.bg, bordercolor=theme.bg, arrowcolor=theme.fg_tertiary, width=8)
    style.map("Vertical.TScrollbar", background=[("active", theme.separator_opaque)])
