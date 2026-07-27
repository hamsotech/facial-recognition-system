package com.springboot.attendance.dto.request;

import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.Setter;

import java.util.List;
import java.util.UUID;

@Getter @Setter
public class InternalAttendanceRequest {
    @NotNull
    private UUID sessionId;

    @NotNull
    private List<RecognitionResult> results;

    @Getter @Setter
    public static class RecognitionResult {
        private UUID studentId;
        private Double confidence;
    }
}