package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.StudentRequest;
import com.springboot.attendance.dto.response.PageResponse;
import com.springboot.attendance.dto.response.StudentResponse;
import com.springboot.attendance.service.StudentService;
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
@RequestMapping("/api/students")
@RequiredArgsConstructor
public class StudentController {

    private final StudentService studentService;

    @GetMapping
    public ResponseEntity<PageResponse<StudentResponse>> getAll(Pageable pageable) {
        return ResponseEntity.ok(studentService.getAll(pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<StudentResponse> getById(@PathVariable UUID id) {
        return ResponseEntity.ok(studentService.getById(id));
    }

    @GetMapping("/research/{researchId}")
    public ResponseEntity<StudentResponse> getByResearchId(@PathVariable String researchId) {
        return ResponseEntity.ok(studentService.getByResearchId(researchId));
    }

    @PostMapping
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<StudentResponse> create(@Valid @RequestBody StudentRequest req, @AuthenticationPrincipal UUID userId) {
        return ResponseEntity.status(HttpStatus.CREATED).body(studentService.create(req, userId));
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<StudentResponse> update(@PathVariable UUID id, @Valid @RequestBody StudentRequest req, @AuthenticationPrincipal UUID userId) {
        return ResponseEntity.ok(studentService.update(id, req, userId));
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<?> deactivate(@PathVariable UUID id, @AuthenticationPrincipal UUID userId) {
        studentService.deactivate(id, userId);
        return ResponseEntity.ok(Map.of("message", "Student deactivated"));
    }
}