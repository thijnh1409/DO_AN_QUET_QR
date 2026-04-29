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
    now = datetime.now()
    time_str = now.strftime("%H:%M - %d/%m/%Y")

    stt = 1
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            valid_lines = [line for line in lines if line.strip() != ""]
            if valid_lines:
                stt = len(valid_lines) + 1

    # VÁ LỖI XUỐNG DÒNG: Thay thế \n bằng ký hiệu đặc biệt (vd: \u2028) hoặc <br>
    safe_content = str(content).replace("\r\n", "<br>").replace("\n", "<br>")

    log_entry = f"{stt} | {time_str} | {qr_type} | {source} | {safe_content}\n"

    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)

    return time_str

def load_scan_logs():
    logs = []
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() == "":
                    continue
                
                # VÁ LỖI DẤU | : Cắt tối đa 4 lần để giữ nguyên nội dung cột cuối
                parts = line.split("|", 4)
                
                if len(parts) >= 5:
                    # Phục hồi lại ký tự xuống dòng khi đưa lên UI
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
    Xóa toàn bộ lịch sử trong file.
    """
    if os.path.exists(LOG_FILE_PATH):
        # Ghi đè file bằng nội dung rỗng
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("")

def delete_scan_log(content, time_str):
    try:
        logs = load_scan_logs()
        new_logs = [log for log in logs if not (log["content"] == content and log["time"] == time_str)]
        
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            for index, log in enumerate(new_logs):
                stt = index + 1
                # Ghi lại y hệt hàm save, phải mã hóa lại \n
                safe_content = log['content'].replace("\r\n", "<br>").replace("\n", "<br>")
                f.write(f"{stt} | {log['time']} | {log['type']} | {log['source']} | {safe_content}\n")
                
    except Exception as e:
        print(f"Lỗi khi xóa dòng lịch sử: {e}")

def export_to_csv_logic(file_path, logs):
    """Nhiệm vụ: Chỉ ghi dữ liệu ra file, không hiện thông báo UI"""
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