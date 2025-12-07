"""
THE KRAKEN DREAMS - Search Dialog
A standalone dialog for searching across transcript files.

This dialog provides a simple interface for searching transcripts
without bloating the main application file.
"""

import tkinter as tk
from tkinter import ttk
import os

from ..core.theme import KRAKEN
from ..core.search import TranscriptSearcher
from ..core.config import TRANSCRIPTS_DIR


class SearchDialog:
    """
    Search dialog for finding text across all transcripts.
    
    Opens as a modal dialog with search input, results list,
    and preview of matched lines.
    """
    
    def __init__(self, parent, on_open_callback=None):
        """
        Initialize the search dialog.
        
        Args:
            parent: Parent window
            on_open_callback: Optional callback when user wants to open a file
                             Called with (filepath, line_number)
        """
        self.parent = parent
        self.on_open_callback = on_open_callback
        self.searcher = TranscriptSearcher(TRANSCRIPTS_DIR)
        self.results = []
        
        self._create_dialog()
        self._scan_transcripts()
    
    def _create_dialog(self):
        """Create the dialog window and widgets."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("🔍 Search Transcripts")
        self.dialog.geometry("700x500")
        self.dialog.configure(bg=KRAKEN['bg_dark'])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Main container
        main = tk.Frame(self.dialog, bg=KRAKEN['bg_dark'], padx=15, pady=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Search input row
        search_frame = tk.Frame(main, bg=KRAKEN['bg_dark'])
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="🔍", font=('Segoe UI', 14),
                bg=KRAKEN['bg_dark'], fg=KRAKEN['accent']).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                    font=('Segoe UI', 12),
                                    bg=KRAKEN['bg_widget'], fg=KRAKEN['text'],
                                    insertbackground=KRAKEN['text'],
                                    relief='flat', width=40)
        self.search_entry.pack(side=tk.LEFT, padx=10, ipady=5, fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', lambda e: self._do_search())
        self.search_entry.bind('<KeyRelease>', lambda e: self._on_key_release())
        
        search_btn = tk.Button(search_frame, text="Search", font=('Segoe UI', 10),
                              bg=KRAKEN['accent'], fg=KRAKEN['text_bright'],
                              activebackground=KRAKEN['accent_light'],
                              bd=0, padx=15, pady=5, cursor='hand2',
                              command=self._do_search)
        search_btn.pack(side=tk.LEFT)
        
        # Options row
        options_frame = tk.Frame(main, bg=KRAKEN['bg_dark'])
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Case sensitive", variable=self.case_var,
                      font=('Segoe UI', 9), bg=KRAKEN['bg_dark'], fg=KRAKEN['text'],
                      selectcolor=KRAKEN['bg_widget'], activebackground=KRAKEN['bg_dark'],
                      activeforeground=KRAKEN['text']).pack(side=tk.LEFT)
        
        self.word_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Whole word", variable=self.word_var,
                      font=('Segoe UI', 9), bg=KRAKEN['bg_dark'], fg=KRAKEN['text'],
                      selectcolor=KRAKEN['bg_widget'], activebackground=KRAKEN['bg_dark'],
                      activeforeground=KRAKEN['text']).pack(side=tk.LEFT, padx=15)
        
        self.status_label = tk.Label(options_frame, text="", font=('Segoe UI', 9),
                                    bg=KRAKEN['bg_dark'], fg=KRAKEN['text_dim'])
        self.status_label.pack(side=tk.RIGHT)
        
        # Results list
        results_frame = tk.Frame(main, bg=KRAKEN['bg_mid'])
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for results
        columns = ('file', 'matches', 'modified')
        self.tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=8)
        self.tree.heading('file', text='File')
        self.tree.heading('matches', text='Matches')
        self.tree.heading('modified', text='Modified')
        self.tree.column('file', width=300)
        self.tree.column('matches', width=80)
        self.tree.column('modified', width=120)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-1>', self._on_double_click)
        
        # Preview area
        preview_label = tk.Label(main, text="Preview:", font=('Segoe UI', 10, 'bold'),
                                bg=KRAKEN['bg_dark'], fg=KRAKEN['text'])
        preview_label.pack(anchor='w', pady=(10, 5))
        
        preview_frame = tk.Frame(main, bg=KRAKEN['bg_mid'])
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_text = tk.Text(preview_frame, font=('Consolas', 10),
                                   bg=KRAKEN['bg_widget'], fg=KRAKEN['text'],
                                   relief='flat', height=8, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Configure highlight tag
        self.preview_text.tag_configure('highlight', 
                                        background=KRAKEN['accent'], 
                                        foreground=KRAKEN['text_bright'])
        
        # Focus search entry
        self.search_entry.focus_set()
    
    def _scan_transcripts(self):
        """Scan transcripts directory and update status."""
        count = self.searcher.scan_transcripts()
        self.status_label.config(text=f"{count} transcripts indexed")
    
    def _on_key_release(self):
        """Handle typing in search box (live search after 3 chars)."""
        query = self.search_var.get()
        if len(query) >= 3:
            self._do_search()
    
    def _do_search(self):
        """Perform the search."""
        query = self.search_var.get().strip()
        if not query:
            return
        
        self.results = self.searcher.search(
            query,
            case_sensitive=self.case_var.get(),
            whole_word=self.word_var.get()
        )
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Populate results
        total_matches = 0
        for result in self.results:
            self.tree.insert('', tk.END, values=(
                result.filename,
                result.match_count,
                result.modified.strftime('%Y-%m-%d %H:%M')
            ))
            total_matches += result.match_count
        
        self.status_label.config(
            text=f"{total_matches} matches in {len(self.results)} files"
        )
        
        # Clear preview
        self.preview_text.delete('1.0', tk.END)
    
    def _on_select(self, event):
        """Handle selection in results tree."""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get selected result
        item = self.tree.item(selection[0])
        filename = item['values'][0]
        
        # Find the result object
        result = next((r for r in self.results if r.filename == filename), None)
        if not result:
            return
        
        # Show matches in preview
        self.preview_text.delete('1.0', tk.END)
        
        query = self.search_var.get().strip()
        for match in result.matches[:10]:  # Limit to 10 matches
            line = match['line']
            line_num = match['line_number']
            
            self.preview_text.insert(tk.END, f"Line {line_num}: ")
            
            # Highlight the search term
            if query.lower() in line.lower():
                start_idx = line.lower().find(query.lower())
                self.preview_text.insert(tk.END, line[:start_idx])
                self.preview_text.insert(tk.END, line[start_idx:start_idx+len(query)], 'highlight')
                self.preview_text.insert(tk.END, line[start_idx+len(query):])
            else:
                self.preview_text.insert(tk.END, line)
            
            self.preview_text.insert(tk.END, '\n')
        
        if len(result.matches) > 10:
            self.preview_text.insert(tk.END, f"\n... and {len(result.matches) - 10} more matches")
    
    def _on_double_click(self, event):
        """Handle double-click to open file."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        filename = item['values'][0]
        
        result = next((r for r in self.results if r.filename == filename), None)
        if result and self.on_open_callback:
            # Open at first match
            line_num = result.matches[0]['line_number'] if result.matches else 1
            self.on_open_callback(result.path, line_num)
            self.dialog.destroy()
