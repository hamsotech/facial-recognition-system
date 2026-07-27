package com.springboot.attendance.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.Setter;

import java.util.UUID;

@Getter @Setter
public class ClassSessionRequest {
    @NotNull
    private UUID classId;

    private String notes;
}