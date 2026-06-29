import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    console.log("1. Hàm xử lý đăng nhập đã được kích hoạt.");
    console.log("2. Đang giả lập gửi request tới Backend...");

    /* --- PHẦN GHI CHÚ: Tạm ẩn việc gọi API thật cho đến khi Server hoạt động ---
    try {
      const response = await api.post("/api/auth/login", {
        username: username,
        password: password,
      });

      console.log("Response data:", response.data);
      alert("Đăng nhập thành công.");

      navigate("/dashboard");
    } catch (error) {
      console.error("Login error:", error);
      alert(
        "Đăng nhập thất bại. Vui lòng kiểm tra lại tên đăng nhập hoặc mật khẩu.",
      );
    }
    -------------------------------------------------------------------------
    */

    // --- PHẦN THÊM VÀO: Mô phỏng Backend trả về kết quả ---
    setTimeout(() => {
      if (username === "admin" && password === "123456") {
        console.log("Mock Response: Đăng nhập thành công");
        alert("Đăng nhập thành công.");
        navigate("/dashboard"); 
      } else {
        console.error("Mock Error: Sai thông tin");
        alert("Đăng nhập thất bại. Vui lòng kiểm tra lại tên đăng nhập hoặc mật khẩu.");
      }
    }, 1000); 
    // ------------------------------------------------------
  };

  return (
    <div className="login-container">
      <h2>Đăng Nhập Quản Trị Hệ Thống</h2>
      <form onSubmit={handleLogin}>
        <div>
          <label>Tên đăng nhập: </label>
          <input
            type="text"
            placeholder="Nhập tên đăng nhập..."
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <br />
        <div>
          <label>Mật khẩu: </label>
          <input
            type="password"
            placeholder="Nhập mật khẩu..."
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <br />
        <button type="submit">Đăng Nhập</button>
      </form>
    </div>
  );
};

export default Login;