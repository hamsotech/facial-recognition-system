package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.ClassEnrollmentRequest;
import com.springboot.attendance.dto.response.ClassEnrollmentResponse;
import com.springboot.attendance.entity.ClassEnrollment;
import com.springboot.attendance.repository.ClassEnrollmentRepository;
import com.springboot.attendance.repository.ClassRepository;
import com.springboot.attendance.repository.StudentRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service @RequiredArgsConstructor
public class ClassEnrollmentService {

    private final ClassEnrollmentRepository enrollmentRepository;
    private final StudentRepository studentRepository;
    private final ClassRepository classRepository;

    @Transactional(readOnly = true)
    public List<ClassEnrollmentResponse> getByClass(UUID classId) {
        return enrollmentRepository.findByClassEntity_Id(classId)
                .stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<ClassEnrollmentResponse> getByStudent(UUID studentId) {
        return enrollmentRepository.findByStudentId(studentId)
                .stream().map(this::toResponse).toList();
    }

    @Transactional
    public ClassEnrollmentResponse enroll(ClassEnrollmentRequest req) {
        if (enrollmentRepository.existsByStudentIdAndClassEntity_Id(req.getStudentId(), req.getClassId()))
            throw new IllegalArgumentException("Student already enrolled in this class");

        var student = studentRepository.findById(req.getStudentId())
                .orElseThrow(() -> new EntityNotFoundException("Student not found"));

        var classEntity = classRepository.findById(req.getClassId())
                .orElseThrow(() -> new EntityNotFoundException("Class not found"));

        return toResponse(enrollmentRepository.save(ClassEnrollment.builder()
                .student(student)
                .classEntity(classEntity)
                .build()));
    }

    @Transactional
    public void unenroll(UUID studentId, UUID classId) {
        var enrollment = enrollmentRepository.findByStudentIdAndClassEntity_Id(studentId, classId)
                .orElseThrow(() -> new EntityNotFoundException("Enrollment not found"));
        enrollmentRepository.delete(enrollment);
    }
    
    private ClassEnrollmentResponse toResponse(ClassEnrollment e) {
        return ClassEnrollmentResponse.builder()
                .id(e.getId())
                .studentId(e.getStudent().getId())
                .researchId(e.getStudent().getResearchId())
                .fullName(e.getStudent().getFullName())
                .studentCode(e.getStudent().getStudentCode())
                .classId(e.getClassEntity().getId())
                .classCode(e.getClassEntity().getClassCode())
                .subjectName(e.getClassEntity().getSubjectName())
                .enrolledAt(e.getEnrolledAt())
                .build();
    }
}