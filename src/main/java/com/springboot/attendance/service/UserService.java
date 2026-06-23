package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.ChangePasswordRequest;
import com.springboot.attendance.dto.request.UserRequest;
import com.springboot.attendance.dto.response.UserResponse;
import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.entity.User;
import com.springboot.attendance.repository.UserRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuditLogService auditLogService;

    @Transactional(readOnly = true)
    public List<UserResponse> getAll() {
        return userRepository.findAll().stream().map(this::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public UserResponse getById(UUID id) {
        return toResponse(findOrThrow(id));
    }

    @Transactional
    public UserResponse create(UserRequest req, UUID actorId) {
        if (userRepository.existsByUsername(req.getUsername()))
            throw new IllegalArgumentException("Username already exists: " + req.getUsername());

        var saved = userRepository.save(User.builder()
                .username(req.getUsername())
                .passwordHash(passwordEncoder.encode(req.getPassword()))
                .fullName(req.getFullName())
                .email(req.getEmail())
                .role(req.getRole())
                .build());

        auditLogService.log(
            actorId,
            AuditAction.CREATE_USER,
            "users",
            saved.getId(),
            null,
            String.format("{\"username\":\"%s\",\"role\":\"%s\"}", req.getUsername(), req.getRole()),
            null,
            null
        );

        return toResponse(saved);
    }

    @Transactional
    public UserResponse update(UUID id, UserRequest req, UUID actorId) {
        var entity = findOrThrow(id);

        String oldValue = String.format("{\"username\":\"%s\",\"role\":\"%s\"}", entity.getUsername(), entity.getRole());

        entity.setFullName(req.getFullName());
        entity.setEmail(req.getEmail());
        entity.setRole(req.getRole());

        var saved = userRepository.save(entity);

        auditLogService.log(
            actorId,
            AuditAction.UPDATE_USER,
            "users",
            id,
            oldValue,
            String.format("{\"fullName\":\"%s\",\"role\":\"%s\"}", req.getFullName(), req.getRole()),
            null,
            null
        );

        return toResponse(saved);
    }

    @Transactional
    public void activate(UUID id, UUID actorId) {
        var entity = findOrThrow(id);
        entity.setActive(true);
        userRepository.save(entity);

        auditLogService.log(actorId, AuditAction.ACTIVATE_USER, "users", id, null, null, null, null);
    }

    @Transactional
    public void deactivate(UUID id, UUID actorId) {
        var entity = findOrThrow(id);
        entity.setActive(false);
        userRepository.save(entity);

        auditLogService.log(actorId, AuditAction.DEACTIVATE_USER, "users", id, null, null, null, null);
    }

    @Transactional
    public void changePassword(UUID id, ChangePasswordRequest req, UUID actorId) {
        var entity = findOrThrow(id);

        if (!passwordEncoder.matches(req.getOldPassword(), entity.getPasswordHash()))
            throw new BadCredentialsException("Old password is incorrect");

        entity.setPasswordHash(passwordEncoder.encode(req.getNewPassword()));
        userRepository.save(entity);

        auditLogService.log(actorId, AuditAction.RESET_PASSWORD, "users", id, null, null, null, null);
    }

    private User findOrThrow(UUID id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("User not found: " + id));
    }

    private UserResponse toResponse(User u) {
        return UserResponse.builder()
                .id(u.getId())
                .username(u.getUsername())
                .fullName(u.getFullName())
                .email(u.getEmail())
                .role(u.getRole().name())
                .isActive(u.isActive())
                .lastLoginAt(u.getLastLoginAt())
                .createdAt(u.getCreatedAt())
                .build();
    }
}