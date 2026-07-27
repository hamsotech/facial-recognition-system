package com.springboot.attendance.controller;

import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.service.AttendanceExportService;
import com.springboot.attendance.service.AuditLogService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/attendance/export")
@RequiredArgsConstructor
public class AttendanceExportController {

    private final AttendanceExportService exportService;
    private final AuditLogService auditLogService;

    @GetMapping("/session/{sessionId}")
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<byte[]> exportBySession(@PathVariable UUID sessionId, @AuthenticationPrincipal UUID userId) {
        byte[] csv = exportService.exportBySession(sessionId);

        auditLogService.log(
            userId,
            AuditAction.EXPORT_REPORT,
            "class_sessions",
            sessionId,
            null,
            null,
            null,
            null
        );

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"attendance_session_" + sessionId + ".csv\"")
                .contentType(MediaType.parseMediaType("text/csv"))
                .body(csv);
    }

    @GetMapping("/class/{classId}")
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<byte[]> exportByClass(@PathVariable UUID classId, @AuthenticationPrincipal UUID userId) {
        byte[] csv = exportService.exportByClass(classId);

        auditLogService.log(
            userId,
            AuditAction.EXPORT_REPORT,
            "classes",
            classId,
            null,
            null,
            null,
            null
        );

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"attendance_class_" + classId + ".csv\"")
                .contentType(MediaType.parseMediaType("text/csv"))
                .body(csv);
    }
}