"""
Nama: Danang Adiwijaya
NIM: F1D02310044
Kelas: D
"""

import sys
import json
import urllib.request
import urllib.error
import ssl
from PySide6.QtCore import (
    Qt, QThread, Signal, QObject
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSplitter,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QScrollArea, QFrame, QStatusBar, QGroupBox
)
from PySide6.QtGui import QFont, QColor, QPalette

BASE_URL = "https://api.pahrul.my.id/api/posts"
TIMEOUT  = 10

class ApiWorker(QObject):
    success  = Signal(object)   # dict or list
    error    = Signal(str)
    finished = Signal()

    def __init__(self, method: str, url: str, payload: dict | None = None):
        super().__init__()
        self.method  = method
        self.url     = url
        self.payload = payload

    def run(self):
        try:
            context = ssl._create_unverified_context()

            data = json.dumps(self.payload).encode() if self.payload else None
            req  = urllib.request.Request(
                self.url,
                data=data,
                method=self.method,
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=context) as resp:
                body = json.loads(resp.read().decode())
                self.success.emit(body)
                
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode())
                msg  = body.get("message") or body.get("error") or str(body)
            except Exception:
                msg = f"HTTP {e.code}: {e.reason}"
            self.error.emit(msg)
        except urllib.error.URLError as e:
            self.error.emit(f"Koneksi gagal: {e.reason}")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

def make_request(method, url, payload=None,
                 on_success=None, on_error=None, on_done=None):
    thread = QThread()
    worker = ApiWorker(method, url, payload)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    
    if on_success:
        worker.success.connect(on_success)
    if on_error:
        worker.error.connect(on_error)
        
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    
    if on_done:
        thread.finished.connect(on_done)
        
    thread.worker = worker 
    
    thread.start()
    return thread

