"""
main.py  --  entry point (JODI)
Run with:  python main.py
Keep every .py file of this program in the same folder as this file.
"""

from gui_app import ParserApp


def main():
    app = ParserApp()
    app.mainloop()


if __name__ == "__main__":
    main()
