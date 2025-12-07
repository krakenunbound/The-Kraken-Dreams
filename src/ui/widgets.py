"""
THE KRAKEN DREAMS - UI Widget Helpers
Reusable styled widget creation functions for the Kraken theme.

These functions ensure consistent styling across all UI components
and reduce code duplication in tab implementations.
"""

import tkinter as tk
from tkinter import ttk
from ..core.theme import KRAKEN


def create_section(parent, title):
    """
    Create a styled section frame with a colored title bar.
    
    This is the standard container for grouped UI elements,
    featuring a purple header bar and dark content area.
    
    Args:
        parent: The parent widget to contain this section
        title (str): The section title (can include emoji)
        
    Returns:
        tk.Frame: The content frame (child of the section, excluding title bar)
                  Add your widgets to this returned frame.
    """
    # Outer frame with border
    frame = tk.Frame(parent, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
    
    # Title bar with distinct purple background
    title_bar = tk.Frame(frame, bg=KRAKEN['tentacle'])
    title_bar.pack(fill=tk.X)
    tk.Label(
        title_bar, 
        text=title, 
        font=('Segoe UI', 10, 'bold'), 
        bg=KRAKEN['tentacle'],
        fg=KRAKEN['text_bright'], 
        anchor='w', 
        padx=10, 
        pady=5
    ).pack(fill=tk.X)
    
    # Content area with padding
    content = tk.Frame(frame, bg=KRAKEN['bg_mid'], padx=15, pady=10)
    content.pack(fill=tk.BOTH, expand=True)
    
    return content


def create_button(parent, text, command, small=False, large=False):
    """
    Create a styled button with Kraken theme.
    
    Three sizes available:
    - small: Compact buttons for secondary actions
    - normal: Default size for standard actions  
    - large: Prominent buttons for primary actions
    
    Args:
        parent: The parent widget
        text (str): Button text (can include emoji)
        command: The function to call on click
        small (bool): Use small button style
        large (bool): Use large button style
        
    Returns:
        tk.Button: The styled button widget
    """
    if large:
        font = ('Segoe UI', 12, 'bold')
        padx, pady = 30, 12
        bg = KRAKEN['accent']
    elif small:
        font = ('Segoe UI', 9)
        padx, pady = 12, 5
        bg = KRAKEN['bg_widget']
    else:
        font = ('Segoe UI', 10)
        padx, pady = 15, 8
        bg = KRAKEN['bg_widget']
    
    btn = tk.Button(
        parent, 
        text=text, 
        font=font, 
        bg=bg, 
        fg=KRAKEN['text'],
        activebackground=KRAKEN['accent_light'], 
        activeforeground=KRAKEN['text_bright'],
        bd=0, 
        cursor='hand2', 
        padx=padx, 
        pady=pady, 
        command=command
    )
    return btn


def create_styled_label(parent, text, font_size=10, bold=False, dim=False, bright=False):
    """
    Create a styled label with Kraken theme colors.
    
    Args:
        parent: The parent widget
        text (str): Label text
        font_size (int): Font size in points
        bold (bool): Use bold font weight
        dim (bool): Use dimmed text color
        bright (bool): Use bright text color
        
    Returns:
        tk.Label: The styled label widget
    """
    weight = 'bold' if bold else 'normal'
    
    if dim:
        fg = KRAKEN['text_dim']
    elif bright:
        fg = KRAKEN['text_bright']
    else:
        fg = KRAKEN['text']
    
    return tk.Label(
        parent,
        text=text,
        font=('Segoe UI', font_size, weight),
        bg=KRAKEN['bg_dark'],
        fg=fg
    )


def create_styled_entry(parent, textvariable=None, width=25):
    """
    Create a styled text entry with Kraken theme.
    
    Args:
        parent: The parent widget
        textvariable: Optional tk.StringVar to bind
        width (int): Width in characters
        
    Returns:
        tk.Entry: The styled entry widget
    """
    entry = tk.Entry(
        parent,
        textvariable=textvariable,
        font=('Segoe UI', 10),
        bg=KRAKEN['bg_widget'],
        fg=KRAKEN['text'],
        insertbackground=KRAKEN['text'],
        relief='flat',
        width=width
    )
    return entry


def create_text_area(parent, font_family='Consolas', font_size=10, wrap=tk.WORD):
    """
    Create a styled multi-line text area with scrollbar.
    
    Args:
        parent: The parent widget
        font_family (str): Font family name
        font_size (int): Font size in points  
        wrap: Text wrapping mode (tk.WORD, tk.CHAR, tk.NONE)
        
    Returns:
        tuple: (frame, text_widget) - The container frame and text widget
    """
    frame = tk.Frame(parent, bg=KRAKEN['bg_mid'], bd=1, relief='solid')
    
    text = tk.Text(
        frame,
        font=(font_family, font_size),
        bg=KRAKEN['bg_widget'],
        fg=KRAKEN['text'],
        insertbackground=KRAKEN['text'],
        relief='flat',
        wrap=wrap,
        padx=15,
        pady=15
    )
    text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
    
    scrollbar = ttk.Scrollbar(frame, command=text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text.config(yscrollcommand=scrollbar.set)
    
    return frame, text


def create_progress_bar(parent, mode='determinate', length=300):
    """
    Create a styled progress bar.
    
    Args:
        parent: The parent widget
        mode (str): 'determinate' or 'indeterminate'
        length (int): Length in pixels
        
    Returns:
        ttk.Progressbar: The progress bar widget
    """
    return ttk.Progressbar(parent, mode=mode, length=length)
