package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.ClassRequest;
import com.springboot.attendance.dto.response.ClassResponse;
import com.springboot.attendance.dto.response.PageResponse;
import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.entity.Class;
import com.springboot.attendance.repository.ClassRepository;
import com.springboot.attendance.repository.UserRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;

import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ClassService {

    private final ClassRepository classRepository;
    private final UserRepository userRepository;
    private final AuditLogService auditLogService;

    @Transactional(readOnly = true)
    public PageResponse<ClassResponse> getAll(Pageable pageable) {
        var page = classRepository.findAll(pageable);
        return PageResponse.<ClassResponse>builder()
                .content(page.getContent().stream().map(this::toResponse).toList())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .last(page.isLast())
                .build();
    }

    @Transactional(readOnly = true)
    public PageResponse<ClassResponse> getByLecturer(UUID lecturerId, Pageable pageable) {
        var page = classRepository.findByLecturerId(lecturerId, pageable);
        return PageResponse.<ClassResponse>builder()
                .content(page.getContent().stream().map(this::toResponse).toList())
                .page(page.getNumber())
                .size(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .last(page.isLast())
                .build();
    }

    @Transactional(readOnly = true)
    public ClassResponse getById(UUID id) {
        return toResponse(findOrThrow(id));
    }

    @Transactional
    public ClassResponse create(ClassRequest req, UUID createdById) {
        if (classRepository.existsByClassCode(req.getClassCode()))
            throw new IllegalArgumentException("Class code already exists: " + req.getClassCode());

        var lecturer = userRepository.findById(req.getLecturerId())
                .orElseThrow(() -> new EntityNotFoundException("Lecturer not found"));

        var saved = classRepository.save(Class.builder()
                .classCode(req.getClassCode())
                .subjectName(req.getSubjectName())
                .lecturer(lecturer)
                .academicYear(req.getAcademicYear())
                .term(req.getTerm())
                .build());

        auditLogService.log(
            createdById,
            AuditAction.CREATE_CLASS,
            "classes",
            saved.getId(),
            null,
            String.format("{\"classCode\":\"%s\",\"subjectName\":\"%s\"}", saved.getClassCode(), saved.getSubjectName()),
            null,
            null
        );

        return toResponse(saved);
    }

    @Transactional
    public ClassResponse update(UUID id, ClassRequest req, UUID actorId) {
        var entity = findOrThrow(id);
        var lecturer = userRepository.findById(req.getLecturerId())
                .orElseThrow(() -> new EntityNotFoundException("Lecturer not found"));

        String oldValue = String.format("{\"classCode\":\"%s\",\"subjectName\":\"%s\"}", entity.getClassCode(), entity.getSubjectName());

        entity.setClassCode(req.getClassCode());
        entity.setSubjectName(req.getSubjectName());
        entity.setLecturer(lecturer);
        entity.setAcademicYear(req.getAcademicYear());
        entity.setTerm(req.getTerm());

        var saved = classRepository.save(entity);

        auditLogService.log(
            actorId,
            AuditAction.UPDATE_CLASS,
            "classes",
            id,
            oldValue,
            String.format("{\"classCode\":\"%s\",\"subjectName\":\"%s\"}", saved.getClassCode(), saved.getSubjectName()),
            null,
            null
        );

        return toResponse(saved);
    }

    @Transactional
    public void deactivate(UUID id, UUID actorId) {
        var entity = findOrThrow(id);
        entity.setActive(false);
        classRepository.save(entity);

        auditLogService.log(
            actorId,
            AuditAction.DELETE_CLASS,
            "classes",
            id,
            String.format("{\"classCode\":\"%s\"}", entity.getClassCode()),
            null,
            null,
            null
        );
    }
    
    private Class findOrThrow(UUID id) {
        return classRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Class not found: " + id));
    }

    private ClassResponse toResponse(Class c) {
        return ClassResponse.builder()
                .id(c.getId())
                .classCode(c.getClassCode())
                .subjectName(c.getSubjectName())
                .lecturerId(c.getLecturer().getId())
                .lecturerName(c.getLecturer().getFullName())
                .academicYear(c.getAcademicYear())
                .term(c.getTerm())
                .isActive(c.isActive())
                .createdAt(c.getCreatedAt())
                .build();
    }
}