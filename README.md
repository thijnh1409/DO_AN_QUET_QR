# ĐỒ ÁN: ỨNG DỤNG QUÉT VÀ QUẢN LÝ MÃ QR (Desktop App)

## Thành viên (Họ tên - MSSV)
* **Nguyễn Lê Phúc Thịnh** - 25139047
* **Nguyễn Truy Phong** - 25139031
* **Lê Nguyễn Văn Hòa** - 25139013
* **Nguyễn Thanh Trí** - 23119217
* **Nguyễn Gia Thiên Phúc** - 25139034

---

## Tính năng nổi bật
**Quét trực tiếp từ Camera:** Ứng dụng kiến trúc đa luồng giúp tách biệt luồng xử lý AI và luồng giao diện, đảm bảo camera hiển thị mượt mà không bị giật lag.
- **Quét từ File ảnh:** Hỗ trợ đọc mã QR từ các tệp hình ảnh có sẵn trên máy tính, sử dụng `numpy` để đọc byte thô giúp khắc phục hoàn toàn lỗi không nhận diện được đường dẫn chứa tiếng Việt.
- **Giao diện đơn giản:** Xây dựng bằng thư viện `customtkinter`, hỗ trợ giao diện trực quan, các nút bấm bo góc mềm mại và tự động tương thích với chế độ hiển thị của hệ thống.
- **Quản lý lịch sử:** Tự động lưu trữ các mã đã quét vào tệp `scan_logs.txt` với cơ chế chuyển đổi ký tự thông minh để chống vỡ cấu trúc file. Hỗ trợ trích xuất toàn bộ lịch sử ra file Excel (`.csv`) định dạng `utf-8-sig`.

## 📂 Cấu trúc thư mục

Dự án được chia thành các module độc lập để dễ quản lý, bảo trì và mở rộng trong tương lai:
```text
QR_Scanner_Project/
├── assets/             # Thư mục chứa tài nguyên tĩnh (logo trường, icon)
├── main.py             # Điểm bắt đầu để khởi chạy ứng dụng
├── ui_manager.py       # Chịu trách nhiệm thiết kế lớp vỏ giao diện và điều hướng
├── qr_decoder.py       # Chứa thuật toán lõi xử lý camera và giải mã AI
├── data_manager.py     # Xử lý hậu cần, ghi/đọc tệp lịch sử và xuất CSV
├── requirements.txt    # Danh sách các thư viện cần thiết
└── scan_logs.txt       # Tệp cơ sở dữ liệu cục bộ lưu lịch sử quét

## 4. Hướng dẫn & Lưu ý quan trọng
* **Chuẩn Code [PEP-8](https://codelearn.io/sharing/pep8-chuan-ket-noi-python-phan-1):** Khuyến khích anh em code tuân thủ chuẩn **PEP-8** của Python (dùng `snake_case` cho tên biến/hàm, comment rõ chức năng, cách dòng chuẩn chỉ). Điều này giúp code sạch, dễ đọc và dễ gộp (merge) mà không bị conflict.
* **Trích dẫn mã nguồn (Quan trọng):** Nếu anh em tham khảo hoặc tái sử dụng thuật toán phức tạp từ GitHub hay các nguồn bên ngoài (như xử lý góc nghiêng, chèn ảnh...), phải comment link nguồn gốc ngay trên đoạn code đó (VD: `# Nguồn tham khảo logic: [Link]`).
* **Thư viện yêu cầu:** Cài đặt toàn bộ thư viện bằng cách mở Terminal tại thư mục code và gõ lệnh: `pip install -r requirements.txt`.
* **Tài nguyên dự án:** Link Google Drive: [[PRPY238164] - Tiểu luận Python - QR Code](https://drive.google.com/drive/folders/18oSkehrKZfj7nN2bt-9R4SEqQLHEXabb?usp=drive_link)

## 🎓 Lời cảm ơn
Nhóm chúng em xin gửi lời cảm ơn sâu sắc đến Thầy TS. Dương Minh Thiện đã tận tình giảng dạy, hỗ trợ và định hướng để nhóm có thể hoàn thiện sản phẩm một cách chỉn chu nhất.