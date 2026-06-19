package com.springboot.attendance.service;

import com.opencsv.CSVWriter;
import com.springboot.attendance.repository.AttendanceRecordRepository;
import com.springboot.attendance.repository.ClassSessionRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AttendanceExportService {

    private final AttendanceRecordRepository attendanceRepository;
    private final ClassSessionRepository sessionRepository;

    @Transactional(readOnly = true)
    public byte[] exportBySession(UUID sessionId) {
        var session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new EntityNotFoundException("Session not found"));

        var records = attendanceRepository.findBySessionId(sessionId);

        try (var baos = new ByteArrayOutputStream();
            var writer = new CSVWriter(new OutputStreamWriter(baos, StandardCharsets.UTF_8))) {

            // Header
            writer.writeNext(new String[]{
                "No", "Student Code", "Full Name", "Research ID",
                "Status", "Confidence", "Detected At", "Override Reason"
            });

            // Rows
            int[] index = {1};
            records.forEach(r -> writer.writeNext(new String[]{
                String.valueOf(index[0]++),
                r.getStudent().getStudentCode(),
                r.getStudent().getFullName(),
                r.getStudent().getResearchId(),
                r.getStatus().name(),
                r.getConfidence() != null ? String.format("%.4f", r.getConfidence()) : "",
                r.getDetectedAt().toString(),
                r.getOverrideReason() != null ? r.getOverrideReason() : ""
            }));

            writer.flush();
            return baos.toByteArray();

        } catch (IOException e) {
            throw new RuntimeException("Failed to export CSV", e);
        }
    }

    @Transactional(readOnly = true)
    public byte[] exportByClass(UUID classId) {
        var sessions = sessionRepository.findByClassEntity_Id(classId);

        try (var baos = new ByteArrayOutputStream();
            
        var writer = new CSVWriter(new OutputStreamWriter(baos, StandardCharsets.UTF_8))) {

            writer.writeNext(new String[]{
                "No", "Session Started At", "Student Code", "Full Name",
                "Research ID", "Status", "Confidence", "Detected At"
            });

            int[] index = {1};
            sessions.forEach(session -> {
                var records = attendanceRepository.findBySessionId(session.getId());
                records.forEach(r -> writer.writeNext(new String[]{
                    String.valueOf(index[0]++),
                    session.getStartedAt().toString(),
                    r.getStudent().getStudentCode(),
                    r.getStudent().getFullName(),
                    r.getStudent().getResearchId(),
                    r.getStatus().name(),
                    r.getConfidence() != null ? String.format("%.4f", r.getConfidence()) : "",
                    r.getDetectedAt().toString()
                }));
            });

            writer.flush();
            return baos.toByteArray();

        } catch (IOException e) {
            throw new RuntimeException("Failed to export CSV", e);
        }
    }
}