from mosaicolabs import MosaicoClient
from mosaicolabs.examples.config import MOSAICO_HOST, MOSAICO_PORT

from rich.console import Console

console = Console()

def main():
    with MosaicoClient.connect(host=MOSAICO_HOST, port=MOSAICO_PORT) as client:

        seq_list = client.list_sequences()

        for seq in seq_list:
            try:
                console.print(f"[bold] Deliting sequence called {seq}[/bold]")
                client.sequence_delete(seq)
            except Exception as e:
                console.print(f"[bold red]Error: could not delete sequence called {seq} because {e} [/bold red]")
                return 
        console.print(f"[bold]Deleted {len(seq_list)} sequences [/bold]")

if __name__ == "__main__":
    main()