import time
import threading
import queue
import gc
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
from qreader import QReader

# ---------------------------------------------------------------------------
# Cấu trúc dữ liệu trả về 
# Dùng @dataclass ở đây hoạt động rất giống với 'struct' trong C/C++, 
# giúp nhóm dễ dàng truy xuất các trường dữ liệu (vd: result.data, result.frame)
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    frame: Optional[object]   # np.ndarray (RGB) or None if camera failed
    data: Optional[str]       # decoded QR content, or None
    data_type: Optional[str]  # e.g. "Website", "WiFi", "Văn bản", or None


# ---------------------------------------------------------------------------
# Cấu trúc lưu tạm kết quả (Snapshot) dùng chung giữa 2 luồng Camera và AI
# ---------------------------------------------------------------------------

@dataclass
class _DetectionSnapshot:
    texts: list
    detections: list


# ---------------------------------------------------------------------------
# LỚP XỬ LÝ CHÍNH: Quét mã QR từ Camera (Chạy đa luồng)
# ---------------------------------------------------------------------------

class QRDecoder:
    """
    Bộ giải mã QR hoạt động trên 2 luồng (Thread) song song:
    - Luồng chính: Đọc ảnh từ Camera siêu nhanh và vẽ khung xanh lên màn hình.
    - Luồng AI (ngầm): Lấy ảnh ra để mô hình QReader phân tích (chậm hơn, 0.1-0.5s).
    """

    MAX_HISTORY_SIZE = 500   # Giới hạn số lượng mã lưu trong RAM để chống tràn bộ nhớ
    COOLDOWN_TIME    = 3.0   # Chống spam: Phải đợi 3 giây mới được quét lại cùng 1 mã QR
    DISPLAY_MAX_LEN  = 25    # Cắt ngắn số ký tự nếu muốn hiển thị chữ lên khung Camera

    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index   # Lưu lại ID thiết bị để dùng khi bật/tắt camera
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            print("CẢNH BÁO: Không tìm thấy Camera! Vui lòng kiểm tra lại thiết bị.")

        self.scanned_history: dict[str, float] = {}

        """ Khóa an toàn (Lock): Ngăn chặn lỗi xung đột bộ nhớ khi luồng AI đang ghi 
            kết quả mà luồng Camera lại nhảy vào đọc."""
        self._lock = threading.Lock()
        self._snapshot = _DetectionSnapshot(texts=[], detections=[])

        """ Hàng đợi chứa ảnh (Queue) với maxsize=1 cực kỳ quan trọng:
        Giúp tự động vứt bỏ các khung hình cũ, luồng AI sẽ luôn chỉ xử lý ảnh mới nhất -> Chống lag"""
        self._frame_queue: queue.Queue = queue.Queue(maxsize=1)
        self._running = True

        print("Đang khởi động AI QReader... Xin vui lòng đợi...")
        self.qreader = QReader()
        print("Tải AI thành công! Sẵn sàng quét mã.")

        # Khởi tạo và kích hoạt luồng AI chạy ngầm. (daemon=True: tự động tắt khi đóng app)
        self._ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self._ai_thread.start()

    # ------------------------------------------------------------------
    # Hỗ trợ Context-manager (with ... as ...): Tự động dọn rác khi có lỗi
    # ------------------------------------------------------------------
    def __enter__(self) -> "QRDecoder":
        return self

    def __exit__(self, *_) -> None:
        self.shutdown()

    # ------------------------------------------------------------------
    # LUỒNG AI CHẠY NGẦM - Xử lý ảnh và cập nhật kết quả một cách an toàn
    # ------------------------------------------------------------------

    def _ai_worker(self) -> None:
        """Luồng AI chạy ngầm liên tục lấy ảnh mới nhất từ hàng đợi, giải mã QR bằng QReader, 
        và cập nhật snapshot kết quả một cách an toàn bằng Lock.
        - Luồng này sẽ không bị lag dù camera có nhiều khung hình mới, 
        vì hàng đợi chỉ giữ 1 khung hình mới nhất, các khung cũ sẽ tự động bị vứt bỏ nếu chưa kịp xử lý.
        - Nếu có lỗi trong quá trình xử lý (vd: lỗi mô hình AI), sẽ được bắt và in ra console, 
        nhưng luồng sẽ tiếp tục chạy để không làm gián đoạn trải nghiệm người dùng.
        """
        while self._running:
            try:
                # Đứng đợi ảnh mới trong 0.5s, nếu có thì lấy ra
                frame_rgb = self._frame_queue.get(timeout=0.5)
                texts, detections = self.qreader.detect_and_decode(
                    image=frame_rgb, return_detections=True
                )
                # Cập nhật snapshot một cách an toàn bằng Lock để tránh xung đột với luồng Camera
                with self._lock:
                    self._snapshot = _DetectionSnapshot(
                        texts=list(texts),
                        detections=list(detections),
                    )
            except queue.Empty:
                continue
            except Exception as exc:
                print(f"Lỗi ở luồng AI: {exc}")

    # ------------------------------------------------------------------
    # Phân loại dữ liệu quét được
    # ------------------------------------------------------------------

    @staticmethod # Dùng staticmethod vì không cần truy cập self, giúp code gọn hơn và dễ hiểu hơn
    def classify_data(content: str) -> str:
        upper = content.upper()
        if upper.startswith(("HTTP://", "HTTPS://", "WWW.")):
            return "Website"
        if upper.startswith("WIFI:"):
            return "WiFi"
        if upper.startswith("BEGIN:VCARD"):
            return "Liên hệ"
        return "Văn bản"

    # ------------------------------------------------------------------
    # Hệ thống chống spam: 
    # Kiểm tra xem mã QR này đã được quét gần đây chưa (trong vòng COOLDOWN_TIME)
    # ------------------------------------------------------------------

    def _check_cooldown(self, qr_data: str) -> bool:
        """Trả về True nếu mã QR này chưa được quét trong vòng COOLDOWN_TIME (mặc định 3s), ngược lại trả về False.
        - Nếu trả về True, hàm sẽ cập nhật thời điểm quét mới nhất cho mã này.
        - Đồng thời, hàm tự động dọn dẹp (xóa mã cũ nhất) nếu lịch sử lưu trữ vượt quá MAX_HISTORY_SIZE để chống tràn bộ nhớ (RAM).
        """
        now = time.time()
        if (now - self.scanned_history.get(qr_data, 0)) > self.COOLDOWN_TIME:
            # Dọn dẹp lịch sử cũ để tránh tràn bộ nhớ (nếu có quá nhiều mã đã quét)
            if len(self.scanned_history) >= self.MAX_HISTORY_SIZE:
                oldest_key = next(iter(self.scanned_history))
                del self.scanned_history[oldest_key]
            # Cập nhật thời điểm quét mới nhất cho mã này
            self.scanned_history[qr_data] = now
            return True
        return False

    # ------------------------------------------------------------------
    # LUỒNG CAMERA CHÍNH (Giao tiếp với phần giao diện)
    # ------------------------------------------------------------------

    def get_frame_and_data(self) -> ScanResult:
        """
        Đọc khung hình mới nhất từ Camera, khoanh vùng mã QR (nếu có) và xuất kết quả.
        Trả về đối tượng ScanResult bao gồm:
        - frame: Ảnh RGB đã vẽ khung định vị (hoặc None nếu lỗi Camera).
        - data: Nội dung giải mã (hoặc None nếu không có mã / bị chặn bởi Cooldown).
        - data_type: Phân loại dữ liệu ("Website", "WiFi", "Văn bản"... hoặc None).
        """
        success, frame = self.cap.read()
        if not success:
            return ScanResult(frame=None, data=None, data_type=None)

        # Chuyển ảnh sang RGB để AI xử lý (OpenCV mặc định là BGR)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Cố gắng đưa khung hình mới nhất vào hàng đợi để luồng AI xử lý, nếu hàng đợi đã đầy thì bỏ qua (để tránh lag)
        if self._frame_queue.empty():
            try:
                self._frame_queue.put_nowait(frame_rgb)
            except queue.Full:
                pass

        # Lấy snapshot kết quả từ luồng AI một cách an toàn bằng Lock để tránh xung đột bộ nhớ
        with self._lock:
            snapshot = _DetectionSnapshot(
                texts=list(self._snapshot.texts),
                detections=list(self._snapshot.detections),
            )

        qr_data_result: Optional[str] = None
        qr_type_result: Optional[str] = None

        # Vẽ khung xanh lên các mã QR được phát hiện và 
        # phân loại dữ liệu (nếu có) để trả về cho giao diện hiển thị.
        for qr_data, detection in zip(snapshot.texts, snapshot.detections):
            if qr_data is None:
                continue
            
            # Vẽ khung vuông xanh lá (0, 255, 0) xung quanh mã QR được phát hiện
            x1, y1, x2, y2 = map(int, detection["bbox_xyxy"])
            cv2.rectangle(frame_rgb, (x1, y1), (x2, y2), (0, 255, 0), 3)

            # label = qr_data if len(qr_data) < self.DISPLAY_MAX_LEN else qr_data[:self.DISPLAY_MAX_LEN] + "…"
            # cv2.putText(frame_rgb, label, (x1, y1 - 10),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            if self._check_cooldown(qr_data):
                # Ghi nhận kết quả của mã đầu tiên thỏa mãn điều kiện thời gian chờ
                # Nếu có nhiều mã QR cùng lúc, chỉ mã đầu tiên được quét sẽ được trả về dữ liệu, 
                # các mã còn lại sẽ chỉ được vẽ khung mà không trả về dữ liệu (để tránh spam).
                qr_data_result = qr_data
                qr_type_result = self.classify_data(qr_data)

        return ScanResult(frame=frame_rgb, data=qr_data_result, data_type=qr_type_result)

    def pause(self) -> None:
        """
        Tạm dừng và giải phóng phần cứng Camera.
        - Điểm cốt lõi: Luồng AI và mô hình QReader vẫn được giữ nguyên trong bộ nhớ RAM.
        - Ứng dụng: Dùng khi người dùng chuyển sang trang khác. Khi quay lại gọi resume() sẽ lên hình ngay lập tức mà không phải tốn 5-10s load lại AI.
        - Lưu ý: Đây chỉ là trạng thái ngủ đông, để tắt hẳn ứng dụng phải dùng shutdown().
        """

        # 1. Đóng camera hiện tại (nếu đang mở) và tạo một đối tượng VideoCapture mới rỗng để giải phóng tài nguyên
        if self.cap.isOpened():
            self.cap.release()
        del self.cap
        self.cap = cv2.VideoCapture() # Tạo một đối tượng VideoCapture mới nhưng không mở camera nào, giúp giải phóng tài nguyên và tránh giữ ref đến frame cũ trong RAM.

        # 2. Tạo lại hàng đợi mới để đảm bảo không giữ ref đến frame cũ (nếu có) trong RAM, giúp Python thu hồi bộ nhớ nhanh hơn.
        self._frame_queue = queue.Queue(maxsize=1)

        # 3. Xoá snapshot hiện tại để giải phóng bộ nhớ (nếu có) và tránh giữ ref đến dữ liệu cũ trong RAM, giúp Python thu hồi bộ nhớ nhanh hơn.
        with self._lock:
            self._snapshot = _DetectionSnapshot(texts=[], detections=[])

        # 4. Gọi gc.collect() để yêu cầu Python thu hồi bộ nhớ ngay lập tức, giúp giải phóng RAM đã dùng cho frame cũ và kết quả cũ (nếu có) nhanh hơn.
        gc.collect()

    def resume(self) -> bool:
        """
        Kích hoạt lại phần cứng Camera sau khi đã gọi pause().
        - Trả về True nếu kết nối thành công, False nếu mất thiết bị (vd: lỏng cáp webcam).
        - Chỉ gọi hàm này khi Camera đang ở trạng thái tắt tạm thời.
        """
        self.cap = cv2.VideoCapture(self._camera_index)
        if not self.cap.isOpened():
            print("⚠️  CẢNH BÁO: Không tìm thấy Camera!")
            return False
        return True

    def shutdown(self) -> None:
        """
        Đóng băng toàn bộ hệ thống: Ép dừng luồng AI, giải phóng Camera và dọn dẹp RAM.
        - Chỉ gọi hàm này khi người dùng bấm thoát (X) phần mềm.
        - Thao tác này không thể đảo ngược. Muốn quét lại phải khởi tạo một đối tượng QRDecoder hoàn toàn mới.
        """
        self._running = False
        self._ai_thread.join(timeout=2.0)
        if self.cap.isOpened():
            self.cap.release()

