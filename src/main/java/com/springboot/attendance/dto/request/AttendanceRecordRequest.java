package com.springboot.attendance.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.Setter;

import java.util.UUID;

@Getter @Setter
public class AttendanceRecordRequest {
    @NotNull
    private UUID sessionId;

    @NotNull
    private UUID studentId;

    private Double confidence;
}