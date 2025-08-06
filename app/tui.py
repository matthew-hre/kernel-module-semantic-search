import threading
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, ProgressBar
from textual.containers import Vertical
from textual.reactive import reactive
from app.modules import get_all_modules
from app.indexer import ModuleIndexer

class KernelModuleSearchApp(App):
    CSS_PATH = "../semantic_kernel_tui.css"

    loading_complete = reactive(False)
    loading_progress = reactive(0)

    def __init__(self):
        super().__init__()
        self.modules = []
        self.indexer = None
        self.loading_error = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Input(placeholder="Search kernel modules... (Loading in progress)",
                  id="search_input", disabled=True),
            Vertical(
                Static("Loading kernel modules...", id="loading_message"),
                ProgressBar(total=100, show_eta=False, id="progress_bar"),
                id="loading_container"
            ),
            ListView(id="results_list"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#results_list", ListView).display = False
        self.start_loading()

    def start_loading(self) -> None:
        def loading_thread():
            try:
                self.call_from_thread(self.update_loading_state, "Scanning kernel modules...", 10)
                modules = get_all_modules(progress_callback=self.modules_progress_callback)

                if not modules:
                    modules = [{"config": "ERROR", "desc": "No modules found", "path": ""}]

                self.call_from_thread(self.update_loading_state, "Loading AI model...", 40)
                indexer = ModuleIndexer(modules, progress_callback=self.indexer_progress_callback)

                self.call_from_thread(self.update_loading_state, "Finalizing...", 95)

                self.modules = modules
                self.indexer = indexer

                self.call_from_thread(self.loading_finished)
            except Exception as e:
                self.loading_error = str(e)
                self.call_from_thread(self.loading_failed, str(e))

        thread = threading.Thread(target=loading_thread, daemon=True)
        thread.start()

    def modules_progress_callback(self, stage: str, progress: int):
        self.call_from_thread(self.update_loading_state, stage, progress)

    def indexer_progress_callback(self, stage: str, progress: int):
        self.call_from_thread(self.update_loading_state, stage, progress)

    def update_loading_state(self, stage: str, progress: int):
        self.loading_progress = progress
        msg = self.query_one("#loading_message", Static)
        bar = self.query_one("#progress_bar", ProgressBar)
        msg.update(f"{stage} ({progress}%)")
        bar.progress = progress

    def loading_finished(self):
        self.loading_complete = True

        self.query_one("#loading_container").display = False
        input_box = self.query_one("#search_input", Input)
        input_box.placeholder = "Search kernel modules..."
        input_box.disabled = False
        input_box.focus()

        results = self.query_one("#results_list", ListView)
        results.display = True
        for m in self.modules[:50]:
            results.append(ListItem(Static(f"{m['config']}: {m['desc']}")))

    def loading_failed(self, error: str):
        msg = self.query_one("#loading_message", Static)
        bar = self.query_one("#progress_bar", ProgressBar)
        msg.update(f"❌ Loading failed: {error}")
        bar.progress = 0
        results = self.query_one("#results_list", ListView)
        results.append(ListItem(Static(f"ERROR: {error}")))

    def on_input_changed(self, event: Input.Changed) -> None:
        if not self.loading_complete or not self.indexer:
            return

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
