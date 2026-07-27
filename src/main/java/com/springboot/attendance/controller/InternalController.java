package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.BenchmarkResultRequest;
import com.springboot.attendance.dto.request.InternalAttendanceRequest;
import com.springboot.attendance.dto.response.BenchmarkResultResponse;
import com.springboot.attendance.dto.response.InternalEmbeddingResponse;
import com.springboot.attendance.entity.AttendanceRecord;
import com.springboot.attendance.entity.AttendanceStatus;
import com.springboot.attendance.entity.FaceEmbedding;
import com.springboot.attendance.repository.AttendanceRecordRepository;
import com.springboot.attendance.repository.ClassSessionRepository;
import com.springboot.attendance.repository.FaceEmbeddingRepository;
import com.springboot.attendance.repository.StudentRepository;
import com.springboot.attendance.security.AesEncryptionUtil;
import com.springboot.attendance.service.BenchmarkResultService;
import jakarta.persistence.EntityNotFoundException;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/internal")
@RequiredArgsConstructor
public class InternalController {

    private final AttendanceRecordRepository attendanceRepository;
    private final ClassSessionRepository sessionRepository;
    private final StudentRepository studentRepository;
    private final FaceEmbeddingRepository embeddingRepository;
    private final BenchmarkResultService benchmarkService;
    private final AesEncryptionUtil encryptionUtil;

    @PostMapping("/attendance/mark")
    @Transactional
    public ResponseEntity<?> markAttendance(@Valid @RequestBody InternalAttendanceRequest req) {
        var session = sessionRepository.findById(req.getSessionId())
                .orElseThrow(() -> new EntityNotFoundException("Session not found"));

        if (session.getEndedAt() != null)
            return ResponseEntity.badRequest().body(Map.of("message", "Session already ended"));

        req.getResults().forEach(result -> {
            var existing = attendanceRepository
                    .findBySessionIdAndStudentId(req.getSessionId(), result.getStudentId());

            if (existing.isPresent()) {
                var record = existing.get();
                record.setStatus(AttendanceStatus.PRESENT);
                record.setConfidence(result.getConfidence());
                attendanceRepository.save(record);
            } else {
                var student = studentRepository.findById(result.getStudentId())
                        .orElse(null);
                if (student != null) {
                    attendanceRepository.save(AttendanceRecord.builder()
                            .session(session)
                            .student(student)
                            .status(AttendanceStatus.PRESENT)
                            .confidence(result.getConfidence())
                            .build());
                }
            }
        });

        return ResponseEntity.ok(Map.of("message", "Attendance marked", "count", req.getResults().size()));
    }

    @GetMapping("/embeddings/{studentId}")
    @Transactional(readOnly = true)
    public ResponseEntity<InternalEmbeddingResponse> getEmbedding(@PathVariable UUID studentId) {
        var embedding = embeddingRepository.findByStudentIdAndIsValidTrue(studentId)
                .orElseThrow(() -> new EntityNotFoundException("No active embedding for student: " + studentId));

        return ResponseEntity.ok(InternalEmbeddingResponse.builder()
                .studentId(embedding.getStudent().getId())
                .researchId(embedding.getStudent().getResearchId())
                .embedding(encryptionUtil.decrypt(embedding.getEmbedding()))
                .modelName(embedding.getModelName().name())
                .embeddingDim(embedding.getEmbeddingDim())
                .build());
    }


    @GetMapping("/embeddings")
    @Transactional(readOnly = true)
    public ResponseEntity<List<InternalEmbeddingResponse>> getAllEmbeddings() {
        var embeddings = embeddingRepository.findAll().stream()
                .filter(FaceEmbedding::isValid)
                .map(e -> InternalEmbeddingResponse.builder()
                        .studentId(e.getStudent().getId())
                        .researchId(e.getStudent().getResearchId())
                        .embedding(encryptionUtil.decrypt(e.getEmbedding()))
                        .modelName(e.getModelName().name())
                        .embeddingDim(e.getEmbeddingDim())
                        .build())
                .toList();

        return ResponseEntity.ok(embeddings);
    }

    @PostMapping("/benchmark")
    public ResponseEntity<BenchmarkResultResponse> saveBenchmark(
            @Valid @RequestBody BenchmarkResultRequest req) {
        return ResponseEntity.ok(benchmarkService.save(req));
    }
}