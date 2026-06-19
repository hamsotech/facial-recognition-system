package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class BenchmarkResultResponse {
    private UUID id;
    private UUID sessionId;
    private String modelName;
    private String scenario;
    private Double threshold;
    private String lightingCondition;
    private String faceAngle;
    private String occlusion;
    private Integer distanceCm;
    private String notes;
    private Double accuracy;
    private Double precision;
    private Double recall;
    private Double f1Score;
    private Double far;
    private Double frr;
    private Double eer;
    private Double avgLatency;
    private Double fps;
    private Integer sampleCount;
    private OffsetDateTime recordedAt;
}