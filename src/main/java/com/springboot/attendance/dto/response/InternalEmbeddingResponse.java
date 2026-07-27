package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.util.UUID;

@Getter @Builder
public class InternalEmbeddingResponse {
    private UUID studentId;
    private String researchId;
    private byte[] embedding;
    private String modelName;
    private Short embeddingDim;
}