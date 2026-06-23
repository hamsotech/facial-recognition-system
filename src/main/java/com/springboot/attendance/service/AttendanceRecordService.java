package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.AttendanceOverrideRequest;
import com.springboot.attendance.dto.request.AttendanceRecordRequest;
import com.springboot.attendance.dto.response.AttendanceRecordResponse;
import com.springboot.attendance.dto.response.PageResponse;
import com.springboot.attendance.entity.AttendanceRecord;
import com.springboot.attendance.entity.AttendanceStatus;
import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.repository.AttendanceRecordRepository;
import com.springboot.attendance.repository.ClassSessionRepository;
import com.springboot.attendance.repository.StudentRepository;
import com.springboot.attendance.repository.UserRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.data.domain.Pageable;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AttendanceRecordService {

    private final AttendanceRecordRepository attendanceRepository;
    private final ClassSessionRepository sessionRepository;
    private final StudentRepository studentRepository;
    private final UserRepository userRepository;
    private final AuditLogService auditLogService;

    @Transactional(readOnly = true)
    public PageResponse<AttendanceRecordResponse> getBySession(UUID sessionId, Pageable pageable) {
        var page = attendanceRepository.findPageBySessionId(sessionId, pageable);
        return PageResponse.<AttendanceRecordResponse>builder()
                .content(page.getContent().stream().map(this::toResponse).toList())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .last(page.isLast())
                .build();
    }
    
    @Transactional(readOnly = true)
    public PageResponse<AttendanceRecordResponse> getByStudent(UUID studentId, Pageable pageable) {
        var page = attendanceRepository.findPageByStudentId(studentId, pageable);
        return PageResponse.<AttendanceRecordResponse>builder()
                .content(page.getContent().stream().map(this::toResponse).toList())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .last(page.isLast())
                .build();
    }

    @Transactional(readOnly = true)
    public AttendanceRecordResponse getById(UUID id) {
        return toResponse(findOrThrow(id));
    }

    @Transactional
    public AttendanceRecordResponse markPresent(AttendanceRecordRequest req) {
        var session = sessionRepository.findById(req.getSessionId())
                .orElseThrow(() -> new EntityNotFoundException("Session not found"));

        if (session.getEndedAt() != null)
            throw new IllegalArgumentException("Session already ended");

        var student = studentRepository.findById(req.getStudentId())
                .orElseThrow(() -> new EntityNotFoundException("Student not found"));

        var existing = attendanceRepository
                .findBySessionIdAndStudentId(req.getSessionId(), req.getStudentId());

        if (existing.isPresent()) {
            var record = existing.get();
            record.setStatus(AttendanceStatus.PRESENT);
            record.setConfidence(req.getConfidence());
            return toResponse(attendanceRepository.save(record));
        }

        return toResponse(attendanceRepository.save(AttendanceRecord.builder()
                .session(session)
                .student(student)
                .status(AttendanceStatus.PRESENT)
                .confidence(req.getConfidence())
                .build()));
    }

    @Transactional
    public AttendanceRecordResponse override(UUID id, AttendanceOverrideRequest req, UUID overriddenById) {
        var record = findOrThrow(id);
        var overriddenBy = userRepository.findById(overriddenById)
                .orElseThrow(() -> new EntityNotFoundException("User not found"));

        String oldValue = String.format("{\"status\":\"%s\"}", record.getStatus().name());

        record.setStatus(AttendanceStatus.MANUAL_OVERRIDE);
        record.setOverriddenBy(overriddenBy);
        record.setOverrideReason(req.getReason());
        record.setConfidence(null);

        var saved = attendanceRepository.save(record);

        String newValue = String.format("{\"status\":\"MANUAL_OVERRIDE\",\"reason\":\"%s\"}", req.getReason());

        auditLogService.log(
            overriddenById,
            AuditAction.OVERRIDE_ATTENDANCE,
            "attendance_records",
            id,
            oldValue,
            newValue,
            null,
            null
        );

        return toResponse(saved);
    }

    private AttendanceRecord findOrThrow(UUID id) {
        return attendanceRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Attendance record not found: " + id));
    }

    private AttendanceRecordResponse toResponse(AttendanceRecord a) {
        return AttendanceRecordResponse.builder()
                .id(a.getId())
                .sessionId(a.getSession().getId())
                .studentId(a.getStudent().getId())
                .researchId(a.getStudent().getResearchId())
                .fullName(a.getStudent().getFullName())
                .studentCode(a.getStudent().getStudentCode())
                .status(a.getStatus().name())
                .confidence(a.getConfidence())
                .detectedAt(a.getDetectedAt())
                .overriddenById(a.getOverriddenBy() != null ? a.getOverriddenBy().getId() : null)
                .overriddenByName(a.getOverriddenBy() != null ? a.getOverriddenBy().getFullName() : null)
                .overrideReason(a.getOverrideReason())
                .build();
    }
}