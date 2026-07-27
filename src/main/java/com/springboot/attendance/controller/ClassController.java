package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.ClassRequest;
import com.springboot.attendance.dto.response.ClassResponse;
import com.springboot.attendance.dto.response.PageResponse;
import com.springboot.attendance.service.ClassService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/classes")
@RequiredArgsConstructor
public class ClassController {

    private final ClassService classService;

    @GetMapping
    public ResponseEntity<PageResponse<ClassResponse>> getAll(Pageable pageable) {
        return ResponseEntity.ok(classService.getAll(pageable));
    }
    
    @GetMapping("/lecturer/{lecturerId}")
    public ResponseEntity<PageResponse<ClassResponse>> getByLecturer(@PathVariable UUID lecturerId, Pageable pageable) {
        return ResponseEntity.ok(classService.getByLecturer(lecturerId, pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ClassResponse> getById(@PathVariable UUID id) {
        return ResponseEntity.ok(classService.getById(id));
    }

    @PostMapping
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<ClassResponse> create(@Valid @RequestBody ClassRequest req, @AuthenticationPrincipal UUID userId) {
        return ResponseEntity.status(HttpStatus.CREATED).body(classService.create(req, userId));
    }
    
    @PutMapping("/{id}")
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<ClassResponse> update(@PathVariable UUID id, @Valid @RequestBody ClassRequest req, @AuthenticationPrincipal UUID userId) {
        return ResponseEntity.ok(classService.update(id, req, userId));
    }
    
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<?> deactivate(@PathVariable UUID id, @AuthenticationPrincipal UUID userId) {
        classService.deactivate(id, userId);
        return ResponseEntity.ok(Map.of("message", "Class deactivated"));
    }
}