package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.BenchmarkResultRequest;
import com.springboot.attendance.dto.response.BenchmarkResultResponse;
import com.springboot.attendance.entity.BenchmarkResult;
import com.springboot.attendance.entity.BenchmarkScenario;
import com.springboot.attendance.entity.ModelName;
import com.springboot.attendance.repository.BenchmarkResultRepository;
import com.springboot.attendance.repository.ClassSessionRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class BenchmarkResultService {

    private final BenchmarkResultRepository benchmarkRepository;
    private final ClassSessionRepository sessionRepository;

    @Transactional(readOnly = true)
    public List<BenchmarkResultResponse> getAll() {
        return benchmarkRepository.findAll().stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<BenchmarkResultResponse> getByModel(String modelName) {
        ModelName model = parseModel(modelName);
        return benchmarkRepository.findByModelName(model)
                .stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<BenchmarkResultResponse> getByScenario(String scenario) {
        BenchmarkScenario sc = parseScenario(scenario);
        return benchmarkRepository.findByScenario(sc)
                .stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<BenchmarkResultResponse> getByModelAndScenario(String modelName, String scenario) {
        return benchmarkRepository.findByModelNameAndScenario(parseModel(modelName), parseScenario(scenario))
                .stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<BenchmarkResultResponse> getBySession(UUID sessionId) {
        return benchmarkRepository.findBySessionId(sessionId)
                .stream().map(this::toResponse).toList();
    }

    @Transactional
    public BenchmarkResultResponse save(BenchmarkResultRequest req) {
        var builder = BenchmarkResult.builder()
                .modelName(parseModel(req.getModelName()))
                .scenario(parseScenario(req.getScenario()))
                .threshold(req.getThreshold())
                .accuracy(req.getAccuracy())
                .precision(req.getPrecision())
                .recall(req.getRecall())
                .f1Score(req.getF1Score())
                .far(req.getFar())
                .frr(req.getFrr())
                .eer(req.getEer())
                .avgLatency(req.getAvgLatency())
                .fps(req.getFps())
                .sampleCount(req.getSampleCount())
                .lightingCondition(req.getLightingCondition())
                .faceAngle(req.getFaceAngle())
                .occlusion(req.getOcclusion())
                .distanceCm(req.getDistanceCm())
                .notes(req.getNotes());

        if (req.getSessionId() != null) {
            var session = sessionRepository.findById(req.getSessionId())
                    .orElseThrow(() -> new EntityNotFoundException("Session not found"));
            builder.session(session);
        }
        return toResponse(benchmarkRepository.save(builder.build()));
    }
    
    private ModelName parseModel(String modelName) {
        try {
            return ModelName.valueOf(modelName);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid model name: " + modelName);
        }
    }

    private BenchmarkScenario parseScenario(String scenario) {
        try {
            return BenchmarkScenario.valueOf(scenario);
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid scenario: " + scenario);
        }
    }

    private BenchmarkResultResponse toResponse(BenchmarkResult b) {
        return BenchmarkResultResponse.builder()
                .id(b.getId())
                .sessionId(b.getSession() != null ? b.getSession().getId() : null)
                .modelName(b.getModelName().name())
                .scenario(b.getScenario().name())
                .threshold(b.getThreshold())
                .accuracy(b.getAccuracy())
                .precision(b.getPrecision())
                .recall(b.getRecall())
                .f1Score(b.getF1Score())
                .far(b.getFar())
                .frr(b.getFrr())
                .eer(b.getEer())
                .avgLatency(b.getAvgLatency())
                .fps(b.getFps())
                .sampleCount(b.getSampleCount())
                .recordedAt(b.getRecordedAt())
                .lightingCondition(b.getLightingCondition() != null ? b.getLightingCondition().name() : null)
                .faceAngle(b.getFaceAngle() != null ? b.getFaceAngle().name() : null)
                .occlusion(b.getOcclusion() != null ? b.getOcclusion().name() : null)
                .distanceCm(b.getDistanceCm())
                .notes(b.getNotes())
                .build();
    }
}