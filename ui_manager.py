"""
NHIỆM VỤ CỦA FILE UI_MANAGER:
1. Tạo cửa sổ ứng dụng chính (sử dụng thư viện Tkinter).
3. Thiết kế hệ thống nút bấm điều khiển: Start Scan, Reset, Exit.
4. Hiển thị nội dung mã QR quét được ngay trên màn hình ứng dụng.
5. Kết nối: Gọi hàm từ qr_decoder.py để lấy dữ liệu và data_manager.py để lưu.

Lưu ý: Sử dụng hàm .after() của Tkinter để cập nhật frame hình ảnh liên tục 
mà không làm treo giao diện (Not Responding).
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class QRCodeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ứng dụng nhận diện mã QR")
        self.geometry("850x550")

        self.bg_image = Image.open("Bg.png")
        self.bg_image = self.bg_image.resize((850, 550))
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        self.frames = {} 

        self.intro_frame = tk.Frame(self)
        self.main_app_frame = tk.Frame(self)

        self.setup_intro_screen()
        self.intro_frame.pack(fill="both", expand=True)
    def show_page(self, page_name):
        for name, btn in self.nav_buttons.items():
            if name == page_name:
                btn.configure(bg="#A9D1C1", fg="white")
            else:
                btn.configure(bg="#FFFFFF", fg="black")

    # hiển thị frame
        frame = self.frames[page_name]
        frame.tkraise()

    def setup_intro_screen(self):
        canvas = tk.Canvas(self.intro_frame, width=850, height=550, highlightthickness=0)
        canvas.pack()

        canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)

        canvas.create_text(425, 100,
                           text="ĐỀ TÀI\nTẠO ỨNG DỤNG NHẬN DIỆN MÃ QR",
                           font=("Arial", 20, "bold"),
                           anchor="center",
                           justify="center")

        canvas.create_text(830, 20,
                           text="Nhóm thực hiện: Nhóm 8",
                           font=("Arial", 10),
                           anchor="ne")

        canvas.create_text(425, 180,
                           text="Giảng viên hướng dẫn: Ts. Dương Minh Thiện",
                           font=("Arial", 14))
        canvas.create_text(300, 250, text="Lê Nguyễn Văn Hòa", anchor="w", font=("Arial", 12))
        canvas.create_text(500, 250, text="25139013", anchor="w", font=("Arial", 12))

        canvas.create_text(300, 280, text="Nguyễn Truy Phong", anchor="w", font=("Arial", 12))
        canvas.create_text(500, 280, text="25139031", anchor="w", font=("Arial", 12))

        canvas.create_text(300, 310, text="Nguyễn Gia Thiên Phúc", anchor="w", font=("Arial", 12))
        canvas.create_text(500, 310, text="25139034", anchor="w", font=("Arial", 12))

        canvas.create_text(300, 340, text="Nguyễn Lê Phúc Thịnh", anchor="w", font=("Arial", 12))
        canvas.create_text(500, 340, text="25139047", anchor="w", font=("Arial", 12))

        canvas.create_text(300, 370, text="Nguyễn Thanh Trí", anchor="w", font=("Arial", 12))
        canvas.create_text(500, 370, text="23119217", anchor="w", font=("Arial", 12))

        btn = tk.Button(self.intro_frame, text="Start",
                        font=("Arial", 12, "bold"),
                        bg="#8CDC8F",
                        fg="white",
                        bd=0,
                        command=self.enter_main_app)

        canvas.create_window(425, 450, window=btn, width=100, height=30)

    def enter_main_app(self):
        self.intro_frame.pack_forget()
        self.main_app_frame.pack(fill="both", expand=True)
        self.setup_main_app()

    def setup_main_app(self):
        self.nav_buttons = {}

        # sidebar
        sidebar = tk.Frame(self.main_app_frame, bg="#A5C1BA", width=200)
        sidebar.pack(side="left", fill="y")

        tk.Label(sidebar, text="QR SCANNER", font=("Arial", 16)).pack(pady=20)

        btn_scan = tk.Button(sidebar, text="Quét mã", font=("Arial", 12),
                         bg="#FFFFFF",
                         command=lambda: self.show_page("scan_page"))
        btn_scan.pack(fill="x", pady=5, ipady=10)
        self.nav_buttons["scan_page"] = btn_scan

        btn_history = tk.Button(sidebar, text="Lịch sử", font=("Arial", 12),
                            bg="#FFFFFF",
                            command=lambda: self.show_page("history_page"))
        btn_history.pack(fill="x", pady=5, ipady=10)
        self.nav_buttons["history_page"] = btn_history

        btn_create = tk.Button(sidebar, text="Tạo mã", font=("Arial", 12),
                           bg="#FFFFFF",
                           command=lambda: self.show_page("create_page"))
        btn_create.pack(fill="x", pady=5, ipady=10)
        self.nav_buttons["create_page"] = btn_create

        self.content_frame = tk.Frame(self.main_app_frame, bg="white")
        self.content_frame.pack(side="right", fill="both", expand=True)

    # tạo các trang
        for F in (scan_page, history_page, create_page):
            frame = F(self.content_frame)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.show_page("scan_page")

class scan_page(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.bg_image = Image.open("Scan.png")
        self.bg_image = self.bg_image.resize((850, 550))
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        bg_label = tk.Label(self, image=self.bg_photo)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.camera_label = tk.Label(self, bg="black")
        self.camera_label.place(relx=0.5, rely=0.386, width=180, height=228, anchor="center")

        # sự kiện click chuột trái
        self.bind_all("<Button-1>", self.check_click)

    def check_click(self, event):
        x, y = event.x, event.y #xác định tọa độ xy
        x0, y0 = 353, 489 #Tọa độ tâm
        r = 30 #bán kính 

        if (x - x0)**2 + (y - y0)**2 <= r**2:
            self.bat_camera() #Khi click trúng biểu tượng thực hiện def bat_camera
    def bat_camera(self):
            print("Đã bật camera!")

class history_page(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.bg_image = Image.open("History.png")
        self.bg_image = self.bg_image.resize((850, 550))
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)

        bg_label = tk.Label(self, image=self.bg_photo)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 14, "bold"))

        tk.Label(self, text="LỊCH SỬ QUÉT MÃ",
                 font=("Arial", 16, "bold"),
                 bg="white").pack(pady=10)

        columns = ("stt", "thoi_gian", "loai_ma", "noi_dung")

        self.tree = ttk.Treeview(self, columns=columns, show="headings")

        self.tree.heading("stt", text="STT")
        self.tree.heading("thoi_gian", text="Thời gian")
        self.tree.heading("loai_ma", text="Loại mã")
        self.tree.heading("noi_dung", text="Nội dung")

        self.tree.column("stt", width=50, anchor="center")
        self.tree.column("thoi_gian", width=150, anchor="center")
        self.tree.column("loai_ma", width=120, anchor="center")
        self.tree.column("noi_dung", width=300, anchor="w")

        self.tree.pack(fill="both", expand=True, padx=20, pady=10)


class create_page(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="white")
        tk.Label(self, text="Coming Soon", font=("Arial", 30), fg="gray", bg="white").pack(expand=True)


if __name__ == "__main__":
    app = QRCodeApp()
    app.mainloop()
