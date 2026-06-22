import click
import asyncio
from rich.console import Console
from rich.table import Table
from rich.text import Text
from datetime import datetime
import sys
import os

# Fix import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from cli.tailer
from cli.tailer.reader import LogReader

console = Console()

@click.group()
def cli():
    """LogPilot - Real-time log monitoring for teams"""
    pass

@cli.command()
def version():
    """Show LogPilot version"""
    console.print("[bold green]LogPilot[/bold green] v0.1.0")
    console.print("Real-time log anomaly detection")

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def watch(file_path):
    """Watch a log file in real-time"""
    console.print(f"[bold blue]📋 Watching:[/bold blue] {file_path}")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Time", style="dim", width=20)
    table.add_column("Line", style="white")
    
    async def tail_logs():
        reader = LogReader(file_path)
        line_count = 0
        
        async for line in reader.read_lines():
            line_count += 1
            
            if "ERROR" in line.upper() or "CRITICAL" in line.upper():
                style = "bold red"
            elif "WARNING" in line.upper():
                style = "yellow"
            elif "INFO" in line.upper():
                style = "green"
            else:
                style = "white"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            table.add_row(timestamp, Text(line, style=style))
            
            if len(table.rows) > 50:
                table.rows.pop(0)
            
            console.clear()
            console.print(f"[bold blue]📋 Watching:[/bold blue] {file_path}")
            console.print(f"[dim]Lines read: {line_count} | Press Ctrl+C to stop[/dim]\n")
            console.print(table)
    
    try:
        asyncio.run(tail_logs())
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Stopped watching logs[/yellow]")

if __name__ == "__main__":
    cli()
