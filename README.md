# Face Attendance Backend

Hệ thống điểm danh nhận diện khuôn mặt — Spring Boot (REST API) + FastAPI (AI/ML) + PostgreSQL.

## Tech Stack

- Spring Boot 3.5.14 / Java 21 / Maven
- PostgreSQL 17
- FastAPI / Python 3.10+

## Yêu cầu

- Java 21, Maven, PostgreSQL 17, Python 3.10+

## Setup & Run

**1. Tạo database và chạy schema**

```bash
psql -U postgres -c "CREATE DATABASE attendance_db;"
psql -U postgres -d attendance_db -f schema.sql
```

**2. Cấu hình `attendance/src/main/resources/application.yml`**

```yaml
spring.datasource.url: jdbc:postgresql://localhost:5432/attendance_db
spring.datasource.username: postgres
spring.datasource.password: yourpassword
jwt.secret: your-secret-key-minimum-32-characters
internal.api-key: your-internal-api-key
```

**3. Chạy Spring Boot**

```bash
cd attendance
./mvnw spring-boot:run
```

**4. Swagger UI:** `http://localhost:8080/swagger-ui.html`

## API Overview

| Group              | Base URL                 |
| ------------------ | ------------------------ |
| Auth               | `/api/auth`              |
| Users              | `/api/users`             |
| Classes            | `/api/classes`           |
| Students           | `/api/students`          |
| Enrollments        | `/api/enrollments`       |
| Sessions           | `/api/sessions`          |
| Attendance         | `/api/attendance`        |
| Export CSV         | `/api/attendance/export` |
| Embeddings         | `/api/embeddings`        |
| Benchmark          | `/api/benchmarks`        |
| Audit Logs         | `/api/audit-logs`        |
| Internal (FastAPI) | `/internal`              |

Chi tiết từng endpoint xem tại Swagger UI.

## Internal API cho FastAPI

Header: `X-Internal-Api-Key: {api-key}`

| Method | Endpoint                           | Mô tả                 |
| ------ | ---------------------------------- | --------------------- |
| GET    | `/internal/embeddings`             | Load tất cả embedding |
| GET    | `/internal/embeddings/{studentId}` | Embedding 1 sinh viên |
| POST   | `/internal/attendance/mark`        | Ghi kết quả nhận diện |
| POST   | `/internal/benchmark`              | Lưu kết quả benchmark |

**Flow:**
Tạo session → Load embeddings → Nhận diện realtime → Mark attendance → End session → Benchmark

## Roles

| Role       | Quyền                             |
| ---------- | --------------------------------- |
| ADMIN      | Toàn quyền                        |
| LECTURER   | Quản lý lớp, sinh viên, điểm danh |
| RESEARCHER | Xem và chạy benchmark             |

## CI/CD

GitHub Actions tự động build và test khi push lên `main` hoặc `develop`.
