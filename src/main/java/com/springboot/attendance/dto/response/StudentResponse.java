package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class StudentResponse {
    private UUID id;
    private String researchId;
    private String fullName;
    private String studentCode;
    private String email;
    private boolean isActive;
    private OffsetDateTime enrolledAt;
}