package com.springboot.attendance.controller;

import com.springboot.attendance.dto.request.LoginRequest;
import com.springboot.attendance.dto.request.RefreshTokenRequest;
import com.springboot.attendance.dto.response.AuthResponse;
import com.springboot.attendance.security.JwtUtil;
import com.springboot.attendance.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;


@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;
    private final JwtUtil jwtUtil;

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody LoginRequest req, HttpServletRequest httpReq) {
        return ResponseEntity.ok(authService.login(
                req,
                httpReq.getRemoteAddr(),
                httpReq.getHeader("User-Agent")
        ));
    }

    @PostMapping("/refresh")
    public ResponseEntity<AuthResponse> refresh(@Valid @RequestBody RefreshTokenRequest req) {
        return ResponseEntity.ok(authService.refresh(req));
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout(@Valid @RequestBody RefreshTokenRequest req) {
        authService.logout(req.getRefreshToken());
        return ResponseEntity.ok(Map.of("message", "Logged out"));
    }

    @PostMapping("/logout-all")
    public ResponseEntity<?> logoutAll(@AuthenticationPrincipal UUID userId) {
        authService.logoutAll(userId);
        return ResponseEntity.ok(Map.of("message", "All sessions revoked"));
    }

    @GetMapping("/verify")
    public ResponseEntity<?> verify(@RequestHeader("Authorization") String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer "))
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("valid", false));
    
        String token = authHeader.substring(7);
        if (!jwtUtil.isTokenValid(token))
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("valid", false));
    
        return ResponseEntity.ok(Map.of(
            "valid", true,
            "userId", jwtUtil.extractUserId(token),
            "role", jwtUtil.extractRole(token)
        ));
    }
    
}