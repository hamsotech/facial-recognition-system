package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.ClassSessionRequest;
import com.springboot.attendance.dto.response.ClassSessionResponse;
import com.springboot.attendance.service.ClassSessionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/class-sessions")
@RequiredArgsConstructor
public class ClassSessionController {

    private final ClassSessionService sessionService;

    @GetMapping("/class/{classId}")
    public ResponseEntity<List<ClassSessionResponse>> getByClass(@PathVariable UUID classId) {
        return ResponseEntity.ok(sessionService.getByClass(classId));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ClassSessionResponse> getById(@PathVariable UUID id) {
        return ResponseEntity.ok(sessionService.getById(id));
    }

    @PostMapping
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<ClassSessionResponse> create(
            @Valid @RequestBody ClassSessionRequest req,
            @AuthenticationPrincipal UUID userId) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(sessionService.create(req, userId));
    }

    @PatchMapping("/{sessionId}/end")
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<ClassSessionResponse> end(@PathVariable UUID sessionId) {
        return ResponseEntity.ok(sessionService.end(sessionId));
    }

    @GetMapping("/{sessionId}/active")
    public ResponseEntity<?> isActive(@PathVariable UUID sessionId) {
        return ResponseEntity.ok(Map.of("active", sessionService.isActive(sessionId)));
    }
}