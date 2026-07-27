package com.springboot.attendance.controller;

import com.springboot.attendance.dto.response.AuditLogResponse;
import com.springboot.attendance.service.AuditLogService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/audit-logs")
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogService auditLogService;

    @GetMapping("/actor/{actorId}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<AuditLogResponse>> getByActor(@PathVariable UUID actorId) {
        return ResponseEntity.ok(auditLogService.getByActor(actorId));
    }

    @GetMapping("/target")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<AuditLogResponse>> getByTarget(
            @RequestParam String targetTable,
            @RequestParam UUID targetId) {
        return ResponseEntity.ok(auditLogService.getByTarget(targetTable, targetId));
    }

    @GetMapping("/action/{action}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<AuditLogResponse>> getByAction(@PathVariable String action) {
        return ResponseEntity.ok(auditLogService.getByAction(action));
    }
}