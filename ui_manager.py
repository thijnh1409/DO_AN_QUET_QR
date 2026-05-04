import sys
import os
import threading
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageOps, ImageTk
from qr_decoder import QRDecoder, FileQRDecoder
from data_manager import (
    save_scan_log, load_scan_logs,
    delete_scan_log, clear_scan_logs,
    export_to_csv_logic,
)

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
    """
    Trả về đường dẫn tuyệt đối đến tài nguyên, hỗ trợ cả khi chạy dưới dạng script lẫn PyInstaller.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ─────────────────────────────────────────────────────────────
# HÀM TIỆN ÍCH DÙNG CHUNG
# ─────────────────────────────────────────────────────────────

def make_topbar(parent, title: str, subtitle: str):
    """
    Tạo một topbar tiêu chuẩn với tiêu đề chính và phụ.
    - Trả về cả topbar lẫn sub_label để có thể cập nhật text sau này (ví dụ: trạng thái camera).
    - Sử dụng make_topbar(parent, title, subtitle) để tạo topbar cho cả ScanPage và HistoryPage, 
    đảm bảo sự nhất quán về thiết kế. Bạn có thể cập nhật text của sub_label sau khi tạo để hiển 
    thị thông tin trạng thái hoặc hướng dẫn cụ thể cho từng trang.

    """
    topbar = ctk.CTkFrame(parent, height=75, fg_color="white", corner_radius=0)
    topbar.pack(fill="x", side="top")

    title_container = ctk.CTkFrame(topbar, fg_color="transparent")
    title_container.pack(side="left", padx=25, pady=10)
    ctk.CTkLabel(title_container, text=title,
                 font=(FONT, 18, "bold"), text_color="#1a1a1a").pack(anchor="w")
                 
    # Gán vào biến sub_label thay vì pack trực tiếp
    sub_label = ctk.CTkLabel(title_container, text=subtitle,
                             font=(FONT, 12), text_color="#888")
    sub_label.pack(anchor="w")
    
    # Trả về cả topbar lẫn sub_label
    return topbar, sub_label


def make_icon_button(parent, icon: str, command, hover_color: str = "#F0F0F0",
                     text_color: str = "#aaa", size: int = 32) -> ctk.CTkButton:
    """
    Tạo một nút icon trong suốt chuẩn (dùng cho copy, xóa…).
    """
    return ctk.CTkButton(
        parent, text=icon, font=("Arial", 13),
        width=size, height=size,
        fg_color="transparent", text_color=text_color,
        hover_color=hover_color, corner_radius=8,
        command=command,
    )


# def fit_image_to_box(pil_img: Image.Image, box_w: int, box_h: int) -> ctk.CTkImage:
#     """Thu/phóng ảnh PIL lấp đầy khung (box_w x box_h), trả về CTkImage."""
#     fitted = ImageOps.fit(pil_img, (box_w, box_h), Image.Resampling.LANCZOS)
#     return ctk.CTkImage(light_image=fitted, dark_image=fitted, size=(box_w, box_h))


# ─────────────────────────────────────────────────────────────
# WIDGET DÙNG LẠI: 1 dòng lịch sử
# ─────────────────────────────────────────────────────────────

class HistoryItemWidget(ctk.CTkFrame):
    """
    Khuôn đúc Component UI: Đại diện cho một dòng hiển thị lịch sử quét.
    - Tái sử dụng: dùng chung cho cả ScanPage (phiên bản rút gọn) và HistoryPage (phiên bản đầy đủ có nút xóa).
    - Tự động thay đổi màu nền, font chữ và Icon hiển thị dựa vào loại mã (qr_type) được nạp từ từ điển QR_TYPE_STYLES.
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
        display = (content[:23] + "…" if len(content) > 26 else content) if truncate else content
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
    """
    Lớp chính của ứng dụng, quản lý toàn bộ giao diện và điều hướng giữa các trang.
        - Chịu trách nhiệm tạo cửa sổ, sidebar, topbar và quản lý các trang con (ScanPage, HistoryPage).
        - Cung cấp phương thức copy_to_clipboard() dùng chung cho cả app để sao chép nội dung và hiển thị hiệu ứng.
        - Đảm bảo rằng khi người dùng đóng ứng dụng, tất cả tài nguyên (đặc biệt là camera và luồng AI) 
        được giải phóng đúng cách thông qua phương thức on_closing().
    """

    def __init__(self):
        super().__init__()
        self.title("AI QR Scanner - Nhóm 8")
        self.geometry("1000x650")
        self.configure(fg_color=COLOR_BG)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.intro_frame    = ctk.CTkFrame(self, fg_color="transparent")
        self.main_app_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.frames:      dict = {}
        self.nav_buttons: dict = {}
        self.assets:      dict = {}

        self._load_assets()
        self._setup_intro_screen()
        self.intro_frame.pack(fill="both", expand=True)

    # ── Graceful Shutdown ───────────────────────────────────────────────

    def on_closing(self):
        """
        Đóng ứng dụng một cách an toàn, đảm bảo rằng tất cả tài nguyên (đặc biệt là camera và luồng AI) được giải phóng đúng cách để tránh lỗi hoặc treo máy.
            - Gọi shutdown() của QRDecoder để dừng luồng AI và giải phóng camera.
            - Sau đó mới gọi self.destroy() để đóng cửa sổ ứng dụng.
        """
        print("Đang dọn dẹp hệ thống...")
        
        # Tìm ScanPage và yêu cầu tắt Camera an toàn
        scan_page = self.frames.get("ScanPage")
        if scan_page and getattr(scan_page, "decoder", None):
            scan_page.decoder.shutdown()
            
        # Tắt hẳn cửa sổ
        self.destroy()

    # ── Assets ───────────────────────────────────────────────

    def _load_assets(self):
        """
        Tải trước tất cả hình ảnh (logo) vào bộ nhớ RAM ngay khi ứng dụng vừa mở lên.
        - Tối ưu: Chỉ đọc file ảnh từ ổ cứng đúng 1 lần. Chỗ nào cần thì gọi ra dùng chung để phần mềm khởi động nhanh hơn.
        - Chống lỗi: Kết hợp xử lý đường dẫn an toàn để đảm bảo lúc xuất thành file .exe đem qua máy khác, 
        phần mềm vẫn tìm thấy ảnh logo mà không bị lỗi văng app.
        """

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
        """
        Xây dựng giao diện màn hình giới thiệu với logo, tiêu đề, thông tin nhóm và nút bắt đầu.
        """

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

        ctk.CTkLabel(info_box, text="Giảng viên hướng dẫn: TS. Dương Minh Thiện",
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
        """
        Chuyển đổi từ màn hình giới thiệu sang giao diện chính của ứng dụng.
        """

        self.intro_frame.pack_forget()
        self.main_app_frame.pack(fill="both", expand=True)
        self._setup_main_app()

# ---------------------------------------------------------------------------
# LAYOUT CHÍNH: Sidebar + Main Content (ScanPage, HistoryPage)
# ---------------------------------------------------------------------------

    def _setup_main_app(self):
        """
        Xây dựng giao diện chính với sidebar điều hướng và khu vực hiển thị nội dung tương ứng.
            - Sidebar: Chứa logo nhỏ và các nút điều hướng giữa ScanPage và HistoryPage. 
            Nút nào đang hoạt động sẽ có màu nền khác biệt.
            - Main Content: Khu vực này sẽ chứa các trang con (ScanPage, HistoryPage) 
            được xếp chồng lên nhau, chỉ hiển thị trang đang được chọn.
        """

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
        """
        Hàm hỗ trợ tạo nhanh các nút bấm bên thanh menu dọc (Sidebar).
        - Tránh lặp code: Chỉ cần gọi hàm này là tự động có ngay một nút bấm bo góc, 
        đổi màu khi chuột lướt qua đúng chuẩn thiết kế chung.
        - Trực quan: Nút nào đang được chọn (is_active=True) thì sẽ sáng màu xanh lên, 
        các nút khác sẽ chìm màu xám xuống.
        """

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
        """
        Hiển thị trang tương ứng và cập nhật trạng thái nút điều hướng.
        - frame_class_name: Tên lớp của trang cần hiển thị (ví dụ: "ScanPage", "HistoryPage").
        - page_id: ID của nút điều hướng tương ứng để cập nhật trạng thái (ví dụ: "scan_page", "history_page").
        """

        for pid, btn in self.nav_buttons.items():
            active = pid == page_id
            btn.configure(
                fg_color=COLOR_GREEN if active else "transparent",
                text_color="white"   if active else "gray",
            )
        self.frames[frame_class_name].tkraise()

# ---------------------------------------------------------------------------
# CLIPBOARD: Hàm tiện ích dùng chung
# ---------------------------------------------------------------------------

    def copy_to_clipboard(self, content: str, button=None):
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


# ---------------------------------------------------------------------------
# TRANG QUÉT MÃ QR: ScanPage
# ---------------------------------------------------------------------------

class ScanPage(ctk.CTkFrame):
    """
    Trang chính để quét mã QR từ camera hoặc file ảnh.
    - Tích hợp QRDecoder để xử lý luồng camera và AI.
    - Cập nhật kết quả quét và lịch sử gần đây ngay lập tức sau mỗi lần quét thành công.
    """

    MAX_RECENT = 10   # số dòng tối đa ở khung "Lịch sử gần đây"

    def __init__(self, parent, controller: QRCodeApp):
        super().__init__(parent, fg_color="transparent")
        self.controller  = controller
        self.decoder     = None
        self.is_scanning = False
        self._file_scanning = False
        self._recent_rows: list = []  # (content, time_str, widget) – dùng để xóa đồng bộ

        self._build_ui()
        self.load_recent_history()

    # ── Xây dựng giao diện ───────────────────────────────────

    def _build_ui(self):
        # Topbar dùng hàm chung; giữ ref để gắn badge camera bên phải
        topbar, self.sub_label = make_topbar(self, "Quét mã QR", "Hướng camera vào mã cần quét")

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

        # Canvas thay cho CTkLabel — cập nhật ảnh IN-PLACE, không tạo object mới mỗi frame
        self.canvas = tk.Canvas(self.view_box, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.open_file_dialog)
        self._photo      = None   # ImageTk.PhotoImage duy nhất, tái sử dụng mãi
        self._canvas_img = None   # ID của item trên canvas

        # Label chữ hướng dẫn (overlay, chỉ hiện khi không có camera)
        self.display_label = ctk.CTkLabel(
            self.view_box, text="Nhấn 'Bật Camera' để bắt đầu", text_color="#555",
            fg_color="transparent")
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
        """Reset khung hiển thị: xoá canvas, hiện chữ hướng dẫn."""
        self.canvas.delete("all")
        self._photo      = None
        self._canvas_img = None
        self.display_label.configure(text=text_str)
        self.display_label.place(relx=0.5, rely=0.5, anchor="center")

    def _show_scan_result(self, content: str, qr_type: str):
        """
        Xử lý hiển thị kết quả và lưu trữ ngầm.
            - Non-blocking UI: Cập nhật chữ lên màn hình ngay lập tức, đồng thời đẩy tác vụ nặng (ghi file lên ổ cứng) 
            ra một luồng nền (Background Thread) để vòng lặp Camera không bị khựng (giật lag).
            - Thread-safe UI: Sau khi luồng nền lưu file xong, sử dụng lệnh self.after(0, ...) để "nhờ" 
            luồng UI chính vẽ thêm dòng lịch sử mới (Tránh lỗi văng app do luồng phụ tự ý can thiệp UI).
        """
        # 1. Update kết quả lên màn hình ngay lập tức (siêu nhẹ, không lag)
        self.res_label.configure(text=str(content), text_color=COLOR_GREEN, font=(FONT, 14, "bold"))
        self.controller.copy_to_clipboard(content, self.btn_copy)

        # 2. Đẩy tác vụ nặng (Lưu file text) ra một luồng riêng
        def background_save():
            try:
                # Việc này tốn thời gian giao tiếp ổ cứng -> Chạy ngầm là đẹp nhất
                time_str = save_scan_log(str(content), str(qr_type), "Camera")
                
                # Dùng self.after để quay lại cập nhật Lịch sử UI an toàn trên luồng chính
                self.after(0, lambda: self.add_history_row(str(content), str(qr_type), time_str))
            except Exception as e:
                print("Lỗi lưu lịch sử:", e)
                
        threading.Thread(target=background_save, daemon=True).start()

    def copy_result(self):
        self.controller.copy_to_clipboard(self.res_label.cget("text"), self.btn_copy)

    # ── Camera ───────────────────────────────────────────────

    def toggle_camera(self):
        """
        Bật hoặc tắt camera một cách an toàn.
        - Khi tắt: Chỉ tạm dừng kết nối camera (pause), nhưng vẫn "giữ" mô hình AI trong RAM để lần sau người dùng 
        bấm bật lại thì lên hình luôn, không phải chờ tải lại AI.
        - Cập nhật đúng các nút bấm, màu sắc và chữ trên màn hình để báo cho người dùng biết camera đang bật hay tắt.
        """

        if not self.is_scanning:
            try:
                # KIỂM TRA: Nếu chưa có decoder thì tạo mới, nếu có rồi thì resume
                if self.decoder is None:
                    self.decoder = QRDecoder()
                else:
                    success = self.decoder.resume()
                    if not success:
                        print("Không thể mở lại camera.")
                        return

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
                
                self.decoder.pause()
                
            self.btn_toggle.configure(text="Bật Camera", fg_color=COLOR_GREEN)
            self.cam_badge.configure(fg_color="#F5F5F5")
            self.dot.configure(text_color="#999")
            self.status_text.configure(text="Camera đang tắt", text_color="#666")
            self.clear_display("Nhấn 'Bật Camera' để bắt đầu")

    def run_camera_loop(self):
        """
        Vòng lặp liên tục lấy ảnh từ camera đưa lên màn hình.
        - Tiết kiệm RAM: Ghi đè màu mới lên bức ảnh có sẵn trên Canvas thay vì liên tục tạo ra đối tượng ảnh mới, 
        giúp máy không bị đầy bộ nhớ khi bật camera lâu.
        - Chống quá tải CPU: Dùng self.after(15) để vòng lặp nghỉ khoảng 15 mili-giây giữa các lần quét, 
        giữ cho ứng dụng chạy êm mà không gây hại đến máy tính.
        """

        if not self.is_scanning or self.decoder is None:
            return
        try:
            result = self.decoder.get_frame_and_data()
            if result.frame is None:
                print("Camera mất kết nối. Đang tắt...")
                self.toggle_camera()
                return

            # Vẽ frame lên canvas IN-PLACE — không tạo object mới mỗi frame
            self.canvas.update_idletasks()
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
            if w > 10 and h > 10:
                img = Image.fromarray(result.frame)
                img = ImageOps.fit(img, (w, h), Image.Resampling.LANCZOS)

                if self._photo is None or self._photo.width() != w or self._photo.height() != h:
                    # Tạo PhotoImage MỘT LẦN (hoặc khi kích thước thay đổi)
                    self._photo = ImageTk.PhotoImage(image=img)
                    self.canvas.delete("all")
                    self._canvas_img = self.canvas.create_image(0, 0, anchor="nw",
                                                                image=self._photo)
                    self.display_label.place_forget()   # ẩn chữ khi có camera
                else:
                    # Cập nhật pixel IN-PLACE — không cấp phát RAM mới
                    self._photo.paste(img)

            # Hiển thị kết quả nếu quét trúng
            if result.data and str(result.data).strip():
                self._show_scan_result(result.data, result.data_type or "Văn bản")

        except Exception as e:
            print(f"Lỗi xử lý khung hình: {e}")

        self.after(15, self.run_camera_loop)

    def destroy(self):
        """Đảm bảo camera và AI được tắt hoàn toàn khi đóng app."""
        if getattr(self, "decoder", None):
            self.decoder.shutdown() # Dùng shutdown() để tắt hẳn thread AI
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
            self.display_label.place(relx=0.5, rely=0.5, anchor="center")
            self.btn_toggle.pack(pady=15)
            self.cam_badge.pack(side="right", padx=25)

    def open_file_dialog(self, event):
        """
        Mở hộp thoại chọn ảnh và xử lý giải mã.
        - Tránh lỗi: Có biến cờ (flag) chặn lại, không cho người dùng bấm mở nhiều hộp thoại cùng lúc nếu ảnh trước đó chưa xử lý xong.
        - Chống đơ app: Việc nhờ AI đọc ảnh tốn thời gian, nên nhóm đẩy việc này ra một luồng ngầm (chạy phía sau). 
        Nhờ vậy giao diện vẫn mượt mà và hiện được chữ "Đang xử lý...".
        """

        if self.tabs.get() != "Từ file ảnh":
            return
        if self._file_scanning:
            return

        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Chọn ảnh QR",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")],
        )
        if not file_path:
            return

        # --- 1. HIỂN THỊ ẢNH LÊN GIAO DIỆN ---
        img = Image.open(file_path)
        img.thumbnail((500, 350))
        photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self._photo = photo
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        self._canvas_img = self.canvas.create_image(cw // 2, ch // 2, anchor="center", image=self._photo)
        self.display_label.place_forget()

        self.res_label.configure(text="Đang xử lý ảnh...", text_color="#aaa", font=(FONT, 12))
        self.update()
        self._file_scanning = True

        # --- 2. CÁC HÀM CẬP NHẬT UI KHI CHẠY XONG ---
        def _show_result(content: str, qr_type: str):
            self._file_scanning = False
            self.res_label.configure(text=str(content), text_color=COLOR_GREEN, font=(FONT, 14, "bold"))
            self.controller.copy_to_clipboard(content, self.btn_copy)
            
            # Đẩy việc lưu file ra luồng nền (Tối ưu chống giật lag)
            def background_save():
                try:
                    time_str = save_scan_log(str(content), qr_type, "File ảnh")
                    self.after(0, lambda: self.add_history_row(str(content), qr_type, time_str))
                except Exception as e:
                    print("Lỗi lưu lịch sử file:", e)
            threading.Thread(target=background_save, daemon=True).start()

        def _show_error(msg: str):
            self._file_scanning = False
            self.res_label.configure(text=msg, text_color=COLOR_RED, font=(FONT, 12))

        # --- 3. GIAO VIỆC CHO KHỐI XỬ LÝ (CHẠY NGẦM) ---
        def _decode_in_thread(f_path):
            try:
                valid_results = FileQRDecoder.decode(f_path)
                
                if valid_results:
                    qr_content = valid_results[0]
                    # Tái sử dụng hàm tĩnh phân loại
                    qr_type = QRDecoder.classify_data(qr_content)
                    
                    self.after(0, lambda: _show_result(qr_content, qr_type))
                else:
                    self.after(0, lambda: _show_error("Không tìm thấy mã QR nào"))
            except Exception as e:
                print(f"Lỗi giải mã file: {e}")
                self.after(0, lambda: _show_error("Lỗi đọc file ảnh!"))

        threading.Thread(target=_decode_in_thread, args=(file_path,), daemon=True).start()

    # ── Lịch sử gần đây ──────────────────────────────────────

    def load_recent_history(self):
        """Tải 10 lịch sử mới nhất khi khởi động."""
        try:
            # Lấy 10 dòng mới nhất, giữ nguyên thứ tự cũ -> mới.
            # Khi pack liên tục lên đầu, phần tử mới nhất sẽ trồi lên trên cùng.
            recent_logs = load_scan_logs()[-self.MAX_RECENT:]
            for log in recent_logs:
                self.add_history_row(log["content"], log["type"], log["time"])
        except Exception as e:
            print(f"Lỗi tải lịch sử gần đây: {e}")

    def add_history_row(self, content: str, qr_type: str, time_str: str):
        """Thêm dòng lịch sử lên đầu danh sách, giữ tối đa MAX_RECENT dòng."""
        # 1. Nếu vượt quá 10 dòng, xóa dòng CŨ NHẤT (dòng nằm ở đầu mảng quản lý)
        if len(self._recent_rows) >= self.MAX_RECENT:
            oldest_entry = self._recent_rows.pop(0)  # Lấy và xóa khỏi mảng
            oldest_entry[2].destroy()                # Xóa widget khỏi màn hình

        # 2. Tạo widget mới
        widget = HistoryItemWidget(
            self.hist_list, content, qr_type, time_str,
            copy_func=self.controller.copy_to_clipboard,
        )
        
        # 3. Đưa widget mới lên ĐẦU giao diện
        if self._recent_rows:
            # Lấy widget đang nằm trên cùng hiện tại (phần tử cuối của mảng)
            top_widget = self._recent_rows[-1][2]
            widget.pack(fill="x", pady=(0, 4), before=top_widget)
        else:
            # Nếu chưa có dòng nào thì cứ pack bình thường
            widget.pack(fill="x", pady=(0, 4))
            
        # 4. Lưu vào danh sách quản lý
        self._recent_rows.append((content, time_str, widget))
        
        # 5. Bắn tín hiệu sang trang Toàn bộ Lịch sử
        hist_page = self.controller.frames.get("HistoryPage") 
        if hist_page and hasattr(hist_page, 'add_new_row_to_top'):
            hist_page.add_new_row_to_top(content, qr_type, time_str)

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

        self._sort_asc = False   # mặc định: mới nhất trên đầu (↓)
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
        # Nhãn "THỜI GIAN" kiêm luôn nút sắp xếp — click để đảo chiều
        self.btn_sort_header = ctk.CTkButton(
            header, text="THỜI GIAN ↓", font=(FONT, 11, "bold"),
            fg_color="transparent", text_color="#888",
            hover_color="#E8E7E3", corner_radius=6,
            width=90, height=28,
            command=self._toggle_sort)
        self.btn_sort_header.pack(side="right", padx=(0, 18))
        ctk.CTkLabel(header, text="THAO TÁC",
                     font=(FONT, 11, "bold"), text_color="#888").pack(side="right", padx=(0, 100))

        self.scroll_list = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_toolbar(self, body):
        toolbar = ctk.CTkFrame(body, fg_color="transparent", height=50)
        toolbar.pack(fill="x", pady=(0, 15))

        # ── Lọc theo loại mã ──────────────────────────────────
        self.filter_combo = ctk.CTkComboBox(
            toolbar, values=["Tất cả", "Website", "Văn bản", "Liên hệ", "WiFi"],
            width=130, height=40, font=(FONT, 13),
            fg_color="white", border_width=1, border_color="#E0DED8",
            button_color=COLOR_BG, button_hover_color="#E0DED8", corner_radius=8,
            command=self._on_filter_change)   # ← gọi ngay khi người dùng chọn
        self.filter_combo.set("Tất cả")
        self.filter_combo.pack(side="left", padx=(0, 6))

        # ── Nút bên phải ──────────────────────────────────────
        ctk.CTkButton(toolbar, text="🗑 Xóa tất cả", font=(FONT, 13, "bold"),
                      width=110, height=40, fg_color="#FDE8E8",
                      text_color="#C0392B", hover_color="#FAD1D1", corner_radius=8,
                      command=self.clear_all_history).pack(side="right")

        ctk.CTkButton(toolbar, text="📥 Xuất CSV", font=(FONT, 13, "bold"),
                      width=110, height=40, fg_color="#EAF3DE",
                      text_color="#3B6D11", hover_color="#D5E8C1", corner_radius=8,
                      command=self._export_csv).pack(side="right", padx=10)

    # ── Dữ liệu ──────────────────────────────────────────────
    # _all_rows: nguồn dữ liệu gốc, không bao giờ bị lọc/xóa bởi filter
    # Mỗi phần tử: {"content", "qr_type", "source", "time_str"}

    def _load_history(self):
        """Tải toàn bộ lịch sử từ file khi khởi động."""
        try:
            # Rút gọn bằng List Comprehension:
            self._all_rows = [
                {
                    "content":  log["content"],
                    "qr_type":  log["type"],
                    "source":   log.get("source", ""),
                    "time_str": log["time"],
                }
                for log in load_scan_logs()[::-1]
            ]
        except Exception as e:
            print(f"Lỗi tải lịch sử: {e}")
            self._all_rows = [] # Nếu lỗi thì trả về mảng rỗng
            
        self._apply_filter_sort()

    def add_history_row(self, content: str, qr_type: str, source: str, time_str: str):
        """Thêm 1 bản ghi vào nguồn dữ liệu rồi re-render."""
        self._all_rows.insert(0, {
            "content":  content,
            "qr_type":  qr_type,
            "source":   source,
            "time_str": time_str,
        })
        self._apply_filter_sort()

    def add_new_row_to_top(self, content: str, qr_type: str, time_str: str):
        """Nhận lệnh từ ScanPage để thêm dòng mới (Tối ưu hóa: Không render lại toàn bộ)."""
        # 1. Chỉ cập nhật dữ liệu gốc, KHÔNG gọi _apply_filter_sort() để tránh giật lag
        self._all_rows.insert(0, {
            "content":  content,
            "qr_type":  qr_type,
            "source":   "Camera",
            "time_str": time_str,
        })

        # 2. Xử lý UI siêu nhẹ: Chỉ chèn 1 widget lên trên cùng
        selected_type = self.filter_combo.get()
        keyword = getattr(self, "search_var", ctk.StringVar()).get().strip().lower()
        
        # Đảm bảo chỉ vẽ thêm nếu dòng này khớp với bộ lọc hiện tại của người dùng
        if (selected_type == "Tất cả" or qr_type == selected_type) and \
           (not keyword or keyword in content.lower()) and \
           (not self._sort_asc):
            
            label  = f"Camera  •  {time_str}"
            widget = HistoryItemWidget(
                self.scroll_list, content, qr_type, label,
                copy_func=self.controller.copy_to_clipboard,
                delete_func=lambda w, c=content, t=time_str: self.delete_row(w, c, t),
                truncate=False,
            )
            
            # Chèn widget mới lên trên cùng của danh sách
            if self.history_widgets:
                top_widget = self.history_widgets[0][2]
                widget.pack(fill="x", pady=(0, 4), before=top_widget)
            else:
                widget.pack(fill="x", pady=(0, 4))
                
            self.history_widgets.insert(0, (content, time_str, widget))

    # ── Filter / Sort ─────────────────────────────────────────

    def _on_filter_change(self, _=None):
        self._apply_filter_sort()

    def _toggle_sort(self):
        self._sort_asc = not self._sort_asc
        # ↓ = mới nhất trên đầu (giảm dần),  ↑ = cũ nhất trên đầu (tăng dần)
        self.btn_sort_header.configure(
            text="THỜI GIAN ↑" if self._sort_asc else "THỜI GIAN ↓",
            text_color=COLOR_GREEN if self._sort_asc else "#888")
        self._apply_filter_sort()

    def _apply_filter_sort(self):
        """Xóa toàn bộ widget, lọc + sắp xếp _all_rows, vẽ lại."""
        # 1. Xóa widget cũ
        for _, _, w in self.history_widgets:
            w.destroy()
        self.history_widgets.clear()

        # 2. Lọc theo loại
        selected_type = self.filter_combo.get()
        keyword = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        rows = [
            r for r in self._all_rows
            if (selected_type == "Tất cả" or r["qr_type"] == selected_type)
            and (not keyword or keyword in r["content"].lower())
        ]

        # 3. Sắp xếp (dùng time_str làm key – định dạng HH:MM - DD/MM/YYYY)
        def parse_time(r):
            try:
                from datetime import datetime   # lazy: chỉ tải khi sort lịch sử
                return datetime.strptime(r["time_str"], "%H:%M - %d/%m/%Y")
            except Exception:
                return r["time_str"]

        rows.sort(key=parse_time, reverse=not self._sort_asc)

        # 4. Vẽ lại
        for r in rows:
            label  = f"{r['source']}  •  {r['time_str']}" if r["source"] else r["time_str"]
            widget = HistoryItemWidget(
                self.scroll_list, r["content"], r["qr_type"], label,
                copy_func=self.controller.copy_to_clipboard,
                delete_func=lambda w, c=r["content"], t=r["time_str"]: self.delete_row(w, c, t),
                truncate=False,
            )
            widget.pack(fill="x", pady=(0, 4))
            self.history_widgets.append((r["content"], r["time_str"], widget))

    def delete_row(self, widget: HistoryItemWidget, content: str, time_str: str):
        """Xóa dòng khỏi HistoryPage VÀ đồng bộ xóa dòng tương ứng ở ScanPage."""
        # 1. Xóa khỏi file
        delete_scan_log(content, time_str)

        # 2. Xóa khỏi nguồn dữ liệu gốc
        self._all_rows = [r for r in self._all_rows
                          if not (r["content"] == content and r["time_str"] == time_str)]

        # 3. Xóa widget khỏi danh sách và màn hình
        self.history_widgets = [(c, t, w) for c, t, w in self.history_widgets if w is not widget]
        widget.destroy()

        # Thông báo cho ScanPage xóa dòng tương ứng trong "Lịch sử gần đây"
        scan_page = self.controller.frames.get("ScanPage")
        if scan_page:
            scan_page.delete_history_row(content, time_str)

    def clear_all_history(self):
        """Xóa toàn bộ lịch sử khỏi file, HistoryPage và ScanPage."""
        clear_scan_logs()

        # Xóa nguồn dữ liệu gốc
        self._all_rows.clear()
        self._apply_filter_sort()

        # Đồng bộ xóa ở ScanPage
        scan_page = self.controller.frames.get("ScanPage")
        if scan_page:
            for _, _, w in list(scan_page._recent_rows):
                w.destroy()
            scan_page._recent_rows.clear()

    def _export_csv(self):
        """Nhiệm vụ: Tương tác với người dùng (Hộp thoại chọn file, Thông báo)"""
        from tkinter import filedialog, messagebox  

        # 1. Lấy dữ liệu
        logs = load_scan_logs()
        if not logs:
            messagebox.showinfo("Thông báo", "Lịch sử trống!")
            return

        # 2. Hỏi nơi lưu (UI)
        file_path = filedialog.asksaveasfilename(
            title="Lưu lịch sử",
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile="Lich_Su_Quet_QR.csv"
        )
        
        if not file_path:
            return

        # 3. Ra lệnh cho data_manager ghi file (Logic)
        try:
            export_to_csv_logic(file_path, logs)
            messagebox.showinfo("Thành công", f"Đã xuất {len(logs)} dòng ra file CSV!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất file: {e}")


# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QRCodeApp()
    app.mainloop()