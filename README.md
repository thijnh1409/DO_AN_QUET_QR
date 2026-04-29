# ĐỒ ÁN: ỨNG DỤNG QUÉT VÀ QUẢN LÝ MÃ QR (Desktop App)

## 1. Thành viên (Họ tên - MSSV)
* **Nguyễn Lê Phúc Thịnh** - 25139047
* **Nguyễn Truy Phong** - 25139031
* **Lê Nguyễn Văn Hòa** - 25139013
* **Nguyễn Thanh Trí** - 23119217
* **Nguyễn Gia Thiên Phúc** - 25139034

---

## 2. Định hướng & Lộ trình phát triển
Dự án là một **Desktop App** chạy trên hệ điều hành máy tính (sử dụng Webcam để quét). Tiến độ code được chia làm 2 giai đoạn:

* 📍 **GIAI ĐOẠN 1 (Bắt buộc hoàn thành):**
  * **Giao diện (UI/UX):** Xây dựng màn hình chính, nút điều hướng, cửa sổ cảnh báo, v.v.
  * **Quét mã QR:** Tích hợp camera, xử lý quét thẳng và nghiêng nhẹ. *(Lưu ý: Quét góc nghiêng sâu là thử thách khó do giới hạn của Webcam, sẽ dùng làm phần nghiên cứu nâng cao).*
  * **Quản lý dữ liệu:** Ghi nhận và xuất lịch sử quét ra file văn bản.
<!-- * 🌟 **GIAI ĐOẠN 2 (Tính năng mở rộng):**
  * **Tạo mã QR:** Bổ sung tính năng cá nhân hóa mã QR (đổi màu, chèn ảnh, tùy chỉnh kích thước) khi thời gian cho phép. -->

---

## 3. Cấu trúc thư mục (Quy định chung)
Hệ thống được chia thành các module độc lập để dễ quản lý:
- `main.py` : File khởi chạy chính (gắn kết giao diện và các module).
- `ui_manager.py` : Quản lý và xử lý giao diện người dùng.
- `qr_scanner.py` : Chứa thuật toán camera, nhận diện và giải mã QR.
- `data_manager.py` : Xử lý logic lưu trữ và đọc/ghi dữ liệu.
- `scan_logs.txt` : File lưu trữ lịch sử các phiên quét QR.

---

## 4. Hướng dẫn & Lưu ý quan trọng
* **Chuẩn Code [PEP-8](https://codelearn.io/sharing/pep8-chuan-ket-noi-python-phan-1):** Khuyến khích anh em code tuân thủ chuẩn **PEP-8** của Python (dùng `snake_case` cho tên biến/hàm, comment rõ chức năng, cách dòng chuẩn chỉ). Điều này giúp code sạch, dễ đọc và dễ gộp (merge) mà không bị conflict.
* **Trích dẫn mã nguồn (Quan trọng):** Nếu anh em tham khảo hoặc tái sử dụng thuật toán phức tạp từ GitHub hay các nguồn bên ngoài (như xử lý góc nghiêng, chèn ảnh...), phải comment link nguồn gốc ngay trên đoạn code đó (VD: `# Nguồn tham khảo logic: [Link]`).
* **Thư viện yêu cầu:** Cài đặt toàn bộ thư viện bằng cách mở Terminal tại thư mục code và gõ lệnh: `pip install -r requirements.txt`.
  * 🚨 **LỖI THƯỜNG GẶP (ĐỌC KỸ TRƯỚC KHI CODE):**     * Nếu cài xong thư viện `pyzbar` mà lúc chạy app bị văng lỗi đỏ: `FileNotFoundError: Could not find module 'libzbar-64.dll'`
    * **Nguyên nhân:** Không phải do code sai, mà do máy tính Windows bị thiếu lõi C++.
    * **Cách sửa:** Lên Google gõ tải và cài đặt phần mềm **Visual C++ Redistributable** của Microsoft vào máy là app sẽ chạy bình thường.
* **Tài nguyên dự án:** Link Google Drive: [[PRPY238164] - Tiểu luận Python - QR Code](https://drive.google.com/drive/folders/18oSkehrKZfj7nN2bt-9R4SEqQLHEXabb?usp=drive_link)