"""
NHIỆM VỤ CỦA FILE QR_DECODER:
2. Sử dụng thư viện ...  để tìm kiếm và giải mã (decode) mã QR trong ảnh.
3. Trích xuất dữ liệu thô (chuỗi văn bản/link) từ mã QR.
4. (Nâng cao) Xác định tọa độ khung hình chữ nhật của mã QR để vẽ vòng bao 
   lên màn hình, giúp người dùng biết máy đã nhận diện được.
5. Trả kết quả về cho ui_manager hiển thị và data_manager lưu trữ.
"""

"""
Module: qr_decoder.py
Chức năng: Quản lý Camera, nhận diện, giải mã QR bằng AI (QReader).
Người phụ trách: Nguyễn Lê Phúc Thịnh
"""

import time
from typing import Tuple, Optional
import cv2
from qreader import QReader

class QRDecoder:
    def __init__(self, camera_index: int = 0):
        self.cap = cv2.VideoCapture(camera_index)
        self.scanned_history = {}
        self.cooldown_time = 3.0
        
        # --- THÔNG SỐ TỐI ƯU HIỆU NĂNG (FRAME SKIPPING) ---
        self.frame_count = 0
        self.frame_skip_rate = 5  # Cứ 5 frame thì AI mới quét 1 lần
        self.last_decoded_texts = []
        self.last_detections = []
        # --------------------------------------------------
        
        print("Đang khởi động AI QReader... (Lần đầu sẽ mất khoảng 5-10 giây để tải mô hình)")
        self.qreader = QReader()
        print("Tải AI thành công! Sẵn sàng quét mã nghệ thuật.")

    def _classify_data(self, content: str) -> str:
        content_upper = content.upper()
        if content_upper.startswith(("HTTP://", "HTTPS://", "WWW.")):
            return "Website"
        elif content_upper.startswith("WIFI:"):
            return "WiFi"
        elif content_upper.startswith("BEGIN:VCARD"):
            return "Liên hệ"
        else:
            return "Văn bản"

    def get_frame_and_data(self) -> Tuple[Optional[object], Optional[str], Optional[str]]:
        success, frame = self.cap.read()
        if not success:
            return None, None, None
            
        qr_data_result = None
        qr_type_result = None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # --- ÁP DỤNG THUẬT TOÁN QUÉT CÁCH NHỊP ---
        self.frame_count += 1
        # Chỉ gọi AI quét mã nếu chia hết cho frame_skip_rate
        if self.frame_count % self.frame_skip_rate == 0:
            self.last_decoded_texts, self.last_detections = self.qreader.detect_and_decode(image=frame_rgb, return_detections=True)
        # -----------------------------------------
        
        # Luôn luôn vẽ lại khung xanh dựa trên kết quả lưu từ lần quét gần nhất
        if self.last_decoded_texts:
            for i in range(len(self.last_decoded_texts)):
                qr_data = self.last_decoded_texts[i]
                if qr_data is None:
                    continue
                    
                bbox = self.last_detections[i]['bbox_xyxy']
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(frame_rgb, (x1, y1), (x2, y2), (0, 255, 0), 3) 
                
                display_text = qr_data if len(qr_data) < 25 else qr_data[:25] + "..."
                cv2.putText(frame_rgb, display_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                
                # THUẬT TOÁN COOLDOWN (Chỉ lưu lịch sử khi đủ thời gian)
                current_time = time.time()
                last_scan_time = self.scanned_history.get(qr_data, 0)
                if (current_time - last_scan_time) > self.cooldown_time:
                    self.scanned_history[qr_data] = current_time
                    qr_data_result = qr_data
                    qr_type_result = self._classify_data(qr_data)
                    
        return frame_rgb, qr_data_result, qr_type_result

    def release_camera(self):
        if self.cap.isOpened():
            self.cap.release()

# ========================================================
# PHẦN TEST ĐỘC LẬP
# ========================================================
"""
if __name__ == "__main__":
    may_quet_test = QRDecoder()
    
    while True:
        anh_rgb, noi_dung, phan_loai = may_quet_test.get_frame_and_data()

        if noi_dung is not None:
            print(f"\n[BÍP!] AI QUÉT THÀNH CÔNG:")
            print(f"- Nội dung: {noi_dung}")
            print(f"- Phân loại: {phan_loai}")
            print("-" * 30)

        if anh_rgb is not None:
            anh_bgr_de_test = cv2.cvtColor(anh_rgb, cv2.COLOR_RGB2BGR)
            cv2.imshow("Cua so Test - AI QReader", anh_bgr_de_test)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    may_quet_test.release_camera()
    cv2.destroyAllWindows()
"""