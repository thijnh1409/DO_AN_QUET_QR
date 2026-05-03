import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Cấu hình Đường dẫn an toàn (Hỗ trợ đóng gói PyInstaller)
# ---------------------------------------------------------------------------

# Kiểm tra xem phần mềm đang chạy dưới dạng file exe hay file .py
# - Nếu là .exe (frozen): Lấy thư mục chứa file exe để lưu log.
# - Nếu là .py (dev): Lấy thư mục hiện tại của file code.
# Việc này giúp file scan_logs.txt luôn đi theo app sang máy khác mà không bị lỗi đường dẫn.
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

LOG_FILE_PATH = os.path.join(application_path, "scan_logs.txt")

# ---------------------------------------------------------------------------
# CÁC HÀM XỬ LÝ DỮ LIỆU LỊCH SỬ (I/O)
# ---------------------------------------------------------------------------

def save_scan_log(content, qr_type, source="Camera"):
    """
    Lưu một bản ghi mới vào file scan_logs.txt với định dạng:
    STT | Thời gian | Loại mã QR | Nguồn quét | Nội dung
    
    - STT: Số thứ tự tự động tăng, bắt đầu từ 1.
    - Thời gian: Định dạng "HH:MM - DD/MM/YYYY".
    - Loại mã QR: Ví dụ "Website", "Văn bản", "WiFi", v.v.
    - Nguồn quét: Mặc định là "Camera", có thể thay đổi thành "File ảnh".
    - Nội dung: Tự động mã hóa các dấu xuống dòng (\n) thành thẻ <br> để bảo vệ cấu trúc file text. (Sẽ được giải mã lại khi load lên giao diện).
    """

    now = datetime.now()
    time_str = now.strftime("%H:%M - %d/%m/%Y")

    stt = 1 # Mặc định là 1, nếu file đã có dữ liệu sẽ được cập nhật lại sau khi đọc số dòng hiện tại. Điều này đảm bảo STT luôn liên tục và không bị trùng lặp khi thêm mới.
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            valid_lines = [line for line in lines if line.strip() != ""]
            if valid_lines:
                stt = len(valid_lines) + 1

    # Để tránh lỗi khi nội dung có dấu xuống dòng, chúng ta sẽ thay thế \n bằng <br> 
    # trước khi lưu vào file. 
    # Khi hiển thị trên UI, chúng ta sẽ phục hồi lại \n từ <br>.
    safe_content = str(content).replace("\r\n", "<br>").replace("\n", "<br>")

    log_entry = f"{stt} | {time_str} | {qr_type} | {source} | {safe_content}\n"

    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)

    return time_str

def load_scan_logs():
    """
    Đọc toàn bộ lịch sử từ file scan_logs.txt và trả về danh sách các từ điển (list of dicts).
    Cấu trúc dữ liệu trả về:
    [
        {
            "stt": "1",
            "time": "14:00 - 08/05/2026",
            "type": "Website",
            "source": "Camera",
            "content": "https://hcmute.edu.vn/"
        },
        ...
    ]
    """

    logs = []
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() == "":
                    continue
                
                # VÁ LỖI DẤU | : Cắt tối đa 4 lần để giữ nguyên nội dung cột cuối
                parts = line.split("|", 4)
                
                if len(parts) >= 5:
                    # Phục hồi lại ký tự xuống dòng (từ <br> về \n) khi đưa lên màn hình UI
                    original_content = parts[4].strip().replace("<br>", "\n")
                    
                    logs.append({
                        "stt": parts[0].strip(),
                        "time": parts[1].strip(),
                        "type": parts[2].strip(),
                        "source": parts[3].strip(),
                        "content": original_content
                    })
    return logs

def clear_scan_logs():
    """
    Xóa sạch toàn bộ lịch sử quét.
    - Cơ chế: Ghi đè nội dung rỗng vào file thay vì xóa hẳn file, giúp tránh lỗi FileNotFoundError ở các lần ghi tiếp theo.
    - Lưu ý: Thao tác này là vĩnh viễn, không thể hoàn tác.
    """
    if os.path.exists(LOG_FILE_PATH):
        # Ghi đè file bằng nội dung rỗng
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("")

def delete_scan_log(content, time_str):
    """
    Xóa bản ghi lịch sử cụ thể dựa vào nội dung và thời điểm quét.
    - Cơ chế: Lọc bỏ các dòng trùng khớp, sau đó ghi đè lại toàn bộ dữ liệu vào file và tự động đánh lại Số thứ tự (STT).
    - Tác dụng phụ: Nếu có nhiều dòng trùng khớp hoàn toàn cả nội dung lẫn thời gian, tất cả chúng đều sẽ bị xóa.
    - Lưu ý: Không thể hoàn tác.
    """
    try:
        logs = load_scan_logs()
        # Tạo một danh sách mới chỉ chứa các log không trùng với nội dung và thời gian cần xóa
        new_logs = [log for log in logs if not (log["content"] == content and log["time"] == time_str)]
        
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            for index, log in enumerate(new_logs):
                stt = index + 1
                # Ghi lại y hệt hàm save, phải mã hóa lại \n thành <br>
                safe_content = log['content'].replace("\r\n", "<br>").replace("\n", "<br>")
                f.write(f"{stt} | {log['time']} | {log['type']} | {log['source']} | {safe_content}\n")
                
    except Exception as e:
        print(f"Lỗi khi xóa dòng lịch sử: {e}")

def export_to_csv_logic(file_path, logs):
    """ 
    Trích xuất bộ dữ liệu lịch sử (list of dicts) ra định dạng file .csv.
    - Cấu trúc: STT, Thời gian, Loại mã QR, Nguồn quét, Nội dung.
    - Khối xử lý này chỉ chịu trách nhiệm Ghi file (Logic/I-O), 
    không chứa các đoạn code hiển thị thông báo hay tương tác với Giao diện (UI).
    """
    import csv
    # Dùng 'utf-8-sig' để hỗ trợ tiếng Việt trên Excel
    with open(file_path, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(["STT", "Thời gian", "Loại mã QR", "Nguồn quét", "Nội dung"])
        for log in logs:
            writer.writerow([
                log.get("stt", ""), 
                log.get("time", ""), 
                log.get("type", ""), 
                log.get("source", ""), 
                log.get("content", "")
            ])