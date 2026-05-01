from ui_manager import QRCodeApp

if __name__ == "__main__":
    print("Đang khởi động Ứng dụng Quét mã QR...")
    
    # Khởi tạo cửa sổ giao diện chính
    app = QRCodeApp()
    
    # Bắt đầu vòng lặp chạy ứng dụng
    app.mainloop()