import axios from 'axios';

// Tạo một bản thể axios với cấu hình mặc định
const api = axios.create({
  // Địa chỉ gốc của Backend Spring Boot (của SV3)
  baseURL: 'http://localhost:8080', 
  // Thiết lập thời gian chờ tối đa (10 giây) để tránh treo hệ thống khi mạng chậm
  timeout: 10000, 
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// 1. REQUEST INTERCEPTOR: Xử lý dữ liệu trước khi gửi lên máy chủ
// ============================================================================
api.interceptors.request.use(
  (config) => {
    // Trích xuất mã xác thực (Token) từ bộ nhớ trình duyệt
    const token = localStorage.getItem('accessToken');
    
    // Nếu tồn tại mã xác thực, đính kèm vào tiêu đề (Header) của yêu cầu
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // Xử lý các lỗi phát sinh trong quá trình thiết lập yêu cầu
    return Promise.reject(error);
  }
);

// ============================================================================
// 2. RESPONSE INTERCEPTOR: Xử lý dữ liệu trả về từ máy chủ
// ============================================================================
api.interceptors.response.use(
  (response) => {
    // Trích xuất trực tiếp dữ liệu (data), lược bỏ các thông số cấu hình dư thừa từ Axios
    return response.data;
  },
  (error) => {
    // Phân tích và xử lý các mã lỗi HTTP (HTTP Status Codes)
    if (error.response) {
      const status = error.response.status;
      
      switch (status) {
        case 401:
          // Lỗi xác thực: Token không hợp lệ, bị thiếu hoặc đã hết hạn
          console.error('Lỗi 401: Phiên đăng nhập đã hết hạn hoặc không hợp lệ.');
          alert('Thông báo: Phiên làm việc của bạn đã kết thúc. Vui lòng đăng nhập lại để tiếp tục sử dụng hệ thống.');
          // Xóa dữ liệu xác thực cũ và điều hướng người dùng về trang đăng nhập
          localStorage.removeItem('accessToken');
          window.location.href = '/login'; 
          break;
          
        case 403:
          // Lỗi phân quyền: Tài khoản không có chức năng truy cập tài nguyên này
          console.error('Lỗi 403: Hệ thống từ chối quyền truy cập do giới hạn phân quyền.');
          alert('Cảnh báo: Tài khoản của bạn không được cấp quyền truy cập vào chức năng này.');
          break;
          
        case 404:
          // Lỗi tài nguyên: Đường dẫn API không tồn tại
          console.error('Lỗi 404: Không tìm thấy tài nguyên yêu cầu trên máy chủ.');
          break;
          
        case 500:
          // Lỗi máy chủ: Sự cố xuất phát từ phía Backend của SV3
          console.error('Lỗi 500: Đã xảy ra lỗi nội bộ từ phía máy chủ hệ thống.');
          alert('Thông báo: Hệ thống máy chủ đang gặp sự cố tạm thời. Vui lòng liên hệ Quản trị viên hoặc thử lại sau.');
          break;
          
        default:
          console.error(`Lỗi ${status}: Đã xảy ra lỗi không xác định.`);
          alert('Thông báo: Đã xảy ra lỗi trong quá trình xử lý yêu cầu. Vui lòng thử lại.');
      }
    } else if (error.request) {
      // Lỗi mạng: Máy chủ không phản hồi hoặc mất kết nối Internet
      console.error('Lỗi mạng: Không thể thiết lập kết nối đến máy chủ.');
      alert('Thông báo: Mất kết nối đến hệ thống. Vui lòng kiểm tra lại đường truyền mạng của bạn và đảm bảo máy chủ đang hoạt động.');
    } else {
      // Lỗi trong quá trình thiết lập cấu hình Axios
      console.error('Lỗi cấu hình hệ thống: ', error.message);
    }

    // Trả về lỗi để các component có thể chủ động catch và xử lý riêng nếu cần
    return Promise.reject(error);
  }
);

export default api;