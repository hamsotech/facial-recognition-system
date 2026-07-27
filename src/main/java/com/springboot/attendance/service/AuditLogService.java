package com.springboot.attendance.service;

import com.springboot.attendance.dto.response.AuditLogResponse;
import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.entity.AuditLog;
import com.springboot.attendance.entity.User;
import com.springboot.attendance.repository.AuditLogRepository;
import com.springboot.attendance.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AuditLogService {

    private final AuditLogRepository auditLogRepository;
    private final UserRepository userRepository;

    @Async
    @Transactional
    public void log(UUID actorId,
                    AuditAction action,
                    String targetTable,
                    UUID targetId,
                    String oldValue,
                    String newValue,
                    String ipAddress,
                    String userAgent) {
        User actor = null;
        if (actorId != null) {
            actor = userRepository.findById(actorId).orElse(null);
        }

        auditLogRepository.save(AuditLog.builder()
                .actor(actor)
                .action(action)
                .targetTable(targetTable)
                .targetId(targetId)
                .oldValue(oldValue)
                .newValue(newValue)
                .ipAddress(ipAddress)
                .userAgent(userAgent)
                .build());
    }

    @Transactional(readOnly = true)
    public List<AuditLogResponse> getByActor(UUID actorId) {
        return auditLogRepository.findByActorIdOrderByCreatedAtDesc(actorId)
                .stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<AuditLogResponse> getByTarget(String targetTable, UUID targetId) {
        return auditLogRepository.findByTargetTableAndTargetId(targetTable, targetId)
                .stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<AuditLogResponse> getByAction(String action) {
        AuditAction auditAction;
        try {
            auditAction = AuditAction.valueOf(action);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid action: " + action);
        }
        return auditLogRepository.findByAction(auditAction)
                .stream().map(this::toResponse).toList();
    }

    private AuditLogResponse toResponse(AuditLog a) {
        return AuditLogResponse.builder()
                .id(a.getId())
                .actorId(a.getActor() != null ? a.getActor().getId() : null)
                .actorName(a.getActor() != null ? a.getActor().getFullName() : null)
                .action(a.getAction().name())
                .targetTable(a.getTargetTable())
                .targetId(a.getTargetId())
                .oldValue(a.getOldValue())
                .newValue(a.getNewValue())
                .ipAddress(a.getIpAddress())
                .userAgent(a.getUserAgent())
                .createdAt(a.getCreatedAt())
                .build();
    }
}