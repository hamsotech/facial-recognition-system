package com.springboot.attendance.repository;

import com.springboot.attendance.entity.ClassEnrollment;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ClassEnrollmentRepository extends JpaRepository<ClassEnrollment, UUID> {
    List<ClassEnrollment> findByClassEntity_Id(UUID classId);
    List<ClassEnrollment> findByStudentId(UUID studentId);
    Optional<ClassEnrollment> findByStudentIdAndClassEntity_Id(UUID studentId, UUID classId);
    boolean existsByStudentIdAndClassEntity_Id(UUID studentId, UUID classId);
}