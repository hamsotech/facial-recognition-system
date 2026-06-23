package com.springboot.attendance.repository;

import com.springboot.attendance.entity.Class;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.util.Optional;
import java.util.UUID;

public interface ClassRepository extends JpaRepository<Class, UUID> {
    Optional<Class> findByClassCode(String classCode);
    Page<Class> findAll(Pageable pageable);
    Page<Class> findByLecturerId(UUID lecturerId, Pageable pageable);
    Page<Class> findByIsActiveTrue(Pageable pageable);
    boolean existsByClassCode(String classCode);
}