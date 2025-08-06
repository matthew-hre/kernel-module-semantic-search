from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem
from textual.containers import Vertical
from app.modules import get_all_modules
from app.indexer import ModuleIndexer


class KernelModuleSearchApp(App):
    CSS_PATH = "../semantic_kernel_tui.css"

    def __init__(self):
        super().__init__()
        self.modules = get_all_modules()
        if not self.modules:
            self.modules = [{"config": "ERROR", "desc": "No modules found", "path": ""}]
        self.indexer = ModuleIndexer(self.modules)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Input(placeholder="Search kernel modules...", id="search_input"),
            ListView(
                *[
                    ListItem(Static(f"{m['config']}: {m['desc']}"))
                    for m in self.modules[:50]
                ],
                id="results_list",
            ),
        )
        yield Footer()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        results_widget = self.query_one("#results_list", ListView)
        results_widget.clear()

        if not query:
            for m in self.modules[:50]:
                results_widget.append(ListItem(Static(f"{m['config']}: {m['desc']}")))
        else:
            results = self.indexer.search(query)
            for mod in results:
                results_widget.append(ListItem(Static(f"{mod['config']}: {mod['desc']}")))