class PostDialog(QDialog):
    def __init__(self, parent=None, post: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Post" if post else "Tambah Post")
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog { background: #1e1e2e; }
            QLabel  { color: #cdd6f4; font-size: 13px; }
            QLineEdit, QTextEdit, QComboBox {
                background: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 6px; padding: 6px 10px; font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                border-radius: 6px; padding: 8px 20px;
                font-size: 13px; font-weight: bold;
            }
            QPushButton#btn_ok {
                background: #89b4fa; color: #1e1e2e;
            }
            QPushButton#btn_ok:hover { background: #b4d0fb; }
            QPushButton#btn_cancel {
                background: #45475a; color: #cdd6f4;
            }
            QPushButton#btn_cancel:hover { background: #585b70; }
        """)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 10)

        self.e_title  = QLineEdit()
        self.e_body   = QTextEdit()
        self.e_body.setFixedHeight(100)
        self.e_author = QLineEdit()
        self.e_slug   = QLineEdit()
        self.e_status = QComboBox()
        self.e_status.addItems(["published", "draft"])

        form.addRow("Title *",  self.e_title)
        form.addRow("Body *",   self.e_body)
        form.addRow("Author *", self.e_author)
        form.addRow("Slug *",   self.e_slug)
        form.addRow("Status",   self.e_status)

        if post:
            self.e_title.setText(post.get("title", ""))
            self.e_body.setPlainText(post.get("body", ""))
            self.e_author.setText(post.get("author", ""))
            self.e_slug.setText(post.get("slug", ""))
            idx = self.e_status.findText(post.get("status", "draft"))
            if idx >= 0:
                self.e_status.setCurrentIndex(idx)

        btn_ok = QPushButton("Simpan")
        btn_ok.setObjectName("btn_ok")
        btn_cancel = QPushButton("Batal")
        btn_cancel.setObjectName("btn_cancel")
        btn_ok.clicked.connect(self._accept)
        btn_cancel.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addSpacing(6)
        root.addLayout(btn_row)
        root.setContentsMargins(0, 0, 0, 16)

    def _accept(self):
        if not self.e_title.text().strip():
            QMessageBox.warning(self, "Validasi", "Title wajib diisi.")
            return
        if not self.e_body.toPlainText().strip():
            QMessageBox.warning(self, "Validasi", "Body wajib diisi.")
            return
        if not self.e_author.text().strip():
            QMessageBox.warning(self, "Validasi", "Author wajib diisi.")
            return
        if not self.e_slug.text().strip():
            QMessageBox.warning(self, "Validasi", "Slug wajib diisi.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "title":  self.e_title.text().strip(),
            "body":   self.e_body.toPlainText().strip(),
            "author": self.e_author.text().strip(),
            "slug":   self.e_slug.text().strip(),
            "status": self.e_status.currentText(),
        }

class DetailPanel(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setMinimumWidth(280)
        self.setStyleSheet("""
            QScrollArea { border: none; background: #181825; }
            QWidget#inner { background: #181825; }
        """)

        inner = QWidget()
        inner.setObjectName("inner")
        self._layout = QVBoxLayout(inner)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(10)
        self.setWidget(inner)

        self._placeholder = QLabel("← Klik baris tabel\nuntuk melihat detail post")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #585b70; font-size: 14px;")
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch()

    def show_loading(self):
        self._clear()
        lbl = QLabel("⏳ Memuat detail…")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #89b4fa; font-size: 13px;")
        self._layout.insertWidget(0, lbl)

    def show_post(self, post: dict, comments: list):
        self._clear()
        L = self._layout

        def section(title):
            lbl = QLabel(title)
            lbl.setStyleSheet(
                "color: #89b4fa; font-size: 11px; font-weight: bold; "
                "letter-spacing: 1px; text-transform: uppercase;"
            )
            L.addWidget(lbl)

        def field(label, value):
            wrap = QWidget()
            wrap.setStyleSheet(
                "background:#1e1e2e; border-radius:8px; padding:2px;"
            )
            vl = QVBoxLayout(wrap)
            vl.setContentsMargins(10, 8, 10, 8)
            vl.setSpacing(2)
            lbl_key = QLabel(label)
            lbl_key.setStyleSheet("color:#6c7086; font-size:11px;")
            lbl_val = QLabel(str(value))
            lbl_val.setWordWrap(True)
            lbl_val.setStyleSheet("color:#cdd6f4; font-size:13px;")
            vl.addWidget(lbl_key)
            vl.addWidget(lbl_val)
            L.addWidget(wrap)

        # Status badge
        status = post.get("status", "")
        color  = "#a6e3a1" if status == "published" else "#f38ba8"
        badge  = QLabel(f"  {status.upper()}  ")
        badge.setStyleSheet(
            f"color:{color}; background:#1e1e2e; border:1px solid {color}; "
            "border-radius:10px; font-size:11px; font-weight:bold;"
        )
        badge.setFixedHeight(24)
        badge.setAlignment(Qt.AlignCenter)
        L.addWidget(badge)

        section("INFORMASI POST")
        field("ID",     post.get("id", "-"))
        field("Title",  post.get("title", "-"))
        field("Author", post.get("author", "-"))
        field("Slug",   post.get("slug", "-"))
        field("Body",   post.get("body", "-"))

        # Comments
        section(f"COMMENTS ({len(comments)})")
        if not comments:
            no_c = QLabel("Belum ada komentar.")
            no_c.setStyleSheet("color:#585b70; font-size:12px;")
            L.addWidget(no_c)
        for c in comments:
            card = QFrame()
            card.setStyleSheet(
                "QFrame{background:#1e1e2e;border-radius:8px;}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            name = QLabel(c.get("name", "Anonymous"))
            name.setStyleSheet("color:#89dceb; font-size:12px; font-weight:bold;")
            body = QLabel(c.get("body", ""))
            body.setWordWrap(True)
            body.setStyleSheet("color:#cdd6f4; font-size:12px;")
            cl.addWidget(name)
            cl.addWidget(body)
            L.addWidget(card)

        L.addStretch()

    def clear(self):
        self._clear()
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch()

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w and w is not self._placeholder:
                w.deleteLater()
        self._placeholder.setParent(None)

STYLESHEET = """
QMainWindow, QWidget { background: #1e1e2e; color: #cdd6f4; }
QTableWidget {
    background: #181825; color: #cdd6f4;
    border: none; gridline-color: #313244;
    selection-background-color: #313244;
    font-size: 13px;
}
QHeaderView::section {
    background: #313244; color: #89b4fa;
    padding: 8px; border: none; font-weight: bold; font-size: 12px;
}
QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #313244; }
QTableWidget::item:selected { background: #45475a; color: #cdd6f4; }
QPushButton {
    border-radius: 6px; padding: 7px 16px;
    font-size: 13px; font-weight: bold; border: none;
}
QPushButton#btn_refresh { background:#313244; color:#89b4fa; }
QPushButton#btn_refresh:hover { background:#45475a; }
QPushButton#btn_add    { background:#a6e3a1; color:#1e1e2e; }
QPushButton#btn_add:hover { background:#c3f0be; }
QPushButton#btn_edit   { background:#89b4fa; color:#1e1e2e; }
QPushButton#btn_edit:hover { background:#b4d0fb; }
QPushButton#btn_edit:disabled  { background:#313244; color:#45475a; }
QPushButton#btn_delete { background:#f38ba8; color:#1e1e2e; }
QPushButton#btn_delete:hover { background:#f7b8c8; }
QPushButton#btn_delete:disabled { background:#313244; color:#45475a; }
QStatusBar { background:#181825; color:#6c7086; font-size:12px; }
QSplitter::handle { background:#313244; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Post Manager — CRUD PySide6")
        self.resize(1100, 680)
        self.setStyleSheet(STYLESHEET)

        self._threads: list = []   
        self._posts:   list = []   
        self._selected_post: dict | None = None

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._set_status("Selamat datang! Klik Refresh untuk memuat data.")

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setObjectName("btn_refresh")
        self.btn_add     = QPushButton("➕ Tambah")
        self.btn_add.setObjectName("btn_add")
        self.btn_edit    = QPushButton("✏️ Edit")
        self.btn_edit.setObjectName("btn_edit")
        self.btn_edit.setEnabled(False)
        self.btn_delete  = QPushButton("🗑 Hapus")
        self.btn_delete.setObjectName("btn_delete")
        self.btn_delete.setEnabled(False)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Author", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        self.detail = DetailPanel()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 6, 12)
        left_layout.setSpacing(8)
        left_layout.addLayout(toolbar)
        left_layout.addWidget(self.table)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([750, 350])

        self.setCentralWidget(splitter)

        self.btn_refresh.clicked.connect(self.load_posts)
        self.btn_add.clicked.connect(self.add_post)
        self.btn_edit.clicked.connect(self.edit_post)
        self.btn_delete.clicked.connect(self.delete_post)
        self.table.itemSelectionChanged.connect(self._on_selection)

        self.load_posts()

    def _set_status(self, msg: str):
        self.status.showMessage(msg)

    def _set_busy(self, busy: bool):
        for b in (self.btn_refresh, self.btn_add, self.btn_edit, self.btn_delete):
            b.setEnabled(not busy)
        if busy:
            self._set_status("⏳ Memuat…")
        else:
            self._set_status("✅ Selesai.")
            self._update_buttons()

    def _update_buttons(self):
        has_sel = self._selected_post is not None
        self.btn_edit.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)

    def _track(self, thread):
        self._threads.append(thread)
        thread.finished.connect(lambda: self._threads.remove(thread)
                                if thread in self._threads else None)

    def _on_selection(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self._selected_post = None
            self.detail.clear()
            self._update_buttons()
            return
        row  = rows[0].row()
        post = self._posts[row]
        self._selected_post = post
        self._update_buttons()
        self._load_detail(post["id"])

    def _load_detail(self, post_id: int):
        self.detail.show_loading()
        url = f"{BASE_URL}/{post_id}"
        t = make_request(
            "GET", url,
            on_success=self._on_detail_loaded,
            on_error=lambda e: self._set_status(f"❌ {e}"),
        )
        self._track(t)

    def _on_detail_loaded(self, data: dict):
        post     = data.get("data") or data
        comments = post.get("comments", [])
        self.detail.show_post(post, comments)

    def load_posts(self):
        self._set_busy(True)
        self._selected_post = None
        self.detail.clear()
        self.table.setRowCount(0)

        t = make_request(
            "GET", BASE_URL,
            on_success=self._on_posts_loaded,
            on_error=self._on_error,
            on_done=lambda: self._set_busy(False),
        )
        self._track(t)

    def _on_posts_loaded(self, data):
        posts = data.get("data") or data
        if not isinstance(posts, list):
            posts = [posts]
        self._posts = posts
        self.table.setRowCount(len(posts))
        for i, p in enumerate(posts):
            self.table.setItem(i, 0, QTableWidgetItem(str(p.get("id", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(p.get("title", "")))
            self.table.setItem(i, 2, QTableWidgetItem(p.get("author", "")))

            status = p.get("status", "")
            status_item = QTableWidgetItem(status)
            color = QColor("#a6e3a1") if status == "published" else QColor("#f38ba8")
            status_item.setForeground(color)
            self.table.setItem(i, 3, status_item)

        self._set_status(f"✅ {len(posts)} post dimuat.")

    def add_post(self):
        dlg = PostDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.get_data()
        self._set_busy(True)
        t = make_request(
            "POST", BASE_URL, payload,
            on_success=lambda _: (
                self._set_status("✅ Post berhasil ditambahkan!"),
                self.load_posts()
            ),
            on_error=self._on_error,
            on_done=lambda: self._set_busy(False),
        )
        self._track(t)

    def edit_post(self):
        if not self._selected_post:
            return
        dlg = PostDialog(self, self._selected_post)
        if dlg.exec() != QDialog.Accepted:
            return
        payload  = dlg.get_data()
        post_id  = self._selected_post["id"]
        url      = f"{BASE_URL}/{post_id}"
        self._set_busy(True)
        t = make_request(
            "PUT", url, payload,
            on_success=lambda _: (
                self._set_status("✅ Post berhasil diperbarui!"),
                self.load_posts()
            ),
            on_error=self._on_error,
            on_done=lambda: self._set_busy(False),
        )
        self._track(t)

    def delete_post(self):
        if not self._selected_post:
            return
        post = self._selected_post
        reply = QMessageBox.question(
            self,
            "Konfirmasi Hapus",
            f"Yakin ingin menghapus post:\n\n"
            f"  \"{post.get('title')}\"\n\n"
            "Semua komentar akan ikut terhapus (cascade delete).",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        url = f"{BASE_URL}/{post['id']}"
        self._set_busy(True)
        t = make_request(
            "DELETE", url,
            on_success=lambda _: (
                self._set_status("✅ Post berhasil dihapus."),
                self.load_posts()
            ),
            on_error=self._on_error,
            on_done=lambda: self._set_busy(False),
        )
        self._track(t)

    def _on_error(self, msg: str):
        self._set_status(f"❌ Error: {msg}")
        QMessageBox.critical(self, "Terjadi Kesalahan", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#1e1e2e"))
    palette.setColor(QPalette.WindowText, QColor("#cdd6f4"))
    palette.setColor(QPalette.Base, QColor("#181825"))
    palette.setColor(QPalette.AlternateBase, QColor("#1e1e2e"))
    palette.setColor(QPalette.Text, QColor("#cdd6f4"))
    palette.setColor(QPalette.Button, QColor("#313244"))
    palette.setColor(QPalette.ButtonText, QColor("#cdd6f4"))
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())