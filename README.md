# Phân tích Dữ liệu Thời tiết & Chất lượng Không khí Hà Nội 2024

Dự án này tập trung vào việc thu thập, xử lý và phân tích các đặc điểm khí tượng và chất lượng không khí tại Hà Nội trong năm 2024. Mục tiêu là tìm ra các xu hướng biến động theo mùa và mối tương quan giữa các yếu tố thời tiết với mức độ ô nhiễm không khí.

## 📂 Nguồn dữ liệu

Dữ liệu được sử dụng trong dự án bao gồm:

1.  **Dữ liệu Thời tiết:**
    * Nguồn: [Meteostat (Trạm 48820)](https://meteostat.net/en/station/48820)
    * Phạm vi: Hà Nội, năm 2024.
2.  **Chất lượng Không khí:**
    * Nguồn: [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
    * Các chỉ số: PM10, PM2.5, Ozone, SO2, NO2, CO, UV Index, v.v.

## 📋 Yêu cầu hệ thống

* **Python:** Phiên bản 3.8 trở lên.
* Các thư viện phụ thuộc chính:
    * `pandas`
    * `numpy`
    * `matplotlib` / `seaborn`
    * `requests` (để gọi API nếu cần)

## ⚙️ Cài đặt

Để thiết lập môi trường chạy, vui lòng thực hiện lệnh sau:

```bash
pip install -r requirements.txt