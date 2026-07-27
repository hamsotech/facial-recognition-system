package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class ClassEnrollmentResponse {
    private UUID id;
    private UUID studentId;
    private String researchId;
    private String fullName;
    private String studentCode;
    private UUID classId;
    private String classCode;
    private String subjectName;
    private OffsetDateTime enrolledAt;
}