package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.AttendanceOverrideRequest;
import com.springboot.attendance.dto.request.AttendanceRecordRequest;
import com.springboot.attendance.dto.response.AttendanceRecordResponse;
import com.springboot.attendance.entity.*;
import com.springboot.attendance.repository.AttendanceRecordRepository;
import com.springboot.attendance.repository.ClassSessionRepository;
import com.springboot.attendance.repository.StudentRepository;
import com.springboot.attendance.repository.UserRepository;
import jakarta.persistence.EntityNotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AttendanceRecordServiceTest {

    @Mock private AttendanceRecordRepository attendanceRepository;
    @Mock private ClassSessionRepository sessionRepository;
    @Mock private StudentRepository studentRepository;
    @Mock private UserRepository userRepository;
    @Mock private AuditLogService auditLogService;

    @InjectMocks
    private AttendanceRecordService attendanceService;

    private ClassSession mockSession;
    private Student mockStudent;
    private User mockUser;
    private UUID sessionId;
    private UUID studentId;
    private UUID userId;

    @BeforeEach
    void setUp() {
        sessionId = UUID.randomUUID();
        studentId = UUID.randomUUID();
        userId = UUID.randomUUID();

        mockSession = ClassSession.builder()
                .id(sessionId)
                .build();

        mockStudent = Student.builder()
                .id(studentId)
                .researchId("SV001")
                .fullName("Nguyen Van A")
                .studentCode("20110001")
                .build();

        mockUser = User.builder()
                .id(userId)
                .username("lecturer")
                .fullName("Giang Vien A")
                .role(UserRole.LECTURER)
                .build();
    }

    @Test
    void markPresent_newRecord_success() {
        var req = new AttendanceRecordRequest();
        req.setSessionId(sessionId);
        req.setStudentId(studentId);
        req.setConfidence(0.98);

        when(sessionRepository.findById(sessionId)).thenReturn(Optional.of(mockSession));
        when(studentRepository.findById(studentId)).thenReturn(Optional.of(mockStudent));
        when(attendanceRepository.findBySessionIdAndStudentId(sessionId, studentId))
                .thenReturn(Optional.empty());

        var savedRecord = AttendanceRecord.builder()
                .id(UUID.randomUUID())
                .session(mockSession)
                .student(mockStudent)
                .status(AttendanceStatus.PRESENT)
                .confidence(0.98)
                .build();

        when(attendanceRepository.save(any())).thenReturn(savedRecord);

        AttendanceRecordResponse res = attendanceService.markPresent(req);

        assertThat(res.getStatus()).isEqualTo("PRESENT");
        assertThat(res.getConfidence()).isEqualTo(0.98);
        verify(attendanceRepository, times(1)).save(any());
    }

    @Test
    void markPresent_sessionEnded_throwsException() {
        mockSession.setEndedAt(java.time.OffsetDateTime.now());
        var req = new AttendanceRecordRequest();
        req.setSessionId(sessionId);
        req.setStudentId(studentId);

        when(sessionRepository.findById(sessionId)).thenReturn(Optional.of(mockSession));

        assertThatThrownBy(() -> attendanceService.markPresent(req))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("Session already ended");
    }

    @Test
    void override_success() {
        var recordId = UUID.randomUUID();
        var existingRecord = AttendanceRecord.builder()
                .id(recordId)
                .session(mockSession)
                .student(mockStudent)
                .status(AttendanceStatus.ABSENT)
                .build();

        var req = new AttendanceOverrideRequest();
        req.setPresent(true);
        req.setReason("Camera không nhận diện được");

        when(attendanceRepository.findById(recordId)).thenReturn(Optional.of(existingRecord));
        when(userRepository.findById(userId)).thenReturn(Optional.of(mockUser));
        when(attendanceRepository.save(any())).thenReturn(existingRecord);

        AttendanceRecordResponse res = attendanceService.override(recordId, req, userId);

        assertThat(res.getStatus()).isEqualTo("MANUAL_OVERRIDE");
        assertThat(res.getOverrideReason()).isEqualTo("Camera không nhận diện được");
    }

    @Test
    void override_recordNotFound_throwsException() {
        var recordId = UUID.randomUUID();
        var req = new AttendanceOverrideRequest();
        req.setPresent(true);
        req.setReason("Test");

        when(attendanceRepository.findById(recordId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> attendanceService.override(recordId, req, userId))
                .isInstanceOf(EntityNotFoundException.class);
    }
}