# Face Attendance Dashboard (Frontend) 🎓

Giao diện Web quản trị cho **Hệ thống điểm danh sinh viên bằng AI nhận diện khuôn mặt**. Đây là phân hệ Frontend nằm trong khuôn khổ dự án Nghiên cứu Khoa học (NCKH) cấp trường.

Hệ thống giúp giảng viên theo dõi tiến độ chuyên cần, xem bằng chứng điểm danh (snapshot) và các chỉ số tin cậy (confidence) do mô hình AI phân tích theo thời gian thực.

## 🚀 Công nghệ sử dụng (Tech Stack)

- **Core Framework:** ReactJS (khởi tạo qua Vite để tối ưu tốc độ build)
- **Ngôn ngữ:** JavaScript, HTML5, CSS3
- **Vẽ biểu đồ:** Recharts (trực quan hóa dữ liệu chuyên cần)
- **Xử lý API:** Axios (tích hợp JWT Token & Error Interceptors)
- **Định tuyến:** React Router DOM

## ⚙️ Yêu cầu hệ thống (Prerequisites)

- **Node.js**: Phiên bản 18.x trở lên
- **NPM** (được cài kèm Node.js) hoặc **Yarn**
- Backend Server (cổng `8080`) phải đang hoạt động để lấy dữ liệu.

## 🛠️ Cài đặt & Khởi chạy (Setup & Run)

**1. Clone dự án về máy**
```bash
git clone [https://github.com/CodyPhamQuynh/face-attendance-frontend.git](https://github.com/CodyPhamQuynh/face-attendance-frontend.git)
cd face-attendance-frontend
