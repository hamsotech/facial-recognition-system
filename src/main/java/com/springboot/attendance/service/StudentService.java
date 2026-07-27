package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.StudentRequest;
import com.springboot.attendance.dto.response.PageResponse;
import com.springboot.attendance.dto.response.StudentResponse;
import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.entity.Student;
import com.springboot.attendance.repository.StudentRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;

import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class StudentService {

    private final StudentRepository studentRepository;
    private final AuditLogService auditLogService;

    @Transactional(readOnly = true)
    public PageResponse<StudentResponse> getAll(Pageable pageable) {
        var page = studentRepository.findAll(pageable);
        return PageResponse.<StudentResponse>builder()
                .content(page.getContent().stream().map(this::toResponse).toList())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .last(page.isLast())
                .build();
    }

    @Transactional(readOnly = true)
    public StudentResponse getById(UUID id) {
        return toResponse(findOrThrow(id));
    }

    @Transactional(readOnly = true)
    public StudentResponse getByResearchId(String researchId) {
        return toResponse(studentRepository.findByResearchId(researchId)
                .orElseThrow(() -> new EntityNotFoundException("Student not found: " + researchId)));
    }

    @Transactional
    public StudentResponse create(StudentRequest req, UUID actorId) {
        if (studentRepository.existsByResearchId(req.getResearchId()))
            throw new IllegalArgumentException("Research ID already exists: " + req.getResearchId());

        var saved = studentRepository.save(Student.builder()
                .researchId(req.getResearchId())
                .fullName(req.getFullName())
                .studentCode(req.getStudentCode())
                .email(req.getEmail())
                .build());

        auditLogService.log(
            actorId,
            AuditAction.CREATE_STUDENT,
            "students",
            saved.getId(),
            null,
            String.format("{\"researchId\":\"%s\",\"studentCode\":\"%s\"}", saved.getResearchId(), saved.getStudentCode()),
            null,
            null
        );

        return toResponse(saved);
    }


    @Transactional
    public StudentResponse update(UUID id, StudentRequest req, UUID actorId) {
        var entity = findOrThrow(id);

        String oldValue = String.format("{\"researchId\":\"%s\",\"studentCode\":\"%s\"}", 
            entity.getResearchId(), entity.getStudentCode());

        entity.setResearchId(req.getResearchId());
        entity.setFullName(req.getFullName());
        entity.setStudentCode(req.getStudentCode());
        entity.setEmail(req.getEmail());

        var saved = studentRepository.save(entity);

        auditLogService.log(
            actorId,
            AuditAction.UPDATE_STUDENT,
            "students",
            id,
            oldValue,
            String.format("{\"researchId\":\"%s\",\"studentCode\":\"%s\"}", saved.getResearchId(), saved.getStudentCode()),
            null,
            null
        );

        return toResponse(saved);
    }


    @Transactional
    public void deactivate(UUID id, UUID actorId) {
        var entity = findOrThrow(id);
        entity.setActive(false);
        studentRepository.save(entity);

        auditLogService.log(
            actorId,
            AuditAction.DELETE_STUDENT,
            "students",
            id,
            String.format("{\"researchId\":\"%s\"}", entity.getResearchId()),
            null,
            null,
            null
        );
    }

    private Student findOrThrow(UUID id) {
        return studentRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Student not found: " + id));
    }

    private StudentResponse toResponse(Student s) {
        return StudentResponse.builder()
                .id(s.getId())
                .researchId(s.getResearchId())
                .fullName(s.getFullName())
                .studentCode(s.getStudentCode())
                .email(s.getEmail())
                .isActive(s.isActive())
                .enrolledAt(s.getEnrolledAt())
                .build();
    }
}