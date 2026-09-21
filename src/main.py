#!/usr/bin/env python3
"""
Indent — Agentic AI Coding Platform
Entry point for the terminal user interface.
"""
from tui.app import IndentCLI

def main():
    cli = IndentCLI()
    cli.run()

if __name__ == '__main__':
    main()