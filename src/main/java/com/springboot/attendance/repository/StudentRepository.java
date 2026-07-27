package com.springboot.attendance.repository;

import com.springboot.attendance.entity.Student;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.util.Optional;
import java.util.UUID;

public interface StudentRepository extends JpaRepository<Student, UUID> {
    Optional<Student> findByResearchId(String researchId);
    Page<Student> findAll(Pageable pageable);
    boolean existsByResearchId(String researchId);
}