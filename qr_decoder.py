import time
import threading
import queue
import gc
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
from qreader import QReader


# ---------------------------------------------------------------------------
# Result type — named fields prevent caller from unpacking in the wrong order
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    frame: Optional[object]   # np.ndarray (RGB) or None if camera failed
    data: Optional[str]       # decoded QR content, or None
    data_type: Optional[str]  # e.g. "Website", "WiFi", "Văn bản", or None


# ---------------------------------------------------------------------------
# Internal snapshot shared between AI thread and main thread
# ---------------------------------------------------------------------------

@dataclass
class _DetectionSnapshot:
    texts: list
    detections: list


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class QRDecoder:
    """
    Threaded QR-code decoder.

    The main thread reads camera frames and draws overlays (fast).
    A background AI thread runs QReader inference (slow, 0.1–0.5 s).
    A maxsize-1 queue ensures the AI thread always works on the freshest frame.

    Usage (recommended — guarantees camera release even on exception):
        with QRDecoder() as decoder:
            while True:
                result = decoder.get_frame_and_data()
                if result.frame is None:
                    break
                ...

    Or manually:
        decoder = QRDecoder()
        try:
            ...
        finally:
            decoder.release_camera()
    """

    MAX_HISTORY_SIZE = 500   # cap on scanned_history to prevent unbounded growth
    COOLDOWN_TIME    = 3.0   # seconds before the same QR code is reported again
    DISPLAY_MAX_LEN  = 25    # max chars shown on-frame before truncation

    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index   # lưu lại để resume() dùng
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            print("CẢNH BÁO: Không tìm thấy Camera! Vui lòng kiểm tra lại thiết bị.")

        self.scanned_history: dict[str, float] = {}

        # Protects _snapshot — written by AI thread, read by main thread
        self._lock = threading.Lock()
        self._snapshot = _DetectionSnapshot(texts=[], detections=[])

        # maxsize=1: AI worker only ever processes the newest frame
        self._frame_queue: queue.Queue = queue.Queue(maxsize=1)
        self._running = True

        print("Đang khởi động AI QReader… (Lần đầu sẽ mất khoảng 5–10 giây để tải mô hình)")
        self.qreader = QReader()
        print("Tải AI thành công! Sẵn sàng quét mã.")

        self._ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self._ai_thread.start()

    # ------------------------------------------------------------------
    # Context-manager support — guarantees cleanup even on exception
    # ------------------------------------------------------------------

    def __enter__(self) -> "QRDecoder":
        return self

    def __exit__(self, *_) -> None:
        self.shutdown()

    # ------------------------------------------------------------------
    # Background AI worker (runs in its own thread)
    # ------------------------------------------------------------------

    def _ai_worker(self) -> None:
        """Dequeue frames and run QReader inference; store result atomically."""
        while self._running:
            try:
                frame_rgb = self._frame_queue.get(timeout=0.5)
                texts, detections = self.qreader.detect_and_decode(
                    image=frame_rgb, return_detections=True
                )
                # Single atomic assignment — no partial read possible
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
    # Data classification
    # ------------------------------------------------------------------

    @staticmethod
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
    # Cooldown / anti-spam helper
    # ------------------------------------------------------------------

    def _check_cooldown(self, qr_data: str) -> bool:
        """Return True if this code should be reported (outside cooldown window)."""
        now = time.time()
        if (now - self.scanned_history.get(qr_data, 0)) > self.COOLDOWN_TIME:
            # Prune history before inserting to cap memory usage
            if len(self.scanned_history) >= self.MAX_HISTORY_SIZE:
                oldest_key = next(iter(self.scanned_history))
                del self.scanned_history[oldest_key]
            self.scanned_history[qr_data] = now
            return True
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # @property
    # def is_camera_ok(self) -> bool:
    #     """True while the camera is open and readable."""
    #     return self.cap.isOpened()

    def get_frame_and_data(self) -> ScanResult:
        """
        Read one frame, draw QR overlays, and return the latest scan result.

        Returns a ScanResult with frame=None if the camera has failed.
        result.data is non-None only when a new code clears the cooldown.
        """
        success, frame = self.cap.read()
        if not success:
            return ScanResult(frame=None, data=None, data_type=None)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Feed freshest frame to AI worker (drop if worker is still busy)
        if self._frame_queue.empty():
            try:
                self._frame_queue.put_nowait(frame_rgb)
            except queue.Full:
                pass

        # Take an atomic snapshot so both lists are consistent
        with self._lock:
            snapshot = _DetectionSnapshot(
                texts=list(self._snapshot.texts),
                detections=list(self._snapshot.detections),
            )

        qr_data_result: Optional[str] = None
        qr_type_result: Optional[str] = None

        # zip() guards against length mismatch between texts and detections
        for qr_data, detection in zip(snapshot.texts, snapshot.detections):
            if qr_data is None:
                continue

            x1, y1, x2, y2 = map(int, detection["bbox_xyxy"])
            cv2.rectangle(frame_rgb, (x1, y1), (x2, y2), (0, 255, 0), 3)

            # label = qr_data if len(qr_data) < self.DISPLAY_MAX_LEN else qr_data[:self.DISPLAY_MAX_LEN] + "…"
            # cv2.putText(frame_rgb, label, (x1, y1 - 10),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            if self._check_cooldown(qr_data):
                # Only the first code that passes cooldown is surfaced per frame.
                # To surface all codes, change return type to List[ScanResult].
                qr_data_result = qr_data
                qr_type_result = self.classify_data(qr_data)

        return ScanResult(frame=frame_rgb, data=qr_data_result, data_type=qr_type_result)

    def pause(self) -> None:
        """
        CHỈ tắt webcam. AI model (QReader) VẪN sống trong RAM.
        Gọi khi người dùng nhấn 'Tắt Camera'.

        Tại sao xoá và tạo lại cap/queue thay vì chỉ release/flush?
        - cap.release() KHÔNG giải phóng hoàn toàn buffer nội bộ của OpenCV.
          del cap + VideoCapture() mới mới thực sự free RAM của OpenCV.
        - Flush queue bằng vòng lặp chỉ lấy item ra nhưng vẫn giữ tham chiếu
          đến numpy array trong stack. Tạo queue mới đảm bảo GC thu hồi ngay.
        """
        # 1. Giải phóng hoàn toàn buffer OpenCV
        if self.cap.isOpened():
            self.cap.release()
        del self.cap
        self.cap = cv2.VideoCapture()   # object rỗng, chưa mở camera nào

        # 2. Tạo queue mới để GC thu hồi numpy array còn sót trong queue cũ
        self._frame_queue = queue.Queue(maxsize=1)

        # 3. Xoá snapshot (chứa kết quả detection có thể giữ ref đến array)
        with self._lock:
            self._snapshot = _DetectionSnapshot(texts=[], detections=[])

        # 4. Ép Python thu hồi RAM ngay, không chờ GC tự chạy
        gc.collect()

    def resume(self) -> bool:
        """
        CHỈ bật webcam. Dùng lại AI model đã có sẵn trong RAM → tức thì.
        Gọi khi người dùng nhấn 'Bật Camera' (từ lần thứ 2 trở đi).
        Trả về True nếu mở camera thành công.
        """
        self.cap = cv2.VideoCapture(self._camera_index)
        if not self.cap.isOpened():
            print("⚠️  CẢNH BÁO: Không tìm thấy Camera!")
            return False
        return True

    def shutdown(self) -> None:
        """
        Huỷ hoàn toàn: dừng AI thread + đóng webcam.
        CHỈ gọi khi đóng app — KHÔNG gọi khi tắt camera thông thường.
        """
        self._running = False
        self._ai_thread.join(timeout=2.0)
        if self.cap.isOpened():
            self.cap.release()

    # def release_camera(self) -> None:
    #     """Giữ lại để không breaking change. Dùng shutdown() cho code mới."""
    #     self.shutdown()

class FileQRDecoder:
    """Khối xử lý chuyên dụng cho việc quét QR từ file ảnh (Không đụng tới Camera)."""
    
    # Dùng biến tĩnh (class variable) để chỉ tải AI QReader đúng 1 lần
    _qreader = None 

    @classmethod
    def decode(cls, file_path: str) -> list[str]:
        if cls._qreader is None:
            print("Đang tải mô hình AI QReader cho File ảnh...")
            cls._qreader = QReader()

        import numpy as np
        
        img_cv2 = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_cv2 is None:
            raise ValueError("Không thể đọc file ảnh (đường dẫn lỗi hoặc định dạng sai)")

        img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
        results = cls._qreader.detect_and_decode(image=img_rgb)
        
        return [qr_text for qr_text in results if qr_text is not None]