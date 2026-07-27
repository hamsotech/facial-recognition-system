package com.springboot.attendance.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.Setter;

@Getter @Setter
public class AttendanceOverrideRequest {
    @NotNull
    private Boolean present;

    @NotBlank
    private String reason;
}