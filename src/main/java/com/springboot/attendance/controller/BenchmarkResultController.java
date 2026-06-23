package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.BenchmarkResultRequest;
import com.springboot.attendance.dto.response.BenchmarkResultResponse;
import com.springboot.attendance.service.BenchmarkResultService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/benchmarks")
@RequiredArgsConstructor
public class BenchmarkResultController {

    private final BenchmarkResultService benchmarkService;

    @GetMapping
    public ResponseEntity<List<BenchmarkResultResponse>> getAll() {
        return ResponseEntity.ok(benchmarkService.getAll());
    }

    @GetMapping("/model/{modelName}")
    public ResponseEntity<List<BenchmarkResultResponse>> getByModel(@PathVariable String modelName) {
        return ResponseEntity.ok(benchmarkService.getByModel(modelName));
    }

    @GetMapping("/scenario/{scenario}")
    public ResponseEntity<List<BenchmarkResultResponse>> getByScenario(@PathVariable String scenario) {
        return ResponseEntity.ok(benchmarkService.getByScenario(scenario));
    }

    @GetMapping("/filter")
    public ResponseEntity<List<BenchmarkResultResponse>> getByModelAndScenario(
            @RequestParam String modelName,
            @RequestParam String scenario) {
        return ResponseEntity.ok(benchmarkService.getByModelAndScenario(modelName, scenario));
    }

    @GetMapping("/session/{sessionId}")
    public ResponseEntity<List<BenchmarkResultResponse>> getBySession(@PathVariable UUID sessionId) {
        return ResponseEntity.ok(benchmarkService.getBySession(sessionId));
    }

    @PostMapping
    @PreAuthorize("hasAnyRole('ADMIN', 'RESEARCHER')")
    public ResponseEntity<BenchmarkResultResponse> save(@Valid @RequestBody BenchmarkResultRequest req) {
        return ResponseEntity.ok(benchmarkService.save(req));
    }
}