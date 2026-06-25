import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import api from '../services/api'; // Kéo file cấu hình Axios xịn sò của Gấu vào đây

// Hàm phiên dịch ngôn ngữ từ Backend sang Tiếng Việt cho UI
const formatStatus = (backendStatus) => {
  switch (backendStatus) {
    case 'PRESENT': return 'Đúng giờ';
    case 'ABSENT': return 'Vắng';
    case 'MANUAL_OVERRIDE': return 'Ghi đè thủ công';
    default: return 'Không xác định';
  }
};

const Dashboard = () => {
  // Khởi tạo danh sách trống, chờ dữ liệu đổ về từ API
  const [attendanceList, setAttendanceList] = useState([]);

  // State và Mock Data cho Bộ lọc (Filters)
  const [filters, setFilters] = useState({
    semester: 'HK1 2024-2025',
    subject: 'Nhập môn Lập trình',
    classCode: 'CS101-01',
    session: 'Buổi 1'
  });

  const mockSemesters = ['HK1 2024-2025', 'HK2 2024-2025'];
  const mockSubjects = ['Nhập môn Lập trình', 'Cơ sở Dữ liệu'];
  const mockClasses = ['CS101-01', 'CS202-01'];
  const mockSessions = ['Buổi 1', 'Buổi 2'];

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters({ ...filters, [name]: value });
  };

  // State quản lý Modal hiển thị ảnh Bằng chứng
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);

  const handleViewDetails = (student) => {
    setSelectedStudent(student);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedStudent(null);
  };

  // TỰ ĐỘNG GỌI API KHI MỞ TRANG (Bước tiến quan trọng cho NCKH)
  useEffect(() => {
    const fetchAttendanceData = async () => {
      try {
        // ID test lấy từ file Postman của Thế Anh
        const sessionId = "94a19f49-287a-4030-984e-d68df0d04449"; 
        
        // Gọi API lấy dữ liệu thật
        const response = await api.get(`/api/attendance/session/${sessionId}?page=0&size=50`);
        
        // Trích xuất mảng dữ liệu (thường Spring Boot bọc trong thuộc tính content khi phân trang)
        const dataArray = response.content || response;

        // Chuyển hóa dữ liệu để render lên UI
        const formattedData = dataArray.map(item => ({
          id: item.id,
          mssv: item.studentCode,
          name: item.fullName,
          timeIn: item.timeIn || "-",
          status: formatStatus(item.status),
          originalStatus: item.status,
          reason: item.overrideReason,
          snapshotUrl: item.snapshotUrl,
          confidence: item.confidence
        }));

        // Đổ dữ liệu thật vào State
        setAttendanceList(formattedData);
      } catch (error) {
        console.error("Lỗi khi tải dữ liệu điểm danh:", error);
      }
    };

    fetchAttendanceData();
  }, []);

  // Dữ liệu giả định cho Biểu đồ (Sẽ nối API sau)
  const chartData = [
    { name: 'Đúng giờ', value: 2, color: '#4caf50' }, 
    { name: 'Ghi đè thủ công', value: 1, color: '#ff9800' },      
    { name: 'Vắng', value: 1, color: '#9e9e9e' }
  ];

  const weeklyData = [
    { name: 'Tuần 1', 'Đúng giờ': 35, 'Ghi đè thủ công': 5, 'Vắng': 2 },
    { name: 'Tuần 2', 'Đúng giờ': 38, 'Ghi đè thủ công': 3, 'Vắng': 1 }
  ];

  return (
    <div className="dashboard-container" style={{ padding: '20px' }}>
      <h2>Bảng Điều Khiển Hệ Thống Điểm Danh</h2>
      
      <div className="charts-section" style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
        <div style={{ flex: 1, padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
          <h3 style={{ textAlign: 'center' }}>Tỷ lệ chuyên cần tổng quan</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
        
        <div style={{ flex: 1, padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
          <h3 style={{ textAlign: 'center' }}>Chuyên cần theo tuần</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={weeklyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="Đúng giờ" fill="#4caf50" />
              <Bar dataKey="Ghi đè thủ công" fill="#ff9800" />
              <Bar dataKey="Vắng" fill="#9e9e9e" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="attendance-section" style={{ marginTop: '30px' }}>
        <h3>Danh sách điểm danh trực tuyến</h3>
        
        <div className="filters-section" style={{ display: 'flex', gap: '15px', marginBottom: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
          <select name="semester" value={filters.semester} onChange={handleFilterChange} style={{ padding: '8px', borderRadius: '4px' }}>
            {mockSemesters.map(sem => <option key={sem} value={sem}>{sem}</option>)}
          </select>
          <select name="subject" value={filters.subject} onChange={handleFilterChange} style={{ padding: '8px', borderRadius: '4px' }}>
            {mockSubjects.map(sub => <option key={sub} value={sub}>{sub}</option>)}
          </select>
          <select name="classCode" value={filters.classCode} onChange={handleFilterChange} style={{ padding: '8px', borderRadius: '4px' }}>
            {mockClasses.map(cls => <option key={cls} value={cls}>{cls}</option>)}
          </select>
          <select name="session" value={filters.session} onChange={handleFilterChange} style={{ padding: '8px', borderRadius: '4px' }}>
            {mockSessions.map(ses => <option key={ses} value={ses}>{ses}</option>)}
          </select>
        </div>
        
        <table border="1" style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f2f2f2' }}>
              <th style={{ padding: '10px' }}>STT</th>
              <th style={{ padding: '10px' }}>MSSV</th>
              <th style={{ padding: '10px' }}>Họ và Tên</th>
              <th style={{ padding: '10px' }}>Thời gian vào</th>
              <th style={{ padding: '10px' }}>Trạng thái</th>
              <th style={{ padding: '10px', textAlign: 'center' }}>Hành động</th>
            </tr>
          </thead>
          <tbody>
            {attendanceList.map((student, index) => (
              <tr key={student.id}>
                <td style={{ padding: '10px' }}>{index + 1}</td>
                <td style={{ padding: '10px' }}>{student.mssv}</td>
                <td style={{ padding: '10px' }}>{student.name}</td>
                <td style={{ padding: '10px' }}>{student.timeIn}</td>
                <td style={{ 
                  padding: '10px',
                  fontWeight: 'bold',
                  color: student.status === 'Đúng giờ' ? 'green' : 
                         student.status === 'Ghi đè thủ công' ? 'orange' : 'gray'
                }}>
                  {student.status}
                </td>
                <td style={{ padding: '10px', textAlign: 'center' }}>
                  <button 
                    onClick={() => handleViewDetails(student)}
                    style={{ padding: '5px 10px', cursor: 'pointer', backgroundColor: '#e0e0e0', border: '1px solid #ccc', borderRadius: '4px' }}
                  >
                    Xem chi tiết
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isModalOpen && selectedStudent && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white', padding: '20px', borderRadius: '8px', width: '400px',
            boxShadow: '0 4px 8px rgba(0,0,0,0.2)'
          }}>
            <h3 style={{ marginTop: 0 }}>Bằng chứng điểm danh</h3>
            <p><strong>MSSV:</strong> {selectedStudent.mssv}</p>
            <p><strong>Họ tên:</strong> {selectedStudent.name}</p>
            <p><strong>Trạng thái:</strong> <span style={{ 
              fontWeight: 'bold',
              color: selectedStudent.status === 'Đúng giờ' ? 'green' : 
                     selectedStudent.status === 'Ghi đè thủ công' ? 'orange' : 'gray' 
            }}>{selectedStudent.status}</span></p>
            
            {/* Hiển thị lý do nếu điểm danh bị can thiệp */}
            {selectedStudent.reason && (
              <p style={{ color: '#d32f2f', fontSize: '14px', fontStyle: 'italic' }}>
                *Lý do: {selectedStudent.reason}
              </p>
            )}
            
            {/* HIỂN THỊ ĐỘ TIN CẬY (CONFIDENCE) DÀNH CHO NCKH */}
            {selectedStudent.confidence && (
              <p style={{ fontSize: '14px', color: '#1976d2' }}>
                <strong>Độ chính xác (AI):</strong> {(selectedStudent.confidence * 100).toFixed(2)}%
              </p>
            )}
            
            <div style={{ textAlign: 'center', margin: '15px 0' }}>
              {selectedStudent.snapshotUrl ? (
                 <img 
                 src={selectedStudent.snapshotUrl} 
                 alt="Snapshot" 
                 style={{ maxWidth: '100%', borderRadius: '4px', border: '1px solid #ccc' }} 
               />
              ) : (
                <div style={{ padding: '40px', backgroundColor: '#f0f0f0', color: '#777', borderRadius: '4px' }}>
                  Không có ảnh bằng chứng
                </div>
              )}
              
              <p style={{ fontSize: '12px', color: 'gray', marginTop: '8px' }}>
                Thời gian: {selectedStudent.timeIn !== '-' ? selectedStudent.timeIn : 'N/A'}
              </p>
            </div>

            <div style={{ textAlign: 'right' }}>
              <button onClick={closeModal} style={{ padding: '8px 16px', cursor: 'pointer', backgroundColor: '#f44336', color: 'white', border: 'none', borderRadius: '4px' }}>
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;