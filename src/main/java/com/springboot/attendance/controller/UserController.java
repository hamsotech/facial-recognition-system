package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.ChangePasswordRequest;
import com.springboot.attendance.dto.request.UserRequest;
import com.springboot.attendance.dto.response.UserResponse;
import com.springboot.attendance.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<UserResponse>> getAll() {
        return ResponseEntity.ok(userService.getAll());
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<UserResponse> getById(@PathVariable UUID id) {
        return ResponseEntity.ok(userService.getById(id));
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<UserResponse> create(@Valid @RequestBody UserRequest req, @AuthenticationPrincipal UUID userId) {
        return ResponseEntity.status(HttpStatus.CREATED).body(userService.create(req, userId));
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<UserResponse> update(@PathVariable UUID id, @Valid @RequestBody UserRequest req, @AuthenticationPrincipal UUID userId) {
        return ResponseEntity.ok(userService.update(id, req, userId));
    }

    @PatchMapping("/{id}/activate")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<?> activate(@PathVariable UUID id, @AuthenticationPrincipal UUID userId) {
        userService.activate(id, userId);
        return ResponseEntity.ok(Map.of("message", "User activated"));
    }

    @PatchMapping("/{id}/deactivate")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<?> deactivate(@PathVariable UUID id, @AuthenticationPrincipal UUID userId) {
        userService.deactivate(id, userId);
        return ResponseEntity.ok(Map.of("message", "User deactivated"));
    }

    @PatchMapping("/{id}/change-password")
    public ResponseEntity<?> changePassword(@PathVariable UUID id, @Valid @RequestBody ChangePasswordRequest req, @AuthenticationPrincipal UUID userId) {
        userService.changePassword(id, req, userId);
        return ResponseEntity.ok(Map.of("message", "Password changed"));
    }
}