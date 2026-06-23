package com.springboot.attendance.service;

import com.springboot.attendance.dto.request.LoginRequest;
import com.springboot.attendance.dto.request.RefreshTokenRequest;
import com.springboot.attendance.dto.response.AuthResponse;
import com.springboot.attendance.entity.AuditAction;
import com.springboot.attendance.entity.UserSession;
import com.springboot.attendance.repository.UserRepository;
import com.springboot.attendance.repository.UserSessionRepository;
import com.springboot.attendance.security.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.OffsetDateTime;
import java.util.HexFormat;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final UserSessionRepository userSessionRepository;
    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;
    private final AuditLogService auditLogService;

    @Transactional
    public AuthResponse login(LoginRequest req, String ipAddress, String userAgent) {
        var user = userRepository.findByUsername(req.getUsername())
                .orElseThrow(() -> new BadCredentialsException("Invalid credentials"));

        if (!user.isActive())
            throw new BadCredentialsException("Account is disabled");

        if (!passwordEncoder.matches(req.getPassword(), user.getPasswordHash()))
            throw new BadCredentialsException("Invalid credentials");

        String accessToken = jwtUtil.generateAccessToken(user.getId(), user.getUsername(), user.getRole().name());
        String refreshToken = jwtUtil.generateRefreshToken(user.getId());

        userSessionRepository.save(UserSession.builder()
                .user(user)
                .refreshTokenHash(hashToken(refreshToken))
                .ipAddress(ipAddress)
                .userAgent(userAgent)
                .isRevoked(false)
                .expiresAt(OffsetDateTime.now().plusSeconds(jwtUtil.getRefreshTokenExpiry()))
                .lastUsedAt(OffsetDateTime.now())
                .build());

        user.setLastLoginAt(OffsetDateTime.now());
        userRepository.save(user);

        auditLogService.log(
            user.getId(),
            AuditAction.LOGIN,
            "users",
            user.getId(),
            null,
            null,
            ipAddress,
            userAgent
        );

        return AuthResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .role(user.getRole().name())
                .username(user.getUsername())
                .build();
    }

    @Transactional
    public AuthResponse refresh(RefreshTokenRequest req) {
        String tokenHash = hashToken(req.getRefreshToken());

        var session = userSessionRepository.findByRefreshTokenHash(tokenHash)
                .orElseThrow(() -> new BadCredentialsException("Invalid refresh token"));

        if (session.isRevoked() || session.getExpiresAt().isBefore(OffsetDateTime.now()))
            throw new BadCredentialsException("Refresh token expired or revoked");

        var user = session.getUser();

        String newAccessToken = jwtUtil.generateAccessToken(user.getId(), user.getUsername(), user.getRole().name());
        String newRefreshToken = jwtUtil.generateRefreshToken(user.getId());

        session.setRevoked(true);
        userSessionRepository.save(session);

        userSessionRepository.save(UserSession.builder()
                .user(user)
                .refreshTokenHash(hashToken(newRefreshToken))
                .ipAddress(session.getIpAddress())
                .userAgent(session.getUserAgent())
                .isRevoked(false)
                .expiresAt(OffsetDateTime.now().plusSeconds(jwtUtil.getRefreshTokenExpiry()))
                .lastUsedAt(OffsetDateTime.now())
                .build());

        return AuthResponse.builder()
                .accessToken(newAccessToken)
                .refreshToken(newRefreshToken)
                .role(user.getRole().name())
                .username(user.getUsername())
                .build();
    }

    @Transactional
    public void logout(String refreshToken) {
        String tokenHash = hashToken(refreshToken);
        var sessionOpt = userSessionRepository.findByRefreshTokenHash(tokenHash);
        if (sessionOpt.isEmpty()) return;
    
        var session = sessionOpt.get();
        UUID userId = session.getUser().getId();
    
        session.setRevoked(true);
        userSessionRepository.save(session);
    
        auditLogService.log(
            userId,
            AuditAction.LOGOUT,
            "users",
            userId,
            null,
            null,
            null,
            null
        );
    }

    @Transactional
    public void logoutAll(UUID userId) {
        userSessionRepository.revokeAllByUserId(userId);
    }

    private String hashToken(String token) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(token.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }
}