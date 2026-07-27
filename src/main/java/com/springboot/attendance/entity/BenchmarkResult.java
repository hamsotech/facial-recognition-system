package com.springboot.attendance.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "benchmark_results")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class BenchmarkResult {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id")
    private ClassSession session;

    @Enumerated(EnumType.STRING)
    @Column(name = "model_name", nullable = false, columnDefinition = "model_name")
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    private ModelName modelName;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, columnDefinition = "benchmark_scenario")
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    private BenchmarkScenario scenario;

    @Column(nullable = false)
    private Double threshold;

    @Enumerated(EnumType.STRING)
    @Column(name = "lighting_condition", columnDefinition = "lighting_condition")
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    private LightingCondition lightingCondition;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "face_angle", columnDefinition = "face_angle")
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    private FaceAngle faceAngle;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "occlusion", columnDefinition = "occlusion_type")
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    private OcclusionType occlusion;

    @Column(name = "distance_cm")
    private Integer distanceCm;
    @Column(name = "notes")
    private String notes;

    @Column private Double accuracy;
    @Column private Double precision;
    @Column private Double recall;
    @Column(name = "f1_score") private Double f1Score;
    @Column private Double far;
    @Column private Double frr;
    @Column private Double eer;
    @Column(name = "avg_latency") private Double avgLatency;
    @Column private Double fps;
    @Column(name = "sample_count") private Integer sampleCount;

    @CreationTimestamp
    @Column(name = "recorded_at", nullable = false, updatable = false)
    private OffsetDateTime recordedAt;
}