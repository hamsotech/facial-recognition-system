package com.springboot.attendance.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.Setter;

import java.util.UUID;

import com.springboot.attendance.entity.FaceAngle;
import com.springboot.attendance.entity.LightingCondition;
import com.springboot.attendance.entity.OcclusionType;

@Getter @Setter
public class BenchmarkResultRequest {
    private UUID sessionId;

    @NotBlank
    private String modelName;

    @NotBlank
    private String scenario;

    @NotNull
    private Double threshold;

    private LightingCondition lightingCondition;
    private FaceAngle faceAngle;
    private OcclusionType occlusion;
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
}