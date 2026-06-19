package com.springboot.attendance.repository;

import com.springboot.attendance.entity.AuditLog;
import com.springboot.attendance.entity.AuditAction;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface AuditLogRepository extends JpaRepository<AuditLog, UUID> {
    List<AuditLog> findByActorIdOrderByCreatedAtDesc(UUID actorId);
    List<AuditLog> findByTargetTableAndTargetId(String targetTable, UUID targetId);
    List<AuditLog> findByAction(AuditAction action);
}