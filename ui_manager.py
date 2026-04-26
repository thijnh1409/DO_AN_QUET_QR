import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageOps
from qr_decoder import QRDecoder
from data_manager import save_scan_log, load_scan_logs
import sys
import os
import cv2
import numpy as np
import threading

# ─────────────────────────────────────────────────────────────
# HẰNG SỐ TOÀN APP  –  chỉnh tại đây, có hiệu lực khắp nơi
# ─────────────────────────────────────────────────────────────
FONT             = "Space Grotesk"
COLOR_BG         = "#F7F6F2"
COLOR_DARK       = "#0D1B2A"
COLOR_GREEN      = "#1D9E75"
COLOR_GREEN_DARK = "#153A30"
COLOR_RED        = "#E74C3C"

# Bảng màu theo loại mã QR – dùng chung cho HistoryItemWidget
QR_TYPE_STYLES: dict[str, tuple[str, str, str]] = {
    "Website": ("#EAF3DE", "#3B6D11", "🔗"),
    "WiFi":    ("#F3E8FF", "#8E24AA", "📶"),
    "Liên hệ": ("#E8F0FE", "#1A73E8", "📞"),
}
QR_TYPE_DEFAULT = ("#FEF0DB", "#E67C22", "📄")


def resource_path(relative_path: str) -> str:
    """Lấy đường dẫn tuyệt đối tới tài nguyên, dùng cho cả Dev và PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ─────────────────────────────────────────────────────────────
# HÀM TIỆN ÍCH DÙNG CHUNG
# ─────────────────────────────────────────────────────────────

def make_topbar(parent, title: str, subtitle: str) -> ctk.CTkFrame:
    """
    Tạo thanh tiêu đề trắng chuẩn dùng cho mọi trang.
    Trả về frame topbar để caller có thể gắn thêm widget vào bên phải nếu cần.
    """
    topbar = ctk.CTkFrame(parent, height=75, fg_color="white", corner_radius=0)
    topbar.pack(fill="x", side="top")

    title_container = ctk.CTkFrame(topbar, fg_color="transparent")
    title_container.pack(side="left", padx=25, pady=10)
    ctk.CTkLabel(title_container, text=title,
                 font=(FONT, 18, "bold"), text_color="#1a1a1a").pack(anchor="w")
    ctk.CTkLabel(title_container, text=subtitle,
                 font=(FONT, 12), text_color="#888").pack(anchor="w")
    return topbar


def make_icon_button(parent, icon: str, command, hover_color: str = "#F0F0F0",
                     text_color: str = "#aaa", size: int = 32) -> ctk.CTkButton:
    """Tạo nút icon trong suốt chuẩn (dùng cho copy, xóa…)."""
    return ctk.CTkButton(
        parent, text=icon, font=("Arial", 13),
        width=size, height=size,
        fg_color="transparent", text_color=text_color,
        hover_color=hover_color, corner_radius=8,
        command=command,
    )


def fit_image_to_box(pil_img: Image.Image, box_w: int, box_h: int) -> ctk.CTkImage:
    """Thu/phóng ảnh PIL lấp đầy khung (box_w × box_h), trả về CTkImage."""
    fitted = ImageOps.fit(pil_img, (box_w, box_h), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=fitted, dark_image=fitted, size=(box_w, box_h))


# ─────────────────────────────────────────────────────────────
# WIDGET DÙNG LẠI: 1 dòng lịch sử
# ─────────────────────────────────────────────────────────────

class HistoryItemWidget(ctk.CTkFrame):
    """
    Khuôn đúc 1 dòng lịch sử.
    Tái sử dụng cho cả ScanPage (không có nút xóa) và HistoryPage (có nút xóa).
    """
    def __init__(self, parent, content: str, qr_type: str, time_str: str,
                 copy_func, delete_func=None, truncate: bool = True):
        super().__init__(parent, fg_color="transparent")

        bg_color, fg_color, icon = QR_TYPE_STYLES.get(qr_type, QR_TYPE_DEFAULT)

        row = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=8, height=50)
        row.pack(fill="x", pady=(0, 2))
        row.pack_propagate(False)

        # Icon loại mã
        ctk.CTkLabel(row, text=icon, font=("Arial", 15),
                     fg_color=bg_color, text_color=fg_color,
                     width=32, height=32, corner_radius=8).pack(side="left", padx=(8, 6))

        # Badge loại mã
        ctk.CTkLabel(row, text=qr_type, font=(FONT, 10, "bold"),
                     text_color=fg_color, fg_color=bg_color,
                     corner_radius=6, width=58, height=20).pack(side="left", padx=(0, 10))

        # Nội dung – ScanPage cắt ngắn (truncate=True), HistoryPage hiện đầy đủ (truncate=False)
        display = (content[:27] + "…" if len(content) > 30 else content) if truncate else content
        ctk.CTkLabel(row, text=display, font=(FONT, 13, "bold"),
                     text_color="#1a1a1a", anchor="w").pack(side="left", fill="x", expand=True)

        # Thời gian
        ctk.CTkLabel(row, text=time_str, font=(FONT, 11),
                     text_color="#aaa").pack(side="right", padx=(0, 8))

        # Nút xóa – chỉ xuất hiện ở HistoryPage
        if delete_func:
            make_icon_button(row, "🗑", lambda: delete_func(self),
                             hover_color="#FDE8E8").pack(side="right", padx=(0, 4))

        # Nút copy
        btn_copy = make_icon_button(row, "📋",
                                    lambda c=content: copy_func(c, btn_copy))
        btn_copy.pack(side="right", padx=(0, 4))


# ─────────────────────────────────────────────────────────────
# APP CHÍNH
# ─────────────────────────────────────────────────────────────

ctk.set_appearance_mode("light")


class QRCodeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI QR Scanner Pro")
        self.geometry("1000x650")
        self.configure(fg_color=COLOR_BG)

        self.intro_frame    = ctk.CTkFrame(self, fg_color="transparent")
        self.main_app_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.frames:      dict = {}
        self.nav_buttons: dict = {}
        self.assets:      dict = {}

        self._load_assets()
        self._setup_intro_screen()
        self.intro_frame.pack(fill="both", expand=True)

    # ── Assets ───────────────────────────────────────────────

    def _load_assets(self):
        logo_path = resource_path(os.path.join("assets", "hcmute-logo.png"))
        if not os.path.exists(logo_path):
            print(f"Không tìm thấy logo tại {logo_path}")
            return
        try:
            img = Image.open(logo_path)
            target_w = 400
            new_h    = int(img.size[1] * target_w / img.size[0])
            self.assets["uni_logo"] = ctk.CTkImage(
                light_image=img, dark_image=img, size=(target_w, new_h))
        except Exception as e:
            print(f"Lỗi load logo: {e}")

    # ── Màn hình Intro ───────────────────────────────────────

    def _setup_intro_screen(self):
        content = ctk.CTkFrame(self.intro_frame, fg_color="transparent")
        content.pack(expand=True)

        if "uni_logo" in self.assets:
            ctk.CTkLabel(content, text="", image=self.assets["uni_logo"]).pack(pady=(0, 20))

        ctk.CTkLabel(content, text="ĐỀ TÀI\nTẠO ỨNG DỤNG NHẬN DIỆN MÃ QR",
                     font=(FONT, 28, "bold"), text_color=COLOR_DARK,
                     justify="center").pack(pady=(0, 30))

        info_box = ctk.CTkFrame(content, fg_color="white", corner_radius=15,
                                border_width=1, border_color="#E0DED8")
        info_box.pack(pady=10, padx=50)

        ctk.CTkLabel(info_box, text="Giảng viên hướng dẫn: Ts. Dương Minh Thiện",
                     font=(FONT, 16, "bold"), text_color=COLOR_GREEN).pack(pady=(20, 15), padx=60)

        members = [
            ("Lê Nguyễn Văn Hòa",    "25139013"),
            ("Nguyễn Truy Phong",     "25139031"),
            ("Nguyễn Gia Thiên Phúc", "25139034"),
            ("Nguyễn Lê Phúc Thịnh",  "25139047"),
            ("Nguyễn Thanh Trí",      "23119217"),
        ]
        for name, mssv in members:
            row = ctk.CTkFrame(info_box, fg_color="transparent")
            row.pack(fill="x", padx=60, pady=4)
            ctk.CTkLabel(row, text=name, font=(FONT, 14)).pack(side="left")
            ctk.CTkLabel(row, text=mssv, font=(FONT, 14, "bold")).pack(side="right")

        ctk.CTkLabel(info_box, text="Nhóm thực hiện: Nhóm 8",
                     font=(FONT, 12, "italic"), text_color="gray").pack(pady=20)

        ctk.CTkButton(content, text="BẮT ĐẦU QUÉT", font=(FONT, 15, "bold"),
                      fg_color=COLOR_GREEN, hover_color=COLOR_GREEN_DARK,
                      height=50, corner_radius=12,
                      command=self._enter_main_app).pack(pady=30)

    def _enter_main_app(self):
        self.intro_frame.pack_forget()
        self.main_app_frame.pack(fill="both", expand=True)
        self._setup_main_app()

    # ── Layout chính ─────────────────────────────────────────

    def _setup_main_app(self):
        sidebar = ctk.CTkFrame(self.main_app_frame, width=80,
                               fg_color=COLOR_DARK, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="QR", font=(FONT, 20, "bold"),
                     fg_color=COLOR_GREEN, text_color="white",
                     width=45, height=45, corner_radius=12).pack(pady=(20, 30))

        self._create_nav_button(sidebar, "scan_page",    "📷\nQuét",    is_active=True)
        self._create_nav_button(sidebar, "history_page", "🕒\nLịch sử")

        main_content = ctk.CTkFrame(self.main_app_frame, fg_color="transparent", corner_radius=0)
        main_content.pack(side="right", fill="both", expand=True)
        main_content.grid_rowconfigure(0, weight=1)
        main_content.grid_columnconfigure(0, weight=1)

        for PageClass in (ScanPage, HistoryPage):
            frame = PageClass(parent=main_content, controller=self)
            self.frames[PageClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_page("ScanPage", "scan_page")

    def _create_nav_button(self, sidebar, page_id: str, text: str, is_active: bool = False):
        """Tạo nút điều hướng sidebar."""
        btn = ctk.CTkButton(
            sidebar, text=text, font=(FONT, 12, "bold"),
            fg_color=COLOR_GREEN_DARK if is_active else "transparent",
            text_color="#5DCAA5"      if is_active else "gray",
            hover_color=COLOR_GREEN,
            width=60, height=60, corner_radius=12,
            command=lambda pid=page_id: self.show_page(
                pid.replace("_page", "").title() + "Page", pid),
        )
        btn.pack(pady=5)
        self.nav_buttons[page_id] = btn

    def show_page(self, frame_class_name: str, page_id: str):
        for pid, btn in self.nav_buttons.items():
            active = pid == page_id
            btn.configure(
                fg_color=COLOR_GREEN if active else "transparent",
                text_color="white"   if active else "gray",
            )
        self.frames[frame_class_name].tkraise()

    # ── Clipboard (dùng chung toàn app) ──────────────────────

    def copy_to_clipboard(self, content: str, button=None):
        """Copy nội dung vào bộ nhớ đệm và hiển thị hiệu ứng ✅ trên nút."""
        if not content or content in ("Chưa có dữ liệu", "Đang xử lý ảnh..."):
            return
        self.clipboard_clear()
        self.clipboard_append(str(content))
        self.update()
        if button is not None:
            old_text  = button.cget("text")
            old_color = button.cget("text_color")
            button.configure(text="✅", text_color=COLOR_GREEN)
            self.after(1000, lambda: button.configure(text=old_text, text_color=old_color))


# ─────────────────────────────────────────────────────────────
# TRANG: QUÉT MÃ QR
# ─────────────────────────────────────────────────────────────

class ScanPage(ctk.CTkFrame):
    MAX_RECENT = 10   # số dòng tối đa ở khung "Lịch sử gần đây"

    def __init__(self, parent, controller: QRCodeApp):
        super().__init__(parent, fg_color="transparent")
        self.controller  = controller
        self.decoder     = None
        self.is_scanning = False
        self._recent_rows: list = []  # (content, time_str, widget) – dùng để xóa đồng bộ

        self._build_ui()
        self.load_recent_history()

    # ── Xây dựng giao diện ───────────────────────────────────

    def _build_ui(self):
        # Topbar dùng hàm chung; giữ ref để gắn badge camera bên phải
        topbar = make_topbar(self, "Quét mã QR", "Hướng camera vào mã cần quét")

        # Lấy lại sub_label để đổi text khi chuyển chế độ
        title_container = topbar.winfo_children()[0]
        self.sub_label  = title_container.winfo_children()[1]

        # Badge trạng thái camera
        self.cam_badge = ctk.CTkFrame(topbar, fg_color="#F5F5F5", corner_radius=20)
        self.cam_badge.pack(side="right", padx=25)
        self.dot = ctk.CTkLabel(self.cam_badge, text="●", text_color="#999", font=("Arial", 10))
        self.dot.pack(side="left", padx=(12, 5))
        self.status_text = ctk.CTkLabel(self.cam_badge, text="Camera đang tắt",
                                        font=(FONT, 11, "bold"), text_color="#666")
        self.status_text.pack(side="left", padx=(0, 12), pady=6)

        # Layout 2 cột
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self._build_left_panel(container)
        self._build_right_panel(container)

    def _build_left_panel(self, container):
        left_p = ctk.CTkFrame(container, fg_color="transparent")
        left_p.grid(row=0, column=0, sticky="nsew", padx=(25, 10), pady=20)

        self.tabs = ctk.CTkSegmentedButton(
            left_p, values=["Từ camera", "Từ file ảnh"],
            selected_color=COLOR_DARK, command=self.switch_mode)
        self.tabs.set("Từ camera")
        self.tabs.pack(pady=(0, 15))

        self.view_box = ctk.CTkFrame(left_p, fg_color="#1a1a1a", corner_radius=16)
        self.view_box.pack(fill="both", expand=True)
        self.view_box.pack_propagate(False)

        self.display_label = ctk.CTkLabel(
            self.view_box, text="Nhấn 'Bật Camera' để bắt đầu", text_color="#555")
        self.display_label.place(relx=0.5, rely=0.5, anchor="center")
        self.display_label.bind("<Button-1>", self.open_file_dialog)

        self.btn_toggle = ctk.CTkButton(
            left_p, text="Bật Camera", fg_color=COLOR_GREEN,
            corner_radius=10, height=40, command=self.toggle_camera)
        self.btn_toggle.pack(pady=15)

    def _build_right_panel(self, container):
        right_p = ctk.CTkFrame(container, fg_color="white", corner_radius=0)
        right_p.grid(row=0, column=1, sticky="nsew")

        # Khu vực kết quả
        res_sec = ctk.CTkFrame(right_p, fg_color="transparent")
        res_sec.pack(fill="x", padx=15, pady=20)
        ctk.CTkLabel(res_sec, text="KẾT QUẢ",
                     font=(FONT, 10, "bold"), text_color="#aaa").pack(anchor="w")

        self.res_box = ctk.CTkFrame(res_sec, fg_color=COLOR_BG, corner_radius=10)
        self.res_box.pack(fill="x", pady=8)

        self.res_label = ctk.CTkLabel(
            self.res_box, text="Chưa có dữ liệu",
            font=(FONT, 12), text_color="#999", pady=25, wraplength=160)
        self.res_label.pack(side="left", padx=(15, 5), expand=True, fill="x")

        self.btn_copy = make_icon_button(
            self.res_box, "📋", self.copy_result,
            hover_color="#E0DED8", text_color="#555", size=35)
        self.btn_copy.pack(side="right", padx=10)

        # Khu vực lịch sử gần đây
        hist_sec = ctk.CTkFrame(right_p, fg_color="transparent")
        hist_sec.pack(fill="both", expand=True, padx=15)
        ctk.CTkLabel(hist_sec, text="LỊCH SỬ GẦN ĐÂY",
                     font=(FONT, 10, "bold"), text_color="#aaa").pack(anchor="w")

        self.hist_list = ctk.CTkScrollableFrame(hist_sec, fg_color="transparent", height=400)
        self.hist_list.pack(fill="both", expand=True, pady=5)

    # ── Helpers ──────────────────────────────────────────────

    def clear_display(self, text_str: str):
        """Reset khung camera về trạng thái rỗng (tránh lỗi pyimage)."""
        empty = ctk.CTkImage(light_image=Image.new("RGBA", (1, 1), 0), size=(1, 1))
        self.display_label.configure(image=empty, text=text_str)
        self.display_label.image = empty

    def _show_scan_result(self, content: str, qr_type: str):
        """Hiển thị kết quả, lưu log, thêm dòng lịch sử. Dùng chung cho Camera và File."""
        self.res_label.configure(text=str(content), text_color=COLOR_GREEN,
                                 font=(FONT, 14, "bold"))
        self.controller.copy_to_clipboard(content, self.btn_copy)
        try:
            time_str = save_scan_log(str(content), str(qr_type), "Camera")
            self.add_history_row(str(content), str(qr_type), time_str)
        except Exception as e:
            print("Lỗi lưu lịch sử:", e)

    def copy_result(self):
        self.controller.copy_to_clipboard(self.res_label.cget("text"), self.btn_copy)

    # ── Camera ───────────────────────────────────────────────

    def toggle_camera(self):
        if not self.is_scanning:
            try:
                self.decoder     = QRDecoder()
                self.is_scanning = True
                self.btn_toggle.configure(text="Tắt Camera", fg_color=COLOR_RED)
                self.cam_badge.configure(fg_color="#EAF3DE")
                self.dot.configure(text_color="#639922")
                self.status_text.configure(text="Camera đang hoạt động", text_color="#3B6D11")
                self.clear_display("")
                self.run_camera_loop()
            except Exception as e:
                print(f"Lỗi không thể mở camera: {e}")
                self.is_scanning = False
        else:
            self.is_scanning = False
            if getattr(self, "decoder", None):
                self.decoder.release_camera()
                self.decoder = None
            self.btn_toggle.configure(text="Bật Camera", fg_color=COLOR_GREEN)
            self.cam_badge.configure(fg_color="#F5F5F5")
            self.dot.configure(text_color="#999")
            self.status_text.configure(text="Camera đang tắt", text_color="#666")
            self.clear_display("Nhấn 'Bật Camera' để bắt đầu")

    def run_camera_loop(self):
        if not self.is_scanning or self.decoder is None:
            return
        try:
            result = self.decoder.get_frame_and_data()
            if result.frame is None:
                print("Camera mất kết nối. Đang tắt...")
                self.toggle_camera()
                return

            # Vẽ frame lên màn hình
            self.view_box.update_idletasks()
            w, h = self.view_box.winfo_width(), self.view_box.winfo_height()
            if w > 10 and h > 10:
                img_ctk = fit_image_to_box(Image.fromarray(result.frame), w, h)
                self.display_label.configure(image=img_ctk, text="")
                self.display_label.image = img_ctk

            # Hiển thị kết quả nếu quét trúng
            if result.data and str(result.data).strip():
                self._show_scan_result(result.data, result.data_type or "Văn bản")

        except Exception as e:
            print(f"Lỗi xử lý khung hình: {e}")

        self.after(15, self.run_camera_loop)

    def destroy(self):
        """Đảm bảo camera được tắt khi đóng cửa sổ."""
        if getattr(self, "decoder", None):
            self.decoder.release_camera()
            self.decoder = None
        super().destroy()

    # ── Chế độ File ảnh ──────────────────────────────────────

    def switch_mode(self, mode: str):
        if self.is_scanning:
            self.toggle_camera()
        if mode == "Từ file ảnh":
            self.sub_label.configure(text="Tải ảnh chứa mã QR lên để quét")
            self.clear_display("Nhấp chuột vào đây để chọn file ảnh")
            self.display_label.configure(cursor="hand2")
            self.btn_toggle.pack_forget()
            self.cam_badge.pack_forget()
        else:
            self.sub_label.configure(text="Hướng camera vào mã cần quét")
            self.clear_display("Nhấn 'Bật Camera' để bắt đầu")
            self.display_label.configure(cursor="")
            self.btn_toggle.pack(pady=15)
            self.cam_badge.pack(side="right", padx=25)

    def open_file_dialog(self, event):
        if self.tabs.get() != "Từ file ảnh":
            return
        if getattr(self, "_file_scanning", False):
            return

        file_path = filedialog.askopenfilename(
            title="Chọn ảnh QR",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")],
        )
        if not file_path:
            return

        # Hiển thị ảnh lên giao diện ngay lập tức
        img = Image.open(file_path)
        img.thumbnail((500, 350))
        img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
        self.display_label.configure(image=img_ctk, text="")
        self.display_label.image = img_ctk

        self.res_label.configure(text="Đang xử lý ảnh...", text_color="#aaa", font=(FONT, 12))
        self.update()
        self._file_scanning = True

        def _show_result(content: str, qr_type: str = "Từ file"):
            self._file_scanning = False
            self.res_label.configure(text=str(content), text_color=COLOR_GREEN,
                                     font=(FONT, 14, "bold"))
            self.controller.copy_to_clipboard(content, self.btn_copy)
            try:
                time_str = save_scan_log(str(content), qr_type, "File ảnh")
                self.add_history_row(str(content), qr_type, time_str)
            except Exception as e:
                print("Lỗi lưu lịch sử file:", e)

        def _show_error(msg: str):
            self._file_scanning = False
            self.res_label.configure(text=msg, text_color=COLOR_RED, font=(FONT, 12))

        def _decode_in_thread():
            try:
                if not hasattr(self, "file_qreader"):
                    from qreader import QReader
                    print("Đang tải mô hình AI cho File ảnh...")
                    self.file_qreader = QReader()

                img_cv2 = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img_cv2 is None:
                    raise ValueError("Không thể đọc file ảnh (đường dẫn lỗi hoặc định dạng sai)")

                img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
                valid   = [t for t in self.file_qreader.detect_and_decode(image=img_rgb)
                           if t is not None]
                if valid:
                    self.after(0, lambda: _show_result(valid[0]))
                else:
                    self.after(0, lambda: _show_error("Không tìm thấy mã QR nào"))
            except Exception as e:
                print(f"Lỗi giải mã file: {e}")
                self.after(0, lambda: _show_error("Lỗi đọc file ảnh!"))

        threading.Thread(target=_decode_in_thread, daemon=True).start()

    # ── Lịch sử gần đây ──────────────────────────────────────

    def load_recent_history(self):
        """Tải 10 lịch sử mới nhất khi khởi động."""
        try:
            for log in load_scan_logs()[::-1][:self.MAX_RECENT]:
                self.add_history_row(log["content"], log["type"], log["time"])
        except Exception as e:
            print(f"Lỗi tải lịch sử gần đây: {e}")

    def add_history_row(self, content: str, qr_type: str, time_str: str):
        """Thêm dòng lịch sử lên đầu danh sách, giữ tối đa MAX_RECENT dòng."""
        children = self.hist_list.winfo_children()
        if len(children) >= self.MAX_RECENT:
            children[-1].destroy()

        widget = HistoryItemWidget(
            self.hist_list, content, qr_type, time_str,
            copy_func=self.controller.copy_to_clipboard,
        )
        # Lưu để delete_history_row có thể tìm đúng dòng cần xóa
        self._recent_rows.append((content, time_str, widget))
        widget.pack(fill="x", pady=(0, 4),
                    before=children[0] if children else None)

    def delete_history_row(self, content: str, time_str: str):
        """
        Được gọi bởi HistoryPage khi người dùng xóa 1 dòng.
        Tìm và xóa dòng khớp trong khung 'Lịch sử gần đây' của ScanPage.
        """
        for entry in list(self._recent_rows):
            c, t, widget = entry
            if c == content and t == time_str:
                self._recent_rows.remove(entry)
                widget.destroy()
                break


# ─────────────────────────────────────────────────────────────
# TRANG: LỊCH SỬ QUÉT
# ─────────────────────────────────────────────────────────────

class HistoryPage(ctk.CTkFrame):
    def __init__(self, parent, controller: QRCodeApp):
        super().__init__(parent, fg_color="transparent")
        self.controller      = controller
        self.history_widgets: list[HistoryItemWidget] = []

        make_topbar(self, "Lịch sử quét", "Quản lý và tra cứu các mã QR đã quét")
        self._build_body()
        self._load_history()

    # ── Xây dựng giao diện ───────────────────────────────────

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=25, pady=20)

        self._build_toolbar(body)

        list_frame = ctk.CTkFrame(body, fg_color="white", corner_radius=12,
                                  border_width=1, border_color="#E0DED8")
        list_frame.pack(fill="both", expand=True)

        # Header cột
        header = ctk.CTkFrame(list_frame, fg_color=COLOR_BG, height=40, corner_radius=0)
        header.pack(fill="x", padx=2, pady=2)
        ctk.CTkLabel(header, text="NỘI DUNG MÃ QR",
                     font=(FONT, 11, "bold"), text_color="#888").pack(side="left", padx=(65, 0))
        ctk.CTkLabel(header, text="THAO TÁC",
                     font=(FONT, 11, "bold"), text_color="#888").pack(side="right", padx=(0, 25))
        ctk.CTkLabel(header, text="THỜI GIAN",
                     font=(FONT, 11, "bold"), text_color="#888").pack(side="right", padx=(0, 100))

        self.scroll_list = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_toolbar(self, body):
        toolbar = ctk.CTkFrame(body, fg_color="transparent", height=50)
        toolbar.pack(fill="x", pady=(0, 15))

        self.search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="🔍 Tìm kiếm nội dung...",
            width=250, height=40, font=(FONT, 13),
            fg_color="white", border_width=1, border_color="#E0DED8", corner_radius=8)
        self.search_entry.pack(side="left")

        self.filter_combo = ctk.CTkComboBox(
            toolbar, values=["Tất cả", "URL", "Văn bản", "Liên hệ", "WiFi"],
            width=120, height=40, font=(FONT, 13),
            fg_color="white", border_width=1, border_color="#E0DED8",
            button_color=COLOR_BG, button_hover_color="#E0DED8", corner_radius=8)
        self.filter_combo.pack(side="left", padx=10)

        ctk.CTkButton(toolbar, text="🗑 Xóa tất cả", font=(FONT, 13, "bold"),
                      width=110, height=40, fg_color="#FDE8E8",
                      text_color="#C0392B", hover_color="#FAD1D1", corner_radius=8,
                      command=self.clear_all_history).pack(side="right")

        ctk.CTkButton(toolbar, text="📥 Xuất CSV", font=(FONT, 13, "bold"),
                      width=110, height=40, fg_color="#EAF3DE",
                      text_color="#3B6D11", hover_color="#D5E8C1", corner_radius=8,
                      command=self._export_csv).pack(side="right", padx=10)

    # ── Dữ liệu ──────────────────────────────────────────────

    def _load_history(self):
        """Tải toàn bộ lịch sử từ file khi khởi động."""
        try:
            for log in load_scan_logs()[::-1]:
                self.add_history_row(log["content"], log["type"],
                                     log.get("source", ""), log["time"])
        except Exception as e:
            print(f"Lỗi tải lịch sử: {e}")

    def add_history_row(self, content: str, qr_type: str, source: str, time_str: str):
        """Thêm 1 dòng vào danh sách (có nút xóa)."""
        label  = f"{source}  •  {time_str}" if source else time_str
        widget = HistoryItemWidget(
            self.scroll_list, content, qr_type, label,
            copy_func=self.controller.copy_to_clipboard,
            delete_func=lambda w, c=content, t=time_str: self.delete_row(w, c, t),
            truncate=False,   # HistoryPage hiện nội dung đầy đủ, không cắt ngắn
        )
        widget.pack(fill="x", pady=(0, 4))
        self.history_widgets.append((content, time_str, widget))

    def delete_row(self, widget: HistoryItemWidget, content: str, time_str: str):
        """Xóa dòng khỏi HistoryPage VÀ đồng bộ xóa dòng tương ứng ở ScanPage."""
        # Xóa khỏi danh sách nội bộ
        self.history_widgets = [(c, t, w) for c, t, w in self.history_widgets if w is not widget]
        widget.destroy()

        # Thông báo cho ScanPage xóa dòng tương ứng trong "Lịch sử gần đây"
        scan_page = self.controller.frames.get("ScanPage")
        if scan_page:
            scan_page.delete_history_row(content, time_str)

    def clear_all_history(self):
        for _, _, widget in self.history_widgets:
            widget.destroy()
        self.history_widgets.clear()
        # Xóa toàn bộ ở ScanPage luôn
        scan_page = self.controller.frames.get("ScanPage")
        if scan_page:
            for _, _, w in list(scan_page._recent_rows):
                w.destroy()
            scan_page._recent_rows.clear()

    def _export_csv(self):
        """Placeholder – kết nối logic xuất CSV tại đây."""
        print("Xuất CSV chưa được triển khai.")


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QRCodeApp()
    app.mainloop()