package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class ClassResponse {
    private UUID id;
    private String classCode;
    private String subjectName;
    private UUID lecturerId;
    private String lecturerName;
    private Short academicYear;
    private Short term;
    private boolean isActive;
    private OffsetDateTime createdAt;
}