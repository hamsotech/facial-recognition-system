package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.ClassEnrollmentRequest;
import com.springboot.attendance.dto.response.ClassEnrollmentResponse;
import com.springboot.attendance.service.ClassEnrollmentService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/enrollments")
@RequiredArgsConstructor
public class ClassEnrollmentController {

    private final ClassEnrollmentService enrollmentService;

    @GetMapping("/class/{classId}")
    public ResponseEntity<List<ClassEnrollmentResponse>> getByClass(@PathVariable UUID classId) {
        return ResponseEntity.ok(enrollmentService.getByClass(classId));
    }

    @GetMapping("/student/{studentId}")
    public ResponseEntity<List<ClassEnrollmentResponse>> getByStudent(@PathVariable UUID studentId) {
        return ResponseEntity.ok(enrollmentService.getByStudent(studentId));
    }

    @PostMapping
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<ClassEnrollmentResponse> enroll(@Valid @RequestBody ClassEnrollmentRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(enrollmentService.enroll(req));
    }

    @DeleteMapping("/class/{classId}/student/{studentId}")
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<?> unenroll(@PathVariable UUID classId, @PathVariable UUID studentId) {
        enrollmentService.unenroll(studentId, classId);
        return ResponseEntity.ok(Map.of("message", "Student unenrolled"));
    }
}