package com.springboot.attendance.repository;

import com.springboot.attendance.entity.BenchmarkResult;
import com.springboot.attendance.entity.BenchmarkScenario;
import com.springboot.attendance.entity.ModelName;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface BenchmarkResultRepository extends JpaRepository<BenchmarkResult, UUID> {
    List<BenchmarkResult> findByModelName(ModelName modelName);
    List<BenchmarkResult> findByScenario(BenchmarkScenario scenario);
    List<BenchmarkResult> findByModelNameAndScenario(ModelName modelName, BenchmarkScenario scenario);
    List<BenchmarkResult> findBySessionId(UUID sessionId);
}