# ---------------------------------------------------------------------------
# LỚP XỬ LÝ PHỤ: Quét mã QR từ file ảnh (Không đụng tới Camera)
# ---------------------------------------------------------------------------

class FileQRDecoder:
    """
    Khối xử lý chuyên dụng để giải mã QR từ File ảnh tĩnh (độc lập với luồng Camera).
    
    - Tối ưu bộ nhớ: Sử dụng chung mô hình QReader dưới dạng biến tĩnh (class variable). 
      Mô hình chỉ được nạp vào RAM đúng 1 lần duy nhất ở lần gọi đầu tiên, các lần quét sau sẽ dùng lại ngay lập tức.
    - Tiện dụng: Được thiết kế dưới dạng @classmethod, có thể gọi trực tiếp FileQRDecoder.decode(file_path) 
      mà không cần khởi tạo đối tượng (instance).
    - An toàn: Hoạt động hoàn toàn độc lập, không gây nghẽn hay ảnh hưởng đến hiệu suất của luồng Camera.
    """
    
    # Biến tĩnh để lưu mô hình AI QReader dùng chung giữa các lần gọi decode() của FileQRDecoder.
    _qreader = None 

    @classmethod
    def decode(cls, file_path: str) -> list[str]:
        if cls._qreader is None:
            print("Đang tải mô hình AI QReader cho File ảnh...")
            cls._qreader = QReader()

        import numpy as np

        # Dùng numpy đọc byte thô để khắc phục triệt để lỗi OpenCV không đọc được thư mục chứa tiếng Việt
        img_cv2 = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_cv2 is None:
            raise ValueError("Không thể đọc file ảnh (đường dẫn lỗi hoặc định dạng sai)")

        img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
        results = cls._qreader.detect_and_decode(image=img_rgb)
        
        #Trả về danh sách các kết quả hợp lệ (loại bỏ None)
        return [qr_text for qr_text in results if qr_text is not None]