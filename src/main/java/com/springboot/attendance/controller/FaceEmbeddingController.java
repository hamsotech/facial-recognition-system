package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.FaceEmbeddingRequest;
import com.springboot.attendance.dto.response.FaceEmbeddingResponse;
import com.springboot.attendance.service.FaceEmbeddingService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/embeddings")
@RequiredArgsConstructor
public class FaceEmbeddingController {

    private final FaceEmbeddingService embeddingService;

    @GetMapping("/student/{studentId}")
    public ResponseEntity<FaceEmbeddingResponse> getByStudent(@PathVariable UUID studentId) {
        return ResponseEntity.ok(embeddingService.getByStudent(studentId));
    }

    @PostMapping
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<FaceEmbeddingResponse> save(
            @Valid @RequestBody FaceEmbeddingRequest req,
            @AuthenticationPrincipal UUID userId) {
        return ResponseEntity.ok(embeddingService.save(req, userId));
    }

    @DeleteMapping("/student/{studentId}")
    @PreAuthorize("hasAnyRole('ADMIN', 'LECTURER')")
    public ResponseEntity<?> invalidate(@PathVariable UUID studentId) {
        embeddingService.invalidate(studentId);
        return ResponseEntity.ok(Map.of("message", "Embedding invalidated"));
    }
}