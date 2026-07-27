package com.springboot.attendance.repository;

import com.springboot.attendance.entity.FaceEmbedding;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface FaceEmbeddingRepository extends JpaRepository<FaceEmbedding, UUID> {
    Optional<FaceEmbedding> findByStudentIdAndIsValidTrue(UUID studentId);
    boolean existsByStudentIdAndIsValidTrue(UUID studentId);
}