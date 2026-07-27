package com.springboot.attendance.dto.request;

import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.Setter;

import java.util.UUID;

@Getter @Setter
public class ClassRequest {
    @NotBlank
    @Size(max = 20)
    private String classCode;

    @NotBlank
    @Size(max = 100)
    private String subjectName;

    @NotNull
    private UUID lecturerId;

    @NotNull
    @Min(2000)
    private Short academicYear;

    @NotNull
    @Min(1) @Max(3)
    private Short term;
}