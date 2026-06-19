package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.FaceEmbeddingRequest;
import com.springboot.attendance.dto.response.FaceEmbeddingResponse;
import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.entity.FaceEmbedding;
import com.springboot.attendance.entity.ModelName;
import com.springboot.attendance.repository.FaceEmbeddingRepository;
import com.springboot.attendance.repository.StudentRepository;
import com.springboot.attendance.repository.UserRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class FaceEmbeddingService {

    private final FaceEmbeddingRepository embeddingRepository;
    private final StudentRepository studentRepository;
    private final UserRepository userRepository;
    private final AuditLogService auditLogService;

    @Transactional(readOnly = true)
    public FaceEmbeddingResponse getByStudent(UUID studentId) {
        return toResponse(embeddingRepository.findByStudentIdAndIsValidTrue(studentId)
                .orElseThrow(() -> new EntityNotFoundException("No active embedding for student: " + studentId)));
    }

    @Transactional
    public FaceEmbeddingResponse save(FaceEmbeddingRequest req, UUID createdById) {
        var student = studentRepository.findById(req.getStudentId())
                .orElseThrow(() -> new EntityNotFoundException("Student not found"));

        var createdBy = userRepository.findById(createdById)
                .orElseThrow(() -> new EntityNotFoundException("User not found"));

        embeddingRepository.findByStudentIdAndIsValidTrue(req.getStudentId())
                .ifPresent(e -> {
                    e.setValid(false);
                    embeddingRepository.save(e);
                });

        ModelName modelName;
        try {
            modelName = ModelName.valueOf(req.getModelName());
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid model name: " + req.getModelName());
        }

        var saved = embeddingRepository.save(FaceEmbedding.builder()
                .student(student)
                .embedding(req.getEmbedding())
                .modelName(modelName)
                .embeddingDim(req.getEmbeddingDim())
                .createdBy(createdBy)
                .build());

        auditLogService.log(
            createdById,
            AuditAction.CREATE_EMBEDDING,
            "face_embeddings",
            saved.getId(),
            null,
            String.format("{\"studentId\":\"%s\",\"modelName\":\"%s\"}", req.getStudentId(), req.getModelName()),
            null,
            null
        );

        return toResponse(saved);
    }    
    
    @Transactional
    public void invalidate(UUID studentId) {
        embeddingRepository.findByStudentIdAndIsValidTrue(studentId)
                .ifPresent(e -> {
                    UUID embeddingId = e.getId();
                    e.setValid(false);
                    embeddingRepository.save(e);

                    auditLogService.log(
                        null,
                        AuditAction.DELETE_EMBEDDING,
                        "face_embeddings",
                        embeddingId,
                        String.format("{\"studentId\":\"%s\"}", studentId),
                        null,
                        null,
                        null
                    );
                });
    }

    private FaceEmbeddingResponse toResponse(FaceEmbedding e) {
        return FaceEmbeddingResponse.builder()
                .id(e.getId())
                .studentId(e.getStudent().getId())
                .researchId(e.getStudent().getResearchId())
                .fullName(e.getStudent().getFullName())
                .modelName(e.getModelName().name())
                .embeddingDim(e.getEmbeddingDim())
                .isValid(e.isValid())
                .createdById(e.getCreatedBy().getId())
                .createdByName(e.getCreatedBy().getFullName())
                .createdAt(e.getCreatedAt())
                .updatedAt(e.getUpdatedAt())
                .build();
    }
}