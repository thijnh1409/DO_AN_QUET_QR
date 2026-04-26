import customtkinter as ctk
import tkinter as tk
from PIL import Image
import os

# Thiết lập theme
ctk.set_appearance_mode("light")

class QRCodeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI QR Scanner Pro")
        self.geometry("1000x650") 
        self.configure(fg_color="#F7F6F2") 
        
        self.intro_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_app_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.frames = {}
        self.nav_buttons = {}
        self.assets = {}

        # --- 1. LOAD ASSETS ---
        self.load_assets()

        # Mở màn hình Intro trước
        self.setup_intro_screen()
        self.intro_frame.pack(fill="both", expand=True)

    def load_assets(self):
        # Đổi tên file thành hcmute-logo.png
        logo_path = os.path.join("assets", "hcmute-logo.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                
                # --- CHỈNH KÍCH THƯỚC LOGO TẠI ĐÂY ---
                # Tăng số này lên nếu muốn logo to hơn (VD: 300, 350)
                # Giảm số này xuống nếu muốn nhỏ lại (VD: 150, 200)
                target_width = 400
                
                # Tự động tính toán chiều cao để giữ đúng tỷ lệ ảnh gốc (không bị méo)
                ratio = target_width / float(img.size[0])
                new_h = int(float(img.size[1]) * ratio)
                
                self.assets['uni_logo'] = ctk.CTkImage(light_image=img, dark_image=img, size=(target_width, new_h))
            except Exception as e:
                print(f"Lỗi load logo: {e}")
        else:
            print(f"Không tìm thấy logo tại {logo_path}")

    def setup_intro_screen(self):
        # Khung chứa toàn bộ nội dung Intro (được tự động canh giữa màn hình)
        content = ctk.CTkFrame(self.intro_frame, fg_color="transparent")
        content.pack(expand=True)

        # 1. Logo trường ở giữa trên cùng
        if 'uni_logo' in self.assets:
            logo_lbl = ctk.CTkLabel(content, text="", image=self.assets['uni_logo'])
            logo_lbl.pack(pady=(0, 20)) # Cách tiêu đề bên dưới 20px

        # 2. Tiêu đề Đề tài
        ctk.CTkLabel(content, text="ĐỀ TÀI\nTẠO ỨNG DỤNG NHẬN DIỆN MÃ QR", 
                     font=("Space Grotesk", 28, "bold"), text_color="#0D1B2A", justify="center").pack(pady=(0, 30))

        # 3. Box Thông tin nhóm
        info_box = ctk.CTkFrame(content, fg_color="white", corner_radius=15, border_width=1, border_color="#E0DED8")
        info_box.pack(pady=10, padx=50)

        ctk.CTkLabel(info_box, text="Giảng viên hướng dẫn: Ts. Dương Minh Thiện", 
                     font=("Space Grotesk", 16, "bold"), text_color="#1D9E75").pack(pady=(20, 15), padx=60)

        members = [
            ("Lê Nguyễn Văn Hòa", "25139013"), ("Nguyễn Truy Phong", "25139031"),
            ("Nguyễn Gia Thiên Phúc", "25139034"), ("Nguyễn Lê Phúc Thịnh", "25139047"),
            ("Nguyễn Thanh Trí", "23119217")
        ]
        for name, mssv in members:
            row = ctk.CTkFrame(info_box, fg_color="transparent")
            row.pack(fill="x", padx=60, pady=4)
            ctk.CTkLabel(row, text=name, font=("Space Grotesk", 14)).pack(side="left")
            ctk.CTkLabel(row, text=mssv, font=("Space Grotesk", 14, "bold")).pack(side="right")

        ctk.CTkLabel(info_box, text="Nhóm thực hiện: Nhóm 8", font=("Space Grotesk", 12, "italic"), text_color="gray").pack(pady=20)

        # 4. Nút Bắt đầu
        ctk.CTkButton(content, text="BẮT ĐẦU QUÉT", font=("Space Grotesk", 15, "bold"),
                      fg_color="#1D9E75", hover_color="#153A30", height=50, corner_radius=12,
                      command=self.enter_main_app).pack(pady=30)

    def enter_main_app(self):
        self.intro_frame.pack_forget()
        self.main_app_frame.pack(fill="both", expand=True)
        self.setup_main_app()

    def setup_main_app(self):
        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self.main_app_frame, width=80, fg_color="#0D1B2A", corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="QR", font=("Space Grotesk", 20, "bold"), 
                                       fg_color="#1D9E75", text_color="white", width=45, height=45, corner_radius=12)
        self.logo_label.pack(pady=(20, 30))

        self.create_nav_button("scan_page", "📷\nQuét", is_active=True)
        self.create_nav_button("history_page", "🕒\nLịch sử")
        self.create_nav_button("create_page", "✨\nTạo mã")

        # Main Content
        self.main_content = ctk.CTkFrame(self.main_app_frame, fg_color="transparent", corner_radius=0)
        self.main_content.pack(side="right", fill="both", expand=True)
        
        for F in (ScanPage, HistoryPage, CreatePage):
            page_name = F.__name__
            frame = F(parent=self.main_content, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.show_page("ScanPage", "scan_page")

    def create_nav_button(self, page_id, text, is_active=False):
        color = "#5DCAA5" if is_active else "gray"
        bg_color = "#153A30" if is_active else "transparent"
        btn = ctk.CTkButton(self.sidebar_frame, text=text, font=("Space Grotesk", 12, "bold"),
                            fg_color=bg_color, text_color=color, hover_color="#1D9E75",
                            width=60, height=60, corner_radius=12,
                            command=lambda: self.show_page(page_id.replace("_page", "Page").title().replace("page", "Page"), page_id))
        btn.pack(pady=5)
        self.nav_buttons[page_id] = btn

    def show_page(self, frame_class_name, page_id):
        for pid, btn in self.nav_buttons.items():
            btn.configure(fg_color="#1D9E75" if pid == page_id else "transparent", 
                          text_color="white" if pid == page_id else "gray")
        self.frames[frame_class_name].tkraise()

# ==========================================
# CÁC TRANG CON
# ==========================================

class ScanPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        
        # 1. TOPBAR
        self.topbar = ctk.CTkFrame(self, height=75, fg_color="white", corner_radius=0)
        self.topbar.pack(fill="x", side="top")

        title_container = ctk.CTkFrame(self.topbar, fg_color="transparent")
        title_container.pack(side="left", padx=25, pady=10)
        ctk.CTkLabel(title_container, text="Quét mã QR", font=("Space Grotesk", 18, "bold"), text_color="#1a1a1a").pack(anchor="w")
        self.sub_label = ctk.CTkLabel(title_container, text="Hướng camera vào mã cần quét", font=("Space Grotesk", 12), text_color="#888")
        self.sub_label.pack(anchor="w")

        self.cam_badge = ctk.CTkFrame(self.topbar, fg_color="#F5F5F5", corner_radius=20)
        self.cam_badge.pack(side="right", padx=25)
        self.dot = ctk.CTkLabel(self.cam_badge, text="●", text_color="#999", font=("Arial", 10))
        self.dot.pack(side="left", padx=(12, 5))
        self.status_text = ctk.CTkLabel(self.cam_badge, text="Camera đang tắt", font=("Space Grotesk", 11, "bold"), text_color="#666")
        self.status_text.pack(side="left", padx=(0, 12), pady=6)

        # 2. BỐ CỤC CHÍNH
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # LEFT
        left_p = ctk.CTkFrame(container, fg_color="transparent")
        left_p.grid(row=0, column=0, sticky="nsew", padx=(25, 10), pady=20)

        self.tabs = ctk.CTkSegmentedButton(left_p, values=["Từ camera", "Từ file ảnh"], 
                                           selected_color="#0D1B2A", command=self.switch_mode)
        self.tabs.set("Từ camera")
        self.tabs.pack(pady=(0, 15))

        self.view_box = ctk.CTkFrame(left_p, fg_color="#1a1a1a", corner_radius=16)
        self.view_box.pack(fill="both", expand=True)
        self.display_label = ctk.CTkLabel(self.view_box, text="Nhấn 'Bật Camera' để bắt đầu", text_color="#555")
        self.display_label.pack(expand=True)

        self.btn_toggle = ctk.CTkButton(left_p, text="Bật Camera", fg_color="#1D9E75", corner_radius=10, 
                                        height=40, command=self.toggle_camera)
        self.btn_toggle.pack(pady=15)

        # RIGHT
        right_p = ctk.CTkFrame(container, fg_color="white", corner_radius=0)
        right_p.grid(row=0, column=1, sticky="nsew")

        res_sec = ctk.CTkFrame(right_p, fg_color="transparent")
        res_sec.pack(fill="x", padx=15, pady=20)
        ctk.CTkLabel(res_sec, text="KẾT QUẢ", font=("Space Grotesk", 10, "bold"), text_color="#aaa").pack(anchor="w")
        self.res_box = ctk.CTkFrame(res_sec, fg_color="#F7F6F2", corner_radius=10)
        self.res_box.pack(fill="x", pady=8)
        self.res_label = ctk.CTkLabel(self.res_box, text="Chưa có dữ liệu", font=("Space Grotesk", 12), text_color="#999", pady=25)
        self.res_label.pack()

        hist_sec = ctk.CTkFrame(right_p, fg_color="transparent")
        hist_sec.pack(fill="both", expand=True, padx=15)
        ctk.CTkLabel(hist_sec, text="LỊCH SỬ GẦN ĐÂY", font=("Space Grotesk", 10, "bold"), text_color="#aaa").pack(anchor="w")
        self.hist_list = ctk.CTkScrollableFrame(hist_sec, fg_color="transparent")
        self.hist_list.pack(fill="both", expand=True, pady=5)

    def toggle_camera(self):
        is_on = self.status_text.cget("text") == "Camera đang tắt"
        self.btn_toggle.configure(text="Tắt Camera" if is_on else "Bật Camera", 
                                  fg_color="#E74C3C" if is_on else "#1D9E75")
        self.cam_badge.configure(fg_color="#EAF3DE" if is_on else "#F5F5F5")
        self.dot.configure(text_color="#639922" if is_on else "#999")
        self.status_text.configure(text="Camera đang hoạt động" if is_on else "Camera đang tắt",
                                   text_color="#3B6D11" if is_on else "#666")
        self.display_label.configure(text="[ Luồng camera thực tế ]" if is_on else "Nhấn 'Bật Camera' để bắt đầu")

    def switch_mode(self, mode):
        if mode == "Từ file ảnh":
            self.sub_label.configure(text="Tải ảnh chứa mã QR lên để quét")
            self.display_label.configure(text="Nhấp để chọn file ảnh")
            self.btn_toggle.pack_forget()
            self.cam_badge.pack_forget()
        else:
            self.sub_label.configure(text="Hướng camera vào mã cần quét")
            self.display_label.configure(text="Nhấn 'Bật Camera' để bắt đầu")
            self.btn_toggle.pack(pady=15)
            self.cam_badge.pack(side="right", padx=25)

class HistoryPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        
        self.topbar = ctk.CTkFrame(self, height=75, fg_color="white", corner_radius=0)
        self.topbar.pack(fill="x", side="top")
        
        title_container = ctk.CTkFrame(self.topbar, fg_color="transparent")
        title_container.pack(side="left", padx=25, pady=10)
        ctk.CTkLabel(title_container, text="Lịch sử quét", font=("Space Grotesk", 18, "bold"), text_color="#1a1a1a").pack(anchor="w")
        ctk.CTkLabel(title_container, text="Quản lý và tra cứu các mã QR đã quét", font=("Space Grotesk", 12), text_color="#888").pack(anchor="w")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=25, pady=20)
        
        self.toolbar = ctk.CTkFrame(self.body, fg_color="transparent", height=50)
        self.toolbar.pack(fill="x", pady=(0, 15))
        
        self.search_entry = ctk.CTkEntry(self.toolbar, placeholder_text="🔍 Tìm kiếm nội dung...", width=250, height=40, 
                                         font=("Space Grotesk", 13), fg_color="white", border_width=1, border_color="#E0DED8", corner_radius=8)
        self.search_entry.pack(side="left")
        
        self.filter_combo = ctk.CTkComboBox(self.toolbar, values=["Tất cả", "URL", "Văn bản", "Liên hệ", "WiFi"], width=120, height=40, 
                                            font=("Space Grotesk", 13), fg_color="white", border_width=1, border_color="#E0DED8", 
                                            button_color="#F7F6F2", button_hover_color="#E0DED8", corner_radius=8)
        self.filter_combo.pack(side="left", padx=10)
        
        self.btn_clear = ctk.CTkButton(self.toolbar, text="🗑 Xóa tất cả", font=("Space Grotesk", 13, "bold"), width=110, height=40, 
                                       fg_color="#FDE8E8", text_color="#C0392B", hover_color="#FAD1D1", corner_radius=8,
                                       command=self.clear_all_history)
        self.btn_clear.pack(side="right")

        self.btn_export = ctk.CTkButton(self.toolbar, text="📥 Xuất CSV", font=("Space Grotesk", 13, "bold"), width=110, height=40, 
                                        fg_color="#EAF3DE", text_color="#3B6D11", hover_color="#D5E8C1", corner_radius=8)
        self.btn_export.pack(side="right", padx=10)

        self.list_frame = ctk.CTkFrame(self.body, fg_color="white", corner_radius=12, border_width=1, border_color="#E0DED8")
        self.list_frame.pack(fill="both", expand=True)
        
        header_frame = ctk.CTkFrame(self.list_frame, fg_color="#F7F6F2", height=40, corner_radius=0)
        header_frame.pack(fill="x", padx=2, pady=2)
        ctk.CTkLabel(header_frame, text="NỘI DUNG MÃ QR", font=("Space Grotesk", 11, "bold"), text_color="#888").pack(side="left", padx=(65, 0))
        ctk.CTkLabel(header_frame, text="THAO TÁC", font=("Space Grotesk", 11, "bold"), text_color="#888").pack(side="right", padx=(0, 25))
        ctk.CTkLabel(header_frame, text="THỜI GIAN", font=("Space Grotesk", 11, "bold"), text_color="#888").pack(side="right", padx=(0, 100))

        self.scroll_list = ctk.CTkScrollableFrame(self.list_frame, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.history_widgets = []
        self.load_dummy_data()

    def load_dummy_data(self):
        self.add_history_row("https://github.com/thijnh1409", "URL", "Camera", "14:30 - 26/04/2026")
        self.add_history_row("0901234567", "Liên hệ", "File ảnh", "10:15 - 25/04/2026")
        self.add_history_row("Xin chào các bạn nhóm 8, đồ án tuyệt quá!", "Văn bản", "Camera", "09:00 - 24/04/2026")

    def add_history_row(self, content, qr_type, source, time_str):
        row = ctk.CTkFrame(self.scroll_list, fg_color="transparent", height=50)
        row.pack(fill="x", pady=2)
        
        if qr_type == "URL":
            bg_color, fg_color, icon = "#EAF3DE", "#3B6D11", "🔗"
        elif qr_type == "Liên hệ":
            bg_color, fg_color, icon = "#E8F0FE", "#1A73E8", "📞"
        elif qr_type == "WiFi":
            bg_color, fg_color, icon = "#F3E8FF", "#8E24AA", "📶"
        else:
            bg_color, fg_color, icon = "#FEF0DB", "#E67C22", "📄"

        icon_box = ctk.CTkLabel(row, text=icon, font=("Arial", 16), fg_color=bg_color, width=36, height=36, corner_radius=8)
        icon_box.pack(side="left", padx=(5, 15))
        
        badge = ctk.CTkLabel(row, text=qr_type, font=("Space Grotesk", 10, "bold"), text_color=fg_color, fg_color=bg_color, corner_radius=6, width=60, height=22)
        badge.pack(side="left", padx=(0, 15))

        display_content = content if len(content) < 45 else content[:42] + "..."
        ctk.CTkLabel(row, text=display_content, font=("Space Grotesk", 14, "bold"), text_color="#1a1a1a", anchor="w").pack(side="left")
        
        ctk.CTkButton(row, text="🗑", font=("Arial", 14), width=35, height=35, fg_color="transparent", text_color="#aaa", hover_color="#FDE8E8", 
                      command=lambda r=row: self.delete_row(r)).pack(side="right", padx=(5, 10))
        ctk.CTkButton(row, text="📋", font=("Arial", 14), width=35, height=35, fg_color="transparent", text_color="#aaa", hover_color="#F5F5F5", 
                      command=lambda c=content: self.copy_to_clipboard(c)).pack(side="right", padx=5)
        
        ctk.CTkLabel(row, text=f"{source}  •  {time_str}", font=("Space Grotesk", 12), text_color="#888").pack(side="right", padx=20)
        
        line = ctk.CTkFrame(self.scroll_list, height=1, fg_color="#F5F4F0")
        line.pack(fill="x", padx=10, pady=2)

        self.history_widgets.append((row, line))

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        print(f"Đã copy: {text}")

    def delete_row(self, row_widget):
        for row, line in self.history_widgets:
            if row == row_widget:
                row.destroy()
                line.destroy()
                self.history_widgets.remove((row, line))
                break

    def clear_all_history(self):
        for row, line in self.history_widgets:
            row.destroy()
            line.destroy()
        self.history_widgets.clear()

class CreatePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        ctk.CTkLabel(self, text="Trang Tạo Mã (Đang phát triển)", font=("Space Grotesk", 20)).pack(expand=True)

if __name__ == "__main__":
    app = QRCodeApp()
    app.mainloop()