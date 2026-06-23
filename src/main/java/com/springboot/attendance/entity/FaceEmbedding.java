package com.springboot.attendance.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "face_embeddings")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class FaceEmbedding {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "student_id", nullable = false)
    private Student student;

    @Column(name = "embedding", nullable = false)
    private byte[] embedding;

    @Enumerated(EnumType.STRING)
    @Column(name = "model_name", nullable = false, columnDefinition = "model_name")
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    private ModelName modelName;

    @Column(name = "embedding_dim", nullable = false)
    private Short embeddingDim;

    @Builder.Default
    @Column(name = "is_valid", nullable = false)
    private boolean isValid = true;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by", nullable = false)
    private User createdBy;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;
}