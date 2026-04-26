import os
import sys
from datetime import datetime

# Lấy thư mục gốc chứa file .exe đang chạy (hoặc file .py nếu đang dev)
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

LOG_FILE_PATH = os.path.join(application_path, "scan_logs.txt")

def save_scan_log(content, qr_type, source="Camera"):
    """
    Lưu dữ liệu quét mã QR vào file text.
    Định dạng: STT | Thời gian | Loại mã | Nguồn | Nội dung
    """
    # 1. Lấy thời gian hiện tại
    now = datetime.now()
    time_str = now.strftime("%H:%M - %d/%m/%Y")

    # 2. Đọc file để xác định Số Thứ Tự (STT) tiếp theo
    stt = 1
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Lọc bỏ các dòng trống
            valid_lines = [line for line in lines if line.strip() != ""]
            if valid_lines:
                try:
                    # Lấy dòng cuối cùng, cắt ra để lấy số thứ tự
                    last_line = valid_lines[-1]
                    last_stt = int(last_line.split("|")[0].strip())
                    stt = last_stt + 1
                except ValueError:
                    stt = len(valid_lines) + 1

    # 3. Tạo chuỗi dữ liệu (Ngăn cách nhau bằng dấu | để dễ đọc lại)
    log_entry = f"{stt} | {time_str} | {qr_type} | {source} | {content}\n"

    # 4. Ghi nối (append) vào file
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)

    return time_str # Trả về thời gian để cập nhật lên UI

def load_scan_logs():
    """
    Đọc dữ liệu từ file text để đưa lên giao diện Lịch sử.
    """
    logs = []
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() == "":
                    continue
                parts = [p.strip() for p in line.split("|")]
                
                # Đảm bảo dòng có đủ 5 cột dữ liệu
                if len(parts) >= 5:
                    logs.append({
                        "stt": parts[0],
                        "time": parts[1],
                        "type": parts[2],
                        "source": parts[3],
                        "content": parts[4]
                    })
    return logs

def clear_scan_logs():
    """
    Xóa toàn bộ lịch sử trong file.
    """
    if os.path.exists(LOG_FILE_PATH):
        # Ghi đè file bằng nội dung rỗng
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("")

if __name__ == "__main__":
    # Test thử file độc lập
    print("Test ghi dữ liệu...")
    save_scan_log("https://hcmute.edu.vn", "URL", "Camera")
    save_scan_log("0912345678", "Liên hệ", "File ảnh")
    print("Dữ liệu đã lưu:")
    print(load_scan_logs())