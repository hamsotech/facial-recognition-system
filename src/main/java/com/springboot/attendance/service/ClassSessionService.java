package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.ClassSessionRequest;
import com.springboot.attendance.dto.response.ClassSessionResponse;
import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.entity.ClassSession;
import com.springboot.attendance.repository.ClassRepository;
import com.springboot.attendance.repository.ClassSessionRepository;
import com.springboot.attendance.repository.UserRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ClassSessionService {

    private final ClassSessionRepository sessionRepository;
    private final ClassRepository classRepository;
    private final UserRepository userRepository;
    private final AuditLogService auditLogService;

    @Transactional(readOnly = true)
    public List<ClassSessionResponse> getByClass(UUID classId) {
        return sessionRepository.findByClassEntity_Id(classId)
                .stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public ClassSessionResponse getById(UUID id) {
        return toResponse(findOrThrow(id));
    }

    @Transactional
    public ClassSessionResponse create(ClassSessionRequest req, UUID createdById) {
        var classEntity = classRepository.findById(req.getClassId())
                .orElseThrow(() -> new EntityNotFoundException("Class not found"));

        var createdBy = userRepository.findById(createdById)
                .orElseThrow(() -> new EntityNotFoundException("User not found"));

        var saved = sessionRepository.save(ClassSession.builder()
                    .classEntity(classEntity)
                    .createdBy(createdBy)
                    .notes(req.getNotes())
                    .build());

        auditLogService.log(
            createdById,
            AuditAction.CREATE_SESSION,
            "class_sessions",
            saved.getId(),
            null,
            String.format("{\"classId\":\"%s\"}", req.getClassId()),
            null,
            null
        );

        return toResponse(saved);

    }

    @Transactional
    public ClassSessionResponse end(UUID id) {
        var session = findOrThrow(id);

        if (session.getEndedAt() != null)
            throw new IllegalArgumentException("Session already ended");

        session.setEndedAt(OffsetDateTime.now());

        var saved = sessionRepository.save(session);

        auditLogService.log(
            null,
            AuditAction.END_SESSION,
            "class_sessions",
            id,
            null,
            String.format("{\"endedAt\":\"%s\"}", saved.getEndedAt()),
            null,
            null
        );

        return toResponse(saved);
    }

    @Transactional(readOnly = true)
    public boolean isActive(UUID id) {
        return findOrThrow(id).getEndedAt() == null;
    }

    private ClassSession findOrThrow(UUID id) {
        return sessionRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Session not found: " + id));
    }

    private ClassSessionResponse toResponse(ClassSession s) {
        return ClassSessionResponse.builder()
                .id(s.getId())
                .classId(s.getClassEntity().getId())
                .classCode(s.getClassEntity().getClassCode())
                .subjectName(s.getClassEntity().getSubjectName())
                .createdById(s.getCreatedBy().getId())
                .createdByName(s.getCreatedBy().getFullName())
                .startedAt(s.getStartedAt())
                .endedAt(s.getEndedAt())
                .notes(s.getNotes())
                .isActive(s.getEndedAt() == null)
                .build();
    }
}