"""
gui_app.py  --  PART 2 of 2 : JODI (front end)

Responsibilities
    * Build the main window (follows the suggested interface of the PE)
    * One Load button for both .prod and .ptbl files
    * Keep track of which files are loaded; a failed/cancelled load never
      destroys a previously loaded file
    * Enable the Parse button only when it is allowed
    * Ask for the output name, call the parser (Louis's modules), save the
      .prsd file and show the result + solution table
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import file_handler as fh
from parser_engine import PredictiveParser, ParserSetupError, tokenize_input


class ParserApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Non-Recursive Predictive Parser")
        self.geometry("860x740")
        self.minsize(700, 600)

        # state of the loaded files
        self.productions = None
        self.table = None
        self.prod_path = None
        self.ptbl_path = None

        # widget variables
        self.prod_name_var = tk.StringVar(value="(none)")
        self.ptbl_name_var = tk.StringVar(value="(none)")
        self.loaded_var = tk.StringVar(value="LOADED: (nothing yet)")
        self.parsing_var = tk.StringVar(value="PARSING:")
        self.input_var = tk.StringVar()
        self.input_var.trace_add("write", lambda *_: self._refresh_parse_button())

        self._build_widgets()
        self._refresh_parse_button()

    # ------------------------------------------------------------------
    # building the window
    # ------------------------------------------------------------------
    @staticmethod
    def _make_tree(parent, columns, widths, height):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        for col, width in zip(columns, widths):
            tree.column(col, width=width, anchor="center", stretch=True)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return frame, tree

    def _build_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        bold = ("TkDefaultFont", 10, "bold")

        # --- row 0: productions and parse table displays ---
        top = ttk.Frame(self, padding=8)
        top.grid(row=0, column=0, sticky="nsew")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=2)

        left = ttk.Frame(top)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(left, text="Productions:", font=bold).pack(anchor="w")
        ttk.Label(left, textvariable=self.prod_name_var).pack(anchor="w")
        frame, self.prod_tree = self._make_tree(
            left, ("id", "nt", "p"), (40, 50, 150), 9)
        for col, text in zip(("id", "nt", "p"), ("ID", "NT", "P")):
            self.prod_tree.heading(col, text=text)
        frame.pack(fill="both", expand=True)

        right = ttk.Frame(top)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right, text="Parse Table:", font=bold).pack(anchor="w")
        ttk.Label(right, textvariable=self.ptbl_name_var).pack(anchor="w")
        frame, self.ptbl_tree = self._make_tree(right, ("nt",), (60,), 9)
        frame.pack(fill="both", expand=True)

        # --- row 1: loaded message + Load button ---
        mid = ttk.Frame(self, padding=(8, 0))
        mid.grid(row=1, column=0, sticky="ew")
        mid.columnconfigure(0, weight=1)
        ttk.Label(mid, textvariable=self.loaded_var,
                  font=bold).grid(row=0, column=0, sticky="w")
        ttk.Button(mid, text="Load", width=12,
                   command=self.on_load).grid(row=0, column=1, sticky="e")

        # --- row 2: input + Parse button ---
        inp = ttk.Frame(self, padding=8)
        inp.grid(row=2, column=0, sticky="ew")
        inp.columnconfigure(1, weight=1)
        ttk.Label(inp, text="INPUT", font=bold).grid(row=0, column=0, padx=(0, 6))
        entry = ttk.Entry(inp, textvariable=self.input_var)
        entry.grid(row=0, column=1, sticky="ew")
        entry.bind("<Return>", lambda _e: self.on_parse())
        self.parse_button = ttk.Button(inp, text="Parse", width=12,
                                       command=self.on_parse)
        self.parse_button.grid(row=0, column=2, padx=(6, 0))
        ttk.Label(inp, textvariable=self.parsing_var,
                  wraplength=800).grid(row=1, column=0, columnspan=3,
                                       sticky="w", pady=(8, 0))

        # --- row 3: solution table ---
        frame, self.solution_tree = self._make_tree(
            self, ("stack", "input", "action"), (250, 250, 300), 14)
        self.solution_tree.heading("stack", text="Stack")
        self.solution_tree.heading("input", text="Input Buffer")
        self.solution_tree.heading("action", text="Action")
        self.solution_tree.column("stack", anchor="e")
        self.solution_tree.column("input", anchor="e")
        self.solution_tree.column("action", anchor="w")
        frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))

    # ------------------------------------------------------------------
    # helpers that change what is shown
    # ------------------------------------------------------------------
    def _clear_solution(self):
        self.solution_tree.delete(*self.solution_tree.get_children())
        self.parsing_var.set("PARSING:")

    def _show_productions(self):
        self.prod_tree.delete(*self.prod_tree.get_children())
        for p in self.productions:
            self.prod_tree.insert("", "end",
                                  values=(p.number, p.lhs, " ".join(p.rhs)))

    def _show_table(self):
        columns = ["nt"] + self.table.terminals
        self.ptbl_tree.delete(*self.ptbl_tree.get_children())
        self.ptbl_tree.configure(columns=columns)
        self.ptbl_tree.heading("nt", text="")
        self.ptbl_tree.column("nt", width=60, anchor="center", stretch=False)
        for term in self.table.terminals:
            self.ptbl_tree.heading(term, text=term)
            self.ptbl_tree.column(term, width=55, anchor="center", stretch=True)
        for nt in self.table.nonterminals:
            row = [nt] + [self.table.lookup(nt, t) if self.table.lookup(nt, t)
                          is not None else "" for t in self.table.terminals]
            self.ptbl_tree.insert("", "end", values=row)

    def _files_ready(self):
        return (self.productions is not None and self.table is not None
                and fh.names_match(self.prod_path, self.ptbl_path))

    def _refresh_parse_button(self):
        ok = self._files_ready() and bool(self.input_var.get().strip())
        self.parse_button.state(["!disabled"] if ok else ["disabled"])

    # ------------------------------------------------------------------
    # Load button
    # ------------------------------------------------------------------
    def on_load(self):
        self._clear_solution()       # any load attempt empties the solution
        path = filedialog.askopenfilename(
            title="Load a productions (.prod) or parse table (.ptbl) file",
            filetypes=[("Grammar files", "*.prod *.ptbl"),
                       ("Productions", "*.prod"),
                       ("Parse table", "*.ptbl"),
                       ("All files", "*.*")])
        if not path:                 # cancelled: keep what was loaded before
            self._refresh_parse_button()
            return

        extension = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)
        try:
            if extension == ".prod":
                productions = fh.load_productions(path)
                self.productions, self.prod_path = productions, path
                self.prod_name_var.set(name)
                self._show_productions()
            elif extension == ".ptbl":
                table = fh.load_parse_table(path)
                self.table, self.ptbl_path = table, path
                self.ptbl_name_var.set(name)
                self._show_table()
            else:
                raise fh.FileFormatError(
                    "Unsupported file type. Please choose a .prod or .ptbl file.")
            self.loaded_var.set("LOADED: " + name)
        except fh.FileFormatError as err:
            messagebox.showerror("Invalid file",
                                 "%s\n\nThe previously loaded file (if any) "
                                 "is still in use." % err)

        if (self.productions is not None and self.table is not None
                and not self._files_ready()):
            self.parsing_var.set("PARSING: The parse table and the productions "
                                 "file must have the same file name.")
        self._refresh_parse_button()

    # ------------------------------------------------------------------
    # Parse button
    # ------------------------------------------------------------------
    def on_parse(self):
        if str(self.parse_button.cget("state")) == "disabled":
            return
        outname = simpledialog.askstring(
            "Output file", "Enter the output file name (no extension):",
            parent=self)
        if outname is None:
            return
        outname = fh.sanitize_output_name(outname)
        if not outname:
            messagebox.showwarning("Output file", "Please type an output name.")
            return

        try:
            parser = PredictiveParser(self.productions, self.table)
        except ParserSetupError as err:
            self._clear_solution()
            messagebox.showerror("Grammar problem", str(err))
            return

        result = parser.parse(tokenize_input(self.input_var.get()))

        out_path = fh.build_output_path(outname, self.prod_path)
        try:
            fh.write_solution(out_path, result.steps)
        except fh.FileFormatError as err:
            messagebox.showerror("Output file", str(err))
            return

        self.solution_tree.delete(*self.solution_tree.get_children())
        for row in result.steps:
            self.solution_tree.insert("", "end", values=row)
        self.parsing_var.set("PARSING: %s. Please see %s." % (
            "Valid" if result.valid else "Invalid", os.path.basename(out_path)))
