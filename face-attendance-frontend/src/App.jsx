import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Import các trang thật từ thư mục pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

// Giữ lại 2 trang này làm tạm để tránh lỗi báo đỏ
const AttendanceRecord = () => <div><h2>Lịch Sử Điểm Danh</h2></div>;
const NotFound = () => <div><h2>404 - Không tìm thấy trang</h2></div>;

function App() {
  return (
    <Router>
      <div className="app-container">
        <header>
          <h1>Hệ Thống Điểm Danh Nhận Diện Khuôn Mặt</h1>
        </header>
        
        <main>
          <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/attendance" element={<AttendanceRecord />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>

        <footer>
          <p>&copy; {new Date().getFullYear()} - Dự án Nghiên cứu Khoa học</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;