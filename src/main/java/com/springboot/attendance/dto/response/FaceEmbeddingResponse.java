package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class FaceEmbeddingResponse {
    private UUID id;
    private UUID studentId;
    private String researchId;
    private String fullName;
    private String modelName;
    private Short embeddingDim;
    private boolean isValid;
    private UUID createdById;
    private String createdByName;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}