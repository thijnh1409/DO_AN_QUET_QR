"""
NHIỆM VỤ CỦA FILE DATA_MANAGER:
1. Nhận dữ liệu từ qr_decoder.py sau khi quét thành công.
2. Lấy thời gian hiện tại từ hệ thống.
3. Ghi dữ liệu vào file 'scan_logs.txt' theo định dạng:
    [STT]: Số thứ tự (1, 2, 3...)
    [Thời gian]: Ngày giờ quét (VD: 11/04 10:00)
    [Loại mã]: Phân loại xem nó là cái gì (VD: Website, WiFi, Văn bản, Thẻ liên hệ...)
    [Nội dung]: Cục dữ liệu gốc quét được (VD: https://hcmute.edu.vn)
4. Lưu ý: Dùng chế độ 'a' (append) để không làm mất dữ liệu cũ.
"""
"""
Những thư viện cần tham khảo: datetime, pathlib, csv, ...
"""
import datetime
LOG_FILE_PATH = "scan_logs.txt"
def lay_stt():
    try:
        with open(LOG_FILE_PATH,"r",encoding="utf-8") as f:
            dongs=f.readlines()
            so_dong=0
            for dong in dongs:
                if dong.strip():
                    so_dong+=1
        return so_dong +1
    except FileNotFoundError:
        return 1
    except Exception as e:
        print("Lỗi khác")
        return 1
def phan_loai_ma(du_lieu):
    du_lieu_check = du_lieu.upper()#VIẾT HOA ĐỂ DỄ SO SÁNH
    if du_lieu_check.startswith(("HTTP://", "HTTPS://")):
        return "Website"
    elif du_lieu_check.startswith("WIFI:"):
        return "WiFi"
    elif du_lieu_check.startswith("TEL:"):
        return "Số điện thoại"
    elif du_lieu_check.strip().startswith("BEGIN:VCARD"):
        return "Thẻ liên hệ"
    else:
        return "Văn bản"
def luu_du_lieu(du_lieu_quet):
    if not du_lieu_quet:
        print("Dữ liệu trống, không lưu!")
        return
    stt=lay_stt()#Lây số
    bay_gio=datetime.datetime.now().strftime("%d/%m %H:%M")## %d/%m: Ngày/Tháng, %H:%M: Giờ:Phút
    loai_ma=phan_loai_ma(du_lieu_quet)#phân loại
    text_luu=f"[{stt}] | [{bay_gio}] | [{loai_ma}] | [{du_lieu_quet}]\n"
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(text_luu)
        print(f"Đã lưu thành công mã số {stt}")
    except FileNotFoundError:
        print("Không thấy file")
    except Exception as e:
        print("Lỗi khác")
