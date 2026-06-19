package com.springboot.attendance.repository;

import com.springboot.attendance.entity.ClassSession;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface ClassSessionRepository extends JpaRepository<ClassSession, UUID> {
    List<ClassSession> findByClassEntity_Id(UUID classId);
    List<ClassSession> findByCreatedById(UUID userId);
}