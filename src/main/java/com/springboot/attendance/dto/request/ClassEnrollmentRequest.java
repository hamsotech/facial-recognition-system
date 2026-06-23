package com.springboot.attendance.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.Setter;

import java.util.UUID;

@Getter @Setter
public class ClassEnrollmentRequest {
    @NotNull
    private UUID studentId;

    @NotNull
    private UUID classId;
}