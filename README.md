# Dự án Phân tích và Dự báo Thời tiết

Dự án này tập trung vào việc xử lý dữ liệu thô, thống kê mô tả, trực quan hóa và xây dựng mô hình dự báo nhiệt độ.

## 📁 Cấu trúc thư mục và Trách nhiệm từng file

Các file mã nguồn chính nằm trong thư mục `src/`:

* **`cleaning_data.ipynb`**: Chịu trách nhiệm tiền xử lý dữ liệu. Bao gồm các bước làm sạch, xử lý giá trị thiếu (null), định dạng lại kiểu dữ liệu và loại bỏ các giá trị ngoại lai (outliers).
* **`summary_statistics.ipynb`**: Thực hiện tính toán các chỉ số thống kê mô tả (trung bình, trung vị, độ lệch chuẩn...) để hiểu rõ hơn về phân phối của tập dữ liệu.
* **`visualize.ipynb`**: Trực quan hóa dữ liệu bằng biểu đồ. Giúp tìm ra xu hướng, sự tương quan giữa các biến thời tiết thông qua hình ảnh.
* **`temp_predict.ipynb`**: Xây dựng, huấn luyện và đánh giá các mô hình học máy để dự báo nhiệt độ trong tương lai.

---

## 🛠 Hướng dẫn cài đặt và sử dụng

Để chạy được dự án này, cần cài đặt các thư viện cần thiết thông qua file `requirements.txt`.
**Trên Windows:**
```bash
.venv\Scripts\activate

