package com.springboot.attendance.dto.response;

import lombok.Builder;
import lombok.Getter;

import java.time.OffsetDateTime;
import java.util.UUID;

@Getter @Builder
public class AuditLogResponse {
    private UUID id;
    private UUID actorId;
    private String actorName;
    private String action;
    private String targetTable;
    private UUID targetId;
    private String oldValue;
    private String newValue;
    private String ipAddress;
    private String userAgent;
    private OffsetDateTime createdAt;
}