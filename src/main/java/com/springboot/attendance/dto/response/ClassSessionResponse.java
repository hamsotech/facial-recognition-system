package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class ClassSessionResponse {
    private UUID id;
    private UUID classId;
    private String classCode;
    private String subjectName;
    private UUID createdById;
    private String createdByName;
    private OffsetDateTime startedAt;
    private OffsetDateTime endedAt;
    private String notes;
    private boolean isActive;
}