package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class AttendanceRecordResponse {
    private UUID id;
    private UUID sessionId;
    private UUID studentId;
    private String researchId;
    private String fullName;
    private String studentCode;
    private String status;
    private Double confidence;
    private OffsetDateTime detectedAt;
    private UUID overriddenById;
    private String overriddenByName;
    private String overrideReason;
}